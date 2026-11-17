"""make_hwpx.py와 fill_hwpx.py가 함께 쓰는 글 정리와 문서 정보(Contents/content.hpf). 표준 라이브러리만 쓴다."""

from __future__ import annotations

import re
from datetime import datetime
from xml.sax.saxutils import escape

# 한글 글꼴(맑은 고딕 등)은 역슬래시(U+005C)를 원화 기호로 그리므로 전각 역슬래시로 바꾼다 (한글에서 확인)
BACKSLASH_FOR_HANGUL_FONTS = "\uff3c"


def _clean(text: str) -> str:
    """XML에 넣을 수 없는 제어 문자, 짝 없는 대리 문자, U+FFFE·U+FFFF를 지운다 (줄바꿈은 남김)."""
    return "".join(ch for ch in text.replace("\t", " ")
                   if (ch == "\n" or ord(ch) >= 0x20) and not 0xD800 <= ord(ch) <= 0xDFFF
                   and ch not in "\ufffe\uffff")


def _xml_text(text: str) -> str:
    cleaned = _clean(text).replace("\\", BACKSLASH_FOR_HANGUL_FONTS)
    return escape(cleaned).replace("\n", "<hp:lineBreak/>")


def as_text(value) -> str:
    """JSON에서 온 값을 글자로: None은 빈칸, 숫자는 그대로 글자로."""
    return "" if value is None else str(value)


WEEKDAYS = "월화수목금토일"


def korean_date(moment: datetime) -> str:
    """한글이 문서 정보 'date'에 쓰는 꼴: 2025년 9월 17일 수요일 오후 1:32:50 (컴퓨터의 현지 시각)."""
    noon = "오전" if moment.hour < 12 else "오후"
    hour = moment.hour % 12 or 12
    return (f"{moment.year}년 {moment.month}월 {moment.day}일 {WEEKDAYS[moment.weekday()]}요일 "
            f"{noon} {hour}:{moment:%M:%S}")


def update_metadata(content_hpf: str, title: str, moment: datetime) -> str:
    """제목(이미 정리한 글자), 만든·고친 날짜(UTC), 골격에 남은 날짜를 바꾼다. moment는 시간대가 있는 시각."""
    stamp = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hpf = content_hpf.replace("<opf:title/>", f"<opf:title>{escape(title)}</opf:title>")
    content_hpf = content_hpf.replace("synthetic-fixture-author", "teacher-kit")
    content_hpf = re.sub(r'(<opf:meta name="(?:CreatedDate|ModifiedDate)" content="text">)[^<]*', rf"\g<1>{stamp}",
                         content_hpf)
    local = korean_date(moment.astimezone())
    return re.sub(r'(<opf:meta name="date" content="text">)[^<]*', lambda found: found.group(1) + local, content_hpf)


# 하 다음은 거·너·더…허로 잇는다 (공문서 항목 기호). 그 뒤는 숫자
HANGUL_ORDER = "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허"


def _outline_marker(level: int, number: int) -> str:
    hangul = HANGUL_ORDER[number - 1] if number <= len(HANGUL_ORDER) else str(number)
    return [f"{number}.", f"{hangul}.", f"{number})", f"{hangul})", f"({number})", f"({hangul})"][level - 1]
