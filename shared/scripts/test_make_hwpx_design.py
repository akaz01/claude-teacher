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
