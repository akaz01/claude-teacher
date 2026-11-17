"""make_pptx.py의 설명 장 도식: 핵심 띠, 흐름(flow), 카드(cards), 그림 설명(callouts).

make_deck.py의 같은 이름 장과 같은 입력을 받는다. 글자는 모두 가운데 정렬이다.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from make_pptx_base import COMPARE_ITEM_RATIO, TABLE_MIN_FONT, Deck, est_lines, line_h

KEY_PAD = Inches(0.12)                  # 핵심 띠의 위아래 여백
KEY_SIDE = Inches(0.3)                  # 핵심 띠의 좌우 여백
KEY_GAP = Inches(0.2)                   # 핵심 띠와 본문 사이
CHEVRON_DEPTH = 0.45                    # 갈매기 머리의 뾰족한 부분 (머리 높이 대비)
MAX_FLOW_STEPS = 5
MAX_CARDS = 4
POINTER_DOT = Inches(0.14)
CALLOUT_AREA_RATIO = 0.62               # 설명이 있을 때 그림이 차지하는 너비


def key_layout(deck: Deck, text: str) -> tuple[float, int]:
    """핵심 띠의 글자 크기와 높이. 한 줄에 들어가도록 글자를 줄이고, 그래도 넘으면 줄 수만큼 높인다."""
    size = deck.theme.body
    inner = deck.body_w - 2 * KEY_SIDE
    while est_lines(text, inner, size) > 1 and size > deck.theme.small:
        size -= 1
    return size, est_lines(text, inner, size) * line_h(size) + 2 * KEY_PAD


def content_bottom(deck: Deck, s: dict) -> int:
    """핵심 띠가 있으면 그 위까지, 없으면 본문 끝까지."""
    if not s.get("key"):
        return deck.body_bottom
    return deck.body_bottom - key_layout(deck, s["key"])[1] - KEY_GAP


def draw_key(deck: Deck, slide, s: dict) -> None:
    text = s.get("key")
    if not text:
        return
    size, height = key_layout(deck, text)
    top = deck.body_bottom - height
    band = deck.box(slide, deck.mx, top, deck.body_w, height, fill=deck.theme.accent)
    frame = deck.plain_frame(band, MSO_ANCHOR.MIDDLE)
    frame.margin_left = frame.margin_right = KEY_SIDE
    frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    deck.runs(frame.paragraphs[0], text, size, True, deck.theme.on_accent)
    if est_lines(text, deck.body_w - 2 * KEY_SIDE, size) > 1:
        deck.warnings.append(f"{deck.count}쪽 핵심 띠가 한 줄을 넘음. 문장을 줄이세요")


def label(deck: Deck, slide, x: int, y: int, w: int, h: int, text: str, size: float, bold: bool = False,
          color: str | None = None) -> None:
    """도형 위에 가로·세로 가운데로 놓는 글."""
    frame = deck.textbox(slide, x, y, w, h, MSO_ANCHOR.MIDDLE)
    frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    deck.runs(frame.paragraphs[0], text, size, bold, color, deck.theme.accent if not color else color)


def render_flow(deck: Deck, s: dict) -> None:
    t = deck.theme
    slide = deck.new_slide(s["title"], s.get("notes"))
    bottom = content_bottom(deck, s)
    steps = s["steps"]
    gap, pad, head_h = Inches(0.1), Inches(0.15), Inches(1.0)
    width = (deck.body_w - gap * (len(steps) - 1)) // len(steps)
    inset = int(head_h * CHEVRON_DEPTH)
    text_top = deck.body_top + head_h + Inches(0.2)
    text_h = max(bottom - text_top, Inches(0.5))
    head_size = deck.fit_font([step["head"] for step in steps], width - 2 * inset, head_h, t.body, t.small, "단계 이름")
    text_size = deck.fit_font([step["text"] for step in steps], width - 2 * pad, text_h - 2 * pad,
                              round(t.body * COMPARE_ITEM_RATIO), TABLE_MIN_FONT, "단계 설명")
    for index, step in enumerate(steps):
        x = deck.mx + index * (width + gap)
        deck.box(slide, x, deck.body_top, width, head_h, fill=t.accent, shape=MSO_SHAPE.CHEVRON)
        label(deck, slide, x + inset, deck.body_top, width - 2 * inset, head_h, step["head"], head_size, True, t.on_accent)
        deck.box(slide, x, text_top, width, text_h, fill=t.panel)
        label(deck, slide, x + pad, text_top + pad, width - 2 * pad, text_h - 2 * pad, step["text"], text_size)
    draw_key(deck, slide, s)


def render_cards(deck: Deck, s: dict) -> None:
    t = deck.theme
    slide = deck.new_slide(s["title"], s.get("notes"))
    bottom = content_bottom(deck, s)
    cards = s["cards"]
    gap, pad, head_h = Inches(0.3), Inches(0.2), Inches(0.8)
    width = (deck.body_w - gap * (len(cards) - 1)) // len(cards)
    text_h = bottom - deck.body_top - head_h - 3 * pad
    head_size = deck.fit_font([card["head"] for card in cards], width - 2 * pad, head_h, t.body, t.small, "카드 머리")
    text_size = deck.fit_font([card["text"] for card in cards], width - 2 * pad, text_h, t.body, TABLE_MIN_FONT, "카드 설명")
    for index, card in enumerate(cards):
        x = deck.mx + index * (width + gap)
        deck.box(slide, x, deck.body_top, width, bottom - deck.body_top, fill=t.panel, line=t.accent, line_w=2)
        deck.box(slide, x + pad, deck.body_top + pad, width - 2 * pad, head_h, fill=t.accent)
        label(deck, slide, x + pad, deck.body_top + pad, width - 2 * pad, head_h, card["head"], head_size, True, t.on_accent)
        label(deck, slide, x + pad, deck.body_top + 2 * pad + head_h, width - 2 * pad, text_h, card["text"], text_size)
    draw_key(deck, slide, s)


def pointer(deck: Deck, slide, start: tuple[int, int], end: tuple[int, int]) -> None:
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(start[0]), Emu(start[1]), Emu(end[0]), Emu(end[1]))
    line.line.color.rgb = RGBColor.from_string(deck.theme.accent)
    line.line.width = Pt(1.5)
    deck.box(slide, end[0] - POINTER_DOT // 2, end[1] - POINTER_DOT // 2, POINTER_DOT, POINTER_DOT,
             fill=deck.theme.accent, shape=MSO_SHAPE.OVAL)


def draw_callouts(deck: Deck, slide, callouts: list[dict], left: int, bottom: int, placed) -> None:
    """그림 오른쪽에 설명 칸을 y 순서로 쌓는다. x, y(0~1)가 있으면 그림 안의 그 점까지 선을 긋는다."""
    t = deck.theme
    gap, pad = Inches(0.2), Inches(0.15)
    width = deck.W - deck.mx - left
    avail = bottom - deck.body_top
    height = min(Inches(1.3), (avail - gap * (len(callouts) - 1)) // len(callouts))
    size = deck.fit_font([c["text"] for c in callouts], width - 2 * pad, height - 2 * pad,
                         round(t.body * COMPARE_ITEM_RATIO), TABLE_MIN_FONT, "그림 설명")
    start = deck.body_top + (avail - height * len(callouts) - gap * (len(callouts) - 1)) // 2
    for index, entry in enumerate(callouts):
        y = start + index * (height + gap)
        deck.box(slide, left, y, width, height, fill=t.panel)
        label(deck, slide, left + pad, y, width - 2 * pad, height, entry["text"], size)
        if placed and "x" in entry and "y" in entry:
            pic_left, pic_top, pic_w, pic_h = placed
            pointer(deck, slide, (left, y + height // 2),
                    (int(pic_left + entry["x"] * pic_w), int(pic_top + entry["y"] * pic_h)))
