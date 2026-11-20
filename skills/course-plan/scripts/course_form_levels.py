"""학교 양식 Ⅺ 성취기준 및 성취수준 채우기.

가. 성취기준별 성취수준: 단원마다 '(1) 단원명'과 표(성취기준 | 수준 | 수준별 진술).
나. 학기단위 성취수준: 수준마다 한 행, 맨 끝에 최소 성취수준 행(입력에 있을 때만).
입력(evaluation.achievement_levels)이 없으면 소제목 아래 [작성 필요]를 두고 경고한다.

쪽 배치: 절은 새 쪽에서 시작한다. 단원 표는 행 단위로 나누어(성취기준 칸이 A~E 행을 합쳐 한 성취기준이 두 쪽에
갈라지지 않음) 머리행이 다음 쪽에 되풀이된다. 표 높이를 어림해, 소제목과 머리행·첫 성취기준이 남은 자리에
들어가지 않으면 소제목부터 다음 쪽에서 시작한다(머리행이나 소제목만 쪽 끝에 남지 않게).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from make_course_plan_layout import TODO

from course_form_xml import (FIT_RATIO, GAP_HEIGHT, HEADING_HEIGHT, TITLE_HEIGHT, build_table, cell_height,
                             cell_map, cell_paragraphs, cell_width, first_table, page_break_before, para, plain,
                             table_shape, tables_in, text_cell, text_height)

SIZE = 900
UNIT_RE = re.compile(r"^\s*\(\d+\)")
BULLET_RE = re.compile(r"^\s*[⦁●•·]\s*")
MINIMUM_LABEL = ["최소", "성취", "수준"]
NEWLINE = chr(10)


@dataclass(frozen=True)
class Rows:
    """표 한 개의 행들. blocks: 머리행 뒤에서 한 덩어리로 움직이는 행 묶음마다의 높이."""
    rows: list
    heights: list
    blocks: list


def unit_rows(base: str, unit: dict) -> Rows:
    """단원 하나: 성취기준마다 성취기준 칸(수준 수만큼 합침)과 수준·진술 행들."""
    cells = cell_map(base)
    rows, heights, blocks = [[cells[(0, 0)], cells[(1, 0)]]], [cell_height(cells[(0, 0)])], []
    text_width = cell_width(cells[(2, 1)])
    for standard in unit["standards"]:
        levels = list(standard["levels"].items()) or [("", TODO)]
        start = len(rows)
        level_heights = [max(cell_height(cells[(2, 2)]), text_height(text, text_width, SIZE)) for _, text in levels]
        quote = f"{standard['code']} {standard['text']}".strip()
        quote_height = text_height(quote, cell_width(cells[(0, 1)]), SIZE)
        if quote_height > sum(level_heights):
            level_heights[-1] += quote_height - sum(level_heights)
        for index, (name, text) in enumerate(levels):
            source = 1 if index == 0 else 2
            row = ([text_cell(cells[(0, 1)], quote, row=start, rowspan=len(levels), height=sum(level_heights))]
                   if index == 0 else [])
            row += [text_cell(cells[(1, source)], name, row=start + index, height=level_heights[index]),
                    text_cell(cells[(2, source)], text, row=start + index, height=level_heights[index])]
            rows.append(row)
        heights += level_heights
        blocks.append(sum(level_heights))
    return Rows(rows, heights, blocks)


def unit_table(base: str, unit: dict, layout: Rows | None = None) -> str:
    """행 단위로 나눈다: 성취기준 칸이 A~E 행을 합쳐 한 성취기준은 통째로 다음 쪽에 간다."""
    layout = layout or unit_rows(base, unit)
    return build_table(base, layout.rows, layout.heights, page_break="TABLE")


def semester_rows(base: str, semester: dict, minimum: list[str]) -> Rows:
    """학기단위 성취수준: 수준마다 한 행(⦁ 줄들), 최소 성취수준 행."""
    cells = cell_map(base)
    rows, heights = [[cells[(0, 0)], cells[(1, 0)]]], [cell_height(cells[(1, 0)])]
    found = BULLET_RE.match(plain(cell_paragraphs(cells[(1, 1)])[0]))
    bullet = found.group(0) if found else "⦁"
    width = cell_width(cells[(1, 1)])
    entries = list(semester.items()) + ([(MINIMUM_LABEL, minimum)] if minimum else [])
    last_row = max(row for _, row in cells)
    for number, (name, lines) in enumerate(entries, 1):
        source = last_row if minimum and number == len(entries) else 1
        lines = [bullet + line for line in lines or [TODO]]
        height = text_height(NEWLINE.join(lines), width, SIZE, minimum=1800)
        rows.append([text_cell(cells[(0, source)], name, row=number, height=height),
                     text_cell(cells[(1, source)], lines, row=number, height=height)])
        heights.append(height)
    return Rows(rows, heights, heights[1:])


def semester_table(base: str, semester: dict, minimum: list[str], page: int = 0) -> str:
    """행이 모두 한 쪽에 들어가면 행 단위로, 한 쪽보다 긴 행이 있으면(어림) 양식처럼 칸 단위로 나눈다."""
    layout = semester_rows(base, semester, minimum)
    fits = page and max(layout.blocks) + layout.heights[0] <= page
    return build_table(base, layout.rows, layout.heights, page_break="TABLE" if fits else "CELL")


class _Cursor:
    """지금 쪽에 찬 높이 어림. page가 0이면 쪽을 따지지 않는다."""

    def __init__(self, page: int, used: int) -> None:
        self.page, self.used = page, used

    def starts_new_page(self, first: int) -> bool:
        """높이 first인 첫 덩어리가 남은 자리에 들어가지 않으면 새 쪽으로 (쪽 맨 위면 그대로)."""
        if not self.page or self.used == 0 or self.used + first <= self.page:
            return False
        self.used = 0
        return True

    def add(self, height: int) -> None:
        self.used += height
        if self.page and self.used > self.page:
            self.used %= self.page

    def flow(self, header: int, blocks: list[int]) -> None:
        """행 단위로 나뉘는 표: 덩어리가 남은 자리에 안 들어가면 다음 쪽에 머리행과 함께."""
        self.add(header)
        for block in blocks:
            if self.page and self.used + block > self.page:
                self.used = header
            self.add(block)


def _find(paragraphs: list[str]) -> dict | None:
    """가./나. 소제목, 첫 단원 소제목, 첫 단원 표, 학기단위 표의 문단 번호."""
    texts = [plain(paragraph).strip() for paragraph in paragraphs]
    ga = next((i for i, text in enumerate(texts) if text.startswith("가.")), None)
    na = next((i for i, text in enumerate(texts) if text.startswith("나.")), None)
    if ga is None or na is None:
        return None
    unit_titles = [i for i, text in enumerate(texts) if UNIT_RE.match(text) and not tables_in(paragraphs[i])]
    shapes = {i: table_shape(table) for i, paragraph in enumerate(paragraphs) if (table := first_table(paragraph))}
    unit_tables = [i for i, shape in shapes.items() if shape[1] == 3 and i < na]
    semester_tables = [i for i, shape in shapes.items() if shape[1] == 2 and i > na]
    if not unit_titles or not unit_tables or not semester_tables:
        return None
    return {"ga": ga, "na": na, "unit_title": unit_titles[0], "unit_table": unit_tables[0],
            "semester_table": semester_tables[0]}


def _blank(paragraph: str) -> bool:
    return not tables_in(paragraph) and not plain(paragraph).strip()


def _units(paragraphs: list[str], found: dict, levels: dict | None, warnings: list[str],
           cursor: _Cursor) -> list[str]:
    """가. 아래: 단원마다 '(n) 단원명', 표, (양식에 있던) 빈 줄."""
    title, holder = paragraphs[found["unit_title"]], paragraphs[found["unit_table"]]
    after = found["unit_table"] + 1
    gap = paragraphs[after] if after < found["na"] and _blank(paragraphs[after]) else None
    if not levels or not levels["units"]:
        warnings.append(f"성취기준별 성취수준(evaluation.achievement_levels.units)이 없어 Ⅺ 가.에 {TODO}로 둠")
        cursor.add(TITLE_HEIGHT)
        return [para(title, TODO)]
    base, body = first_table(holder), []
    for number, unit in enumerate(levels["units"], 1):
        layout = unit_rows(base, unit)
        heading = para(title, f"({number}) {unit['name']}")
        spacing = GAP_HEIGHT if number > 1 and gap is not None else 0
        cursor.add(spacing)
        if cursor.starts_new_page(TITLE_HEIGHT + layout.heights[0] + (layout.blocks or [0])[0]):
            body.append(page_break_before(heading))
        else:
            body += [gap, heading] if spacing else [heading]
        cursor.add(TITLE_HEIGHT)
        cursor.flow(layout.heights[0], layout.blocks)
        body.append(holder.replace(base, unit_table(base, unit, layout), 1))
    if gap is not None:
        cursor.add(GAP_HEIGHT)
    return body + ([gap] if gap is not None else [])


def _semester(paragraphs: list[str], found: dict, levels: dict | None, warnings: list[str],
              cursor: _Cursor) -> tuple[bool, list[str]]:
    """나. 아래: 학기단위 성취수준 표 (최소 성취수준만 있으면 수준 칸은 [작성 필요]).
    (나. 소제목 앞에서 쪽을 나눌지, 문단들)."""
    holder = paragraphs[found["semester_table"]]
    semester = (levels or {}).get("semester") or {}
    minimum = (levels or {}).get("minimum") or []
    if not semester and not minimum:
        warnings.append(f"학기단위 성취수준(achievement_levels.semester)이 없어 Ⅺ 나.에 {TODO}로 둠")
        return False, [para(paragraphs[found["unit_title"]], TODO)]
    if not semester:
        warnings.append(f"학기단위 성취수준(achievement_levels.semester)이 없어 수준 칸을 {TODO}로 둠")
        semester = {"": [TODO]}
    base = first_table(holder)
    layout = semester_rows(base, semester, minimum)
    new_page = cursor.starts_new_page(TITLE_HEIGHT + layout.heights[0] + layout.blocks[0])
    return new_page, [holder.replace(base, semester_table(base, semester, minimum, cursor.page), 1)]


def levels_part(paragraphs: list[str], levels: dict | None, warnings: list[str], page: int = 0) -> list[str]:
    """Ⅺ 절 전체. paragraphs[0]은 절 제목 문단. 가.(단원별)와 나.(학기단위)를 따로 채운다.
    page(쪽 본문 높이)를 주면 모듈 설명의 쪽 배치 규칙을 쓴다."""
    found = _find(paragraphs)
    if found is None:
        return paragraphs
    head, tail = paragraphs[:found["ga"]], paragraphs[found["semester_table"] + 1:]
    head = [page_break_before(head[0])] + head[1:]
    cursor = _Cursor(round(page * FIT_RATIO), HEADING_HEIGHT + GAP_HEIGHT * (len(head) - 1) + TITLE_HEIGHT)
    units = _units(paragraphs, found, levels, warnings, cursor)
    na = paragraphs[found["na"]]
    new_page, semester = _semester(paragraphs, found, levels, warnings, cursor)
    return head + [paragraphs[found["ga"]], *units, page_break_before(na) if new_page else na, *semester] + tail
