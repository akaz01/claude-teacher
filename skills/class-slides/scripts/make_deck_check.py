"""make_deck.py와 make_pptx.py의 입력 검사: JSON 읽기, 인자 읽기, 장 형식 검사. 오류 문구는 모두 한국어다."""

from __future__ import annotations

import json
import sys
from pathlib import Path

STUDENT_FLAG = "--student"
OUTPUT_SUFFIX = ".pptx"
ACTIVITY_FACTS = (("시간", "time"), ("모둠", "group"), ("역할", "roles"), ("준비물", "materials"), ("산출물", "output"))
SHOWN_CHARS = 30
TEXT_FIELDS = ("title", "tag", "subtitle", "caption", "key", "notes", "reveal_notes", "question", "explain",
               "output", "time", "group", "roles", "materials", "unit", "meta")
LIST_FIELDS = {
    "goals": ("items",), "summary": ("items",), "outline": ("items",), "content": ("items",),
    "keywords": ("words",), "flow": ("steps",), "cards": ("cards",), "table": ("header", "rows"),
    "figure": ("callouts",), "check": ("choices", "reasons"), "quiz": ("choices", "reasons"),
    "task": ("steps",), "activity": ("steps",),
}
LIST_HINT = '글자 하나가 아니라 ["가", "나"]처럼 대괄호로 묶은 목록으로 쓰세요'


def use_utf8_output() -> None:
    """한국어 문구가 깨지지 않게 표준 출력을 UTF-8로 바꾼다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass  # 이미 바뀌었거나 바꿀 수 없는 출력 스트림


def split_student_flag(args: list[str]) -> tuple[list[str], bool] | None:
    """(경로 목록, 학생용 여부)를 돌려준다. 모르는 선택(--로 시작)이 있으면 None."""
    paths = [arg for arg in args if arg != STUDENT_FLAG]
    if any(arg.startswith("--") for arg in paths):
        return None
    return paths, STUDENT_FLAG in args


def describe_os_error(error: OSError) -> str:
    """운영체제의 영어 오류 문구 대신 한국어로 알린다."""
    where = f": {error.filename}" if getattr(error, "filename", None) else ""
    return f"파일을 읽거나 쓸 수 없음{where} (경로와 폴더가 있는지, 다른 프로그램이 열고 있지 않은지 확인하세요)"


def read_input_json(path) -> object:
    """입력 JSON을 읽는다. 문법이 틀리면 몇 번째 줄 몇 번째 글자 근처인지 한국어로 알린다."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise ValueError(f"입력 파일을 찾을 수 없음: {path}") from error
    except UnicodeDecodeError as error:
        raise ValueError("입력 파일을 UTF-8 글자로 읽을 수 없음 (UTF-8로 저장해 주세요)") from error
    except OSError as error:
        raise ValueError(describe_os_error(error)) from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON 문법 오류: {error.lineno}번째 줄 {error.colno}번째 글자 근처") from error


def check_output_path(input_path: Path, output_path: Path) -> None:
    if output_path.suffix.lower() != OUTPUT_SUFFIX:
        raise ValueError(f"출력 파일 이름은 {OUTPUT_SUFFIX}로 끝나야 함 (받은 값: {output_path.name})")
    if output_path.resolve() == input_path.resolve():
        raise ValueError("출력 파일이 입력 JSON 파일과 같을 수 없음 (원본이 덮어써집니다)")


def _shown(value) -> str:
    text = repr(value)
    return text if len(text) <= SHOWN_CHARS else text[:SHOWN_CHARS] + "…"


def _all_text(where: str, field: str, entries: list) -> None:
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, str):
            raise ValueError(f"{where}: {field}의 {index}번째 항목은 글자여야 함 (받은 값: {_shown(entry)})")


def _entries(where: str, field: str, value, keys: tuple[str, ...]) -> None:
    """목록의 항목마다 {키: 글자} 형식을 요구한다."""
    for index, entry in enumerate(value, 1):
        if not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) for key in keys):
            shape = ", ".join(f'"{key}": ...' for key in keys)
            raise ValueError(f"{where}: {field}의 {index}번째 항목은 {{{shape}}} 형식이어야 함 (받은 값: {_shown(entry)})")


def _text_items(where: str, items: list, field: str = "items") -> None:
    for index, item in enumerate(items, 1):
        if isinstance(item, str):
            continue
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError(f'{where}: {field}의 {index}번째 항목은 글자 또는 {{"text": ...}} 형식이어야 함 (받은 값: {_shown(item)})')
        sub = item.get("sub")
        if sub is not None and not (isinstance(sub, list) and all(isinstance(line, str) for line in sub)):
            raise ValueError(f"{where}: {field}의 {index}번째 항목의 sub는 글자 목록이어야 함")


def _lines(where: str, field: str, value) -> None:
    if value is not None and not isinstance(value, (str, list)):
        raise ValueError(f"{where}: {field}는 글자 또는 글자 목록이어야 함 (받은 값: {_shown(value)})")
    if isinstance(value, list):
        _all_text(where, field, value)


def _check_compare(where: str, spec: dict) -> None:
    for side in ("left", "right"):
        value = spec.get(side)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(f'{where}: {side}는 {{"head": ..., "items": [...]}} 형식이어야 함')
        if not isinstance(value.get("items"), list):
            raise ValueError(f"{where}: {side}의 items는 목록이어야 함 ({LIST_HINT})")
        _all_text(where, f"{side}의 items", value["items"])


def _check_table(where: str, spec: dict) -> None:
    header, rows = spec.get("header"), spec.get("rows") or []
    if header is None:
        return
    _all_text(where, "header", header)
    for number, row in enumerate(rows, 1):
        if not isinstance(row, list):
            raise ValueError(f"{where}: rows의 {number}번째 행은 목록이어야 함 (받은 값: {_shown(row)})")
        _all_text(where, f"rows의 {number}번째 행", row)
        if len(row) > len(header):
            raise ValueError(f"{where}: rows의 {number}번째 행은 칸이 {len(row)}개로 header({len(header)}개)보다 많음")


def _check_example(where: str, spec: dict) -> None:
    for side in ("worked", "problem"):
        value = spec.get(side)
        if value is None:
            continue
        if not isinstance(value, dict) or not isinstance(value.get("lines"), list):
            raise ValueError(f'{where}: {side}는 {{"head": ..., "lines": [...]}} 형식이어야 함')
        _all_text(where, f"{side}의 lines", value["lines"])


def _check_by_kind(where: str, kind: str, spec: dict) -> None:
    if kind in ("goals", "summary", "outline", "content"):
        _text_items(where, spec.get("items") or [])
    elif kind == "keywords":
        _entries(where, "words", spec.get("words") or [], ("word", "meaning"))
    elif kind == "flow":
        _entries(where, "steps", spec.get("steps") or [], ("head", "text"))
    elif kind == "cards":
        _entries(where, "cards", spec.get("cards") or [], ("head", "text"))
    elif kind == "compare":
        _check_compare(where, spec)
    elif kind == "table":
        _check_table(where, spec)
    elif kind == "figure":
        _text_items(where, spec.get("callouts") or [], "callouts")
    elif kind in ("check", "quiz"):
        _all_text(where, "choices", spec.get("choices") or [])
        _all_text(where, "reasons", spec.get("reasons") or [])
        if "truth" in spec and not isinstance(spec["truth"], bool):
            raise ValueError(f"{where}: truth는 true 또는 false여야 함 (받은 값: {_shown(spec['truth'])})")
    elif kind in ("task", "activity"):
        _all_text(where, "steps", spec.get("steps") or [])
    if kind in ("task", "example"):
        _lines(where, "answer", spec.get("answer"))
    if kind == "example":
        _check_example(where, spec)


def check_slide(where: str, kind: str, spec: dict) -> None:
    """장 하나의 입력 형식을 본다. 틀리면 몇 번째 장의 무엇이 어떻게 틀렸는지 한국어로 알린다."""
    for field in TEXT_FIELDS:
        if spec.get(field) is not None and not isinstance(spec[field], str):
            raise ValueError(f"{where}: {field}는 글자여야 함 (받은 값: {_shown(spec[field])})")
    for field in LIST_FIELDS.get(kind, ()):
        if spec.get(field) is not None and not isinstance(spec[field], list):
            raise ValueError(f"{where}: {field}는 목록이어야 함 ({LIST_HINT})")
    _check_by_kind(where, kind, spec)


def validate_deck(doc, kinds) -> None:
    """입력 전체의 형식을 본다 (최상위, 장 목록, 장마다의 항목)."""
    if not isinstance(doc, dict):
        raise ValueError("입력 JSON의 최상위는 {...} 객체여야 함")
    for key in ("subject", "unit", "slides"):
        if not doc.get(key):
            raise ValueError(f"'{key}' 값이 필요함")
    for key in ("subject", "unit"):
        if not isinstance(doc[key], str):
            raise ValueError(f"'{key}'는 글자여야 함 (받은 값: {_shown(doc[key])})")
    if not isinstance(doc["slides"], list):
        raise ValueError("slides는 장 목록([...])이어야 함")
    for number, spec in enumerate(doc["slides"], 1):
        if not isinstance(spec, dict):
            raise ValueError(f'{number}번째 장: {{"type": ...}} 형식이어야 함 (받은 값: {_shown(spec)})')
        kind = spec.get("type")
        if kind not in kinds:
            raise ValueError(f"{number}번째 장: type '{kind}'은 쓸 수 없음 ({', '.join(kinds)})")
        check_slide(f"{number}번째 장({kind})", kind, spec)
