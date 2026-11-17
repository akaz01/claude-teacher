"""개념 정리 학습지의 형성평가(문항 머리·보기·단답·O·X·서술·해설)와 도달 점검 블록 만들기.

공용 값과 도우미는 make_worksheet_base.py에 있다."""

from __future__ import annotations

from make_worksheet_base import *  # noqa: F401,F403  (색·크기·칸 도우미)
from make_worksheet_base import WIDTHS, wrapped_lines


def _dash(first: bool) -> dict:
    return {} if first else {"top": edge(THIN, HAIR, "DASH")}


def question_head(number: int, item: dict, first: bool, pad_top: float = 0, teacher: bool = False) -> tuple[dict, float]:
    """문항 머리: 남색 동그라미 번호 + 문항 글(11.25pt) + 오른쪽 종류 칩."""
    pad_top = 0 if first else pad_top
    lines = wrapped_lines(item["text"], 590, 11.25)
    height = pad_top + max(25, lines * 24.75)
    edges = _dash(first)
    middle = "center" if lines == 1 else "top"       # 한 줄이면 번호·글·종류 칩의 세로 가운데가 같다
    row = [cell([circle(str(number), NAVY, 24)], pad=(0, 0, pad_top, 0), height_px=height, edges=edges, spacing=100,
                valign=middle),
           cell(item["text"], pad=(0, 0, pad_top, 0), size=11.25, spacing=LINE_165, height_px=height, edges=edges,
                valign=middle, **({"mark_color": ANS} if teacher else {})),
           cell([chip(item["kind"], TINT, NAVY, height=22, pt=9)], align="right", pad=(0, 0, pad_top, 0),
                height_px=height, edges=edges, spacing=100, valign=middle)]
    return table([34, 594, 70], [row]), height


def options_table(item: dict, teacher: bool) -> tuple[dict, float]:
    """선택형 보기. 열 수만큼 칸을 나누고, 교사용은 정답을 파랑 굵게 밑줄."""
    options = item.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= len(CIRCLED):
        raise ValueError(f"선택형 문항에는 보기 2~{len(CIRCLED)}개(options)가 필요함")
    columns = min(max(int(item.get("cols", 3)), 1), len(options))
    step = (664 + 12) / columns
    widths = [34] + [round(step, 1)] * (columns - 1) + [round(664 - step * (columns - 1), 1)]
    rows, height = [], 0.0
    for start in range(0, len(options), columns):
        last_row = start + columns >= len(options)
        row_h = 24 if last_row else 24 + QUESTION_GAP
        cells = [cell(None, height_px=row_h)]
        for column in range(columns):
            number = start + column + 1
            if number > len(options):
                cells.append(cell(None, height_px=row_h))
                continue
            label = f"{CIRCLED[number - 1]} {options[number - 1]}"
            right = teacher and item.get("answer") == number
            piece = run(label, 11.25, ANS if right else INK, bold=right, underline=right)
            cells.append(cell([piece], height_px=row_h, spacing=LINE_160))
        rows.append(cells)
        height += row_h
    return table(widths, rows), height


def source_table(item: dict) -> tuple[dict, float]:
    """제시문 상자: 연한 바탕 + 왼쪽 남색 막대."""
    note = item.get("source_note")
    body = [run(item["source"], 10.5, INK)] + ([run("\n" + note, 9, MUTED)] if note else [])
    lines = wrapped_lines(item["source"], 664 - 34, 10.5) + (1 if note else 0)
    height = 8 + lines * 21 + 8
    edges = {"left": edge(THICK, SKY_LINE), "right": edge(THICK, SKY_LINE), "top": edge(THICK, SKY_LINE),
             "bottom": edge(THICK, SKY_LINE)}
    box = cell(body, fill=PALE, pad=(16, 16, 8, 8), spacing=LINE_165, height_px=height, edges=edges)
    return table([34, 664], [[cell(None, height_px=height), box]]), height


def short_answer_table(item: dict, teacher: bool) -> tuple[dict, float]:
    """단답형: '답' 칩 + 밑줄 칸. 교사용은 칸 안에 파랑 굵은 답."""
    answer = str(item.get("answer", "")) if teacher and has_answer(item.get("answer")) else ""
    width = WIDTHS.short_answer_px              # 답 길이와 상관없이 단답 칸은 모두 같은 너비
    line = cell([run(answer, 11.25, ANS, bold=True)] if answer else None, align="center", valign="center", height_px=26,
                edges={"bottom": edge(THICK, INK)})
    tag = cell([chip("답", SKY, BLUE, height=20, pt=9, w=30)], valign="center", height_px=26, pad=(0, 8, 0, 0),
               spacing=100)
    return table([34, 38, width, 664 - 38 - width], [[cell(None, height_px=26), tag, line, cell(None, height_px=26)]]), 26


def ox_table(item: dict, teacher: bool) -> tuple[dict, float]:
    answer = str(item.get("answer", "")).strip().upper()

    def mark(letter: str) -> dict:
        right = teacher and answer == letter
        return run(letter + ("  ← 정답" if right else ""), 11.25, ANS if right else INK, bold=right)

    body = [run("( ", 11.25), mark("O"), run("　/　", 11.25), mark("X"), run(" )", 11.25)]
    return table([34, 664], [[cell(None, height_px=26), cell(body, height_px=26, spacing=LINE_160)]]), 26


def essay_table(item: dict, teacher: bool) -> tuple[dict, float]:
    """서술형 칸: 연한 바탕 + 네 변 얇은 테두리 + 회색 첫 문장 + 실제 선 쓰기 줄(마지막 줄 아래 여백 칸)."""
    count = int(item.get("lines", 3))
    notes = []
    if teacher:
        notes = [str(item["answer"]) if has_answer(item.get("answer")) else "",
                 f"채점: {item['point']}" if item.get("point") else ""]
        notes = [note for note in notes if note]
    if len(notes) > count:
        notes = notes[:count - 1] + ["\n".join(notes[count - 1:])]       # 줄 수는 학생용과 같게 둔다
    notes += [""] * (count - len(notes))
    rows, height = [], 0.0
    starter = item.get("starter")
    total = (1 if starter else 0) + count
    for index in range(total):
        is_start = bool(starter) and index == 0
        first = index == 0
        edges = {"left": edge(THICK, SKY_LINE), "right": edge(THICK, SKY_LINE)}
        if first:
            edges["top"] = edge(THICK, SKY_LINE)
        if not is_start:
            edges["bottom"] = edge(0.25, ROW_LINE)
        text = starter if is_start else notes[index - (1 if starter else 0)]
        pad_top = 8 if first else 0
        row_h = max(ESSAY_ROW_PX + pad_top, wrapped_lines(text, 598, 10.5) * 10.5 * PX_PER_PT * LINE_160 / 100 + pad_top)
        pad_bottom = 0
        colored = {} if is_start or not text else {"color": ANS, "bold": True}
        body = cell(text, fill=PALE, height_px=row_h, pad=(16, 16, pad_top, pad_bottom), valign="center", size=10.5,
                    spacing=LINE_160, edges=edges, **({"color": FAINT} if is_start else colored))
        rows.append([cell(None, height_px=row_h), body])
        height += row_h
    # 마지막 쓰기 줄 아래 여백 칸: 쓰기 줄 밑줄과 상자 아래 테두리가 겹치지 않게
    tail = {"left": edge(THICK, SKY_LINE), "right": edge(THICK, SKY_LINE), "bottom": edge(THICK, SKY_LINE)}
    rows.append([cell(None, height_px=8), cell("", fill=PALE, height_px=8, pad=(16, 16, 0, 0), edges=tail)])
    height += 8
    return table([34, 664], rows), height


CHALLENGE_LABEL = "도전 과제"                     # 학생에게 보이는 머리말. 기존 문제 형식의 도전 과제 칸과 같은 이름이다
CHALLENGE_WIDTHS = [90, 608]


def challenge_table(item: dict, teacher: bool) -> tuple[dict, float]:
    """도전 과제 칸: 남색 이름표 + 연한 바탕 과제 글, 그 아래 전체 너비 쓰기 줄. 교사용은 줄에 파랑 굵은 답이 든다.
    줄 수와 높이는 학생용·교사용이 같다 (essay_table과 같은 방식)."""
    count = int(item.get("lines", 3))
    notes = []
    if teacher:
        notes = [str(item["answer"]) if has_answer(item.get("answer")) else "",
                 f"채점: {item['point']}" if item.get("point") else ""]
        notes = [note for note in notes if note]
    if len(notes) > count:
        notes = notes[:count - 1] + ["\n".join(notes[count - 1:])]
    notes += [""] * (count - len(notes))
    head_h = max(34, wrapped_lines(item["text"], CHALLENGE_WIDTHS[1] - 32, 11.25) * 11.25 * PX_PER_PT * LINE_160 / 100 + 14)
    side = edge(THICK, SKY_LINE)
    rows = [[cell(CHALLENGE_LABEL, fill=NAVY, color=WHITE, font=SERIF, size=10.5, bold=True, align="center",
                  valign="center", height_px=head_h),
             cell(item["text"], fill=PALE, size=11.25, spacing=LINE_165, valign="center", pad=(16, 16, 0, 0),
                  height_px=head_h, edges={"top": side, "right": side, "bottom": edge(0.25, ROW_LINE)},
                  **({"mark_color": ANS} if teacher else {}))]]
    height = head_h
    for note in notes:
        row_h = max(ESSAY_ROW_PX, wrapped_lines(note, sum(CHALLENGE_WIDTHS) - 32, 10.5) * 10.5 * PX_PER_PT * LINE_160 / 100)
        colored = {"color": ANS, "bold": True} if note else {}
        rows.append([cell(note, colspan=2, fill=PALE, height_px=row_h, pad=(16, 16, 0, 0), valign="center", size=10.5,
                          spacing=LINE_160, edges={"left": side, "right": side, "bottom": edge(0.25, ROW_LINE)}, **colored)])
        height += row_h
    tail = {"left": side, "right": side, "bottom": side}
    rows.append([cell("", colspan=2, fill=PALE, height_px=8, pad=(16, 16, 0, 0), edges=tail)])
    return table(CHALLENGE_WIDTHS, rows), height + 8


def explain_table(item: dict) -> tuple[dict, float]:
    text = f"해설: {item['explain']}"
    lines = wrapped_lines(text, 664, 9)
    height = lines * 12 * 1.5
    return table([34, 664], [[cell(None), cell(text, size=9, color=ANS, spacing=150)]]), height


def reach_table(items: list) -> tuple[dict, float]:
    """도달 점검: 남색 머리띠 + 연한 바탕 줄(예 / 아니요)."""
    head = [cell([run("도달 점검", 10.5, WHITE, bold=True, font=SERIF)], fill=NAVY, valign="center", height_px=32,
                 pad=(16, 0, 0, 0)),
            cell([run("학습 목표에 도달했는지 스스로 표시하세요.", 9, BAND_TEXT)], fill=NAVY, valign="center", align="right",
                 pad=(0, 16, 0, 0))]
    rows, height = [head], 32.0
    for index, text in enumerate(items):
        last = index == len(items) - 1
        edges = {}
        if last:
            edges["bottom"] = edge(THICK, SKY_LINE)
        if index:
            edges["top"] = edge(THIN, SKY_LINE, "DASH")
        left_edges, right_edges = {**edges, "left": edge(THICK, SKY_LINE)}, {**edges, "right": edge(THICK, SKY_LINE)}
        row_h = 36 + (4 if index == 0 else 0) + (3 if last else 0)
        pad_top = 5 + (4 if index == 0 else 0)
        rows.append([cell(text, fill=PALE, size=11.25, pad=(16, 0, pad_top, 5), height_px=row_h, edges=left_edges,
                          valign="center"),
                     cell([run("예　/　아니요", 10.5, MUTED)], fill=PALE, align="right", pad=(0, 16, pad_top, 5),
                          height_px=row_h, edges=right_edges, valign="center")])
        height += row_h
    return table([428, 270], rows), height


def question_blocks(number: int, item: dict, teacher: bool, pad_top: float = 0,
                    gap_above: float = 0) -> list[tuple[dict, float, float]]:
    kind = item.get("kind")
    if kind not in QUESTION_KINDS or not item.get("text"):
        raise ValueError(f"문항 {number}: kind({'/'.join(QUESTION_KINDS)})와 text가 필요함")
    parts = [(*question_head(number, item, number == 1, pad_top, teacher), 0 if number == 1 else gap_above)]
    if item.get("source"):
        parts.append((*source_table(item), BOX_GAP))
    makers = {"선택형": options_table, "단답형": short_answer_table, "O·X": ox_table, "서술형": essay_table}
    box_before = kind == "서술형" or bool(item.get("source"))      # 상자(서술 칸)·제시문 뒤 보기는 상자와 떼어 둔다
    parts.append((*makers[kind](item, teacher), BOX_GAP if box_before else QUESTION_GAP))
    if teacher and item.get("explain"):
        parts.append((*explain_table(item), QUESTION_GAP))
    return parts

