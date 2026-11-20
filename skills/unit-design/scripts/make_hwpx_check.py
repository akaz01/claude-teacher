"""make_hwpx.py의 hwpx 구조 검사 (--check). 표준 라이브러리만 쓴다."""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from make_hwpx_zip import PackageError, read_entry, refuse_dtd

MIMETYPE = b"application/hwp+zip"
UNSET_ID_REF = "4294967295"             # 한글이 "지정 안 함"에 쓰는 값 (0xFFFFFFFF)
MAX_ENTRY_BYTES = 64 * 1024 * 1024      # 이보다 큰 항목은 읽지 않는다 (fill_hwpx.py가 채우는 상한과 같음)
HEADER, MANIFEST = "Contents/header.xml", "Contents/content.hpf"
SECTION_PREFIX, FIRST_SECTION = "Contents/section", "Contents/section0.xml"
SECTION_NAME = re.compile(r"Contents/section(\d+)\.xml")
LANG_ATTRS = {"hangul": "HANGUL", "latin": "LATIN", "hanja": "HANJA", "japanese": "JAPANESE",
              "other": "OTHER", "symbol": "SYMBOL", "user": "USER"}
NS = {"hh": "http://www.hancom.co.kr/hwpml/2011/head",
      "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}


OWN_FILE_MARK = b'"lastsaveby" content="text">teacher-kit<'     # 한글에서 다시 저장하면 사용자 이름으로 바뀐다


def refuse_foreign_target(path: Path) -> None:
    """결과 파일이 이미 있으면, 이 도구가 만들고 아무도 다시 저장하지 않은 파일만 바꿔 쓴다.
    교사 양식이나 한글에서 고친 파일은 FileExistsError로 멈춘다."""
    if not path.exists():
        return
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = read_entry(archive, archive.getinfo(MANIFEST), MAX_ENTRY_BYTES)
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError, PackageError):
        manifest = b""
    if OWN_FILE_MARK not in manifest:
        raise FileExistsError(f"이미 있는 파일이라 덮어쓰지 않음: {path.name}. 다른 이름을 적어 주세요")


def _check_header(header: ElementTree.Element) -> tuple[list[str], dict]:
    problems = []
    for container in ("borderFills", "charProperties", "paraProperties", "styles",
                      "tabProperties", "numberings"):
        element = header.find(f".//hh:{container}", NS)
        if element is not None and int(element.get("itemCnt", -1)) != len(list(element)):
            problems.append(f"header: {container} itemCnt가 실제 개수와 다름")
    font_counts = {}
    for group in header.findall(".//hh:fontface", NS):
        fonts = group.findall("hh:font", NS)
        font_counts[group.get("lang")] = len(fonts)
        if int(group.get("fontCnt", -1)) != len(fonts):
            problems.append(f"header: {group.get('lang')} fontCnt가 실제 글꼴 수와 다름")
    for font_ref in header.findall(".//hh:fontRef", NS):
        for attr, lang in LANG_ATTRS.items():
            if int(font_ref.get(attr, 0)) >= font_counts.get(lang, 0):
                problems.append(f"header: fontRef {attr}={font_ref.get(attr)} 글꼴 없음")
    ids = {tag: {el.get("id") for el in header.findall(f".//hh:{tag}", NS)}
           for tag in ("charPr", "paraPr", "borderFill", "style")}
    return problems, ids


def _check_refs(root: ElementTree.Element, ids: dict, where: str) -> list[str]:
    ref_targets = {"charPrIDRef": "charPr", "paraPrIDRef": "paraPr",
                   "styleIDRef": "style", "borderFillIDRef": "borderFill"}
    return [
        f"{where}: {attr}={element.get(attr)} 정의 없음"
        for element in root.iter() for attr, tag in ref_targets.items()
        if element.get(attr) not in (None, UNSET_ID_REF) and element.get(attr) not in ids[tag]
    ]


def _check_tables(section: ElementTree.Element, where: str) -> list[str]:
    problems = []
    for table in section.iter(f"{{{NS['hp']}}}tbl"):
        rows = table.findall("hp:tr", NS)
        if int(table.get("rowCnt")) != len(rows):
            problems.append(f"{where}: 표 {table.get('id')} rowCnt 불일치")
        width = int(table.find("hp:sz", NS).get("width"))
        for row in rows:
            cells = row.findall("hp:tc", NS)
            spans = sum(int(c.find("hp:cellSpan", NS).get("colSpan")) for c in cells)
            widths = sum(int(c.find("hp:cellSz", NS).get("width")) for c in cells)
            if spans == int(table.get("colCnt")) and widths != width:
                problems.append(f"{where}: 표 {table.get('id')} 칸 너비 합이 표 너비와 다름")
    return problems


def _section_names(archive: zipfile.ZipFile) -> list[str]:
    """Contents/section0.xml, section1.xml, ... 을 번호 순서로. section0이 없으면 KeyError."""
    archive.getinfo(FIRST_SECTION)
    numbered = {int(found.group(1)): found.group(0)
                for found in map(SECTION_NAME.fullmatch, archive.namelist()) if found}
    return [numbered[number] for number in sorted(numbered)]


def _read_parts(archive: zipfile.ZipFile) -> tuple[list[str], dict[str, ElementTree.Element]]:
    """검사할 XML을 읽는다. 너무 크거나 손상된 항목은 건너뛰고 문제로 적는다."""
    oversized, problems, parts = [], [], {}
    for name in [HEADER, MANIFEST, *_section_names(archive)]:
        info = archive.getinfo(name)
        if info.file_size > MAX_ENTRY_BYTES:
            oversized.append(name)
            continue
        try:   # 머리말 크기를 속인 항목은 read_entry가 실제로 풀린 크기로 막는다
            data = read_entry(archive, info, MAX_ENTRY_BYTES)
            refuse_dtd(data, name)
            parts[name] = ElementTree.fromstring(data)
        except PackageError as error:
            problems.append(f"파일 구조 오류: {error}")
    if oversized:
        problems.insert(0, f"항목이 너무 큼 ({MAX_ENTRY_BYTES // 1024 // 1024}MB 초과, 검사하지 못함): "
                           f"{', '.join(oversized)}")
    return problems, parts


def _open_package(path: Path) -> tuple[list[str], dict[str, ElementTree.Element]]:
    with zipfile.ZipFile(path) as archive:
        first = archive.infolist()[0]
        if first.filename != "mimetype" or first.compress_type != zipfile.ZIP_STORED:
            return ["mimetype이 첫 항목(무압축)이 아님"], {}
        try:
            mimetype = read_entry(archive, first, len(MIMETYPE))
        except PackageError:
            mimetype = b""
        if mimetype != MIMETYPE:
            return ["mimetype 내용이 다름"], {}
        return _read_parts(archive)


def _check_parts(parts: dict[str, ElementTree.Element]) -> list[str]:
    problems, ids = _check_header(parts[HEADER]) if HEADER in parts else ([], None)
    if ids is not None:
        problems += _check_refs(parts[HEADER], ids, "header")
    for name, section in parts.items():
        if not name.startswith(SECTION_PREFIX):
            continue
        where = name[len("Contents/"):-len(".xml")]
        problems += (_check_refs(section, ids, where) if ids is not None else []) + _check_tables(section, where)
    if FIRST_SECTION in parts:      # 문서 첫 용지 설정(secPr)은 첫 구역의 첫 문단에 있어야 한다
        first = parts[FIRST_SECTION].find("hp:p", NS)
        if first is None or first.find(".//hp:secPr", NS) is None:
            problems.append("section0: 첫 문단에 secPr 없음")
    return problems


def validate_package(path: Path) -> list[str]:
    """hwpx 구조를 검사해 문제 목록을 돌려준다. 빈 목록이면 통과.

    본문은 Contents/section*.xml을 모두 본다. 너무 큰 항목은 그 항목만 건너뛰고 나머지는 계속 검사한다.
    그림 같은 다른 항목은 읽지 않는다.
    """
    try:
        problems, parts = _open_package(path)
    except (OSError, zipfile.BadZipFile, KeyError, IndexError, ElementTree.ParseError) as error:
        return [f"파일 구조 오류: {error}"]
    except RuntimeError:  # zipfile은 암호 걸린 항목을 읽을 때 RuntimeError를 낸다
        return ["파일 구조 오류: 암호가 걸린 파일이라 검사할 수 없음 (한글에서 암호를 풀고 다시 저장해 주세요)"]
    try:
        return problems + _check_parts(parts)
    except (TypeError, AttributeError, ValueError) as error:
        return [*problems, f"구조 검사 중 예상하지 못한 형식: {error}"]


def main(argv: list[str] | None = None) -> int:
    """python make_hwpx_check.py 파일.hwpx: 통과면 0, 문제가 있으면 1, 사용법이 틀리면 2."""
    args = sys.argv[1:] if argv is None else argv
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    if len(args) != 1:
        sys.stdout.write("사용법: python make_hwpx_check.py 파일.hwpx\n")
        return 2
    problems = validate_package(Path(args[0]))
    sys.stdout.write("통과\n" if not problems else "\n".join(problems) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
