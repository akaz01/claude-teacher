"""fill_exam의 자료 표(table)와 그림 두 장 나란히(picture 목록) 시험."""
import re
from pathlib import Path

import pytest

from fill_exam import fill_exam
from fill_exam_grid import column_widths
from fill_hwpx import FillError
from test_fill_exam_media import FORM, item, package, png

TABLE = {"head": ["구분", "1950년", "1960년"], "rows": [["농업", "46.4", "37.1"], ["공업", "7.6", "11.2"]],
         "caption": "<표> 산업별 취업자 비율(%)", "widths": [2, 1, 1]}
COLUMN = 26505                                                   # 원안지 단 너비


def table_of(xml: str) -> str:
    return re.search(r'<hp:tbl\b[^>]*rowCnt="3" colCnt="3".*?</hp:tbl>', xml, re.S).group(0)


def shape_of(header: str, number: str) -> str:
    return re.search(rf'<hh:paraPr id="{number}".*?</hh:paraPr>', header, re.S).group(0)


def test_table_has_rows_cols_and_centered_head(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(table=TABLE)]}, out)
    xml, header, _, _ = package(out)
    table = table_of(xml)
    assert table.count("<hp:tr>") == 3 and table.count("<hp:tc ") == 9
    assert "&lt;표&gt; 산업별 취업자 비율(%)" in xml
    cells = re.findall(r"<hp:tc .*?</hp:tc>", table, re.S)
    for cell in cells:
        ref = re.search(r'paraPrIDRef="(\d+)"', cell).group(1)
        assert 'horizontal="CENTER"' in shape_of(header, ref)
    assert len({re.search(r'borderFillIDRef="(\d+)"', cell).group(1) for cell in cells[:3]}) == 1
    assert re.search(r'borderFillIDRef="(\d+)"', cells[0]).group(1) != re.search(
        r'borderFillIDRef="(\d+)"', cells[3]).group(1)           # 머리 칸 바탕이 다르다


def test_table_fits_column_and_starts_at_baseline(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(table=TABLE)]}, out)
    xml, header, _, _ = package(out)
    table = table_of(xml)
    width = int(re.search(r'<hp:sz width="(\d+)"', table).group(1))
    cells = [int(w) for w in re.findall(r'<hp:cellSz width="(\d+)"', table)[:3]]
    assert sum(cells) == width
    assert COLUMN - 1100 <= width <= COLUMN - 900                # 왼쪽은 글자 하나 들어간 기준선, 오른쪽은 단 끝
    ref = re.findall(r'paraPrIDRef="(\d+)"', xml[:xml.index(table)])[-1]
    assert 'horizontal="RIGHT"' in shape_of(header, ref)


def test_table_borders_are_added_to_header_once(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(table=TABLE), item(table=TABLE)]}, out)
    xml, header, _, _ = package(out)
    ids = re.findall(r'<hh:borderFill id="(\d+)"', header)
    assert int(re.search(r'<hh:borderFills itemCnt="(\d+)"', header).group(1)) == len(ids) == len(set(ids))
    assert xml.count('rowCnt="3" colCnt="3"') == 2


def test_table_comes_after_box_and_before_choices(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(box="자료 글", table=TABLE)]}, out)
    xml = package(out)[0]
    assert xml.index("자료 글") < xml.index("농업") < xml.index("갑, 을, 병")


def test_wide_word_is_reported(tmp_path):
    spec = {"head": ["구분", "값"], "rows": [["아주아주아주긴낱말이들어간칸", "1"]], "widths": [1, 5]}
    result = fill_exam(FORM, {"items": [item(table=spec)]}, tmp_path / "out.hwpx")
    assert any("표 칸보다 넓어" in note for note in result.notes)


def test_short_label_filling_cell_is_reported(tmp_path):
    """"Reading Stand"처럼 칸에 거의 꽉 찬 짧은 이름은 한글에서 두 줄이 되므로 알린다 (실측: 영어 17번)."""
    rows = [["Reading Stand", "holding a book open", "9,000 won"], ["Page Holder", "holding a book open", "12,000 won"]]
    tight = {"head": ["Product", "Use", "Price"], "rows": rows, "widths": [15, 21, 14]}
    roomy = {"head": ["Product", "Use", "Price"], "rows": [[a, b, c.replace(" won", "")] for a, b, c in rows],
             "widths": [17, 23, 10]}
    tight_notes = fill_exam(FORM, {"items": [item(table=tight)]}, tmp_path / "tight.hwpx").notes
    roomy_notes = fill_exam(FORM, {"items": [item(table=roomy)]}, tmp_path / "roomy.hwpx").notes
    assert any("꽉 차" in note and "Reading Stand" in note for note in tight_notes)
    assert not any("꽉 차" in note for note in roomy_notes)


def test_student_copy_keeps_table(tmp_path):
    out = tmp_path / "student.hwpx"
    fill_exam(FORM, {"items": [item(table=TABLE)]}, out, student=True)
    assert "농업" in package(out)[0]


def test_default_widths_follow_text():
    cells = [["구분", "값"], ["아주 긴 글이 들어갑니다", "1"]]
    widths = column_widths({}, cells, 20000)
    assert sum(widths) == 20000 and widths[0] > widths[1]


@pytest.mark.parametrize("table, message", [
    ({"head": ["가"]}, "table은"),
    ({"head": ["가", "나"], "rows": [["1"]]}, "칸 수가 head와 같아야"),
    ({"head": ["가", "나"], "rows": [["1", "2"]], "widths": [1]}, "widths"),
    ({"head": ["가", "나"], "rows": [["1", "2"]], "align": ["middle", "left"]}, "align"),
    ({"head": ["가", "나"], "rows": []}, "rows"),
    ({"head": ["가"] * 9, "rows": [["1"] * 9]}, "8칸"),
    ("표", "table은"),
])
def test_bad_table_specs_are_refused(tmp_path, table, message):
    with pytest.raises(FillError, match=message):
        fill_exam(FORM, {"items": [item(table=table)]}, tmp_path / "out.hwpx")
    assert not (tmp_path / "out.hwpx").exists()


def test_written_items_cannot_take_tables(tmp_path):
    with pytest.raises(FillError, match="서답형"):
        fill_exam(FORM, {"items": [{"type": "written", "stem": "가", "points": 5, "table": TABLE}]},
                  tmp_path / "out.hwpx")


def two_pictures(tmp_path: Path) -> list[dict]:
    (tmp_path / "a.png").write_bytes(png(40, 20))
    (tmp_path / "b.png").write_bytes(png(30, 30))
    return [{"file": str(tmp_path / "a.png"), "caption": "(가)"}, {"file": str(tmp_path / "b.png"), "caption": "(나)"}]


def pic_sizes(table: str) -> list[tuple[int, int]]:
    return [(int(w), int(h)) for w, h in re.findall(r'<hp:pic .*?<hp:sz width="(\d+)"[^>]*?height="(\d+)"', table, re.S)]


def test_two_pictures_share_one_row(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(picture=two_pictures(tmp_path))]}, out)
    table = re.search(r'<hp:tbl\b[^>]*rowCnt="1" colCnt="3".*?</hp:tbl>', package(out)[0], re.S).group(0)
    assert table.count("<hp:pic ") == 2 and "(가)" in table and "(나)" in table
    sizes = pic_sizes(table)
    assert abs(sizes[0][1] - sizes[1][1]) <= 2                   # 높이를 맞춘다
    cells = [int(w) for w in re.findall(r'<hp:cellSz width="(\d+)"', table)]
    assert cells[1] == 2000 and sum(cells) <= COLUMN             # 사이는 글자 두 개


def test_two_pictures_with_width_mm(tmp_path):
    pictures = two_pictures(tmp_path)
    pictures[0]["width_mm"], pictures[1]["width_mm"] = 30, 20
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(picture=pictures)]}, out)
    table = re.search(r'<hp:tbl\b[^>]*colCnt="3".*?</hp:tbl>', package(out)[0], re.S).group(0)
    widths = [w for w, _ in pic_sizes(table)]
    assert abs(widths[0] - 30 * 7200 / 25.4) < 2 and abs(widths[1] - 20 * 7200 / 25.4) < 2


def test_one_item_list_is_a_single_picture(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(picture=two_pictures(tmp_path)[:1])]}, out)
    xml = package(out)[0]
    assert xml.count("<hp:pic ") == 1 and 'colCnt="3"' not in xml


def test_student_copy_keeps_two_pictures(tmp_path):
    out = tmp_path / "student.hwpx"
    fill_exam(FORM, {"items": [item(picture=two_pictures(tmp_path))]}, out, student=True)
    assert package(out)[0].count("<hp:pic ") == 2


@pytest.mark.parametrize("picture, message", [
    ([], "한두 장"),
    (["a.png", "b.png", "c.png"], "한두 장"),
    ([{"file": "a.png"}, 3], "picture"),
    ([{"file": "a.png", "width_mm": 500}, "b.png"], "width_mm"),
])
def test_bad_picture_lists_are_refused(tmp_path, picture, message):
    with pytest.raises(FillError, match=message):
        fill_exam(FORM, {"items": [item(picture=picture)]}, tmp_path / "out.hwpx")


def test_table_and_pictures_together_keep_header_ids_unique(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(table=TABLE, picture=two_pictures(tmp_path)), item(table=TABLE)]}, out)
    ids = re.findall(r'<hh:borderFill id="(\d+)"', package(out)[1])
    assert len(ids) == len(set(ids))
