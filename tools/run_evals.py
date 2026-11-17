"""teacher-kit 평가 실행 도구.

evals/ 의 평가 문항을 실제로 돌린다.
  - 스킬 고르기(trigger): evals/trigger.json 의 질의마다 어떤 스킬이 불렸는지 기록한다.
  - 스킬 출력(output): evals/<스킬>.json 의 prompt 를 실행하고 assertion 별로 Claude 채점자가 판정한다.

실행 예 (저장소 루트에서):
    python tools/run_evals.py --jobs 3
    python tools/run_evals.py --mode output --skill rubric --id 1 --repeats 2

결과는 evals/results/<날짜시각>/ 에 results.json, summary.md 로 남는다.
표준 라이브러리만 쓴다. claude 호출은 Executor(함수)로 분리해 시험에서 바꿔 끼운다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_PREFIX = "teacher-kit:"
ALLOWED_OUTPUT_TOOLS = "Bash Read Write Edit Glob Grep Skill"
HWPX_CHECK = ROOT / "shared" / "scripts" / "make_hwpx_check.py"
MAX_FILE_TEXT = 6000
MAX_ASSISTANT_TEXT = 14000
DROPPED_ENV = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN")


# ---------------------------------------------------------------- 자료형

@dataclass(frozen=True)
class RunRequest:
    """claude 한 번 호출에 필요한 값."""
    prompt: str
    cwd: Path
    kind: str  # "trigger" | "output" | "judge"
    model: str | None = None
    timeout: int = 600
    plugin_dir: Path | None = None
    max_budget: float = 5.0
    stderr_path: Path | None = None  # claude의 오류 출력을 덧붙여 남길 파일(없으면 버림)


@dataclass(frozen=True)
class RunOutput:
    """claude 한 번 호출의 결과."""
    ok: bool
    error: str = ""
    result_text: str = ""
    assistant_text: str = ""        # 도구 사이 진행 문장까지 모은 전체 글
    tool_calls: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    cost: float = 0.0
    duration: float = 0.0
    final_text: str = ""            # 마지막 도구 호출 뒤의 최종 답변 (교사가 받는 답)
    stopped: bool = False           # 끝나기 전에 멈춘 실행(result 이벤트 없음). 최종 답변이 없다


def final_answer(out: RunOutput) -> str:
    """채점할 답변: 최종 답변. 없으면(가짜 실행기·옛 결과) 전체 글. 멈춘 실행은 최종 답변이 없다."""
    if out.stopped:
        return ""
    return out.final_text or out.result_text or out.assistant_text


STOPPED_NOTE = "중단된 실행(최종 답변 없음)"
Executor = Callable[[RunRequest], RunOutput]
HwpxChecker = Callable[[Path], dict]


@dataclass
class Config:
    """한 번의 실행 설정."""
    executor: Executor
    plugin_dir: Path
    model: str | None = None
    judge_model: str | None = "sonnet"
    repeats: int = 1
    jobs: int = 1
    timeout: int = 900
    trigger_timeout: int = 240
    judge_timeout: int = 300
    max_budget: float = 5.0
    work_root: Path = field(default_factory=lambda: Path(tempfile.gettempdir()))
    keep_dir: Path | None = None  # 산출 파일을 복사해 둘 결과 폴더(files/)
    hwpx_checker: HwpxChecker | None = None
    stderr_dir: Path | None = None  # 실행별 오류 출력 파일을 둘 결과 폴더(stderr/)


# ---------------------------------------------------------------- 문항 읽기

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_trigger_cases(evals_dir: Path, query_id: int | None = None) -> list[dict]:
    cases = read_json(evals_dir / "trigger.json")
    return [c for c in cases if query_id is None or c["id"] == query_id]


def load_skill_cases(evals_dir: Path, skill: str | None, case_id: int | None) -> list[dict]:
    """[{skill, id, name, prompt, expected_output, assertions, files}] 로 편다."""
    cases: list[dict] = []
    for path in sorted(evals_dir.glob("*.json")):
        if path.name == "trigger.json":
            continue
        data = read_json(path)
        if skill and data["skill_name"] != skill:
            continue
        for ev in data["evals"]:
            if case_id is not None and ev["id"] != case_id:
                continue
            cases.append({**ev, "skill": data["skill_name"]})
    return cases


# ---------------------------------------------------------------- JSON 형식 검사 (--validate)

def _is_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _expected_problem(value, known: set[str]) -> str | None:
    names = [value] if isinstance(value, str) else value
    if value is None:
        return None
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        return "expected_skill은 null, 스킬 이름, 또는 스킬 이름 목록이어야 함"
    unknown = [n for n in names if n not in known]
    return f"expected_skill에 없는 스킬 이름: {', '.join(unknown)}" if unknown else None


def _trigger_problems(cases, known: set[str]) -> list[str]:
    if not isinstance(cases, list):
        return ["trigger.json: 질의 목록([...])이어야 함"]
    problems, seen = [], set()
    for index, case in enumerate(cases, start=1):
        where = f"trigger.json {index}번째"
        if not isinstance(case, dict):
            problems.append(f"{where}: 항목은 {{...}} 꼴이어야 함")
            continue
        if not _is_id(case.get("id")):
            problems.append(f"{where}: id는 정수여야 함")
        elif case["id"] in seen:
            problems.append(f"{where}: id가 겹침 ({case['id']})")
        if _is_id(case.get("id")):
            seen.add(case["id"])
        if not _is_text(case.get("query")):
            problems.append(f"{where}: query에 질의 글이 있어야 함")
        if "expected_skill" not in case:
            problems.append(f"{where}: expected_skill이 없음 (안 불러야 하면 null)")
            continue
        problem = _expected_problem(case["expected_skill"], known)
        if problem:
            problems.append(f"{where}: {problem}")
    return problems


def _case_problems(case, where: str) -> list[str]:
    if not isinstance(case, dict):
        return [f"{where}: 항목은 {{...}} 꼴이어야 함"]
    checks = [(_is_id(case.get("id")), "id는 정수여야 함"), (_is_text(case.get("name")), "name에 이름이 있어야 함"),
              (_is_text(case.get("prompt")), "prompt에 질의 글이 있어야 함"),
              (isinstance(case.get("expected_output"), str), "expected_output은 글이어야 함"),
              (isinstance(case.get("files"), list) and all(isinstance(f, str) for f in case["files"]),
               "files는 파일 이름 목록이어야 함"),
              (isinstance(case.get("assertions"), list) and bool(case["assertions"])
               and all(_is_text(a) for a in case["assertions"]), "assertions는 글 목록이고 하나 이상이어야 함")]
    return [f"{where}: {message}" for ok, message in checks if not ok]


def _skill_file_problems(path: Path, data) -> list[str]:
    name = path.name
    if not isinstance(data, dict) or not isinstance(data.get("evals"), list):
        return [f"{name}: {{\"skill_name\": ..., \"evals\": [...]}} 꼴이어야 함"]
    problems = []
    if data.get("skill_name") != path.stem:
        problems.append(f"{name}: skill_name이 파일 이름({path.stem})과 다름: {data.get('skill_name')!r}")
    seen = set()
    for index, case in enumerate(data["evals"], start=1):
        problems += _case_problems(case, f"{name} {index}번째")
        case_id = case.get("id") if isinstance(case, dict) else None
        if not _is_id(case_id):
            continue
        if case_id in seen:
            problems.append(f"{name} {index}번째: id가 겹침 ({case_id})")
        seen.add(case_id)
    return problems


def validate_evals(evals_dir: Path, known_skills: set[str]) -> list[str]:
    """evals/ 의 JSON 모양을 검사해 문제 목록을 돌려준다. 실제로 claude를 부르지 않는다."""
    problems = []
    for path in sorted(evals_dir.glob("*.json")):
        try:
            data = read_json(path)
        except (OSError, ValueError) as error:
            problems.append(f"{path.name}: 읽을 수 없음 ({error})")
            continue
        if path.name == "trigger.json":
            problems += _trigger_problems(data, known_skills)
        else:
            problems += _skill_file_problems(path, data)
    return problems


def installed_skills() -> set[str]:
    return {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}


# ---------------------------------------------------------------- claude 이벤트 해석

@dataclass
class StreamState:
    """stream-json 이벤트를 모으는 상태."""
    texts: list[str] = field(default_factory=list)
    final_texts: list[str] = field(default_factory=list)     # 마지막 도구 호출 뒤의 글
    tool_calls: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    result_text: str = ""
    cost: float = 0.0
    is_error: bool = False
    error: str = ""
    finished: bool = False


def short_input(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False)
    return text if len(text) <= 160 else text[:157] + "..."


def consume_event(state: StreamState, event: dict) -> None:
    """이벤트 하나를 상태에 반영한다."""
    kind = event.get("type")
    if kind == "assistant":
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "text":
                state.texts.append(block["text"])
                state.final_texts.append(block["text"])
            elif block.get("type") == "tool_use":
                state.final_texts.clear()          # 도구 앞의 글은 진행 문장이다
                name, data = block.get("name", ""), block.get("input", {})
                state.tool_calls.append(f"{name} {short_input(data)}")
                if name == "Skill":
                    state.skills.append(str(data.get("skill", "")))
    elif kind == "result":
        state.finished = True
        state.result_text = event.get("result") or ""
        state.cost = float(event.get("total_cost_usd") or 0.0)
        if event.get("is_error"):
            state.is_error = True
            state.error = f"{event.get('subtype', 'error')}: {state.result_text[:200]}"


def first_plugin_skill(skills: tuple[str, ...] | list[str]) -> str | None:
    """불린 스킬 중 teacher-kit 스킬의 첫 이름(접두어 없이). 없으면 None."""
    for name in skills:
        if name.startswith(PLUGIN_PREFIX):
            return name[len(PLUGIN_PREFIX):]
    return None


# ---------------------------------------------------------------- 실제 claude 실행기

def build_command(req: RunRequest) -> list[str]:
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--setting-sources", "project", "--strict-mcp-config",
           "--max-budget-usd", str(req.max_budget)]
    if req.model:
        cmd += ["--model", req.model]
    if req.kind == "judge":
        return cmd + ["--tools", ""]
    if req.plugin_dir:
        cmd += ["--plugin-dir", str(req.plugin_dir)]
    if req.kind == "trigger":
        return cmd + ["--tools", "Skill"]
    cmd += ["--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED_OUTPUT_TOOLS.split(),
            "--disallowedTools", "WebFetch", "WebSearch"]
    return cmd


def child_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in DROPPED_ENV}
    env.update({"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
    return env


def open_stderr_sink(path: Path | None):
    """claude의 오류 출력을 받을 곳. 경로가 있으면 파일에 덧붙이고(재시도도 같은 파일), 없으면 버린다."""
    if path is None:
        return subprocess.DEVNULL
    path.parent.mkdir(parents=True, exist_ok=True)
    sink = open(path, "ab")
    sink.write(f"--- 실행 시작 {datetime.now():%Y-%m-%d %H:%M:%S} ---\n".encode("utf-8"))
    sink.flush()
    return sink


def close_stderr_sink(sink) -> None:
    if sink is not subprocess.DEVNULL:
        sink.close()


def stderr_file(cfg: Config, label: str) -> Path | None:
    """실행 하나의 오류 출력 파일 경로 (결과 폴더의 stderr/). 결과 폴더를 안 쓰는 설정이면 None."""
    return None if cfg.stderr_dir is None else cfg.stderr_dir / f"{label}.stderr.txt"


def run_claude(req: RunRequest) -> RunOutput:
    """claude -p 를 실행해 이벤트를 읽는다. trigger 는 첫 Skill 호출에서 멈춘다."""
    started = time.time()
    req.cwd.mkdir(parents=True, exist_ok=True)
    sink = open_stderr_sink(req.stderr_path)
    try:
        proc = subprocess.Popen(build_command(req), cwd=req.cwd, env=child_env(), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=sink)
    except BaseException:
        close_stderr_sink(sink)
        raise
    timer = threading.Timer(req.timeout, proc.kill)
    timer.start()
    state, stopped = StreamState(), False
    try:
        proc.stdin.write(req.prompt.encode("utf-8"))
        proc.stdin.close()
        for raw in proc.stdout:
            event = parse_line(raw)
            if event is None:
                continue
            consume_event(state, event)
            if req.kind == "trigger" and state.skills:
                stopped = True
                break
    finally:
        timer.cancel()
        proc.kill()
        proc.wait()
        close_stderr_sink(sink)
    return finish_output(state, stopped, time.time() - started, req.timeout)


def parse_line(raw: bytes) -> dict | None:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def finish_output(state: StreamState, stopped: bool, duration: float, timeout: int) -> RunOutput:
    ok = (state.finished and not state.is_error) or stopped
    cut_short = stopped and not state.finished              # 멈췄고 result가 없으면 최종 답변이 없다
    error = ""
    if not ok:
        error = state.error or (f"시간 초과({timeout}초)" if duration >= timeout else "결과 없이 종료")
    return RunOutput(ok=ok, error=error, result_text=state.result_text,
                     assistant_text="\n".join(state.texts), tool_calls=tuple(state.tool_calls),
                     skills=tuple(state.skills), cost=state.cost, duration=duration,
                     stopped=cut_short,
                     final_text="" if cut_short else (
                         state.result_text if state.result_text.strip() else "\n".join(state.final_texts)))


# ---------------------------------------------------------------- 스킬 고르기 평가

def expected_skills(expected: str | list[str] | None) -> list[str]:
    """기대 스킬 값(없음·이름 하나·이름 목록)을 목록으로 편다. 목록이면 그중 하나만 불려도 맞다."""
    if expected is None:
        return []
    return [expected] if isinstance(expected, str) else list(expected)


def case_expects(case: dict, skill: str) -> bool:
    return skill in expected_skills(case.get("expected_skill"))


def expected_label(expected: str | list[str] | None) -> str | None:
    """보고서에 적는 이름. 목록이면 '가/나'."""
    names = expected_skills(expected)
    return "/".join(names) if names else None


def classify_trigger(expected: str | list[str] | None, got: str | None) -> str:
    """correct | miss(놓침) | wrong(잘못 고름) | false_positive(엉뚱하게 부름)."""
    names = expected_skills(expected)
    if got in names or (not names and got is None):
        return "correct"
    if not names:
        return "false_positive"
    return "miss" if got is None else "wrong"


def run_with_retry(executor: Executor, req: RunRequest) -> tuple[RunOutput, int]:
    """실패하면 한 번만 다시 시도한다. (결과, 시도 횟수)."""
    out = executor(req)
    if out.ok:
        return out, 1
    return executor(req), 2


def run_trigger_case(case: dict, cfg: Config) -> dict:
    cwd = cfg.work_root / "trigger" / f"q{case['id']}"
    req = RunRequest(case["query"], cwd, "trigger", cfg.model, cfg.trigger_timeout,
                     cfg.plugin_dir, 1.0, stderr_file(cfg, f"trigger-q{case['id']}"))
    out, attempts = run_with_retry(cfg.executor, req)
    record = {"id": case["id"], "query": case["query"], "expected": expected_label(case["expected_skill"]),
              "attempts": attempts, "cost": out.cost, "duration": round(out.duration, 1)}
    if not out.ok:
        return {**record, "status": "error", "error": out.error}
    got = first_plugin_skill(out.skills)
    others = [s for s in out.skills if not s.startswith(PLUGIN_PREFIX)]
    return {**record, "status": "done", "got": got, "other_skills": others,
            "outcome": classify_trigger(case["expected_skill"], got)}


def trigger_group_label(expected: str) -> str:
    """기대 스킬이 목록이면('가/나') 한 줄로 세되 공통 질의임이 보이게 이름을 붙인다."""
    names = expected.split("/")
    if len(names) == 1:
        return expected
    kind = "학생부 공통" if all(n.endswith("-record") for n in names) else "공통"
    return f"{kind}({expected})"


def summarize_trigger(results: list[dict]) -> dict:
    done = [r for r in results if r["status"] == "done"]
    counts = {k: sum(1 for r in done if r["outcome"] == k)
              for k in ("correct", "miss", "wrong", "false_positive")}
    per_skill: dict[str, dict] = {}
    for r in done:
        if r["expected"]:
            row = per_skill.setdefault(trigger_group_label(r["expected"]), {"total": 0, "correct": 0})
            row["total"] += 1
            row["correct"] += r["outcome"] == "correct"
    return {"total": len(results), "done": len(done), "errors": len(results) - len(done),
            **counts, "accuracy": counts["correct"] / len(done) if done else 0.0,
            "per_skill": per_skill}


# ---------------------------------------------------------------- 산출물 수집

def hwpx_text(path: Path) -> str:
    """hwpx(zip) 의 본문 글자만 뽑는다."""
    try:
        with zipfile.ZipFile(path) as zf:
            names = sorted(n for n in zf.namelist() if re.search(r"Contents/section\d+\.xml$", n))
            xml = " ".join(zf.read(n).decode("utf-8", "replace") for n in names)
    except (zipfile.BadZipFile, OSError) as exc:
        return f"(hwpx 열기 실패: {exc})"
    text = re.sub(r"</hp:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", text)


def check_hwpx(path: Path) -> dict:
    """make_hwpx_check.py 로 구조를 검사한다."""
    try:
        proc = subprocess.run([sys.executable, str(HWPX_CHECK), str(path)], capture_output=True,
                              timeout=90, cwd=ROOT)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "message": f"검사 실행 실패: {exc}"}
    message = (proc.stdout + proc.stderr).decode("utf-8", "replace").strip()
    return {"ok": proc.returncode == 0, "message": message[:600]}


def collect_artifacts(workdir: Path, checker: HwpxChecker) -> list[dict]:
    """작업 폴더에 새로 생긴 파일 목록과 hwpx 검사·본문."""
    artifacts = []
    for path in sorted(p for p in workdir.rglob("*") if p.is_file() and not p.name.startswith(".")):
        item = {"name": str(path.relative_to(workdir)), "size": path.stat().st_size}
        if path.suffix.lower() == ".hwpx":
            item["check"] = checker(path)
            item["text"] = hwpx_text(path)[:MAX_FILE_TEXT]
        elif path.suffix.lower() in (".md", ".txt", ".csv", ".json"):
            item["text"] = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_TEXT]
        artifacts.append(item)
    return artifacts


# ---------------------------------------------------------------- LLM 채점

def build_judge_prompt(case: dict, out: RunOutput, artifacts: list[dict]) -> str:
    files = "\n".join(_describe_artifact(a) for a in artifacts) or "(만들어진 파일 없음)"
    assertions = "\n".join(f"{i}. {a}" for i, a in enumerate(case["assertions"], 1))
    tools = "\n".join(out.tool_calls[-40:]) or "(도구 호출 없음)"
    return (
        "너는 교사용 AI 스킬의 출력을 채점하는 엄격한 채점자다. 아래 [응답]과 [만든 파일]만 근거로 "
        "각 확인 항목이 사실인지 판정한다. 근거가 없으면 거짓이다. 이유는 한국어 한 줄로 쓴다.\n\n"
        f"[교사 요청]\n{case['prompt']}\n\n[기대 동작]\n{case['expected_output']}\n\n"
        f"[응답]\n{STOPPED_NOTE if out.stopped else final_answer(out)[-MAX_ASSISTANT_TEXT:]}\n\n"
        f"[도구 호출]\n{tools}\n\n[만든 파일]\n{files}\n\n[확인 항목]\n{assertions}\n\n"
        '출력은 JSON 배열 하나만: [{"index":1,"pass":true,"reason":"한 줄 이유"}, ...] '
        f"(항목 {len(case['assertions'])}개 모두)"
    )


def _describe_artifact(item: dict) -> str:
    head = f"- {item['name']} ({item['size']}바이트)"
    if "check" in item:
        head += f" 구조검사={'통과' if item['check']['ok'] else '실패'}: {item['check']['message'][:200]}"
    return head + (f"\n  본문:\n{item['text']}" if item.get("text") else "")


def parse_verdicts(text: str, count: int) -> list[dict] | None:
    """채점자 응답에서 JSON 배열을 읽어 항목 수만큼의 판정을 돌려준다."""
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        raw = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    by_index = {int(v.get("index", 0)): v for v in raw if isinstance(v, dict)}
    if set(by_index) != set(range(1, count + 1)):
        return None
    return [{"pass": bool(by_index[i].get("pass")), "reason": str(by_index[i].get("reason", ""))}
            for i in range(1, count + 1)]


def judge_case(case: dict, out: RunOutput, artifacts: list[dict], cfg: Config, cwd: Path) -> tuple[list[dict] | None, float]:
    """채점자 호출. 응답 형식이 틀리면 한 번 다시 시도한다. (판정, 비용)."""
    req = RunRequest(build_judge_prompt(case, out, artifacts), cwd, "judge", cfg.judge_model,
                     cfg.judge_timeout, None, 2.0,
                     stderr_file(cfg, f"judge-{case.get('skill', 'trigger')}-{case.get('id', 0)}"))
    cost = 0.0
    for _ in range(2):
        res = cfg.executor(req)
        cost += res.cost
        if res.ok:
            verdicts = parse_verdicts(res.result_text or res.assistant_text, len(case["assertions"]))
            if verdicts:
                return verdicts, cost
    return None, cost


# ---------------------------------------------------------------- 스킬 출력 평가

def run_output_case(case: dict, run_no: int, cfg: Config) -> dict:
    workdir = cfg.work_root / "output" / f"{case['skill']}-{case['id']}-r{run_no}"
    base = {"skill": case["skill"], "id": case["id"], "name": case["name"], "run": run_no}
    if workdir.exists():
        shutil.rmtree(workdir)
    req = RunRequest(case["prompt"], workdir, "output", cfg.model, cfg.timeout, cfg.plugin_dir, cfg.max_budget,
                     stderr_file(cfg, f"output-{case['skill']}-{case['id']}-r{run_no}"))
    out, attempts = run_with_retry(cfg.executor, req)
    base.update(attempts=attempts, cost=out.cost, duration=round(out.duration, 1),
                skills=list(out.skills), tool_calls=list(out.tool_calls))
    if not out.ok:
        return {**base, "status": "error", "error": out.error}
    artifacts = collect_artifacts(workdir, cfg.hwpx_checker or check_hwpx)
    keep_outputs(workdir, cfg.keep_dir, f"{case['skill']}-{case['id']}-r{run_no}")
    verdicts, judge_cost = judge_case(case, out, artifacts, cfg, cfg.work_root / "judge")
    base.update(cost=out.cost + judge_cost, stopped=out.stopped, response=final_answer(out)[-MAX_ASSISTANT_TEXT:],
                transcript=out.assistant_text[-MAX_ASSISTANT_TEXT:],
                files=[{k: v for k, v in a.items() if k != "text"} for a in artifacts])
    if verdicts is None:
        return {**base, "status": "error", "error": "채점 결과를 읽지 못함"}
    results = [{"assertion": a, **v} for a, v in zip(case["assertions"], verdicts)]
    return {**base, "status": "done", "assertions": results}


def rejudge_output(old: dict, case: dict, cfg: Config, work_dir: Path) -> dict:
    """저장된 작업 폴더와 응답으로 채점만 다시 한다 (실행은 다시 하지 않음)."""
    if old["status"] == "error" and "error" in old and "response" not in old:
        return old
    label = f"{case['skill']}-{case['id']}-r{old['run']}"
    workdir = work_dir.parent / "files" / label
    if not workdir.is_dir():
        workdir = work_dir / "output" / label
    out = RunOutput(ok=True, assistant_text=old.get("response", ""), tool_calls=tuple(old.get("tool_calls", ())),
                    stopped=bool(old.get("stopped")))
    artifacts = collect_artifacts(workdir, cfg.hwpx_checker or check_hwpx) if workdir.is_dir() else []
    verdicts, cost = judge_case(case, out, artifacts, cfg, work_dir / "judge")
    new = {**old, "cost": old["cost"] + cost,
           "files": [{k: v for k, v in a.items() if k != "text"} for a in artifacts]}
    if verdicts is None:
        return {**new, "status": "error", "error": "다시 채점 실패"}
    new.pop("error", None)
    return {**new, "status": "done",
            "assertions": [{"assertion": a, **v} for a, v in zip(case["assertions"], verdicts)]}


def rejudge_report(report: dict, cfg: Config, evals_dir: Path, result_dir: Path) -> dict:
    """결과 폴더의 results.json 을 읽어 출력 평가 채점만 다시 한다."""
    cases = {(c["skill"], c["id"]): c for c in load_skill_cases(evals_dir, None, None)}
    todo = report.get("outputs", [])
    done = parallel_map(lambda r: rejudge_output(r, cases[(r["skill"], r["id"])], cfg, result_dir / "work"), todo, cfg.jobs)
    return {**report, "outputs": done, "output_summary": summarize_outputs(done),
            "cost": report["cost"] + sum(d["cost"] - o["cost"] for d, o in zip(done, todo))}


def keep_outputs(workdir: Path, keep_dir: Path | None, label: str) -> None:
    """작업 폴더의 산출 파일을 결과 폴더로 복사한다."""
    if keep_dir is None or not workdir.is_dir():
        return
    shutil.copytree(workdir, keep_dir / label, dirs_exist_ok=True)


def summarize_outputs(results: list[dict]) -> dict:
    """스킬별 assertion 통과율."""
    per_skill: dict[str, dict] = {}
    for r in results:
        row = per_skill.setdefault(r["skill"], {"cases": 0, "errors": 0, "stopped": 0, "passed": 0, "total": 0})
        row["cases"] += 1
        row["stopped"] += bool(r.get("stopped"))
        if r["status"] != "done":
            row["errors"] += 1
            continue
        row["total"] += len(r["assertions"])
        row["passed"] += sum(1 for a in r["assertions"] if a["pass"])
    for row in per_skill.values():
        row["rate"] = row["passed"] / row["total"] if row["total"] else 0.0
    return per_skill


# ---------------------------------------------------------------- 요약 마크다운

def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def trigger_markdown(summary: dict, results: list[dict]) -> list[str]:
    lines = ["## 스킬 고르기", "",
             f"- 정확도: {pct(summary['accuracy'])} ({summary['correct']}/{summary['done']}), 실행 오류 {summary['errors']}건",
             f"- 놓침(써야 하는데 안 부름): {summary['miss']}건",
             f"- 잘못 고름(다른 스킬을 부름): {summary['wrong']}건",
             f"- 엉뚱하게 부름(안 써야 하는데 부름): {summary['false_positive']}건", "",
             "| 스킬 | 질의 수 | 맞게 고름 | 비율 |", "|---|---|---|---|"]
    for name, row in sorted(summary["per_skill"].items(), key=lambda item: ("공통(" in item[0], item[0])):
        lines.append(f"| {name} | {row['total']} | {row['correct']} | {pct(row['correct'] / row['total'])} |")
    if any("공통(" in name for name in summary["per_skill"]):
        lines += ["", "공통(...) 행은 기대 스킬이 목록인 질의다. 목록 가운데 아무 스킬이나 불러도 맞게 고른 것으로 센다."]
    lines += ["", "틀린 질의:", ""]
    for r in results:
        if r["status"] == "done" and r["outcome"] != "correct":
            lines.append(f"- [{r['id']}] 기대={r['expected']} 실제={r['got']} ({r['outcome']}) {r['query'][:60]}")
    return lines + [""]


def output_markdown(per_skill: dict, results: list[dict]) -> list[str]:
    lines = ["## 스킬 출력 (assertion 통과율)", "",
             "| 스킬 | 문항 | 오류 | 중단 | 통과/전체 | 통과율 |", "|---|---|---|---|---|---|"]
    for name, row in sorted(per_skill.items()):
        lines.append(f"| {name} | {row['cases']} | {row['errors']} | {row.get('stopped', 0)} | "
                     f"{row['passed']}/{row['total']} | {pct(row['rate'])} |")
    passed = sum(r["passed"] for r in per_skill.values())
    total = sum(r["total"] for r in per_skill.values())
    stopped = sum(r.get("stopped", 0) for r in per_skill.values())
    lines += ["", f"전체: {passed}/{total} ({pct(passed / total) if total else '-'})",
              f"{STOPPED_NOTE}: {stopped}건", "", "### 실패한 assertion", ""]
    for r in results:
        if r["status"] == "done":
            lines += [f"- {r['skill']} #{r['id']} {r['name']} (실행 {r['run']}): {a['assertion']} -> {a['reason']}"
                      for a in r["assertions"] if not a["pass"]]
    lines += ["", "### 실행 오류", ""]
    lines += [f"- {r['skill']} #{r['id']} (실행 {r['run']}, {r['attempts']}회 시도): {r.get('error', '')}"
              for r in results if r["status"] != "done"]
    return lines + [""]


def build_summary(report: dict) -> str:
    lines = ["# 평가 실행 요약", "",
             f"- 실행 시각: {report['started']}", f"- 걸린 시간: {report['elapsed_sec']}초",
             f"- 모델: {report['model'] or '기본값'} / 채점 모델: {report['judge_model']}",
             f"- claude 호출 비용 합계(추정): ${report['cost']:.2f}", ""]
    if report.get("trigger_summary"):
        lines += trigger_markdown(report["trigger_summary"], report["trigger"])
    if report.get("output_summary") is not None:
        lines += output_markdown(report["output_summary"], report["outputs"])
    return "\n".join(lines)


# ---------------------------------------------------------------- 전체 실행

def parallel_map(fn: Callable, items: list, jobs: int) -> list:
    if jobs <= 1:
        return [fn(i) for i in items]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(fn, items))


def run_all(cfg: Config, evals_dir: Path, mode: str, skill: str | None, case_id: int | None) -> dict:
    started = datetime.now()
    clock = time.time()
    report: dict = {"started": started.strftime("%Y-%m-%d %H:%M:%S"), "model": cfg.model,
                    "judge_model": cfg.judge_model, "repeats": cfg.repeats}
    if mode in ("all", "trigger"):
        cases = load_trigger_cases(evals_dir, case_id)
        if skill:
            cases = [c for c in cases if case_expects(c, skill)]
        report["trigger"] = parallel_map(lambda c: run_trigger_case(c, cfg), cases, cfg.jobs)
        report["trigger_summary"] = summarize_trigger(report["trigger"])
    if mode in ("all", "output"):
        jobs = [(c, n) for c in load_skill_cases(evals_dir, skill, case_id) for n in range(1, cfg.repeats + 1)]
        report["outputs"] = parallel_map(lambda j: run_output_case(j[0], j[1], cfg), jobs, cfg.jobs)
        report["output_summary"] = summarize_outputs(report["outputs"])
    everything = report.get("trigger", []) + report.get("outputs", [])
    report["cost"] = sum(r.get("cost", 0.0) for r in everything)
    report["elapsed_sec"] = round(time.time() - clock)
    return report


def write_report(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(build_summary(report), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="teacher-kit 평가 실행 (스킬 고르기·스킬 출력)")
    p.add_argument("--mode", choices=["all", "trigger", "output"], default="all", help="실행할 평가 종류")
    p.add_argument("--skill", help="스킬 이름 하나만")
    p.add_argument("--id", type=int, dest="case_id", help="문항(또는 질의) id 하나만")
    p.add_argument("--repeats", type=int, default=1, help="출력 평가 반복 횟수")
    p.add_argument("--model", help="실행 모델 (기본: claude 기본값)")
    p.add_argument("--judge-model", default="sonnet", help="채점 모델")
    p.add_argument("--jobs", type=int, default=1, help="동시에 돌릴 실행 수")
    p.add_argument("--timeout", type=int, default=900, help="출력 평가 한 건 제한 시간(초)")
    p.add_argument("--plugin-dir", type=Path, default=ROOT / "dist" / "plugin" / "teacher-kit",
                   help="평가할 플러그인 폴더 (python tools/build.py 로 만든 것)")
    p.add_argument("--evals-dir", type=Path, default=ROOT / "evals")
    p.add_argument("--validate", action="store_true", help="evals/ JSON 모양만 검사한다 (claude를 부르지 않음)")
    p.add_argument("--rejudge", type=Path, help="이 결과 폴더의 출력 채점만 다시 한다 (실행은 안 함)")
    p.add_argument("--work-dir", type=Path, help="실행 작업 폴더 (기본: 임시 폴더. 저장소 밖이어야 함)")
    p.add_argument("--results-dir", type=Path, help="결과를 둘 폴더 (기본: evals/results/<날짜시각>)")
    return p.parse_args(argv)


def rejudge_main(args: argparse.Namespace, executor: Executor) -> int:
    folder = args.rejudge
    report = read_json(folder / "results.json")
    cfg = Config(executor=executor, plugin_dir=args.plugin_dir, judge_model=args.judge_model, jobs=args.jobs)
    write_report(rejudge_report(report, cfg, args.evals_dir, folder), folder)
    print(f"다시 채점함: {folder}")
    return 0


def main(argv: list[str] | None = None, executor: Executor = run_claude) -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows 기본 콘솔(cp949)에서도 한국어가 깨지지 않게
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    args = parse_args(argv)
    if args.validate:
        problems = validate_evals(args.evals_dir, installed_skills())
        print("\n".join(problems) if problems else f"형식 검사 통과: {args.evals_dir}")
        return 1 if problems else 0
    if not (args.plugin_dir / "skills").is_dir():
        print(f"플러그인 폴더가 없습니다: {args.plugin_dir} (먼저 python tools/build.py)", file=sys.stderr)
        return 2
    if args.rejudge:
        return rejudge_main(args, executor)
    out_dir = args.results_dir or args.evals_dir / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    work_root = args.work_dir or Path(tempfile.gettempdir()) / "teacher-kit-evals" / out_dir.name
    if ROOT in work_root.resolve().parents or work_root.resolve() == ROOT:
        print("작업 폴더가 저장소 안에 있으면 스킬 원본을 읽어 결과가 오염됩니다.", file=sys.stderr)
        return 2
    cfg = Config(executor=executor, plugin_dir=args.plugin_dir, model=args.model,
                 judge_model=args.judge_model, repeats=args.repeats, jobs=args.jobs,
                 timeout=args.timeout, work_root=work_root, keep_dir=out_dir / "files", stderr_dir=out_dir / "stderr")
    report = run_all(cfg, args.evals_dir, args.mode, args.skill, args.case_id)
    write_report(report, out_dir)
    print(f"결과 폴더: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
