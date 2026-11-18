"""fill_exam 지시(JSON) 검사. 표준 라이브러리만 쓴다.

문항 지시가 틀 고르기와 복제로 넘어가기 전에 모양을 한꺼번에 검사해 모든 문제를 모아 알린다."""

from __future__ import annotations

import re

from fill_exam_parse import COMBO_TABLE, GRID_TABLE, PARAGRAPHS, SHORT_TABLE, WRITTEN
from fill_hwpx import FillError, is_count, is_text, validate_spec
from make_hwpx_text import _clean

PASSAGE = "passage"
CHOICE_KINDS = (SHORT_TABLE, COMBO_TABLE, PARAGRAPHS)
COMMON_KEYS = {"type", "stem", "points", "box", "bogi", "layout", "dialogue", "dialogue_layout", "picture", "table"}
DIALOGUE_LAYOUTS = ("row", "column")
SPEAKER_KEYS = {"who", "text", "figure"}
PICTURE_KEYS = {"file", "width_mm", "caption"}
MAX_SPEAKERS = 4
ITEM_KEYS = {SHORT_TABLE: COMMON_KEYS | {"choices", "answer"}, COMBO_TABLE: COMMON_KEYS | {"choices", "answer"},
             PARAGRAPHS: COMMON_KEYS | {"choices", "answer"}, GRID_TABLE: COMMON_KEYS | {"head", "rows", "answer"},
             WRITTEN: {"type", "stem", "points"}, PASSAGE: {"type", "count", "lead", "paragraphs"}}
SPEC_KEYS = {"fills", "items"}
PICTURE_GUIDE = ('그림은 "picture": {"file": "그림.png"}로 넣고(두 장은 목록), 대화 장면은 "dialogue", 칸 있는 표는 "table"로 넣어 주세요. '
                 "서답형(written)과 지문(passage)에는 넣을 수 없습니다")
TABLE_KEYS = {"head", "rows", "caption", "widths", "align"}
MAX_TABLE_COLS = 8
MAX_TABLE_ROWS = 30
LAYOUT = re.compile(r"\d+\s*[x×X]\s*\d+")


def _texts(value: object, where: str, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(is_text(item) for item in value):
        raise FillError(f"{where}: {label}는 글 목록이어야 함")
    return [_plain(item) for item in value]


def _plain(value: object) -> str:
    return _clean(str(value).replace("\r\n", "\n"))


def _check_answer(item: dict, count: int, where: str) -> None:
    answer = item.get("answer")
    if not is_count(answer) or answer > count:
        raise FillError(f"{where}: answer는 1부터 {count}까지의 번호여야 함")


def _check_common(item: dict, where: str) -> None:
    if not is_text(item.get("stem")) or not str(item.get("stem")).strip():
        raise FillError(f"{where}: stem에 문제 글을 적어 주세요")
    if "points" in item and (not is_text(item["points"]) or not re.fullmatch(r"\d+(\.\d+)?", str(item["points"]))):
        raise FillError(f"{where}: points는 3 또는 3.2 같은 수여야 함")
    if "box" in item and not (is_text(item["box"]) or isinstance(item["box"], list)):
        raise FillError(f"{where}: box는 글이나 글 목록이어야 함")
    if "box" in item and isinstance(item["box"], list):
        _texts(item["box"], where, "box")
    if "bogi" in item:
        _texts(item["bogi"], where, "bogi")
    if "dialogue" in item:
        _check_dialogue(item["dialogue"], where)
    if "dialogue_layout" in item and ("dialogue" not in item or item["dialogue_layout"] not in DIALOGUE_LAYOUTS):
        raise FillError(f'{where}: dialogue_layout은 dialogue와 함께 "row"(머리 위 말풍선)나 "column"(옆 말풍선)으로 적어 주세요')
    if "picture" in item:
        _check_pictures(item["picture"], where)
    if "table" in item:
        _check_table(item["table"], where)
    if "layout" in item and not (isinstance(item["layout"], str) and LAYOUT.fullmatch(item["layout"].strip())):
        raise FillError(f'{where}: layout은 선지 표의 행x칸이어야 함 (예: "5x1", "2x3", "1x5")')


def _check_dialogue(value: object, where: str) -> None:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SPEAKERS:
        raise FillError(f"{where}: dialogue는 1~{MAX_SPEAKERS}명의 목록이어야 함")
    for person in value:
        if not isinstance(person, dict) or set(person) - SPEAKER_KEYS:
            raise FillError(f'{where}: dialogue의 사람은 {{"who", "text", "figure"}} 꼴이어야 함')
        if not is_text(person.get("who")) or not str(person["who"]).strip():
            raise FillError(f"{where}: dialogue의 who에 갑, 교사처럼 이름을 적어 주세요")
        if not is_text(person.get("text")) or not str(person["text"]).strip():
            raise FillError(f"{where}: dialogue의 text에 말풍선 글을 적어 주세요")
        if "figure" in person and not (isinstance(person["figure"], str) and person["figure"].strip()):
            raise FillError(f"{where}: dialogue의 figure는 teacher_f 같은 인물 이름이나 그림 파일 경로여야 함")


def _check_pictures(value: object, where: str) -> None:
    """picture는 그림 하나나 한 줄에 나란히 놓을 그림 둘의 목록이다."""
    if not isinstance(value, list):
        _check_picture(value, where)
        return
    if not 1 <= len(value) <= 2:
        raise FillError(f"{where}: picture 목록은 그림 한두 장이어야 함 (한 줄에 나란히 놓는 것은 두 장까지)")
    for one in value:
        _check_picture(one, where)


def _check_table(value: object, where: str) -> None:
    guide = '{"head": ["구분", "값"], "rows": [["가", "1"]], "caption": "<표> 설명", "widths": [2, 1]} 꼴이어야 함'
    if not isinstance(value, dict) or set(value) - TABLE_KEYS or not {"head", "rows"} <= set(value):
        raise FillError(f"{where}: table은 {guide}")
    head = _texts(value["head"], where, "table의 head")
    rows = value["rows"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_TABLE_ROWS:
        raise FillError(f"{where}: table의 rows는 1~{MAX_TABLE_ROWS}개 행의 목록이어야 함")
    if not 1 <= len(head) <= MAX_TABLE_COLS:
        raise FillError(f"{where}: table은 1~{MAX_TABLE_COLS}칸까지 만들 수 있음")
    for row in rows:
        if len(_texts(row, where, "table의 rows의 행")) != len(head):
            raise FillError(f"{where}: table의 행마다 칸 수가 head와 같아야 함 ({len(head)}칸)")
    if "caption" in value and (not is_text(value["caption"]) or not str(value["caption"]).strip()):
        raise FillError(f"{where}: table의 caption은 글이어야 함")
    _check_table_layout(value, len(head), where)


def _check_table_layout(value: dict, count: int, where: str) -> None:
    widths = value.get("widths")
    if widths is not None and (not isinstance(widths, list) or len(widths) != count or not all(
            isinstance(w, (int, float)) and not isinstance(w, bool) and w > 0 for w in widths)):
        raise FillError(f"{where}: table의 widths는 칸 수({count}개)와 같은 양수 목록이어야 함 (예: [2, 1, 1])")
    align = value.get("align")
    if align is not None and (not isinstance(align, list) or len(align) != count
                              or any(a not in ("left", "center", "right") for a in align)):
        raise FillError(f'{where}: table의 align은 칸 수({count}개)와 같은 "left", "center", "right" 목록이어야 함')


def _check_picture(value: object, where: str) -> None:
    spec = {"file": value} if isinstance(value, str) else value
    if not isinstance(spec, dict) or set(spec) - PICTURE_KEYS or not isinstance(spec.get("file"), str):
        raise FillError(f'{where}: picture는 "그림.png"나 {{"file", "width_mm", "caption"}} 꼴이어야 함')
    width = spec.get("width_mm")
    if width is not None and (isinstance(width, bool) or not isinstance(width, (int, float)) or not 5 <= width <= 180):
        raise FillError(f"{where}: picture의 width_mm는 5~180 사이의 수여야 함")
    if "caption" in spec and not is_text(spec["caption"]):
        raise FillError(f"{where}: picture의 caption은 글이어야 함")


def _check_grid(item: dict, where: str) -> None:
    head = _texts(item.get("head"), where, "head")
    rows = item.get("rows")
    if not isinstance(rows, list) or not rows:
        raise FillError(f"{where}: rows에 선지 행을 적어 주세요")
    for row in rows:
        if len(_texts(row, where, "rows의 행")) != len(head):
            raise FillError(f"{where}: rows의 행마다 칸 수가 head와 같아야 함 ({len(head)}칸)")
    _check_answer(item, len(rows), where)


def _check_passage(item: dict, where: str) -> None:
    if not is_count(item.get("count")):
        raise FillError(f"{where}: count에 이 지문으로 푸는 문항 수를 적어 주세요")
    if not is_text(item.get("lead")):
        raise FillError(f"{where}: lead에 '다음 글을 읽고 물음에 답하시오.' 같은 글을 적어 주세요")
    parts = item.get("paragraphs")
    if not isinstance(parts, list) or not parts:
        raise FillError(f"{where}: paragraphs에 지문을 적어 주세요")
    for part in parts:
        text = part.get("text") if isinstance(part, dict) else part
        if not is_text(text) or (isinstance(part, dict) and set(part) - {"label", "text"}):
            raise FillError(f'{where}: paragraphs의 항목은 글이나 {{"label", "text"}} 꼴이어야 함')


def _check_item(item: object, where: str) -> None:
    if not isinstance(item, dict):
        raise FillError(f"{where}: 항목은 {{...}} 꼴이어야 함")
    kind = item.get("type")
    if kind not in ITEM_KEYS:
        raise FillError(f"{where}: type은 {', '.join(ITEM_KEYS)} 가운데 하나여야 함")
    if "image" in item or (kind in (WRITTEN, PASSAGE) and ("picture" in item or "dialogue" in item or "table" in item)):
        raise FillError(f"{where}: {PICTURE_GUIDE}")
    extra = set(item) - ITEM_KEYS[kind]
    if extra:
        raise FillError(f"{where}: 모르는 항목 {', '.join(sorted(extra))}")
    if kind == PASSAGE:
        _check_passage(item, where)
        return
    _check_common(item, where)
    if kind == GRID_TABLE:
        _check_grid(item, where)
    elif kind in CHOICE_KINDS:
        _check_answer(item, len(_texts(item.get("choices"), where, "choices")), where)


def _numbered(items: list[dict]) -> list[tuple[str, dict]]:
    """(문항 이름, 지시) 목록. 오류 문장에 쓸 이름이다."""
    named = []
    count = 0
    for index, item in enumerate(items, start=1):
        is_item = isinstance(item, dict) and item.get("type") != PASSAGE
        count += is_item
        named.append((f"문항 {count}" if is_item else f"{index}번째 지문", item))
    return named


def _validate(spec: object) -> tuple[list[dict], list[tuple[str, dict]]]:
    if not isinstance(spec, dict):
        raise FillError('지시는 {"items": [...]} 꼴이어야 함')
    extra = set(spec) - SPEC_KEYS
    if extra:
        raise FillError(f"모르는 항목: {', '.join(sorted(extra))}")
    items = spec.get("items")
    if not isinstance(items, list) or not any(isinstance(i, dict) and i.get("type") != PASSAGE for i in items):
        raise FillError('지시에 "items" 문항 목록이 없음')
    fills = validate_spec({"fills": spec["fills"]}) if spec.get("fills") else []
    named = _numbered(items)
    failures = []
    for where, item in named:
        try:
            _check_item(item, where)
        except FillError as error:
            failures.append(str(error))
    if failures:
        raise FillError("\n".join(failures))
    return fills, named
