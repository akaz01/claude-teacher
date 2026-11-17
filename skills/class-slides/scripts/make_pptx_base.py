"""make_pptx.py의 바탕: 테마 5종, 글자 측정, 슬라이드를 만드는 Deck. 교사 템플릿이면 템플릿 색과 쪽 번호 자리를 읽는다."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.exc import PackageNotFoundError
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Emu, Inches, Pt

from make_pptx_color import backdrop_at, restyle_for_template, template_background, template_palette, text_color_on
from pptx_safety import check_pptx

FONT = "맑은 고딕"
OUTPUT_SUFFIX = ".pptx"
EMU_PER_INCH = 914400
SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
BLANK_LAYOUT = 6
LINE_SPACING = 1.4
SPACE_UNITS = 0.3                       # 띄어쓰기 한 칸의 폭 (전각 1 기준)
WRAP_SLACK = 0.92                       # 한 줄 글이 상자 끝까지 차지 않도록 줄 길이의 이만큼만 쓴다고 본다
NUMBER_SIZE = Inches(0.3)               # 쪽 번호 상자의 높이
COMPARE_MIN_RATIO = 0.45                # 비교 상자의 최소 높이 (본문 영역 대비)
TABLE_FONT_OFFSET = 4                   # 표 글자는 본문보다 이만큼 작게
TABLE_MIN_FONT = 16
TABLE_CELL_PAD = Inches(0.35)           # 표 칸 좌우 여백 합 + 여유
MIN_CHOICE_H = Inches(0.45)             # 퀴즈 선지 상자의 최소 높이
MARGIN_X_RATIO = 0.06                   # 좌우 여백 (슬라이드 너비 대비)
TOP_RATIO = 0.08                        # 제목 영역 시작 위치 (슬라이드 높이 대비)
TITLE_H_RATIO = 0.13                    # 제목 영역 높이
TITLE_GAP_RATIO = 0.04                  # 제목과 본문 사이 간격
BODY_BOTTOM_RATIO = 0.9                 # 본문 아래쪽 끝
CORNER_ADJUST = 0.12                    # 둥근 모서리 정도
COMPARE_ITEM_RATIO = 0.92               # 비교·선지·단계 글자 크기 (본문 대비)
STEP_CIRCLE_RATIO = 0.9                 # 활동 단계 번호 원 크기 (줄 높이 대비)
QUIZ_SHORT_CHOICE_UNITS = 14            # 이 길이 이하의 선지만 2단으로 배치
SECTION_LAYOUT = "secHead"              # 템플릿 레이아웃 종류: 소주제 표지
SUBTITLE_KINDS = (PP_PLACEHOLDER.SUBTITLE, PP_PLACEHOLDER.BODY)


@dataclass(frozen=True)
class Theme:
    bg: str
    fg: str
    head: str
    muted: str
    accent: str
    accent2: str
    panel: str
    on_accent: str
    rule: str
    deco1: str
    deco2: str
    cover: int
    title: int
    body: int
    small: int
    rounded: bool
    deco: str


THEMES = {
    "basic": Theme("FFFFFF", "232A35", "232A35", "6A7380", "2E62A6", "C2563A", "EEF2F7", "FFFFFF", "D3DBE6",
                   "2E62A6", "EEF2F7", 40, 30, 24, 16, False, "bar"),
    "elem": Theme("FFF7E3", "3A2D27", "3A2D27", "8A7666", "F07A2B", "2E9C8F", "FFFFFF", "FFFFFF", "F3DDB5",
                  "FFE1B8", "CDEDE7", 48, 36, 32, 20, True, "circles"),
    "sci": Theme("F5F9FD", "12233D", "0E3A6E", "5E7189", "1D6FD8", "0E9A93", "FFFFFF", "FFFFFF", "C9D9EC",
                 "DCE8F5", "C9D9EC", 40, 30, 24, 16, False, "grid"),
    "hum": Theme("FBF6EF", "3B2F27", "6E2F1E", "85766A", "A64B2A", "5F7351", "F3EAE0", "FFFFFF", "D8C6B4",
                 "D8C6B4", "F3EAE0", 40, 30, 24, 16, False, "frame"),
    "board": Theme("1F3D31", "F5F3EA", "FFFFFF", "B8C9BE", "FFD45C", "8FD3FF", "2A4C3E", "1F3D31", "5D7D6E",
                   "6B4A2F", "2A4C3E", 48, 36, 28, 18, False, "board"),
}


# ---------------------------------------------------------------- 글자 측정과 나누기

def text_units(text: str) -> float:
    """글자 폭을 전각 1 기준으로 어림한다. 맑은 고딕을 재어 보니 한글 1.0, 영문·숫자 약 0.5, 띄어쓰기 약 0.3이다."""
    return sum(SPACE_UNITS if ch == " " else 0.55 if ord(ch) < 128 else 1.0 for ch in text)


def est_lines(text: str, width: int, size: float) -> int:
    per_line = max(1, int((width / EMU_PER_INCH * 72) / size * WRAP_SLACK))
    return max(1, math.ceil(text_units(text) / per_line))


def line_h(size: float) -> int:
    return int(size * LINE_SPACING / 72 * EMU_PER_INCH)


def plain(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", str(text))


def paginate(heights: list[int], capacity: int) -> list[list[int]]:
    pages: list[list[int]] = [[]]
    used = 0
    for index, height in enumerate(heights):
        if pages[-1] and used + height > capacity:
            pages.append([])
            used = 0
        pages[-1].append(index)
        used += height
    return pages


def split_bold(text: str) -> list[tuple[str, bool]]:
    return [(part, i % 2 == 1) for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", str(text))) if part]


# ---------------------------------------------------------------- 덱

class Deck:
    def __init__(self, theme: Theme, template: str | None, student: bool = False):
        self.theme = theme
        self.template = bool(template)
        self.student = student              # 학생용 사본: 발표자 노트(정답이 들어 있음)를 쓰지 않는다
        self.warnings: list[str] = []
        if template:
            check_pptx(template, "템플릿")
            try:
                self.prs = Presentation(template)
            except (PackageNotFoundError, OSError, KeyError, ValueError) as error:
                raise ValueError(f"템플릿을 열 수 없음: {template} (.pptx 파일인지 확인해 주세요)") from error
            _clear_slides(self.prs)
            self.layout = _title_only_layout(self.prs)
            self.cover_layout = _title_slide_layout(self.prs)
            self.section_layout = _section_layout(self.prs) or self.cover_layout
            self.theme = restyle_for_template(theme, self.prs)      # 템플릿의 테마 색을 강조색으로
        else:
            self.prs = Presentation()
            self.prs.slide_width, self.prs.slide_height = SLIDE_W, SLIDE_H
            self.layout = self.prs.slide_layouts[BLANK_LAYOUT]
            self.cover_layout = self.section_layout = None
        self.W, self.H = self.prs.slide_width, self.prs.slide_height
        self.mx = int(self.W * MARGIN_X_RATIO)
        self.top = int(self.H * TOP_RATIO)
        self.title_h = int(self.H * TITLE_H_RATIO)
        self.body_top = self.top + self.title_h + int(self.H * TITLE_GAP_RATIO)
        self.body_bottom = int(self.H * BODY_BOTTOM_RATIO)
        self.body_w = self.W - 2 * self.mx
        self.count = 0
        self.number_box = self._number_box()

    def _number_box(self) -> tuple[int, int, int, int, str]:
        """쪽 번호 상자의 (x, y, w, h)와 글자색. 템플릿의 띠 같은 바탕 위에서도 보이는 색과 자리를 고른다."""
        w, h = Inches(1), NUMBER_SIZE
        x = self.W - self.mx - w
        default_y = self.H - Inches(0.55)
        if not self.template:
            return x, default_y, w, h, self.theme.muted
        palette = template_palette(self.prs)
        layers = [self.prs.slide_master, self.layout]
        background = template_background(self.prs, palette)

        def colors_at(y: int) -> set[str]:
            return {backdrop_at(layers, px, py, background, palette) for px in (x, x + w) for py in (y, y + h)}
        for y in (default_y, self.H - Inches(0.08) - h, default_y - Inches(0.35)):
            if len(colors_at(y)) == 1:
                return x, y, w, h, text_color_on(next(iter(colors_at(y))), self.theme.muted)
        return x, default_y, w, h, text_color_on(backdrop_at(layers, x + w // 2, default_y + h // 2, background, palette),
                                                 self.theme.muted)

    @property
    def body_h(self) -> int:
        return self.body_bottom - self.body_top

    def fit_font(self, texts: list[str], width: int, height: int, size: float, floor: float, what: str) -> float:
        """모든 글이 칸(EMU)에 들어가는 가장 큰 글자 크기. floor까지 줄여도 넘치면 경고를 남긴다."""
        def over(candidate: float) -> bool:
            return any(est_lines(plain(text), width, candidate) * line_h(candidate) > height for text in texts)
        while size > floor and over(size):
            size -= 1
        if over(size):
            self.warnings.append(f"{self.count}쪽 {what} 글이 많아 {floor:g}pt까지 줄여도 넘칠 수 있음")
        return size

    # --- 글자 ---

    def font(self, run, size: float, bold: bool = False, color: str | None = None) -> None:
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(color or self.theme.fg)
        r_pr = run._r.get_or_add_rPr()
        # 언어를 한국어로 지정해야 PowerPoint가 어절 단위로 줄을 바꾼다 (영어로 두면 글자 단위로 잘림)
        r_pr.set("lang", "ko-KR")
        r_pr.set("altLang", "en-US")
        if self.template:
            return      # 글꼴은 양식 테마의 것을 이어받는다 (맑은 고딕을 박지 않는다)
        run.font.name = FONT
        latin = r_pr.find(qn("a:latin"))
        for tag in ("a:cs", "a:ea"):
            if r_pr.find(qn(tag)) is None:
                element = OxmlElement(tag)
                element.set("typeface", FONT)
                latin.addnext(element)

    @staticmethod
    def inherit_runs(paragraph, text: str) -> None:
        """글만 바꾼다: 크기·굵기·색·글꼴은 양식(자리 표시자)의 모양을 이어받는다. 한국어 지정만 한다."""
        for part, is_bold in split_bold(text):
            run = paragraph.add_run()
            run.text = part
            run._r.get_or_add_rPr().set("lang", "ko-KR")
            if is_bold:
                run.font.bold = True

    def runs(self, paragraph, text: str, size: float, bold: bool = False, color: str | None = None,
             bold_color: str | None = None) -> None:
        for part, is_bold in split_bold(text):
            run = paragraph.add_run()
            run.text = part
            self.font(run, size, bold or is_bold, (bold_color or color) if is_bold else color)

    def textbox(self, slide, x: int, y: int, w: int, h: int, anchor=MSO_ANCHOR.TOP):
        return self.plain_frame(slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h)), anchor)

    @staticmethod
    def plain_frame(shape, anchor=MSO_ANCHOR.TOP):
        """도형의 글 틀을 여백 없는 고정 크기 틀로 맞춘다."""
        frame = shape.text_frame
        frame.word_wrap = True
        frame.auto_size = MSO_AUTO_SIZE.NONE
        frame.vertical_anchor = anchor
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        return frame

    @staticmethod
    def paragraphs(frame, align=PP_ALIGN.CENTER):
        """다음 문단을 차례로 돌려주는 함수. 문단은 기본으로 가운데 정렬이다 (make_deck.py와 같음)."""
        first = [True]

        def next_paragraph():
            if first[0]:
                first[0] = False
                paragraph = frame.paragraphs[0]
            else:
                paragraph = frame.add_paragraph()
            paragraph.alignment = align
            return paragraph
        return next_paragraph

    # --- 도형 ---

    def box(self, slide, x: int, y: int, w: int, h: int, fill: str | None = None, line: str | None = None,
            line_w: float = 1.5, dash: bool = False, shape=None):
        kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if self.theme.rounded else MSO_SHAPE.RECTANGLE)
        item = slide.shapes.add_shape(kind, Emu(x), Emu(y), Emu(w), Emu(h))
        if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            item.adjustments[0] = CORNER_ADJUST
        if fill:
            item.fill.solid()
            item.fill.fore_color.rgb = RGBColor.from_string(fill)
        else:
            item.fill.background()
        if line:
            item.line.color.rgb = RGBColor.from_string(line)
            item.line.width = Pt(line_w)
            if dash:
                item.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        else:
            item.line.fill.background()
        item.shadow.inherit = False
        return item

    def rule(self, slide, x1: int, y: int, x2: int, color: str, width: float = 1.5, dash: bool = False) -> None:
        line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(x1), Emu(y), Emu(x2), Emu(y))
        line.line.color.rgb = RGBColor.from_string(color)
        line.line.width = Pt(width)
        if dash:
            line.line.dash_style = MSO_LINE_DASH_STYLE.DASH

    # --- 슬라이드 ---

    def new_slide(self, title: str | None = None, notes: str | None = None, kind: str = "body"):
        slide = self.prs.slides.add_slide(self.layout_for(kind))
        self.count += 1
        if not self.template:
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = RGBColor.from_string(self.theme.bg)
            self._decorate(slide, kind)
        if title is not None:
            self._title(slide, title)
        elif self.template and slide.shapes.title is not None:
            element = slide.shapes.title._element
            element.getparent().remove(element)
        if notes and not self.student:
            slide.notes_slide.notes_text_frame.text = notes
        if kind == "body":
            x, y, w, h, color = self.number_box
            paragraph = self.textbox(slide, x, y, w, h, MSO_ANCHOR.MIDDLE).paragraphs[0]
            paragraph.alignment = PP_ALIGN.RIGHT        # 쪽 번호는 모서리에 붙인다
            self.runs(paragraph, str(self.count), 14, True, color)
        return slide

    def layout_for(self, kind: str):
        """표지·소주제 장은 템플릿의 제목 장·구역 머리 레이아웃을 쓴다. 없으면 제목만 있는 레이아웃이다."""
        if self.template and kind == "cover" and self.cover_layout is not None:
            return self.cover_layout
        if self.template and kind == "section" and self.section_layout is not None:
            return self.section_layout
        return self.layout

    def uses_title_layout(self, kind: str) -> bool:
        return self.layout_for(kind) is not self.layout

    def fill_subtitle(self, slide, lines: list[str], size: float) -> None:
        """부제 자리(없으면 제목 아래 글상자)에 글을 넣는다. 남는 빈 자리 표시자는 지운다."""
        lines = [line for line in lines if line]
        title = slide.shapes.title
        spots = [ph for ph in slide.placeholders if ph.placeholder_format.type in SUBTITLE_KINDS]
        for extra in spots[1:] if lines else spots:
            extra._element.getparent().remove(extra._element)
        if not lines:
            return
        if spots:
            frame = spots[0].text_frame
            frame.clear()
            for index, line in enumerate(lines):
                self.inherit_runs(frame.paragraphs[0] if index == 0 else frame.add_paragraph(), line)
            return
        top = (title.top + title.height + Inches(0.1)) if title is not None else int(self.H * 0.6)
        frame = self.textbox(slide, self.mx, top, self.body_w, line_h(size) * len(lines))
        next_paragraph = self.paragraphs(frame)
        for line in lines:
            self.runs(next_paragraph(), line, size, color=self.theme.muted)

    def _decorate(self, slide, kind: str) -> None:
        t, W, H = self.theme, self.W, self.H
        if t.deco == "bar" and kind == "cover":
            self.box(slide, self.mx, 0, Inches(0.9), Inches(0.16), fill=t.deco1)
        elif t.deco == "circles":
            # 모든 도형은 슬라이드 테두리 안에 둔다: 제목·본문 바깥 여백(오른쪽 위, 왼쪽 아래)에 작은 원
            size, gap = int(H * 0.07), int(H * 0.03)
            self.box(slide, W - size - gap, int(H * 0.02), size, size, fill=t.deco1, shape=MSO_SHAPE.OVAL)
            self.box(slide, gap, H - size - gap, size, size, fill=t.deco2, shape=MSO_SHAPE.OVAL)
        elif t.deco == "grid":
            step = Inches(0.4)
            for x in range(step, W, step):
                line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(x), 0, Emu(x), Emu(H))
                line.line.color.rgb, line.line.width = RGBColor.from_string(t.deco1), Pt(0.5)
            for y in range(step, H, step):
                self.rule(slide, 0, y, W, t.deco1, 0.5)
        elif t.deco == "frame":
            inset = Inches(0.18)
            self.box(slide, inset, inset, W - 2 * inset, H - 2 * inset, line=t.deco1, line_w=1)
        elif t.deco == "board":
            self.box(slide, 0, 0, W, H, line=t.deco1, line_w=16)

    def _title(self, slide, text: str) -> None:
        t = self.theme
        if self.template and slide.shapes.title is not None:
            frame = slide.shapes.title.text_frame
            frame.clear()
            self.inherit_runs(frame.paragraphs[0], text)     # 제목은 양식의 크기·굵기·색·글꼴을 그대로 따른다
            return
        frame = self.textbox(slide, self.mx, self.top, self.body_w, self.title_h, MSO_ANCHOR.BOTTOM)
        paragraph = frame.paragraphs[0]
        paragraph.alignment = PP_ALIGN.CENTER
        if t.deco == "grid":
            self.runs(paragraph, f"{self.count:02d}   ", t.small, True, t.accent)
        self.runs(paragraph, text, t.title, True, t.head)
        under = self.top + self.title_h + int(self.H * 0.015)
        if t.deco == "bar":
            self.rule(slide, self.mx, under, self.W - self.mx, t.rule, 1.5)
        elif t.deco == "frame":
            self.box(slide, (self.W - Inches(0.8)) // 2, under, Inches(0.8), Inches(0.04), fill=t.accent)
        elif t.deco == "board":
            self.rule(slide, self.mx, under, self.W - self.mx, t.rule, 2, dash=True)


def _clear_slides(prs) -> None:
    id_list = prs.slides._sldIdLst
    for slide_id in list(id_list):
        prs.part.drop_rel(slide_id.rId)
        id_list.remove(slide_id)


def _has_title_placeholder(layout, kinds) -> bool:
    return any(ph.placeholder_format.type in kinds for ph in layout.placeholders)


def _title_slide_layout(prs):
    """템플릿의 표지용(가운데 제목) 레이아웃. 없으면 None."""
    for layout in prs.slide_layouts:
        if _has_title_placeholder(layout, (PP_PLACEHOLDER.CENTER_TITLE,)):
            return layout
    return None


def _section_layout(prs):
    """템플릿의 구역 머리(소주제) 레이아웃. 없으면 None."""
    for layout in prs.slide_layouts:
        if layout._element.get("type") == SECTION_LAYOUT and _has_title_placeholder(
                layout, (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)):
            return layout
    return None


def _title_only_layout(prs):
    def score(layout):
        kinds = [ph.placeholder_format.type for ph in layout.placeholders]
        has_title = any(str(k).startswith(("TITLE", "CENTER_TITLE")) for k in kinds)
        return (0 if has_title else 1, len(kinds))
    return min(prs.slide_layouts, key=score)

