"""교사가 올린 pptx와 그림 경로를 열기 전에 검사하고, 만든 pptx의 문서 속성을 정리한다.

pptx도 zip이다. hwpx와 같은 검사(위험한 경로·이름이 겹친 항목·암호 항목·실제 풀린 크기 상한·DTD 거부)를
make_hwpx_zip.py의 함수로 거친 뒤에야 python-pptx가 연다. 오류 문구는 모두 한국어다.
(tools/build.py가 스크립트의 import를 따라가 make_hwpx_zip.py를 스킬에 함께 넣는다.)
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

SCRIPTS = Path(__file__).resolve().parent
for folder in (SCRIPTS, SCRIPTS.parents[2] / "shared" / "scripts"):      # 스킬 묶음 안, 저장소 안
    if (folder / "make_hwpx_zip.py").exists():
        sys.path.insert(0, str(folder))
        break
from make_hwpx_zip import PackageError, check_infos, read_entry, refuse_dtd  # noqa: E402

MAX_ENTRY_BYTES = 64 * 1024 * 1024      # 이보다 큰 항목은 읽지 않는다 (압축 폭탄 방지)
MAX_TOTAL_BYTES = 512 * 1024 * 1024     # 모든 항목을 푼 크기의 합
MAX_IMAGE_BYTES = 30 * 1024 * 1024      # 사진 한 장의 파일 크기 상한
XML_SUFFIXES = (".xml", ".rels")        # DTD를 거부할 항목 (그림 같은 이진 항목은 보지 않는다)
APP_NAME = "파워포인트"
AUTHOR = "teacher-kit"                  # hwpx 생성기와 같은 작성자 이름


def check_pptx(path: str | Path, label: str = "양식") -> None:
    """pptx를 python-pptx로 열기 전에 검사한다. 파일이 없으면 열 때 나는 오류에 맡기고 그냥 지나간다.

    label은 오류 문구의 이름(양식, 템플릿). 문제가 있으면 한국어 ValueError.
    """
    path = Path(path)
    if not path.is_file():
        return
    head = f"{label}을 열 수 없음: {path}"
    try:
        with zipfile.ZipFile(path) as archive:
            infos = tuple(archive.infolist())
            check_infos(infos, MAX_ENTRY_BYTES, MAX_TOTAL_BYTES, APP_NAME)
            _read_all(archive, infos, head)
    except PackageError as error:
        raise ValueError(f"{head} ({error})") from error
    except zipfile.BadZipFile as error:
        raise ValueError(f"{head} (.pptx 파일이 아니거나 손상됨. 암호가 걸린 파일이면 {APP_NAME}에서 암호를 풀고 "
                         "다시 저장해 주세요)") from error


def _read_all(archive: zipfile.ZipFile, infos: tuple[zipfile.ZipInfo, ...], head: str) -> None:
    """모든 항목을 실제로 풀어 크기를 세고 XML의 DTD를 찾는다. 내용은 남기지 않는다."""
    total = 0
    for info in infos:
        try:
            data = read_entry(archive, info, min(MAX_ENTRY_BYTES, MAX_TOTAL_BYTES - total))
        except RuntimeError as error:       # 암호가 걸린 항목
            raise PackageError(f"암호가 걸린 파일은 열 수 없음. {APP_NAME}에서 암호를 풀고 다시 저장해 주세요") from error
        total += len(data)
        if info.filename.lower().endswith(XML_SUFFIXES):
            refuse_dtd(data, info.filename)


def check_inside_folder(raw: str, base: Path, label: str = "그림") -> None:
    """상대 경로가 ..로 기준 폴더 밖으로 나가면 거부한다. 절대 경로(claude.ai 업로드 폴더 등)는 막지 않는다."""
    if (PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).is_absolute()
            or raw.startswith(("/", "\\"))):
        return
    base = Path(base).resolve()
    if not (base / raw).resolve().is_relative_to(base):
        raise ValueError(f"{label} 경로가 입력 파일이 있는 폴더 밖을 가리킴: {raw} "
                         f"(..로 위 폴더에 나갈 수 없음. {label} 파일을 입력 파일이 있는 폴더 안에 두세요)")


def check_image_size(path: str | Path) -> None:
    """그림 파일이 상한보다 크면 거부한다. 없는 파일은 여기서 따지지 않는다(열 때 알린다)."""
    try:
        size = Path(path).stat().st_size
    except OSError:
        return
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"그림 파일이 너무 큼: {path} ({size // (1024 * 1024)}MB, 상한 {MAX_IMAGE_BYTES // (1024 * 1024)}MB). "
                         "크기를 줄여서 다시 주세요")


def stamp_properties(prs) -> None:
    """작성자와 마지막 수정자를 teacher-kit으로 맞춘다 (양식을 만든 교사의 이름이 결과에 남지 않게)."""
    prs.core_properties.author = AUTHOR
    prs.core_properties.last_modified_by = AUTHOR
