"""교사가 준 엑셀(xlsx) 양식의 지정한 칸에 값만 채운다. 표준 라이브러리만 쓴다.

openpyxl처럼 통째로 읽고 다시 저장하지 않는다. 바꿀 칸의 XML만 고치고 나머지(서식, 병합, 조건부 서식,
데이터 유효성, 도형, 그림, 차트 등)는 압축 항목째 바이트 그대로 복사한다. 바뀌는 것은 고친 시트의 해당 칸과
workbook.xml의 "열 때 수식 다시 계산" 설정뿐이다.

사용법:
    python fill_xlsx.py --inspect 양식.xlsx               # 시트와 칸을 주소와 함께 보여 줌
    python fill_xlsx.py 양식.xlsx 지시.json 결과.xlsx     # 새 파일을 만듦 (원본은 그대로)

지시 JSON 형식:
{
  "fills": [
    {"sheet": "1반", "cell": "C5", "value": "홍길동"},    # 시트 이름(또는 1부터 센 번호)과 칸 주소의 값을 통째로
    {"sheet": 1, "cell": "D5", "value": 85},               # 숫자는 숫자로 (따옴표 없이). "85"는 글자로 들어감
    {"find": "○○", "replace": "국어", "all": true},        # 양식의 글을 바꿈. 여러 곳이면 all(모두)이나 nth(몇 번째)
    {"find": "○○", "replace": "국어", "sheet": "1반"}      # find에 sheet를 더하면 그 시트에서만 찾음
  ]
}

- 수식 칸은 덮어쓰지 않고 오류로 알린다 (합계 자동 계산을 지키기 위해). 열 때 엑셀이 수식을 다시 계산한다.
- 합친 칸은 왼쪽 위 칸의 주소를 쓴다. 다른 주소는 오류다.
- 양식 범위(--inspect에 나온 범위) 밖의 칸, 없는 시트, 못 찾은 글이 하나라도 있으면 파일을 만들지 않는다.
- value가 null이나 ""이면 칸을 비운다 (서식은 그대로).
- 찾는 자리는 모두 원본 양식에서 정한다. 한 칸을 두 번 고치면 오류다.
- 값은 인라인 문자열로 넣는다. 공유 문자열 표(sharedStrings.xml)는 건드리지 않는다.
- 글은 한 칸에 32,767자까지(엑셀 상한, 넘으면 오류). 15자리가 넘는 정수(학번·전화번호 등)는 엑셀이
  끝자리를 바꾸지 않도록 글자로 넣고 알려 준다.
- 행·열을 더하거나 서식, 병합, 수식을 바꾸는 일은 하지 못한다. 글자별 서식이 있던 칸을 find로 바꾸면
  칸 전체 서식만 남는다 (알려 줌). 데이터 유효성 목록에 맞는 값인지는 검사하지 않는다.
- xlsx와 xlsm만 채운다. 옛 xls와 암호가 걸린 파일은 엑셀에서 xlsx로 저장한 뒤 쓴다.
"""

from __future__ import annotations

import json
import math
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from fill_xlsx_parse import (CellSpan, SharedString, SheetScan, cell_name, describe, local, parse_cell,
                             read_shared_strings, scan_sheet)
from make_hwpx_save import file_error_message, save_atomically, write_zip
from make_hwpx_zip import PackageError, read_package, refuse_dtd, unsafe_name

MAX_ENTRY_BYTES = 64 * 1024 * 1024      # 이보다 큰 항목은 읽지 않는다 (압축 폭탄 방지)
MAX_TOTAL_BYTES = 512 * 1024 * 1024
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0"     # 옛 xls와 암호 걸린 파일의 시작
OLE_GUIDE = ("옛 엑셀(xls) 파일이거나 암호가 걸린 파일이라 채울 수 없습니다. 엑셀에서 열고 암호를 푼 뒤 "
             "[파일 > 다른 이름으로 저장하기]에서 파일 형식을 xlsx로 저장하고, 그 파일을 주세요.")
NOT_XLSX = "xlsx 파일이 아님. 엑셀에서 xlsx로 저장한 파일을 주세요"
WORKBOOK = "xl/workbook.xml"
WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
PLACES_SHOWN = 10
EXCEL_TEXT_LIMIT = 32767                # 엑셀 한 칸에 들어가는 글자 수 상한
EXACT_INTEGER_LIMIT = 10 ** 15          # 엑셀은 15자리까지만 정확히 담는다. 이보다 큰 정수는 글자로 넣는다
LINES_SHOWN = 2000
FIND_KEYS = {"find", "replace", "all", "nth", "sheet"}
CELL_KEYS = {"sheet", "cell", "value"}
BAD_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")
SAME_AS_SPACE = str.maketrans({" ": " ", "　": " ", " ": " ", **{chr(c): " " for c in range(0x2002, 0x200b)}})
CALC_PR = re.compile(r"<calcPr(?=[\s/>])[^>]*?/?>")
CALC_BEFORE = re.compile(r"<(?:oleSize|customWorkbookViews|pivotCaches|smartTagPr|smartTagTypes|webPublishing|"
                         r"fileRecoveryPr|webPublishObjects|extLst)(?=[\s/>])|</workbook>")


class FillError(ValueError):
    """교사에게 그대로 보여 줄 수 있는 실패."""


@dataclass(frozen=True)
class Sheet:
    index: int
    name: str
    state: str
    path: str
    xml: str = ""
    scan: SheetScan | None = None       # 워크시트가 아니면(차트 시트 등) None
    protected: bool = False

    @property
    def fillable(self) -> bool:
        return self.scan is not None


@dataclass(frozen=True)
class Form:
    infos: tuple[zipfile.ZipInfo, ...]
    entries: dict[str, bytes]
    sheets: tuple[Sheet, ...]
    shared: tuple[SharedString, ...]


@dataclass(frozen=True)
class Write:
    """한 칸에 넣을 값. value가 None이나 ""이면 칸을 비운다."""
    sheet: int
    row: int
    col: int
    value: object
    label: str
    rich: bool = False


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    new: str
    order: int = 0


# ---------------------------------------------------------------- 양식 읽기

def _read_package(path: Path) -> tuple[tuple[zipfile.ZipInfo, ...], dict[str, bytes]]:
    try:
        with path.open("rb") as handle:
            signature = handle.read(len(OLE_SIGNATURE))
    except OSError as error:
        raise FillError(f"양식 파일을 열 수 없음: {error}") from error
    if signature == OLE_SIGNATURE:
        raise FillError(OLE_GUIDE)
    try:
        return read_package(path, MAX_ENTRY_BYTES, MAX_TOTAL_BYTES, "엑셀")
    except PackageError as error:
        raise FillError(str(error)) from error
    except zipfile.BadZipFile as error:
        raise FillError(NOT_XLSX) from error


def _parse(entries: dict[str, bytes], name: str) -> tuple[str, ElementTree.Element]:
    try:
        refuse_dtd(entries[name], name)
        xml = entries[name].decode("utf-8")
        return xml, ElementTree.fromstring(xml)
    except PackageError as error:
        raise FillError(str(error)) from error
    except (KeyError, UnicodeDecodeError, ElementTree.ParseError) as error:
        raise FillError(f"양식의 {name}을 읽을 수 없음: {error}") from error


def _part_path(target: str, base: str, entries: dict[str, bytes]) -> str:
    joined = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(base, target))
    if joined.startswith("..") or unsafe_name(joined):
        raise FillError(f"양식의 연결 경로가 안전하지 않음: {target}")
    if joined not in entries:
        raise FillError(f"양식에 {joined} 파일이 없음")
    return joined


def _relationships(entries: dict[str, bytes]) -> dict[str, tuple[str, str]]:
    _, root = _parse(entries, WORKBOOK_RELS)
    return {item.get("Id", ""): (item.get("Type", ""), item.get("Target", "")) for item in root}


def _load_sheet(index: int, element: ElementTree.Element, rels: dict, entries: dict[str, bytes]) -> Sheet:
    name, state = element.get("name", ""), element.get("state", "visible")
    link = next((value for key, value in element.attrib.items() if local(key) == "id"), "")
    kind, target = rels.get(link, ("", ""))
    if not target:
        raise FillError(f"양식에서 시트 '{name}'의 파일을 찾을 수 없음")
    path = _part_path(target, "xl", entries)
    if not kind.endswith("/worksheet"):
        return Sheet(index, name, state, path)
    xml, _ = _parse(entries, path)
    try:
        scan = scan_sheet(xml)
    except ValueError as error:
        raise FillError(f"양식의 {path}을 읽을 수 없음: {error}") from error
    return Sheet(index, name, state, path, xml, scan, scan.protected)


def read_form(path: Path) -> Form:
    infos, entries = _read_package(Path(path))
    if WORKBOOK not in entries or "[Content_Types].xml" not in entries:
        raise FillError(NOT_XLSX)
    _, root = _parse(entries, WORKBOOK)
    holder = next((item for item in root if local(item.tag) == "sheets"), None)
    if holder is None or not len(holder):
        raise FillError("양식에 시트가 없음")
    rels = _relationships(entries)
    sheets = tuple(_load_sheet(number, item, rels, entries) for number, item in enumerate(holder, start=1))
    shared_rel = next((target for kind, target in rels.values() if kind.endswith("/sharedStrings")), None)
    shared = ()
    if shared_rel:
        xml, _ = _parse(entries, _part_path(shared_rel, "xl", entries))
        shared = read_shared_strings(xml)
    return Form(infos, entries, sheets, shared)


# ---------------------------------------------------------------- 살펴보기

def _shown(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", " ⏎ ")


def _merge_owner(scan: SheetScan, row: int, col: int) -> str | None:
    for first_row, first_col, last_row, last_col in scan.merges:
        if first_row <= row <= last_row and first_col <= col <= last_col and (row, col) != (first_row, first_col):
            return cell_name(first_row, first_col)
    return None


def _cell_line(cell: CellSpan, scan: SheetScan, shared: tuple[SharedString, ...]) -> str:
    name = cell_name(cell.row, cell.col)
    view = describe(cell, shared)
    if view.kind == "formula":
        return f"  {name}: [수식] ={view.formula}"
    owner = _merge_owner(scan, cell.row, cell.col)
    if view.kind == "empty":
        return f"  {name}: (합쳐진 칸. {owner} 사용)" if owner else f"  {name}: (빈 칸)"
    return f"  {name}: {_shown(view.text)}"


def _sheet_lines(sheet: Sheet, shared: tuple[SharedString, ...]) -> list[str]:
    marks = ""
    if sheet.state != "visible":
        marks += " [숨김]" if sheet.state == "hidden" else " [완전 숨김]"
    if sheet.protected:
        marks += " [시트 보호]"
    if not sheet.fillable:
        return [f'시트 {sheet.index} "{sheet.name}"{marks} [워크시트가 아니라 채울 수 없음]']
    scan = sheet.scan
    lines = [f'시트 {sheet.index} "{sheet.name}"{marks} (범위 {scan.area})']
    if scan.merges:
        lines.append("  합침: " + ", ".join(f"{cell_name(a, b)}:{cell_name(c, d)}" for a, b, c, d in scan.merges))
    cells = sorted((cell for row in scan.rows for cell in row.cells), key=lambda cell: (cell.row, cell.col))
    lines.extend(_cell_line(cell, scan, shared) for cell in cells[:LINES_SHOWN])
    if len(cells) > LINES_SHOWN:
        lines.append(f"  … 이하 {len(cells) - LINES_SHOWN}칸 생략")
    return lines


def inspect_form(path: Path) -> str:
    """시트와 칸의 목록. 시트 이름(또는 번호)과 칸 주소는 지시 JSON에 그대로 쓴다."""
    form = read_form(Path(path))
    lines = [line for sheet in form.sheets for line in _sheet_lines(sheet, form.shared)]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 지시 검사

def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _is_sheet_ref(value: object) -> bool:
    return _is_count(value) or (isinstance(value, str) and bool(value.strip()))


def _check_extra(fill: dict, allowed: set[str], where: str) -> None:
    extra = set(fill) - allowed
    if extra:
        raise FillError(f"{where}: 모르는 항목 {', '.join(sorted(extra))}")


def _check_text(value: object, key: str, where: str, allow_empty: bool = False) -> None:
    ok = isinstance(value, (str, int, float)) and not isinstance(value, bool)
    if allow_empty and value is None:
        return
    if not ok or (isinstance(value, float) and not math.isfinite(value)):
        raise FillError(f"{where}: {key}에는 글이나 숫자를 적어 주세요")
    if isinstance(value, str) and BAD_CHARS.search(value):
        raise FillError(f"{where}: {key}에 쓸 수 없는 제어 문자가 있음")
    if isinstance(value, str) and excel_length(value) > EXCEL_TEXT_LIMIT:
        raise FillError(_too_long(f"{where}: {key}", excel_length(value)))


def excel_length(text: str) -> int:
    """엑셀이 세는 글자 수(UTF-16 단위). 이모지처럼 BMP 밖 글자는 2로 센다."""
    return len(text.encode("utf-16-le")) // 2


def _too_long(where: str, length: int) -> str:
    return f"{where}: 글이 {length:,}자라 엑셀 한 칸에 넣을 수 있는 {EXCEL_TEXT_LIMIT:,}자를 넘음. 나눠서 넣어 주세요"


def _long_integer(value: object) -> bool:
    """15자리를 넘는 정수: 숫자로 넣으면 엑셀이 끝자리를 0으로 바꾼다 (학번·전화번호 등)."""
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) >= EXACT_INTEGER_LIMIT


def _validate_find(fill: dict, where: str) -> None:
    _check_extra(fill, FIND_KEYS, where)
    if not isinstance(fill["find"], str) or not fill["find"].translate(SAME_AS_SPACE).strip():
        raise FillError(f"{where}: find는 비어 있지 않은 글이어야 함")
    if "replace" not in fill:
        raise FillError(f"{where}: replace에 바꿀 글을 적어 주세요")
    _check_text(fill["replace"], "replace", where)
    if "all" in fill and "nth" in fill:
        raise FillError(f"{where}: all과 nth는 함께 쓸 수 없음")
    if not isinstance(fill.get("all", False), bool):
        raise FillError(f"{where}: all은 true 또는 false여야 함")
    if "nth" in fill and not _is_count(fill["nth"]):
        raise FillError(f"{where}: nth는 1 이상의 정수여야 함")
    if "sheet" in fill and not _is_sheet_ref(fill["sheet"]):
        raise FillError(f"{where}: sheet는 시트 이름이나 1 이상의 번호여야 함")


def _validate_cell(fill: dict, where: str) -> None:
    _check_extra(fill, CELL_KEYS, where)
    if not _is_sheet_ref(fill.get("sheet")):
        raise FillError(f"{where}: sheet는 시트 이름이나 1 이상의 번호여야 함")
    if parse_cell(fill.get("cell")) is None:
        raise FillError(f"{where}: 칸 주소가 올바르지 않음 (예: C5, 한 칸만)")
    if "value" not in fill:
        raise FillError(f"{where}: value에 넣을 값을 적어 주세요 (비우려면 null)")
    _check_text(fill["value"], "value", where, allow_empty=True)


def _validate_spec(spec: object) -> list[dict]:
    fills = spec.get("fills") if isinstance(spec, dict) else None
    if not isinstance(fills, list) or not fills:
        raise FillError('지시에 "fills" 목록이 없음')
    for number, fill in enumerate(fills, start=1):
        where = f"{number}번 지시"
        if not isinstance(fill, dict):
            raise FillError(f"{where}: 항목은 {{...}} 꼴이어야 함")
        if "find" in fill:
            _validate_find(fill, where)
        elif "sheet" in fill or "cell" in fill:
            _validate_cell(fill, where)
        else:
            raise FillError(f"{where}: find 또는 sheet와 cell이 있어야 함")
    return fills


# ---------------------------------------------------------------- 고칠 칸 정하기

def _find_sheet(form: Form, reference: object, where: str) -> Sheet:
    if isinstance(reference, int):
        if reference > len(form.sheets):
            raise FillError(f"{where}: 시트 {reference} 없음 (시트 {len(form.sheets)}개)")
        sheet = form.sheets[reference - 1]
    else:
        sheet = next((item for item in form.sheets if item.name == reference), None)
        if sheet is None:
            names = ", ".join(item.name for item in form.sheets)
            raise FillError(f'{where}: 시트 "{reference}" 없음 (있는 시트: {names})')
    if not sheet.fillable:
        raise FillError(f'{where}: 시트 "{sheet.name}"는 워크시트가 아니라 채울 수 없음')
    return sheet


def _place(sheet: Sheet, row: int, col: int) -> str:
    return f"{sheet.name}!{cell_name(row, col)}"


def _existing_cell(sheet: Sheet, row: int, col: int) -> CellSpan | None:
    found = sheet.scan.row_map.get(row)
    return next((cell for cell in found.cells if cell.col == col), None) if found else None


def _check_cell(sheet: Sheet, row: int, col: int, shared: tuple[SharedString, ...], where: str) -> None:
    place, scan = _place(sheet, row, col), sheet.scan
    if row > scan.max_row or col > scan.max_col:
        raise FillError(f"{where}: {place}는 양식 범위({scan.area}) 밖. 양식에 없는 칸은 채우지 않음")
    owner = _merge_owner(scan, row, col)
    if owner:
        raise FillError(f"{where}: {place}는 {owner}에 합쳐져 있음. 합친 칸의 왼쪽 위 칸 {owner}를 써 주세요")
    cell = _existing_cell(sheet, row, col)
    if cell and describe(cell, shared).kind == "formula":
        raise FillError(f"{where}: {place}는 수식 칸이라 덮어쓰지 않음 (합계 자동 계산을 지키기 위해)")


def _plan_value(form: Form, fill: dict, where: str) -> list[Write]:
    sheet = _find_sheet(form, fill["sheet"], where)
    row, col = parse_cell(fill["cell"])
    _check_cell(sheet, row, col, form.shared, where)
    return [Write(sheet.index, row, col, fill["value"], where)]


def _spaced(text: str) -> str:
    return text.translate(SAME_AS_SPACE)


def _matches(form: Form, sheets: list[Sheet], target: str) -> list[tuple[Sheet, CellSpan, int, bool]]:
    found = []
    for sheet in sheets:
        cells = sorted((cell for row in sheet.scan.rows for cell in row.cells), key=lambda c: (c.row, c.col))
        for cell in cells:
            view = describe(cell, form.shared)
            text = _spaced(view.text) if view.kind == "text" else ""
            position = text.find(target)
            while position != -1:
                found.append((sheet, cell, position, view.rich))
                position = text.find(target, position + len(target))
    return found


def _choose(found: list, fill: dict, where: str) -> list:
    label = f'{where}: "{fill["find"]}"'
    if not found:
        raise FillError(f"{label} 찾지 못함")
    if fill.get("all"):
        return found
    if "nth" in fill:
        if fill["nth"] > len(found):
            raise FillError(f"{label} {len(found)}곳뿐인데 nth가 {fill['nth']}임")
        return [found[fill["nth"] - 1]]
    if len(found) > 1:
        places = ", ".join(_place(sheet, cell.row, cell.col) for sheet, cell, _, _ in found[:PLACES_SHOWN])
        more = " 등" if len(found) > PLACES_SHOWN else ""
        raise FillError(f'{label} {len(found)}곳에 있음({places}{more}). "all": true 또는 "nth": 번호로 정해 주세요')
    return found


def _plan_find(form: Form, fill: dict, where: str) -> list[Write]:
    target = _spaced(fill["find"])
    sheets = [_find_sheet(form, fill["sheet"], where)] if "sheet" in fill else [s for s in form.sheets if s.fillable]
    chosen = _choose(_matches(form, sheets, target), fill, where)
    by_cell: dict[tuple[int, int, int], list] = {}
    for sheet, cell, position, rich in chosen:
        by_cell.setdefault((sheet.index, cell.row, cell.col), []).append((position, rich))
    writes = []
    for (index, row, col), hits in by_cell.items():
        cell = _existing_cell(form.sheets[index - 1], row, col)
        text, new = describe(cell, form.shared).text, str(fill["replace"])
        for position, _ in sorted(hits, reverse=True):
            text = text[:position] + new + text[position + len(target):]
        writes.append(Write(index, row, col, text, where, hits[0][1]))
    return writes


def _check_overlap(writes: list[Write], form: Form) -> None:
    seen: dict[tuple[int, int, int], Write] = {}
    problems = []
    for write in writes:
        key = (write.sheet, write.row, write.col)
        if key in seen:
            place = _place(form.sheets[write.sheet - 1], write.row, write.col)
            problems.append(f"{seen[key].label}와 {write.label}의 자리({place})가 겹침. 한 칸은 한 번만 고쳐 주세요")
        seen.setdefault(key, write)
    if problems:
        raise FillError("\n".join(problems))


def _plan(form: Form, fills: list[dict]) -> list[Write]:
    """모든 지시의 칸을 원본에서 정한다. 실패한 지시는 모아서 한 번에 알린다."""
    writes: list[Write] = []
    failures: list[str] = []
    for number, fill in enumerate(fills, start=1):
        planner = _plan_find if "find" in fill else _plan_value
        try:
            writes += planner(form, fill, f"{number}번 지시")
        except FillError as error:
            failures.append(str(error))
    if failures:
        raise FillError("\n".join(failures))
    _check_overlap(writes, form)
    return writes


# ---------------------------------------------------------------- 쓰기

def _value_parts(value: object) -> tuple[str, str]:
    """(t 속성, 칸 안쪽 XML). 글자는 인라인 문자열, 숫자는 그대로."""
    if value is None or value == "":
        return "", ""
    if _long_integer(value):
        value = str(value)
    if isinstance(value, str):
        text = value.replace("\r\n", "\n").replace("\r", "\n")
        if excel_length(text) > EXCEL_TEXT_LIMIT:
            raise FillError(_too_long("채운 칸", excel_length(text)))
        return ' t="inlineStr"', f'<is><t xml:space="preserve">{escape(text)}</t></is>'
    return "", f"<v>{value!r}</v>"


def _cell_xml(attrs: str, value: object) -> str:
    kind, inner = _value_parts(value)
    return f"<c{attrs}{kind}>{inner}</c>" if inner else f"<c{attrs}/>"


def _without_type(attrs: str) -> str:
    return re.sub(r"""\s+t=(?:"[^"]*"|'[^']*')""", "", attrs)


def _without_spans(attrs: str) -> str:
    return re.sub(r"""\s+spans=(?:"[^"]*"|'[^']*')""", "", attrs)


def _new_cell(row: int, col: int, value: object) -> str:
    return _cell_xml(f' r="{cell_name(row, col)}"', value)


def _need_addresses(scan: SheetScan, sheet: Sheet) -> None:
    if scan.implicit:
        raise FillError(f'시트 "{sheet.name}"는 칸 주소가 생략된 형식이라 빈 자리에 새로 넣을 수 없음. '
                        "엑셀에서 한 번 저장한 양식을 주세요")


def _row_edits(sheet: Sheet, row, cols: dict[int, object]) -> list[Edit]:
    edits, added = [], {}
    for col, value in cols.items():
        cell = next((item for item in row.cells if item.col == col), None)
        if cell:
            edits.append(Edit(cell.start, cell.end, _cell_xml(_without_type(cell.attrs), value)))
        else:
            added[col] = value
    if not added:
        return edits
    _need_addresses(sheet.scan, sheet)
    if row.self_closing:
        body = "".join(_new_cell(row.number, col, added[col]) for col in sorted(added))
        return edits + [Edit(row.start, row.end, f"<row{_without_spans(row.attrs)}>{body}</row>")]
    edits.append(Edit(row.start, row.open_end, f"<row{_without_spans(row.attrs)}>"))
    for col in sorted(added):
        anchor = next((item.start for item in row.cells if item.col > col), row.close_start)
        edits.append(Edit(anchor, anchor, _new_cell(row.number, col, added[col]), col))
    return edits


def _new_rows_edits(sheet: Sheet, rows: dict[int, dict[int, object]]) -> list[Edit]:
    if not rows:
        return []
    scan = sheet.scan
    _need_addresses(scan, sheet)
    xml = {number: f'<row r="{number}">' + "".join(_new_cell(number, col, value) for col, value in sorted(cols.items()))
           + "</row>" for number, cols in rows.items()}
    if scan.close_start is None:
        start, end = scan.data_open
        return [Edit(start, end, "<sheetData>" + "".join(xml[n] for n in sorted(xml)) + "</sheetData>")]
    existing = scan.rows
    edits = []
    for number in sorted(xml):
        anchor = next((row.start for row in existing if row.number > number), scan.close_start)
        edits.append(Edit(anchor, anchor, xml[number], number))
    return edits


def _sheet_edits(sheet: Sheet, writes: list[Write]) -> list[Edit]:
    by_row: dict[int, dict[int, object]] = {}
    for write in writes:
        by_row.setdefault(write.row, {})[write.col] = write.value
    row_map = sheet.scan.row_map
    edits, missing = [], {}
    for number, cols in by_row.items():
        if number in row_map:
            edits += _row_edits(sheet, row_map[number], cols)
        else:
            missing[number] = cols
    return edits + _new_rows_edits(sheet, missing)


def _apply(xml: str, edits: list[Edit]) -> str:
    pieces, position = [], 0
    for edit in sorted(edits, key=lambda item: (item.start, item.end, item.order)):
        pieces += [xml[position:edit.start], edit.new]
        position = edit.end
    pieces.append(xml[position:])
    return "".join(pieces)


def _recalc_on_open(xml: str) -> str:
    """열 때 엑셀이 모든 수식을 다시 계산하게 한다. 합계 칸의 옛 계산값이 남지 않도록."""
    found = CALC_PR.search(xml)
    if found:
        tag = re.sub(r"""\s+fullCalcOnLoad=(?:"[^"]*"|'[^']*')""", "", found.group(0))
        tag = re.sub(r"/?>$", ' fullCalcOnLoad="1"/>', tag)
        return xml[:found.start()] + tag + xml[found.end():]
    anchor = CALC_BEFORE.search(xml)
    if not anchor:
        raise FillError("양식의 workbook.xml 구조를 알 수 없음")
    return xml[:anchor.start()] + '<calcPr fullCalcOnLoad="1"/>' + xml[anchor.start():]


def _checked(name: str, xml: str) -> bytes:
    try:
        ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise FillError(f"채운 결과의 {name}이 깨짐: {error}") from error
    return xml.encode("utf-8")


def _changed_entries(form: Form, writes: list[Write]) -> dict[str, bytes]:
    entries = dict(form.entries)
    for sheet in form.sheets:
        mine = [write for write in writes if write.sheet == sheet.index]
        if mine:
            entries[sheet.path] = _checked(sheet.path, _apply(sheet.xml, _sheet_edits(sheet, mine)))
    workbook = form.entries[WORKBOOK].decode("utf-8")
    entries[WORKBOOK] = _checked(WORKBOOK, _recalc_on_open(workbook))
    return entries


def _check_written(path: Path) -> None:
    """다시 열어 읽히는지 본다."""
    with zipfile.ZipFile(path) as archive:
        broken = archive.testzip()
    if broken:
        raise FillError(f"채운 파일 검사 실패: {broken}")
    read_form(path)


def _publish(form: Form, entries: dict[str, bytes], target: Path) -> None:
    """같은 폴더의 임시 파일에 쓰고, 다시 열어 읽히는지 본 뒤에 결과 파일로 옮긴다."""
    save_atomically(target, lambda path: write_zip(path, form.infos, entries), _check_written)


def _notes(form: Form, writes: list[Write]) -> list[str]:
    notes = []
    for sheet in (form.sheets[index - 1] for index in sorted({write.sheet for write in writes})):
        if sheet.state != "visible":
            notes.append(f'시트 "{sheet.name}"는 숨김 시트입니다. 숨김 시트에도 채웠으니 맞는 시트인지 확인해 주세요')
        if sheet.protected:
            notes.append(f'시트 "{sheet.name}"는 보호된 시트입니다. 채운 뒤 고치려면 엑셀에서 보호를 풀어야 합니다')
    long_numbers = sum(1 for write in writes if _long_integer(write.value))
    if long_numbers:
        notes.append(f"15자리가 넘는 정수 {long_numbers}칸은 엑셀이 끝자리를 바꾸지 않도록 글자로 넣었습니다")
    rich = sum(1 for write in writes if write.rich)
    if rich:
        notes.append(f"글자별 서식(굵게, 색 등)이 있던 {rich}칸은 칸 전체 서식만 남았습니다. 엑셀에서 확인해 주세요")
    return notes


def _check_paths(source: Path, target: Path) -> None:
    if target.suffix.lower() != source.suffix.lower():
        raise FillError(f"결과 파일의 확장자는 양식과 같아야 함 ({source.suffix})")
    if target.exists():
        if source.exists() and target.samefile(source):
            raise FillError("원본 양식을 덮어쓸 수 없음. 결과 파일 이름을 다르게 적어 주세요")
        raise FillError(f"이미 있는 파일이라 덮어쓰지 않음: {target.name}. 다른 이름을 적어 주세요")
    if not target.parent.is_dir():
        raise FillError(f"결과를 저장할 폴더가 없음: {target.parent}")


def fill_form_notes(source: Path, spec: dict, target: Path) -> tuple[int, list[str]]:
    """양식을 채워 target에 새 파일을 만들고 (채운 칸 수, 알림 문장들)을 돌려준다. 실패하면 FillError."""
    source, target = Path(source), Path(target)
    _check_paths(source, target)
    fills = _validate_spec(spec)
    form = read_form(source)
    writes = _plan(form, fills)
    _publish(form, _changed_entries(form, writes), target)
    return len(writes), _notes(form, writes)


def fill_form(source: Path, spec: dict, target: Path) -> int:
    """fill_form_notes에서 채운 칸 수만 돌려준다."""
    return fill_form_notes(source, spec, target)[0]


# ---------------------------------------------------------------- 명령줄

def _run_fill(source: str, spec_path: str, target: str) -> str:
    try:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise FillError(f"지시 파일을 읽을 수 없음: {error}") from error
    count, notes = fill_form_notes(Path(source), spec, Path(target))
    lines = [f"완료: {target} ({count}곳 채움). 합계 같은 수식은 엑셀이 열 때 다시 계산합니다", *notes]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """통과면 0, 실패면 1, 사용법이 틀리면 2."""
    args = sys.argv[1:] if argv is None else argv
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    try:
        if len(args) == 2 and args[0] == "--inspect":
            sys.stdout.write(inspect_form(Path(args[1])))
        elif len(args) == 3 and not args[0].startswith("--"):
            sys.stdout.write(_run_fill(*args))
        else:
            sys.stdout.write("사용법: python fill_xlsx.py --inspect 양식.xlsx\n"
                             "        python fill_xlsx.py 양식.xlsx 지시.json 결과.xlsx\n")
            return 2
    except FillError as error:
        sys.stdout.write(f"{error}\n")
        return 1
    except OSError as error:
        sys.stdout.write(file_error_message(error) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
