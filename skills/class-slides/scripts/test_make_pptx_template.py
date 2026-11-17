"""교사 템플릿 경로(make_pptx.py)의 설명 장 띠·도식, 정답 노트, 템플릿 색, 쪽 번호, 정렬 시험."""
import copy
import re

import pytest
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Inches

import make_pptx
from make_pptx import THEMES, build_pptx

FLOW = {"type": "flow", "title": "과정", "steps": [{"head": "준비", "text": "도구를 모은다"},
                                                  {"head": "측정", "text": "길이를 잰다"},
                                                  {"head": "기록", "text": "표에 적는다"}], "key": "순서를 지키면 오차가 줄어든다"}
CARDS = {"type": "cards", "title": "세 가지", "cards": [{"head": "가", "text": "첫째 설명"}, {"head": "나", "text": "둘째 설명"}],
         "key": "셋을 기억한다"}
EXPLAIN_WITH_KEY = [
    {"type": "content", "title": "설명", "items": ["하나", "둘", "셋"], "key": "핵심 한 줄"},
    {"type": "compare", "title": "비교", "left": {"heading": "가", "items": ["a"]},
     "right": {"heading": "나", "items": ["b"]}, "key": "핵심 한 줄"},
    {"type": "table", "title": "표", "header": ["구분", "내용"], "rows": [["가", "나"]], "key": "핵심 한 줄"},
    {"type": "figure", "title": "그림", "caption": "교과서 32쪽", "key": "핵심 한 줄"},
    FLOW, CARDS,
]


def build(tmp_path, slides, **spec):
    out = tmp_path / "out.pptx"
    warnings = build_pptx({"theme": "basic", "slides": slides, **spec}, out)
    return Presentation(out), warnings


def shape_with(slide, text):
    return next((s for s in slide.shapes if s.has_text_frame and s.text_frame.text == text), None)


def fill_of(shape):
    return str(shape.fill.fore_color.rgb)


def make_template(path, accent=None, band=None, background=None):
    """시험용 템플릿: 테마 색, 마스터 아래 띠, 마스터 배경을 고른다."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    master = prs.slide_master
    if accent:
        theme = master.part.part_related_by(RT.THEME)
        theme._blob = re.sub(rb'(<a:accent1>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}', rb"\g<1>" + accent.encode(), theme.blob)
    if background:
        master.background.fill.solid()
        master.background.fill.fore_color.rgb = RGBColor.from_string(background)
    if band:
        scratch = prs.slides.add_slide(prs.slide_layouts[6])
        shape = scratch.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(7.0), prs.slide_width, Inches(0.5))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(band)
        shape.line.fill.background()
        tree = master.shapes._spTree
        tree.insert(len(tree) - 1, copy.deepcopy(shape._element))
        prs.part.drop_rel(prs.slides._sldIdLst[-1].rId)
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[-1])
    prs.save(str(path))
    return str(path)


@pytest.mark.parametrize("slide", EXPLAIN_WITH_KEY, ids=lambda s: s["type"])
def test_explain_slides_get_a_key_band_below_the_body(tmp_path, slide):
    prs, _ = build(tmp_path, [slide])
    band = shape_with(prs.slides[0], slide["key"])
    assert band is not None
    assert band.top + band.height <= prs.slide_height * 0.9 + 1000
    others = [s for s in prs.slides[0].shapes if s.shape_id != band.shape_id and s.top + s.height > band.top + 1000
              and s.height > Inches(0.05) and s.top < band.top + band.height and s.has_text_frame and s.text_frame.text
              and not re.fullmatch(r"\d+", s.text_frame.text)]
    assert others == []


def test_key_band_uses_accent_fill_and_contrast_text(tmp_path):
    prs, _ = build(tmp_path, [EXPLAIN_WITH_KEY[0]], theme="board")
    band = shape_with(prs.slides[0], "핵심 한 줄")
    assert fill_of(band) == THEMES["board"].accent
    assert str(band.text_frame.paragraphs[0].runs[0].font.color.rgb) == THEMES["board"].on_accent


def test_flow_draws_one_chevron_per_step_with_text(tmp_path):
    prs, _ = build(tmp_path, [FLOW])
    chevrons = [s for s in prs.slides[0].shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE and s.auto_shape_type == MSO_SHAPE.CHEVRON]
    assert len(chevrons) == 3
    text = "\n".join(s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame)
    for word in ("준비", "도구를 모은다", "길이를 잰다", "표에 적는다"):
        assert word in text


def test_cards_show_every_head_and_text(tmp_path):
    prs, _ = build(tmp_path, [CARDS])
    text = "\n".join(s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame)
    for word in ("가", "첫째 설명", "둘째 설명"):
        assert word in text


def test_figure_callouts_become_side_cards(tmp_path):
    prs, _ = build(tmp_path, [{"type": "figure", "title": "그림", "callouts": ["왼쪽 설명", {"text": "점 설명", "x": 0.5, "y": 0.2}]}])
    text = "\n".join(s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame)
    assert "왼쪽 설명" in text and "점 설명" in text


def test_deck_only_slide_type_error_names_a_substitute(tmp_path):
    with pytest.raises(ValueError) as caught:
        build(tmp_path, [{"type": "keywords", "words": []}])
    message = str(caught.value)
    assert "keywords" in message and "make_deck" in message and "table" in message


def test_flow_with_too_many_steps_is_rejected_clearly(tmp_path):
    steps = [{"head": str(n), "text": "가"} for n in range(9)]
    with pytest.raises(ValueError) as caught:
        build(tmp_path, [{"type": "flow", "title": "t", "steps": steps}])
    assert "1번" in str(caught.value) or "1번 슬라이드" in str(caught.value)


def test_quiz_answer_slide_notes_carry_answer_and_next_action(tmp_path):
    quiz = {"type": "quiz", "question": "문제", "choices": ["가", "나", "다"], "answer": 1, "reveal": True, "notes": "발문"}
    prs, _ = build(tmp_path, [quiz])
    notes = prs.slides[1].notes_slide.notes_text_frame.text
    assert "정답" in notes and "나" in notes and "다음" in notes


def test_quiz_answer_slide_uses_reveal_notes_when_given(tmp_path):
    quiz = {"type": "quiz", "question": "문제", "choices": ["가", "나"], "answer": 0, "reveal": True,
            "reveal_notes": "절반 넘게 틀리면 앞 설명으로 돌아간다."}
    prs, _ = build(tmp_path, [quiz])
    notes = prs.slides[1].notes_slide.notes_text_frame.text
    assert "앞 설명으로 돌아간다" in notes and "정답" in notes


def table_header_fill(prs):
    table = next(s for s in prs.slides[0].shapes if s.has_table).table
    return str(table.cell(0, 0).fill.fore_color.rgb)


TABLE = {"type": "table", "title": "표", "header": ["가", "나"], "rows": [["x", "y"]]}


def test_template_theme_color_becomes_the_accent(tmp_path):
    template = make_template(tmp_path / "t.pptx", accent="7A1F5C")
    prs, _ = build(tmp_path, [TABLE], template=template)
    assert table_header_fill(prs) == "7A1F5C"


def test_unreadable_template_theme_falls_back_to_the_default_accent(tmp_path):
    prs = Presentation(make_template(tmp_path / "t.pptx"))
    prs.slide_master.part.part_related_by(RT.THEME)._blob = b"not xml"
    broken = tmp_path / "broken.pptx"
    prs.save(str(broken))
    out, _ = build(tmp_path, [TABLE], template=str(broken))
    assert table_header_fill(out) == THEMES["basic"].accent


def test_broken_theme_part_does_not_stop_the_build(tmp_path):
    from make_pptx_color import template_palette
    template = make_template(tmp_path / "t.pptx")
    prs = Presentation(template)
    prs.slide_master.part.part_related_by(RT.THEME)._blob = b"not xml"
    assert template_palette(prs) == {}


def test_too_light_template_accent_is_skipped_for_a_readable_one(tmp_path):
    template = make_template(tmp_path / "t.pptx", accent="FFF3B0")
    prs, _ = build(tmp_path, [TABLE], template=template)
    assert table_header_fill(prs) != "FFF3B0"


def page_number_run(prs):
    slide = prs.slides[0]
    box = next(s for s in slide.shapes if s.has_text_frame and s.text_frame.text == "1")
    return box, box.text_frame.paragraphs[0].runs[0]


def luminance(hex_color):
    from make_pptx_color import luminance as lum
    return lum(hex_color)


def test_page_number_is_light_over_a_dark_template_band(tmp_path):
    template = make_template(tmp_path / "t.pptx", band="1F3B57")
    prs, _ = build(tmp_path, [{"type": "content", "title": "t", "items": ["a"]}], template=template)
    box, run = page_number_run(prs)
    assert luminance(str(run.font.color.rgb)) > 0.6
    assert box.top >= Inches(7.0) or box.top + box.height <= Inches(7.0)


def test_page_number_is_dark_over_a_light_template(tmp_path):
    template = make_template(tmp_path / "t.pptx", background="FFF8EC")
    prs, _ = build(tmp_path, [{"type": "content", "title": "t", "items": ["a"]}], template=template)
    _, run = page_number_run(prs)
    assert luminance(str(run.font.color.rgb)) < 0.3


def test_page_number_is_light_on_a_dark_theme_without_template(tmp_path):
    prs, _ = build(tmp_path, [{"type": "content", "title": "t", "items": ["a"]}], theme="board")
    _, run = page_number_run(prs)
    assert luminance(str(run.font.color.rgb)) > 0.4


LISTS = [
    {"type": "goals", "items": ["목표 하나", "목표 둘"]},
    {"type": "content", "title": "설명", "items": ["항목", {"text": "항목2", "sub": ["하위"]}]},
    {"type": "compare", "title": "비교", "left": {"heading": "가", "items": ["a"]}, "right": {"heading": "나", "items": ["b"]}},
    {"type": "activity", "title": "활동", "time": "5분", "group": "짝", "materials": "연필", "steps": ["하나", "둘"]},
    {"type": "quiz", "question": "문제", "choices": ["가", "나", "다"], "answer": 0},
    {"type": "summary", "items": ["정리 하나"]},
    {"type": "section", "title": "소주제", "subtitle": "부제"},
    {"type": "cover", "title": "표지", "meta": "중1"},
]


@pytest.mark.parametrize("slide", LISTS, ids=lambda s: s["type"])
def test_lists_and_texts_are_centered_like_make_deck(tmp_path, slide):
    prs, _ = build(tmp_path, [slide])
    for shape in prs.slides[0].shapes:
        if not shape.has_text_frame or not shape.text_frame.text or re.fullmatch(r"\d+", shape.text_frame.text):
            continue
        for paragraph in shape.text_frame.paragraphs:
            if paragraph.runs:
                assert paragraph.alignment == PP_ALIGN.CENTER, (shape.text_frame.text, paragraph.alignment)


def test_table_cells_are_centered(tmp_path):
    prs, _ = build(tmp_path, [TABLE])
    table = next(s for s in prs.slides[0].shapes if s.has_table).table
    assert all(table.cell(r, c).text_frame.paragraphs[0].alignment == PP_ALIGN.CENTER for r in range(2) for c in range(2))
