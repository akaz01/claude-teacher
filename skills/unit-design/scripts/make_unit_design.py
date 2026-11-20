"""단원 설계서(백워드 3단계 + 개념기반 요소) 한글(hwpx) 만들기.

내용만 JSON으로 받아 공용 생성기(make_hwpx.py)의 표·도형으로 바꾼다. 모양은 앱 디자인 캔버스와 같다
(make_unit_design_layout.py: 진한 청록 머리 띠, 마디 띠 Ⅰ~Ⅳ, GRASPS 칸, 평가 배치 줄, 평가 칩).
만들 때마다 교육과정-수업-평가 일체화를 점검해 경고로 알린다(alignment_warnings).

입력 JSON (자세한 예: references/unit-design-input.md):
{
  "info": {"subject": "한국사1", "grade": "고1", "unit": "단원명", "periods": 8, "curriculum": "2022 개정",
           "date": "2026-11-20", "semester_periods": "48차시 (3학점 × 16회)"},       # date는 YYYY-MM-DD
  "stage1": {"standards": [{"code": "[10한사1-01-03]", "text": "…", "know": "…", "do": "…"}],
             "core_ideas": ["…"], "content_elements": {"지식⋅이해": ["…"], "과정⋅기능": ["…"], "가치⋅태도": ["…"]},
             "concepts": ["…"], "understandings": ["…"], "essential_questions": ["…"],
             "questions": {"사실": ["…"], "개념": ["…"], "논쟁": ["…"]}},
  "stage2": {"grasps": {"goal": "…", "role": "…", "audience": "…", "situation": "…", "product": "…", "standards": "…"},
             "criteria": [{"element": "평가 요소", "look": "보는 것"}],                   # 선택
             "evidence": [{"periods": "3~4", "kind": "진단|형성|수행|지필", "method": "…", "focus": "…",
                           "standards": ["[코드]"]}]},
  "stage3": [{"periods": "1", "goal": "…", "activities": "◉ …\\n○ …", "assessment": "진단", "standards": ["[코드]"]}],
  "next_steps": [{"skill": "지도안", "request": "지도안: 3차시 써 줘", "what": "넘길 내용"}]
}

사용법:
    python make_unit_design.py 단원설계.json 단원설계.hwpx
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
for folder in (SCRIPTS, SCRIPTS.parents[2] / "shared" / "scripts"):      # 스킬 묶음 안, 저장소 안
    if (folder / "make_hwpx.py").exists():
        sys.path.insert(0, str(folder))
        break
from make_hwpx import build_hwpx  # noqa: E402
from make_hwpx_save import file_error_message  # noqa: E402
from make_unit_design_layout import (  # noqa: E402
    BAND_CHIP_MAX_W, CHECK, CHIP_MAX_W, GRASPS_PARTS, LABEL_MAX_W, LABEL_PAD, NEXT_NOTE, band_blocks,
    codes_of as _codes, concept_row, criteria_table, evidence_table, flow_table, footer_blocks, grasps_cards,
    idea_boxes, info_strip, key_boxes, kind_of as _kind, next_table, note_line, question_box, run_note, section_strip,
    standards_table, sub_title, text_of as _text, timeline_box, too_long)

ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
PERIOD = re.compile(r"^\s*(\d+)\s*(?:차시)?\s*(?:[~∼\-–]\s*(\d+)\s*(?:차시)?)?\s*$")   # "3", "3~4", "3차시", "3~4차시"
KINDS = ("진단", "형성", "수행", "지필")
MAX_PERIOD = 200      # 한 학기 수업(고교 최대 기본 학점 × 16회)을 넉넉히 넘는 값
TIMELINE_MAX = 36     # 평가 배치 줄(차시 동그라미)을 그리는 차시 수 한도 (넘으면 평가 배치 표만)
OFFICIAL_DATE_WARNING = "공문서 표기가 아님"     # make_hwpx_lint: YYYY-MM-DD를 쓰기로 한 문서라 거른다


class DesignError(ValueError):
    """입력이 단원 설계서 형식에 맞지 않을 때."""


# ---------------------------------------------------------------- 입력 읽기

def periods_of(label) -> set[int]:
    """'3', '3~4', '5, 6' → 차시 번호 집합. 숫자가 아니면(정기시험 등) 빈 집합.
    차시 번호가 MAX_PERIOD를 넘으면 오류다(큰 범위로 메모리를 다 쓰지 않게)."""
    found: set[int] = set()
    for part in re.split(r"[,，]", _text(label)):
        match = PERIOD.match(part)
        if match:
            first, last = int(match.group(1)), int(match.group(2) or match.group(1))
            if max(first, last) > MAX_PERIOD:
                raise DesignError(f"차시 '{part.strip()}'가 너무 큼 (한 단원은 {MAX_PERIOD}차시까지)")
            found.update(range(min(first, last), max(first, last) + 1))
    return found


def _check_date(info: dict) -> None:
    value = _text(info.get("date"))
    match = ISO_DATE.match(value)
    try:
        if not match:
            raise ValueError
        date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        raise DesignError(f"작성일 '{value}'은 YYYY-MM-DD 꼴의 있는 날짜여야 함 (예: 2026-11-20)") from None


def _require_shape(spec: dict) -> None:
    """칸마다 객체·목록인지 본다. 틀리면 칸 이름을 넣어 알린다."""
    for key in ("info", "stage1", "stage2"):
        if not isinstance(spec[key], dict):
            raise DesignError(f"'{key}'는 {{...}} 객체여야 함")
    stage1, stage2 = spec["stage1"], spec["stage2"]
    for key, value in (("stage3", spec["stage3"]), ("stage2.evidence", stage2.get("evidence") or []),
                       ("stage2.criteria", stage2.get("criteria") or []),
                       ("stage1.standards", stage1.get("standards") or []), ("next_steps", spec.get("next_steps") or [])):
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            raise DesignError(f"'{key}'는 {{...}} 객체들의 목록 [...]이어야 함")
    for key, value, example in (("stage2.grasps", stage2.get("grasps"), '{"goal": ..., "role": ...}'),
                                ("stage1.content_elements", stage1.get("content_elements"), '{"지식⋅이해": [...], ...}'),
                                ("stage1.questions", stage1.get("questions"), '{"사실": [...], "개념": [...], "논쟁": [...]}')):
        if value is not None and not isinstance(value, dict):
            raise DesignError(f"'{key}'는 {example} 꼴의 객체여야 함")


def _require(spec: dict) -> None:
    if not isinstance(spec, dict):
        raise DesignError("입력은 JSON 객체여야 함")
    for key in ("info", "stage1", "stage2", "stage3"):
        if key not in spec:
            raise DesignError(f"'{key}'가 없음 (info, stage1, stage2, stage3는 꼭 있어야 함)")
    _require_shape(spec)
    _check_date(spec["info"])
    if not spec["stage3"]:
        raise DesignError("stage3(차시별 흐름)에 차시가 하나 이상 있어야 함")
    for number, row in enumerate(spec["stage3"], 1):
        if not _text(row.get("periods")):
            raise DesignError(f"stage3의 {number}번째 행에 차시가 없음")
    if not spec["stage1"].get("standards"):
        raise DesignError("stage1에 성취기준이 하나 이상 있어야 함 (모르면 code에 '[확인 필요]')")


# ---------------------------------------------------------------- 일체화 점검

def _taught_periods(spec: dict) -> dict[str, set[int]]:
    taught: dict[str, set[int]] = {}
    for row in spec["stage3"]:
        for code in _codes(row.get("standards")):
            taught.setdefault(code, set()).update(periods_of(row.get("periods")))
    return taught


def _period_warnings(spec: dict) -> list[str]:
    total = spec["info"].get("periods")
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        return [f"차시 수가 숫자가 아님: {total!r}"]
    if total > MAX_PERIOD:
        raise DesignError(f"단원 차시 수 {total}이 너무 큼 (한 단원은 {MAX_PERIOD}차시까지)")
    unreadable = [_text(row.get("periods")) for row in spec["stage3"] if not periods_of(row.get("periods"))]
    if unreadable:
        return [f"차시를 숫자로 읽을 수 없음: {', '.join(unreadable)} (예: 3, 3~4, 3차시)"]
    covered = set().union(*(periods_of(row.get("periods")) for row in spec["stage3"]))
    expected = set(range(1, total + 1))
    if covered == expected:
        return []
    missing, extra = sorted(expected - covered), sorted(covered - expected)
    detail = ", ".join(part for part in (f"빠진 차시 {missing}" if missing else "",
                                          f"넘친 차시 {extra}" if extra else "") if part)
    return [f"차시 수 {total}과 차시 흐름표가 맞지 않음 ({detail})"]


def _timing_warnings(evidence: list[dict], taught: dict[str, set[int]]) -> list[str]:
    warnings: list[str] = []
    for item in evidence:
        when, kind = periods_of(item.get("periods")), _kind(item.get("kind"))
        if kind not in KINDS:
            warnings.append(f"평가 종류 '{_text(item.get('kind'))}'는 진단·형성·수행·지필 가운데 하나로 써야 함")
        if kind == "수행" and not when:
            warnings.append(f"수행 평가 '{_text(item.get('method'))}'에 수업 차시가 없음 (수업 시간 안에서 하도록 차시를 적기)")
        if kind == "진단" or not when:
            continue
        for code in _codes(item.get("standards")):
            if taught.get(code) and min(taught[code]) > max(when):
                warnings.append(f"{_text(item.get('periods'))}차시 {kind} 평가가 {code}를 배우기 전에 있음")
    return warnings


def _evidence_warnings(spec: dict, standards: list[str], taught: dict[str, set[int]]) -> list[str]:
    evidence = spec["stage2"].get("evidence") or []
    assessed = {code for item in evidence for code in _codes(item.get("standards"))}
    warnings = [f"성취기준 {code}: 평가 증거가 없음 (2단계 평가 배치에 넣기)" for code in standards if code not in assessed]
    if not any(_kind(item.get("kind")) == "수행" for item in evidence):
        warnings.append("2단계에 수행 평가(GRASPS 수행과제)가 없음")
    return warnings + _timing_warnings(evidence, taught) + _range_warnings(spec, evidence)


def _unit_total(spec: dict) -> int | None:
    total = spec["info"].get("periods")
    valid = isinstance(total, int) and not isinstance(total, bool) and 1 <= total <= MAX_PERIOD
    return total if valid else None


def _range_warnings(spec: dict, evidence: list[dict]) -> list[str]:
    """평가 차시가 단원 차시(1~N) 밖이면 알린다 (평가 배치 줄에는 그릴 자리가 없다)."""
    total = _unit_total(spec)
    if total is None:
        return []
    return [f"평가 '{_text(item.get('periods'))}'차시가 단원 차시(1~{total}) 밖에 있음"
            for item in evidence if any(not 1 <= n <= total for n in periods_of(item.get("periods")))]


def alignment_warnings(spec: dict) -> list[str]:
    """성취기준 → 차시 → 평가가 이어지는지 점검한 경고 목록."""
    standards = _codes(item.get("code") for item in spec["stage1"]["standards"])
    taught = _taught_periods(spec)
    warnings = [f"성취기준 {code}: 다루는 차시가 없음 (3단계 standards에 넣기)" for code in standards if code not in taught]
    evidence = spec["stage2"].get("evidence") or []
    used = set(taught) | {code for item in evidence for code in _codes(item.get("standards"))}
    warnings += [f"1단계에 없는 성취기준이 쓰임: {code}" for code in sorted(used - set(standards))]
    warnings += _evidence_warnings(spec, standards, taught)
    return warnings + _period_warnings(spec)


# ---------------------------------------------------------------- 문서 짜기 (모양은 make_unit_design_layout.py)

def _periods_label(info: dict) -> str:
    return f"{_text(info.get('periods'))}차시" if _text(info.get("periods")) else CHECK


def _timeline_data(spec: dict) -> tuple[int, dict[int, list[str]], list[tuple[str, str]]]:
    """평가 배치 줄에 쓸 값: (차시 수, 차시별 평가 종류, 차시 밖 평가(종류, 글))."""
    total = _unit_total(spec) or max((n for row in spec["stage3"] for n in periods_of(row.get("periods"))), default=0)
    marks: dict[int, list[str]] = {}
    outside: list[tuple[str, str]] = []
    for item in spec["stage2"].get("evidence") or []:
        found = periods_of(item.get("periods"))
        for number in sorted(found):
            marks.setdefault(number, []).append(_kind(item.get("kind")))
        if not found:
            label = " · ".join(part for part in (_text(item.get("periods")), _text(item.get("method"))) if part)
            outside.append((_kind(item.get("kind")), label))
    inside = {number: kinds for number, kinds in marks.items() if 1 <= number <= total}   # 밖은 경고로 알린다
    return total, inside, outside


def _shortened(field: str, text: str) -> str:
    return f"{field} '{text[:15]}…'이 길어 줄여 씀 (짧게 고쳐 주세요)"


def _chip_warnings(spec: dict) -> list[str]:
    """칩에 들어가는 글이 너비 한도를 넘어 줄여 쓴 것을 알린다."""
    info, stage1 = spec["info"], spec["stage1"]
    named = [("학년", _text(info.get("grade")), BAND_CHIP_MAX_W), ("과목", _text(info.get("subject")), BAND_CHIP_MAX_W)]
    named += [("핵심 개념", text, CHIP_MAX_W) for text in _codes(stage1.get("concepts"))]
    for key, field in (("content_elements", "내용 요소 이름"), ("questions", "탐구 질문 이름")):
        named += [(field, str(name), CHIP_MAX_W) for name in (stage1.get(key) or {})]
    return [_shortened(field, text) for field, text, max_w in named if too_long(text, max_w)]


def _timeline_blocks(spec: dict, warnings: list[str]) -> list[dict]:
    total, marks, outside = _timeline_data(spec)
    if not 1 <= total <= TIMELINE_MAX:
        if total:
            warnings.append(f"차시가 {TIMELINE_MAX}개를 넘어 평가 배치 줄은 그리지 않고 표로만 둠")
        return []
    warnings += [_shortened("차시 밖 평가", label) for _, label in outside if too_long(label, LABEL_MAX_W, LABEL_PAD)]
    return [timeline_box(total, marks, outside)]


def _stage1_blocks(stage1: dict) -> list[dict]:
    return [section_strip("Ⅰ", "바라는 결과", "1단계"), sub_title("성취기준 분석"), standards_table(stage1),
            idea_boxes(stage1), concept_row(stage1), key_boxes(stage1), question_box(stage1)]


def _stage2_blocks(spec: dict, warnings: list[str]) -> list[dict]:
    stage2 = spec["stage2"]
    grasps = stage2.get("grasps") or {}
    for _, name, key in GRASPS_PARTS:
        if not _text(grasps.get(key)):
            warnings.append(f"GRASPS {name} 칸이 비어 {CHECK}로 둠")
    blocks = [section_strip("Ⅱ", "평가 계획", "2단계"), sub_title("GRASPS 수행과제"), grasps_cards(grasps), run_note()]
    if stage2.get("criteria"):
        blocks += [sub_title("채점 기준 요약"), criteria_table(stage2["criteria"])]
    return blocks + [sub_title("평가 배치"), *_timeline_blocks(spec, warnings),
                     evidence_table(stage2.get("evidence") or [])]


def to_spec(spec: dict, warnings: list[str]) -> dict:
    """단원 설계 입력을 make_hwpx 입력으로 바꾼다. 빈칸 경고는 warnings에 더한다.

    편집 용지: A4 세로, 좌우 15mm(margins narrow: 넓은 표를 담으면서 캔버스 본문 너비에 가깝다), 위 약 10.6mm,
    아래 약 11.6mm + 꼬리말 3mm(page app: 1쪽 머리 띠는 쪽 위 끝에 붙고, 둘째 쪽부터 위아래 낭비가 적다)."""
    info = spec["info"]
    warnings += _chip_warnings(spec)
    blocks = [*band_blocks(info, _periods_label(info)), info_strip(info, _periods_label(info)),
              *_stage1_blocks(spec["stage1"]), *_stage2_blocks(spec, warnings),
              # 강제 쪽 나눔은 두지 않는다: 평가 배치 표 뒤 쪽이 거의 비게 된다. 마디 띠는 흐름표와 붙어 다닌다
              section_strip("Ⅲ", "차시별 흐름", "3단계"), flow_table(spec["stage3"]),
              section_strip("Ⅳ", "다음 단계", "다른 스킬로")]
    steps = spec.get("next_steps") or []
    if steps:
        blocks += [note_line(NEXT_NOTE), next_table(steps)]
    else:
        warnings.append("다음 단계 안내(next_steps)가 없음")
        blocks.append(note_line(f"{CHECK} 다음에 만들 것(next_steps)이 없음"))
    return {"doc_title": f"단원 설계서 - {_text(info.get('unit'))}", "page": "app", "margins": "narrow",
            "footer": footer_blocks(info), "blocks": blocks}


def build(spec: dict, out_path: Path) -> list[str]:
    """hwpx를 만들고 경고(일체화 점검, 빈칸, 생성기 경고)를 돌려준다."""
    _require(spec)
    warnings = alignment_warnings(spec)
    made = build_hwpx(to_spec(spec, warnings), Path(out_path))
    return warnings + [w for w in made if OFFICIAL_DATE_WARNING not in w]


def _run(source: Path, target: Path) -> tuple[str | None, list[str]]:
    """JSON을 읽어 만든다. (실패 문장 또는 None, 경고 목록). 읽기와 쓰기 오류를 나누어 알린다."""
    try:
        spec = json.loads(source.read_text(encoding="utf-8-sig"))
    except OSError as error:
        return f"입력 파일을 읽지 못함 - {file_error_message(error)}", []
    except ValueError as error:          # JSON 문법, 글자 인코딩
        return f"입력 오류: JSON을 읽지 못함 ({error})", []
    except RecursionError:
        return "입력 오류: JSON이 너무 깊게 겹쳐 있음", []
    try:
        return None, build(spec, target)
    except OSError as error:
        return file_error_message(error), []
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as error:   # RuntimeError: 만든 뒤 검사 실패
        return f"입력 오류: {error}", []
    except Exception as error:  # noqa: BLE001  예상 밖 입력도 추적 로그 대신 안내 문장으로
        return f"내부 오류: 예상하지 못한 입력입니다 ({type(error).__name__})", []


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    if len(args) != 2:
        sys.stdout.write("사용법: python make_unit_design.py 단원설계.json 단원설계.hwpx\n")
        return 2
    failure, warnings = _run(Path(args[0]), Path(args[1]))
    if failure:
        sys.stdout.write(f"만들지 못함: {failure}\n")
        return 1
    sys.stdout.write(f"만들었습니다: {args[1]}\n")
    sys.stdout.write("".join(f"점검: {warning}\n" for warning in warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
