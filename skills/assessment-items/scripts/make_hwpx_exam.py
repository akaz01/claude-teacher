"""make_hwpx.py 문제지 블록: 문두(stem), 선지(choices), 자료 상자(box). 표준 라이브러리만 쓴다.

수능 문제지처럼 가독성 있게 줄을 맞춘다 (shared/exam-layout.md의 공통 법칙, 도구 적용 현황 12번).
- stem: 번호는 단 왼쪽 끝, 둘째 줄부터는 번호 자리에서 글자 하나(1em) 들어간 기준선에 맞춘다(내어쓰기). 양쪽 정렬.
  배점 앞은 보통 빈칸이다(묶음 빈칸이면 "것은? [5점]"이 통째로 내려가 윗줄 끝이 빈다. 교사 지적). 다음 문단과 함께(문단 보호 포함).
- choices: ①이 기준선에서 시작하는 테두리 없는 표. 한 줄 5칸(1x5), 3+2(2x3), 한 줄에 하나(5x1), auto는 가장 긴 선지로 고른다.
  두 줄이 된 선지의 둘째 줄은 "① " 뒤 글 시작에 맞춘다.
- box: 기준선에서 단 끝까지 이르는 1칸 실선 상자. 자료 상자와 <보기>가 같은 자리에 선다.
"""

from __future__ import annotations

import math
import re

from make_hwpx_equation import equation_preview
from make_hwpx_layout import _table_position
from make_hwpx_lint import _word_width
from make_hwpx_options import _bool_option, _choice, _int_option, _list_or_empty
from make_hwpx_text import _clean, as_text

NBSP = " "
EM = 1100                               # 문제지 본문 글자 11pt
STEM_HANG = EM                          # 기준선: 번호 자리에서 글자 하나
CHOICE_HANG = 1430                      # "① " 뒤 글 시작 (① 한 글자 + 빈칸)
CHOICE_PAD_RIGHT = 141                  # 선지 칸 오른쪽 여백 (옆 칸 글과 붙지 않게)
LINE_HEIGHT = 1760                      # 본문 줄 높이 (11pt, 160%)
ITEM_GAP = 1760                         # 문항 사이 빈 줄 하나
BOX_GAP_ABOVE, BOX_GAP_BELOW = 1100, 1400   # 문두 → 상자 1em, 상자 → 선지 1.3em쯤
BOX_PAD_X, BOX_PAD_TOP, BOX_PAD_BOTTOM = 825, 990, 660   # 상자 안 여백 (좌우 0.75em, 위 0.9em, 아래 0.6em)
BOX_ITEM_HANG = 1760                    # "ㄱ. " 뒤 글 시작 (1.6em)
LAYOUTS = ("auto", "1x5", "2x3", "5x1")
MAX_CHOICES = 10
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
POINTS_AT_END = re.compile(r"\[\s*\d+(?:\.\d+)?\s*점\s*\]\s*$")
BOX_MARKER = re.compile(r"[ㄱ-ㅎ]\.\s")

# 이름: (정렬, 줄 간격 %, 문단 위, 문단 아래, 왼쪽 여백, 다음 문단과 함께, 내어쓰기). make_hwpx.PARA_STYLES에 더해 쓴다
# 한글 내어쓰기는 왼쪽 여백 0 + 음수 intent: 첫 줄은 제자리, 둘째 줄부터 내어쓰기만큼 들어간다 (한글 화면에서 확인)
EXAM_PARA_STYLES = {
    "stem": ("JUSTIFY", 160, 0, 0, 0, True, STEM_HANG),
    "stem_free": ("JUSTIFY", 160, 0, 0, 0, False, STEM_HANG),
    "choice_cell": ("JUSTIFY", 160, 0, 0, 0, False, CHOICE_HANG),
    "choice_anchor": ("LEFT", 100, 0, ITEM_GAP, STEM_HANG, False),
    "choice_anchor_keep": ("LEFT", 100, 0, ITEM_GAP, STEM_HANG, True),
    "box_anchor": ("LEFT", 100, BOX_GAP_ABOVE, BOX_GAP_BELOW, STEM_HANG, False),
    "box_anchor_keep": ("LEFT", 100, BOX_GAP_ABOVE, BOX_GAP_BELOW, STEM_HANG, True),
    "box_text": ("JUSTIFY", 160, 0, 0, 0, False),
    "box_item": ("JUSTIFY", 160, 0, 0, 0, False, BOX_ITEM_HANG),
    "box_label": ("CENTER", 160, 0, 0, 0, False),
}


# ---------------------------------------------------------------- 글 다루기

def _plain(text: str) -> str:
    """폭 어림용 글: **굵게**·__밑줄__ 표기를 떼고 수식은 보이는 글로."""
    return equation_preview(re.sub(r"\*\*|__", "", text))


def _points_label(points) -> str:
    if isinstance(points, bool) or not isinstance(points, (int, float)) or not points > 0:
        raise ValueError(f"points는 0보다 큰 수여야 함 (받은 값: {points!r})")
    return f"[{int(points) if float(points).is_integer() else points}점]"


def keep_points(body: str, points: int | float | None = None) -> str:
    """끝의 배점("[5점]") 앞을 보통 빈칸 하나로 맞춘다. points가 있고 글에 배점이 없으면 덧붙인다.
    글에 배점이 있는데 points도 주면 두 값이 같아야 한다(다르면 ValueError, fill_exam.py와 같은 규칙).

    묶음 빈칸으로 붙이면 "것은? [5점]"이 통째로 다음 줄로 내려가 윗줄 끝이 비었다(교사 지적 2026-11-18)."""
    found = POINTS_AT_END.search(body)
    if found is None and points is not None:
        return f"{body.rstrip()} {_points_label(points)}"
    if found is not None and points is not None and re.sub(r"\s", "", found.group(0)) != _points_label(points):
        raise ValueError(f"문두의 배점 {found.group(0).strip()}과 points {points}가 다름. 하나로 맞춰 주세요")
    if found is None or "\n" in body[found.start():]:
        return body
    return f"{body[:found.start()].rstrip()} {body[found.start():].strip()}"


def _runs(writer, text: str, char: str = "body") -> str:
    return writer.runs(text, char).replace(NBSP, "<hp:nbSpace/>")


def _text_width(text: str) -> float:
    return _word_width(_plain(text), EM)


def _lines_needed(text: str, first: int, rest: int) -> int:
    """글이 몇 줄이 될지 어림한다. first는 첫 줄 가용 폭, rest는 둘째 줄부터의 폭."""
    width = _text_width(text)
    if width <= first:
        return 1
    return 1 + math.ceil((width - first) / max(rest, EM))


# ---------------------------------------------------------------- 표 조각

def _cell_xml(writer, content: str, col: int, row: int, size: tuple[int, int], border: int,
              margins: tuple[int, int, int, int]) -> str:
    left, right, top, bottom = margins
    return (
        f'<hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{border}">'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
        'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'{content}</hp:subList><hp:cellAddr colAddr="{col}" rowAddr="{row}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
        f'<hp:cellSz width="{size[0]}" height="{size[1]}"/>'
        f'<hp:cellMargin left="{left}" right="{right}" top="{top}" bottom="{bottom}"/></hp:tc>')


def _anchored_table(writer, rows_xml: list[str], widths: list[int], heights: list[int], border: int,
                    anchor: str) -> str:
    """표를 글자처럼 취급해 담은 문단. 문단 왼쪽 여백이 기준선이라 표 왼쪽 끝이 기준선에 선다."""
    table = (
        f'<hp:tbl id="{next(writer._table_ids)}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="{len(heights)}" colCnt="{len(widths)}" cellSpacing="0" borderFillIDRef="{border}" noAdjust="0">'
        f'<hp:sz width="{sum(widths)}" widthRelTo="ABSOLUTE" height="{sum(heights)}" heightRelTo="ABSOLUTE" '
        f'protect="0"/>{_table_position(True, None)}<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + "".join(f"<hp:tr>{row}</hp:tr>" for row in rows_xml) + "</hp:tbl>")
    run = f'<hp:run charPrIDRef="{writer.styles.char["body"]}">{table}<hp:t/></hp:run>'
    return writer.paragraph(run, anchor)


# ---------------------------------------------------------------- 문두

def stem_xml(writer, block: dict, body_width: int) -> str:
    """{"type": "stem", "number": 3, "text": "…", "points": 3.2, "keep_with_next": true}"""
    number = block.get("number")
    label = "" if number is None else f"**{_int_option(number, 'number', 1, 999)}.** "
    keep = _bool_option(block.get("keep_with_next"), "keep_with_next", True)
    text = keep_points(f"{label}{as_text(block.get('text'))}", block.get("points"))
    writer.preview.append(_clean(_plain(text).replace(NBSP, " ")))
    return writer.paragraph(_runs(writer, text), "stem" if keep else "stem_free")


# ---------------------------------------------------------------- 선지

def _with_marker(item, index: int) -> str:
    text = as_text(item).strip()
    if text[:1] in CIRCLED:
        return f"{text[0]}{NBSP}{text[1:].lstrip()}"
    return f"{CIRCLED[index]}{NBSP}{text}"


def _column_count(layout: str, widths: list[float], room: int) -> int:
    """배치 이름 → 한 줄 칸 수. auto는 가장 긴 선지가 들어가는 가장 좁은 배치(1x5 → 2x3 → 5x1)."""
    count = len(widths)
    options = {"1x5": count, "2x3": math.ceil(count / 2), "5x1": 1}
    if layout != "auto":
        return options[layout]
    longest = max(widths)
    for cols in dict.fromkeys(options.values()):
        if longest <= room // cols - CHOICE_HANG - CHOICE_PAD_RIGHT:
            return cols
    return 1


def _choice_widths(room: int, cols: int) -> list[int]:
    column = room // cols
    return [column] * (cols - 1) + [room - column * (cols - 1)]


def choices_xml(writer, block: dict, body_width: int) -> str:
    """{"type": "choices", "items": ["가", "나", …], "layout": "auto|1x5|2x3|5x1", "keep_with_next": false}"""
    items = _list_or_empty(block.get("items"), "items")
    if not 2 <= len(items) <= MAX_CHOICES:
        raise ValueError(f"choices의 items는 2~{MAX_CHOICES}개여야 함 (받은 개수: {len(items)})")
    layout = _choice(block.get("layout"), "layout", LAYOUTS, "auto")
    keep = _bool_option(block.get("keep_with_next"), "keep_with_next", False)
    texts = [_with_marker(item, index) for index, item in enumerate(items)]
    room = body_width - STEM_HANG
    cols = _column_count(layout, [_text_width(text) for text in texts], room)
    widths = _choice_widths(room, cols)
    rows = [texts[start:start + cols] for start in range(0, len(texts), cols)]
    heights = [_row_height(row, widths[0]) for row in rows]
    _warn_overflow(writer, layout, cols, widths[0], texts)
    rows_xml = [_choice_row(writer, row, index, widths, heights[index]) for index, row in enumerate(rows)]
    writer.preview.extend(_clean("  ".join(_plain(text).replace(NBSP, " ") for text in row)) for row in rows)
    return _anchored_table(writer, rows_xml, widths, heights, writer.styles.no_border,
                           "choice_anchor_keep" if keep else "choice_anchor")


def _row_height(row: list[str], column: int) -> int:
    inner = column - CHOICE_HANG - CHOICE_PAD_RIGHT
    return LINE_HEIGHT * max(_lines_needed(text, inner + CHOICE_HANG, inner) for text in row)


def _warn_overflow(writer, layout: str, cols: int, column: int, texts: list[str]) -> None:
    """고른 배치의 칸보다 선지가 넓으면 한 선지가 두 줄이 된다. 막지 않고 알린다 (auto는 넘치면 넓은 배치로 간다)."""
    if cols == 1 or layout == "auto":
        return
    inner = column - CHOICE_HANG - CHOICE_PAD_RIGHT
    long = [text for text in texts if _text_width(text) > inner + CHOICE_HANG - CHOICE_PAD_RIGHT]
    if long:
        writer.warnings.append(f"선지 {len(long)}개가 칸보다 길어 두 줄이 됩니다. layout을 더 넓은 배치(2x3 또는 5x1)로 바꿔 주세요")


def _choice_row(writer, row: list[str], row_index: int, widths: list[int], height: int) -> str:
    cells = []
    for col, width in enumerate(widths):
        text = row[col] if col < len(row) else ""
        content = writer.paragraph(_runs(writer, text), "choice_cell", in_cell=True)
        cells.append(_cell_xml(writer, content, col, row_index, (width, height), writer.styles.no_border,
                               (0, CHOICE_PAD_RIGHT, 0, 0)))
    return "".join(cells)


# ---------------------------------------------------------------- 자료 상자

def box_xml(writer, block: dict, body_width: int) -> str:
    """{"type": "box", "label": "<보 기>", "paragraphs": ["…", "ㄱ. …"], "keep_with_next": true}"""
    paragraphs = [as_text(text) for text in _list_or_empty(block.get("paragraphs"), "paragraphs")]
    label = as_text(block.get("label"))
    if not paragraphs:
        raise ValueError("box에는 paragraphs(글 목록)가 필요함")
    keep = _bool_option(block.get("keep_with_next"), "keep_with_next", True)
    width = body_width - STEM_HANG
    inner = width - 2 * BOX_PAD_X
    content = "".join(
        [writer.paragraph(_runs(writer, label), "box_label", in_cell=True)] * bool(label)
        + [writer.paragraph(_runs(writer, text), "box_item" if BOX_MARKER.match(text) else "box_text", in_cell=True)
           for text in paragraphs])
    lines = bool(label) + sum(_lines_needed(text, inner, inner) for text in paragraphs)
    height = lines * LINE_HEIGHT + BOX_PAD_TOP + BOX_PAD_BOTTOM
    writer.preview.extend(_clean(_plain(text)) for text in [label, *paragraphs] if text)
    cell = _cell_xml(writer, content, 0, 0, (width, height), writer.styles.border,
                     (BOX_PAD_X, BOX_PAD_X, BOX_PAD_TOP, BOX_PAD_BOTTOM))
    return _anchored_table(writer, [cell], [width], [height], writer.styles.border,
                           "box_anchor_keep" if keep else "box_anchor")


# ---------------------------------------------------------------- 연결

def exam_handlers(writer, body_width) -> dict:
    """SectionWriter 블록 처리기. body_width는 지금 단 너비를 돌려주는 함수."""
    return {"stem": lambda block: stem_xml(writer, block, body_width()),
            "choices": lambda block: choices_xml(writer, block, body_width()),
            "box": lambda block: box_xml(writer, block, body_width())}
