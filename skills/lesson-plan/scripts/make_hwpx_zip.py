"""hwpx·xlsx 같은 zip 양식을 안전하게 읽는다. 표준 라이브러리만 쓴다.

zip 머리말에 적힌 크기를 믿지 않는다. 항목을 조금씩 풀면서 실제로 풀린 크기를 세고, 상한을 넘으면
바로 멈춘다(압축 폭탄 방지). fill_hwpx.py, fill_xlsx.py, make_hwpx_check.py가 함께 쓴다.
(tools/build.py가 스크립트의 import를 따라가 이 모듈을 스킬에 함께 넣는다.)
"""

from __future__ import annotations

import zipfile
import zlib
from pathlib import Path

CHUNK_BYTES = 1024 * 1024
NAMES_SHOWN = 10


class PackageError(ValueError):
    """교사에게 그대로 보여 줄 수 있는 실패."""


def unsafe_name(name: str) -> bool:
    """압축 안의 경로가 위험한가: 절대 경로, 드라이브, 역슬래시, 상위 폴더(..), 빈 이름."""
    return (name.startswith("/") or "\\" in name or ":" in name.split("/")[0]
            or ".." in name.split("/") or not name)


def check_infos(infos: tuple[zipfile.ZipInfo, ...], max_entry: int, max_total: int, app: str) -> None:
    """항목 목록만 보고 거를 수 있는 것을 거른다. 크기는 머리말 값이라 읽을 때 다시 센다."""
    names = [info.filename for info in infos]
    bad = [name for name in names if unsafe_name(name)]
    if bad:
        raise PackageError(f"양식 안에 안전하지 않은 경로가 있음: {', '.join(bad[:NAMES_SHOWN])}")
    if len(set(names)) != len(names):
        raise PackageError(f"양식 안에 이름이 같은 항목이 겹쳐 있음. {app}에서 다시 저장한 파일을 주세요")
    oversized = [info.filename for info in infos if info.file_size > max_entry]
    if oversized or sum(info.file_size for info in infos) > max_total:
        raise PackageError(f"양식 안의 항목이 너무 큼: {', '.join(oversized[:NAMES_SHOWN]) or '전체 크기'}")
    if any(info.flag_bits & 1 for info in infos):
        raise PackageError(f"암호가 걸린 양식은 채울 수 없음. {app}에서 암호를 풀고 다시 저장해 주세요")


def read_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    """항목 하나를 limit 바이트까지만 푼다. 넘거나 손상되었으면 PackageError.

    암호가 걸린 항목은 zipfile이 RuntimeError를 낸다. 그것은 부른 쪽이 처리한다.
    """
    if info.file_size > limit:
        raise PackageError(f"항목이 너무 큼: {info.filename}")
    pieces: list[bytes] = []
    size = 0
    try:
        with archive.open(info) as stream:
            while chunk := stream.read(CHUNK_BYTES):
                size += len(chunk)
                if size > limit:
                    raise PackageError(f"항목이 너무 큼: {info.filename}")
                pieces.append(chunk)
    except (zipfile.BadZipFile, zlib.error, EOFError) as error:
        raise PackageError(f"파일이 손상되어 {info.filename}을 읽을 수 없음") from error
    return b"".join(pieces)


DTD_MARKS = ("<!DOCTYPE", "<!ENTITY")
# 한글·엑셀 XML은 UTF-8이지만 XML은 UTF-16·UTF-32로도 쓸 수 있다. 글자마다 0 바이트가 끼므로
# UTF-8 표식만 찾으면 놓친다. BOM이 있든 없든 걸리도록 인코딩별 바이트열을 모두 찾는다.
DTD_ENCODINGS = ("ascii", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")


def refuse_dtd(xml: bytes | str, name: str) -> None:
    """문서 형식 선언(DTD)이나 개체 정의가 든 XML은 거부한다. 한글·엑셀이 쓰는 XML에는 없고,
    개체(&e;)가 다른 글로 풀려 엉뚱한 자리를 바꾸거나 크기를 부풀릴 수 있다. UTF-16·UTF-32 XML도 본다."""
    if isinstance(xml, str):
        found = any(mark in xml for mark in DTD_MARKS)
    else:
        found = any(mark.encode(encoding) in xml for mark in DTD_MARKS for encoding in DTD_ENCODINGS)
    if found:
        raise PackageError(f"{name}에 문서 형식 선언(DTD, <!DOCTYPE·<!ENTITY)이 있어 읽지 않음. "
                           "한글·엑셀에서 다시 저장한 파일을 주세요")


def read_package(path: Path, max_entry: int, max_total: int,
                 app: str) -> tuple[tuple[zipfile.ZipInfo, ...], dict[str, bytes]]:
    """zip 양식의 항목 목록과 {이름: 내용}을 돌려준다.

    zip이 아니면 zipfile.BadZipFile을 그대로 올린다(무슨 파일인지 알리는 문장은 부른 쪽이 정한다).
    app은 암호를 풀 프로그램 이름(한글, 엑셀)이다.
    """
    with zipfile.ZipFile(path) as archive:
        infos = tuple(archive.infolist())
        check_infos(infos, max_entry, max_total, app)
        entries: dict[str, bytes] = {}
        total = 0
        for info in infos:
            data = read_entry(archive, info, min(max_entry, max_total - total))
            total += len(data)
            entries[info.filename] = data
    return infos, entries
