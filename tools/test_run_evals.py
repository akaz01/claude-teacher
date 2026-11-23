"""tools/run_evals.py 단위 시험 (실제 claude 호출 없이 가짜 실행기로)."""
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_evals as ev  # noqa: E402


def ok(**kw):
    return ev.RunOutput(ok=True, **kw)


def make_cfg(tmp_path, executor):
    return ev.Config(executor=executor, plugin_dir=tmp_path, work_root=tmp_path / "work",
                     hwpx_checker=lambda p: {"ok": True, "message": "정상"})


def test_classify_trigger():
    assert ev.classify_trigger("rubric", "rubric") == "correct"
    assert ev.classify_trigger(None, None) == "correct"
    assert ev.classify_trigger("rubric", None) == "miss"
    assert ev.classify_trigger("rubric", "worksheet") == "wrong"
    assert ev.classify_trigger(None, "worksheet") == "false_positive"


def test_first_plugin_skill_ignores_other_plugins():
    assert ev.first_plugin_skill(["deep-research", "teacher-kit:rubric"]) == "rubric"
    assert ev.first_plugin_skill(["deep-research"]) is None


def test_consume_event_collects_skill_text_and_result():
    state = ev.StreamState()
    ev.consume_event(state, {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "안녕"},
        {"type": "tool_use", "name": "Skill", "input": {"skill": "teacher-kit:worksheet"}}]}})
    ev.consume_event(state, {"type": "result", "result": "끝", "total_cost_usd": 0.5})
    assert state.skills == ["teacher-kit:worksheet"] and state.texts == ["안녕"]
    assert state.finished and state.cost == 0.5 and not state.is_error


def stream(*events):
    state = ev.StreamState()
    for event in events:
        ev.consume_event(state, event)
    return ev.finish_output(state, False, 1.0, 600)


PROGRESS = "파일을 만드는 중입니다."          # 도구를 부르기 전에 쓴 진행 문장
TOOL_TURN = {"type": "assistant", "message": {"content": [
    {"type": "text", "text": PROGRESS}, {"type": "tool_use", "name": "Write", "input": {"file_path": "a.json"}}]}}
FINAL_TURN = {"type": "assistant", "message": {"content": [{"type": "text", "text": "> 책임 안내\n최종 답"}]}}


def test_final_text_is_the_answer_after_the_last_tool_call():
    out = stream(TOOL_TURN, FINAL_TURN, {"type": "result", "result": "> 책임 안내\n최종 답"})
    assert out.final_text == "> 책임 안내\n최종 답"
    assert PROGRESS in out.assistant_text            # 전체 글은 따로 남는다


def test_final_text_falls_back_to_texts_after_the_last_tool_call():
    out = stream(TOOL_TURN, FINAL_TURN, {"type": "result", "result": ""})
    assert out.final_text == "> 책임 안내\n최종 답"


def test_judge_sees_only_the_final_answer():
    out = stream(TOOL_TURN, FINAL_TURN, {"type": "result", "result": "> 책임 안내\n최종 답"})
    case = {"prompt": "p", "expected_output": "e", "assertions": ["책임 안내가 맨 위"]}
    prompt = ev.build_judge_prompt(case, out, [])
    assert "[응답]\n> 책임 안내\n최종 답\n" in prompt and PROGRESS not in prompt


def test_output_case_saves_final_answer_and_full_transcript(tmp_path):
    seen = []

    def fake(req):
        if req.kind == "judge":
            seen.append(req.prompt)
            return ok(result_text='[{"index":1,"pass":true,"reason":"ok"}]')
        return ok(assistant_text=f"{PROGRESS}\n최종 답", final_text="최종 답", skills=("teacher-kit:rubric",))

    case = {"skill": "rubric", "id": 1, "name": "n", "prompt": "p", "expected_output": "e", "assertions": ["x"]}
    result = ev.run_output_case(case, 1, make_cfg(tmp_path, fake))
    assert result["response"] == "최종 답" and PROGRESS in result["transcript"]
    assert PROGRESS not in seen[0]


def test_consume_event_marks_error():
    state = ev.StreamState()
    ev.consume_event(state, {"type": "result", "is_error": True, "subtype": "error_max_budget", "result": ""})
    assert state.is_error and "error_max_budget" in state.error


def test_parse_verdicts_accepts_wrapped_json_and_rejects_missing_index():
    text = '판정:\n[{"index":1,"pass":true,"reason":"a"},{"index":2,"pass":false,"reason":"b"}]'
    assert ev.parse_verdicts(text, 2) == [{"pass": True, "reason": "a"}, {"pass": False, "reason": "b"}]
    assert ev.parse_verdicts('[{"index":1,"pass":true}]', 2) is None
    assert ev.parse_verdicts("없음", 1) is None


def test_trigger_case_counts_and_summary(tmp_path):
    answers = {"q1": ("teacher-kit:rubric",), "q2": (), "q3": ("teacher-kit:worksheet",), "q4": ("deep-research",)}

    def fake(req):
        return ok(skills=answers[req.cwd.name])

    cfg = make_cfg(tmp_path, fake)
    cases = [{"id": 1, "query": "a", "expected_skill": "rubric"},
             {"id": 2, "query": "b", "expected_skill": "rubric"},
             {"id": 3, "query": "c", "expected_skill": None},
             {"id": 4, "query": "d", "expected_skill": None}]
    results = [ev.run_trigger_case(c, cfg) for c in cases]
    summary = ev.summarize_trigger(results)
    assert (summary["correct"], summary["miss"], summary["false_positive"], summary["wrong"]) == (2, 1, 1, 0)
    assert summary["accuracy"] == 0.5
    assert results[3]["other_skills"] == ["deep-research"]


def test_trigger_error_retried_once(tmp_path):
    calls = []

    def fake(req):
        calls.append(1)
        return ev.RunOutput(ok=False, error="시간 초과")

    result = ev.run_trigger_case({"id": 1, "query": "a", "expected_skill": None}, make_cfg(tmp_path, fake))
    assert len(calls) == 2 and result["status"] == "error" and result["attempts"] == 2


def test_output_case_judged_per_assertion_and_collects_hwpx(tmp_path):
    def fake(req):
        if req.kind == "judge":
            return ok(result_text='[{"index":1,"pass":true,"reason":"ok"},{"index":2,"pass":false,"reason":"없음"}]')
        req.cwd.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(req.cwd / "a.hwpx", "w") as zf:
            zf.writestr("Contents/section0.xml", "<hp:p><hp:t>채점기준</hp:t></hp:p>")
        return ok(assistant_text="만들었어요", skills=("teacher-kit:rubric",))

    case = {"skill": "rubric", "id": 1, "name": "n", "prompt": "p", "expected_output": "e",
            "assertions": ["x", "y"]}
    result = ev.run_output_case(case, 1, make_cfg(tmp_path, fake))
    assert result["status"] == "done"
    assert [a["pass"] for a in result["assertions"]] == [True, False]
    assert result["files"][0]["check"]["ok"] is True
    summary = ev.summarize_outputs([result])
    assert summary["rubric"]["passed"] == 1 and summary["rubric"]["total"] == 2


def test_output_case_bad_judge_is_error(tmp_path):
    def fake(req):
        return ok(result_text="형식 아님") if req.kind == "judge" else ok(assistant_text="답")

    case = {"skill": "rubric", "id": 1, "name": "n", "prompt": "p", "expected_output": "e", "assertions": ["x"]}
    result = ev.run_output_case(case, 1, make_cfg(tmp_path, fake))
    assert result["status"] == "error"


def test_hwpx_text_extracts_paragraphs(tmp_path):
    path = tmp_path / "t.hwpx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/section0.xml", "<hp:p><hp:t>하나</hp:t></hp:p><hp:p><hp:t>둘</hp:t></hp:p>")
    assert ev.hwpx_text(path).split() == ["하나", "둘"]


def test_load_cases_filters(tmp_path):
    (tmp_path / "rubric.json").write_text(json.dumps({"skill_name": "rubric", "evals": [
        {"id": 1, "name": "a", "prompt": "p", "expected_output": "", "files": [], "assertions": ["x"]},
        {"id": 2, "name": "b", "prompt": "p", "expected_output": "", "files": [], "assertions": ["x"]}]}),
        encoding="utf-8-sig")
    (tmp_path / "trigger.json").write_text(json.dumps([{"id": 1, "query": "q", "expected_skill": None}]),
                                           encoding="utf-8")
    assert len(ev.load_skill_cases(tmp_path, "rubric", None)) == 2
    assert [c["id"] for c in ev.load_skill_cases(tmp_path, None, 2)] == [2]
    assert ev.load_skill_cases(tmp_path, "worksheet", None) == []
    assert len(ev.load_trigger_cases(tmp_path)) == 1


def test_build_command_per_kind(tmp_path):
    base = dict(prompt="p", cwd=tmp_path, plugin_dir=tmp_path)
    trig = ev.build_command(ev.RunRequest(kind="trigger", **base))
    assert "--tools" in trig and "Skill" in trig and "--plugin-dir" in trig
    judge = ev.build_command(ev.RunRequest(kind="judge", **base))
    assert "--plugin-dir" not in judge
    out = ev.build_command(ev.RunRequest(kind="output", model="sonnet", **base))
    assert "--allowedTools" in out and "sonnet" in out


def test_main_end_to_end_writes_reports(tmp_path):
    evals = tmp_path / "evals"
    evals.mkdir()
    (evals / "rubric.json").write_text(json.dumps({"skill_name": "rubric", "evals": [
        {"id": 1, "name": "a", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["x"]}]}),
        encoding="utf-8")
    (evals / "trigger.json").write_text(json.dumps([{"id": 1, "query": "q", "expected_skill": "rubric"}]),
                                        encoding="utf-8")
    (tmp_path / "plugin" / "skills").mkdir(parents=True)

    def fake(req):
        if req.kind == "judge":
            return ok(result_text='[{"index":1,"pass":true,"reason":"ok"}]')
        return ok(assistant_text="답", skills=("teacher-kit:rubric",))

    out = tmp_path / "res"
    code = ev.main(["--evals-dir", str(evals), "--plugin-dir", str(tmp_path / "plugin"),
                    "--results-dir", str(out)], executor=fake)
    assert code == 0
    report = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert report["trigger_summary"]["accuracy"] == 1.0
    assert "rubric" in (out / "summary.md").read_text(encoding="utf-8")


def test_main_resolves_relative_plugin_dir(tmp_path, monkeypatch):
    # claude는 임시 작업 폴더에서 돈다. 상대 경로를 그대로 넘기면 플러그인을 못 찾아 모든 질의가 '놓침'이 된다
    evals = tmp_path / "evals"
    evals.mkdir()
    (evals / "trigger.json").write_text(json.dumps([{"id": 1, "query": "q", "expected_skill": "rubric"}]),
                                        encoding="utf-8")
    (tmp_path / "plugin" / "skills").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    seen = []

    def fake(req):
        seen.append(req.plugin_dir)
        return ok(skills=("teacher-kit:rubric",))

    code = ev.main(["--mode", "trigger", "--evals-dir", str(evals), "--plugin-dir", "plugin",
                    "--results-dir", str(tmp_path / "res")], executor=fake)
    assert code == 0
    assert seen == [(tmp_path / "plugin").resolve()]


@pytest.mark.parametrize("value,expected", [(0.5, "50.0%"), (1, "100.0%")])
def test_pct(value, expected):
    assert ev.pct(value) == expected


def test_rejudge_uses_saved_response_and_workdir(tmp_path):
    work = tmp_path / "work" / "output" / "rubric-1-r1"
    work.mkdir(parents=True)
    (work / "a.txt").write_text("내용", encoding="utf-8")
    old = {"skill": "rubric", "id": 1, "name": "n", "run": 1, "status": "done", "cost": 1.0,
           "response": "답", "tool_calls": [], "assertions": [{"assertion": "x", "pass": False, "reason": "r"}]}
    case = {"skill": "rubric", "id": 1, "name": "n", "prompt": "p", "expected_output": "e", "assertions": ["x"]}
    seen = []

    def fake(req):
        seen.append(req.prompt)
        return ok(result_text='[{"index":1,"pass":true,"reason":"고침"}]')

    new = ev.rejudge_output(old, case, make_cfg(tmp_path, fake), tmp_path / "work")
    assert new["assertions"][0]["pass"] is True and "내용" in seen[0]


# ---------------------------------------------------------------- expected_skill 목록

def test_classify_trigger_accepts_any_skill_of_a_list():
    pair = ["activity-record", "subject-record"]
    assert ev.classify_trigger(pair, "subject-record") == "correct"
    assert ev.classify_trigger(pair, "activity-record") == "correct"
    assert ev.classify_trigger(pair, None) == "miss"
    assert ev.classify_trigger(pair, "worksheet") == "wrong"


def test_trigger_list_case_summary_and_skill_filter(tmp_path):
    cfg = make_cfg(tmp_path, lambda req: ok(skills=("teacher-kit:subject-record",)))
    case = {"id": 1, "query": "학생 개인정보 일반 작업", "expected_skill": ["activity-record", "subject-record"]}
    result = ev.run_trigger_case(case, cfg)
    assert result["outcome"] == "correct"
    summary = ev.summarize_trigger([result])
    label = "학생부 공통(activity-record/subject-record)"
    assert summary["per_skill"][label] == {"total": 1, "correct": 1}
    table = ev.trigger_markdown(summary, [result])
    assert any(label in line for line in table)
    assert any("목록 가운데 아무 스킬이나" in line for line in table)
    assert ev.case_expects(case, "subject-record") and not ev.case_expects(case, "rubric")
    assert ev.case_expects({"expected_skill": "rubric"}, "rubric") and not ev.case_expects({"expected_skill": None}, "rubric")


# ---------------------------------------------------------------- JSON 형식 검사 (--validate)

def write_evals(folder, trigger=None, skill_cases=None, skill_name="rubric"):
    folder.mkdir(exist_ok=True)
    good_trigger = [{"id": 1, "query": "q", "expected_skill": "rubric"}, {"id": 2, "query": "r", "expected_skill": None},
                    {"id": 3, "query": "s", "expected_skill": ["rubric", "worksheet"]}]
    good_case = {"id": 1, "name": "a", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["x"]}
    (folder / "trigger.json").write_text(json.dumps(trigger or good_trigger), encoding="utf-8")
    (folder / "rubric.json").write_text(json.dumps({"skill_name": skill_name, "evals": skill_cases or [good_case]}),
                                        encoding="utf-8")


KNOWN = {"rubric", "worksheet"}


def test_validate_passes_good_files(tmp_path):
    write_evals(tmp_path)
    assert ev.validate_evals(tmp_path, KNOWN) == []


@pytest.mark.parametrize("trigger,phrase", [
    ([{"id": 1, "query": "q", "expected_skill": "rubric"}, {"id": 1, "query": "r", "expected_skill": None}], "id가 겹침"),
    ([{"id": 1, "query": "", "expected_skill": None}], "query"),
    ([{"id": 1, "query": "q", "expected_skill": "없는스킬"}], "없는스킬"),
    ([{"id": 1, "query": "q", "expected_skill": ["rubric", 3]}], "expected_skill"),
    ([{"id": 1, "query": "q", "expected_skill": []}], "expected_skill"),
    ([{"id": 1, "query": "q"}], "expected_skill"),
    ({"id": 1}, "목록"),
])
def test_validate_reports_bad_trigger_cases(tmp_path, trigger, phrase):
    write_evals(tmp_path, trigger=trigger)
    problems = ev.validate_evals(tmp_path, KNOWN)
    assert problems and any(phrase in problem and "trigger.json" in problem for problem in problems)


@pytest.mark.parametrize("change,phrase", [
    ({"prompt": ""}, "prompt"), ({"assertions": []}, "assertions"), ({"assertions": ["x", 5]}, "assertions"),
    ({"files": "a.pdf"}, "files"), ({"name": 3}, "name"), ({"expected_output": None}, "expected_output"),
    ({"id": "1"}, "id"),
])
def test_validate_reports_bad_output_cases(tmp_path, change, phrase):
    case = {"id": 1, "name": "a", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["x"], **change}
    write_evals(tmp_path, skill_cases=[case])
    problems = ev.validate_evals(tmp_path, KNOWN)
    assert any(phrase in problem and "rubric.json" in problem for problem in problems)


def test_validate_reports_duplicate_ids_and_wrong_skill_name(tmp_path):
    case = {"id": 1, "name": "a", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["x"]}
    write_evals(tmp_path, skill_cases=[case, dict(case)], skill_name="worksheet")
    problems = "\n".join(ev.validate_evals(tmp_path, KNOWN))
    assert "id가 겹침" in problems and "skill_name" in problems


def test_validate_reports_unreadable_json(tmp_path):
    write_evals(tmp_path)
    (tmp_path / "rubric.json").write_text("{", encoding="utf-8")
    assert any("rubric.json" in problem and "읽을 수 없음" in problem for problem in ev.validate_evals(tmp_path, KNOWN))


def test_main_validate_needs_no_plugin_and_sets_exit_code(tmp_path, capsys):
    evals = tmp_path / "evals"
    write_evals(evals, skill_name="rubric")
    assert ev.main(["--validate", "--evals-dir", str(evals), "--plugin-dir", str(tmp_path / "없음")],
                   executor=lambda req: pytest.fail("claude를 부르면 안 됨")) == 0
    write_evals(evals, skill_cases=[{"id": 1, "name": "a", "prompt": "", "expected_output": "e", "files": [],
                                     "assertions": ["x"]}])
    assert ev.main(["--validate", "--evals-dir", str(evals), "--plugin-dir", str(tmp_path / "없음")]) == 1
    assert "prompt" in capsys.readouterr().out


def test_validate_reports_non_integer_ids_without_crashing(tmp_path):
    trigger = [{"id": [1], "query": "a", "expected_skill": None}, {"id": [1], "query": "b", "expected_skill": None},
               {"id": 2, "query": "c", "expected_skill": None}]
    problems = ev._trigger_problems(trigger, {"rubric"})
    assert sum("id는 정수여야 함" in p for p in problems) == 2
    case = {"id": [1], "name": "n", "prompt": "p", "expected_output": "", "files": [], "assertions": ["a"]}
    data = {"skill_name": "rubric", "evals": [case, dict(case)]}
    problems = ev._skill_file_problems(tmp_path / "rubric.json", data)
    assert sum("id는 정수여야 함" in p for p in problems) == 2


def test_group_label_for_non_record_lists():
    result = {"status": "done", "expected": "rubric/worksheet", "outcome": "correct"}
    assert "공통(rubric/worksheet)" in ev.summarize_trigger([result])["per_skill"]


def stopped_stream(*events):
    state = ev.StreamState()
    for event in events:
        ev.consume_event(state, event)
    return ev.finish_output(state, True, 1.0, 600)


def test_stopped_run_has_no_final_answer():
    out = stopped_stream(TOOL_TURN, FINAL_TURN)          # result 이벤트 없이 멈춤
    assert out.ok and out.stopped and out.final_text == ""
    assert ev.final_answer(out) == ""


def test_judge_is_told_the_run_was_stopped():
    out = stopped_stream(TOOL_TURN, FINAL_TURN)
    case = {"prompt": "p", "expected_output": "e", "assertions": ["x"]}
    prompt = ev.build_judge_prompt(case, out, [])
    assert "[응답]\n중단된 실행(최종 답변 없음)\n" in prompt and "책임 안내" not in prompt


def test_stopped_count_is_in_summary_and_markdown(tmp_path):
    def fake(req):
        if req.kind == "judge":
            return ok(result_text='[{"index":1,"pass":false,"reason":"없음"}]')
        return ev.RunOutput(ok=True, stopped=True, assistant_text="진행 문장")

    case = {"skill": "rubric", "id": 1, "name": "n", "prompt": "p", "expected_output": "e", "assertions": ["x"]}
    result = ev.run_output_case(case, 1, make_cfg(tmp_path, fake))
    assert result["stopped"] is True and result["response"] == ""
    summary = ev.summarize_outputs([result])
    assert summary["rubric"]["stopped"] == 1
    assert any("중단" in line and "1" in line for line in ev.output_markdown(summary, [result]))


class FakeProcess:
    """claude 대신 stderr 받는 곳만 기록하는 가짜 프로세스."""

    def __init__(self, command, **kwargs):
        FakeProcess.kwargs = kwargs
        if hasattr(kwargs["stderr"], "write"):
            kwargs["stderr"].write("가짜 오류 출력\n".encode("utf-8"))
        self.stdin = type("Sink", (), {"write": lambda self, data: None, "close": lambda self: None})()
        self.stdout = iter([b'{"type":"result","is_error":false,"result":"\xeb\x81\x9d"}\n'])

    def kill(self):
        pass

    def wait(self):
        pass


def run_fake_claude(monkeypatch, req):
    monkeypatch.setattr(ev.subprocess, "Popen", FakeProcess)
    return ev.run_claude(req)


def test_run_claude_keeps_stderr_in_a_per_run_file(tmp_path, monkeypatch):
    path = tmp_path / "결과" / "stderr" / "output-rubric-1-r1.stderr.txt"
    req = ev.RunRequest("p", tmp_path / "w", "output", stderr_path=path)
    run_fake_claude(monkeypatch, req)
    run_fake_claude(monkeypatch, req)        # 다시 시도하면 같은 파일에 덧붙는다
    text = path.read_text(encoding="utf-8")
    assert text.count("가짜 오류 출력") == 2 and text.count("실행 시작") == 2
    assert FakeProcess.kwargs["stderr"] is not ev.subprocess.DEVNULL


def test_run_claude_discards_stderr_without_a_path(tmp_path, monkeypatch):
    run_fake_claude(monkeypatch, ev.RunRequest("p", tmp_path / "w", "output"))
    assert FakeProcess.kwargs["stderr"] is ev.subprocess.DEVNULL


def test_cases_name_their_stderr_files(tmp_path):
    seen = []

    def fake(req):
        seen.append((req.kind, req.stderr_path))
        if req.kind == "judge":
            return ok(result_text='[{"index":1,"pass":true,"reason":"좋음"}]')
        return ok(assistant_text="답")

    cfg = ev.Config(executor=fake, plugin_dir=tmp_path, work_root=tmp_path / "work", stderr_dir=tmp_path / "stderr",
                    hwpx_checker=lambda p: {"ok": True, "message": "정상"})
    case = {"skill": "rubric", "id": 3, "name": "n", "prompt": "p", "expected_output": "e", "assertions": ["x"]}
    ev.run_output_case(case, 2, cfg)
    ev.run_trigger_case({"id": 7, "query": "q", "expected_skill": None}, cfg)
    names = {kind: path.name for kind, path in seen}
    assert names["output"] == "output-rubric-3-r2.stderr.txt"
    assert names["judge"] == "judge-rubric-3.stderr.txt"
    assert names["trigger"] == "trigger-q7.stderr.txt"
