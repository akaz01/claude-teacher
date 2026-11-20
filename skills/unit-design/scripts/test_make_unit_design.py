"""단원 설계서 생성기 시험."""
import copy
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "scripts"))
from make_hwpx import validate_package  # noqa: E402

from make_unit_design import DesignError, alignment_warnings, build, main  # noqa: E402

A, B = "[10한사1-01-03]", "[10한사1-01-04]"
UNIT = {
    "info": {"subject": "한국사1", "grade": "고1", "unit": "Ⅰ. 근대 이전 한국사의 이해 – 조선의 성립과 변화",
             "periods": 4, "curriculum": "2022 개정", "date": "2026-11-20", "semester_periods": "48차시 (3학점 × 16회)"},
    "stage1": {
        "standards": [{"code": A, "text": "조선 시대 통치 체제의 정비를 이해한다.", "know": "통치 체제", "do": "설명한다"},
                      {"code": B, "text": "조선 후기 사회 변동을 탐구한다.", "know": "사회 변동", "do": "탐구한다"}],
        "core_ideas": ["한국사는 국제 질서의 변동과 맞물려 변화하였다."],
        "content_elements": {"지식⋅이해": ["조선의 통치 체제"], "과정⋅기능": ["사료 분석하기"], "가치⋅태도": ["다양한 관점 존중"]},
        "concepts": ["제도", "변화"],
        "understandings": ["통치 제도는 사회 구조가 바뀌면 그에 맞게 다시 짜인다."],
        "essential_questions": ["제도는 왜 바뀌는가?"],
        "questions": {"사실": ["조선은 어떤 기구로 나라를 다스렸는가?"], "개념": ["제도와 사회 변화는 어떻게 맞물리는가?"],
                      "논쟁": ["영조와 정조의 개혁은 성공했다고 볼 수 있는가?"]},
    },
    "stage2": {
        "grasps": {"goal": "조선 후기 개혁안을 평가해 권고한다.", "role": "실록 편찬 연구원", "audience": "다른 학급 학생",
                   "situation": "박물관 특별전 해설 준비", "product": "사료를 인용한 해설문", "standards": "사료 근거, 시대 맥락, 다관점"},
        "evidence": [
            {"periods": "1", "kind": "진단", "method": "사전 질문지", "focus": "통치 기구 선행 지식", "standards": [A]},
            {"periods": "2", "kind": "형성", "method": "출구 카드", "focus": "제도 설명", "standards": [A]},
            {"periods": "3~4", "kind": "수행", "method": "GRASPS 해설문", "focus": "사료 근거 해석", "standards": [A, B]},
            {"periods": "정기시험", "kind": "지필", "method": "서술형 1문항", "focus": "사회 변동 설명", "standards": [B]},
        ],
    },
    "stage3": [
        {"periods": "1", "goal": "통치 기구를 설명할 수 있다.", "activities": "◉ 핵심 질문 열기\n○ 과제와 채점 기준 미리 보기",
         "assessment": "진단", "standards": [A]},
        {"periods": "2", "goal": "제도 변화를 설명할 수 있다.", "activities": "◉ 사료 읽기", "assessment": "형성", "standards": [A]},
        {"periods": "3~4", "goal": "개혁을 평가할 수 있다.", "activities": "◉ 해설문 초안 → 피드백 → 수정",
         "assessment": "수행", "standards": [A, B]},
    ],
    "next_steps": [{"skill": "지도안", "request": "지도안: 3차시 써 줘", "what": "3차시 목표·활동·평가"}],
}


def section(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        return package.read("Contents/section0.xml").decode("utf-8")


def texts(xml: str) -> str:
    """보이는 글. 칸 안 줄바꿈(<hp:lineBreak/>)은 줄바꿈 글자로 읽는다."""
    return "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", xml.replace("<hp:lineBreak/>", "\n")))


def make(tmp_path: Path, spec: dict) -> tuple[str, list[str]]:
    out = tmp_path / "out.hwpx"
    warnings = build(spec, out)
    assert not validate_package(out)
    return texts(section(out)), warnings


def test_document_has_all_four_parts_in_order(tmp_path):
    body, warnings = make(tmp_path, UNIT)
    order = [body.index(word) for word in ("단원 설계서", "1단계", "2단계", "3단계", "다음 단계")]
    assert order == sorted(order)
    for word in ("영속적 이해", "핵심 질문", "논쟁", "청중", "평가 배치", "지도안: 3차시 써 줘", "2026-11-20", "48차시"):
        assert word in body
    assert warnings == []


def test_flow_section_follows_without_forced_page_break():
    """3단계를 무조건 새 쪽에서 시작하면 평가 배치 표 뒤 쪽이 거의 비므로 강제 쪽 나눔을 두지 않는다.
    마디 띠는 다음 블록(차시 흐름표)과 같은 쪽에 붙는다."""
    from make_unit_design import to_spec
    blocks = to_spec(copy.deepcopy(UNIT), [])["blocks"]
    assert {"type": "page_break"} not in blocks
    stage3 = next(i for i, b in enumerate(blocks) if "차시별 흐름" in json.dumps(b, ensure_ascii=False))
    assert blocks[stage3]["keep_with_next"] is True
    assert "학습 목표" in json.dumps(blocks[stage3 + 1], ensure_ascii=False)


def test_iso_date_is_not_reported_as_wrong(tmp_path):
    _, warnings = make(tmp_path, UNIT)
    assert not any("공문서 표기" in warning for warning in warnings)


@pytest.mark.parametrize("date", ["2026. 11. 20.", "2026-13-01", "20261120", ""])
def test_date_must_be_iso(tmp_path, date):
    spec = copy.deepcopy(UNIT)
    spec["info"]["date"] = date
    with pytest.raises(DesignError, match="YYYY-MM-DD"):
        build(spec, tmp_path / "out.hwpx")


def test_standard_codes_are_shown_in_the_flow_table(tmp_path):
    body, _ = make(tmp_path, UNIT)
    assert body.count(A) >= 3      # 1단계, 평가 배치, 차시 흐름


def test_alignment_is_clean_for_the_sample():
    assert alignment_warnings(UNIT) == []


def test_standard_never_taught_is_reported():
    spec = copy.deepcopy(UNIT)
    for row in spec["stage3"]:
        row["standards"] = [A]
    assert any(B in w and "다루는 차시가 없음" in w for w in alignment_warnings(spec))


def test_standard_never_assessed_is_reported():
    spec = copy.deepcopy(UNIT)
    for item in spec["stage2"]["evidence"]:
        item["standards"] = [A]
    assert any(B in w and "평가 증거가 없음" in w for w in alignment_warnings(spec))


def test_assessing_before_teaching_is_reported():
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["evidence"][1]["standards"] = [B]       # 2차시 형성평가인데 B는 3~4차시에 배운다
    assert any("배우기 전" in w and B in w for w in alignment_warnings(spec))


def test_unknown_code_in_flow_is_reported():
    spec = copy.deepcopy(UNIT)
    spec["stage3"][0]["standards"] = ["[10한사1-09-09]"]
    assert any("1단계에 없는 성취기준" in w for w in alignment_warnings(spec))


def test_period_count_must_match_the_flow():
    spec = copy.deepcopy(UNIT)
    spec["info"]["periods"] = 6
    assert any("차시 수" in w for w in alignment_warnings(spec))


def test_missing_performance_task_is_reported():
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["evidence"] = [e for e in spec["stage2"]["evidence"] if e["kind"] != "수행"]
    assert any("수행" in w for w in alignment_warnings(spec))


def test_empty_grasps_cell_becomes_check_needed(tmp_path):
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["grasps"]["audience"] = ""
    body, warnings = make(tmp_path, spec)
    assert "[확인 필요]" in body
    assert any("청중" in w for w in warnings)


def test_flow_rows_must_have_periods(tmp_path):
    spec = copy.deepcopy(UNIT)
    spec["stage3"][0]["periods"] = ""
    with pytest.raises(DesignError, match="차시"):
        build(spec, tmp_path / "out.hwpx")


@pytest.mark.parametrize("label", ["1~100000", "999999999", "3, 1~5000"])
def test_huge_period_ranges_are_refused_without_eating_memory(tmp_path, label):
    spec = copy.deepcopy(UNIT)
    spec["stage3"][0]["periods"] = label
    with pytest.raises(DesignError, match="너무 큼"):
        build(spec, tmp_path / "out.hwpx")


def test_huge_unit_period_count_is_refused(tmp_path):
    spec = copy.deepcopy(UNIT)
    spec["info"]["periods"] = 10 ** 9
    with pytest.raises(DesignError, match="너무 큼"):
        build(spec, tmp_path / "out.hwpx")


def test_period_labels_with_chasi_are_read():
    spec = copy.deepcopy(UNIT)
    spec["stage3"][0]["periods"], spec["stage3"][2]["periods"] = "1차시", "3~4차시"
    assert alignment_warnings(spec) == []


def test_unreadable_flow_period_is_reported_not_crashing():
    spec = copy.deepcopy(UNIT)
    spec["stage3"][2]["periods"] = "마지막 두 시간"
    warnings = alignment_warnings(spec)
    assert any("숫자로 읽을 수 없음" in w for w in warnings)


@pytest.mark.parametrize("kind", ["수행평가", "수행 평가", " 수행 "])
def test_kind_with_pyeongga_suffix_counts_as_performance(kind):
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["evidence"][2]["kind"] = kind
    assert alignment_warnings(spec) == []


def test_unknown_kind_is_reported():
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["evidence"][1]["kind"] = "관찰"
    assert any("진단·형성·수행·지필" in w for w in alignment_warnings(spec))


def test_single_code_string_is_treated_as_one_code():
    spec = copy.deepcopy(UNIT)
    spec["stage3"][0]["standards"] = A
    assert alignment_warnings(spec) == []


@pytest.mark.parametrize("key, value", [("stage2", None), ("info", []), ("next_steps", {"skill": "x"}),
                                         ("stage3", ["1차시"])])
def test_wrong_shapes_name_the_field(tmp_path, key, value):
    spec = copy.deepcopy(UNIT)
    spec[key] = value
    with pytest.raises(DesignError, match=key):
        build(spec, tmp_path / "out.hwpx")


def test_deeply_nested_json_is_a_message_not_a_traceback(tmp_path, capsys):
    source = tmp_path / "deep.json"
    source.write_text("[" * 100000 + "]" * 100000, encoding="utf-8")
    assert main([str(source), str(tmp_path / "unit.hwpx")]) == 1
    assert "입력 오류" in capsys.readouterr().out


def test_missing_periods_value_becomes_check_needed(tmp_path):
    spec = copy.deepcopy(UNIT)
    del spec["info"]["periods"]
    body, _ = make(tmp_path, spec)
    assert "None차시" not in body


def test_missing_stage_is_an_error(tmp_path):
    spec = copy.deepcopy(UNIT)
    del spec["stage2"]
    with pytest.raises(DesignError, match="stage2"):
        build(spec, tmp_path / "out.hwpx")


def test_cli_reports_warnings_and_success(tmp_path, capsys):
    source = tmp_path / "unit.json"
    spec = copy.deepcopy(UNIT)
    spec["info"]["periods"] = 6
    source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    assert main([str(source), str(tmp_path / "unit.hwpx")]) == 0
    out = capsys.readouterr().out
    assert "만들었습니다" in out and "차시 수" in out


def test_cli_reports_input_errors(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text("{", encoding="utf-8")
    assert main([str(source), str(tmp_path / "unit.hwpx")]) == 1
    assert "입력 오류" in capsys.readouterr().out


# ---------------------------------------------------------------- 모양 (앱 디자인 캔버스와 같은 디자인)

from make_unit_design import to_spec  # noqa: E402
from make_unit_design_layout import CREAM, DEEP, GOLD, MINT_LINE, TEAL, TINT, WHITE, kind_chip  # noqa: E402


def shapes_in(node):
    """명세 속 모든 도형(칩·글자 칸·동그라미)."""
    if isinstance(node, dict):
        if "shape" in node:
            yield node
        for value in node.values():
            yield from shapes_in(value)
    elif isinstance(node, list):
        for value in node:
            yield from shapes_in(value)


def test_header_band_is_deep_teal_gradient_across_the_page_top(tmp_path):
    band = to_spec(copy.deepcopy(UNIT), [])["blocks"][0]
    assert (band["type"], band["fill"], band["fill_to"], band["w"]) == ("shape", DEEP, TEAL, 794)
    assert band["paper"] == {"x": 0, "y": 0}
    out = tmp_path / "out.hwpx"
    build(copy.deepcopy(UNIT), out)
    assert DEEP in section(out) and TEAL in section(out)


def test_four_section_strips_in_order():
    blocks = to_spec(copy.deepcopy(UNIT), [])["blocks"]
    marks = [b["rows"][0][0]["text"] for b in blocks
             if b.get("type") == "table" and b["rows"][0][0].get("fill") == TEAL and b["widths"][0] == 40]
    assert marks == ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ"]


def test_grasps_has_six_letter_cells():
    letters = [s["text"] for s in shapes_in(to_spec(copy.deepcopy(UNIT), [])["blocks"])
               if s.get("fill") == DEEP and s.get("size") == 15]
    assert "".join(letters) == "GRASPS"


def test_kind_chips_differ_in_black_and_white():
    looks = {kind: (kind_chip(kind)["fill"], kind_chip(kind)["color"], kind_chip(kind).get("line"))
             for kind in ("진단", "형성", "수행", "지필")}
    assert looks == {"진단": (WHITE, DEEP, DEEP), "형성": (TINT, DEEP, MINT_LINE), "수행": (DEEP, WHITE, None),
                     "지필": (CREAM, GOLD, "#E6C383")}


def test_timeline_marks_each_period_and_lists_outside_exams():
    shapes = list(shapes_in(to_spec(copy.deepcopy(UNIT), [])["blocks"]))
    circles = [s for s in shapes if s["shape"] == "ellipse"]
    assert [c["text"] for c in circles] == ["1", "2", "3", "4"]
    assert all(c["fill"] == DEEP for c in circles)          # 네 차시 모두 평가가 있다
    assert any(s.get("text") == "정기시험 · 서술형 1문항" for s in shapes)


def test_boxes_stay_whole_and_long_tables_repeat_header():
    blocks = to_spec(copy.deepcopy(UNIT), [])["blocks"]
    tables = [b for b in blocks if b.get("type") == "table" and "paper" not in b]
    headed = [b for b in tables if b.get("header")]
    assert headed and all(not b["keep_together"] for b in headed)           # 성취기준·평가·차시 흐름 표
    assert all(b["keep_together"] for b in tables if not b.get("header"))   # 상자들


def test_page_is_a4_portrait_with_15mm_sides(tmp_path):
    spec = to_spec(copy.deepcopy(UNIT), [])
    assert (spec["page"], spec["margins"]) == ("app", "narrow")
    out = tmp_path / "out.hwpx"
    build(copy.deepcopy(UNIT), out)
    assert 'left="4252" right="4252"' in section(out) and 'landscape="WIDELY"' in section(out)


def test_many_periods_skip_the_timeline_with_a_note():
    spec = copy.deepcopy(UNIT)
    spec["info"]["periods"] = 40
    warnings: list[str] = []
    blocks = to_spec(spec, warnings)["blocks"]
    assert not any(s["shape"] == "ellipse" for s in shapes_in(blocks))
    assert any("평가 배치 줄" in w for w in warnings)


def test_headed_tables_split_by_rows_at_page_end():
    """머리 행 있는 표는 짧아도 쪽 끝에서 행 단위로 나뉜다 (통째로 넘어가 앞 쪽 아래가 비지 않게)."""
    blocks = to_spec(copy.deepcopy(UNIT), [])["blocks"]
    headed = [b for b in blocks if b.get("type") == "table" and b.get("header")]
    assert headed and all(b.get("split_rows") for b in headed)


@pytest.mark.parametrize("key, value", [("stage2.criteria", ["요소"]), ("stage2.criteria", {"element": "x"}),
                                         ("stage2.grasps", ["x"]), ("stage1.content_elements", ["조선의 통치 체제"]),
                                         ("stage1.questions", ["질문"])])
def test_wrong_inner_shapes_name_the_field(tmp_path, key, value):
    spec = copy.deepcopy(UNIT)
    part, field = key.split(".")
    spec[part][field] = value
    with pytest.raises(DesignError, match=re.escape(key)):
        build(spec, tmp_path / "out.hwpx")


@pytest.mark.parametrize("path", [("stage2", "evidence"), (None, "next_steps")])
def test_null_lists_mean_none(tmp_path, path):
    spec = copy.deepcopy(UNIT)
    (spec[path[0]] if path[0] else spec)[path[1]] = None
    _, warnings = make(tmp_path, spec)
    assert warnings


def test_many_concepts_wrap_inside_one_cell(tmp_path):
    from make_unit_design_layout import concept_row
    concepts = [f"개념{n:02d}다섯" for n in range(30)]
    row = concept_row({"concepts": concepts})
    assert len(row["widths"]) == 2
    assert [s["text"] for s in shapes_in(row)] == concepts
    spec = copy.deepcopy(UNIT)
    spec["stage1"]["concepts"] = concepts
    body, _ = make(tmp_path, spec)
    assert "개념29다섯" in body


def test_long_chip_names_are_shortened_with_a_warning(tmp_path):
    spec = copy.deepcopy(UNIT)
    spec["stage1"]["content_elements"] = {"가" * 40: ["내용"]}
    spec["stage1"]["concepts"] = ["나" * 80]
    spec["info"]["subject"] = "다" * 80
    spec["stage2"]["evidence"].append({"periods": "정기시험", "kind": "지필", "method": "라" * 120, "standards": A})
    _, warnings = make(tmp_path, spec)
    assert sum("길어 줄여" in w for w in warnings) == 4


@pytest.mark.parametrize("label", ["0", "9", "3~9"])
def test_evidence_outside_unit_periods_is_reported(label):
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["evidence"].append({"periods": label, "kind": "형성", "standards": A})
    assert any("단원 차시" in w and "밖" in w for w in alignment_warnings(spec))


def test_evidence_outside_unit_periods_keeps_the_timeline():
    spec = copy.deepcopy(UNIT)
    spec["stage2"]["evidence"].append({"periods": "50", "kind": "형성", "standards": A})
    circles = [s for s in shapes_in(to_spec(spec, [])["blocks"]) if s["shape"] == "ellipse"]
    assert [c["text"] for c in circles] == ["1", "2", "3", "4"]


def test_long_question_names_widen_the_label_column():
    from make_unit_design_layout import question_box
    box = question_box({"questions": {"사실적 질문": ["a"], "개념적 질문": ["b"], "논쟁적 질문": ["c"]}})
    chips = list(shapes_in(box))
    assert box["widths"][0] >= max(c["w"] for c in chips) + 12
    assert chips[2]["fill"] == DEEP                     # '논쟁적 질문'도 논쟁 색


def test_no_shortened_warning_when_timeline_is_not_drawn():
    spec = copy.deepcopy(UNIT)
    spec["info"]["periods"] = 40
    spec["stage2"]["evidence"].append({"periods": "정기시험", "kind": "지필", "method": "라" * 120, "standards": A})
    warnings: list[str] = []
    to_spec(spec, warnings)
    assert not any("차시 밖 평가" in w for w in warnings)


def test_timeline_rows_are_balanced():
    from make_unit_design_layout import timeline_box
    box = timeline_box(12, {1: ["진단"]}, [])
    assert len(box["widths"]) == 2 + 3 * 6          # 9 + 3이 아니라 6 + 6
    assert sum(1 for s in shapes_in(box) if s["shape"] == "ellipse") == 12
