"""fill_exam.py가 쓰는 선택지 표 줄이기. 표준 라이브러리만 쓴다.

양식의 선택지 표가 5칸인데 선택지가 4개나 3개이면 남는 칸을 지우고 표를 다시 짠다.
표의 바깥 너비, 칸 모양(테두리·여백·문단 모양)은 양식 그대로 두고 칸 수, 행 수, 칸 너비만 바꾼다.

배치: 한 줄에 하나씩(5x1)이면 아래 칸을 지우고, 한 줄에 다섯(1x5)이면 오른쪽 칸을 지우고 칸 너비를 나눠 다시 채운다.
여러 줄 여러 칸(2x3)이면 4개는 2x2(①② / ③④), 3개는 1x3으로 짠다. 칸이 남는 배치는 만들지 않는다."""

from __future__ import annotations

import re

from fill_exam_parse import choice_cells
from fill_hwpx_parse import Table

MIN_CHOICES = 2
ROWS_BLOCK = re.compile(r"<hp:tr>.*</hp:tr>", re.S)
CELL = re.compile(r"<hp:tc\b.*?</hp:tc>", re.S)
CELL_ADDR = re.compile(r"<hp:cellAddr\b[^>]*/>")
CELL_SIZE = re.compile(r"<hp:cellSz\b[^>]*/>")
TABLE_OPEN = re.compile(r"<hp:tbl\b[^>]*>")
TABLE_SIZE = re.compile(r"<hp:sz\b[^>]*/>")


def _number(tag: str, name: str) -> int:
    found = re.search(rf'\b{name}="(\d+)"', tag)
    return int(found.group(1)) if found else 0


def _set(tag: str, name: str, value: int) -> str:
    return re.sub(rf'(\b{name}=")\d+(")', rf"\g<1>{value}\g<2>", tag, count=1)


def reshaped_layout(table: Table, slots: int, wanted: int) -> tuple[int, int] | None:
    """선택지 wanted개로 줄인 표의 (행, 칸). 줄일 수 없으면 None.

    선택지 칸이 표의 앞쪽 칸(행 순서)이고 모든 칸이 합쳐지지 않은 표만 줄인다."""
    if not MIN_CHOICES <= wanted < slots:
        return None
    cells = sorted(table.cells, key=lambda cell: (cell.row, cell.col))
    kept = choice_cells(table)
    if len(cells) != table.rows * table.cols or len(kept) != slots:
        return None
    if any(cell.row_span != 1 or cell.col_span != 1 for cell in cells):
        return None
    if not all(first is second for first, second in zip(cells, kept)):
        return None
    if table.cols == 1:
        return wanted, 1
    if table.rows == 1:
        return 1, wanted
    rows = -(-wanted // table.cols)
    cols = -(-wanted // rows)
    return (rows, cols) if rows * cols == wanted else None


def reshape_table_xml(xml: str, old: tuple[int, int], new: tuple[int, int], wanted: int) -> str:
    """표가 든 문단의 원문에서 앞의 wanted칸만 남기고 new(행, 칸)로 다시 짠다."""
    block = ROWS_BLOCK.search(xml)
    cells = CELL.findall(block.group(0)) if block else []
    old_rows, old_cols = old
    new_rows, new_cols = new
    if len(cells) != old_rows * old_cols:
        raise ValueError("선택지 표의 칸을 읽지 못했습니다")
    sizes = [CELL_SIZE.search(cell).group(0) for cell in cells]
    total = sum(_number(size, "width") for size in sizes[:old_cols])
    row_heights = [_number(sizes[row * old_cols], "height") for row in range(old_rows)]
    rows: list[list[str]] = [[] for _ in range(new_rows)]
    for index in range(wanted):
        row, col = divmod(index, new_cols)
        width = total // new_cols + (total % new_cols if col == new_cols - 1 else 0)
        size = _set(_set(sizes[index], "width", width), "height", row_heights[min(row, old_rows - 1)])
        cell = CELL_ADDR.sub(lambda found: _set(_set(found.group(0), "colAddr", col), "rowAddr", row), cells[index])
        rows[row].append(CELL_SIZE.sub(lambda _: size, cell, count=1))
    body = "".join(f"<hp:tr>{''.join(row)}</hp:tr>" for row in rows)
    removed = sum(row_heights[new_rows:])
    xml = xml[:block.start()] + body + xml[block.end():]
    xml = TABLE_OPEN.sub(lambda found: _set(_set(found.group(0), "rowCnt", new_rows), "colCnt", new_cols), xml, count=1)
    return TABLE_SIZE.sub(lambda found: _set(found.group(0), "height", max(_number(found.group(0), "height") - removed, 0)),
                          xml, count=1)
