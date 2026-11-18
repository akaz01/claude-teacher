"""make_hwpx 보조: 쪽 나눔 보정과 표기 점검.

- with_auto_keep: 표·답 칸 바로 앞 문단("3. 추진 일정" 같은 소제목)을 표와 같은 쪽에 붙인다.
- date_warnings: 2026-11-14처럼 쓴 날짜를 찾아 공문서 표기(2026. 11. 14.)로 고치라고 알리고,
  공문서 표기 날짜의 요일이 틀렸거나 날짜가 없거나 주말이면 확인하라고 알린다.
"""

import re
from datetime import date

KEEP_TARGETS = ("table", "answer_box")
ISO_DATE = re.compile(r"(?<![\d-])(?:19|20)\d{2}-(?:1[0-2]|0?[1-9])(?:-(?:3[01]|[12]\d|0?[1-9]))?(?![\d-])")
OFFICIAL_DATE = re.compile(
    r"(?<![\w.])((?:19|20)\d{2})\. ?(1[0-2]|0?[1-9])\. ?(3[01]|[12]\d|0?[1-9])\.(?: ?\(([월화수목금토일])\))?")
WEEKDAYS = "월화수목금토일"
WEEKEND = {5, 6}
MAX_EXAMPLES = 3


def with_auto_keep(blocks: list) -> list:
    """표·답 칸 바로 앞 paragraph에 keep_with_next를 켠 새 목록을 돌려준다. 명시한 값은 그대로 둔다."""
    result = []
    for index, block in enumerate(blocks):
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        if (isinstance(block, dict) and block.get("type") == "paragraph" and "keep_with_next" not in block
                and isinstance(following, dict) and following.get("type") in KEEP_TARGETS):
            block = {**block, "keep_with_next": True}
        result.append(block)
    return result


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    return []


def _iso_warning(texts: list[str]) -> list[str]:
    found = [match for text in texts for match in ISO_DATE.findall(text)]
    if not found:
        return []
    examples = ", ".join(list(dict.fromkeys(found))[:MAX_EXAMPLES])
    return [f"주의: 날짜 {len(found)}곳이 공문서 표기가 아님 ({examples}) "
            f"→ 2026. 11. 14.(토), 2026. 10. 처럼 고쳐 주세요"]


def _official_warnings(texts: list[str]) -> list[str]:
    impossible, wrong_weekday, weekend = [], [], []
    for text in texts:
        for match in OFFICIAL_DATE.finditer(text):
            year, month, day, written = match.groups()
            try:
                actual = date(int(year), int(month), int(day)).weekday()
            except ValueError:
                impossible.append(match.group(0))
                continue
            if written and written != WEEKDAYS[actual]:
                wrong_weekday.append(f"{match.group(0)} → ({WEEKDAYS[actual]})")
            elif actual in WEEKEND:
                weekend.append(match.group(0))
    warnings = []
    if impossible:
        warnings.append(f"주의: 없는 날짜 {', '.join(dict.fromkeys(impossible))} → 날짜를 확인해 주세요")
    if wrong_weekday:
        warnings.append(f"주의: 요일이 틀림 {', '.join(dict.fromkeys(wrong_weekday))}")
    if weekend:
        examples = ", ".join(list(dict.fromkeys(weekend))[:MAX_EXAMPLES])
        warnings.append(f"확인: 주말 날짜 {len(weekend)}곳 ({examples}) → 행사·마감 날짜가 맞는지 교사에게 확인하세요")
    return warnings


def date_warnings(spec: dict) -> list[str]:
    """날짜 표기 경고 목록을 돌려준다. 문제가 없으면 빈 목록."""
    texts = _strings(spec)
    return _iso_warning(texts) + _official_warnings(texts)


# ---------------------------------------------------------------- 표 칸보다 넓은 낱말

CELL_EM = 1000                          # 표 칸 글자 10pt
NARROW = set(" .,:;'\"()[]·-/|!?")


def _word_width(word: str, em: int = CELL_EM) -> float:
    """낱말 폭 어림 (HWPUNIT). 한글·한자·원문자 1em, 영문·숫자 0.5em, 문장 부호·괄호 0.35em (한글 2024 화면과 맞춤)."""
    return sum(em * (0.35 if char in NARROW else 1.0 if ord(char) > 0x2E7F else 0.5) for char in word)


def wide_words(text: str, inner_width: int, em: int = CELL_EM) -> list[str]:
    """칸 안쪽 너비보다 넓어 한글이 낱말 중간에서 줄을 바꿀 낱말들. 수식({{ }})과 표기(**, __, ~~)는 뺀다."""
    plain = re.sub(r"\{\{.*?\}\}", " ", text)
    plain = re.sub(r"\*\*|__|~~", "", plain)
    return [word for word in plain.split() if _word_width(word, em) > inner_width]
