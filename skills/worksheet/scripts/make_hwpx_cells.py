"""make_hwpx.py의 표 칸: 칸 값 읽기, 합친 칸 배치, 열 너비, 칸 높이 어림. 표준 라이브러리만 쓴다."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from make_hwpx_design import CellDesign, read_design
from make_hwpx_shapes import PX, read_shape
from make_hwpx_options import _bool_option, _choice, _int_option
from make_hwpx_text import as_text

# 칸 글자의 줄 수를 어림할 때 쓰는 값 (10pt 글자, 줄 간격 130%, 칸 안쪽 여백 좌우 510·위아래 141)
CELL_FULL_CHAR_WIDTH = 1000
CELL_HALF_CHAR_WIDTH = 500
CELL_LINE_HEIGHT = 1300
CELL_MARGIN_X = 510                     # 칸 안쪽 여백 좌우
CELL_MARGIN_Y = 141                     # 칸 안쪽 여백 위아래
CELL_PADDING_X = 2 * CELL_MARGIN_X
CELL_PADDING_Y = 2 * CELL_MARGIN_Y
ROW_HEIGHT = 1800
MAX_SPAN = 50                           # 칸 합치기 한도
MAX_TABLE_ROWS = 500
MAX_TABLE_COLS = 30
MAX_LINES = 50                          # 답 칸·쓰기 칸 줄 수 한도
CELL_VALIGNS = ("top", "center", "bottom")
CELL_ALIGNS = ("left", "center", "right")
ANSWER_LINE_HEIGHT = 2400


@dataclass(frozen=True)
class TableCell:
    text: str
    row: int
    col: int
    rowspan: int
    colspan: int
    header: bool
    shade: bool
    bold: bool
    align: str
    valign: str | None
    lines: int
    design: CellDesign | None = None
    content: tuple = ()


def _span(spec: dict, key: str, where: str) -> int:
    value = spec.get(key, 1)
    if value is None:
        return 1
    return _int_option(value, f"{where}: {key}", 1, MAX_SPAN)


def _make_cell(raw, row: int, col: int, header_rows: int) -> TableCell:
    spec = raw if isinstance(raw, dict) else {"text": raw}
    content = _content(spec.get("content"), row)
    text = "".join(item if isinstance(item, str) else item.get("run", "") for item in content) if content         else as_text(spec.get("text"))
    where = f"{row + 1}행 '{text[:10]}' 칸"
    is_header = _bool_option(spec.get("header"), f"{where}: header", row < header_rows)
    lines = spec.get("lines")
    return TableCell(
        text=text, row=row, col=col,
        rowspan=_span(spec, "rowspan", where), colspan=_span(spec, "colspan", where),
        header=is_header, shade=_bool_option(spec.get("shade"), f"{where}: shade", is_header),
        bold=_bool_option(spec.get("bold"), f"{where}: bold", is_header),
        align=_choice(spec.get("align"), f"{where}: align", CELL_ALIGNS, "center" if is_header else "left"),
        valign=_choice(spec.get("valign"), f"{where}: valign", CELL_VALIGNS, "") or None,
        lines=0 if lines is None else _int_option(lines, f"{where}: lines", 0, MAX_LINES),
        design=read_design(spec, where), content=content,
    )


def _content(value, row: int) -> tuple:
    """칸 content: 글과 도형(make_hwpx_shapes)을 섞어 놓은 목록. 도형 값은 검사한다."""
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{row + 1}행 칸의 content는 글자와 도형의 목록이어야 함 (받은 값: {value!r})")
    return tuple(_content_item(item, row) for item in value)


def _content_item(item, row: int):
    if isinstance(item, dict) and "run" in item:      # 글자 모양이 따로 있는 글 조각
        return {**item, "run": as_text(item["run"])}
    if isinstance(item, dict):
        return read_shape(item, f"{row + 1}행 칸 도형")
    return as_text(item)


def layout_table(rows: list, header_rows: int) -> tuple[list[TableCell], int]:
    """HTML 표처럼 rowspan/colspan으로 합쳐 가려진 칸은 생략해서 쓴다. (칸 목록, 열 수)를 돌려준다."""
    if len(rows) > MAX_TABLE_ROWS:
        raise ValueError(f"표는 최대 {MAX_TABLE_ROWS}행까지 만들 수 있음 (받은 행 수: {len(rows)})")
    occupied: set[tuple[int, int]] = set()
    cells: list[TableCell] = []
    for r, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            raise ValueError(f"{r + 1}행은 목록이어야 함 (받은 값: {row!r})")
        if len(row) > MAX_TABLE_COLS:
            raise ValueError(f"{r + 1}행의 칸이 너무 많음: 표는 최대 {MAX_TABLE_COLS}열까지 만들 수 있음")
        c = 0
        for raw in row:
            while (r, c) in occupied:
                c += 1
            cell = _make_cell(raw, r, c, header_rows)
            if c + cell.colspan > MAX_TABLE_COLS:
                raise ValueError(f"{r + 1}행 '{cell.text[:10]}' 칸이 표 너비를 넘음: 최대 {MAX_TABLE_COLS}열")
            if r + cell.rowspan > len(rows):
                raise ValueError(f"{r + 1}행 '{cell.text[:10]}' 칸의 rowspan이 표 아래로 넘침")
            area = {(r + dr, c + dc) for dr in range(cell.rowspan) for dc in range(cell.colspan)}
            if area & occupied:
                raise ValueError(f"{r + 1}행 '{cell.text[:10]}' 칸이 위에서 합친 칸과 겹침")
            occupied |= area
            cells.append(cell)
            c += cell.colspan
    covered_per_row = Counter(row for row, _ in occupied)
    cols = covered_per_row[0]  # 첫 행의 너비를 표의 열 수로 본다
    for r in range(len(rows)):
        covered = covered_per_row[r]
        if covered != cols:
            raise ValueError(f"{r + 1}행의 칸 수가 맞지 않음: {covered}칸 / 표는 {cols}칸 (rowspan·colspan을 확인해 주세요)")
    return cells, cols


def _row_heights(cells: list[TableCell], row_count: int, base: int) -> list[int]:
    """행 높이. 칸에 height_px가 있으면 그 행은 기본 높이 대신 그 값(칸 중 가장 큰 값)을 쓴다."""
    explicit: dict[int, int] = {}
    for cell in cells:
        if cell.design and cell.design.height_px and cell.rowspan == 1:
            explicit[cell.row] = max(explicit.get(cell.row, 0), round(cell.design.height_px * PX))
    heights = [explicit.get(row, base) for row in range(row_count)]
    for cell in cells:
        if cell.lines and cell.rowspan == 1:
            heights[cell.row] = max(heights[cell.row], cell.lines * ANSWER_LINE_HEIGHT)
    return heights


def _text_lines(text: str, width: int) -> int:
    """칸 너비에 글자가 몇 줄로 들어갈지 어림한다 (한글·전각은 1칸, 영문·숫자·공백은 반 칸)."""
    usable = max(width - CELL_PADDING_X, CELL_FULL_CHAR_WIDTH)
    lines = 0
    for part in text.split("\n"):
        used = sum(CELL_HALF_CHAR_WIDTH if ord(ch) < 0x1100 else CELL_FULL_CHAR_WIDTH for ch in part
                   if not 0xE000 <= ord(ch) <= 0xE00F)          # 형광펜·메모 표식 (course-plan course_form_marks.py)
        lines += max(1, -(-used // usable))
    return lines


def _estimated_rows(cells: list[TableCell], heights: list[int], col_widths: list[int]) -> list[int]:
    """행마다 행 높이와 칸 글자 줄 수 중 큰 값으로 높이를 어림한다 (쪽 나눔 방식을 고를 때만 쓴다)."""
    rows = list(heights)
    for cell in cells:
        if cell.rowspan != 1:
            continue
        width = sum(col_widths[cell.col:cell.col + cell.colspan])
        text_height = _text_lines(cell.text, width) * CELL_LINE_HEIGHT + CELL_PADDING_Y
        rows[cell.row] = max(rows[cell.row], text_height)
    return rows


def _box_height(cells: list[TableCell], rows: list[int], col_widths: list[int]) -> int:
    """상자(keep_together 표) 전체 높이 어림: 행 높이 합에, 여러 행을 합친 칸의 글이 걸친 행들보다 길면 그만큼 더한다."""
    extra = 0
    for cell in cells:
        if cell.rowspan == 1:
            continue
        width = sum(col_widths[cell.col:cell.col + cell.colspan])
        need = _text_lines(cell.text, width) * CELL_LINE_HEIGHT + CELL_PADDING_Y
        extra = max(extra, need - sum(rows[cell.row:cell.row + cell.rowspan]))
    return sum(rows) + extra


def _split_width(total: int, ratios: list) -> list[int]:
    valid = isinstance(ratios, (list, tuple)) and ratios and all(
        not isinstance(r, bool) and isinstance(r, (int, float)) and math.isfinite(r) and r > 0 for r in ratios)
    if not valid or not math.isfinite(sum(ratios)):
        raise ValueError(f"widths는 양수 목록이어야 함: {ratios}")
    widths = [int(total * r / sum(ratios)) for r in ratios]
    widths[-1] += total - sum(widths)
    if min(widths) <= 0:
        raise ValueError(f"widths 비율 차이가 너무 커서 열 너비가 0이 됨: {ratios}")
    return widths
