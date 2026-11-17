"""교수·학습 과정안(기본 양식) 생성기 시험."""
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "scripts"))
from make_hwpx import validate_package  # noqa: E402

import make_lesson_form  # noqa: E402
from make_lesson_form import FormError, build, main  # noqa: E402

SPEC = {
    "title": "Ⅱ. 집합과 명제", "topic": "집합과 명제", "period": "1/8", "subtopic": "명제와 조건", "time": "50분",
    "goals": ["1. 명제를 구별할 수 있다.", "진리집합을 구할 수 있다."],
    "rows": [{"label": "성취기준", "text": "[10공수2-02-04] 명제와 조건의 뜻을 안다."}],
    "style": "전체 → 짝", "prep": {"teacher": "PPT", "student": "학습지"},
    "stages": [{"name": "도입", "steps": [{"content": "동기\n유발", "teacher": "◉ 발문", "student": "- 답", "time": "5'"}]},
               {"name": "전개", "steps": [{"content": "활동 1", "teacher": "◉ {{x>4}}", "time": "20'"},
                                          {"content": "활동 2", "teacher": "◉ 짝 활동", "time": "20'"}]},
               {"name": "정리", "steps": [{"content": "정리", "teacher": "◉ 한 문장", "time": "5'"}]}],
}


def build_xml(tmp_path: Path, spec: dict) -> tuple[str, str]:
    out = tmp_path / "out.hwpx"
    build(spec, out)
    assert not validate_package(out)
    with zipfile.ZipFile(out) as package:
        return package.read("Contents/section0.xml").decode("utf-8"), package.read("Contents/header.xml").decode("utf-8")


def tables(xml: str) -> list[str]:
    return re.findall(r"<hp:tbl .*?</hp:tbl>", xml, re.S)


def test_one_row_per_activity_and_merged_stage(tmp_path):
    xml, _ = build_xml(tmp_path, SPEC)
    activity = [t for t in tables(xml) if "교수" in t][0]
    assert 'rowCnt="6"' in activity                      # 머리 2행 + 활동 4행
    stage = re.search(r"<hp:t>전개</hp:t>.*?rowSpan=\"(\d+)\"", activity, re.S).group(1)
    assert stage == "2"
    assert 'treatAsChar="0"' in activity and 'vertOffset="0"' in activity    # 쪽을 넘어 나뉘는 표
    assert activity.count('header="1"') == 7             # 머리 2행이 쪽마다 되풀이


def test_info_rows_goals_and_equation(tmp_path):
    xml, _ = build_xml(tmp_path, SPEC)
    words = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", xml))
    assert "1. 명제를 구별할 수 있다." in words and "2. 진리집합을 구할 수 있다." in words
    assert "성 취" in words and "[10공수2-02-04]" in words
    assert "<hp:equation" in xml


def test_body_paragraphs_wrap_by_word_and_hang(tmp_path):
    xml, header = build_xml(tmp_path, SPEC)
    para = re.search(r'paraPrIDRef="(\d+)"[^>]*><hp:run charPrIDRef="\d+"><hp:t>◉ 발문', xml).group(1)
    shape = re.search(rf'<hh:paraPr id="{para}".*?</hh:paraPr>', header, re.S).group(0)
    assert 'breakNonLatinWord="BREAK_WORD"' in shape and 'horizontal="LEFT"' in shape
    assert '<hc:intent value="-1000"' in shape


@pytest.mark.parametrize("bad, message", [
    ({"stages": []}, "stages"),
    ({"stages": [{"name": "", "steps": [{}]}]}, "단계 이름"),
    ({"stages": [{"name": "도입", "steps": []}]}, "활동 목록"),
    ({"goals": [1]}, "학습 목표"),
])
def test_bad_input_is_refused_in_korean(tmp_path, bad, message):
    with pytest.raises(FormError, match=message):
        build({**SPEC, **bad}, tmp_path / "out.hwpx")


# ---------------------------------------------------------------- 제어 문자, BOM, 안전 저장

def test_control_characters_are_removed_not_written(tmp_path):
    spec = {**SPEC, "title": "제\u0001목", "goals": ["목\u000b표"],
            "stages": [{"name": "도\u0002입", "steps": [{"content": "가\u000c나", "teacher": "◉ 발\u0001문", "time": "5'"}]}]}
    xml, _ = build_xml(tmp_path, spec)                  # build_xml은 validate_package 통과까지 본다
    assert not re.search("[\x00-\x08\x0b\x0c\x0e-\x1f]", xml)
    words = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", xml))
    assert "제목" in words and "1. 목표" in words and "도입" in words and "발문" in words


def test_bom_json_is_read(tmp_path, capsys):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8-sig")
    out = tmp_path / "out.hwpx"
    assert main([str(source), str(out)]) == 0
    assert not validate_package(out)
    assert main([str(source), str(out)]) == 1           # 이미 있는 파일은 덮어쓰지 않는다
    assert "덮어쓰지 않음" in capsys.readouterr().out


def test_failed_check_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(make_lesson_form, "validate_package", lambda path: ["가짜 문제"])
    with pytest.raises(FormError, match="가짜 문제"):
        build(SPEC, tmp_path / "out.hwpx")
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------- 평가 계획표

EVALUATION = [
    {"element": "명제 판별", "method": "활동지",
     "levels": ["참·거짓의 근거를 들어 새 문장도 판별한다", "주어진 문장을 명제와 조건으로 가른다", "예시를 보며 명제를 하나 고른다"],
     "feedback": "참·거짓을 가를 수 있는지 묻는 질문을 짚게 한다"},
    {"element": "참여 태도", "method": "자기평가", "levels": ["자기평가 체크리스트로 확인"], "feedback": ""},
]


def eval_table(xml: str) -> str:
    found = [t for t in tables(xml) if "평가 요소" in t]
    assert len(found) == 1
    return found[0]


def test_evaluation_plan_table_is_added_below_activity_table(tmp_path):
    xml, _ = build_xml(tmp_path, {**SPEC, "evaluation": EVALUATION})
    table = eval_table(xml)
    assert xml.index(table) > xml.index([t for t in tables(xml) if "교수" in t][0])
    words = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", table))
    for word in ("평가 요소", "평가 방법", "평가 기준", "상", "중", "하", "피드백(하)", "명제 판별", "활동지",
                 "주어진 문장을 명제와 조건으로 가른다", "자기평가 체크리스트로 확인"):
        assert word in words
    assert 'rowCnt="4"' in table                         # 머리 2행 + 평가 요소 2행
    assert table.count('header="1"') == 7                # 머리행이 쪽마다 되풀이
    assert re.search(r"자기평가 체크리스트로 확인.*?colSpan=\"3\"", table, re.S)   # 한 문장은 상·중·하 칸을 합친다
    assert "[확인 필요]" in words                        # 빈 피드백은 지어내지 않고 표시


def test_evaluation_table_uses_form_borders_and_level_names(tmp_path):
    xml, _ = build_xml(tmp_path, {**SPEC, "evaluation": EVALUATION[:1], "evaluation_levels": ["잘함", "보통", "노력 요함"]})
    table = eval_table(xml)
    words = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", table))
    assert "노력 요함" in words and "피드백(노력 요함)" in words
    fills = set(re.findall(r'<hp:tc [^>]*borderFillIDRef="(\d+)"', table))
    activity = [t for t in tables(xml) if "교수" in t][0]
    assert fills <= set(re.findall(r'<hp:tc [^>]*borderFillIDRef="(\d+)"', activity))   # 활동표와 같은 선·음영


def test_control_characters_only_cell_is_marked_unknown(tmp_path):
    item = {**EVALUATION[0], "feedback": "\u0001\u000b"}
    words = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", eval_table(build_xml(tmp_path, {**SPEC, "evaluation": [item]})[0])))
    assert "[확인 필요]" in words                        # 지운 뒤 빈칸이면 빈칸으로 두지 않는다


def test_three_or_more_evaluation_rows_use_the_middle_row_frame(tmp_path):
    items = [{**EVALUATION[0], "element": f"요소{n}"} for n in range(1, 6)]
    table = eval_table(build_xml(tmp_path, {**SPEC, "evaluation": items})[0])   # build_xml이 구조 검사도 한다
    assert 'rowCnt="7"' in table                         # 머리 2행 + 평가 요소 5행
    for n in range(1, 6):
        assert f"요소{n}" in table


def test_without_evaluation_output_is_unchanged(tmp_path):
    xml, _ = build_xml(tmp_path, SPEC)
    assert len(tables(xml)) == 3
    assert "평가 요소" not in xml


@pytest.mark.parametrize("bad, message", [
    ({"evaluation": "관찰"}, "evaluation"),
    ({"evaluation": [{"element": "가", "levels": ["상", "중"]}]}, "levels"),
    ({"evaluation": [{"element": "가", "levels": ["a", "b", "c"]}], "evaluation_levels": []}, "evaluation_levels"),
])
def test_bad_evaluation_is_refused_in_korean(tmp_path, bad, message):
    with pytest.raises(FormError, match=message):
        build({**SPEC, **bad}, tmp_path / "out.hwpx")


# ---------------------------------------------------------------- 통합형 활동표 (초등)

FORM_WIDTH = 48194                                       # 양식 활동표 너비 (HWPUNIT)


def activity_table(xml: str) -> str:
    return [t for t in tables(xml) if "<hp:t>단계</hp:t>" in t][0]


def table_rows(table: str) -> list[list[str]]:
    return [re.findall(r"<hp:tc .*?</hp:tc>", row, re.S) for row in re.findall(r"<hp:tr>(.*?)</hp:tr>", table, re.S)]


def cell_words(tc: str) -> str:
    return "\n".join(re.findall(r"<hp:t>([^<]*)</hp:t>", tc))


INTEGRATED_HEAD = ["단계", "학습\n형태", "교수\n⋅학습 활동", "소요\n시간", "학습자료 및 유의점", "평가"]


def test_integrated_layout_has_six_columns_and_one_header_row(tmp_path):
    table = activity_table(build_xml(tmp_path, {**SPEC, "layout": "integrated"})[0])
    assert 'colCnt="6"' in table and 'rowCnt="5"' in table          # 머리 1행 + 활동 4행
    rows = table_rows(table)
    header = rows[0]
    assert all('header="1"' in tc for tc in header)
    assert table.count('header="1"') == 6                             # 머리행만 쪽마다 되풀이
    assert [cell_words(tc) for tc in header] == INTEGRATED_HEAD       # 단계|학습 형태|교수·학습 활동|시간|자료·유의점|평가
    assert "교사(T)" not in table and "학생(S)" not in table and "학습내용" not in table
    for row in rows:                                                  # 모든 열이 있는 행은 칸 너비 합이 양식 표 너비
        if 'colAddr="0"' in row[0]:
            assert sum(int(re.search(r'<hp:cellSz width="(\d+)"', tc).group(1)) for tc in row) == FORM_WIDTH


def test_integrated_layout_puts_teacher_and_student_in_one_cell(tmp_path):
    step = {"group": "전체", "teacher": "◉ 발문", "student": "- 답", "materials": "▣ PPT", "time": "5'", "assess": "관찰"}
    spec = {**SPEC, "layout": "integrated", "stages": [{"name": "도입", "steps": [step]}, *SPEC["stages"][1:]]}
    first_step = table_rows(activity_table(build_xml(tmp_path, spec)[0]))[1]
    assert [cell_words(tc) for tc in first_step] == ["도입", "전체", "◉ 발문\n- 답", "5'", "▣ PPT", "관찰"]


def test_integrated_activity_text_keeps_its_own_order(tmp_path):
    step = {"content": "탐구", "activity": "◉ 활동\n○ “무엇이 보이나요?”\n- 그림자\n○ 되묻기\n- 해", "time": "40'",
            "teacher": "쓰이지 않음", "student": "쓰이지 않음"}
    spec = {**SPEC, "layout": "integrated", "stages": [{"name": "전개", "steps": [step]}]}
    words = cell_words(table_rows(activity_table(build_xml(tmp_path, spec)[0]))[1][2])
    assert words.split("\n") == ["◉ 탐구", "◉ 활동", "○ “무엇이 보이나요?”", "- 그림자", "○ 되묻기", "- 해"]
    assert "쓰이지 않음" not in words


def test_integrated_content_goes_on_the_first_activity_line(tmp_path):
    step = {"content": "동기\n유발", "teacher": "◉ 발문", "student": "- 답", "time": "5'"}
    spec = {**SPEC, "layout": "integrated", "stages": [{"name": "도입", "steps": [step]}]}
    words = cell_words(table_rows(activity_table(build_xml(tmp_path, spec)[0]))[1][2])
    assert words.split("\n") == ["◉ 동기 유발", "◉ 발문", "- 답"]


def test_integrated_without_content_is_unchanged(tmp_path):
    step = {"activity": "◉ 활동", "time": "5'"}
    spec = {**SPEC, "layout": "integrated", "stages": [{"name": "도입", "steps": [step]}]}
    words = cell_words(table_rows(activity_table(build_xml(tmp_path, spec)[0]))[1][2])
    assert words == "◉ 활동"


def test_split_layout_still_keeps_content_in_its_own_cell(tmp_path):
    step = {"content": "동기", "teacher": "◉ 발문", "student": "- 답", "time": "5'"}
    spec = {**SPEC, "stages": [{"name": "도입", "steps": [step]}]}
    row = table_rows(activity_table(build_xml(tmp_path, spec)[0]))[2]
    assert cell_words(row[1]) == "동기" and cell_words(row[2]) == "◉ 발문"


def test_integrated_layout_keeps_form_borders_and_evaluation_table(tmp_path):
    xml, _ = build_xml(tmp_path, {**SPEC, "layout": "integrated", "evaluation": EVALUATION})
    table = activity_table(xml)
    with zipfile.ZipFile(make_lesson_form.FORM) as form:
        form_table = activity_table(form.read("Contents/section0.xml").decode("utf-8"))
    fill = r'<hp:tc [^>]*borderFillIDRef="(\d+)"'
    assert set(re.findall(fill, table)) <= set(re.findall(fill, form_table))      # 양식 활동표의 선·음영만 씀
    head_fills = [re.search(fill, tc).group(1) for tc in table_rows(table)[0]]
    form_head = {re.search(r'colAddr="(\d+)" rowAddr="0"', tc).group(1): re.search(fill, tc).group(1)
                 for tc in table_rows(form_table)[0]}
    # 머리칸 음영·굵은 위선 그대로. 시간 칸은 안쪽 칸 선, 끝 칸(평가)은 오른쪽 굵은 바깥선
    assert head_fills == [form_head[col] for col in ("0", "1", "2", "4", "4", "5")]
    body_fills = [re.search(fill, tc).group(1) for tc in table_rows(table)[1]]
    form_body = [re.search(fill, tc).group(1) for tc in table_rows(form_table)[2]]
    assert body_fills == [form_body[i] for i in (0, 1, 2, 4, 4, 5)]
    assert xml.index(eval_table(xml)) > xml.index(table)                         # 평가 계획표도 붙는다


def test_split_layout_is_the_default_and_unchanged(tmp_path):
    default = build_xml(tmp_path, SPEC)
    (tmp_path / "split").mkdir()
    named = build_xml(tmp_path / "split", {**SPEC, "layout": "split"})
    assert default == named
    assert 'colCnt="6"' in activity_table(default[0]) and "교사(T)" in default[0]


def test_unknown_layout_is_refused_in_korean(tmp_path):
    with pytest.raises(FormError, match="layout"):
        build({**SPEC, "layout": "mixed"}, tmp_path / "out.hwpx")


# ---------------------------------------------------------------- SKILL.md 안내와 맞는가

SKILL = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")


def test_skill_example_of_evaluation_builds(tmp_path):
    line = next(text for text in SKILL.splitlines() if text.startswith("- `evaluation`"))
    example = json.loads(re.search(r"예: `(\{.*?\})`", line).group(1))
    xml, _ = build_xml(tmp_path, {**SPEC, "evaluation": [example]})
    assert "피드백(하)" in "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", eval_table(xml)))


def test_skill_layout_values_exist_and_elementary_uses_integrated():
    section = SKILL[SKILL.index("## 9. 파일 만들기"):SKILL.index("## 10. 출력 순서")]
    named = set(re.findall(r'"layout": "(\w+)"', section))
    assert named and named <= set(make_lesson_form.LAYOUTS)
    elementary = next(line for line in section.splitlines() if line.startswith("- 초등"))
    assert '"layout": "integrated"' in elementary
    assert all(f"`{key}`" in elementary for key in make_lesson_form.INTEGRATED_KEYS)


def test_lookup_and_profile_requests_branch_before_lesson_questions():
    section = SKILL[SKILL.index("## 1. 정보 확인"):SKILL.index("> 지도안을 만들기 위해 알려 주세요.")]
    assert "references/curriculum-lookup.md" in section and "references/teacher-profile.md" in section
    assert "지도안 질문을 하지 않는다" in section
