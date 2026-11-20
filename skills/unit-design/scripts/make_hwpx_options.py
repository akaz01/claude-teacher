"""make_hwpx.py의 입력 값 검증 도우미. 표준 라이브러리만 쓴다."""

from __future__ import annotations

MAX_BLOCKS = 2000


def _int_option(value, name: str, minimum: int, maximum: int) -> int:
    """bool·실수·범위 밖 값을 거부하고 정수만 돌려준다."""
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name}는 {minimum}~{maximum} 사이의 정수여야 함 (받은 값: {value!r})")
    return value


def _choice(value, name: str, allowed: tuple, default: str | None) -> str | None:
    """허용 목록에 있는 글자만 돌려준다. 값이 없으면(null·빈 글자) 기본값."""
    if value is None or value == "":
        return default
    if isinstance(value, str) and value.lower() in allowed:
        return value.lower()
    raise ValueError(f"{name}는 {', '.join(allowed)} 중 하나여야 함 (받은 값: {value!r})")


def _bool_option(value, name: str, default: bool) -> bool:
    """true·false만 받는다 ("false" 같은 글자나 0·1은 거부). 값이 없으면(null) 기본값."""
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{name}은 true 또는 false여야 함 (받은 값: {value!r})")
    return value


def _item_spec(item, number: int) -> dict:
    """outline·bullets·numbered 항목을 {"text": ...} 객체로. 글자·숫자만 주면 text로 본다.

    null 항목이나 text 없는 객체는 빈 번호·기호만 찍히므로 거부한다."""
    spec = item if isinstance(item, dict) else {"text": item}
    if spec.get("text") is None:
        raise ValueError(f"items의 {number}번째 항목에 글자가 없음 (받은 값: {item!r})")
    return spec


def _start_option(value, kind: str) -> int:
    """outline·numbered의 첫 번호 (표 등으로 끊긴 목록을 이어 쓸 때). 1 이상의 정수만."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{kind}의 start는 1 이상의 정수여야 합니다: {value!r}")
    return value


def _list_or_empty(value, name: str) -> list:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name}는 목록이어야 함 (받은 값: {value!r})")
    return list(value)


def _validate_spec(spec) -> None:
    """최상위 구조(객체·목록·글자 종류)를 확인한다. 세부 값은 블록을 쓸 때 확인한다."""
    if not isinstance(spec, dict):
        raise ValueError(f"입력은 객체여야 함: 맨 위가 {{ }} 형식이어야 합니다 (받은 형식: {type(spec).__name__})")
    blocks = spec.get("blocks")
    if blocks is not None and not isinstance(blocks, list):
        raise ValueError(f"blocks는 목록이어야 함 (받은 형식: {type(blocks).__name__})")
    if blocks and len(blocks) > MAX_BLOCKS:
        raise ValueError(f"블록은 최대 {MAX_BLOCKS}개까지 쓸 수 있음 (받은 개수: {len(blocks)})")
    for number, block in enumerate(blocks or [], 1):
        if not isinstance(block, dict):
            raise ValueError(f"{number}번째 블록은 객체여야 함 (받은 형식: {type(block).__name__})")
    for key in ("title", "doc_title"):
        title = spec.get(key)
        if title is not None and (isinstance(title, bool) or not isinstance(title, (str, int))):
            raise ValueError(f"{key}은 글자 또는 숫자여야 함 (받은 형식: {type(title).__name__})")
    notes = spec.get("notes")
    if notes is not None and not (isinstance(notes, list) and all(isinstance(note, str) for note in notes)):
        raise ValueError("notes는 글의 목록이어야 함 (만든 글에 덧붙일 경고)")
