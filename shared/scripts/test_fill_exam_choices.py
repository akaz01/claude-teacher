"""기본 원안지 양식에서 4지선다·3지선다 문항을 채우는 시험 (5개짜리 틀을 줄여 쓴다)."""
import re
import zipfile
from pathlib import Path

import pytest

from fill_exam import FillError, fill_exam
from fill_exam_parse import choice_order_notes, read_exam
from fill_hwpx import read_form
from make_hwpx_check import validate_package

FORM = Path(__file__).resolve().parents[2] / "skills" / "assessment-items" / "assets" / "exam_form.hwpx"
pytestmark = pytest.mark.skipif(not FORM.exists(), reason="기본 원안지 양식이 없음")
HIGHLIGHT = "markpenBegin"


def pick(count: int, answer: int, **extra) -> dict:
    words = ["가나", "다라마", "바사아자", "차카타파하", "거너더러머버"]
    return {"type": "short_table", "stem": f"{count}지선다 문제", "points": 3,
            "choices": words[:count], "answer": answer, **extra}


def section(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        return package.read("Contents/section0.xml").decode("utf-8")


def choice_tables(xml: str) -> list[tuple[int, int, str]]:
    """①이 든 표의 (행 수, 칸 수, 원문)."""
    found = []
    for table in re.finditer(r'<hp:tbl [^>]*rowCnt="(\d+)" colCnt="(\d+)"', xml):
        text = xml[table.start():xml.index("</hp:tbl>", table.start())]
        if "①" in text:
            found.append((int(table.group(1)), int(table.group(2)), text))
    return found


def cell_places(table: str) -> list[tuple[int, int]]:
    return [(int(row), int(col)) for col, row in re.findall(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', table)]


def make(tmp_path: Path, items: list[dict], student: bool = False) -> Path:
    out = tmp_path / ("student.hwpx" if student else "pen.hwpx")
    fill_exam(FORM, {"items": items}, out, student=student)
    return out


MIXED = [pick(4, 1), pick(4, 2), pick(4, 4), pick(5, 3), pick(5, 5)]


@pytest.mark.parametrize("student", [False, True])
def test_mixed_four_and_five_choices_pass_the_checker(tmp_path, student):
    out = make(tmp_path, MIXED, student)
    assert validate_package(out) == []


def test_four_choices_have_no_fifth_slot(tmp_path):
    xml = section(make(tmp_path, MIXED))
    tables = choice_tables(xml)
    assert len(tables) == 5
    for (rows, cols, text), count in zip(tables, [4, 4, 4, 5, 5]):
        assert (rows, cols) == (1, count)
        assert [text.count(sign) for sign in "①②③④⑤"] == [1] * count + [0] * (5 - count)
        assert len(cell_places(text)) == count == len(re.findall(r"<hp:tc\b", text))


def test_four_choice_cells_fill_the_table_width(tmp_path):
    text = choice_tables(section(make(tmp_path, [pick(4, 1)])))[0][2]
    widths = [int(width) for width in re.findall(r'<hp:cellSz width="(\d+)"', text)]
    table_width = int(re.search(r'<hp:sz width="(\d+)"', text).group(1))
    assert len(widths) == 4 and sum(widths) == table_width


def test_answer_mark_follows_the_answer_number(tmp_path):
    xml = section(make(tmp_path, [pick(4, 3)]))
    cells = re.findall(r"<hp:tc\b.*?</hp:tc>", choice_tables(xml)[0][2], re.S)
    marked = [index + 1 for index, cell in enumerate(cells) if HIGHLIGHT in cell]
    assert marked == [3]


def test_student_file_has_no_answer_mark(tmp_path):
    xml = section(make(tmp_path, MIXED, student=True))
    assert "hp:markpen" not in xml


@pytest.mark.parametrize("layout, shape, order", [
    ("5x1", (4, 1), [(0, 0), (1, 0), (2, 0), (3, 0)]),
    ("2x3", (2, 2), [(0, 0), (0, 1), (1, 0), (1, 1)]),
])
def test_four_choices_follow_the_frame_layout(tmp_path, layout, shape, order):
    item = {"type": "combo_table", "layout": f"{shape[0]}x{shape[1]}", "stem": "가", "points": 3,
            "choices": ["하나", "둘", "셋", "넷"], "answer": 2}
    rows, cols, text = choice_tables(section(make(tmp_path, [item])))[0]
    assert (rows, cols) == shape and cell_places(text) == order
    height = int(re.search(r'<hp:sz width="\d+" widthRelTo="ABSOLUTE" height="(\d+)"', text).group(1))
    assert height > 0


def test_two_by_three_frame_becomes_one_by_three_for_three_choices(tmp_path):
    item = {"type": "combo_table", "stem": "가", "points": 3, "bogi": ["하나", "둘", "셋"],
            "choices": ["ㄱ", "ㄴ", "ㄱ, ㄴ"], "answer": 3}
    rows, cols, text = choice_tables(section(make(tmp_path, [item])))[0]
    assert (rows, cols) == (1, 3) and "④" not in text and "⑤" not in text


def test_three_choices_in_a_single_row(tmp_path):
    rows, cols, text = choice_tables(section(make(tmp_path, [pick(3, 2)])))[0]
    assert (rows, cols) == (1, 3) and "④" not in text


def test_tables_after_a_reduced_one_stay_intact(tmp_path):
    items = [pick(4, 1), {"type": "combo_table", "layout": "5x1", "stem": "나", "points": 3,
                          "choices": ["가", "나", "다", "라", "마"], "answer": 5}]
    tables = choice_tables(section(make(tmp_path, items)))
    assert [(rows, cols) for rows, cols, _ in tables] == [(1, 4), (5, 1)]


def test_more_choices_than_any_frame_is_still_refused(tmp_path):
    item = {"type": "short_table", "stem": "가", "points": 3,
            "choices": ["가", "나", "다", "라", "마", "바"], "answer": 1}
    with pytest.raises(FillError, match="선택지가 6개"):
        make(tmp_path, [item])


def test_one_choice_is_refused(tmp_path):
    with pytest.raises(FillError):
        make(tmp_path, [{"type": "short_table", "stem": "가", "points": 3, "choices": ["가"], "answer": 1}])


def test_long_four_choices_get_the_width_note(tmp_path):
    item = pick(4, 1)
    item["choices"] = ["아주 긴 선택지 문장이 칸보다 훨씬 길게 이어집니다"] * 4
    out = tmp_path / "long.hwpx"
    result = fill_exam(FORM, {"items": [item]}, out)
    assert any("칸보다 길어" in note for note in result.notes)


def test_reduced_form_is_read_back_with_four_slots(tmp_path):
    out = make(tmp_path, [pick(4, 2)])
    exam = read_exam(read_form(out))
    assert [len(frame.slots) for frame in exam.frames if frame.kind == "short_table"] == [4]


def answers(counts: list[int]) -> list[tuple[str, dict]]:
    return [(f"문항 {n}", pick(4, answer)) for n, answer in enumerate(counts, start=1)]


def test_answer_spread_is_checked_for_four_choices():
    even = answers([1, 2, 3, 4, 1, 2, 3, 4])
    lopsided = answers([2, 2, 1, 2, 3, 2, 4, 2])
    assert not choice_order_notes(even)
    assert any("정답 번호 분포" in note for note in choice_order_notes(lopsided))
    assert any("4문항 이어짐" in note for note in choice_order_notes(answers([3, 3, 3, 3])))


def test_four_and_five_choice_answers_are_counted_apart():
    mixed = [(f"문항 {n}", pick(count, answer)) for n, (count, answer) in
             enumerate([(4, 1), (4, 2), (4, 3), (5, 5), (5, 4)], start=1)]
    assert not choice_order_notes(mixed)


def test_same_answer_run_counts_across_choice_counts():
    streak = [(f"문항 {n}", pick(count, 3)) for n, count in enumerate([4, 5, 4, 5], start=1)]
    assert any("4문항 이어짐" in note for note in choice_order_notes(streak))


def test_run_is_broken_by_a_different_answer_of_another_choice_count():
    mixed = [(f"문항 {n}", pick(count, answer)) for n, (count, answer) in
             enumerate([(4, 3), (5, 1), (4, 3), (4, 3), (4, 3)], start=1)]
    assert not any("이어짐" in note for note in choice_order_notes(mixed))


@pytest.mark.parametrize("layout, shape", [("2x3", (2, 2)), ("5x1", (4, 1)), ("2x2", (2, 2)), ("4x1", (4, 1))])
def test_five_choice_layout_names_map_to_the_reduced_layout(tmp_path, layout, shape):
    item = {"type": "combo_table", "layout": layout, "stem": "가", "points": 3,
            "choices": ["하나", "둘", "셋", "넷"], "answer": 2}
    out = tmp_path / "out.hwpx"
    result = fill_exam(FORM, {"items": [item]}, out)
    rows, cols, _ = choice_tables(section(out))[0]
    assert (rows, cols) == shape
    assert not any("layout" in note for note in result.notes)
