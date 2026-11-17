"""make_hwpx 앱 학습지 기능 시험: 도형, 그라데이션, 명조·장평, 글자 음영 빈칸, 종이 기준 배치, 꼬리말 표."""
import re
import zipfile

import pytest

import make_hwpx


def build(tmp_path, spec):
    out = tmp_path / "out.hwpx"
    make_hwpx.build_hwpx(spec, out)
    assert not make_hwpx.validate_package(out)
    with zipfile.ZipFile(out) as package:
        return (package.read("Contents/header.xml").decode("utf-8"),
                package.read("Contents/section0.xml").decode("utf-8"))


def one_cell(cell, **table):
    return {"blocks": [{"type": "table", "widths": [1], "rows": [[cell]], **table}]}


def test_round_shape_in_a_cell_is_a_text_box_with_rounded_corners(tmp_path):
    chip = {"shape": "round", "w": 60, "h": 20, "fill": "#E3EDF9", "text": "칩", "color": "#1F3F7A", "bold": True}
    _, section = build(tmp_path, one_cell({"content": ["앞 ", chip]}))
    assert "<hp:rect " in section and 'ratio="50"' in section and "<hp:drawText" in section
    assert 'width="4500"' in section and 'height="1500"' in section       # 60px x 20px, 1px = 75
    assert 'treatAsChar="1"' in section and "<hp:t>칩</hp:t>" in section


def test_ellipse_shape_has_ellipse_geometry(tmp_path):
    circle = {"shape": "ellipse", "w": 24, "h": 24, "fill": "#2E6DB4", "text": "1", "color": "#FFFFFF"}
    _, section = build(tmp_path, one_cell({"content": [circle]}))
    assert "<hp:ellipse " in section and "<hc:center " in section and "<hc:ax1 " in section


def test_shape_text_gets_its_own_char_style(tmp_path):
    chip = {"shape": "round", "w": 60, "h": 20, "text": "칩", "color": "#1F3F7A", "bold": True, "size": 9, "ratio": 88}
    header, _ = build(tmp_path, one_cell({"content": [chip]}))
    assert 'textColor="#1F3F7A"' in header and 'height="900"' in header and 'hangul="88"' in header


@pytest.mark.parametrize("shape, message", [
    ({"shape": "star", "w": 10, "h": 10}, "shape"),
    ({"shape": "round", "w": 0, "h": 10}, "w"),
    ({"shape": "round", "w": 10}, "h"),
])
def test_bad_shape_is_refused(tmp_path, shape, message):
    with pytest.raises(ValueError, match=message):
        build(tmp_path, one_cell({"content": [shape]}))


def test_cell_gradient_fill_makes_a_gradation_brush(tmp_path):
    header, _ = build(tmp_path, one_cell({"text": "가", "fill": "#1F3F7A", "fill_to": "#2E6DB4", "fill_angle": 80}))
    assert '<hc:gradation type="LINEAR" angle="80"' in header and 'value="#2E6DB4"' in header
    assert 'step="50"' in header


def test_serif_font_adds_a_second_face_and_uses_it(tmp_path):
    header, _ = build(tmp_path, one_cell({"text": "가", "font": "serif", "size": 10.5, "bold": True}))
    assert header.count('face="함초롬바탕"') >= 7 and 'height="1050"' in header
    serif_ids = set(re.findall(r'<hh:fontRef hangul="(\d+)"', header))
    assert len(serif_ids) >= 2


def test_default_documents_keep_one_extra_face_pair_only_for_used_fonts(tmp_path):
    header, _ = build(tmp_path, {"blocks": [{"type": "paragraph", "text": "가"}]})
    assert 'shadeColor="none"' in header and 'hangul="100"' in header


def test_ratio_narrows_the_characters(tmp_path):
    header, _ = build(tmp_path, one_cell({"text": "가", "ratio": 88}))
    assert 'hangul="88" latin="88"' in header


def test_bad_ratio_is_refused(tmp_path):
    with pytest.raises(ValueError, match="ratio"):
        build(tmp_path, one_cell({"text": "가", "ratio": 5}))


def test_blank_markup_is_shaded_and_underlined(tmp_path):
    header, section = build(tmp_path, one_cell({"text": "앞 ~~      ~~ 뒤", "size": 10.5, "blank": True}))
    assert 'shadeColor="#FFEFC2"' in header and '<hh:underline type="BOTTOM"' in header
    assert "~~" not in section


def test_teacher_blank_is_blue_bold_inside_the_shade(tmp_path):
    header, _ = build(tmp_path, one_cell({"text": "~~ 답 ~~", "blank": True, "mark_color": "#1D4ED8", "blank_fill": "#FFEFC2"}))
    blank = next(item for item in re.findall(r"<hh:charPr .*?</hh:charPr>", header) if "FFEFC2" in item)
    assert 'textColor="#1D4ED8"' in blank and "<hh:bold/>" in blank


def test_blank_markup_is_only_read_inside_cells(tmp_path):
    _, section = build(tmp_path, {"blocks": [{"type": "paragraph", "text": "~~그대로~~"}]})
    assert "~~그대로~~" in section


def test_paper_table_is_placed_on_the_paper_without_pushing_text(tmp_path):
    spec = one_cell({"text": "띠"}, paper={"x": 10, "y": 20, "width": 794, "wrap": "front"})
    _, section = build(tmp_path, spec)
    assert 'vertRelTo="PAPER" horzRelTo="PAPER"' in section and 'textWrap="IN_FRONT_OF_TEXT"' in section
    assert 'vertOffset="1500" horzOffset="750"' in section and 'treatAsChar="0"' in section
    assert f'<hp:sz width="{794 * 75}"' in section


def test_paper_table_needs_numbers(tmp_path):
    with pytest.raises(ValueError, match="paper"):
        build(tmp_path, one_cell({"text": "띠"}, paper={"x": 1}))


def test_shape_block_is_a_gradient_rectangle_behind_the_text(tmp_path):
    block = {"type": "shape", "shape": "rect", "w": 794, "h": 101, "corner": 0, "fill": "#1F3F7A",
             "fill_to": "#2E6DB4", "paper": {"x": 0, "y": 0}}
    _, section = build(tmp_path, {"page": "app", "blocks": [block]})
    assert 'textWrap="BEHIND_TEXT"' in section and "<hc:gradation" in section and 'ratio="0"' in section


def test_shape_block_needs_a_paper_place(tmp_path):
    with pytest.raises(ValueError, match="paper"):
        build(tmp_path, {"blocks": [{"type": "shape", "shape": "rect", "w": 5, "h": 5}]})


def test_gap_px_and_width_px_set_outer_margin_and_table_width(tmp_path):
    spec = {"page": "app", "margins": "app", "blocks": [
        {"type": "table", "widths": [1], "gap_px": [12, 4], "width_px": 488, "rows": [[{"text": "가"}]]}]}
    _, section = build(tmp_path, spec)
    assert 'top="900" bottom="300"' in section and f'<hp:sz width="{488 * 75}"' in section


def test_app_tables_have_no_table_inner_margin_and_no_paragraph_gap(tmp_path):
    spec = {"page": "app", "blocks": [{"type": "table", "widths": [1], "rows": [[{"text": "가"}]]}]}
    header, section = build(tmp_path, spec)
    assert '<hp:inMargin left="0" right="0" top="0" bottom="0"/>' in section
    assert '<hp:inMargin left="510"' not in section


def test_cell_pad_height_spacing_and_custom_edges(tmp_path):
    cell = {"text": "가", "pad_px": [10, 0, 2, 0], "height_px": 40, "spacing": 145,
            "edges": {"left": ["SOLID", 1.5, "#2E6DB4"], "bottom": ["DASH", 0.25, "#C9D3DF"]}}
    header, section = build(tmp_path, one_cell(cell))
    assert 'hasMargin="1"' in section and '<hp:cellMargin left="750" right="0" top="150" bottom="0"/>' in section
    assert 'height="3000"' in section and 'value="145"' in header
    assert '<hh:leftBorder type="SOLID" width="1.5 mm" color="#2E6DB4"/>' in header
    assert 'type="DASH" width="0.25 mm" color="#C9D3DF"' in header


@pytest.mark.parametrize("cell, message", [
    ({"text": "가", "pad_px": [1, 2]}, "pad_px"),
    ({"text": "가", "spacing": 5}, "spacing"),
    ({"text": "가", "height_px": 0}, "height_px"),
    ({"text": "가", "edges": {"middle": ["SOLID", 1, "#000000"]}}, "edges"),
    ({"text": "가", "font": "comic"}, "font"),
])
def test_bad_cell_values_are_refused(tmp_path, cell, message):
    with pytest.raises(ValueError, match=message):
        build(tmp_path, one_cell(cell))


def test_footer_blocks_go_into_the_footer_with_a_page_number_shape(tmp_path):
    badge = {"shape": "round", "w": 44, "h": 18, "fill": "#1F3F7A", "color": "#FFFFFF", "page_number": True}
    footer = [{"type": "table", "widths": [1, 1], "rows": [[{"text": "꼬리"}, {"content": [badge]}]]}]
    spec = {"page": "app", "footer": footer, "blocks": [{"type": "paragraph", "text": "본문"}]}
    _, section = build(tmp_path, spec)
    inside = re.search(r"<hp:footer .*?</hp:footer>", section, re.S).group(0)
    assert "꼬리" in inside and 'numType="PAGE"' in inside and 'numType="TOTAL_PAGE"' in inside


def test_app_page_has_app_margins_and_a_small_first_paragraph(tmp_path):
    _, section = build(tmp_path, {"page": "app", "margins": "app", "blocks": []})
    assert 'left="3317" right="3317"' in section and 'top="3000" bottom="3300"' in section


def test_sheet_page_uses_school_exam_paper_margins(tmp_path):
    # 원안지와 같다: 위 15mm, 아래 8mm, 좌·우 10mm, 머리말 0mm, 꼬리말 17mm, 제본 0mm. margins 값은 무시
    _, section = build(tmp_path, {"page": "sheet", "margins": "normal", "columns": 2,
                                  "blocks": [{"type": "paragraph", "text": "1. 문항"}]})
    margin = re.search(r"<hp:margin [^>]*/>", section).group(0)
    assert 'header="0" footer="4818" gutter="0"' in margin
    assert 'left="2834" right="2834"' in margin and 'top="4251" bottom="2267"' in margin


def test_other_pages_keep_their_margins(tmp_path):
    _, section = build(tmp_path, {"page": "compact", "margins": "narrow", "blocks": []})
    margin = re.search(r"<hp:margin [^>]*/>", section).group(0)
    assert 'left="4252" right="4252"' in margin and 'top="1984" bottom="1984"' in margin


def test_myeongjo_font_is_a_hancom_face_and_dots_stay_narrow(tmp_path):
    header, section = build(tmp_path, one_cell({"text": "5·16 → 가", "font": "myeongjo", "bold": True, "size": 12}))
    assert 'face="HY견명조"' in header and 'face="HY헤드라인M"' in header
    assert section.count("<hp:t>·</hp:t>") == 1 and section.count("<hp:t>→</hp:t>") == 1
    assert "<hp:t>5</hp:t>" in section and "<hp:t>16 </hp:t>" in section


def test_font_space_and_track_are_written_into_the_char_style(tmp_path):
    header, _ = build(tmp_path, one_cell({"text": "가", "font_space": True, "track": -3}))
    style = next(item for item in re.findall(r"<hh:charPr .*?</hh:charPr>", header) if 'useFontSpace="1"' in item)
    assert 'hangul="-3"' in style


def test_track_out_of_range_is_refused(tmp_path):
    with pytest.raises(ValueError, match="track"):
        build(tmp_path, one_cell({"text": "가", "track": 99}))


def test_marked_and_blank_styles_keep_ratio_font_and_track(tmp_path):
    cell = {"text": "**굵게** ~~빈칸~~", "font": "myeongjo", "ratio": 85, "track": -2, "font_space": True,
            "mark_color": "#1D4ED8", "blank": True}
    header, _ = build(tmp_path, one_cell(cell))
    styles = [item for item in re.findall(r"<hh:charPr .*?</hh:charPr>", header) if 'hangul="85"' in item]
    assert len(styles) >= 3 and all('hangul="-2"' in item and 'useFontSpace="1"' in item for item in styles)


# ---- ~~빈칸~~ 읽기는 앱 학습지(page "app")나 칸이 켠 경우만이다 (다른 스킬 출력은 이전과 같다)

def _preview(tmp_path, spec):
    out = tmp_path / "p.hwpx"
    make_hwpx.build_hwpx(spec, out)
    with zipfile.ZipFile(out) as package:
        return package.read("Preview/PrvText.txt").decode("utf-8")


@pytest.mark.parametrize("spec", [
    {"blocks": [{"type": "table", "rows": [["~~취소~~ 칸", "b"]]}]},
    {"blocks": [{"type": "table", "header": ["~~머리~~", "b"], "rows": [["가", "나"]]}]},
    {"blocks": [{"type": "table", "rows": [[{"text": "~~색 없음~~"}, "b"]]}]},
])
def test_strike_marks_stay_literal_outside_app_pages(tmp_path, spec):
    header, section = build(tmp_path, spec)
    assert "~~" in section and "FFEFC2" not in header
    assert "~~" in _preview(tmp_path, spec)


def test_app_page_reads_blank_marks_in_string_and_header_cells(tmp_path):
    spec = {"page": "app", "blocks": [{"type": "table", "header": ["~~머리~~", "b"], "rows": [["~~문자열~~ 칸", "~~둘~~"]]}]}
    header, section = build(tmp_path, spec)
    assert "~~" not in section and 'shadeColor="#FFEFC2"' in header
    assert "~~" not in _preview(tmp_path, spec)


def test_preview_text_shows_blanks_as_brackets(tmp_path):
    spec = {"page": "app", "blocks": [{"type": "table", "rows": [["앞 ~~      ~~ 뒤"]]}]}
    preview = _preview(tmp_path, spec)
    assert "~~" not in preview and "(" in preview


# ---- 도형 값 검사

@pytest.mark.parametrize("key,value", [
    ("fill", "red"), ("fill_to", '#12"34'), ("line", "#12345"), ("color", "blue"),
    ("fill_angle", 400), ("fill_angle", 1.5), ("pad_px", "큼"), ("ml_px", -3), ("mr_px", True), ("line_px", 0),
])
def test_bad_shape_values_are_refused_in_korean(tmp_path, key, value):
    shape = {"shape": "round", "w": 20, "h": 10, "fill": "#E3EDF9", key: value}
    with pytest.raises(ValueError, match=key):
        build(tmp_path, one_cell({"content": [shape]}))


def test_good_shape_values_are_kept(tmp_path):
    shape = {"shape": "rect", "w": 20, "h": 10, "fill": "#e3edf9", "fill_to": "#2E6DB4", "fill_angle": 80, "line": "#1F3F7A",
             "line_px": 2, "pad_px": 3, "ml_px": 1, "mr_px": 2}
    _, section = build(tmp_path, one_cell({"content": [shape]}))
    assert 'faceColor' not in section and 'angle="80"' in section
