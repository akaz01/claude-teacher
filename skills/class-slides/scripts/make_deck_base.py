"""수업 PPT 폼 생성기의 바탕: 글자 폭·줄 수 어림, 글자 크기 맞춤, 슬라이드를 그리는 Deck, 줄 배치 계산.

make_deck.py(장 그리기와 명령줄)가 가져다 쓴다. 입력 형식과 사용법은 make_deck.py 머리말에 있다.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

from slide_check import SHORT_TAIL_RATIO

FONT = "맑은 고딕"
SLIDE_W, SLIDE_H = 13.333, 7.5
BLANK_LAYOUT = 6
MARGIN = 0.75
BODY_W = SLIDE_W - 2 * MARGIN
BODY_TOP, BODY_BOTTOM, KEY_TOP, KEY_H = 1.85, 6.75, 6.0, 0.72
GAP = 0.3
ROW_GAP = 0.18
MIN_FONT = 14                   # 이보다 작게는 줄이지 않는다
CLASSROOM_FONT = 18             # 이보다 작아지면 경고한다 (visual-design.md 5절: 카드 본문 20~24, 사진 설명 16 이상)
SPLIT_FONT = 20                 # 설명 행은 글자가 이보다 작아질 만큼 담지 않고 다음 장으로 나눈다
SPACE_UNITS = 0.3               # 띄어쓰기 한 칸의 폭 (전각 1 기준)
WRAP_SLACK = 0.92               # 한 줄 글이 상자 끝까지 차지 않도록 줄 길이의 이만큼만 쓴다고 본다
SHORT_TAIL = SHORT_TAIL_RATIO   # 마지막 줄이 한 줄의 이만큼도 안 차면 "몇 글자만 넘어간" 줄로 본다 (모든 검사가 같은 값)
MAX_TRIM = 0.15                 # 그 줄을 없애려고 글자를 줄이는 한도
BASE_ROW_FONT = 28              # 설명 행의 시작 글자 크기
MAX_ROW_SCALE = 2.3             # 행이 필요한 높이의 이 배수까지만 늘어난다
LINE_RATIO = 1.3
PAD = 0.14
VPAD = 0.05
BADGE = 0.8
CHEVRON_INSET = 1.0
MAX_ROWS = 5
MAX_CHOICES = 5
CHOICE_FONT = 28
CHOICE_MARKS = "①②③④⑤"
ANSWER_MARK = "✔"
CONTINUED = " (계속)"
WHITE, INK, MUTED = "FFFFFF", "262B33", "6B7380"
PALETTES = {
    "국어": ("8C3A4F", "F9EEF1"), "영어": ("0F6E7A", "E6F4F5"), "수학": ("2B4FA2", "EBF0FA"),
    "사회": ("B25A12", "FCF1E6"), "과학": ("1F7A4D", "E7F5EE"),
}
DEFAULT_PALETTE = ("33415C", "EEF1F6")
BOLD_MARK = re.compile(r"\*\*(.+?)\*\*")


def split_marks(text: str) -> list[tuple[str, bool]]:
    """`**굵게**`를 (글, 굵게 여부) 조각으로 나눈다. 짝이 없는 별표는 지운다."""
    pieces = [(part.replace("**", ""), index % 2 == 1) for index, part in enumerate(BOLD_MARK.split(text))]
    return [piece for piece in pieces if piece[0]]


def plain(text: str) -> str:
    return "".join(piece for piece, _ in split_marks(text))


def text_units(text: str) -> float:
    """글자 폭을 전각 1 기준으로 어림한다. 맑은 고딕을 재어 보니 한글 1.0, 영문·숫자 약 0.5, 띄어쓰기 약 0.3이다."""
    return sum(SPACE_UNITS if ch == " " else 0.55 if ord(ch) < 128 else 1.0 for ch in text)


def line_count(text: str, width: float, size: float) -> int:
    """칸(인치)에서 글이 몇 줄이 되는지 어림한다. 줄 끝의 어절 남김을 생각해 폭을 조금 덜 쓴다."""
    per_line = max(1.0, (width - 2 * PAD) / (size / 72) * WRAP_SLACK)
    return sum(math.ceil(max(text_units(plain(part)), 1) / per_line) for part in text.split("\n"))


def fits(text: str, width: float, height: float, size: float) -> bool:
    return line_count(text, width, size) * size * LINE_RATIO / 72 <= height - 2 * VPAD


def has_short_tail(text: str, width: float, size: float) -> bool:
    """두 줄 이상인 문단 중 마지막 줄에 몇 글자만 남는 것이 있는가."""
    per_line = max(1.0, (width - 2 * PAD) / (size / 72) * WRAP_SLACK)
    for part in text.split("\n"):
        lines = math.ceil(max(text_units(plain(part)), 1) / per_line)
        if lines > 1 and text_units(plain(part)) / per_line - (lines - 1) < SHORT_TAIL:
            return True
    return False


def fit_size(text: str, width: float, height: float, size: float) -> float:
    """칸(인치)에 들어가는 글자 크기를 돌려준다."""
    while size > MIN_FONT and not fits(text, width, height, size):
        size -= 1
    return size


def tidy_size(text: str, width: float, height: float, size: float) -> float:
    """fit_size에 더해, 끝 줄에 몇 글자만 남으면 조금 줄여 그 줄을 없앤다 (줄이는 한도는 MAX_TRIM)."""
    size = fit_size(text, width, height, size)
    if not has_short_tail(text, width, size):
        return size
    for smaller in range(int(size) - 1, max(MIN_FONT, math.floor(size * (1 - MAX_TRIM))) - 1, -1):
        if not has_short_tail(text, width, smaller):
            return smaller
    return size


def common_size(texts: list[str], width: float, height: float, size: float) -> float:
    """같은 역할의 칸들이 함께 쓸 글자 크기를 돌려준다."""
    return min(tidy_size(text, width, height, size) for text in texts)


def item_text(item: str | dict) -> str:
    """목록 항목을 글로 바꾼다. 하위 항목이 있으면 머리를 굵게 하고 아랫줄에 잇는다."""
    if isinstance(item, str):
        return item
    subs = item.get("sub") or []
    return "\n".join([f"**{plain(item['text'])}**", *subs]) if subs else item["text"]


def as_lines(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    return [value] if isinstance(value, str) else list(value)


def join_notes(*parts: str | None) -> str:
    return "\n".join(part for part in parts if part)


class Deck:
    def __init__(self, doc: dict, base_dir: Path, student: bool = False):
        self.doc = doc
        self.base_dir = base_dir
        self.student = student          # 학생용 사본: 답 장과 발표자 노트(정답이 들어 있음)를 만들지 않는다
        self.dark, self.tint = PALETTES.get(doc["subject"], DEFAULT_PALETTE)
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(SLIDE_W), Inches(SLIDE_H)
        self.number = 0
        self.warnings: list[str] = []

    def warn(self, message: str) -> None:
        entry = f"{self.number}번째 장: {message}"
        if entry not in self.warnings:
            self.warnings.append(entry)

    def slide(self, notes: str | None = None):
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[BLANK_LAYOUT])
        self.shape(slide, 0, 0, SLIDE_W, 0.14, fill=self.dark)
        if notes and not self.student:
            slide.notes_slide.notes_text_frame.text = notes
        return slide

    def shape(self, slide, x, y, w, h, text="", size=20, bold=False, color=INK, fill=None, line=None,
              kind=MSO_SHAPE.RECTANGLE, line_width=1.25, floor=CLASSROOM_FONT):
        item = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            item.adjustments[0] = 0.08
        item.shadow.inherit = False
        if fill:
            item.fill.solid()
            item.fill.fore_color.rgb = RGBColor.from_string(fill)
        else:
            item.fill.background()
        if line:
            item.line.color.rgb = RGBColor.from_string(line)
            item.line.width = Pt(line_width)
        else:
            item.line.fill.background()
        fitted = fit_size(text, w, h, size)
        if text and fitted < floor:
            self.warn(f"글이 많아 교실 기준 {CLASSROOM_FONT}pt보다 작게 줄었고 넘칠 수 있음. 글을 줄이거나 장을 나누세요")
        self._write(item.text_frame, text, fitted, bold, color)
        return item

    def _write(self, frame, text: str, size: float, bold: bool, color: str) -> None:
        frame.word_wrap = True
        frame.auto_size = MSO_AUTO_SIZE.NONE
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        frame.margin_left = frame.margin_right = Inches(PAD)
        frame.margin_top = frame.margin_bottom = Inches(VPAD)
        for index, part in enumerate(text.split("\n")):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.alignment = PP_ALIGN.CENTER
            for piece, marked in split_marks(part) or [("", False)]:
                self._run(paragraph, piece, size, bold or marked, self.dark if marked and color == INK else color)

    @staticmethod
    def _run(paragraph, text: str, size: float, bold: bool, color: str) -> None:
        run = paragraph.add_run()
        run.text = text
        run.font.size, run.font.bold, run.font.name = Pt(size), bold, FONT
        run.font.color.rgb = RGBColor.from_string(color)
        props = run._r.get_or_add_rPr()
        props.set("lang", "ko-KR")      # 한국어로 지정해야 어절 단위로 줄이 바뀐다
        east_asian = OxmlElement("a:ea")
        east_asian.set("typeface", FONT)
        props.find(qn("a:latin")).addnext(east_asian)

    def heading(self, slide, spec: dict, default_tag: str = "") -> None:
        tag = spec.get("tag") or default_tag or self.doc["unit"]
        self.shape(slide, MARGIN, 0.34, BODY_W, 0.44, tag, 18, True, self.dark)
        self.shape(slide, MARGIN, 0.78, BODY_W, 0.85, spec["title"], 38, True, INK)

    def key(self, slide, text: str | None) -> None:
        if text:
            self.shape(slide, MARGIN, KEY_TOP, BODY_W, KEY_H, text, 26, True, WHITE, self.dark,
                       kind=MSO_SHAPE.ROUNDED_RECTANGLE)

    @staticmethod
    def body_bottom(spec: dict) -> float:
        return KEY_TOP - 0.25 if spec.get("key") else BODY_BOTTOM

    def columns(self, count: int, gap: float = GAP) -> tuple[float, list[float]]:
        width = (BODY_W - gap * (count - 1)) / count
        return width, [MARGIN + index * (width + gap) for index in range(count)]


def row_positions(count: int, top: float, bottom: float, limit: float = 1.1, gap: float = ROW_GAP) -> tuple[float, list[float]]:
    """줄의 높이와 y 좌표를 돌려준다. 남는 자리는 위아래로 고르게 나눈다."""
    if count == 0:
        raise ValueError("목록이 비어 있음")
    height = min(limit, (bottom - top - gap * (count - 1)) / count)
    start = top + (bottom - top - height * count - gap * (count - 1)) / 2
    return height, [start + index * (height + gap) for index in range(count)]


def weighted_rows(needs: list[float], top: float, bottom: float, gap: float = ROW_GAP) -> tuple[list[float], list[float]]:
    """줄마다 필요한 높이(인치)에 비례해 높이를 나누고 (높이 목록, y 목록)을 돌려준다. 남는 자리는 위아래로 나눈다."""
    scale = min(MAX_ROW_SCALE, (bottom - top - gap * (len(needs) - 1)) / sum(needs))
    heights = [need * scale for need in needs]
    y = top + (bottom - top - sum(heights) - gap * (len(needs) - 1)) / 2
    ys = []
    for height in heights:
        ys.append(y)
        y += height + gap
    return heights, ys


def content_layout(texts: list[str], bottom: float) -> tuple[list[float], list[float], float]:
    """설명 행들의 높이, y, 모두가 쓸 글자 크기를 돌려준다. 하위 항목이 많은 행이 더 높고 다른 행은 줄지 않는다."""
    width = BODY_W - 0.8
    needs = [line_count(text, width, BASE_ROW_FONT) * BASE_ROW_FONT * LINE_RATIO / 72 + 2 * VPAD for text in texts]
    heights, ys = weighted_rows(needs, BODY_TOP, bottom)
    size = min(tidy_size(text, width, height, BASE_ROW_FONT) for text, height in zip(texts, heights))
    return heights, ys, size


def content_pages(texts: list[str], bottom: float) -> list[tuple[int, int]]:
    """한 장에 5줄까지, 그리고 글자가 SPLIT_FONT 아래로 줄지 않는 만큼만 담도록 (시작, 끝) 쪽 나누기를 정한다."""
    pages, start = [], 0
    while start < len(texts):
        end = start + 1
        while end < min(start + MAX_ROWS, len(texts)) and content_layout(texts[start:end + 1], bottom)[2] >= SPLIT_FONT:
            end += 1
        pages.append((start, end))
        start = end
    return pages
