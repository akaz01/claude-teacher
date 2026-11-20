"""fill_xlsx.py가 쓰는 xlsx 읽기 도구. 표준 라이브러리만 쓴다.

시트 XML을 다시 쓰지 않고 칸(`<c>`)과 행(`<row>`)의 글자 위치만 찾아 두기 위한 것이다.
위치를 알면 바꿀 칸만 고치고 나머지 부분은 바이트 그대로 둘 수 있다.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from xml.etree import ElementTree

MAX_ROW, MAX_COL = 1048576, 16384
CELL_REF = re.compile(r"^([A-Za-z]{1,3})([1-9][0-9]{0,6})$")
RANGE_REF = re.compile(r"^([A-Za-z]{1,3})([1-9][0-9]{0,6}):([A-Za-z]{1,3})([1-9][0-9]{0,6})$")
ATTRS = r"""(?:[^>"']|"[^"]*"|'[^']*')*?"""
SHEET_DATA = re.compile(rf"<sheetData(?=[\s/>]){ATTRS}(/?)>")
ROW_OPEN = re.compile(rf"<row(?=[\s/>])({ATTRS})(/?)>")
CELL_OPEN = re.compile(rf"<c(?=[\s/>])({ATTRS})(/?)>")
FORMULA = re.compile(r"<f(?=[\s/>])[^>]*?(?:/>|>(.*?)</f>)", re.S)
VALUE = re.compile(r"<v(?:\s[^>]*)?>(.*?)</v>", re.S)
INLINE = re.compile(r"<is(?:\s[^>]*)?>(.*?)</is>", re.S)
TEXT_PIECE = re.compile(r"<t(?:\s[^>]*)?>(.*?)</t>", re.S)
PHONETIC = re.compile(r"<rPh\b.*?</rPh>", re.S)
MERGE = re.compile(r"<mergeCell\s[^>]*?ref=\"([^\"]+)\"")
DIMENSION = re.compile(r"<dimension\s[^>]*?ref=\"([^\"]+)\"")
PROTECTION = re.compile(r"<sheetProtection(?=[\s/>])")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def column_number(letters: str) -> int:
    number = 0
    for letter in letters.upper():
        number = number * 26 + ord(letter) - 64
    return number


def column_letters(number: int) -> str:
    letters = ""
    while number:
        number, rest = divmod(number - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def cell_name(row: int, col: int) -> str:
    return f"{column_letters(col)}{row}"


def parse_cell(ref: str) -> tuple[int, int] | None:
    """'C5' -> (행 5, 열 3). 엑셀 범위를 넘거나 꼴이 틀리면 None."""
    found = CELL_REF.match(ref) if isinstance(ref, str) else None
    if not found:
        return None
    row, col = int(found.group(2)), column_number(found.group(1))
    return (row, col) if row <= MAX_ROW and col <= MAX_COL else None


def parse_range(ref: str) -> tuple[int, int, int, int] | None:
    """'A1:F3' -> (첫 행, 첫 열, 끝 행, 끝 열). 한 칸 'A1'도 받는다."""
    found = RANGE_REF.match(ref)
    if not found:
        single = parse_cell(ref)
        return (single[0], single[1], single[0], single[1]) if single else None
    first, last = parse_cell(found.group(1) + found.group(2)), parse_cell(found.group(3) + found.group(4))
    return (first[0], first[1], last[0], last[1]) if first and last else None


def attr(attrs: str, name: str) -> str | None:
    found = re.search(rf"""\s{name}=(?:"([^"]*)"|'([^']*)')""", attrs)
    if not found:
        return None
    return html.unescape(found.group(1) if found.group(1) is not None else found.group(2))


@dataclass(frozen=True)
class SharedString:
    text: str
    rich: bool


def read_shared_strings(xml: str) -> tuple[SharedString, ...]:
    items = []
    for item in ElementTree.fromstring(xml):
        if local(item.tag) != "si":
            continue
        pieces, rich = [], False
        for child in item:
            name = local(child.tag)
            if name == "t":
                pieces.append(child.text or "")
            elif name == "r":
                rich = True
                pieces.extend(piece.text or "" for piece in child if local(piece.tag) == "t")
        items.append(SharedString("".join(pieces), rich))
    return tuple(items)


@dataclass(frozen=True)
class CellSpan:
    row: int
    col: int
    start: int
    end: int
    attrs: str
    inner: str


@dataclass(frozen=True)
class RowSpan:
    number: int
    start: int
    open_end: int          # 여는 태그가 끝나는 자리 (한 줄짜리 <row/>면 end와 같다)
    close_start: int | None
    end: int
    attrs: str
    cells: tuple[CellSpan, ...]

    @property
    def self_closing(self) -> bool:
        return self.close_start is None


@dataclass(frozen=True)
class SheetScan:
    rows: tuple[RowSpan, ...]
    data_open: tuple[int, int]          # <sheetData ...>의 [시작, 끝)
    close_start: int | None             # </sheetData>의 시작. 한 줄짜리면 None
    merges: tuple[tuple[int, int, int, int], ...]
    max_row: int
    max_col: int
    implicit: bool                      # 행·칸에 주소(r)가 없는 시트
    protected: bool

    @property
    def row_map(self) -> dict[int, RowSpan]:
        return {row.number: row for row in self.rows}

    @property
    def area(self) -> str:
        return f"A1:{cell_name(self.max_row, self.max_col)}"


def _scan_cells(xml: str, start: int, stop: int, row_number: int) -> tuple[list[CellSpan], bool]:
    cells, implicit, col, position = [], False, 0, start
    while (found := CELL_OPEN.search(xml, position, stop)):
        end = found.end() if found.group(2) else xml.index("</c>", found.end(), stop) + 4
        ref = attr(found.group(1), "r")
        parsed = parse_cell(ref) if ref else None
        implicit = implicit or parsed is None
        col = parsed[1] if parsed else col + 1
        inner = "" if found.group(2) else xml[found.end():end - 4]
        cells.append(CellSpan(row_number, col, found.start(), end, found.group(1), inner))
        position = end
    return cells, implicit


def _scan_rows(xml: str, start: int, stop: int) -> tuple[list[RowSpan], bool]:
    rows, implicit, number, position = [], False, 0, start
    while (found := ROW_OPEN.search(xml, position, stop)):
        given = attr(found.group(1), "r")
        implicit = implicit or not (given and given.isdigit())
        number = int(given) if given and given.isdigit() else number + 1
        if found.group(2):
            rows.append(RowSpan(number, found.start(), found.end(), None, found.end(), found.group(1), ()))
            position = found.end()
            continue
        close = xml.index("</row>", found.end(), stop)
        cells, cells_implicit = _scan_cells(xml, found.end(), close, number)
        implicit = implicit or cells_implicit
        rows.append(RowSpan(number, found.start(), found.end(), close, close + 6, found.group(1), tuple(cells)))
        position = close + 6
    return rows, implicit


def scan_sheet(xml: str) -> SheetScan:
    """시트 XML에서 행과 칸의 위치를 찾는다. 처리할 수 없는 구조면 ValueError."""
    opened = SHEET_DATA.search(xml)
    if not opened:
        raise ValueError("sheetData를 찾을 수 없음 (지원하지 않는 시트 구조)")
    close = None if opened.group(1) else xml.find("</sheetData>", opened.end())
    if close == -1:
        raise ValueError("sheetData가 닫히지 않음")
    rows, implicit = ([], False) if close is None else _scan_rows(xml, opened.end(), close)
    merges = tuple(box for box in (parse_range(ref) for ref in MERGE.findall(xml)) if box)
    boxes = [(cell.row, cell.col, cell.row, cell.col) for row in rows for cell in row.cells]
    dimension = DIMENSION.search(xml)
    declared = parse_range(dimension.group(1)) if dimension else None
    corners = [*boxes, *merges, *([declared] if declared else [])]
    return SheetScan(tuple(rows), (opened.start(), opened.end()), close, merges,
                     max((box[2] for box in corners), default=1), max((box[3] for box in corners), default=1),
                     implicit, bool(PROTECTION.search(xml)))


@dataclass(frozen=True)
class CellView:
    kind: str            # empty / text / number / formula
    text: str
    formula: str = ""
    rich: bool = False


def _inline_text(inner: str) -> str:
    found = INLINE.search(inner)
    body = PHONETIC.sub("", found.group(1)) if found else ""
    return html.unescape("".join(TEXT_PIECE.findall(body)))


def describe(cell: CellSpan, shared: tuple[SharedString, ...]) -> CellView:
    formula = FORMULA.search(cell.inner)
    if formula:
        return CellView("formula", "", html.unescape(formula.group(1) or ""))
    kind = attr(cell.attrs, "t")
    if kind == "inlineStr":
        text = _inline_text(cell.inner)
        return CellView("text" if text else "empty", text)
    value = VALUE.search(cell.inner)
    if value is None:
        return CellView("empty", "")
    raw = html.unescape(value.group(1))
    if kind == "s":
        index = int(raw) if raw.isdigit() else -1
        item = shared[index] if 0 <= index < len(shared) else SharedString("", False)
        return CellView("text" if item.text else "empty", item.text, rich=item.rich)
    if kind == "b":
        return CellView("number", "TRUE" if raw == "1" else "FALSE")
    return CellView("text" if kind in ("str", "e", "d") else "number", raw)
