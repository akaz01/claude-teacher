"""교사가 준 hwpx 양식의 지정한 자리에 글만 채운다. 표준 라이브러리만 쓴다.

용지, 문단 모양, 글자 모양, 크기, 표 구조는 건드리지 않는다. 바뀌는 것은 지정한 글과
그 문단의 줄 배치 정보(한글이 열 때 다시 계산), 미리 보기 글(Preview/PrvText.txt)뿐이다.

사용법:
    python fill_hwpx.py --inspect 양식.hwpx               # 문단과 표 칸을 번호와 함께 보여 줌
    python fill_hwpx.py 양식.hwpx 지시.json 결과.hwpx     # 새 파일을 만듦 (원본은 그대로)

지시 JSON 형식:
{
  "fills": [
    {"find": "○○ 단원", "replace": "일차방정식"},      # 찾을 글을 바꿀 글로 (첫 글자의 모양을 따름)
    {"find": "○월", "replace": "3월", "all": true},     # 여러 곳이면 모두. 안 쓰면 오류로 알림
    {"find": "학년", "replace": "2학년", "nth": 2},     # 여러 곳 중 몇 번째만 (1부터)
    {"table": 1, "row": 2, "col": 3, "text": "내용"}    # 표 번호·행·칸(1부터, --inspect의 번호)의 글을 통째로
  ]
}

- 찾는 자리는 모두 원본 양식에서 정한다. 앞 지시로 넣은 글을 뒤 지시가 찾지 않는다.
- 찾는 글은 한 문단 안에서 찾고, 글자 모양이 달라지는 경계는 넘을 수 있다. 메모 글은 찾지 않는다.
- 특수 공백은 보통 공백으로 찾는다. 바꿀 글의 \\n은 같은 문단의 줄바꿈이 된다.
- 칸 쓰기는 첫 문단의 모양을 쓰고 나머지 문단을 지운다. 표·그림이 든 칸은 find로 고친다.
- **굵게**, {{2/3}} 같은 make_hwpx.py 표기는 쓰지 않는다 (글자 그대로 들어감).
- 못 찾은 자리가 하나라도 있으면 파일을 만들지 않는다.
- hwp 파일은 채울 수 없다. 한글에서 hwpx로 저장한 파일을 쓴다.
- 미리 보기 그림(Preview/PrvImage.png)은 양식의 옛 그림이 남지 않도록 빈 그림으로 바꾼다. 한글에서 저장하면 새로 만들어진다.
- 양식에 메모가 있으면 채운 뒤에도 그대로 남으므로, 개수를 알리고 한글에서 확인하라고 안내한다.
"""

from __future__ import annotations

import json
import math
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from fill_hwpx_parse import BODY, MEMO, OBJECT, SAME_AS_SPACE, Cell, Char, Paragraph, SectionReader, Table
from make_hwpx_check import MIMETYPE, validate_package
from make_hwpx_save import BLANK_PNG, PREVIEW_IMAGE, file_error_message, hwpx_check, save_atomically, write_zip
from make_hwpx_text import _clean, _xml_text
from make_hwpx_zip import PackageError, read_package, refuse_dtd

MAX_ENTRY_BYTES = 64 * 1024 * 1024      # 이보다 큰 항목은 읽지 않는다 (압축 폭탄 방지)
MAX_TOTAL_BYTES = 512 * 1024 * 1024     # 모든 항목을 푼 크기의 합
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0"     # hwp(바이너리) 파일의 시작
PREVIEW_ENTRY = "Preview/PrvText.txt"
XML_SUFFIXES = (".xml", ".hpf", ".rdf")    # DTD를 거부할 XML 항목 (그림 같은 이진 항목은 보지 않는다)
PREVIEW_LIMIT = 1024
PLACES_SHOWN = 10
MEMO_FIELD = re.compile(r'<hp:fieldBegin\b[^>]*\btype="MEMO"')
SECTION_PREFIX, SECTION_SUFFIX = "Contents/section", ".xml"
HWP_GUIDE = ("hwp 파일은 직접 채울 수 없습니다. 한글에서 양식을 열고 [파일 > 다른 이름으로 저장하기]에서 "
             "파일 형식을 hwpx로 골라 hwpx로 저장한 뒤, 그 파일을 주세요.")
FIND_KEYS = {"find", "replace", "all", "nth"}
CELL_KEYS = {"table", "row", "col", "text"}


class FillError(ValueError):
    """교사에게 그대로 보여 줄 수 있는 실패."""


@dataclass(frozen=True)
class Edit:
    """section 원문의 [start, end) 구간을 new로 바꾼다."""
    section: int
    start: int
    end: int
    new: str


@dataclass(frozen=True)
class Claim:
    """지시 하나가 차지하는 원문 구간. 두 지시가 겹치는지 볼 때 쓴다."""
    section: int
    start: int
    end: int
    label: str


@dataclass(frozen=True)
class Plan:
    edits: tuple[Edit, ...]
    claims: tuple[Claim, ...]


@dataclass(frozen=True)
class Form:
    infos: tuple[zipfile.ZipInfo, ...]
    entries: dict[str, bytes]
    section_names: tuple[str, ...]
    section_xml: tuple[str, ...]
    paragraphs: tuple[Paragraph, ...]
    tables: tuple[Table, ...]


# ---------------------------------------------------------------- 양식 읽기

def _section_order(name: str) -> int | None:
    if not (name.startswith(SECTION_PREFIX) and name.endswith(SECTION_SUFFIX)):
        return None
    number = name[len(SECTION_PREFIX):-len(SECTION_SUFFIX)]
    return int(number) if number.isdigit() else None


def _read_package(path: Path) -> tuple[tuple[zipfile.ZipInfo, ...], dict[str, bytes]]:
    try:
        with path.open("rb") as handle:
            signature = handle.read(len(OLE_SIGNATURE))
    except OSError as error:
        raise FillError(f"양식 파일을 열 수 없음: {error}") from error
    if signature == OLE_SIGNATURE:
        raise FillError(HWP_GUIDE)
    try:
        return read_package(path, MAX_ENTRY_BYTES, MAX_TOTAL_BYTES, "한글")
    except PackageError as error:
        raise FillError(str(error)) from error
    except zipfile.BadZipFile as error:
        raise FillError("hwpx 파일이 아님. 한글에서 hwpx로 저장한 파일을 주세요") from error


def _read_sections(names: list[str], entries: dict[str, bytes]) -> list[SectionReader]:
    readers = []
    for index, name in enumerate(names):
        try:
            refuse_dtd(entries[name], name)
            xml = entries[name].decode("utf-8")
            ElementTree.fromstring(xml)
            readers.append(SectionReader(xml, index).read())
        except PackageError as error:
            raise FillError(str(error)) from error
        except (UnicodeDecodeError, ElementTree.ParseError, ValueError) as error:
            raise FillError(f"양식의 {name}을 읽을 수 없음: {error}") from error
    return readers


def read_form(path: Path) -> Form:
    infos, entries = _read_package(Path(path))
    if entries.get("mimetype") != MIMETYPE:
        raise FillError("hwpx 파일이 아님. 한글에서 hwpx로 저장한 파일을 주세요")
    for name in entries:     # 본문 밖 XML(header.xml, content.hpf 등)도 DTD를 거부한다. 검사가 그 항목을 건너뛰기 때문
        if name.lower().endswith(XML_SUFFIXES):
            try:
                refuse_dtd(entries[name], name)
            except PackageError as error:
                raise FillError(str(error)) from error
    names = sorted((name for name in entries if _section_order(name) is not None), key=_section_order)
    if not names:
        raise FillError("양식에 본문(section)이 없음")
    readers = _read_sections(names, entries)
    tables = tuple(table for reader in readers for table in reader.tables)
    for number, table in enumerate(tables, start=1):
        table.number = number
    paragraphs = tuple(paragraph for reader in readers for paragraph in reader.paragraphs)
    outside_cells = (paragraph for paragraph in paragraphs if paragraph.cell is None)
    for number, paragraph in enumerate(outside_cells, start=1):
        paragraph.number = number
    return Form(infos, entries, tuple(names), tuple(reader.xml for reader in readers), paragraphs, tables)


# ---------------------------------------------------------------- 살펴보기

def _shown(text: str, empty: str) -> str:
    return text.replace(OBJECT, "[표·그림]").replace("\n", " ⏎ ") if text.strip() else empty


def paragraph_line(paragraph: Paragraph) -> str:
    label = "" if paragraph.kind == BODY else f" [{paragraph.kind}]"
    return f"문단 {paragraph.number}{label}: {_shown(paragraph.text, '(빈 줄)')}"


def _cell_name(cell: Cell) -> str:
    return f"표 {cell.table.number} 행 {cell.row + 1} 칸 {cell.col + 1}"


def cell_line(cell: Cell) -> str:
    merged = f" [합침 {cell.row_span}행 × {cell.col_span}칸]" if cell.row_span > 1 or cell.col_span > 1 else ""
    return f"  {_cell_name(cell)}{merged}: {_shown(cell.text, '(빈 칸)')}"


def memo_count(form: Form) -> int:
    return sum(len(MEMO_FIELD.findall(xml)) for xml in form.section_xml)


def memo_notice(count: int) -> str:
    """양식에 남은 메모 안내. 메모에는 지난 학년도 정보나 개인 의견이 있을 수 있다. 없으면 빈 글."""
    return f"메모 {count}개가 남아 있습니다. 한글에서 확인하세요\n" if count else ""


def inspect_form(path: Path) -> str:
    """문단과 표 칸의 번호 목록. 표 번호·행·칸은 지시 JSON에 그대로 쓴다."""
    form = read_form(Path(path))
    lines = []
    for section in range(len(form.section_names)):
        items = [(p.start, paragraph_line(p)) for p in form.paragraphs if p.section == section and p.cell is None]
        for table in (table for table in form.tables if table.section == section):
            items.append((table.start, f"표 {table.number} ({table.rows}행 × {table.cols}칸)"))
            items.extend((cell.start, cell_line(cell)) for cell in table.cells)
        lines.append(f"구역 {section + 1}")
        lines.extend(line for _, line in sorted(items, key=lambda item: item[0]))
    return "\n".join(lines) + "\n" + memo_notice(memo_count(form))


# ---------------------------------------------------------------- 지시 검사

def is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def is_text(value: object) -> bool:
    """글이나 숫자인가. NaN·무한대는 "nan", "inf"로 들어가므로 받지 않는다."""
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def _validate_find(fill: dict, where: str) -> None:
    extra = set(fill) - FIND_KEYS
    if extra:
        raise FillError(f"{where}: 모르는 항목 {', '.join(sorted(extra))}")
    if not isinstance(fill["find"], str) or not _normalized(fill["find"]) or OBJECT in fill["find"]:
        raise FillError(f"{where}: find는 비어 있지 않은 글이어야 함")
    if not is_text(fill.get("replace")):
        raise FillError(f"{where}: replace에 바꿀 글을 적어 주세요")
    if "all" in fill and "nth" in fill:
        raise FillError(f"{where}: all과 nth는 함께 쓸 수 없음")
    if not isinstance(fill.get("all", False), bool):
        raise FillError(f"{where}: all은 true 또는 false여야 함")
    if "nth" in fill and not is_count(fill["nth"]):
        raise FillError(f"{where}: nth는 1 이상의 정수여야 함")


def _validate_cell(fill: dict, where: str) -> None:
    extra = set(fill) - CELL_KEYS
    if extra:
        raise FillError(f"{where}: 모르는 항목 {', '.join(sorted(extra))}")
    for key in ("table", "row", "col"):
        if not is_count(fill.get(key)):
            raise FillError(f"{where}: {key}는 1 이상의 정수여야 함")
    if not is_text(fill.get("text")):
        raise FillError(f"{where}: text에 넣을 글을 적어 주세요")


def validate_spec(spec: object) -> list[dict]:
    fills = spec.get("fills") if isinstance(spec, dict) else None
    if not isinstance(fills, list) or not fills:
        raise FillError('지시에 "fills" 목록이 없음')
    for number, fill in enumerate(fills, start=1):
        where = f"{number}번 지시"
        if not isinstance(fill, dict):
            raise FillError(f"{where}: 항목은 {{...}} 꼴이어야 함")
        if "find" in fill:
            _validate_find(fill, where)
        elif "table" in fill:
            _validate_cell(fill, where)
        else:
            raise FillError(f"{where}: find 또는 table이 있어야 함")
    return fills


# ---------------------------------------------------------------- 고칠 자리 정하기

def _normalized(text: str) -> str:
    return _clean(text).translate(SAME_AS_SPACE)


def _new_xml(value: object) -> str:
    return _xml_text(str(value).replace("\r\n", "\n"))


def _print_width(text: str) -> float:
    return sum(1 if ord(letter) > 0x2E7F else 0.5 for letter in text)


def _layout_edit(form: Form, paragraph: Paragraph, old: str, new: object) -> list[Edit]:
    """글이 바뀌면 옛 줄 배치 정보가 맞지 않으므로 지운다. 한글이 열 때 다시 계산한다.

    한 줄 문단의 글이 넓어지지 않으면 그대로 둔다. 다시 계산하면 꽉 찬 칸의 글이 두 줄로 내려갈 수 있다.
    """
    if paragraph.line_layout is None:
        return []
    start, end = paragraph.line_layout
    one_line = form.section_xml[paragraph.section][start:end].count("<hp:lineseg ") == 1
    if one_line and _print_width(str(new)) <= _print_width(old):
        return []
    return [Edit(paragraph.section, start, end, "")]


def _replace_chars(paragraph: Paragraph, chars: list[Char], new: str) -> list[Edit]:
    """글자들을 지우고 첫 글자 자리에 새 글을 넣는다. 사이의 조판 부호와 글자 없는 표시는 남긴다."""
    spans: list[list[int]] = []
    for item in chars:
        if spans and spans[-1][1] == item.start:
            spans[-1][1] = item.end
        else:
            spans.append([item.start, item.end])
    return [Edit(paragraph.section, start, end, new if index == 0 else "")
            for index, (start, end) in enumerate(spans)]


def _insert_into_empty(paragraph: Paragraph, xml: str, new: str, where: str) -> Edit:
    """글자가 하나도 없는 문단에 글을 넣는다. 누름틀이 있으면 그 안에, 아니면 첫 글자 모양으로."""
    section = paragraph.section
    if paragraph.text_slot is not None:
        start, end, empty = paragraph.text_slot
        return Edit(section, start, end, f"<hp:t>{new}</hp:t>") if empty else Edit(section, end, end, new)
    wrapped = f"<hp:t>{new}</hp:t>"
    if paragraph.field_slot not in (None, -1):
        return Edit(section, paragraph.field_slot, paragraph.field_slot, wrapped)
    if paragraph.run_tag is None:
        raise FillError(f"{where}: 글자 모양 정보가 없는 문단이라 채울 수 없음")
    start, end, empty = paragraph.run_tag
    if empty:
        return Edit(section, start, end, f"{xml[start:end - 2].rstrip()}>{wrapped}</hp:run>")
    return Edit(section, paragraph.run_close, paragraph.run_close, wrapped)


def _matches(form: Form, target: str) -> list[tuple[Paragraph, int]]:
    found = []
    for paragraph in form.paragraphs:
        if paragraph.kind == MEMO:
            continue
        text = paragraph.text
        position = text.find(target)
        while position != -1:
            found.append((paragraph, position))
            position = text.find(target, position + len(target))
    return found


def _place(paragraph: Paragraph) -> str:
    return _cell_name(paragraph.cell) if paragraph.cell else f"문단 {paragraph.number}"


def _choose(found: list[tuple[Paragraph, int]], fill: dict, where: str) -> list[tuple[Paragraph, int]]:
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
        places = ", ".join(_place(paragraph) for paragraph, _ in found[:PLACES_SHOWN])
        more = " 등" if len(found) > PLACES_SHOWN else ""
        raise FillError(f'{label} {len(found)}곳에 있음({places}{more}). "all": true 또는 "nth": 번호로 정해 주세요')
    return found


def _plan_find(form: Form, fill: dict, where: str) -> Plan:
    target = _normalized(fill["find"])
    edits: list[Edit] = []
    claims: list[Claim] = []
    new = _new_xml(fill["replace"])
    for paragraph, position in _choose(_matches(form, target), fill, where):
        chars = paragraph.chars[position:position + len(target)]
        edits += _replace_chars(paragraph, chars, new) + _layout_edit(form, paragraph, target, fill["replace"])
        claims.append(Claim(paragraph.section, chars[0].start, chars[-1].end, where))
    return Plan(tuple(edits), tuple(claims))


def _find_cell(form: Form, fill: dict, where: str) -> Cell:
    number, row, col = fill["table"], fill["row"] - 1, fill["col"] - 1
    if number > len(form.tables):
        raise FillError(f"{where}: 표 {number} 없음 (표 {len(form.tables)}개)")
    table = form.tables[number - 1]
    if row >= table.rows:
        raise FillError(f"{where}: 표 {number}에 행 {row + 1} 없음 ({table.rows}행)")
    if col >= table.cols:
        raise FillError(f"{where}: 표 {number}에 칸 {col + 1} 없음 ({table.cols}칸)")
    for cell in table.cells:
        if (cell.row, cell.col) == (row, col):
            return cell
    for cell in table.cells:
        if cell.row <= row < cell.row + cell.row_span and cell.col <= col < cell.col + cell.col_span:
            raise FillError(f"{where}: 이 자리는 {_cell_name(cell)}에 합쳐져 있음. 그 칸 번호를 써 주세요")
    raise FillError(f"{where}: 표 {number} 행 {row + 1} 칸 {col + 1} 없음")


def _plan_cell(form: Form, fill: dict, where: str) -> Plan:
    cell = _find_cell(form, fill, where)
    first, *rest = cell.paragraphs
    if first.objects or any(p.objects or p.has_control for p in rest):
        raise FillError(f"{where}: {_cell_name(cell)}에는 표, 그림, 누름틀 같은 개체가 있어 통째로 바꿀 수 없음. "
                        "find로 글만 바꿔 주세요")
    new = _new_xml(fill["text"])
    xml = form.section_xml[first.section]
    if first.chars:
        edits = _replace_chars(first, first.chars, new)
    else:
        edits = [_insert_into_empty(first, xml, new, where)]
    kept = "" if rest else first.text
    edits += _layout_edit(form, first, kept, fill["text"]) + [Edit(p.section, p.start, p.end, "") for p in rest]
    return Plan(tuple(edits), (Claim(first.section, cell.start, cell.end, where),))


def _check_overlap(claims: list[Claim]) -> None:
    ordered = sorted(claims, key=lambda claim: (claim.section, claim.start, claim.end))
    for before, after in zip(ordered, ordered[1:]):
        if before.section == after.section and after.start < before.end:
            raise FillError(f"{before.label}와 {after.label}의 자리가 겹침. 한 자리는 한 번만 고쳐 주세요")


def plan_edits(form: Form, fills: list[dict]) -> tuple[list[Edit], int]:
    """모든 지시의 자리를 원본에서 정한다. 실패한 지시는 모아서 한 번에 알린다."""
    edits: list[Edit] = []
    claims: list[Claim] = []
    failures: list[str] = []
    for number, fill in enumerate(fills, start=1):
        planner = _plan_find if "find" in fill else _plan_cell
        try:
            plan = planner(form, fill, f"{number}번 지시")
        except FillError as error:
            failures.append(str(error))
            continue
        edits += plan.edits
        claims += plan.claims
    if failures:
        raise FillError("\n".join(failures))
    _check_overlap(claims)
    return list(dict.fromkeys(edits)), len(claims)    # 같은 문단의 줄 배치 지우기는 한 번만


# ---------------------------------------------------------------- 쓰기

def apply_edits(xml: str, edits: list[Edit]) -> str:
    pieces = []
    position = 0
    for edit in sorted(edits, key=lambda item: (item.start, item.end)):
        pieces += [xml[position:edit.start], edit.new]
        position = edit.end
    pieces.append(xml[position:])
    return "".join(pieces)


def _preview(sections: list[str]) -> bytes:
    """미리 보기 글을 채운 뒤의 글로 바꾼다. 양식에 있던 옛 글이 파일에 남지 않게."""
    lines = []
    for index, xml in enumerate(sections):
        paragraphs = SectionReader(xml, index).read().paragraphs
        lines += [p.text.replace(OBJECT, "") for p in paragraphs if p.kind != MEMO]
    return ("\r\n".join(line for line in lines if line.strip())[:PREVIEW_LIMIT] + "\r\n").encode("utf-8")


def changed_entries(form: Form, edits: list[Edit]) -> dict[str, bytes]:
    sections = [apply_edits(xml, [edit for edit in edits if edit.section == index])
                for index, xml in enumerate(form.section_xml)]
    entries = dict(form.entries)
    for name, xml in zip(form.section_names, sections):
        try:
            ElementTree.fromstring(xml)
        except ElementTree.ParseError as error:
            raise FillError(f"채운 결과의 {name}이 깨짐: {error}") from error
        entries[name] = xml.encode("utf-8")
    if PREVIEW_ENTRY in entries:
        entries[PREVIEW_ENTRY] = _preview(sections)
    if PREVIEW_IMAGE in entries:
        entries[PREVIEW_IMAGE] = BLANK_PNG
    return entries


def publish(source: Path, form: Form, entries: dict[str, bytes], target: Path) -> None:
    """같은 폴더의 임시 파일에 쓰고, 원본에 없던 검사 문제가 없을 때만 결과 파일로 옮긴다."""
    check = hwpx_check(FillError, "채운 파일 검사 실패:", validate_package(source), validate_package)
    save_atomically(target, lambda path: write_zip(path, form.infos, entries), check)


def fill_form(source: Path, spec: dict, target: Path) -> int:
    """양식을 채워 target에 새 파일을 만들고 고친 자리 수를 돌려준다. 실패하면 FillError."""
    source, target = Path(source), Path(target)
    if target.exists():
        if source.exists() and target.samefile(source):
            raise FillError("원본 양식을 덮어쓸 수 없음. 결과 파일 이름을 다르게 적어 주세요")
        raise FillError(f"이미 있는 파일이라 덮어쓰지 않음: {target.name}. 다른 이름을 적어 주세요")
    if not target.parent.is_dir():
        raise FillError(f"결과를 저장할 폴더가 없음: {target.parent}")
    fills = validate_spec(spec)
    form = read_form(source)
    edits, count = plan_edits(form, fills)
    publish(source, form, changed_entries(form, edits), target)
    return count


# ---------------------------------------------------------------- 명령줄

def _run_fill(source: str, spec_path: str, target: str) -> str:
    try:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise FillError(f"지시 파일을 읽을 수 없음: {error}") from error
    count = fill_form(Path(source), spec, Path(target))
    notice = memo_notice(memo_count(read_form(Path(source))))
    return f"완료: {target} ({count}곳 채움). 글이 늘어 쪽이 넘어가는지는 한글에서 확인해 주세요\n{notice}"


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
            sys.stdout.write("사용법: python fill_hwpx.py --inspect 양식.hwpx\n"
                             "        python fill_hwpx.py 양식.hwpx 지시.json 결과.hwpx\n")
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
