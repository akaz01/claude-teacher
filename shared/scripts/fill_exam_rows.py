"""선지 표의 행 높이를 글 줄 수에 맞춘다.

한글 2024는 hwpx를 열 때 선지 표의 칸 높이를 다시 계산하지 않았다(한글에서 확인: 두 줄이 된 선지의 둘째 줄이
다음 선지에 붙고, 칸 높이를 낮추면 선지끼리 겹친다). 그래서 도구가 선지마다 줄 수를 어림해 행 높이를 정한다.
(자료 상자처럼 칸이 하나인 표는 한글이 글에 맞춰 늘렸다 — fill_exam.py `_shrink_row`.)

줄 수 어림은 원안지 줄나눔(한글은 글자 단위, 영어는 낱말 단위)을 따른다. 줄 간격과 둘째 줄 내어쓰기는
칸 문단 모양에서 읽고, 읽지 못하면 기본 원안지 값(160%, 1300)을 쓴다.
"""
from __future__ import annotations

import html
import math
import re

from fill_exam_parse import _text_width

LINE_RATIO = 1.6                        # 기본 원안지 선지 문단 줄 간격 160% (문단 모양을 읽지 못할 때)
CHOICE_HANG = 1300                      # 기본 원안지 선지 둘째 줄 내어쓰기 ("① " 폭, 문단 모양을 읽지 못할 때)
SAFETY = 1.00                           # 폭 어림 여유. 한글 실측: 어림 0.5% 초과는 한 줄, 2.2% 초과는 두 줄
SPACE_EM = 0.4                          # 한글 선지 빈칸 폭 (글자 크기 대비). 한글 실측: "② 김약연 … 교육하였"까지 한 줄 → 0.27~0.41
SPACE_LATIN_EM = 0.55                   # 영어 선지 빈칸 폭. 한글 실측: "③ The Green Art Box cleans paint water with filters."가 두 줄
HANGUL = re.compile("[가-힣ㄱ-ㅎㅏ-ㅣ一-鿿㐀-䶿]")      # 이런 글자가 든 낱말은 글자 단위로 넘어간다
ROW = re.compile(r"<hp:tr>.*?</hp:tr>", re.S)
CELL = re.compile(r"<hp:tc\b.*?</hp:tc>", re.S)
CELL_SIZE = re.compile(r'(<hp:cellSz\b[^>]*\bheight=")(\d+)(")')
CELL_WIDTH = re.compile(r'<hp:cellSz\b[^>]*\bwidth="(\d+)"')
TABLE_HEIGHT = re.compile(r'(<hp:tbl\b.*?<hp:sz\b[^>]*\bheight=")(\d+)(")', re.S)
EQUATION_WIDTH = re.compile(r'<hp:equation\b.*?<hp:sz\b[^>]*\bwidth="(\d+)"', re.S)
PARA_REF = re.compile(r'<hp:p\b[^>]*\bparaPrIDRef="(\d+)"')
LINE_SPACING = re.compile(r'<hh:lineSpacing type="PERCENT" value="(\d+)"')
INTENT = re.compile(r'<hc:intent value="(-?\d+)"')


def _attribute(tag: str, name: str) -> int:
    found = re.search(rf'\b{name}="(-?\d+)"', tag)
    return int(found.group(1)) if found else 0


def _side_margins(cell: str, table_xml: str) -> int:
    """칸 안 왼쪽+오른쪽 여백. hasMargin="0"인 칸은 한글이 표의 안 여백(inMargin)을 쓴다."""
    head = re.match(r"<hp:tc\b[^>]*>", cell)
    own = head is not None and 'hasMargin="1"' in head.group(0)
    found = re.search(r"<hp:cellMargin\b[^>]*>", cell) if own else re.search(r"<hp:inMargin\b[^>]*>", table_xml)
    if found is None:
        found = re.search(r"<hp:cellMargin\b[^>]*>", cell)
    return _attribute(found.group(0), "left") + _attribute(found.group(0), "right") if found else 0


def _cell_lines(cell: str) -> tuple[list[str], int]:
    """칸 글을 강제 줄(줄바꿈 태그, 문단)마다 나눈 목록과 수식 폭(HWPUNIT)."""
    body = re.sub(r"<hp:equation\b.*?</hp:equation>", "", cell, flags=re.S)
    body = body.replace("<hp:nbSpace/>", " ").replace("<hp:fwSpace/>", " ").replace("<hp:lineBreak/>", "\n")
    lines: list[str] = []
    for paragraph in re.findall(r"<hp:p\b.*?</hp:p>", body, re.S) or [body]:
        parts = re.findall(r"<hp:t>(.*?)</hp:t>", paragraph, re.S)
        text = "".join(html.unescape(re.sub(r"<[^>]+>", "", part)) for part in parts)   # 형광펜 같은 태그는 뺀다
        lines += text.split("\n")
    equations = sum(int(width) for width in EQUATION_WIDTH.findall(cell))
    return [line.strip() for line in lines], equations


def _shape_metrics(cell: str, para_shapes: dict[str, str] | None, em: int) -> tuple[int, int]:
    """(줄 높이, 둘째 줄 내어쓰기). 칸 첫 문단의 문단 모양에서 읽는다."""
    shape = ""
    found = PARA_REF.search(cell)
    if found and para_shapes:
        shape = para_shapes.get(found.group(1), "")
    spacing = LINE_SPACING.search(shape)
    intent = INTENT.search(shape)
    pitch = round(em * (int(spacing.group(1)) / 100 if spacing else LINE_RATIO))
    hang = -int(intent.group(1)) if intent and int(intent.group(1)) < 0 else CHOICE_HANG
    return pitch, hang


def choice_lines(text: str, inner: int, hang: int, em: int, extra: int = 0, first_room: int | None = None) -> int:
    """한 줄로 이어진 글의 줄 수. 한글이 든 낱말은 글자 단위, 영어 낱말은 낱말 단위로 넘어간다(칸보다 긴 영어 낱말은 쪼갠다).
    extra는 수식처럼 글 밖에서 더해지는 폭, first_room은 첫 줄 폭(없으면 inner)."""
    inner = max(inner, em)                      # 아주 좁은 칸에서도 한 줄에 한 글자는 든다
    hang = min(hang, inner - em) if inner - hang < em else hang
    later = inner - hang
    room = max(first_room if first_room is not None else inner, em)
    used, lines = 0.0, 1
    latin = not HANGUL.search(text)
    space = em * (SPACE_LATIN_EM if latin else SPACE_EM) * SAFETY
    for word in text.split(" "):
        width = _text_width(word, em) * SAFETY
        gap = space if used else 0.0
        if used + gap + width <= room:
            used += gap + width
            continue
        if not HANGUL.search(word) and width <= later:      # 영어 낱말은 통째로 다음 줄로
            lines, room, used = lines + 1, later, width
            continue
        used += gap + width                     # 한글(과 줄보다 긴 영어 낱말)은 글자 단위로 이어서 채운다
        while used > room:
            used -= room
            lines, room = lines + 1, later
    if extra:
        lines += math.ceil(max(0.0, used + extra - room) / max(later, 1))
    return lines


def _cell_line_count(cell: str, inner: int, hang: int, em: int) -> int:
    texts, equations = _cell_lines(cell)
    if not any(texts) and not equations:
        return 0
    total = 0
    for index, text in enumerate(texts):        # 줄바꿈 뒤 줄은 내어쓰기 자리에서 시작한다
        first_room = None if index == 0 else inner - hang
        total += choice_lines(text, inner, hang, em, equations if index == 0 else 0, first_room)
    return total


def fit_choice_rows(table_xml: str, em: int, para_shapes: dict[str, str] | None = None) -> str:
    """선지가 든 행마다 줄 수만큼 높이를 늘리고 표 높이도 같이 늘린다. 칸 안에 표가 든 표는 그대로 둔다."""
    if table_xml.count("<hp:tbl") > 1:
        return table_xml
    added = 0
    for row in ROW.findall(table_xml):
        most, pitch = 0, round(em * LINE_RATIO)
        for cell in CELL.findall(row):
            sized = CELL_WIDTH.search(cell)
            if sized is None:                   # 칸 너비를 읽지 못하면 그 칸은 세지 않는다
                continue
            cell_pitch, hang = _shape_metrics(cell, para_shapes, em)
            lines = _cell_line_count(cell, int(sized.group(1)) - _side_margins(cell, table_xml), hang, em)
            if lines > most:
                most, pitch = lines, cell_pitch
        grow = (most - 1) * pitch if most > 1 else 0
        if grow:
            added += grow
            grown = CELL_SIZE.sub(lambda m: f"{m.group(1)}{int(m.group(2)) + grow}{m.group(3)}", row)
            table_xml = table_xml.replace(row, grown, 1)
    if added:
        table_xml = TABLE_HEIGHT.sub(lambda m: f"{m.group(1)}{int(m.group(2)) + added}{m.group(3)}", table_xml, count=1)
    return table_xml
