"""칸 색·테두리·좁은 쪽 여백 시험."""
import re
import zipfile

import pytest

import make_hwpx


def build(tmp_path, spec):
    out = tmp_path / "t.hwpx"
    make_hwpx.build_hwpx(spec, out)
    with zipfile.ZipFile(out) as package:
        return package.read("Contents/header.xml").decode(), package.read("Contents/section0.xml").decode()


def table(cell, **options):
    return {"blocks": [{"type": "table", "rows": [[cell]], **options}]}


def test_cell_fill_is_written_to_header_and_used_by_cell(tmp_path):
    header, section = build(tmp_path, table({"text": "띠", "fill": "#1F3A5F"}))
    assert 'faceColor="#1F3A5F"' in header
    assert section.count('<hp:tc ') == 1


def test_cell_text_color_and_size_make_new_char_style(tmp_path):
    header, _ = build(tmp_path, table({"text": "제목", "color": "#FFFFFF", "size": "xlarge", "bold": True}))
    assert 'height="1800" textColor="#FFFFFF"' in header


def test_same_design_is_registered_once(tmp_path):
    cell = {"text": "가", "fill": "#ABCDEF"}
    header, _ = build(tmp_path, {"blocks": [{"type": "table", "rows": [[cell, dict(cell)]]}]})
    assert header.count('faceColor="#ABCDEF"') == 1


def test_bottom_dot_edge_hides_other_sides(tmp_path):
    header, _ = build(tmp_path, table({"text": "", "edges": "bottom_dot", "edge_color": "#8899AA"}))
    assert '<hh:bottomBorder type="DOT" width="0.12 mm" color="#8899AA"/>' in header
    assert '<hh:leftBorder type="NONE" width="0.12 mm" color="#8899AA"/>' in header


@pytest.mark.parametrize("cell, message", [
    ({"text": "", "fill": "navy"}, "fill"),
    ({"text": "", "color": "#12345"}, "color"),
    ({"text": "", "edges": "wavy"}, "edges"),
    ({"text": "", "size": "huge"}, "size"),
])
def test_bad_design_value_is_refused(tmp_path, cell, message):
    with pytest.raises(ValueError, match=message):
        build(tmp_path, table(cell))


def test_plain_table_output_does_not_change(tmp_path):
    header, section = build(tmp_path, table({"text": "가", "shade": True}))
    assert 'faceColor="#D9D9D9"' in header
    assert 'textColor="#FFFFFF"' not in header


def _char_of_run(header, section, text):
    """글이 든 run의 글자 모양 XML을 찾는다."""
    char_id = re.search(rf'charPrIDRef="(\d+)"><hp:t>{text}</hp:t>', section).group(1)
    return re.search(rf'<hh:charPr id="{char_id}".*?</hh:charPr>', header, re.S).group(0)


def test_mark_color_paints_bold_marks_only(tmp_path):
    header, section = build(tmp_path, table({"text": "식물은 **광합성**을 한다", "mark_color": "#0000FF"}))
    marked, plain = _char_of_run(header, section, "광합성"), _char_of_run(header, section, "식물은 ")
    assert 'textColor="#0000FF"' in marked and "<hh:bold/>" in marked
    assert 'textColor="#000000"' in plain and "<hh:bold/>" not in plain


def test_mark_color_keeps_cell_text_color(tmp_path):
    header, section = build(tmp_path, table({"text": "회색 **답**", "color": "#7F7F7F", "mark_color": "#0000FF"}))
    assert 'textColor="#7F7F7F"' in _char_of_run(header, section, "회색 ")
    assert 'textColor="#0000FF"' in _char_of_run(header, section, "답")


def test_bad_mark_color_is_refused(tmp_path):
    with pytest.raises(ValueError, match="mark_color"):
        build(tmp_path, table({"text": "", "mark_color": "blue"}))


def test_compact_page_reduces_top_margin(tmp_path):
    _, section = build(tmp_path, {"page": "compact", "blocks": [{"type": "paragraph", "text": "가"}]})
    assert 'header="850" footer="1134"' in section and 'top="1984" bottom="1984"' in section


def test_default_page_keeps_skeleton_margin(tmp_path):
    _, section = build(tmp_path, {"blocks": [{"type": "paragraph", "text": "가"}]})
    assert 'header="4252" footer="4252"' in section and 'top="5668"' in section


def test_tight_table_has_no_outer_gap(tmp_path):
    _, section = build(tmp_path, table({"text": "가"}, gap="tight"))
    assert 'top="0" bottom="0"/><hp:inMargin' in section


def test_small_gap_uses_short_outer_margin(tmp_path):
    _, section = build(tmp_path, table({"text": "가"}, gap="small"))
    assert 'top="340" bottom="340"/><hp:inMargin' in section


def _long_table(count=30, **options):
    rows = [[{"text": f"{number}행", "height_px": 40}] for number in range(count)]
    return {"page": "app", "blocks": [{"type": "table", "rows": rows, **options}]}


def test_long_table_splits_across_pages_by_rows(tmp_path):
    _, section = build(tmp_path, _long_table())
    assert 'pageBreak="TABLE"' in section and 'treatAsChar="0"' in section


def _short_headed_table(**options):
    return {"page": "app", "blocks": [{"type": "table", "header": ["차시", "방법"],
                                       "rows": [["1", "사전 질문지"], ["3", "출구 카드"]], **options}]}


def test_short_headed_table_moves_whole_by_default(tmp_path):
    _, section = build(tmp_path, _short_headed_table())
    assert 'pageBreak="NONE"' in section and 'treatAsChar="1"' in section


def test_split_rows_lets_short_table_split_by_rows(tmp_path):
    """split_rows면 짧은 표도 쪽 끝에서 행 단위로 나뉜다 (통째로 넘어가 앞 쪽 아래가 비는 것을 막는다)."""
    _, section = build(tmp_path, _short_headed_table(split_rows=True))
    assert 'pageBreak="TABLE"' in section and 'treatAsChar="0"' in section and 'repeatHeader="1"' in section


def test_keep_together_wins_over_split_rows(tmp_path):
    _, section = build(tmp_path, _short_headed_table(split_rows=True, keep_together=True))
    assert 'pageBreak="NONE"' in section and 'treatAsChar="1"' in section


def test_keep_together_table_moves_whole_to_next_page(tmp_path):
    _, section = build(tmp_path, _long_table(12, keep_together=True))     # 약 127mm: 짧은 표 한도보다 길다
    assert 'pageBreak="NONE"' in section and 'treatAsChar="1"' in section


def test_tall_answer_box_still_moves_whole(tmp_path):
    """한도 검사는 keep_together 상자만 본다. 시험지 답 칸(28줄)은 예전처럼 통째로 옮겨진다."""
    out = tmp_path / "t.hwpx"
    warnings = make_hwpx.build_hwpx({"page": "sheet", "blocks": [{"type": "answer_box", "lines": 28}]}, out)
    with zipfile.ZipFile(out) as package:
        section = package.read("Contents/section0.xml").decode()
    assert 'pageBreak="NONE"' in section and 'treatAsChar="1"' in section
    assert not any("한 쪽보다 길어" in w for w in warnings)


def test_merged_cell_text_counts_toward_box_height(tmp_path):
    """여러 행을 합친 칸의 글이 길면 그 높이도 센다 (단원 설계의 핵심 아이디어 칸)."""
    long_text = "\n".join("가나다라마바사아자차카타파하 " * 4 for _ in range(60))
    rows = [[{"text": long_text, "rowspan": 2}, {"text": "짧은 칸"}], [{"text": "짧은 칸"}]]
    out = tmp_path / "t.hwpx"
    warnings = make_hwpx.build_hwpx({"page": "app", "blocks": [{"type": "table", "rows": rows,
                                                                 "keep_together": True}]}, out)
    assert any("한 쪽보다 길어" in w and "가나다라" in w for w in warnings)


def test_keep_together_box_taller_than_a_page_splits_with_warning(tmp_path):
    """통째로 옮길 상자가 한 쪽보다 길면 잘리지 않게 행 단위로 나누고 알린다."""
    out = tmp_path / "t.hwpx"
    warnings = make_hwpx.build_hwpx(_long_table(30, keep_together=True), out)
    with zipfile.ZipFile(out) as package:
        section = package.read("Contents/section0.xml").decode()
    assert 'pageBreak="TABLE"' in section and 'treatAsChar="0"' in section
    assert any("한 쪽보다 길어" in w for w in warnings)


def test_app_table_keep_with_next_uses_keeping_anchor(tmp_path):
    header, section = build(tmp_path, {"page": "app", "blocks": [
        {"type": "table", "rows": [["제목"]], "keep_with_next": True}, {"type": "table", "rows": [["본문"]]}]})
    anchors = re.findall(r'<hp:p id="\d+" paraPrIDRef="(\d+)"[^>]*><hp:run[^>]*><hp:tbl', section)
    keeps = [re.search(rf'<hh:paraPr id="{anchor}"[^>]*>.*?keepWithNext="(\d)"', header, re.S).group(1)
             for anchor in anchors]
    assert keeps == ["1", "0"]
