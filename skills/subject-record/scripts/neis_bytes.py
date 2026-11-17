"""NEIS 학생부 입력 글자 수·바이트 계산기.

NEIS 계산 방식(2026학년도 기재요령 최대 글자수 표): 한글 3Byte, 영문·숫자 1Byte, 엔터 1Byte.
공백·기본 기호는 UTF-8과 같이 1바이트로 센다 (원문에 명시는 없음).
한글·영문·숫자·기본 기호(ASCII) 밖의 글자(·, …, 둥근 따옴표, 이모지 등)도 UTF-8 길이로 세지만
NEIS 계산은 확인되지 않았으므로 결과에 그 글자들을 따로 알린다.
초등학교는 2026학년도부터 서술형 항목의 글자 수 제한이 없으므로 --limit 을 쓰지 않는다.
글자 수 한도(예: 500자)는 한글 기준이므로 바이트 한도는 한도 x 3 이다.

사용법:
    python neis_bytes.py --limit 500 기록.txt
    python neis_bytes.py --limit 500 --split < 여러명.txt   # '---' 줄로 학생 구분
    python neis_bytes.py --limit-bytes 900 기록.txt         # NEIS 화면의 바이트 한도를 그대로 쓸 때
"""

from __future__ import annotations

import argparse
import codecs
import re
import sys
import unicodedata

BYTES_PER_HANGUL = 3
ENTRY_SEPARATOR = re.compile(r"^\s*-{3,}\s*$", re.MULTILINE)
UTF16_BOMS = (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)     # 메모장 '유니코드'(UTF-16) 저장
# NEIS 바이트 수가 기재요령에 적힌 글자: 한글(자모·호환 자모·완성형 음절)과 ASCII(영문·숫자·공백·기본 기호·엔터)
HANGUL_RANGES = ((0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7A3))


def _normalize(text: str) -> str:
    """줄바꿈을 \\n 하나로 맞추고 한글을 완성형(NFC)으로 통일한다. 앞뒤 공백·빈 줄은 세지 않고 지운다."""
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", unified).strip()


def count_chars(text: str) -> int:
    """글자 수 (앞뒤 공백 제외, 줄바꿈 1글자, 한글은 완성형 기준)."""
    return len(_normalize(text))


def count_bytes(text: str) -> int:
    """NEIS 바이트 수: 한글 3, 영문·숫자·공백 1, 줄바꿈 1 (앞뒤 공백 제외)."""
    normalized = _normalize(text)
    return len(normalized.encode("utf-8"))


def _is_verified(ch: str) -> bool:
    code = ord(ch)
    return code < 0x80 or any(low <= code <= high for low, high in HANGUL_RANGES)


def unverified_chars(text: str) -> list[str]:
    """NEIS 바이트 수가 확인되지 않은 글자(한글·ASCII 밖) 목록. 처음 나온 순서대로 한 번씩.

    이 글자들도 count_bytes는 UTF-8 길이로 세지만, NEIS가 같은 값으로 세는지는 확인되지 않았다."""
    return list(dict.fromkeys(ch for ch in _normalize(text) if not _is_verified(ch)))


def check(text: str, limit_chars: int | None, limit_bytes: int | None = None) -> dict:
    """글자 수·바이트 수와, 한도가 있으면 바이트 한도(글자 한도x3 또는 limit_bytes) 대비 여유·통과 여부를 돌려준다.

    unverified: NEIS 바이트 수가 확인되지 않은 글자 목록 (있으면 NEIS 화면에서 다시 확인)."""
    used_bytes = count_bytes(text)
    unverified = unverified_chars(text)
    if limit_chars is None and limit_bytes is None:
        return {"chars": count_chars(text), "bytes": used_bytes,
                "limit_bytes": None, "remaining_bytes": None, "ok": None, "unverified": unverified}
    if limit_bytes is None:
        limit_bytes = limit_chars * BYTES_PER_HANGUL
    return {
        "chars": count_chars(text),
        "bytes": used_bytes,
        "limit_bytes": limit_bytes,
        "remaining_bytes": limit_bytes - used_bytes,
        "ok": used_bytes <= limit_bytes,
        "unverified": unverified,
    }


def split_entries(text: str) -> list[str]:
    """'---' 줄을 기준으로 여러 기록으로 나눈다 (앞뒤 공백을 지우고 빈 기록은 뺀다)."""
    return [entry.strip() for entry in ENTRY_SEPARATOR.split(text) if entry.strip()]


def decode_text(data: bytes) -> str:
    """UTF-16(BOM 있는 메모장 '유니코드'), UTF-8(BOM 포함), 안 되면 한글 윈도우 기본 인코딩(CP949)으로 읽는다."""
    if data.startswith(UTF16_BOMS):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp949")


def read_text(path: str) -> str:
    """파일을 읽어 글자로 돌려준다 (인코딩은 decode_text와 같이 판단)."""
    with open(path, "rb") as handle:
        return decode_text(handle.read())


def _shown(ch: str) -> str:
    """경고에 보일 글자. 보이지 않는 글자(줄 안 띄어쓰기 등)는 U+00A0처럼 번호로."""
    return ch if ch.isprintable() and not ch.isspace() else f"U+{ord(ch):04X}"


def _unverified_note(result: dict) -> str:
    chars = result.get("unverified") or []
    if not chars:
        return ""
    return (f"\n    ※ NEIS 바이트 수가 확인되지 않은 글자: {' '.join(_shown(ch) for ch in chars)}"
            " (UTF-8 기준으로 셈. NEIS 화면에서 다시 확인해 주세요)")


def _format(index: int, result: dict) -> str:
    line = f"[{index}] {result['chars']}자 / {result['bytes']}바이트"
    if result["ok"] is None:
        return line + _unverified_note(result)
    status = "통과" if result["ok"] else "초과"
    remaining = result["remaining_bytes"]
    hint = f"남은 여유 {remaining}바이트" if remaining >= 0 else f"{-remaining}바이트 줄여야 함"
    return f"{line} (한도 {result['limit_bytes']}바이트) → {status}, {hint}" + _unverified_note(result)


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"정수여야 합니다: {value!r}") from None
    if number <= 0:
        raise argparse.ArgumentTypeError(f"0보다 커야 합니다: {value}")
    return number


def main(argv: list[str] | None = None) -> int:
    """명령줄 진입점. 종료 코드: 0 통과, 1 한도 초과, 2 읽기 실패·기록 없음."""
    parser = argparse.ArgumentParser(description="NEIS 글자 수·바이트 계산")
    parser.add_argument("file", nargs="?", help="텍스트 파일 (없으면 표준입력)")
    limits = parser.add_mutually_exclusive_group()
    limits.add_argument("--limit", type=_positive_int, help="글자 수 한도 (예: 500)")
    limits.add_argument("--limit-bytes", type=_positive_int, help="바이트 한도 (예: 900). 학생마다 다르면 학생별로 실행")
    parser.add_argument("--split", action="store_true", help="'---' 줄로 여러 기록 구분")
    args = parser.parse_args(argv)

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    try:
        text = read_text(args.file) if args.file else decode_text(sys.stdin.buffer.read())
    except (OSError, UnicodeDecodeError) as error:
        sys.stdout.write(f"파일을 읽을 수 없음: {error}\n")
        return 2

    if args.split:
        entries = split_entries(text)
    else:
        entries = [text] if _normalize(text) else []
    if not entries:
        sys.stdout.write("확인할 기록이 없음\n")
        return 2
    results = [check(entry, args.limit, args.limit_bytes) for entry in entries]

    for index, result in enumerate(results, start=1):
        sys.stdout.write(_format(index, result) + "\n")
    return 1 if any(result["ok"] is False for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
