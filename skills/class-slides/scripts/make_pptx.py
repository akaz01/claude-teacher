"""수업용 PPT(.pptx) 생성기. 테마 5종, 내용이 넘치면 자동으로 다음 장에 이어 쓴다.

입력 JSON 예시 (그대로 복사해도 유효한 JSON):
{
  "theme": "basic",
  "template": "선생님템플릿.pptx",
  "slides": [
    {"type": "cover", "unit": "Ⅱ. 물질의 구성", "title": "입자의 운동", "meta": "중학교 2학년 과학 · 3/8차시"},
    {"type": "section", "title": "1. 확산", "subtitle": "입자가 퍼져 나가는 현상"},
    {"type": "goals", "items": ["확산을 설명할 수 있다."]},
    {"type": "content", "title": "제목", "items": ["항목", {"text": "항목", "sub": ["하위 항목"]}], "key": "핵심 문장"},
    {"type": "flow", "title": "확산은 어떻게 일어날까", "steps": [{"head": "움직임", "text": "입자가 스스로 움직인다"},
                                                       {"head": "섞임", "text": "서로 섞여 들어간다"}], "key": "핵심 문장"},
    {"type": "cards", "title": "세 가지 상태", "cards": [{"head": "고체", "text": "모양이 일정하다"},
                                                  {"head": "액체", "text": "담는 그릇을 따른다"}], "key": "핵심 문장"},
    {"type": "compare", "title": "제목", "left": {"heading": "확산", "items": ["..."]},
                                        "right": {"heading": "증발", "items": ["..."]}, "key": "핵심 문장"},
    {"type": "activity", "title": "실험", "time": "20분", "group": "4명 모둠", "materials": "비커, 잉크",
     "steps": ["준비한다", "관찰한다"]},
    {"type": "quiz", "question": "문제", "choices": ["가", "나", "다", "라"], "answer": 0, "reveal": true,
     "reveal_notes": "절반 넘게 틀리면 앞 설명으로 돌아간다."},
    {"type": "summary", "title": "오늘 배운 내용", "items": ["**굵게** 강조 가능"]},
    {"type": "figure", "title": "제목", "image": "그림.png", "caption": "교과서 32쪽",
     "callouts": ["그림 옆 설명", {"text": "선을 긋는 설명", "x": 0.5, "y": 0.3}], "key": "핵심 문장"},
    {"type": "table", "title": "제목", "header": ["구분", "내용"], "rows": [["가", "나"]], "key": "핵심 문장"}
  ]
}

설명:
- theme: basic(기본) / elem(초등) / sci(이과) / hum(문과) / board(고대비 칠판형).
- template: 선택. 있으면 그 디자인 위에 내용만 채운다. 템플릿 테마의 색(accent1부터)을 강조색으로 읽어 쓰고,
  읽지 못하거나 배경 위에서 안 보이는 색뿐일 때만 theme의 색을 쓴다. 쪽 번호는 템플릿의 띠 같은 바탕 위에서도 보이게 색을 고른다.
  상대 경로는 입력 JSON 파일이 있는 폴더를 기준으로 찾는다.
- 모든 슬라이드에 "notes"(발표자 노트)를 넣을 수 있다.
- 설명 장(content, flow, cards, compare, table, figure)에 "key"(핵심 문장)를 쓰면 아래에 핵심 띠가 붙는다.
- flow의 steps는 2~5개, cards는 2~4개이며 항목은 {"head": ..., "text": ...} 형식이다.
- figure의 callouts는 그림 옆 설명 칸이다. x, y(0~1)를 쓰면 그림 안의 그 점까지 선을 긋는다.
- goals와 summary의 items는 글자 또는 {"text": "..."} 형식이다.
- table의 rows는 행마다 목록이어야 하고, compare의 items도 목록이어야 한다.
- quiz의 answer는 0부터 센다 (첫 번째 선지 = 0). reveal이 true면 정답 공개 슬라이드를 바로 뒤에 만들고,
  노트에 정답과 다음 행동을 넣는다. 다음 행동은 "reveal_notes"에 쓴다 (없으면 기본 문구).
- figure에 image가 없으면 [그림: caption] 자리를 만든다.
- 글은 모두 가운데 정렬이다 (make_deck.py와 같음). 템플릿의 제목 자리는 템플릿의 정렬을 따른다.
- make_deck.py에만 있는 장(keywords, outline, check, task, example)은 쓸 수 없다. 오류 문구가 대신 쓸 장을 알려 준다.
- figure의 image와 template의 상대 경로는 입력 JSON 파일이 있는 폴더를 기준으로 찾는다. 없는 그림은 한국어 오류로 알린다.
- compare의 머리글은 heading 또는 head(make_deck.py와 같음), activity는 time, group, roles, materials, output 중 적은 것만 칸으로 그린다.
- 템플릿에 제목 장(가운데 제목)이나 구역 머리 레이아웃이 있으면 cover와 section은 그 레이아웃을 쓰고,
  템플릿의 제목 자리에는 글만 넣어 양식의 크기·굵기·색·글꼴을 그대로 이어받는다.
- 출력 파일은 .pptx여야 하며 입력 JSON이나 템플릿 파일과 같은 경로일 수 없다 (원본 덮어쓰기 방지).
- --student를 붙이면 학생용 사본을 만든다: quiz의 정답 장(reveal)을 만들지 않고 발표자 노트를 모두 비운다 (make_deck.py와 같은 동작).

사용법:
    python make_pptx.py 슬라이드.json 수업.pptx
    python make_pptx.py 슬라이드.json 학생용.pptx --student
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.parts.image import Image
from pptx.util import Emu, Inches, Pt

from make_pptx_base import (COMPARE_ITEM_RATIO, COMPARE_MIN_RATIO, MIN_CHOICE_H, OUTPUT_SUFFIX,
                            QUIZ_SHORT_CHOICE_UNITS, STEP_CIRCLE_RATIO, TABLE_CELL_PAD, TABLE_FONT_OFFSET,
                            TABLE_MIN_FONT, THEMES, Deck, est_lines, line_h, paginate, text_units)
from make_deck_check import (ACTIVITY_FACTS, describe_os_error, read_input_json, split_student_flag,
                             use_utf8_output)
from pptx_safety import check_image_size, check_inside_folder, stamp_properties
from slide_check import polish
from make_pptx_diagrams import (CALLOUT_AREA_RATIO, MAX_CARDS, MAX_FLOW_STEPS, content_bottom, draw_callouts, draw_key,
                                render_cards, render_flow)

MARKS = ["①", "②", "③", "④", "⑤"]
SLIDE_TYPES = ("cover", "section", "goals", "content", "flow", "cards", "compare", "activity", "quiz", "summary",
               "figure", "table")
DECK_ONLY_SUBSTITUTES = {
    "keywords": "table (머리 칸 '낱말'·'뜻')", "outline": "content (지금 주기를 **굵게**)", "check": "quiz",
    "task": "content 두 장 (문제 장, 답 장)", "example": "compare (왼쪽 풀이, 오른쪽 문제)",
}
DEFAULT_NEXT_ACTION = "다음 행동: 정답을 확인하고 이유를 묻는다. 절반 넘게 틀리면 앞 설명으로 돌아간다."


# ---------------------------------------------------------------- 슬라이드 종류별

def render_cover(deck: Deck, s: dict) -> None:
    t = deck.theme
    if deck.uses_title_layout("cover"):      # 양식의 제목 장: 제목 자리에 글만 넣고 모양은 양식을 따른다
        slide = deck.new_slide(s["title"], s.get("notes"), kind="cover")
        deck.fill_subtitle(slide, [s.get("unit"), s.get("meta")], t.small)
        return
    slide = deck.new_slide(notes=s.get("notes"), kind="cover")
    frame = deck.textbox(slide, deck.mx, int(deck.H * 0.2), deck.body_w, int(deck.H * 0.6), MSO_ANCHOR.MIDDLE)
    next_paragraph = deck.paragraphs(frame)
    for text, size, bold, color in ((s.get("unit"), t.small, True, t.accent), (s["title"], t.cover, True, t.head),
                                    (s.get("meta"), t.small, False, t.muted)):
        if not text:
            continue
        paragraph = next_paragraph()
        paragraph.space_after = Pt(size * 0.6)
        deck.runs(paragraph, text, size, bold, color)


def render_section(deck: Deck, s: dict) -> None:
    t = deck.theme
    if deck.uses_title_layout("section"):
        slide = deck.new_slide(s["title"], s.get("notes"), kind="section")
        deck.fill_subtitle(slide, [s.get("subtitle")], t.body)
        return
    slide = deck.new_slide(notes=s.get("notes"), kind="section")
    deck.box(slide, (deck.W - Inches(1.2)) // 2, int(deck.H * 0.36), Inches(1.2), Inches(0.08), fill=t.accent)
    frame = deck.textbox(slide, deck.mx, int(deck.H * 0.4), deck.body_w, int(deck.H * 0.35))
    next_paragraph = deck.paragraphs(frame)
    for text, size, color in ((s["title"], t.cover, t.head), (s.get("subtitle"), t.body, t.muted)):
        if text:
            deck.runs(next_paragraph(), text, size, size == t.cover, color)


def render_goals(deck: Deck, s: dict) -> None:
    t = deck.theme
    slide = deck.new_slide(s.get("title", "학습 목표"), s.get("notes"))
    pad = Inches(0.35)
    inner_w = deck.body_w - 2 * pad - Inches(0.5)
    height = sum(est_lines(g, inner_w, t.body) * line_h(t.body) for g in s["items"]) + 2 * pad
    height += int(len(s["items"]) * Pt(t.body * 0.5))
    if height > deck.body_h:
        deck.warnings.append(f"{deck.count}쪽 학습 목표가 길어 넘칠 수 있음")
    deck.box(slide, deck.mx, deck.body_top, deck.body_w, min(height, deck.body_h), fill=t.panel)
    frame = deck.textbox(slide, deck.mx + pad, deck.body_top + pad, deck.body_w - 2 * pad, height - 2 * pad)
    next_paragraph = deck.paragraphs(frame)
    for number, goal in enumerate(s["items"], 1):
        paragraph = next_paragraph()
        paragraph.space_after = Pt(t.body * 0.5)
        deck.runs(paragraph, f"{number}   ", t.body, True, t.accent)
        deck.runs(paragraph, goal, t.body)


def _normalize_items(items: list) -> list[tuple[str, list[str]]]:
    return [(item, []) if isinstance(item, str) else (item["text"], item.get("sub", [])) for item in items]


def render_content(deck: Deck, s: dict) -> None:
    t = deck.theme
    sub_size = round(t.body * 0.85)
    indent = Inches(0.45)
    bottom = content_bottom(deck, s)
    items = _normalize_items(s["items"])
    heights = [
        est_lines(text, deck.body_w - indent, t.body) * line_h(t.body) + int(Pt(t.body * 0.5))
        + sum(est_lines(sub, deck.body_w - 2 * indent, sub_size) * line_h(sub_size) for sub in subs)
        for text, subs in items
    ]
    for page, indexes in enumerate(paginate(heights, bottom - deck.body_top)):
        title = s["title"] + (" (계속)" if page else "")
        slide = deck.new_slide(title, s.get("notes") if page == 0 else None)
        frame = deck.textbox(slide, deck.mx, deck.body_top, deck.body_w, bottom - deck.body_top, MSO_ANCHOR.MIDDLE)
        next_paragraph = deck.paragraphs(frame)
        for index in indexes:
            text, subs = items[index]
            paragraph = next_paragraph()
            paragraph.space_before = Pt(t.body * 0.5)
            deck.runs(paragraph, text, t.body, bold_color=t.accent)     # 가운데 정렬이라 글머리표는 줄마다 어긋나서 쓰지 않는다
            for sub in subs:
                deck.runs(next_paragraph(), sub, sub_size, color=t.fg)
        draw_key(deck, slide, s)


def _column_height(side: dict, width: int, size: float) -> int:
    item_size = round(size * COMPARE_ITEM_RATIO)
    return line_h(size) + sum(est_lines(i, width, item_size) * line_h(item_size) + int(Pt(size * 0.4))
                              for i in side.get("items", []))


def render_compare(deck: Deck, s: dict) -> None:
    t = deck.theme
    slide = deck.new_slide(s["title"], s.get("notes"))
    avail = content_bottom(deck, s) - deck.body_top
    gap, pad = Inches(0.4), Inches(0.3)
    col_w = (deck.body_w - gap) // 2
    sides = (s["left"], s["right"])
    content_h = max(_column_height(side, col_w - 2 * pad, t.body) for side in sides) + 2 * pad
    if content_h > avail:
        deck.warnings.append(f"{deck.count}쪽 비교 내용이 길어 넘칠 수 있음")
    panel_h = min(avail, max(content_h, int(avail * COMPARE_MIN_RATIO)))
    for column, (side, color) in enumerate(zip(sides, (t.accent, t.accent2))):
        x = deck.mx + column * (col_w + gap)
        deck.box(slide, x, deck.body_top, col_w, panel_h, fill=t.panel)
        frame = deck.textbox(slide, x + pad, deck.body_top + pad, col_w - 2 * pad, panel_h - 2 * pad)
        next_paragraph = deck.paragraphs(frame)
        deck.runs(next_paragraph(), side["heading"], t.body, True, color)
        for item in side.get("items", []):
            paragraph = next_paragraph()
            paragraph.space_before = Pt(t.body * 0.4)
            deck.runs(paragraph, "·  " + item, round(t.body * COMPARE_ITEM_RATIO))
    draw_key(deck, slide, s)


def render_activity(deck: Deck, s: dict) -> None:
    t = deck.theme
    slide = deck.new_slide(s["title"], s.get("notes"))
    facts = [(label, s[name], name) for label, name in ACTIVITY_FACTS if s.get(name)]
    gap, pad = Inches(0.3), Inches(0.2)
    crowded = len(facts) > 3                     # 칸이 4~5개면 글자를 조금 줄여 한 줄에 둔다
    y = deck.body_top
    if facts:
        card_w = (deck.body_w - (len(facts) - 1) * gap) // len(facts)
        small_body = round(t.body * COMPARE_ITEM_RATIO)
        sizes = [t.title if name == "time" and not crowded else small_body if crowded else t.body
                 for _, _, name in facts]
        value_h = max(est_lines(value, card_w - 2 * pad, size) * line_h(size) for (_, value, _), size in zip(facts, sizes))
        card_h = line_h(t.small) + value_h + 2 * pad
        for number, ((label, value, _), size) in enumerate(zip(facts, sizes)):
            x = deck.mx + number * (card_w + gap)
            deck.box(slide, x, deck.body_top, card_w, card_h, line=t.accent, line_w=2)
            frame = deck.textbox(slide, x + pad, deck.body_top + pad, card_w - 2 * pad, card_h - 2 * pad)
            next_paragraph = deck.paragraphs(frame)
            deck.runs(next_paragraph(), label, t.small, color=t.muted)
            deck.runs(next_paragraph(), value, size, True, t.accent if number == 0 else t.fg)
        y = deck.body_top + card_h + Inches(0.35)
    circle = int(line_h(t.body) * STEP_CIRCLE_RATIO)
    step_size = round(t.body * COMPARE_ITEM_RATIO)
    text_x = deck.mx + circle + Inches(0.25)
    for number, step in enumerate(s.get("steps") or [], 1):
        step_h = max(circle, est_lines(step, deck.W - deck.mx - text_x, step_size) * line_h(step_size))
        deck.box(slide, deck.mx, y, circle, circle, fill=t.accent, shape=MSO_SHAPE.OVAL)
        frame = deck.textbox(slide, deck.mx, y, circle, circle, MSO_ANCHOR.MIDDLE)
        deck.runs(deck.paragraphs(frame)(), str(number), t.small, True, t.on_accent)
        text_frame = deck.textbox(slide, text_x, y, deck.W - deck.mx - text_x, step_h, MSO_ANCHOR.MIDDLE)
        deck.runs(deck.paragraphs(text_frame)(), step, step_size)
        y += step_h + Inches(0.2)
    if y > deck.body_bottom:
        deck.warnings.append(f"{deck.count}쪽 활동 단계가 많아 넘칠 수 있음")


def _answer_line(s: dict) -> str:
    answer = s.get("answer")
    return f"정답: {MARKS[answer]} {s['choices'][answer]}" if isinstance(answer, int) else ""


def _quiz_notes(s: dict, reveal: bool) -> str | None:
    """문제 장에는 교사용 정답을, 정답 장에는 정답과 다음 행동을 노트에 적는다."""
    if not reveal:
        return "\n".join(part for part in (s.get("notes"), _answer_line(s)) if part) or None
    action = s.get("reveal_notes") or "\n".join(part for part in (s.get("notes"), DEFAULT_NEXT_ACTION) if part)
    return "\n".join(part for part in (_answer_line(s), action) if part)


def _quiz_slide(deck: Deck, s: dict, reveal: bool) -> None:
    t = deck.theme
    title = s.get("title", "확인 문제") + (" (정답)" if reveal else "")
    slide = deck.new_slide(title, _quiz_notes(s, reveal))
    q_lines = est_lines(s["question"], deck.body_w, t.body)
    frame = deck.textbox(slide, deck.mx, deck.body_top, deck.body_w, q_lines * line_h(t.body))
    deck.runs(deck.paragraphs(frame)(), s["question"], t.body, True)
    choices = s["choices"]
    two_columns = len(choices) <= 4 and all(text_units(c) <= QUIZ_SHORT_CHOICE_UNITS for c in choices)
    columns = 2 if two_columns else 1
    gap = Inches(0.25)
    top = deck.body_top + q_lines * line_h(t.body) + Inches(0.35)
    if reveal:
        top += line_h(t.small)
    rows = math.ceil(len(choices) / columns)
    cell_w = (deck.body_w - gap * (columns - 1)) // columns
    available = deck.body_bottom - top - gap * (rows - 1)
    cell_h = max(MIN_CHOICE_H, min(line_h(t.body) + Inches(0.3), available // rows))
    if top + rows * cell_h + gap * (rows - 1) > deck.body_bottom:
        deck.warnings.append(f"{deck.count}쪽 퀴즈 문제가 길어 선지가 넘칠 수 있음 (문제를 줄이거나 자료 슬라이드로 나누세요)")
    for index, choice in enumerate(choices):
        x = deck.mx + (index % columns) * (cell_w + gap)
        y = top + (index // columns) * (cell_h + gap)
        is_answer = reveal and index == s["answer"]
        deck.box(slide, x, y, cell_w, cell_h, fill=t.panel, line=t.accent2 if is_answer else None, line_w=3)
        box = deck.textbox(slide, x + Inches(0.25), y, cell_w - Inches(0.5), cell_h, MSO_ANCHOR.MIDDLE)
        paragraph = deck.paragraphs(box)()
        deck.runs(paragraph, f"{MARKS[index]}  ", round(t.body * COMPARE_ITEM_RATIO), True, t.accent)
        deck.runs(paragraph, choice, round(t.body * COMPARE_ITEM_RATIO), is_answer)
    if reveal:
        label = deck.textbox(slide, deck.mx, top - line_h(t.small) - Inches(0.1), deck.body_w, line_h(t.small))
        answer = s["answer"]
        deck.runs(deck.paragraphs(label)(), f"정답: {MARKS[answer]} {choices[answer]}", t.small, True, t.accent2)


def render_quiz(deck: Deck, s: dict) -> None:
    _quiz_slide(deck, s, reveal=False)
    if s.get("reveal") and not deck.student:
        _quiz_slide(deck, s, reveal=True)


def render_summary(deck: Deck, s: dict) -> None:
    t = deck.theme
    pad, gap = Inches(0.25), Inches(0.2)
    inner_w = deck.body_w - 2 * pad
    heights = [est_lines(item, inner_w, t.body) * line_h(t.body) + 2 * pad + gap for item in s["items"]]
    for page, indexes in enumerate(paginate(heights, deck.body_h)):
        title = s.get("title", "오늘 배운 내용") + (" (계속)" if page else "")
        slide = deck.new_slide(title, s.get("notes") if page == 0 else None)
        y = deck.body_top
        for index in indexes:
            height = heights[index] - gap
            deck.box(slide, deck.mx, y, deck.body_w, height, fill=t.panel)
            frame = deck.textbox(slide, deck.mx + pad, y + pad, inner_w, height - 2 * pad, MSO_ANCHOR.MIDDLE)
            deck.runs(deck.paragraphs(frame)(), s["items"][index], t.body, bold_color=t.accent)
            y += heights[index]


def _image_size(path: str) -> tuple[int, int]:
    """그림의 (가로, 세로) 픽셀. 없거나 그림이 아니면 한국어 오류로 알린다."""
    if not Path(path).is_file():
        raise ValueError(f"그림 파일을 찾을 수 없음: {path}")
    check_image_size(path)
    try:
        return Image.from_file(path).size
    except OSError as error:        # 그림이 아니거나 깨진 파일
        raise ValueError(f"그림 파일을 열 수 없음: {path}") from error


def render_figure(deck: Deck, s: dict) -> None:
    t = deck.theme
    slide = deck.new_slide(s["title"], s.get("notes"))
    bottom = content_bottom(deck, s)
    callouts = s.get("callouts") or []
    caption_h = line_h(t.small) if s.get("caption") else 0
    area_h = bottom - deck.body_top - caption_h - Inches(0.1)
    area_w = int(deck.body_w * CALLOUT_AREA_RATIO) if callouts else deck.body_w
    placed = None
    if s.get("image"):
        width_px, height_px = _image_size(s["image"])
        scale = min(area_w / width_px, area_h / height_px)
        w, h = int(width_px * scale), int(height_px * scale)
        x = deck.mx + (area_w - w) // 2
        slide.shapes.add_picture(s["image"], Emu(x), Emu(deck.body_top), Emu(w), Emu(h))
        placed = (x, deck.body_top, w, h)
        if caption_h:
            frame = deck.textbox(slide, deck.mx, deck.body_top + h + Inches(0.1), area_w, caption_h)
            deck.runs(deck.paragraphs(frame)(), s["caption"], t.small, color=t.muted)
    else:
        deck.box(slide, deck.mx, deck.body_top, area_w, area_h + caption_h, line=t.muted, line_w=2, dash=True)
        frame = deck.textbox(slide, deck.mx, deck.body_top, area_w, area_h + caption_h, MSO_ANCHOR.MIDDLE)
        next_paragraph = deck.paragraphs(frame)
        deck.runs(next_paragraph(), "그림 자리", t.body, True)
        deck.runs(next_paragraph(), f"[그림: {s.get('caption', s['title'])}]", t.small, color=t.muted)
    if callouts:
        draw_callouts(deck, slide, callouts, deck.mx + area_w + Inches(0.3), bottom, placed)
    draw_key(deck, slide, s)


def _table_page(deck: Deck, s: dict, rows: list, widths: list[int], heights: list[int], title: str, notes) -> None:
    t = deck.theme
    size = max(TABLE_MIN_FONT, t.body - TABLE_FONT_OFFSET)
    slide = deck.new_slide(title, notes)
    all_rows = [s["header"]] + rows
    shape = slide.shapes.add_table(len(all_rows), len(widths), Emu(deck.mx), Emu(deck.body_top),
                                   Emu(deck.body_w), Emu(sum(heights)))
    table = shape.table
    for column, width in enumerate(widths):
        table.columns[column].width = Emu(width)
    for r, (row, height) in enumerate(zip(all_rows, heights)):
        table.rows[r].height = Emu(height)
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string(t.accent if r == 0 else (t.panel if r % 2 else t.bg))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.12)
            frame = cell.text_frame
            frame.clear()
            frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            deck.runs(frame.paragraphs[0], str(value), size, r == 0, t.on_accent if r == 0 else t.fg)
    draw_key(deck, slide, s)


def render_table(deck: Deck, s: dict) -> None:
    t = deck.theme
    size = max(TABLE_MIN_FONT, t.body - TABLE_FONT_OFFSET)
    columns = len(s["header"])
    rows_all = [s["header"]] + s["rows"]
    weights = [max(2.0, max(text_units(row[c]) for row in rows_all)) for c in range(columns)]
    # 머리말이 한 줄에 들어가는 최소 너비를 먼저 주고, 남는 너비를 내용 길이 비율로 나눈다
    minimums = [min(int(Pt(size) * max(2.0, text_units(s["header"][c]))) + TABLE_CELL_PAD, deck.body_w // columns)
                for c in range(columns)]
    spare = max(0, deck.body_w - sum(minimums))
    widths = [minimums[c] + int(spare * weights[c] / sum(weights)) for c in range(columns)]
    widths[-1] += deck.body_w - sum(widths)

    def row_height(row) -> int:
        lines = max(est_lines(str(v), w - Inches(0.24), size) for v, w in zip(row, widths))
        return lines * line_h(size) + Inches(0.12)

    header_h = row_height(s["header"])
    heights = [row_height(row) for row in s["rows"]]
    capacity = content_bottom(deck, s) - deck.body_top - header_h
    for page, indexes in enumerate(paginate(heights, capacity)):
        title = s["title"] + (" (계속)" if page else "")
        rows = [s["rows"][i] for i in indexes]
        _table_page(deck, s, rows, widths, [header_h] + [heights[i] for i in indexes], title,
                    s.get("notes") if page == 0 else None)


RENDERERS = {
    "cover": render_cover, "section": render_section, "goals": render_goals, "content": render_content,
    "flow": render_flow, "cards": render_cards, "compare": render_compare, "activity": render_activity,
    "quiz": render_quiz, "summary": render_summary, "figure": render_figure, "table": render_table,
}


# ---------------------------------------------------------------- 입력 검사와 실행

REQUIRED_FIELDS = {
    "cover": ("title",), "section": ("title",), "goals": ("items",), "content": ("title", "items"),
    "flow": ("title", "steps"), "cards": ("title", "cards"),
    "compare": ("title", "left", "right"), "activity": ("title",), "quiz": ("question", "choices"),
    "summary": ("items",), "figure": ("title",), "table": ("title", "header"),
}
TEXT_FIELDS = ("title", "unit", "meta", "subtitle", "question", "caption", "time", "group", "roles", "materials", "output",
               "notes", "key", "reveal_notes")
LIST_FIELDS = ("items", "choices", "header", "rows", "steps", "cards", "callouts")


def _as_text(value) -> str:
    return "" if value is None else str(value)


def _validate_quiz(where: str, slide: dict) -> None:
    choices = slide["choices"]
    if not 2 <= len(choices) <= len(MARKS):
        raise ValueError(f"{where}: 선지는 2~{len(MARKS)}개여야 함")
    answer = slide.get("answer")
    if answer is None and not slide.get("reveal"):
        return
    if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(choices):
        raise ValueError(f"{where}: answer는 0부터 {len(choices) - 1} 사이의 정수여야 함 (첫 선지 = 0)")


def _validate_slide(number: int, slide, check_files: bool = True) -> None:
    if not isinstance(slide, dict):
        raise ValueError(f"{number}번 슬라이드: {{\"type\": ...}} 형식이어야 함")
    kind = slide.get("type")
    if kind in DECK_ONLY_SUBSTITUTES:
        raise ValueError(f"{number}번 슬라이드: '{kind}'은 make_deck.py에서만 쓸 수 있음. "
                         f"make_pptx.py에서는 {DECK_ONLY_SUBSTITUTES[kind]}로 대신하세요")
    if kind not in SLIDE_TYPES:
        raise ValueError(f"{number}번 슬라이드: 알 수 없는 종류 {kind!r} (가능: {', '.join(SLIDE_TYPES)})")
    where = f"{number}번 슬라이드({kind})"
    missing = [field for field in REQUIRED_FIELDS[kind] if slide.get(field) in (None, "", [])]
    if missing:
        raise ValueError(f"{where}: {', '.join(missing)} 항목이 필요함")
    for field in LIST_FIELDS:
        if slide.get(field) is not None and not isinstance(slide[field], list):
            raise ValueError(f"{where}: {field}는 목록이어야 함")
    _validate_kind_specific(where, kind, slide)
    if check_files and kind == "figure" and slide.get("image") not in (None, ""):
        try:
            _image_size(str(slide["image"]))
        except ValueError as error:
            raise ValueError(f"{where}: {error}") from error


def _validate_kind_specific(where: str, kind: str, slide: dict) -> None:
    if kind in ("goals", "summary"):
        _validate_text_items(where, slide["items"])
    if kind == "content":
        _validate_content_items(where, slide["items"])
    if kind == "compare":
        _validate_compare(where, slide)
    if kind == "quiz":
        _validate_quiz(where, slide)
    if kind == "table":
        _validate_table(where, slide)
    if kind == "flow":
        _validate_head_text(where, slide, "steps", MAX_FLOW_STEPS)
    if kind == "cards":
        _validate_head_text(where, slide, "cards", MAX_CARDS)
    if kind == "figure":
        _validate_callouts(where, slide.get("callouts") or [])


def _validate_head_text(where: str, slide: dict, field: str, limit: int) -> None:
    entries = slide[field]
    if not 2 <= len(entries) <= limit:
        raise ValueError(f"{where}: {field}는 2~{limit}개여야 함 (더 많으면 장을 나누세요)")
    for entry in entries:
        if not isinstance(entry, dict) or "head" not in entry or "text" not in entry:
            raise ValueError(f'{where}: {field}의 항목은 {{"head": ..., "text": ...}} 형식이어야 함 (받은 값: {entry!r})')


def _validate_callouts(where: str, callouts: list) -> None:
    for entry in callouts:
        if isinstance(entry, dict) and "text" not in entry:
            raise ValueError(f'{where}: callouts의 항목은 글자 또는 {{"text": ...}} 형식이어야 함 (받은 값: {entry})')
        point = [entry[name] for name in ("x", "y") if isinstance(entry, dict) and name in entry]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in point):
            raise ValueError(f"{where}: callouts의 x, y는 0~1 사이의 숫자여야 함")


def _validate_text_items(where: str, items: list) -> None:
    for item in items:
        if isinstance(item, dict) and "text" not in item:
            raise ValueError(f'{where}: items의 항목은 글자 또는 {{"text": ...}} 형식이어야 함 (받은 값: {item})')


def _validate_content_items(where: str, items: list) -> None:
    for item in items:
        if isinstance(item, dict) and not isinstance(item.get("sub") or [], list):
            raise ValueError(f"{where}: items의 sub는 목록이어야 함")


def _validate_compare(where: str, slide: dict) -> None:
    for side in ("left", "right"):
        if not isinstance(slide[side], dict):
            raise ValueError(f'{where}: left와 right는 {{"heading": ..., "items": [...]}} 형식이어야 함')
        if not isinstance(slide[side].get("items") or [], list):
            raise ValueError(f"{where}: {side}의 items는 목록이어야 함")


def _validate_table(where: str, slide: dict) -> None:
    for row in slide.get("rows") or []:
        if not isinstance(row, list):
            raise ValueError(f"{where}: rows의 각 행은 목록이어야 함 (받은 값: {row!r})")
        if len(row) != len(slide["header"]):
            raise ValueError(f"{where}: 표의 행마다 칸 수가 header와 같아야 함")


def validate(spec: dict, check_files: bool = True) -> None:
    if not isinstance(spec, dict):
        raise ValueError("입력 JSON의 최상위는 {...} 객체여야 함")
    if spec.get("theme", "basic") not in THEMES:
        raise ValueError(f"theme은 {', '.join(THEMES)} 중 하나여야 함")
    if spec.get("template") is not None and not isinstance(spec["template"], str):
        raise ValueError("template은 .pptx 파일 경로(글자)여야 함")
    slides = spec.get("slides")
    if not slides:
        raise ValueError("slides가 비어 있음")
    for number, slide in enumerate(slides, 1):
        _validate_slide(number, slide, check_files)


def _normalize_item(item):
    if isinstance(item, dict):
        return {"text": _as_text(item.get("text")), "sub": [_as_text(sub) for sub in item.get("sub") or []]}
    return _as_text(item)


def _normalize_callout(entry) -> dict:
    return {"text": _as_text(entry)} if not isinstance(entry, dict) else {**entry, "text": _as_text(entry["text"])}


def normalize(slide: dict) -> dict:
    """숫자나 None이 섞여 와도 렌더러가 글자만 다루도록 정리한다."""
    clean = {**slide, **{key: _as_text(slide[key]) for key in TEXT_FIELDS if slide.get(key) is not None}}
    for key in ("choices", "header") + (("steps",) if slide["type"] != "flow" else ()):
        if slide.get(key) is not None:
            clean[key] = [_as_text(value) for value in slide[key]]
    for key in ("steps", "cards"):
        if slide.get(key) is not None and slide["type"] in ("flow", "cards"):
            clean[key] = [{"head": _as_text(e["head"]), "text": _as_text(e["text"])} for e in slide[key]]
    if slide.get("callouts") is not None:
        clean["callouts"] = sorted((_normalize_callout(e) for e in slide["callouts"]), key=lambda e: e.get("y", 0))
    if slide.get("items") is not None and slide["type"] in ("goals", "summary"):
        clean["items"] = [_as_text(item["text"] if isinstance(item, dict) else item) for item in slide["items"]]
    elif slide.get("items") is not None:
        clean["items"] = [_normalize_item(item) for item in slide["items"]]
    clean["rows"] = [[_as_text(cell) for cell in row] for row in slide.get("rows") or []]
    for side in ("left", "right"):
        if isinstance(slide.get(side), dict):
            heading = slide[side].get("heading") if slide[side].get("heading") is not None else slide[side].get("head")
            clean[side] = {"heading": _as_text(heading),
                           "items": [_as_text(i) for i in slide[side].get("items") or []]}
    return clean


def build_pptx(spec: dict, out_path: Path, student: bool = False) -> list[str]:
    validate(spec)
    deck = Deck(THEMES[spec.get("theme", "basic")], spec.get("template"), student)
    for slide in spec["slides"]:
        RENDERERS[slide["type"]](deck, normalize(slide))
    # 생성기가 이미 넘침을 알린 장은 다듬기 단계가 같은 경고를 또 내지 않게 알려 준다 ("3쪽 ..." -> "3번째 장: ...")
    known = [re.sub(r"^(\d+)쪽 ", lambda found: f"{found.group(1)}번째 장: ", warning) for warning in deck.warnings]
    deck.warnings.extend(polish(deck.prs, known))
    stamp_properties(deck.prs)
    deck.prs.save(str(out_path))
    return deck.warnings


def _check_paths(input_path: Path, output_path: Path, template: str | None) -> None:
    if output_path.suffix.lower() != OUTPUT_SUFFIX:
        raise ValueError(f"출력 파일 이름은 {OUTPUT_SUFFIX}로 끝나야 함 (받은 값: {output_path.name})")
    output = output_path.resolve()
    if output == input_path.resolve():
        raise ValueError("출력 파일이 입력 JSON 파일과 같을 수 없음 (원본이 덮어써집니다)")
    if template and output == Path(template).resolve():
        raise ValueError("출력 파일이 템플릿 파일과 같을 수 없음 (템플릿이 덮어써집니다)")


def _resolve_paths(spec: dict, input_path: Path) -> dict:
    """상대 경로(템플릿, 그림)를 입력 JSON이 있는 폴더 기준 경로로 바꾼 새 spec을 돌려준다."""
    base = input_path.resolve().parent
    for slide in spec["slides"]:
        if slide.get("type") == "figure" and isinstance(slide.get("image"), str) and slide["image"]:
            check_inside_folder(slide["image"], base)

    def resolve(value):
        return str(base / value) if isinstance(value, str) and value and not Path(value).is_absolute() else value

    slides = [{**slide, "image": resolve(slide["image"])} if slide.get("type") == "figure" and slide.get("image") else slide
              for slide in spec["slides"]]
    template = {"template": resolve(spec["template"])} if spec.get("template") is not None else {}
    return {**spec, **template, "slides": slides}


def _run(args: list[str], student: bool = False) -> list[str]:
    input_path, output_path = Path(args[0]), Path(args[1])
    spec = read_input_json(input_path)
    validate(spec, check_files=False)
    spec = _resolve_paths(spec, input_path)
    _check_paths(input_path, output_path, spec.get("template"))
    return build_pptx(spec, output_path, student)


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    parsed = split_student_flag(sys.argv[1:] if argv is None else argv)
    if parsed is None or len(parsed[0]) != 2:
        sys.stdout.write("사용법: python make_pptx.py 입력.json 출력.pptx [--student]\n")
        return 2
    args, student = parsed
    try:
        warnings = _run(args, student)
    except OSError as error:
        sys.stdout.write(f"입력 오류: {describe_os_error(error)}\n")
        return 1
    except (ValueError, KeyError, TypeError, AttributeError) as error:   # JSON 문법 오류도 read_input_json이 ValueError로 바꾼다
        sys.stdout.write(f"입력 오류: {error}\n")
        return 1
    except Exception as error:  # noqa: BLE001 - 어떤 입력에도 traceback 대신 안내 문구를 보인다
        sys.stdout.write(f"입력 오류: 예상하지 못한 입력입니다 ({type(error).__name__})\n")
        return 1
    sys.stdout.write(f"완료: {args[1]}\n")
    for warning in warnings:
        sys.stdout.write(f"확인 필요: {warning}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
