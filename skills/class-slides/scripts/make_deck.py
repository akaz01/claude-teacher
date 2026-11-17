"""수업 PPT 폼 생성기. 교과별 색, 도식 장, 핵심 띠가 있는 16:9 슬라이드를 만든다.

모든 글자는 도형 안에서 가로·세로 가운데로 맞추고, 칸을 넘으면 글자 크기를 줄인다.
교실 기준(18pt)보다 작아지면 멈추지 않고 "확인 필요" 경고를 낸다. 최소 크기는 14pt다.
설명 행(content)은 줄 수에 비례해 높이를 나누고, 글자가 20pt보다 작아질 만큼 담기면 다음 장으로 나눈다.
수업 안내(outline)가 주기마다 있는지도 검사한다 (빠진 주기를 경고).

입력 JSON:
{
  "subject": "수학",                  # 국어/영어/수학/사회/과학 (색이 정해짐, 그 밖은 기본색)
  "unit": "일차방정식", "meta": "중학교 1학년 · 3/8차시",
  "slides": [
    # 도입
    {"type": "cover", "title": "제목"},
    {"type": "goals", "items": ["학습 목표"]},
    {"type": "keywords", "words": [{"word": "낱말", "meaning": "짧은 뜻"}]},
    {"type": "outline", "items": ["주기 이름"], "current": 0},     # 주기가 시작될 때마다 current를 바꿔 한 장씩
    {"type": "section", "title": "소주제", "subtitle": "질문이나 짧은 구"},

    # 설명 장 (key를 쓰면 핵심 띠가 붙는다)
    {"type": "content", "title": "제목", "items": ["항목", {"text": "항목", "sub": ["하위 항목"]}], "key": "핵심 문장"},
    {"type": "flow", "title": "제목", "steps": [{"head": "단계", "text": "설명"}], "key": "핵심 문장"},
    {"type": "cards", "title": "제목", "cards": [{"head": "머리", "text": "설명"}], "key": "핵심 문장"},
    {"type": "compare", "title": "제목", "left": {"head": "가", "items": ["..."]},
     "right": {"head": "나", "items": ["..."]}, "key": "핵심 문장"},
    {"type": "table", "title": "제목", "header": ["구분"], "rows": [["가"]], "key": "핵심 문장"},
    {"type": "figure", "title": "제목", "image": "그림.png", "caption": "교과서 32쪽",
     "callouts": ["그림 옆 설명", {"text": "선을 긋는 설명", "x": 0.5, "y": 0.3}], "key": "핵심 문장"},

    # 확인·연습·답 장 (답 장이 뒤에 저절로 붙는다)
    {"type": "check", "question": "문제", "choices": ["가", "나"], "answer": 0, "explain": "왜 맞고 왜 틀린가"},
    {"type": "check", "question": "참일까요?", "truth": false, "reasons": ["근거 가", "근거 나"], "answer": 1},
    {"type": "task", "title": "제목", "steps": ["지시문"], "minutes": 3, "output": "공책에 두 문장",
     "answer": ["답"], "sample": true},
    {"type": "example", "title": "제목", "worked": {"head": "풀이", "lines": ["한 줄"]},
     "problem": {"head": "이제 풀어 봅시다", "lines": ["문제"]}, "answer": ["답"]},
    {"type": "activity", "title": "제목", "time": "20분", "group": "4명 모둠", "roles": "기록, 발표",
     "materials": "비커", "output": "결과표", "steps": ["단계"]},

    # 정리
    {"type": "summary", "items": ["배운 내용"]}
  ]
}
- 모든 장에 "tag"(제목 위 작은 글)와 "notes"(발표자 노트)를 넣을 수 있다. cover를 뺀 장에 노트가 없으면 경고한다.
- 글 안의 **낱말**은 굵게 나오고, 검은 글에서는 교과 색도 입는다. 별표는 화면에 남지 않는다.
- quiz는 check와 같다. answer는 0부터 세고 선택지는 5개까지다.
- check, task, example은 답 장을 뒤에 붙이고, 노트에 답을 넣는다. "reveal": false면 답 장을 만들지 않는다.
  답 장의 노트는 "reveal_notes"에 쓴다 (없으면 notes). 다음 행동을 여기에 적는다.
- check의 truth는 참·거짓 문제다. reasons를 함께 쓰면 근거 고르기가 붙고, 이때 answer는 reasons의 번호다.
- task의 sample이 true면 답 칸의 이름이 "이렇게 쓸 수 있어요"가 된다. 답이 하나가 아닐 때 쓴다.
- content의 항목이 5개를 넘거나 글자가 20pt보다 작아질 만큼 많으면 다음 장에 "(계속)"을 붙여 잇는다.
- figure의 image는 입력 JSON이 있는 폴더를 기준으로 찾고, 없으면 [그림: caption] 자리를 만든다.
  callouts의 x, y는 그림 안의 위치(0~1)이며, 쓰면 설명에서 그 점까지 선을 긋는다. 선이 엇갈리지 않게 y 순서로 놓는다.
- compare의 head는 heading으로, cover의 unit, meta는 장마다 다시 쓸 수 있다.

- 입력 형식이 틀리면(최상위가 객체가 아님, 항목이 목록이 아님, 표 행의 칸이 머리보다 많음 등) 몇 번째 장인지 알리고 멈춘다.
- --student를 붙이면 학생용 사본을 만든다: 답 장을 만들지 않고, 발표자 노트를 모두 비운다 (노트에 정답이 있으므로).
  확인 문제 장에는 정답 표시가 남지 않는다. 같은 입력을 make_pptx.py에 줘도 같은 동작이다.

사용법:
    python make_deck.py 입력.json 수업.pptx
    python make_deck.py 입력.json 학생용.pptx --student
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.parts.image import Image
from pptx.util import Inches, Pt

from make_deck_check import (ACTIVITY_FACTS, check_output_path, describe_os_error, read_input_json,
                             split_student_flag, use_utf8_output, validate_deck)
from pptx_safety import check_image_size, check_inside_folder, stamp_properties
from slide_check import polish
from make_deck_base import *  # noqa: F401,F403  (상수·글자 크기 도우미·Deck: 시험도 make_deck에서 가져다 씀)


def render_cover(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    unit, meta = spec.get("unit", deck.doc["unit"]), spec.get("meta", deck.doc.get("meta", ""))
    deck.shape(slide, 0, 0, SLIDE_W, SLIDE_H, fill=deck.dark)
    deck.shape(slide, 1.4, 1.5, SLIDE_W - 2.8, 4.5, fill=WHITE, kind=MSO_SHAPE.ROUNDED_RECTANGLE)
    deck.shape(slide, 1.9, 1.9, SLIDE_W - 3.8, 0.55, f"{deck.doc['subject']}  |  {unit}", 22, True, deck.dark)
    deck.shape(slide, 1.9, 2.55, SLIDE_W - 3.8, 1.9, spec["title"], 50, True, INK)
    deck.shape(slide, 5.4, 4.6, SLIDE_W - 10.8, 0.05, fill=deck.dark)
    deck.shape(slide, 1.9, 4.8, SLIDE_W - 3.8, 0.6, meta, 20, False, MUTED)


def render_section(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.shape(slide, 0, 0, SLIDE_W, SLIDE_H, fill=deck.dark)
    deck.shape(slide, 1.4, 2.2, SLIDE_W - 2.8, 1.7, spec["title"], 44, True, WHITE)
    if spec.get("subtitle"):
        deck.shape(slide, 1.4, 4.0, SLIDE_W - 2.8, 1.0, spec["subtitle"], 28, False, WHITE)


def _numbered_rows(deck: Deck, slide, items: list[str], top: float = BODY_TOP, bottom: float = BODY_BOTTOM,
                   size: float = 30, gap: float = GAP) -> None:
    height, ys = row_positions(len(items), top, bottom, gap=gap)
    badge = min(BADGE, height)
    x = MARGIN + badge + 0.12
    width = SLIDE_W - MARGIN - x
    size = common_size(items, width, height, size)
    for index, (y, text) in enumerate(zip(ys, items)):
        deck.shape(slide, x, y, width, height, text, size, False, INK, deck.tint, kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.shape(slide, MARGIN, y + (height - badge) / 2, badge, badge, str(index + 1), 26, True, WHITE, deck.dark,
                   kind=MSO_SHAPE.OVAL)


def render_list(deck: Deck, spec: dict, title: str) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, {**spec, "title": spec.get("title", title)})
    _numbered_rows(deck, slide, [item_text(item) for item in spec["items"]])


def render_keywords(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, {**spec, "title": spec.get("title", "오늘의 핵심어")}, "핵심어")
    words = spec["words"]
    height, ys = row_positions(len(words), BODY_TOP, BODY_BOTTOM)
    word_size = common_size([entry["word"] for entry in words], 3.2, height, 28)
    meaning_size = common_size([entry["meaning"] for entry in words], BODY_W - 3.4, height, 26)
    for y, entry in zip(ys, words):
        deck.shape(slide, MARGIN, y, 3.2, height, entry["word"], word_size, True, WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.shape(slide, MARGIN + 3.4, y, BODY_W - 3.4, height, entry["meaning"], meaning_size, False, INK, deck.tint,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def render_outline(deck: Deck, spec: dict) -> None:
    items, current = spec["items"], spec.get("current")
    if current is not None and current not in range(len(items)):
        raise ValueError(f"current는 0부터 {len(items) - 1}까지 쓸 수 있음")
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, {**spec, "title": spec.get("title", "오늘 수업의 순서")}, "수업 안내")
    height, ys = row_positions(len(items), BODY_TOP, BODY_BOTTOM)
    labels = [f"지금 ▶ {plain(text)}" if index == current else text for index, text in enumerate(items)]
    size = common_size(labels, BODY_W - 2.0, height, 30)
    for index, (y, label) in enumerate(zip(ys, labels)):
        now = index == current
        deck.shape(slide, MARGIN + 1.0, y, BODY_W - 2.0, height, label, size, now,
                   WHITE if now else INK, deck.dark if now else deck.tint, kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def render_content(deck: Deck, spec: dict) -> None:
    if not spec["items"]:
        raise ValueError("목록이 비어 있음")
    texts = [item_text(item) for item in spec["items"]]
    bottom = deck.body_bottom(spec)
    for start, end in content_pages(texts, bottom):
        slide = deck.slide(None if start else spec.get("notes"))
        deck.heading(slide, {**spec, "title": spec["title"] + (CONTINUED if start else "")})
        heights, ys, size = content_layout(texts[start:end], bottom)
        for y, height, text in zip(ys, heights, texts[start:end]):
            deck.shape(slide, MARGIN + 0.4, y, BODY_W - 0.8, height, text, size, False, INK, deck.tint,
                       kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.key(slide, spec.get("key"))


def render_flow(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, spec)
    steps = spec["steps"]
    width, xs = deck.columns(len(steps), 0.12)
    text_h = deck.body_bottom(spec) - BODY_TOP - 1.2
    head_size = common_size([step["head"] for step in steps], width - CHEVRON_INSET, 1.0, 22)
    text_size = common_size([step["text"] for step in steps], width - 0.2, text_h, 26)
    for x, step in zip(xs, steps):
        deck.shape(slide, x, BODY_TOP, width, 1.0, step["head"], head_size, True, WHITE, deck.dark, kind=MSO_SHAPE.CHEVRON)
        deck.shape(slide, x + 0.1, BODY_TOP + 1.2, width - 0.2, text_h, step["text"], text_size, False, INK, deck.tint,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)
    deck.key(slide, spec.get("key"))


def render_cards(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, spec)
    width, xs = deck.columns(len(spec["cards"]))
    bottom = deck.body_bottom(spec)
    head_size = common_size([card["head"] for card in spec["cards"]], width - 0.4, 0.8, 24)
    text_size = common_size([card["text"] for card in spec["cards"]], width - 0.4, bottom - BODY_TOP - 1.3, 28)
    for x, card in zip(xs, spec["cards"]):
        deck.shape(slide, x, BODY_TOP, width, bottom - BODY_TOP, line=deck.dark, fill=WHITE,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.shape(slide, x + 0.2, BODY_TOP + 0.2, width - 0.4, 0.8, card["head"], head_size, True, WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.shape(slide, x + 0.2, BODY_TOP + 1.1, width - 0.4, bottom - BODY_TOP - 1.3, card["text"], text_size)
    deck.key(slide, spec.get("key"))


def render_compare(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, spec)
    width, xs = deck.columns(2, 1.0)
    bottom = deck.body_bottom(spec)
    sides = (spec["left"], spec["right"])
    text_h = bottom - BODY_TOP - 0.95
    size = common_size(["\n".join(side["items"]) for side in sides], width, text_h, 30)
    for x, side in zip(xs, sides):
        deck.shape(slide, x, BODY_TOP, width, 0.8, side.get("head") or side["heading"], 26, True, WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.shape(slide, x, BODY_TOP + 0.95, width, text_h, "\n".join(side["items"]), size, False, INK,
                   deck.tint, kind=MSO_SHAPE.ROUNDED_RECTANGLE)
    deck.shape(slide, SLIDE_W / 2 - 0.4, (BODY_TOP + bottom) / 2 - 0.4, 0.8, 0.8, "vs", 20, True, WHITE, INK,
               kind=MSO_SHAPE.OVAL)
    deck.key(slide, spec.get("key"))


def render_table(deck: Deck, spec: dict) -> None:
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, spec)
    rows = [spec["header"], *spec["rows"]]
    bottom = deck.body_bottom(spec)
    height = (bottom - BODY_TOP - 0.08 * (len(rows) - 1)) / len(rows)
    width, xs = deck.columns(len(spec["header"]), 0.08)
    head_size = common_size(spec["header"], width, height, 28)
    cell_size = common_size([text for row in spec["rows"] for text in row] or [""], width, height, 26)
    for row_index, row in enumerate(rows):
        y = BODY_TOP + row_index * (height + 0.08)
        for x, text in zip(xs, row):
            head = row_index == 0
            deck.shape(slide, x, y, width, height, text, head_size if head else cell_size, head, WHITE if head else INK,
                       deck.dark if head else deck.tint)
    deck.key(slide, spec.get("key"))


def _callout(item: str | dict) -> dict:
    entry = {"text": item} if isinstance(item, str) else item
    point = [entry[name] for name in ("x", "y") if name in entry]
    if any(not 0 <= value <= 1 for value in point):
        raise ValueError("callouts의 x, y는 0~1 사이여야 함")
    return entry


def _place_image(deck: Deck, slide, raw_path: str, x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    """그림을 비율을 지켜 칸 가운데에 놓고 실제 자리를 돌려준다."""
    check_inside_folder(raw_path, deck.base_dir)
    path = deck.base_dir / raw_path
    if not path.is_file():
        raise ValueError(f"그림 파일을 찾을 수 없음: {raw_path}")
    check_image_size(path)
    try:
        width_px, height_px = Image.from_file(str(path)).size
    except OSError as error:        # 그림이 아니거나 깨진 파일 (UnidentifiedImageError도 OSError)
        raise ValueError(f"그림 파일을 열 수 없음: {raw_path}") from error
    scale = min(w / width_px, h / height_px)
    pic_w, pic_h = width_px * scale, height_px * scale
    left, top = x + (w - pic_w) / 2, y + (h - pic_h) / 2
    slide.shapes.add_picture(str(path), Inches(left), Inches(top), Inches(pic_w), Inches(pic_h))
    return left, top, pic_w, pic_h


def _draw_pointer(deck: Deck, slide, start: tuple[float, float], end: tuple[float, float]) -> None:
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(start[0]), Inches(start[1]), Inches(end[0]), Inches(end[1]))
    line.line.color.rgb = RGBColor.from_string(deck.dark)
    line.line.width = Pt(1.5)
    dot = 0.14
    deck.shape(slide, end[0] - dot / 2, end[1] - dot / 2, dot, dot, fill=deck.dark, kind=MSO_SHAPE.OVAL)


def render_figure(deck: Deck, spec: dict) -> None:
    callouts = sorted((_callout(item) for item in spec.get("callouts", [])), key=lambda entry: entry.get("y", 0))
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, spec)
    bottom = deck.body_bottom(spec)
    caption = spec.get("caption")
    area_h = bottom - BODY_TOP - (0.5 if caption and spec.get("image") else 0)
    area_w = BODY_W * 0.62 if callouts else BODY_W
    if spec.get("image"):
        placed = _place_image(deck, slide, spec["image"], MARGIN, BODY_TOP, area_w, area_h)
        if caption:
            deck.shape(slide, MARGIN, BODY_TOP + area_h + 0.05, area_w, 0.45, caption, 16, False, MUTED, floor=16)
    else:
        placed = None
        deck.shape(slide, MARGIN, BODY_TOP, area_w, area_h, f"[그림: {caption or spec['title']}]", 24, False, MUTED,
                   line=MUTED, kind=MSO_SHAPE.ROUNDED_RECTANGLE)
    if callouts:
        x = MARGIN + area_w + GAP
        height, ys = row_positions(len(callouts), BODY_TOP, bottom, limit=1.3)
        for y, entry in zip(ys, callouts):
            deck.shape(slide, x, y, SLIDE_W - MARGIN - x, height, entry["text"], 24, False, INK, deck.tint,
                       kind=MSO_SHAPE.ROUNDED_RECTANGLE)
            if placed and "x" in entry and "y" in entry:
                left, top, pic_w, pic_h = placed
                _draw_pointer(deck, slide, (x, y + height / 2), (left + entry["x"] * pic_w, top + entry["y"] * pic_h))
    deck.key(slide, spec.get("key"))


def _answer_index(spec: dict, options: list[str]) -> int:
    answer = spec.get("answer")
    if isinstance(answer, bool) or not isinstance(answer, int) or answer not in range(len(options)):
        raise ValueError(f"answer는 0부터 {len(options) - 1}까지의 번호여야 함")
    return answer


def _check_options(spec: dict) -> list[str]:
    options = spec.get("reasons", []) if "truth" in spec else spec["choices"]
    if len(options) > MAX_CHOICES:
        raise ValueError(f"선택지는 {MAX_CHOICES}개까지 쓸 수 있음 (지금 {len(options)}개). 문항을 나누세요")
    if options:
        _answer_index(spec, options)
    return options


def _check_answer_line(spec: dict, options: list[str]) -> str:
    parts = ["참" if spec["truth"] else "거짓"] if "truth" in spec else []
    if options:
        parts.append(f"{CHOICE_MARKS[spec['answer']]} {plain(options[spec['answer']])}")
    return "정답: " + ", ".join(parts)


def _choice_grid(deck: Deck, slide, options: list[str], answer: int | None, top: float, bottom: float) -> None:
    """선택지를 두 줄 격자로 놓는다. answer를 주면 그 선택지를 표시와 굵기로 드러낸다."""
    width, xs = deck.columns(2)
    marked = [f"{ANSWER_MARK} {CHOICE_MARKS[index]}  {plain(text)}" for index, text in enumerate(options)]
    one_line = (width - 2 * PAD) / (CHOICE_FONT / 72)
    if len(options) <= 3 and max(text_units(text) for text in marked) > one_line:
        width, xs = BODY_W, [MARGIN]
    rows = math.ceil(len(options) / len(xs))
    height = min(1.15, (bottom - top - ROW_GAP * (rows - 1)) / rows)
    size = common_size(marked, width, height, CHOICE_FONT)
    for index, text in enumerate(options):
        correct = index == answer
        y = top + (index // len(xs)) * (height + ROW_GAP)
        deck.shape(slide, xs[index % len(xs)], y, width, height, marked[index] if correct else f"{CHOICE_MARKS[index]}  {text}",
                   size, correct, WHITE if correct else INK, deck.dark if correct else WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def _truth_row(deck: Deck, slide, truth: bool, reveal: bool, top: float) -> None:
    width, xs = deck.columns(2)
    for x, value, label in zip(xs, (True, False), ("O  참", "X  거짓")):
        correct = reveal and value == truth
        deck.shape(slide, x, top, width, 0.8, f"{ANSWER_MARK} {label}" if correct else label, 28, correct,
                   WHITE if correct else INK, deck.dark if correct else WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def _check_slide(deck: Deck, spec: dict, options: list[str], reveal: bool) -> None:
    line = _check_answer_line(spec, options)
    slide = deck.slide(join_notes((spec.get("reveal_notes") or spec.get("notes")) if reveal else spec.get("notes"), line))
    tag = spec.get("tag") or "확인 문제"
    deck.heading(slide, {**spec, "title": spec.get("title") or ("정답을 확인해 봅시다" if reveal else "생각해 봅시다"),
                         "tag": f"{tag} · 정답" if reveal else tag})
    deck.shape(slide, MARGIN, BODY_TOP, BODY_W, 1.2, spec["question"], 32, True, INK, deck.tint,
               kind=MSO_SHAPE.ROUNDED_RECTANGLE)
    top = BODY_TOP + 1.35
    bottom = BODY_BOTTOM - (0.85 if spec.get("explain") else 0)
    if "truth" in spec:
        _truth_row(deck, slide, spec["truth"], reveal, top)
        top += 0.95
        if options:
            deck.shape(slide, MARGIN, top, BODY_W, 0.5, "왜 그럴까요?", 20, True, deck.dark)
            top += 0.55
    if options:
        _choice_grid(deck, slide, options, spec["answer"] if reveal else None, top, bottom)
    if reveal and spec.get("explain"):
        deck.shape(slide, MARGIN, BODY_BOTTOM - 0.72, BODY_W, 0.72, spec["explain"], 24, False, INK, deck.tint,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def render_check(deck: Deck, spec: dict) -> None:
    options = _check_options(spec)
    _check_slide(deck, spec, options, False)
    if spec.get("reveal", True) and not deck.student:
        _check_slide(deck, spec, options, True)


def _task_slide(deck: Deck, spec: dict, answers: list[str], reveal: bool) -> None:
    label = "이렇게 쓸 수 있어요" if spec.get("sample") else "답"
    minutes = f"{spec['minutes']}분" if spec.get("minutes") else ""
    hint = "  ·  ".join(part for part in (minutes, spec.get("output")) if part)
    answer_line = f"{label}: " + " / ".join(plain(line) for line in answers) if answers else ""
    notes = (spec.get("reveal_notes") or spec.get("notes")) if reveal else spec.get("notes")
    slide = deck.slide(join_notes(notes, answer_line, f"시간: {minutes}" if minutes else ""))
    tag = spec.get("tag") or "연습"
    deck.heading(slide, {**spec, "tag": f"{tag} · 답" if reveal else tag})
    band_h = min(2.3, 0.75 + 0.5 * len(answers)) if answers else (0.8 if hint else 0)
    band_top = BODY_BOTTOM - band_h
    _numbered_rows(deck, slide, spec["steps"], BODY_TOP, band_top - (ROW_GAP if band_h else 0), 26, ROW_GAP)
    if reveal:
        text = "\n".join([f"{ANSWER_MARK} {label}", *(plain(line) for line in answers)])
        deck.shape(slide, MARGIN, band_top, BODY_W, band_h, text, 26, True, deck.dark, WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE, line_width=3)
    elif hint:
        deck.shape(slide, MARGIN, band_top, BODY_W, band_h, hint, 24, True, INK, WHITE, deck.dark,
                   kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def render_task(deck: Deck, spec: dict) -> None:
    answers = as_lines(spec.get("answer"))
    _task_slide(deck, spec, answers, False)
    if answers and spec.get("reveal", True) and not deck.student:
        _task_slide(deck, spec, answers, True)


def _example_slide(deck: Deck, spec: dict, answers: list[str], reveal: bool) -> None:
    answer_line = "답: " + " / ".join(plain(line) for line in answers) if answers else ""
    notes = (spec.get("reveal_notes") or spec.get("notes")) if reveal else spec.get("notes")
    slide = deck.slide(join_notes(notes, answer_line))
    tag = spec.get("tag") or "예제"
    deck.heading(slide, {**spec, "tag": f"{tag} · 답" if reveal else tag})
    width, xs = deck.columns(2, 0.5)
    worked, problem = spec["worked"], spec["problem"]
    shown = [f"**{ANSWER_MARK} {plain(line)}**" for line in answers] if reveal else []
    sides = ((worked.get("head", "풀이 예"), worked["lines"]), (problem.get("head", "이제 풀어 봅시다"), [*problem["lines"], *shown]))
    for x, (head, lines) in zip(xs, sides):
        deck.shape(slide, x, BODY_TOP, width, 0.8, head, 26, True, WHITE, deck.dark, kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        deck.shape(slide, x, BODY_TOP + 0.95, width, BODY_BOTTOM - BODY_TOP - 0.95, "\n".join(lines), 28, False, INK,
                   deck.tint, kind=MSO_SHAPE.ROUNDED_RECTANGLE)


def render_example(deck: Deck, spec: dict) -> None:
    answers = as_lines(spec.get("answer"))
    _example_slide(deck, spec, answers, False)
    if answers and spec.get("reveal", True) and not deck.student:
        _example_slide(deck, spec, answers, True)


def render_activity(deck: Deck, spec: dict) -> None:
    steps = spec["steps"]
    if len(steps) > MAX_ROWS:
        deck.warn(f"방법이 {MAX_ROWS}줄을 넘음. 자세한 방법은 학습지로 보내세요")
    slide = deck.slide(spec.get("notes"))
    deck.heading(slide, spec, "활동")
    facts = [(label, spec[name]) for label, name in ACTIVITY_FACTS if spec.get(name)]
    top = BODY_TOP
    if facts:
        width, xs = deck.columns(len(facts), 0.15)
        texts = [f"**{label}**\n{value}" for label, value in facts]
        size = common_size(texts, width, 1.0, 22)
        for x, text in zip(xs, texts):
            deck.shape(slide, x, top, width, 1.0, text, size, False, INK, WHITE, deck.dark,
                       kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        top += 1.15
    _numbered_rows(deck, slide, steps, top, BODY_BOTTOM, 26, ROW_GAP)


RENDERERS = {
    "cover": render_cover, "section": render_section, "keywords": render_keywords, "outline": render_outline,
    "content": render_content, "flow": render_flow, "cards": render_cards, "compare": render_compare,
    "table": render_table, "figure": render_figure, "check": render_check, "quiz": render_check,
    "task": render_task, "example": render_example, "activity": render_activity,
    "goals": lambda deck, spec: render_list(deck, spec, "오늘의 학습 목표"),
    "summary": lambda deck, spec: render_list(deck, spec, "오늘 배운 내용"),
}


def _render(deck: Deck, spec: dict) -> None:
    where = f"{deck.number}번째 장({spec.get('type')})"
    try:
        RENDERERS[spec["type"]](deck, spec)
    except KeyError as error:
        raise ValueError(f"{where}: '{error.args[0]}' 값이 필요함") from error
    except (TypeError, AttributeError) as error:
        raise ValueError(f"{where}: 입력 형식이 맞지 않음 (글자, 목록, {{...}} 자리를 입력 설명과 견주어 보세요)") from error
    except ValueError as error:
        raise ValueError(f"{where}: {error}") from error


def outline_warnings(slides: list[dict]) -> list[str]:
    """주기마다 수업 안내(outline) 장이 있는지 본다: 안내 장의 current가 주기 번호를 빠짐없이 가리켜야 한다."""
    outlines = [spec for spec in slides if spec.get("type") == "outline"]
    if not outlines:
        sections = sum(1 for spec in slides if spec.get("type") == "section")
        return [f"전체: 소주제(section) 장이 {sections}개인데 수업 안내(outline) 장이 없음. 주기마다 지금 위치를 보여 주세요"] if sections >= 2 else []
    items = max((spec.get("items") or [] for spec in outlines), key=len)
    shown = {spec.get("current") for spec in outlines}
    missing = [f"{plain(str(name))}(current={index})" for index, name in enumerate(items) if index not in shown]
    if not missing:
        return []
    return [f"전체: 수업 안내 장이 없는 주기가 있음: {', '.join(missing)}. 주기가 시작될 때마다 current를 바꾼 수업 안내 장을 두세요"]


def build_deck(doc: dict, out_path: Path, base_dir: Path | None = None, student: bool = False) -> list[str]:
    """덱을 저장하고 교사가 확인할 경고를 돌려준다. base_dir은 그림의 상대 경로 기준이다. student면 학생용 사본이다."""
    validate_deck(doc, tuple(RENDERERS))
    deck = Deck(doc, base_dir or Path.cwd(), student)
    for number, spec in enumerate(doc["slides"], 1):
        deck.number = number
        _render(deck, spec)
        if spec["type"] != "cover" and not spec.get("notes") and not student:
            deck.warn("발표자 노트가 없음")
    deck.warnings.extend(outline_warnings(doc["slides"]))
    deck.warnings.extend(polish(deck.prs, deck.warnings))
    stamp_properties(deck.prs)
    deck.prs.save(out_path)
    return deck.warnings


USAGE = "사용법: python make_deck.py 입력.json 수업.pptx [--student]\n"


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    parsed = split_student_flag(sys.argv[1:] if argv is None else argv)
    if parsed is None or len(parsed[0]) != 2:
        sys.stdout.write(USAGE)
        return 2
    (source, target), student = (Path(arg) for arg in parsed[0]), parsed[1]
    try:
        check_output_path(source, target)
        warnings = build_deck(read_input_json(source), target, source.resolve().parent, student)
    except ValueError as error:
        sys.stdout.write(f"입력 오류: {error}\n")
        return 1
    except OSError as error:
        sys.stdout.write(f"입력 오류: {describe_os_error(error)}\n")
        return 1
    sys.stdout.write(f"완료: {target}\n")
    for warning in warnings:
        sys.stdout.write(f"확인 필요: {warning}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
