"""기본 양식(학교 교과진도평가계획) 채우기 시험: 1·2학기 양식, 진도표 두 모양, 가로 채점 기준, Ⅺ 성취수준, 양식 파일."""
import copy
import re
import sys
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "shared" / "scripts"))
sys.path.insert(0, str(HERE))
from test_make_course_plan import A, B, C, D, ELEMENTARY, HIGH, PEN, changed, make  # noqa: E402

from make_course_plan import CoursePlanError  # noqa: E402
from make_course_plan_check import plan_warnings  # noqa: E402
from make_course_plan_form import DEFAULT_FORM  # noqa: E402
from test_make_course_plan import TEACHING_FORM  # noqa: E402
from make_course_plan_input import read_plan  # noqa: E402

SECOND = changed(changed(HIGH, "info.semester", 2), "calendar",
                 {"start": "2026-08-17", "end": "2026-09-25", "group": 2,
                  "no_class": [{"date": "2026-09-24", "label": "추석 연휴"}],
                  "events": [{"date": "2026-08-17", "label": "개학식"}]})
SECOND = changed(changed(SECOND, "evaluation.kinds.0.timing", "9월 4주"), "evaluation.kinds.1.timing", "9월 1주")
SECOND = changed(SECOND, "evaluation.tasks.0.timing", "9월 1주")


def unit(code: str) -> dict:
    return {"code": code, "text": f"{code} 원문", "levels": {grade: f"{code} {grade} 수준" for grade in "ABCDE"}}


LEVELS = {"units": [{"name": "통합적 관점", "standards": [unit(A), unit(B)]},
                    {"name": "행복과 문화", "standards": [unit(C), unit(D)]}],
          "semester": {grade: [f"학기 {grade} 첫 줄", f"학기 {grade} 둘째 줄"] for grade in "ABCDE"},
          "minimum": ["최소 성취수준 진술"]}
WITH_LEVELS = changed(HIGH, "evaluation.achievement_levels", LEVELS)


def cell_with(xml: str, text: str) -> str:
    return next(tc for tc in re.findall(r"<hp:tc .*?</hp:tc>", xml, re.S) if text in tc)


# ---------------------------------------------------------------- 1·2학기 양식

def test_first_semester_also_uses_the_five_column_default_form(tmp_path):
    body, warnings, _ = make(tmp_path, HIGH)
    assert "2026학년도 1학기 <통합사회1>" in body and "시수/누계" in body and "수업 방법 및" not in body
    assert any("수업 방법·주안점 칸이 없어 progress의 methods, focus는 넣지 않음" in w for w in warnings)


def test_a_given_form_with_a_teaching_column_is_filled(tmp_path):
    body, warnings, _ = make(tmp_path, HIGH, form=TEACHING_FORM)
    assert "수업 방법 및 수업·평가 연계의 주안점" in body and "시수/누계" not in body
    assert not any("수업 방법·주안점 칸이 없어" in w for w in warnings)


def test_a_form_of_another_shape_is_a_clear_error(tmp_path):
    other = tmp_path / "other.hwpx"
    other.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="hwpx 파일이 아님"):
        make(tmp_path, HIGH, form=other)
    with pytest.raises(ValueError, match="초등은 학교 양식"):
        make(tmp_path, ELEMENTARY, form=DEFAULT_FORM)


def test_second_semester_uses_the_five_column_form(tmp_path):
    body, warnings, _ = make(tmp_path, SECOND)
    assert "2026학년도 2학기 <통합사회1>" in body and "시수/누계" in body and "수업 방법 및" not in body
    assert "8.17.~8.28.\n8/8" in body                         # 시기 | 시수/누계 (2주 묶음)
    assert "9.14.~9.25.\n(1)\n7/23" in body                   # 추석 연휴 하루 공제
    assert any("수업 방법·주안점 칸이 없어 progress의 methods, focus는 넣지 않음" in w for w in warnings)


def test_long_periods_break_after_the_tilde(tmp_path):
    spec = changed(changed(SECOND, "calendar.start", "2026-10-05"), "calendar.end", "2026-11-13")
    spec = changed(spec, "calendar.no_class", [])
    body, _, _ = make(tmp_path, spec)
    assert "10.5.~\n10.16." in body and "10.19.~\n10.30." in body


def test_events_are_in_date_order_and_holidays_use_the_red_character(tmp_path):
    _, _, xml = make(tmp_path, HIGH)
    holiday = re.search(r'charPrIDRef="(\d+)"><hp:t>3\.2\. 대체공휴일', xml).group(1)
    event = re.search(r'charPrIDRef="(\d+)"><hp:t>3\.3\. 개학식', xml).group(1)
    assert holiday != event and xml.index("3.2. 대체공휴일") < xml.index("3.3. 개학식")


@pytest.mark.parametrize("semester", [1, 2])
def test_every_list_part_has_exactly_the_input_items(tmp_path, semester):
    """양식의 원래 항목(특수 공백이 든 '바.' 문단 등)이 남지 않고 입력 항목만 있다."""
    spec = HIGH if semester == 1 else SECOND
    body, _, _ = make(tmp_path, spec)
    direction = body[body.index("1. 평가의 기본 방향"):body.index("2. 평가의 방침")]
    assert re.findall(r"^\s*([가-하])\. ", direction, re.M) == ["가"]
    policy = body[body.index("2. 평가의 방침"):body.index("평가의 종류와 방법")]
    assert re.findall(r"^\s*([가-하])\. ", policy, re.M) == ["가", "나"]


def test_school_sample_text_does_not_remain(tmp_path):
    for spec in (HIGH, SECOND):
        body, _, xml = make(tmp_path, spec, f"s{spec['info']['semester']}.hwpx")
        for word in ("수학자", "공통수학", "방정식과 부등식", "세종", "구글 클래스룸", "도형의 방정식"):
            assert word not in body
        ids = re.findall(r'<hp:tbl id="(\d+)"', xml)
        assert len(ids) == len(set(ids))                     # 복제한 표의 id가 겹치지 않음
        assert "linesegarray" not in xml


# ---------------------------------------------------------------- Ⅳ, Ⅵ

def test_many_kinds_widen_the_table_without_breaking_widths(tmp_path):
    spec = copy.deepcopy(HIGH)
    exam, task = spec["evaluation"]["kinds"]
    spec["evaluation"]["kinds"] = ([{**exam, "name": f"{n}회 정기시험", "ratio": 10, "essay_ratio": 2} for n in (1, 2, 3)]
                                   + [{**task, "name": f"과제{n}", "ratio": 10 + (n == 1) * 30, "essay_ratio": 5}
                                      for n in (1, 2, 3)])
    body, _, xml = make(tmp_path, spec)                       # make가 칸 너비 합을 검사한다
    assert all(f"{n}회 정기시험" in body for n in (1, 2, 3)) and "정기시험(30%)" in body
    assert 'colCnt="9"' in xml


def test_horizontal_rubric_merges_the_last_level_of_a_shorter_element(tmp_path):
    levels = [{"text": f"{s}점 기준", "score": s} for s in (4, 3, 2, 1)]
    elements = [{"name": "자료 선정", "points": 4, "levels": levels},
                {"name": "정리", "points": 6, "levels": [{"text": "정리 잘함", "score": 6}, {"text": "정리 미흡", "score": 3}]}]
    spec = changed(SECOND, "evaluation.tasks.0.areas", [{"area": "보고서", "points": 10, "elements": elements}])
    body, _, xml = make(tmp_path, spec)
    assert 'colSpan="3"' in cell_with(xml, "정리 미흡")           # 수준 4열 가운데 둘째 수준이 나머지 세 열을 합침
    assert "4\n3\n2\n1" in body and "10\n9\n8\n7\n6\n5\n4" in body


def test_rubric_without_notes_drops_the_notes_rows(tmp_path):
    body, _, _ = make(tmp_path, changed(HIGH, "evaluation.tasks.0.notes", []))
    assert "학생 유의사항" not in body


# ---------------------------------------------------------------- Ⅺ 성취기준 및 성취수준

def test_achievement_levels_fill_part_eleven(tmp_path):
    body, warnings, _ = make(tmp_path, WITH_LEVELS)
    assert "(1) 통합적 관점" in body and "(2) 행복과 문화" in body
    assert f"{A} {A} 원문\nA\n{A} A 수준" in body
    assert re.search(r"[⦁●]\s?학기 A 첫 줄\n[⦁●]\s?학기 A 둘째 줄", body)
    assert "최소\n성취\n수준" in body and "[작성 필요]" not in body
    assert not any("성취수준" in w for w in warnings)


def test_missing_levels_are_marked_and_reported(tmp_path):
    body, warnings, _ = make(tmp_path, HIGH)
    assert "가. 성취기준별 성취수준\n[작성 필요]" in body
    assert any("achievement_levels" in w for w in warnings)


def test_levels_missing_a_taught_standard_or_a_statement_are_reported():
    spec = copy.deepcopy(LEVELS)
    spec["units"][1]["standards"] = [unit(C)]
    spec["units"][0]["standards"][0]["levels"]["E"] = ""
    warnings = plan_warnings(read_plan(changed(HIGH, "evaluation.achievement_levels", spec)))
    assert any("성취수준(Ⅺ)에 없는 성취기준 1개: [10통사1-04-01]" in w for w in warnings)
    assert any(f"성취수준 진술이 빈 성취기준 1개: {A}" in w for w in warnings)


@pytest.mark.parametrize("value, message", [
    ({"units": "단원"}, "목록"),
    ({"units": [{"name": "가", "standards": [{"text": "원문"}]}]}, "code"),
    ({"units": [], "semester": {str(n): ["가"] for n in range(6)}}, "너무 많음"),
    ({"units": [], "semester": {"A": [{"x": 1}]}}, "글이어야"),
])
def test_wrong_levels_input_is_a_clear_error(value, message):
    with pytest.raises(CoursePlanError, match=message):
        read_plan(changed(HIGH, "evaluation.achievement_levels", value))


def test_elementary_rejects_achievement_levels():
    with pytest.raises(CoursePlanError, match="evaluation.achievement_levels"):
        read_plan(changed(ELEMENTARY, "evaluation.achievement_levels", LEVELS))


# ---------------------------------------------------------------- 양식 파일

@pytest.mark.parametrize("form", [DEFAULT_FORM, TEACHING_FORM])
def test_form_files_carry_no_memo_author_saver_or_teacher_name(form):
    with zipfile.ZipFile(form) as package:
        section = package.read("Contents/section0.xml").decode("utf-8")
        content = package.read("Contents/content.hpf").decode("utf-8")
        header = package.read("Contents/header.xml").decode("utf-8")
    assert 'type="MEMO"' not in section and "markpen" not in section and "Author" not in section
    assert re.search(r'name="lastsaveby" content="text">\s*<', content)
    assert 'secCnt="1"' in header and section.count("<hp:secPr") == 1
    assert not re.search(r"[가-힣]{2,4} \(인\)", re.sub(r"<[^>]+>", "", section))   # 교사 이름은 OOO뿐


# ---------------------------------------------------------------- 리뷰 반영 (2026-11-21)

def table_problems(xml: str) -> list[str]:
    """표마다 칸 주소·합침으로 격자를 그려 겹침, 빈 자리, 행 너비 합, 열 너비, rowCnt·colCnt를 본다
    (공용 검사기는 합친 칸이 이어지는 행을 거의 보지 않는다)."""
    from xml.etree import ElementTree
    hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
    problems = []
    for table in ElementTree.fromstring(xml).iter(hp + "tbl"):
        rows, cols = int(table.get("rowCnt")), int(table.get("colCnt"))
        width = int(table.find(hp + "sz").get("width"))
        grid, cells, column_widths = {}, [], {}
        trs = table.findall(hp + "tr")
        if len(trs) != rows:
            problems.append(f"{table.get('id')}: 행 수 {len(trs)} != rowCnt {rows}")
        for index, tr in enumerate(trs):
            for tc in tr.findall(hp + "tc"):
                col, row = int(tc.find(hp + "cellAddr").get("colAddr")), int(tc.find(hp + "cellAddr").get("rowAddr"))
                span = tc.find(hp + "cellSpan")
                colspan, rowspan = int(span.get("colSpan")), int(span.get("rowSpan"))
                cell_width = int(tc.find(hp + "cellSz").get("width"))
                if row != index:
                    problems.append(f"{table.get('id')}: {index}행 칸의 rowAddr {row}")
                cells.append(cell_width)
                if colspan == 1:
                    column_widths.setdefault(col, set()).add(cell_width)
                for x in range(col, col + colspan):
                    for y in range(row, row + rowspan):
                        if (x, y) in grid or x >= cols or y >= rows:
                            problems.append(f"{table.get('id')}: 겹침 또는 범위 밖 ({x},{y})")
                        grid[(x, y)] = len(cells) - 1
        if len(grid) != rows * cols:
            problems.append(f"{table.get('id')}: 빈 자리 {rows * cols - len(grid)}개")
        for y in range(rows):
            total = sum(cells[k] for k in {grid[(x, y)] for x in range(cols) if (x, y) in grid})
            if total != width:
                problems.append(f"{table.get('id')}: {y}행 너비 합 {total} != {width}")
        problems += [f"{table.get('id')}: {c}열 너비가 행마다 다름" for c, ws in column_widths.items() if len(ws) > 1]
    return problems


EDGE_CASES = [
    WITH_LEVELS, SECOND, changed(HIGH, "evaluation.tasks", []), changed(HIGH, "progress", []),
    changed(HIGH, "evaluation.kinds", [HIGH["evaluation"]["kinds"][1]]),
    changed(HIGH, "evaluation.tasks.0.base", []), changed(SECOND, "evaluation.tasks.0.notes", []),
    changed(changed(HIGH, "info.level", "중"), "info.credits", None),
]


@pytest.mark.parametrize("index", range(len(EDGE_CASES)))
def test_every_table_has_a_consistent_grid(tmp_path, index):
    spec = EDGE_CASES[index]
    if spec["info"]["level"] == "중":
        spec = changed(spec, "info.course_type", "중학교")
    _, _, xml = make(tmp_path, spec)
    assert table_problems(xml) == []


def test_line_breaks_inside_a_cell_are_hangul_line_breaks_or_paragraphs(tmp_path):
    spec = changed(HIGH, "evaluation.kinds.0.method", "선택형\n서술형")
    _, _, xml = make(tmp_path, changed(spec, "evaluation.purpose", ["첫째 줄\n둘째 줄"]), form=TEACHING_FORM)
    assert not re.search(r"<hp:t>[^<]*\n", xml)                       # 날 줄바꿈 문자가 글에 없음
    assert "선택형<hp:lineBreak/>서술형" in xml and "첫째 줄<hp:lineBreak/>둘째 줄" in xml
    assert "<hp:t>[강의식 수업]</hp:t>" in xml and "<hp:t>- 관점 살펴보기</hp:t>" in xml   # 수업 방법 줄은 문단으로


def test_backslash_is_written_full_width(tmp_path):
    body, _, _ = make(tmp_path, changed(HIGH, "evaluation.use", ["C:\자료 폴더에 보관한다."]))
    assert "C:＼자료" in body


def test_kept_absence_table_is_marked_and_counted(tmp_path):
    body, warnings, xml = make(tmp_path, HIGH)
    assert "[학교 규정 확인]" not in body
    absence = xml[xml.index("수행평가가 불가능한"):]
    absence = absence[:absence.index("</hp:tbl>")]
    assert "markpenBegin" in absence                                   # 양식 학교의 결시 처리 글에 형광펜
    assert f"(메모 {xml.count('type=' + chr(34) + 'MEMO' + chr(34))}개)" in warnings[0]


def test_semester_levels_alone_still_fill_part_na(tmp_path):
    spec = changed(HIGH, "evaluation.achievement_levels", {"units": [], "semester": {"A": ["학기 A"]}, "minimum": []})
    body, warnings, _ = make(tmp_path, spec)
    assert "가. 성취기준별 성취수준\n[작성 필요]" in body and "학기 A" in body
    spec = changed(HIGH, "evaluation.achievement_levels", {"units": [], "minimum": ["최소 진술"]})
    body, warnings, _ = make(tmp_path, spec, "minimum.hwpx")
    assert "최소 진술" in body and any("수준 칸을 [작성 필요]로 둠" in w for w in warnings)


def test_blank_line_separates_unit_tables(tmp_path):
    body, _, _ = make(tmp_path, WITH_LEVELS)
    assert "\n\n(2) 행복과 문화" in body


@pytest.mark.parametrize("value, message", [
    ({"units": [{"name": "가", "standards": []}]}, "하나 이상"),
    ({"unit": []}, "모르는 칸"),
    ({"units": [], "semester": {"A": ["가"], "A ": ["나"]}}, "겹침"),
])
def test_more_wrong_levels_input(value, message):
    with pytest.raises(CoursePlanError, match=message):
        read_plan(changed(HIGH, "evaluation.achievement_levels", value))


def test_standard_without_levels_is_reported():
    spec = copy.deepcopy(LEVELS)
    spec["units"][0]["standards"][0]["levels"] = {}
    warnings = plan_warnings(read_plan(changed(HIGH, "evaluation.achievement_levels", spec)))
    assert any(f"성취수준 진술이 빈 성취기준 1개: {A}" in w for w in warnings)


def test_only_the_last_base_row_takes_the_bottom_border(tmp_path):
    base = [{"text": f"기본점수 줄 {n}", "score": "2"} for n in range(3)]
    _, _, xml = make(tmp_path, changed(HIGH, "evaluation.tasks.0.base", base))
    fills = [re.search(r'borderFillIDRef="(\d+)"', cell_with(xml, f"기본점수 줄 {n}")).group(1) for n in range(3)]
    assert fills[0] == fills[1] != fills[2]


# ---------------------------------------------------------------- 쪽 배치 (2026-11-21)

LONG_TEXT = "자료를 근거로 관점을 비교하고 그 까닭을 사례와 함께 자세히 설명하였으며 결론을 분명히 밝혔다. " * 3


def long_task(name: str, count: int) -> dict:
    levels = [{"text": f"{score}점 {LONG_TEXT}", "score": score} for score in (3, 2, 1)]
    elements = [{"name": f"{name} 요소{n}", "points": 3, "levels": levels} for n in range(count)]
    return {**HIGH["evaluation"]["tasks"][0], "name": name,
            "areas": [{"area": f"{name} 영역", "points": 3 * count, "elements": elements}]}


def opening_before(xml: str, text: str) -> str:
    """text가 든 문단의 여는 태그 (text가 표 안에 있으면 그 표를 담은 바깥 문단)."""
    at = xml.index(text)
    table = xml.rfind("<hp:tbl ", 0, at)
    if table != -1 and xml.rfind("</hp:tbl>", 0, at) < table:
        at = table
    return re.findall(r"<hp:p [^>]*>", xml[:at])[-1]


def test_parts_six_and_eleven_start_on_a_new_page(tmp_path):
    _, _, xml = make(tmp_path, WITH_LEVELS)
    assert 'pageBreak="1"' in opening_before(xml, "수행평가 세부기준")
    assert 'pageBreak="1"' in opening_before(xml, "성취기준 및 성취수준")


def test_unit_tables_break_between_rows_so_a_standard_stays_together(tmp_path):
    _, _, xml = make(tmp_path, WITH_LEVELS)
    unit_tags = [tag for tag in re.findall(r"<hp:tbl [^>]*>", xml) if 'colCnt="3"' in tag and 'rowCnt="11"' in tag]
    assert unit_tags and all('pageBreak="TABLE"' in tag for tag in unit_tags)


def test_a_task_that_does_not_fit_starts_on_the_next_page(tmp_path):
    spec = changed(HIGH, "evaluation.tasks", [long_task("첫 과제", 4), long_task("둘째 과제", 4)])
    _, _, xml = make(tmp_path, spec)
    assert 'pageBreak="1"' in opening_before(xml, "2. 둘째 과제")
    assert 'pageBreak="1"' not in opening_before(xml, "1. 첫 과제")


def test_a_rubric_longer_than_a_page_splits_at_an_element_boundary(tmp_path):
    spec = changed(HIGH, "evaluation.tasks", [long_task("긴 과제", 9)])
    _, _, xml = make(tmp_path, spec)
    table = next(t for t in re.findall(r"<hp:tbl .*?</hp:tbl>", xml, re.S) if "긴 과제 영역" in t)
    assert table.count("긴 과제 영역") >= 2                    # 쪽마다 영역 칸을 새로 합쳐 이름을 다시 씀
    assert table_problems(xml) == []


def test_trailing_blank_paragraphs_do_not_make_an_empty_last_page(tmp_path):
    _, _, xml = make(tmp_path, WITH_LEVELS)
    assert xml[xml.rindex("</hp:tbl>"):].count("<hp:p ") <= 2


def test_a_long_vertical_rubric_in_a_given_form_also_splits_cleanly(tmp_path):
    spec = changed(HIGH, "evaluation.tasks", [long_task("세로 과제", 9)])
    _, _, xml = make(tmp_path, spec, form=TEACHING_FORM)
    table = next(t for t in re.findall(r"<hp:tbl .*?</hp:tbl>", xml, re.S) if "세로 과제 영역" in t)
    assert table.count("세로 과제 영역") >= 2
    assert table_problems(xml) == []


def test_cli_takes_a_school_form(tmp_path, capsys):
    import json
    from make_course_plan import main
    source, target = tmp_path / "plan.json", tmp_path / "plan.hwpx"
    source.write_text(json.dumps(HIGH, ensure_ascii=False), encoding="utf-8")
    assert main([str(source), str(target), "--form", str(TEACHING_FORM)]) == 0
    assert "만들었습니다" in capsys.readouterr().out
    assert main([str(source), str(target), "--form"]) == 2


def test_school_assigned_education_goes_into_the_remarks_or_a_marked_place(tmp_path):
    spec = changed(HIGH, "progress.0.education", ["교통안전교육(3시간)", "[성교육·양성평등교육(1시간)]"])
    body, _, xml = make(tmp_path, spec)
    assert "3.3. 개학식\n[교통안전교육(3시간)]\n[성교육·양성평등교육(1시간)]" in body
    assert "[학교 안내 교육]" not in body
    body, _, xml = make(tmp_path, HIGH, "none.hwpx")
    assert PEN + "[학교 안내 교육]" in xml and xml.count("그 주 비고 칸에 [교육명(시간)]으로 적고") == 1


# ---------------------------------------------------------------- 리뷰 반영 2 (2026-11-21): 메모·표식·양식 짜임

def memo_ids(xml: str) -> list[str]:
    return re.findall(r'<hp:fieldBegin id="(\d+)" type="MEMO"', xml)


def test_an_output_with_memos_can_be_filled_again_as_a_school_form(tmp_path):
    first = tmp_path / "first.hwpx"
    from make_course_plan import build
    build(HIGH, first)
    _, warnings, xml = make(tmp_path, changed(HIGH, "evaluation.absence", ["가.", "나.", "다."]), "again.hwpx",
                            form=first)
    ids = memo_ids(xml)
    assert len(ids) == len(set(ids))                                   # 양식에 있던 메모와 번호가 겹치지 않음
    assert xml.count("<hp:fieldBegin") == xml.count("<hp:fieldEnd")
    assert any("양식에 원래 있던 메모" in w for w in warnings)


def test_mark_characters_in_the_input_do_not_break_the_document(tmp_path):
    spec = changed(HIGH, "evaluation.use", ["피드백" + chr(0xE003) + "에 활용", chr(0xE000) + "열림만"])
    body, _, xml = make(tmp_path, spec)
    assert "피드백에 활용" in body and chr(0xE003) not in xml
    assert xml.count("markpenBegin") == xml.count("markpenEnd")


def test_a_multi_line_base_row_keeps_each_memo_inside_one_paragraph(tmp_path):
    spec = changed(HIGH, "evaluation.tasks.0.base", [{"text": ["미제출 시", "기본점수"], "score": "2"}])
    _, _, xml = make(tmp_path, spec)
    flat = re.sub(r'<hp:ctrl><hp:fieldBegin [^>]*type="MEMO".*?</hp:fieldBegin></hp:ctrl>', "<MEMO>", xml, flags=re.S)
    for paragraph in re.findall(r"<hp:p [^>]*>(?:(?!<hp:p ).)*?</hp:p>", flat, re.S):
        assert paragraph.count("<MEMO>") == paragraph.count("<hp:fieldEnd")
        assert paragraph.count("markpenBegin") == paragraph.count("markpenEnd")


def test_page_breaks_are_never_set_inside_a_table(tmp_path):
    _, _, xml = make(tmp_path, WITH_LEVELS)
    for table in re.findall(r"<hp:tbl .*?</hp:tbl>", xml, re.S):
        assert 'pageBreak="1"' not in table


def test_a_school_form_of_another_shape_is_a_form_error(tmp_path):
    import zipfile as zf
    odd = tmp_path / "odd.hwpx"
    with zf.ZipFile(DEFAULT_FORM) as source, zf.ZipFile(odd, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "Contents/section0.xml":
                data = data.decode("utf-8").replace("유의사항", "주의").encode("utf-8")
            target.writestr(info, data)
    with pytest.raises(ValueError, match="양식 짜임이 기본 양식과 달라"):
        make(tmp_path, HIGH, form=odd)


def test_elementary_also_gets_the_school_education_place_or_lines(tmp_path):
    _, _, xml = make(tmp_path, ELEMENTARY)
    assert PEN + "[학교 안내 교육]" in xml and xml.count("그 주 비고 칸에 [교육명(시간)]으로 적고") == 1
    spec = changed(ELEMENTARY, "progress.0.education", ["생활안전교육(1시간)"])
    body, _, xml = make(tmp_path, spec, "given.hwpx")
    assert "[생활안전교육" in body and "(1시간)]" in body and "[학교 안내 교육]" not in body   # 좁은 칸은 '(' 앞에서 줄바꿈


# ---------------------------------------------------------------- 리뷰 반영 3 (2026-11-21)

def test_wrapping_a_paragraph_that_starts_with_a_memo_keeps_the_new_marks_outside_it():
    from course_form_marks import MEMO_CLOSE, RULE_OPEN, wrap_paragraph
    memo = ('<hp:ctrl><hp:fieldBegin id="5" type="MEMO"><hp:subList><hp:p id="0"><hp:run charPrIDRef="1">'
            '<hp:t>옛 메모</hp:t></hp:run></hp:p></hp:subList></hp:fieldBegin></hp:ctrl>')
    paragraph = f'<hp:p id="0"><hp:run charPrIDRef="1">{memo}<hp:t>본문 글</hp:t></hp:run></hp:p>'
    wrapped = wrap_paragraph(paragraph, RULE_OPEN, MEMO_CLOSE)
    assert memo in wrapped and RULE_OPEN + "본문 글" + MEMO_CLOSE in wrapped


def test_education_lines_are_one_bracketed_line_each():
    from make_course_plan_input import CoursePlanError, _education
    assert _education(["교통안전\n교육(3시간)", "[[성교육(1시간)", "", "[안전]"], "e") == [
        "[교통안전 교육(3시간)]", "[성교육(1시간)]", "[안전]"]
    with pytest.raises(CoursePlanError, match="너무 김"):
        _education(["가" * 101], "e")


def test_a_failed_highlight_step_leaves_the_earlier_elementary_file_and_no_draft(tmp_path, monkeypatch):
    import make_course_plan
    from make_course_plan import build
    target = tmp_path / "elem.hwpx"
    build(ELEMENTARY, target)
    before = target.read_bytes()

    def broken(*_args, **_kwargs):
        raise RuntimeError("검사 실패 흉내")
    monkeypatch.setattr(make_course_plan, "apply_marks", broken)
    with pytest.raises(RuntimeError):
        build(ELEMENTARY, target)
    assert target.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["elem.hwpx"]
