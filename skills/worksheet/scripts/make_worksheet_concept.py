"""개념 정리 학습지(topics) 명세 만들기. 앱 디자인 학습지(write_sheet.py)와 눈으로 같은 모양의 한글(hwpx)을 낸다.

모든 크기는 앱 화면 px(1px = 0.75pt)로 적는다. 머리 띠 바탕은 그라데이션 사각형, 칩·번호 동그라미·이름 칸은 한글 도형
(글상자)이고, 나머지는 한글 표와 문단이다. 그림은 쓰지 않으므로 한글에서 글자·도형·칸을 모두 고칠 수 있다.
옆 칸(용어 풀이·연표)은 종이 기준으로 놓은 표라서 앱처럼 오른쪽에 따로 선다.
빈칸은 글자 음영(연노랑) + 밑줄이다. 학생용은 공백이고, 교사용은 그 안에 파랑 굵은 답이 들어간다.
빈칸 너비는 답 길이와 상관없이 한 학습지 안에서 모두 같다(가장 긴 답이 들어갈 너비). [[답]]은 build_concept_spec 끝에서
모든 글(칸·글 조각·도형·문서 제목·꼬리말)을 한 번에 훑어 풀기 때문에 학생용에는 답이 남을 길이 없다.
"""

from __future__ import annotations

from make_worksheet_base import *  # noqa: F401,F403  (색·크기·칸 도우미: make_worksheet.py와 시험이 여기서 가져다 씀)
from make_worksheet_base import _strings
from make_worksheet_quiz import (  # noqa: F401
    _dash, challenge_table, essay_table, explain_table, options_table, ox_table, question_blocks, question_head, reach_table,
    short_answer_table, source_table)


def _need(doc: dict, *keys: str) -> None:
    for key in keys:
        if not doc.get(key):
            raise ValueError(f"'{key}' 값이 필요함")


# ---------------------------------------------------------------- 머리 띠·학습 목표·마디 띠

ID_LABELS = (("학년", 28), ("반", 28), ("번", 28), ("이름", 92))


def ids_block() -> dict:
    """머리 띠 오른쪽의 '학년 [ ] 반 [ ] 번 [ ] 이름 [ ]': 글과 흰 칸을 각자 칸에 두고 세로 가운데로 맞춘다."""
    widths, cells = [], []
    for index, (label, box_w) in enumerate(ID_LABELS):
        label_w = round(text_px(label, 9) * WIDTH_SLACK + 8)
        gap = 0 if index == len(ID_LABELS) - 1 else 9
        widths += [label_w, box_w + gap]
        cells += [cell([run(label, 9, BAND_TEXT)], align="right", valign="center", pad=(0, 4, 0, 0), height_px=22),
                  cell([{"shape": "round", "w": box_w, "h": 22, "corner": 25, "fill": WHITE}], valign="center",
                       height_px=22)]
    width = sum(widths)
    return table(widths, [cells], paper={"x": BODY_X + BODY_W - width, "y": 18, "width": width, "wrap": "front"})


def band_blocks(doc: dict, teacher: bool) -> list:
    """쪽 위·양옆 끝까지 닿는 남색→파랑 그라데이션 띠. 바탕 사각형과 그 위의 글 표 둘, 이름 칸 표로 이뤄진다."""
    meta = doc.get("meta") or " · ".join(filter(None, (doc.get("subject"), doc.get("unit"), doc.get("lesson"))))
    sub = doc.get("sub", "") + ("  · " + FOOTER_LABEL if teacher else "")
    title = doc["title"]
    pt = next((size for size in (21, 18, 15) if text_px(title, size, True) * WIDTH_SLACK <= 560), 15)
    top = {"valign": "bottom", "height_px": 52}
    bottom = {"valign": "bottom", "height_px": 49}
    rows = [
        [cell([chip(meta, WHITE, NAVY, height=24, pt=9)], pad=(48, 0, 0, 23), **top, colspan=1),
         cell(None, **top, colspan=2)],
        [cell(title, pad=(48, 0, 0, 16), font=SERIF, size=pt, bold=True, color=WHITE, spacing=120, **bottom, colspan=2),
         cell(sub, pad=(0, 48, 0, 20), size=9, color=BAND_TEXT, align="right", **bottom)]]
    backdrop = {"type": "shape", "shape": "rect", "w": PAGE_W, "h": BAND_H, "corner": 0, "fill": NAVY, "fill_to": BLUE,
                "fill_angle": 80, "paper": {"x": 0, "y": 0}}
    text = table([440, 170, 184], rows, paper={"x": 0, "y": 0, "width": PAGE_W, "wrap": "front"})
    return [backdrop, text, ids_block()]


def _goal_rows(doc: dict, teacher: bool) -> list[tuple]:
    """(이름표 글, 이름표 바탕, 본문 글, 글 크기, 글 색) 목록."""
    rows = [("학습 목표", BLUE, "\n".join(text_list(doc["goal"], "goal")), 10.5, INK)]
    if doc.get("question"):
        rows.append(("핵심 질문", NAVY, doc["question"], 10.5, INK))
    lines = text_list(doc.get("standards"), "standards")
    if lines and doc.get("curriculum"):
        lines[0] = f"{doc['curriculum']} · {lines[0]}"
    if teacher and lines:
        rows.append(("교육과정", ANS, "\n".join(lines), 9, ANS))
    return rows


GOAL_TEXT_W = 575


def goal_block(doc: dict, teacher: bool) -> tuple[dict, float]:
    """학습 목표 상자: 하늘색 바탕 + 왼쪽 파랑 굵은 막대 + 둥근 이름표. 글 한 줄이 표 한 행이라
    이름표는 첫 줄과 세로 가운데가 같다. 글의 왼쪽 시작선은 모든 줄이 같다. (표, 높이)"""
    groups = _goal_rows(doc, teacher)
    visual = []         # (이름표 또는 None, 글, 크기, 색, 줄 수)
    for label, fill, text, pt, color in groups:
        for index, line in enumerate(text.split("\n")):
            visual.append(((label, fill) if index == 0 else None, line, pt, color,
                           wrapped_lines(line, GOAL_TEXT_W, pt), index == len(text.split("\n")) - 1))
    out, height = [], 0.0
    for index, (label, line, pt, color, count, group_end) in enumerate(visual):
        first, last = index == 0, index == len(visual) - 1
        pitch = pt * PX_PER_PT * (LINE_160 if pt > 9 else LINE_145) / 100
        pad_top = BORDER_PX + BOX_PAD if first else 0
        pad_bottom = (BOX_PAD + BORDER_PX if last else 4 if group_end else 0)
        row_h = pad_top + count * pitch + pad_bottom
        sides = {"left": edge(THICK, SKY_LINE)}
        text_sides = {"right": edge(THICK, SKY_LINE)}
        if first:
            sides["top"] = text_sides["top"] = edge(THICK, SKY_LINE)
        if last:
            sides["bottom"] = text_sides["bottom"] = edge(THICK, SKY_LINE)
        chip_cell = cell([chip(label[0], label[1], WHITE, pt=9)] if label else None, fill=SKY, valign="center",
                         height_px=row_h, pad=(21, 12, pad_top, pad_bottom), spacing=100, edges=sides)
        text_cell = cell(line, fill=SKY, valign="center" if count == 1 else "top", height_px=row_h,
                         pad=(0, 16, pad_top, pad_bottom), size=pt, color=color, spacing=LINE_160 if pt > 9 else LINE_145,
                         edges=text_sides)
        out.append([chip_cell, text_cell])
        height += row_h
    return table([111, 587], out), height


def strip_block(mark: str, title: str, right=None) -> tuple[dict, float]:
    """마디 띠: 파랑 번호 칸(흰 명조) + 하늘색 바탕 남색 명조 제목 + 아래 파랑 선. (표, 높이)"""
    line = {"bottom": edge(0.5, BLUE)}
    cells = [cell(mark, fill=BLUE, color=WHITE, font=SERIF, size=12, bold=True, align="center", valign="center",
                  height_px=42, edges=line),
             cell(title, fill=SKY, color=NAVY, font=SERIF, size=15, bold=True, valign="center", pad=(12, 0, 0, 0),
                  edges=line)]
    widths = [40, 658]
    if right is not None:
        cells.append(cell([right], fill=SKY, align="right", valign="center", pad=(0, 10, 0, 0), edges=line))
        widths = [40, 508, 150]
    return table(widths, [cells]), 42


# ---------------------------------------------------------------- 개념 정리 (주제)

LABEL_W = 36
TOPIC_HEAD_H = 24


def _topic_label_width(rows: list) -> int:
    longest = max(len(row["label"]) for row in rows)
    return max(LABEL_W, 12 * longest + 12)


def topic_head(number: int, topic: dict) -> dict:
    """주제 머리: 파랑 동그라미 번호 | 명조 제목 | 연도 칩 | 연한 선. 칸마다 세로 가운데로 맞춘다."""
    title_w = round(text_px(topic["title"], 12, True) * WIDTH_SLACK + 8)
    widths = [24, title_w]
    cells = [cell([circle(str(number), BLUE, 24)], valign="center", height_px=TOPIC_HEAD_H, spacing=100),
             cell(topic["title"], font=SERIF, size=12, bold=True, valign="center", pad=(8, 0, 0, 0),
                  height_px=TOPIC_HEAD_H)]
    if topic.get("tag"):
        tag = chip(topic["tag"], TINT, NAVY, height=20, pt=9)
        widths.append(tag["w"] + 8)
        cells.append(cell([tag], valign="center", pad=(8, 0, 0, 0), height_px=TOPIC_HEAD_H, spacing=100))
    rest = MAIN_W - sum(widths)
    if rest < 0:
        room = MAIN_W - 24 - 8 - (widths[2] if len(widths) > 2 else 0)
        raise ValueError(f"주제 {number} 제목이 너무 김(약 {int(room / (text_px('가', 12, True) * WIDTH_SLACK))}자 이하)")
    if rest >= 14:
        widths.append(rest)
        cells.append(cell([{"shape": "rect", "w": rest - 8, "h": 2, "corner": 0, "fill": TINT}], valign="center",
                          pad=(8, 0, 0, 0), height_px=TOPIC_HEAD_H, spacing=100))
    else:
        widths[-1] += rest
    return table(widths, [cells], width_px=MAIN_W)


def topic_rows(topic: dict, teacher: bool, number: int = 0, notes: list | None = None) -> tuple[dict, float]:
    """주제의 이름표 줄들: 왼쪽 연한 세로선 | 이름표 칩 | 글. 글 한 줄이 표 한 행이고 이름표는 첫 줄과 세로 가운데가 같다.
    빈칸이 넓어 줄이 하나 더 넘치면 notes에 알린다."""
    rows = topic["rows"]
    label_w = _topic_label_width(rows)
    left_w = 13 + 10 + label_w + 10
    out, height = [], 0.0
    for index, row in enumerate(rows):
        lines = row["lines"] if isinstance(row["lines"], list) else [row["lines"]]
        for line_no, line in enumerate(lines):
            count = wrapped_lines(line, MAIN_W - left_w, 10.5)
            if notes is not None and BLANK_MARK.search(line) and count > wrapped_lines(BLANK_MARK.sub("가", line), MAIN_W - left_w, 10.5):
                notes.append(f"확인: 주제 {number}의 '{plain_text(line)[:12]}…' 줄은 빈칸이 넓어 한 줄 넘침 — 줄을 줄이거나 긴 답을 줄이세요")
            row_gap = 4 if line_no == len(lines) - 1 and index < len(rows) - 1 else 0
            row_h = round(count * LINE_PX + row_gap, 1)
            height += row_h
            label = [chip(row["label"], TINT, NAVY, height=18, pt=9, corner=25, w=label_w)] if line_no == 0 else None
            out.append([cell(None, height_px=row_h, edges={"right": edge(0.5, TINT)}),
                        cell(None, height_px=row_h),
                        cell(label, height_px=row_h, pad=(0, 0, 0, row_gap), spacing=100, valign="center"),
                        cell(None, height_px=row_h),
                        cell(line, height_px=row_h, size=10.5, spacing=LINE_145, mark_color=ANS if teacher else None,
                             pad=(0, 0, 0, row_gap), valign="center" if count == 1 else "top")])
    return table([13, 10, label_w, 10, MAIN_W - left_w], out, width_px=MAIN_W), height


# ---------------------------------------------------------------- 옆 칸

def _box_edges(first: bool, last: bool, dashed: bool) -> dict:
    sides = {"left": edge(THICK, SKY_LINE), "right": edge(THICK, SKY_LINE)}
    if last:
        sides["bottom"] = edge(THICK, SKY_LINE)
    if dashed:
        sides["top"] = edge(THIN, SKY_LINE, "DASH")
    return sides


def side_head(title: str, color: str, columns: int) -> dict:
    return cell(title, fill=color, color=WHITE, font=SERIF, size=10.5, bold=True, colspan=columns, valign="center",
                pad=(12, 0, 0, 0), height_px=32)


def gloss_table(terms: list, target: float | None = None) -> tuple[dict, float]:
    """용어 풀이 상자: 남색 머리띠 + 용어(남색 굵게 10.5pt) + 풀이(9pt) + 점선.
    target(상자 전체 높이)이 있으면 남는 높이를 용어 줄마다 고르게 나눠 용어를 고르게 띄운다."""
    minimum = [30 + 19 * wrapped_lines(text if isinstance(text, str) else "\n".join(text), SIDE_W - 26, 9)
               for _, text in terms]
    fixed = 32 + 4 + 9                                  # 머리띠, 첫 줄 위 여백, 끝 줄 아래 여백
    extra = max(0.0, ((target or 0) - fixed - sum(minimum)) / len(terms))
    rows, height = [[side_head("용어 풀이", NAVY, 1)]], 32.0
    for index, ((term, text), base) in enumerate(zip(terms, minimum)):
        first, last = index == 0, index == len(terms) - 1
        desc = text if isinstance(text, str) else "\n".join(text)
        row_h = round(base + extra + (4 if first else 0) + (9 if last else 0), 1)
        height += row_h
        rows.append([cell([run(term, 10.5, NAVY, bold=True), run("\n" + desc, 9, INK)], fill=PALE, height_px=row_h,
                          pad=(12, 12, 4 if first else 0, 9 if last else 0), spacing=LINE_145, valign="center",
                          edges=_box_edges(first, last, index > 0))])
    return table([SIDE_W], rows), height


def timeline_table(title: str, items: list) -> tuple[dict, float]:
    """한눈에 보는 연표 상자: 파랑 머리띠 + (파랑 점, 명조 연도, 내용) 줄."""
    rows = [[side_head(title, BLUE, 3)]]
    height = 32.0
    for index, (year, text) in enumerate(items):
        last = index == len(items) - 1
        row_h = 22.4 + (6 if index == 0 else 0) + (8 if last else 0)
        height += row_h
        pad_top = 2.5 + (6 if index == 0 else 0)
        edges = _box_edges(index == 0, last, False)
        common = {"fill": PALE, "height_px": row_h, "valign": "center", "spacing": LINE_145}
        no_left = {k: v for k, v in edges.items() if k != "left"}
        middle = {k: v for k, v in edges.items() if k not in ("left", "right")}
        no_right = {k: v for k, v in edges.items() if k != "right"}
        rows.append([cell([{"shape": "ellipse", "w": 9, "h": 9, "fill": BLUE, "line": WHITE, "line_px": 2, "pad_px": 0}],
                           pad=(12, 0, pad_top + 4, 0), edges=no_right, **common),
                     cell([run(year, 9, NAVY, bold=True, font=SERIF)], pad=(0, 0, pad_top, 0), edges=middle, **common),
                     cell([run(text, 9, INK)], pad=(0, 6, pad_top, 0), edges=no_left, **common)])
    return table([30, 36, SIDE_W - 66], rows), height


def side_blocks(doc: dict, top: float, bottom: float) -> tuple[list, float]:
    """오른쪽 옆 칸 상자들. 종이 기준 자리에 놓아 왼쪽 본문을 밀지 않는다. 첫 상자는 언제나 용어 풀이이고,
    용어 풀이가 있으면 아래 끝이 bottom에 닿도록 늘어난다. (블록 목록, 마지막 상자의 아래 끝)"""
    side = doc.get("side")
    timeline = timeline_table(side.get("title", "한눈에 보는 연표"), _pairs(side.get("items"), "side.items")) if side else None
    parts = []
    if doc.get("terms"):
        below = (timeline[1] + SIDE_GAP) if timeline else 0
        parts.append(gloss_table(_pairs(doc["terms"], "terms"), bottom - top - below))
    if timeline:
        parts.append(timeline)
    blocks, y = [], top
    for built, height in parts:
        blocks.append({**built, "paper": {"x": SIDE_X, "y": round(y), "width": SIDE_W, "wrap": "front"}})
        y += height + SIDE_GAP
    return blocks, y - SIDE_GAP


def _pairs(value, name: str) -> list:
    if not isinstance(value, list) or not all(isinstance(item, (list, tuple)) and len(item) == 2 for item in value):
        raise ValueError(f"'{name}'은 [이름, 글] 쌍의 목록이어야 함")
    return value



# ---------------------------------------------------------------- 꼬리말

def footer_blocks(doc: dict) -> list:
    """꼬리말: 연파랑 선 위에 파랑 짧은 막대 + 글, 오른쪽 남색 둥근 칩 '쪽 / 전체'."""
    foot = doc.get("foot") or " ".join(filter(None, (" · ".join(filter(None, (doc.get("subject"), doc.get("lesson")))),
                                                    doc.get("title"))))
    top = {"top": edge(THICK, SKY_LINE)}
    bar = cell([{"shape": "round", "w": 22, "h": 4, "corner": 50, "fill": BLUE, "ml_px": 0, "mr_px": 8}], height_px=28,
               valign="center", edges=top)
    text = cell(foot, size=9, color=MUTED, valign="center", height_px=28, edges=top)
    page = cell([{"shape": "round", "w": 44, "h": 18, "fill": NAVY, "color": WHITE, "bold": True, "size": 9,
                  "page_number": True, "pad_px": 2, "ratio": SANS_RATIO}], align="right", valign="center", height_px=28, edges=top)
    return [table([32, 622, 44], [[bar, text, page]], gap_px=[0, 0])]


# ---------------------------------------------------------------- 문서

def score_pill(total: int) -> dict:
    """형성평가 띠 오른쪽의 흰 둥근 '맞은 문항 _ / 7'."""
    text = f"맞은 문항 ____ / {total}"
    return {"shape": "round", "w": round(text_px(text, 9) * WIDTH_SLACK + 28), "h": 22, "fill": WHITE, "line": BLUE,
            "line_px": 1.5, "text": text, "color": NAVY, "bold": True, "size": 9, "pad_px": 4}


def _over(name: str, overflow: float, advice: str) -> str:
    """어림 높이가 쪽 아래 끝을 넘을 때 알림 글."""
    return f"확인: {name} 약 {round(overflow)}px(약 {max(1, round(overflow / LINE_PX))}줄) 넘침 — {advice}"


def concept_page(doc: dict, teacher: bool, notes: list) -> tuple[list, float]:
    """1쪽: 머리 띠·학습 목표·마디 띠 + 주제들 + 옆 칸. 남는 높이를 주제 사이에 고르게 나눠 아래 끝이
    BODY_BOTTOM에 닿게 한다(주제 사이 최소 12px). 넘치면 notes에 알린다. (블록 목록, 쓴 높이)"""
    flow = Flow()
    goal, goal_h = goal_block(doc, teacher)
    flow.add(goal, goal_h, above=BAND_H + 12 - TOP_MARGIN)
    strip, strip_h = strip_block("Ⅰ", "주요 개념 및 내용 정리")
    flow.add(strip, strip_h, above=19)
    top = flow.y + FIRST_TOPIC_GAP
    topics = [topic_rows(topic, teacher, number, notes) for number, topic in enumerate(doc["topics"], 1)]
    used = sum(TOPIC_HEAD_H + 4 + rows_h for _, rows_h in topics)
    count = len(topics)
    gap = (min(MAX_GAP, max(MIN_TOPIC_GAP, (BODY_BOTTOM - top - used) / (count - 1)))
           if count > 1 else MIN_TOPIC_GAP)
    for number, (topic, (rows_table, rows_h)) in enumerate(zip(doc["topics"], topics), 1):
        flow.add(topic_head(number, topic), TOPIC_HEAD_H, above=FIRST_TOPIC_GAP if number == 1 else gap)
        flow.add(rows_table, rows_h, above=4)
    if flow.y > BODY_BOTTOM + 1:
        notes.append(_over("1쪽 개념 정리가", flow.y - BODY_BOTTOM, "주제나 줄을 줄이세요"))
    side, side_end = side_blocks(doc, top, flow.y)
    if side and side_end > BODY_BOTTOM + 1:
        notes.append(_over("1쪽 옆 칸(용어 풀이·연표)이", side_end - BODY_BOTTOM, "용어나 연표 항목을 줄이세요"))
    return [*band_blocks(doc, teacher), *flow.blocks, *side], flow.y


def quiz_gap(free: float, slots: float, teacher: bool) -> tuple[float, float]:
    """형성평가 문항 사이 간격과 넘치는 높이(0 이하면 들어감). 쪽 아래에 SAFETY_PX를 남긴다.
    교사용은 해설 줄만큼 길어 학생용보다 좁은 간격(TEACHER_MIN_QUESTION_GAP)까지 허용한다."""
    if not slots:
        return MIN_QUESTION_GAP, SAFETY_PX - free
    room = free - SAFETY_PX
    least = TEACHER_MIN_QUESTION_GAP if teacher else MIN_QUESTION_GAP
    gap = min(MAX_GAP, max(least, room / slots))
    return gap, slots * gap - room


def quiz_page(doc: dict, teacher: bool, notes: list) -> list:
    """2쪽: 형성평가 + 도달 점검. 남는 높이를 문항 사이에 고르게 나눠 아래 끝이 QUIZ_BOTTOM에 닿게 한다.
    점선은 문항 사이 한가운데, 마지막 문항과 도달 점검 사이는 점선 없이 문항 사이 간격의 1.5배(최소 20px).
    넘치면 notes에 알린다."""
    questions = doc.get("questions") or []
    blocks = [{"type": "page_break"}]
    strip, strip_h = strip_block("Ⅱ", "형성평가", score_pill(len(questions)))
    check = text_list(doc.get("check"), "check") if doc.get("closing", "auto") != "none" else None
    reach, reach_h = reach_table(check) if check else (None, 0.0)
    challenge, challenge_h = challenge_table(doc["challenge"], teacher) if doc.get("challenge") else (None, 0.0)
    measured = [question_blocks(number, item, teacher) for number, item in enumerate(questions, 1)]     # 높이만 잰다
    content = sum(sum(height + (gap if index else 0) for index, (_, height, gap) in enumerate(part)) for part in measured)
    slots = (len(questions) - 1) + (1 if challenge else 0) + (1.5 if reach else 0)
    free = QUIZ_BOTTOM - TOP_PAGE_MARGIN - strip_h - FIRST_QUESTION_GAP - content - challenge_h - reach_h
    gap, overflow = quiz_gap(free, slots, teacher)
    if overflow > 1:
        notes.append(_over("2쪽 형성평가가", overflow, "문항이나 보기·서술 줄을 줄이세요"))
    blocks.append({**strip, "gap_px": [0, FIRST_QUESTION_GAP]})
    for number, item in enumerate(questions, 1):
        for part, _, inner in question_blocks(number, item, teacher, pad_top=gap / 2, gap_above=gap / 2):
            blocks.append({**part, "gap_px": [inner, 0]})
    if challenge:
        blocks.append({**challenge, "gap_px": [gap, 0]})
    if reach:
        blocks.append({**reach, "gap_px": [max(1.5 * gap, 20), 0]})
    return blocks


def resolve_blanks(node, teacher: bool):
    """명세 속 모든 글의 [[답]]을 푼다: 칸·글 조각은 ~~음영 밑줄~~(교사용은 그 칸 글에 파랑 굵게 색), 도형 글은 괄호."""
    if isinstance(node, str):
        return fill_blanks(node, teacher)
    if isinstance(node, list):
        return [resolve_blanks(item, teacher) for item in node]
    if not isinstance(node, dict):
        return node
    if "shape" in node and isinstance(node.get("text"), str):
        return {**node, "text": plain_blank(node["text"], teacher)}
    out = {key: resolve_blanks(value, teacher) for key, value in node.items()}
    holds = [node.get(key) for key in ("text", "run")] + [item for item in node.get("content") or [] if isinstance(item, str)]
    if teacher and any(isinstance(text, str) and BLANK_MARK.search(text) for text in holds):
        out.setdefault("mark_color", ANS)
    return out


def _unresolved(node) -> str | None:
    return next((text for text in _strings(node) if "[[" in text or "]]" in text), None)


def build_concept_spec(doc: dict, teacher: bool = False) -> dict:
    """doc은 make_worksheet.normalize_concept로 모양을 검사·정리한 값이다."""
    _need(doc, "title", "goal", "topics")
    set_widths(doc)
    notes: list[str] = []
    blocks, _ = concept_page(doc, teacher, notes)
    if doc.get("questions"):
        blocks += quiz_page(doc, teacher, notes)
    elif doc.get("check") and doc.get("closing", "auto") != "none":
        notes.append("확인: 형성평가 문항(questions)이 없어 도달 점검(check)을 넣지 않음")
    if doc.get("challenge") and not doc.get("questions"):
        notes.append("확인: 형성평가 문항(questions)이 없어 도전 과제(challenge)를 넣지 않음")
    spec = resolve_blanks({"doc_title": plain_blank(doc["title"], teacher), "margins": "app", "page": "app",
                           "footer": footer_blocks(doc), "blocks": blocks}, teacher)
    left = _unresolved(spec)
    if left is not None:       # 안전장치: 답이 학생용에 남을 수 있는 짝 안 맞는 표시는 만들지 않는다
        raise ValueError(f"[[ ]] 표시의 짝이 맞지 않음 (…{left[:20]}…): 모든 [[답]]은 닫혀야 함")
    return {**spec, "notes": notes}


# ---------------------------------------------------------------- 답이 빠진 곳 알림

def unanswered_concept(doc: dict) -> list[str]:
    """교사용에 답이 빠진 빈칸·문항을 알린다."""
    messages = []
    for number, topic in enumerate(doc["topics"], 1):
        lines = ["\n".join(text_list(row.get("lines"), "lines")) for row in topic.get("rows", [])]
        count = len(TYPED_BLANK.findall("\n".join(lines)))
        if count:
            messages.append(f"주제 {number}: 답이 없는 빈칸 {count}곳")
    for number, item in enumerate(doc.get("questions") or [], 1):
        if question_open(item):
            messages.append(f"문항 {number}: 답이 없거나 맞지 않음")
    challenge = doc.get("challenge")
    if challenge and not has_answer(challenge.get("answer")):
        messages.append("도전 과제: 답이 없음")
    return messages


def question_open(item: dict) -> bool:
    answer = item.get("answer")
    if item.get("kind") == "선택형":
        count = len(item.get("options") or [])
        return not (isinstance(answer, int) and not isinstance(answer, bool) and 1 <= answer <= count)
    if item.get("kind") == "O·X":
        return str(answer).strip().upper() not in ("O", "X")
    return not has_answer(answer)
