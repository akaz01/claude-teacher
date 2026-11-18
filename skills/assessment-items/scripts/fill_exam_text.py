"""시험지 글의 문단 모양(표지 내어쓰기, 출처·각주 오른쪽 정렬, 줄글 첫 줄 들여쓰기)과 선지 배치 자동 고르기.

fill_exam.py가 부른다. 표준 라이브러리만 쓴다. 기준은 shared/exam-layout.md 2절·3절·5절.

자료 상자(box)와 공통 지문(passage) 본문의 문단마다 양식의 문단 모양을 복제해 쓴다 (같은 모양은 하나를 되풀이해 쓴다).
- 표지로 시작하는 문단: 둘째 줄부터 표지 뒤 글 시작에 맞게 내어쓰기. 표지는 ○ ◦ ● ※, "ㄱ.", ㉠ ⓐ,
  "(가)" "(A)", 화자 "교사:" "갑:" "학생 1:"(쌍점 앞 6자 이하 낱말). 표지 뒤에 한 칸이 있어야 한다.
  폭은 10pt 기준 ○ 1100, ㄱ. 1600, 갑: 1900, (가) 2100, 교사: 2900이고 글자 크기에 비례한다.
- 상자의 마지막 문단이 출처("- 지은이, 「제목」 -", "-『…』")이거나 "*낱말: 뜻" 각주 문단이면 오른쪽 정렬.
- 그 밖의 줄글 문단은 첫 줄을 글자 하나 들여쓴다. 소제목(<…>, [...]), 줄바꿈이 든 문단(시), 식만 있는 문단은 뺀다.
- 양식의 문단에 이미 들여쓰기나 내어쓰기가 있는 상자는 그대로 둔다 (학교 양식 우선). 공통 지문 본문만
  양식의 거꾸로 내어쓰기를 바로잡는다.

선지 배치(layout이 없을 때): 가장 긴 선지의 폭으로 1x5 → 2x3 → 5x1 가운데 들어가는 가장 좁은 것을 고른다.
"""

from __future__ import annotations

import re

from fill_exam_parse import CIRCLED, COMBO_TABLE, SHORT_TABLE, _text_width
from fill_exam_spec import _plain
from fill_hwpx import FillError

UNIT = 1000                              # 10pt 글자 하나 (HWPUNIT)
STEP = 100                               # 폭은 100 단위로 맞춰 같은 폭이 한 모양을 쓰게 한다
BULLET_WIDTH, JAMO_WIDTH, SIGN_WIDTH = 1100, 1600, 1300
NAME_GAP, PAREN_GAP = 900, 1100          # 이름 + 쌍점 + 빈칸, 괄호 + 빈칸이 이름·글자 폭에 더하는 폭
BULLET = re.compile(r"[○◦●※]\s")
JAMO = re.compile(r"[ㄱ-ㅎ]\.\s")
SIGN = re.compile(r"[㉠-㉭ⓐ-ⓩ]\s")
PAREN = re.compile(r"\(([가-힣A-Za-z0-9]{1,3})\)\s")
SPEAKER = re.compile(r"([가-힣A-Za-z]{1,6}(?:\s?\d{1,2})?)\s?[:：]\s")
DASH = "-―—–"
SOURCE = re.compile(rf"[{DASH}]\s*[『「｢].+[』」｣]\s*$|[{DASH}]\s*\S.*?\S\s*[{DASH}]$")
FOOTNOTE = re.compile(r"\*[^:：\n]{1,30}[:：]\s*\S")
HEADING = re.compile(r"<[^<>]+>$|\[[^\[\]]+\]$|〔[^〕]+〕$")
PARA_NUMBER = re.compile(r'\bparaPrIDRef="(\d+)"')
PARA_SHAPE_ID = re.compile(r'(<hh:paraPr\b[^>]*?\bid=")\d+')
ALIGN = re.compile(r'(<hh:align horizontal=")[A-Z_]+')
INTENT = re.compile(r'(<hc:intent value=")(-?\d+)')
LEFT = re.compile(r'(<hc:left value=")(-?\d+)')

AUTO_ORDER = ("1x5", "2x3", "5x1")       # 좁은 틀부터
AUTO_LIMITS = {5: (2.6, 5.9), 4: (3.9, 5.9), 3: (5.9, 5.9)}   # (한 줄 칸, 3+2 칸)에 든 가장 긴 선지 폭(글자 수)
DEFAULT_LIMITS = (2.6, 5.9)


# ---------------------------------------------------------------- 선지 배치

def auto_layout(item: dict) -> str | None:
    """layout이 없는 선택형 문항의 선지 배치("1x5", "2x3", "5x1"). 고를 수 없으면 None.

    <보기>가 있는 문항은 합답형이라 1x5를 쓰지 않는다 (원안지에서 합답형은 늘 2x3 이상)."""
    if item.get("type") not in (SHORT_TABLE, COMBO_TABLE) or not item.get("choices"):
        return None
    choices = [re.sub(rf"^\s*[{CIRCLED}]\s*", "", _plain(text)) for text in item["choices"]]
    longest = max(_text_width(re.sub(r"\{\{.*?\}\}", "수", text), UNIT) for text in choices) / UNIT
    one_row, two_rows = AUTO_LIMITS.get(len(choices), DEFAULT_LIMITS)
    if longest <= one_row and "bogi" not in item:
        return "1x5"
    return "2x3" if longest <= two_rows else "5x1"


def auto_fits(fits: list, auto: str, count: int, matches) -> list:
    """auto 배치부터 넓은 쪽으로 양식에 있는 첫 배치의 틀들. 하나도 없으면 fits 그대로."""
    for layout in AUTO_ORDER[AUTO_ORDER.index(auto):]:
        found = [frame for frame in fits if matches(frame, count, layout)]
        if found:
            return found
    return fits


# ---------------------------------------------------------------- 문단 종류

NBSP = chr(0xA0)                         # fill_exam.Writer.runs가 한글 묶음 빈칸(hp:nbSpace)으로 바꾼다


def glue_marker(text: str) -> str:
    """표지 뒤 빈칸을 묶음 빈칸으로. 양쪽 정렬에서 표지 뒤가 벌어져 둘째 줄과 어긋나는 것을 막는다(한글에서 확인)."""
    for pattern in (BULLET, JAMO, SIGN, PAREN, SPEAKER):
        found = pattern.match(text)
        if found and text[found.end() - 1] == " ":
            return f"{text[:found.end() - 1]}{NBSP}{text[found.end():]}"
    return text


def marker_width(text: str) -> int | None:
    """표지(뒤의 빈칸 포함)로 시작하는 문단이면 10pt 기준 표지 폭, 아니면 None."""
    if BULLET.match(text):
        return BULLET_WIDTH
    if JAMO.match(text):
        return JAMO_WIDTH
    if SIGN.match(text):
        return SIGN_WIDTH
    found = PAREN.match(text)
    if found:
        return round(_text_width(found.group(1), UNIT)) + PAREN_GAP
    found = SPEAKER.match(text)
    return round(_text_width(found.group(1), UNIT)) + NAME_GAP if found else None


def _is_prose(text: str) -> bool:
    """첫 줄을 들여쓸 줄글인가. 소제목, 줄바꿈이 든 시, 식, 아주 짧은 글은 아니다."""
    if "\n" in text or HEADING.match(text) or text.startswith("{{") or len(text) < 8:
        return False
    return not ("=" in text and not re.search("[가-힣]", text))


def _is_part_source(text: str) -> bool:
    """(가)·(나) 자료마다 바로 아래에 다는 출처 줄("- 『신한민보』, 1910. 7. 6. -"). 상자 중간에 있어도 오른쪽 정렬한다.
    잘못 잡지 않게 앞뒤 줄표와 책·글 이름 괄호가 함께 있을 때만 본다 (수능 한국사 꼴: "- 『조선 총독부 관보』 -")."""
    if not (re.match(rf"[{DASH}]\s*\S.*\S\s*[{DASH}]$", text) and re.search("[『「｢]", text)):
        return False
    inner = text.strip(f"{DASH} ")
    return not re.search(r"[다요까][.?!]?$", inner)     # "- 「가」 문서를 읽고 토론하였다 -"처럼 문장으로 끝나면 출처가 아니다


def classify(text: str, last: bool) -> tuple[str, int]:
    """("hang", 표지 폭) / ("right", 0) / ("indent", 0) / ("plain", 0). 폭은 10pt 기준."""
    text = text.strip()
    if FOOTNOTE.match(text) or (last and SOURCE.match(text)) or _is_part_source(text):
        return "right", 0
    width = marker_width(text)
    if width is not None:
        return "hang", width
    return ("indent", 0) if _is_prose(text) else ("plain", 0)


# ---------------------------------------------------------------- 문단 모양

def _margins(shape: str) -> tuple[int, int]:
    """(첫 줄 들여쓰기, 왼쪽 여백). 새 방식(HwpUnitChar) 값을 읽는다."""
    intent, left = INTENT.search(shape), LEFT.search(shape)
    return (int(intent.group(2)) if intent else 0, int(left.group(2)) if left else 0)


def _with_margins(shape: str, intent: int, left: int, align: str | None) -> str:
    """들여쓰기와 왼쪽 여백(과 정렬)을 바꾼다. 옛 방식(<hp:default>) 값은 두 배다."""
    head, sep, tail = shape.partition("<hp:default>")
    parts = []
    for part, factor in ((head, 1), (tail, 2)):
        part = INTENT.sub(lambda m: f"{m.group(1)}{intent * factor}", part)
        parts.append(LEFT.sub(lambda m: f"{m.group(1)}{left * factor}", part))
    shape = parts[0] + sep + parts[1]
    return ALIGN.sub(lambda m: f"{m.group(1)}{align}", shape) if align else shape


class TextShapes:
    """양식의 문단 모양에서 표지 내어쓰기·첫 줄 들여쓰기·오른쪽 정렬 모양을 복제해 준다."""

    def __init__(self, writer) -> None:
        self.writer = writer
        self.made: dict[tuple, str] = {}

    def _derive(self, source: str, intent: int, left: int, align: str | None) -> str:
        key = (source, intent, left, align)
        if key not in self.made:
            shape = self.writer.para_shapes.get(source)
            if shape is None:
                raise FillError("양식의 문단 모양을 읽지 못해 표지 내어쓰기·들여쓰기를 넣지 못함")
            new = str(next(self.writer.next_shape))
            made = _with_margins(PARA_SHAPE_ID.sub(rf"\g<1>{new}", shape, count=1), intent, left, align)
            self.writer.new_shapes.append(made)
            self.writer.para_shapes[new] = made
            self.made[key] = new
        return self.made[key]

    def shape_for(self, template, text: str, last: bool, em: int, keep_own: bool = True) -> str | None:
        """문단에 쓸 문단 모양 번호. 양식 모양 그대로면 None. keep_own이면 양식에 이미 들여·내어쓰기가 있는 문단은 둔다."""
        kind, width = classify(text, last)
        number = PARA_NUMBER.search(self.writer._open(template))
        source = number.group(1) if number else "0"
        intent, left = _margins(self.writer.para_shapes.get(source, ""))
        if kind == "right":
            return self._derive(source, 0, 0, "RIGHT")
        if kind == "plain" and not keep_own and intent < 0:
            return self._derive(source, 0, left, None)         # 지문 본문의 거꾸로 내어쓰기를 편다
        if kind == "plain" or (keep_own and intent != 0):
            return None
        if kind == "hang":
            size = round(width * em / UNIT / STEP) * STEP
            # 한글 내어쓰기: intent가 음수면 첫 줄은 left에 서고 둘째 줄부터 |intent|만큼 들어간다.
            # left에 표지 폭을 더하면 첫 줄까지 밀린다 (한글 2024 화면에서 확인)
            return self._derive(source, -size, left, None)
        return self._derive(source, em, left, None)

    def box_shapes(self, paragraphs, texts: list[str], char: str) -> list[str | None]:
        """자료 상자 문단마다의 문단 모양 번호 목록."""
        em = self.writer.media._em(char)
        return [self.shape_for(paragraphs[min(index, len(paragraphs) - 1)], text, index == len(texts) - 1, em)
                for index, text in enumerate(texts)]
