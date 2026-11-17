"""hwpx·xlsx 결과 파일을 안전하게 저장한다. 표준 라이브러리만 쓴다.

같은 폴더의 고유한 임시 파일에 쓰고, 검사를 통과한 뒤에만 결과 이름으로 바꾼다(원자적 교체).
검사에 실패하거나 도중에 멈추면 임시 파일을 지우므로 결과 이름에 깨진 파일이 남지 않는다.
make_hwpx.py, fill_hwpx.py, fill_xlsx.py와 기본 양식 생성기(make_lesson_form.py, make_rubric_form.py)가 함께 쓴다.
(tools/build.py가 스크립트의 import를 따라가 이 모듈을 스킬에 함께 넣는다.)
"""

from __future__ import annotations

import base64
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Iterable

from make_hwpx_check import refuse_foreign_target, validate_package

REFUSE_EXISTING = "refuse"     # 이미 있는 파일은 무엇이든 덮어쓰지 않는다
OWN_FILES_ONLY = "own"         # 이 도구가 만들고 아무도 다시 저장하지 않은 hwpx만 바꿔 쓴다 (make_hwpx.py)


PREVIEW_IMAGE = "Preview/PrvImage.png"
# 양식의 옛 미리 보기 그림(다른 학교·학생 정보가 보일 수 있음)을 대신하는 1x1 빈 그림. 한글에서 저장하면 새로 만들어진다
BLANK_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")


def current_umask() -> int:
    umask = os.umask(0)
    os.umask(umask)
    return umask


def write_zip(path: Path, infos: Iterable[zipfile.ZipInfo], entries: dict[str, bytes]) -> None:
    """양식의 항목 순서·압축 방식·날짜를 그대로 두고 내용만 entries로 바꿔 쓴다."""
    with zipfile.ZipFile(path, "w") as archive:
        for info in infos:
            copied = zipfile.ZipInfo(info.filename, info.date_time)
            copied.compress_type = info.compress_type
            copied.external_attr = info.external_attr
            archive.writestr(copied, entries[info.filename])


def _guard(target: Path, existing: str) -> None:
    if existing == OWN_FILES_ONLY:
        refuse_foreign_target(target)
    elif target.exists():
        raise FileExistsError(f"이미 있는 파일이라 덮어쓰지 않음: {target.name}. 다른 이름을 적어 주세요")


def save_atomically(target: Path, write: Callable[[Path], None],
                    check: Callable[[Path], None] | None = None, existing: str = REFUSE_EXISTING) -> None:
    """write(임시 경로)로 쓰고, check(임시 경로)가 예외 없이 끝나면 target으로 옮긴다.

    check는 문제가 있으면 예외를 낸다(부른 쪽의 오류 종류로). 이미 있는 target은 existing 규칙으로 막는다.
    검사하는 사이에 생긴 파일도 덮어쓰지 않도록 옮기기 직전에 한 번 더 본다.
    """
    target = Path(target)
    _guard(target, existing)
    handle, temp_name = tempfile.mkstemp(prefix=f"{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        write(temp_path)
        if check is not None:
            check(temp_path)
        _guard(target, existing)
        os.chmod(temp_path, 0o666 & ~current_umask())  # mkstemp의 0600 대신 보통 파일 권한 (윈도우는 영향 없음)
        if existing == REFUSE_EXISTING:
            _move_without_overwrite(temp_path, target)
        else:
            os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)


def _move_without_overwrite(temp_path: Path, target: Path) -> None:
    """대상이 이미 있으면 바꾸지 않고 FileExistsError. 확인과 옮기기 사이에 생긴 파일도 덮어쓰지 않는다."""
    try:
        if os.name == "nt":
            os.rename(temp_path, target)       # 윈도우의 rename은 대상이 있으면 실패한다
        else:
            os.link(temp_path, target)         # 대상이 있으면 실패한다. 임시 이름은 finally에서 지운다
    except FileExistsError as error:
        raise FileExistsError(f"이미 있는 파일이라 덮어쓰지 않음: {target.name}. 다른 이름을 적어 주세요") from error


def file_error_message(error: OSError) -> str:
    """파일을 읽거나 저장하지 못했을 때 명령줄에 낼 한 문장. 덮어쓰기 거부와 잠긴 파일을 나누어 알린다."""
    if isinstance(error, FileExistsError):
        return str(error)
    if isinstance(error, PermissionError):
        return (f"파일 오류: 다른 프로그램(한글·엑셀, 백신, 동기화 프로그램)이 파일을 쓰고 있어 열거나 저장하지 못함 "
                f"({error.filename or error}). 그 파일을 닫거나 잠시 뒤 다시 실행해 주세요")
    return f"파일 오류: {error}"


def hwpx_check(error: type[Exception], message: str, known: Iterable[str] = (),
               validate: Callable[[Path], list[str]] = validate_package) -> Callable[[Path], None]:
    """validate_package 검사. known(원본 양식에 이미 있던 문제)을 뺀 문제가 있으면 error(message + 문제 목록)."""
    known = tuple(known)

    def check(path: Path) -> None:
        problems = [problem for problem in validate(path) if problem not in known]
        if problems:
            raise error(message + "\n" + "\n".join(problems))

    return check
