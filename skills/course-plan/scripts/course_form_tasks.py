"""학교 양식 Ⅵ 수행평가 세부기준 채우기: 과제마다 소제목('1. 과제명')과 표 하나.

표는 성취기준 · 평가 방법(■□) · 머리행 · 채점 기준 · 기본점수 행 · 학생 유의사항으로 되어 있다.
채점 기준 부분은 기본 양식 두 가지를 열 수로 가른다.
- 세로(1학기 양식, 5열): 평가 영역 | 평가 요소 | 채점 기준 | 배점 | 평가 척도. 수준마다 한 행.
- 가로(2학기 양식, 7열): 평가 영역 | 평가 요소 | 수준1 … 수준k | 평가 척도. 요소마다 배점 행과 기준 행 두 행.
평가 척도에는 수준 점수를 하나씩 골라 더해 나올 수 있는 합을 모두 적는다(학교 양식의 '조합 가능 점수').
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from make_course_plan_check import number_text
from make_course_plan_layout import TODO
from make_course_plan_rubric import method_line

from course_form_marks import rule_lines

from course_form_xml import (FIT_RATIO, GAP_HEIGHT, HEADING_HEIGHT, TITLE_HEIGHT, build_table, cell_height, cell_map, cell_paragraphs, cell_width, char_with, fill_cell,
                             first_char, page_break_before, para, plain, run_chars, split_widths, table_shape,
                             table_width, tables_in, text_cell, text_height)

SIZE = 900
TASK_BREAK = "CELL"             # 쪽 높이를 모를 때: 행 단위로 나누면 채점 기준 덩어리가 통째로 넘어가 머리행만 남는다
MAX_SCALE_LINES = 40            # 나올 수 있는 합이 이보다 많으면 '최고 ~ 최저'로 줄여 쓴다
MAX_SUMS = 5000
NOTE_LINES = 2000                # 유의사항 본문을 머리행 아래에 이어 쓰려면 남아야 하는 높이 (두 줄 남짓)
LONG_START = 0.4                # 한 쪽보다 긴 덩어리는 남은 자리가 쪽의 이만큼보다 적으면 다음 쪽에서 시작
NUMBER_RE = re.compile(r"^\s*\d+\.\s")
SPAN_RE = re.compile(r'<hp:cellSpan colSpan="(\d+)" rowSpan="(\d+)"/>')


def _colspan(tc: str) -> int:
    return int(SPAN_RE.search(tc).group(1))


def scale_lines(task: dict) -> list[str]:
    """수준 점수를 하나씩 골라 더해 나올 수 있는 합 (큰 것부터)."""
    elements = [element for area in task["areas"] for element in area["elements"]]
    top = sum(max(level["score"] for level in element["levels"]) for element in elements)
    low = sum(min(level["score"] for level in element["levels"]) for element in elements)
    sums = {0}
    for element in elements:
        sums = {total + level["score"] for total in sums for level in element["levels"]}
        if len(sums) > MAX_SUMS:                          # 너무 많으면 세지 않고 최고 ~ 최저로
            break
    if len(sums) > MAX_SCALE_LINES:
        return [number_text(top), "~", number_text(low)]
    return [number_text(value) for value in sorted(sums, reverse=True)]


def _element_lines(element: dict) -> list[str]:
    lines = [f"[{element['group']}]"] if element["group"] else []
    return lines + [element["name"], f"({number_text(element['points'])}점)"]


def _area_lines(area: dict) -> list[str]:
    return [area["area"], f"({number_text(area['points'])}점)"]


def scale_col_of(cells: dict) -> int:
    """평가 척도 열 번호 (머리행에서 '척도'가 든 칸)."""
    return next(col for (col, row), tc in cells.items() if row == 2 and "척도" in plain(tc))


def _places(cells: dict) -> dict:
    """양식 표의 열 수, 기본점수 행들, 유의사항 머리 행 번호."""
    notes_head = next(row for (col, row), tc in cells.items() if col == 0 and "유의사항" in plain(tc))
    cols = max(col + _colspan(tc) for (col, _), tc in cells.items())
    base_rows = sorted(row for (col, row), tc in cells.items()
                       if col == 0 and 2 < row < notes_head and _colspan(tc) >= cols - 2)
    return {"notes_head": notes_head, "base_rows": base_rows, "cols": cols}


# ---------------------------------------------------------------- 위·아래 공통 행

def _top_rows(cells: dict, task: dict, span: int, width: int) -> tuple[list[list[str]], list[int]]:
    """성취기준, 평가 방법 두 행."""
    quotes = [f"{q['code']} {q['text']}".strip() for q in task["standards"]] or [TODO]
    quote_height = max(cell_height(cells[(2, 0)]), text_height("\n".join(quotes), width, SIZE))
    return ([[cells[(0, 0)], text_cell(cells[(2, 0)], quotes, colspan=span, width=width, height=quote_height)],
             [cells[(0, 1)], text_cell(cells[(2, 1)], method_line(task["methods"]), colspan=span, width=width)]],
            [quote_height, cell_height(cells[(2, 1)])])


def _note_paragraphs(body: str, notes: list[str]) -> list[str]:
    template = cell_paragraphs(body)[0]
    bullet = char_with(body, "‣") or first_char(template)
    text_char = next((c for c, t in run_chars(template) if t.strip() and "‣" not in t), bullet)
    return [para(template, [(bullet, "‣ "), (text_char, note)]) for note in notes]


def _tail_rows(cells: dict, task: dict, places: dict, start: int, cols: int, scale_col: int,
               width: int) -> tuple[list[list[str]], list[int]]:
    """기본점수 행들과 학생 유의사항 두 행 (유의사항이 없으면 뺀다)."""
    rows, heights, row_no = [], [], start
    sources = places["base_rows"] or [places["notes_head"] - 1]
    old_scale = scale_col_of(cells)
    left_width = width - cell_width(cells[(old_scale, sources[0])])
    for index, base in enumerate(task["base"]):
        # 양식의 마지막 기본점수 행은 아래가 굵은 선: 입력의 마지막 줄에만 쓰고 나머지는 첫 행 모양
        source = sources[-1] if index == len(task["base"]) - 1 else sources[0]
        text = chr(10).join(rule_lines(base["text"])) if base["rule"] else base["text"]
        height = max(cell_height(cells[(0, source)]), text_height(text, left_width, SIZE))
        rows.append([text_cell(cells[(0, source)], text, row=row_no, colspan=scale_col, width=left_width,
                               height=height),
                     text_cell(cells[(old_scale, source)], base["score"], col=scale_col, row=row_no, height=height)])
        heights.append(height)
        row_no += 1
    if task["notes"]:
        head, body = cells[(0, places["notes_head"])], cells[(0, places["notes_head"] + 1)]
        notes_height = sum(text_height("‣ " + note, width, SIZE) - 600 for note in task["notes"]) + 600
        rows += [[fill_cell(head, cell_paragraphs(head), row=row_no, colspan=cols, width=width)],
                 [fill_cell(body, _note_paragraphs(body, task["notes"]), row=row_no + 1, colspan=cols, width=width,
                            height=notes_height)]]
        heights += [cell_height(head), notes_height]
    return rows, heights


# ---------------------------------------------------------------- 채점 기준 나누기

def _segments(count: int, cuts: tuple[int, ...]) -> list[tuple[int, int]]:
    """요소 count개를 cuts(새 쪽에서 시작할 요소 번호)에서 나눈 (시작, 끝) 묶음들."""
    edges = [0, *sorted(cut for cut in set(cuts) if 0 < cut < count), count]
    return list(zip(edges, edges[1:]))


def _area_runs(owners: list[int], start: int, end: int) -> list[tuple[int, int]]:
    """요소 start~end 사이에서 같은 영역이 이어지는 (시작, 끝) 묶음들."""
    runs, k = [], start
    while k < end:
        j = k
        while j < end and owners[j] == owners[k]:
            j += 1
        runs.append((k, j))
        k = j
    return runs


# ---------------------------------------------------------------- 세로 양식 (수준마다 한 행)

def _vertical_body(cells: dict, task: dict, scale: list[str],
                   cuts: tuple[int, ...] = ()) -> tuple[list[list[str]], list[int], list[int]]:
    """(행들, 행 높이, 요소마다의 높이). cuts의 요소에서 영역·평가 척도 칸을 새로 합친다."""
    criteria_width = cell_width(cells[(2, 3)])
    elements = [(index, element) for index, area in enumerate(task["areas"]) for element in area["elements"]]
    owners = [index for index, _ in elements]
    starts = [sum(len(element["levels"]) for _, element in elements[:k]) for k in range(len(elements) + 1)]
    heights = [max(cell_height(cells[(2, 4)]), text_height(level["text"], criteria_width, SIZE))
               for _, element in elements for level in element["levels"]]
    lead, trail = {}, {}
    for s, e in _segments(len(elements), cuts):
        for k, j in _area_runs(owners, s, e):
            r0, r1 = starts[k], starts[j]
            lead[r0] = text_cell(cells[(0, 3)], _area_lines(task["areas"][owners[k]]), row=3 + r0,
                                 rowspan=r1 - r0, height=sum(heights[r0:r1]))
        r0, r1 = starts[s], starts[e]
        trail[r0] = text_cell(cells[(4, 3)], scale if s == 0 else "", row=3 + r0, rowspan=r1 - r0,
                              height=sum(heights[r0:r1]))
    later_element = (1, 5) if (1, 5) in cells else (1, 3)
    rows = []
    for k, (_, element) in enumerate(elements):
        for l, level in enumerate(element["levels"]):
            position = starts[k] + l
            row_no, source = 3 + position, 3 if position == 0 else 4
            row = [lead[position]] if position in lead else []
            if l == 0:
                span = len(element["levels"])
                row.append(text_cell(cells[(1, 3) if position == 0 else later_element], _element_lines(element),
                                     row=row_no, rowspan=span, height=sum(heights[position:position + span])))
            row.append(text_cell(cells[(2, source)], level["text"], row=row_no, height=heights[position]))
            row.append(text_cell(cells[(3, source)], number_text(level["score"]), row=row_no,
                                 height=heights[position]))
            if position in trail:
                row.append(trail[position])
            rows.append(row)
    blocks = [sum(heights[starts[k]:starts[k + 1]]) for k in range(len(elements))]
    return rows, heights, blocks


# ---------------------------------------------------------------- 가로 양식 (수준마다 한 열)

def _element_rows(cells: dict, element: dict, row_no: int, widths: list[int],
                  first: bool) -> tuple[list[str], list[str], int, int]:
    """요소 하나의 배점 행과 기준 행. 수준이 열 수보다 적으면 마지막 수준 칸을 합친다."""
    score_src, text_src = (3, 4) if first else (5, 6)
    count, levels = len(widths), element["levels"]
    text_h = max([cell_height(cells[(2, text_src)])] +
                 [text_height(level["text"], widths[min(i, count - 1)], SIZE) for i, level in enumerate(levels)])
    score_h = cell_height(cells[(2, score_src)])
    score_row = [text_cell(cells[(1, score_src)], _element_lines(element), row=row_no, rowspan=2,
                           height=score_h + text_h)]
    text_row = []
    for i, level in enumerate(levels):
        span = count - i if i == len(levels) - 1 else 1
        width = sum(widths[i:i + span])
        score_row.append(text_cell(cells[(2, score_src)], number_text(level["score"]), col=2 + i, row=row_no,
                                   colspan=span, width=width, height=score_h))
        text_row.append(text_cell(cells[(2, text_src)], level["text"], col=2 + i, row=row_no + 1, colspan=span,
                                  width=width, height=text_h))
    return score_row, text_row, score_h, text_h


def _horizontal_body(cells: dict, task: dict, scale: list[str], widths: list[int], scale_col: int,
                     cuts: tuple[int, ...] = ()) -> tuple[list[list[str]], list[int], list[int]]:
    """(행들, 행 높이, 요소마다의 높이). cuts의 요소에서 영역·평가 척도 칸을 새로 합친다."""
    rows, heights, owners = [], [], []
    for index, area in enumerate(task["areas"]):
        for element in area["elements"]:
            score_row, text_row, score_h, text_h = _element_rows(cells, element, 3 + len(rows), widths, not rows)
            rows += [score_row, text_row]
            heights += [score_h, text_h]
            owners.append(index)
    old_scale = scale_col_of(cells)
    for s, e in _segments(len(owners), cuts):
        for k, j in _area_runs(owners, s, e):
            rows[2 * k].insert(0, text_cell(cells[(0, 3)], _area_lines(task["areas"][owners[k]]), row=3 + 2 * k,
                                            rowspan=2 * (j - k), height=sum(heights[2 * k:2 * j])))
        rows[2 * s].append(text_cell(cells[(old_scale, 3)], scale if s == 0 else "", col=scale_col, row=3 + 2 * s,
                                     rowspan=2 * (e - s), height=sum(heights[2 * s:2 * e])))
    blocks = [heights[2 * k] + heights[2 * k + 1] for k in range(len(owners))]
    return rows, heights, blocks


# ---------------------------------------------------------------- 표와 절

@dataclass(frozen=True)
class TaskLayout:
    """과제 표 하나의 행들.

    kept: 앞에서부터 한 덩어리로 움직이는 행 수(성취기준·평가 방법·머리행·채점 기준; 채점 기준은 영역·평가 척도
    칸이 모든 행을 합쳐 행 단위로 나누면 통째로 움직인다). blocks: 채점 기준의 요소마다의 높이."""
    rows: list
    heights: list
    cols: int | None
    kept: int
    blocks: list
    notes: bool = False                 # 맨 끝 두 행이 학생 유의사항 머리행과 본문


def task_layout(base: str, task: dict, cuts: tuple[int, ...] = ()) -> TaskLayout:
    """양식 과제 표 base를 과제 하나의 영역·요소·수준 수에 맞춘 행들. cuts: 채점 기준을 새 쪽에서 이어 갈
    요소 번호들(그 요소에서 영역·평가 척도 칸을 새로 합쳐, 행 단위로 나눌 때 요소 경계에서 쪽이 나뉜다)."""
    cells = cell_map(base)
    places = _places(cells)
    width, scale = table_width(base), scale_lines(task)
    label_width = cell_width(cells[(0, 0)])
    head_height = cell_height(cells[(2, 2)])
    notes = bool(task["notes"])
    if places["cols"] <= 5:                                  # 세로 양식
        top, top_h = _top_rows(cells, task, 3, width - label_width)
        header = [cells[(col, 2)] for col in sorted(c for c, r in cells if r == 2)]
        body, body_h, blocks = _vertical_body(cells, task, scale, cuts)
        tail, tail_h = _tail_rows(cells, task, places, 3 + len(body), 5, 4, width)
        return TaskLayout(top + [header] + body + tail, top_h + [head_height] + body_h + tail_h, None,
                          3 + len(body), blocks, notes)
    count = max(len(element["levels"]) for area in task["areas"] for element in area["elements"])
    old_scale = scale_col_of(cells)
    level_total = sum(cell_width(cells[(col, 3)]) for col in range(2, old_scale))
    widths = split_widths(level_total, count)
    scale_col, cols = 2 + count, 3 + count
    top, top_h = _top_rows(cells, task, count + 1, width - label_width)
    header = [cells[(0, 2)], cells[(1, 2)],
              text_cell(cells[(2, 2)], plain(cells[(2, 2)]), colspan=count, width=level_total),
              fill_cell(cells[(old_scale, 2)], cell_paragraphs(cells[(old_scale, 2)]), col=scale_col)]
    body, body_h, blocks = _horizontal_body(cells, task, scale, widths, scale_col, cuts)
    tail, tail_h = _tail_rows(cells, task, places, 3 + len(body), cols, scale_col, width)
    return TaskLayout(top + [header] + body + tail, top_h + [head_height] + body_h + tail_h, cols, 3 + len(body),
                      blocks, notes)


def task_table(base: str, task: dict, page_break: str = "TABLE", layout: TaskLayout | None = None) -> str:
    """양식 과제 표 base를 과제 하나에 맞춰 채운 표. page_break는 build_table 설명을 본다."""
    layout = layout or task_layout(base, task)
    return build_table(base, layout.rows, layout.heights, cols=layout.cols, page_break=page_break)


def _blank(paragraph: str) -> bool:
    return not tables_in(paragraph) and not plain(paragraph).strip()


def _is_task_table(paragraph: str) -> bool:
    spans = tables_in(paragraph)
    return bool(spans) and table_shape(paragraph[slice(*spans[0])])[0] >= 6


def _tail_mode(room: int, layout: TaskLayout, page: int) -> str:
    """채점 기준 뒤 행(기본점수·유의사항)이 쪽에 남은 자리 room을 넘칠 때의 나눔 방식.

    행 단위로 나누면 유의사항 머리행만 쪽 끝에 남는 경우(머리행과 본문 몇 줄은 들어가는데 본문 전체는 안 들어감)에는
    칸 단위로 나눠 본문이 머리행 아래에서 이어지게 한다. 머리행이 실제로 들어가는지가 중요해서 여기서는 줄여 잡지
    않은 쪽 높이로 본다(한글 2024 쪽 그림으로 맞춤)."""
    tail = layout.heights[layout.kept:]
    if sum(tail) <= room or not layout.notes:
        return "TABLE"
    full_room = room + round(page / FIT_RATIO) - page
    return "CELL" if sum(tail[:-1]) + NOTE_LINES <= full_room else "TABLE"


def _cuts(layout: TaskLayout, room: int, page: int) -> tuple[tuple[int, ...], int]:
    """채점 기준을 요소 경계에서 쪽마다 나눌 요소 번호들과, 마지막 쪽에 남는 자리.
    room은 표를 시작하는 쪽에 남은 자리(소제목 포함)."""
    left = room - TITLE_HEIGHT - sum(layout.heights[:3])          # 소제목, 성취기준, 평가 방법, 머리행
    cuts = []
    for index, block in enumerate(layout.blocks):
        if block > left and index > 0:
            cuts.append(index)
            left = page
        left -= block
    return tuple(cuts), left


def _place(used: int, base: str, task: dict, page: int, first: bool) -> tuple[bool, str, TaskLayout, int]:
    """(소제목 앞에서 쪽을 나눌지, 표 나눔 방식, 표 행들, 표를 쓴 뒤 마지막 쪽에 찬 높이).
    used는 지금 쪽에 찬 높이(빈 줄 포함), page는 줄여 잡은 쪽 높이.

    - 표 전체가 남은 자리에 들어가면 그대로 둔다.
    - 한 쪽에 들어가는 표는 다음 쪽에서 통째로 시작한다(첫 과제는 절 제목 바로 뒤라 쪽을 나누지 않는다).
    - 앞 덩어리(성취기준~채점 기준)가 쪽에 들어가면 행 단위로 나눠 뒤의 기본점수·유의사항 행만 다음 쪽으로 넘긴다.
    - 덩어리가 남은 자리(첫 과제)나 한 쪽보다 길면 채점 기준을 요소 경계에서 쪽마다 나눈다(_cuts). 남은 자리가
      쪽의 LONG_START보다 적으면 다음 쪽에서 시작한다."""
    layout = task_layout(base, task)
    whole = TITLE_HEIGHT + sum(layout.heights)
    kept = TITLE_HEIGHT + sum(layout.heights[:layout.kept])
    tail = sum(layout.heights[layout.kept:])
    room = page - used
    if whole <= room:
        return False, "TABLE", layout, used + whole
    if not first and whole <= page:
        return True, "TABLE", layout, whole
    if kept <= room:
        return False, _tail_mode(room - kept, layout, page), layout, (used + whole) % page
    if not first and kept <= page:
        return True, _tail_mode(page - kept, layout, page), layout, whole % page
    head = TITLE_HEIGHT + sum(layout.heights[:3])               # 소제목, 성취기준, 평가 방법, 머리행
    first_block = layout.blocks[0] if layout.blocks else 0
    new_page = not first and (room < page * LONG_START or head + first_block > room)   # 머리행만 남지 않게
    cuts, left = _cuts(layout, page if new_page else room, page)
    layout = task_layout(base, task, cuts)
    return new_page, _tail_mode(left, layout, page), layout, (page - left + tail) % page


def tasks_part(paragraphs: list[str], evaluation: dict, warnings: list[str], page: int = 0) -> list[str]:
    """Ⅵ 절: 양식의 첫 과제(소제목, 표, 빈 줄)를 본떠 과제 수만큼 쓴다.

    절은 새 쪽에서 시작한다(2학기 학교 양식처럼). page(본문 높이)를 주면 표 높이를 어림해 _place 규칙으로
    과제를 쪽에 배치한다: 표 첫 행이나 머리행만 쪽 끝에 걸치거나 행 가운데가 잘리는 일을 줄인다."""
    tables = [index for index, paragraph in enumerate(paragraphs) if _is_task_table(paragraph)]
    titles = [index for index, paragraph in enumerate(paragraphs)
              if not tables_in(paragraph) and NUMBER_RE.match(plain(paragraph))]
    if not tables or not titles:
        return paragraphs
    paragraphs = [page_break_before(paragraphs[0])] + paragraphs[1:]
    title, holder = paragraphs[titles[0]], paragraphs[tables[0]]
    gap = paragraphs[tables[0] + 1] if tables[0] + 1 < len(paragraphs) and _blank(paragraphs[tables[0] + 1]) else None
    end = tables[-1] + 1
    if not evaluation["tasks"]:
        warnings.append(f"수행평가 세부기준(evaluation.tasks)이 없어 {TODO}로 둠")
        return paragraphs[:titles[0]] + [para(title, TODO)] + paragraphs[end:]
    base = holder[slice(*tables_in(holder)[0])]
    fit = round(page * FIT_RATIO)
    used = HEADING_HEIGHT + GAP_HEIGHT * (titles[0] - 1)       # 절 제목과 소제목 앞 빈 줄
    body = []
    for number, task in enumerate(evaluation["tasks"], 1):
        heading = para(title, f"{number}. {task['name']}")
        spacing = GAP_HEIGHT if number > 1 and gap is not None else 0
        if fit:
            new_page, mode, layout, used = _place(used + spacing, base, task, fit, number == 1)
        else:
            new_page, mode, layout = False, TASK_BREAK, task_layout(base, task)
        if new_page:
            body.append(page_break_before(heading))
        else:
            body += [gap, heading] if spacing else [heading]
        body.append(holder.replace(base, task_table(base, task, mode, layout), 1))
    return paragraphs[:titles[0]] + body + paragraphs[end:]
