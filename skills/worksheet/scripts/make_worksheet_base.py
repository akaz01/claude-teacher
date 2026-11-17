"""개념 정리 학습지 공용 바탕: 하우스 스타일 색, 쪽 모양, 글자 너비 어림, 칸·도형 도우미, 빈칸 처리.

make_worksheet_concept.py(개요·옆 칸·문서)와 make_worksheet_quiz.py(형성평가)가 함께 쓴다. 모든 크기는 앱 화면 px.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# 하우스 스타일 색(앱 디자인 학습지 samples/app-sample/write_sheet.py와 같은 값). 활동지(make_worksheet.py)도 여기서 가져다 쓴다
NAVY, BLUE, ANS = "#1F3F7A", "#2E6DB4", "#1D4ED8"
INK, MUTED, FAINT = "#14213D", "#556070", "#767676"
SKY, SKY_LINE, PALE, TINT = "#EAF0F7", "#B9CDE6", "#F6F9FD", "#E3EDF9"
HAIR, ROW_LINE = "#C9D3DF", "#97AECB"
GOLD, CREAM, FILL = "#A8670F", "#FFF6E3", "#FFEFC2"       # 노랑 포인트(FILL은 빈칸 음영색으로 공용 모듈 기본값과 같다)
WHITE, BAND_TEXT, GRAY = "#FFFFFF", "#DCE7F6", "#7F7F7F"
CIRCLED = "①②③④⑤"
QUESTION_KINDS = ("선택형", "단답형", "O·X", "서술형")
BLANK_MARK = re.compile(r"\[\[(.+?)\]\]", re.S)
TYPED_BLANK = re.compile(r"\(\s{3,}\)")

# ---- 쪽 모양 (px)
PAGE_W, BODY_X, BODY_W = 794, 48, 698
BAND_H = 101
TOP_MARGIN = 58.7                                 # 본문이 시작하는 자리: 위 여백 40px + 첫 문단 14px + 도형 문단 둘
SIDE_X, SIDE_W, MAIN_W, SIDE_GAP = 550, 196, 488, 10
FIRST_TOPIC_GAP = 15
BOX_GAP = 8                                       # 상자(제시문·서술 칸)와 앞뒤 글 사이
QUESTION_GAP = 6                                  # 문항 글과 보기·답 칸 사이, 보기 줄 사이
TOP_PAGE_MARGIN = 40                              # 쪽 위 여백(px)
QUIZ_BOTTOM = 1046                                # 형성평가 쪽의 아래 끝(높이 어림이 쪽마다 조금 다르다)
BODY_BOTTOM = 1041                                # 본문 아래 끝(꼬리말 위쪽). 개념 정리·형성평가가 여기까지 찬다
MIN_TOPIC_GAP, MIN_QUESTION_GAP, FIRST_QUESTION_GAP = 12, 14, 16
MAX_GAP = 44                                      # 내용이 적을 때 간격이 끝없이 벌어지지 않게 하는 상한
SAFETY_PX = 8                                     # 형성평가 쪽 아래에 남기는 여유 (한글은 표마다 높이가 조금씩 늘어난다)
TEACHER_MIN_QUESTION_GAP = 8                      # 교사용(해설 줄이 더 있음)은 문항 사이를 이만큼까지 좁혀 2쪽을 지킨다
BORDER_PX, BOX_PAD = 1.5, 8                      # 상자 선 두께와 안쪽 위아래 여백
LINE_145, LINE_160, LINE_165 = 145, 160, 165      # 줄 간격 %(앱 line-height 1.45·1.6·1.65)
LINE_PX = 14 * 1.45                               # 10.5pt 글자 한 줄 (px)
FOOTER_LABEL = "교사용"
BLANK_UNIT_PX = 0.49 * 14                         # 공백 한 칸의 너비 어림(px)
BLANK_PAD_PX, MIN_BLANK_UNITS = 26, 4             # 가장 긴 답 양옆 여유, 빈칸 최소 공백 수
SHORT_ANSWER_PAD_PX, MIN_SHORT_ANSWER_PX = 60, 220    # 단답 칸 기본 너비 = 앱 판 answer_line(220px)
ESSAY_LINES = (1, 8)                              # 서술형 쓰기 줄 수 범위
ESSAY_ROW_PX = 30                                 # 서술형 쓰기 줄 한 줄 높이
THIN, THICK = 0.25, 0.4                           # 선 굵기 mm: 1px 점선, 1.5px 상자 선

# ---- 글자 너비 어림(em). 한컴오피스 함초롬바탕·맑은 고딕을 한글에서 PDF로 바꿔 잰 값
SERIF_EM = {"han": 1.0, "digit": 0.67, "latin": 0.58, " ": 0.33, "narrow": 0.22, "wide": 0.72, "arrow": 0.95}
SANS_EM = {"han": 1.0, "digit": 0.55, "latin": 0.52, " ": 0.35, "narrow": 0.22, "wide": 0.70, "arrow": 0.95}
NARROW_MARKS, WIDE_MARKS = "·.,:()'", "~+/-“”"
PX_PER_PT = 96 / 72
SANS_RATIO, SERIF_RATIO = 92, 85                  # 장평 %: 앱 글꼴(Noto Sans KR·Hahmlet)의 글자 너비에 맞춘다
SERIF = "myeongjo"                                # HY견명조: 한컴오피스 기본 명조 계열 중 굵게가 앱 Hahmlet과 가장 비슷하다
WIDTH_SLACK = 1.06                                # 어림이 모자라 줄바꿈되지 않게 두는 여유


def text_px(text: str, pt: float, serif: bool = False) -> float:
    """글 한 줄의 너비 어림 (px)."""
    table = SERIF_EM if serif else SANS_EM
    total = 0.0
    for char in text:
        if char in NARROW_MARKS:
            total += table["narrow"]
        elif char in WIDE_MARKS:
            total += table["wide"]
        elif char in "→↔":
            total += table["arrow"]
        elif char == " ":
            total += table[" "]
        elif char.isdigit():
            total += table["digit"]
        elif char.isascii():
            total += table["latin"]
        else:
            total += table["han"]
    return total * pt * PX_PER_PT * (SERIF_RATIO if serif else SANS_RATIO) / 100


def wrapped_lines(text: str, width: float, pt: float, serif: bool = False) -> int:
    """칸 너비에 글이 몇 줄로 들어갈지 어림한다 (줄바꿈 \\n은 그대로 센다)."""
    shown = plain_text(text)                            # 표기를 떼고 빈칸은 학생용 너비로 센다 (교사용도 같은 줄 수)
    return sum(max(1, math.ceil(text_px(part, pt, serif) * WIDTH_SLACK / max(width, 1))) for part in shown.split("\n"))



def has_answer(answer) -> bool:
    return answer is not None and answer != ""      # 숫자 0도 답이다


def text_list(value, name: str) -> list[str]:
    """목록 자리에 글 하나가 오면 [글]로 감싼다. 글이나 글 목록이 아니면 한국어 오류. 활동지·개념 정리가 함께 쓴다."""
    if value is None:
        return []
    items = [value] if isinstance(value, (str, int, float)) and not isinstance(value, bool) else value
    if not isinstance(items, list) or not all(isinstance(item, (str, int, float)) and not isinstance(item, bool)
                                              for item in items):
        raise ValueError(f"'{name}'은 글 또는 글 목록이어야 함 (받은 값: {value!r})")
    return [str(item) for item in items]


@dataclass
class Widths:
    """한 학습지 안에서 모두 같게 쓰는 칸 너비. build_concept_spec이 학습지마다 새로 정한다."""
    blank_units: int = MIN_BLANK_UNITS      # 개요 빈칸의 공백 수
    short_answer_px: int = MIN_SHORT_ANSWER_PX


WIDTHS = Widths()


# ---------------------------------------------------------------- 칸·선 도우미

def edge(width_mm: float, color: str, kind: str = "SOLID") -> list:
    return [kind, width_mm, color]


def cell(content=None, **options) -> dict:
    """표 칸. content는 글 또는 글·도형 목록. 기본은 테두리 없음·왼쪽 위·여백 없음·앱 글자 색."""
    pad = options.pop("pad", (0, 0, 0, 0))
    base = {"edges": "none", "valign": "top", "align": "left", "pad_px": list(pad), "color": INK,
            "ratio": SERIF_RATIO if options.get("font") == SERIF else SANS_RATIO, "font_space": True}
    if isinstance(content, list):
        base["content"] = content
    elif content is not None:
        base["text"] = content
        if "**" in str(content):                # **굵게**는 칸 글자 색 그대로 굵게
            base["mark_color"] = options.get("color", INK)
    return {**base, **options}


def table(widths: list, rows: list, **options) -> dict:
    return {"type": "table", "widths": widths, "border": "none", "rows": rows, **options}


def chip(text: str, fill: str, color: str, height: float = 20, pt: float = 9, serif: bool = False, **extra) -> dict:
    """둥근 이름표(글상자). 너비는 글 길이에 맞춘다."""
    width = text_px(text, pt, serif) * WIDTH_SLACK + 22
    return {"shape": "round", "w": round(width), "h": height, "fill": fill, "text": text, "color": color,
            "bold": True, "size": pt, "pad_px": 4, "ratio": SERIF_RATIO if serif else SANS_RATIO, "font_space": True,
            **extra}


def circle(text: str, fill: str, size: int = 24, pt: float = 10.5, **extra) -> dict:
    return {"shape": "ellipse", "w": size, "h": size, "fill": fill, "text": text, "color": WHITE, "bold": True,
            "font": SERIF, "size": pt, "pad_px": 0, "ratio": SERIF_RATIO, "font_space": True, **extra}


def run(text: str, pt: float, color: str = INK, **extra) -> dict:
    ratio = SERIF_RATIO if extra.get("font") == SERIF else SANS_RATIO
    return {"run": text, "size": pt, "color": color, "ratio": ratio, "font_space": True, **extra}


@dataclass
class Flow:
    """위에서 아래로 놓는 블록과 그 높이를 세어 둔다 (종이 기준으로 놓는 옆 칸의 자리를 정할 때 쓴다)."""
    y: float = TOP_MARGIN
    blocks: list = field(default_factory=list)

    def add(self, block: dict, height: float, above: float = 0, below: float = 0) -> None:
        self.blocks.append({**block, "gap_px": [above, below]})
        self.y += above + height + below

    def extra(self, block: dict) -> None:
        self.blocks.append(block)


# ---------------------------------------------------------------- 빈칸

def blank_text(answer: str, teacher: bool) -> str:
    """[[답]]을 ~~음영 밑줄~~ 칸으로. 너비는 답과 상관없이 늘 같고(WIDTHS.blank_units), 교사용은 그 안에 답이 든다."""
    units = WIDTHS.blank_units
    if not teacher:
        return "~~" + " " * units + "~~"
    spare = max(1, int((units - text_px(answer, 10.5) / BLANK_UNIT_PX) // 2))
    return "~~" + " " * spare + answer + " " * spare + "~~"


def plain_blank(text: str, teacher: bool) -> str:
    """음영을 못 쓰는 곳(도형 글·문서 제목)의 [[답]]: 학생용은 같은 너비의 괄호, 교사용은 (답)."""
    return BLANK_MARK.sub(lambda found: f"({found.group(1) if teacher else ' ' * WIDTHS.blank_units})", text)


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def set_widths(doc: dict) -> None:
    """학습지 전체에서 가장 긴 답에 맞춰 개요 빈칸·단답 칸 너비를 한 값으로 정한다 (학생용·교사용이 같은 값)."""
    answers = [found for text in _strings(doc) for found in BLANK_MARK.findall(text)]
    longest = max((text_px(answer, 10.5) for answer in answers), default=0)
    WIDTHS.blank_units = max(MIN_BLANK_UNITS, round((longest + BLANK_PAD_PX) / BLANK_UNIT_PX))
    shorts = [str(item["answer"]) for item in doc.get("questions") or [] if item.get("kind") == "단답형"
              and has_answer(item.get("answer"))]
    widest = max((text_px(answer, 11.25) for answer in shorts), default=0)
    WIDTHS.short_answer_px = max(MIN_SHORT_ANSWER_PX, round(widest + SHORT_ANSWER_PAD_PX))


def fill_blanks(text: str, teacher: bool) -> str:
    return BLANK_MARK.sub(lambda found: blank_text(found.group(1), teacher), text)


def plain_text(text: str) -> str:
    """글자 너비를 어림할 때 쓰는, 표기를 뗀 글. [[답]]은 학생용 빈칸 너비로 센다."""
    return re.sub(r"~~|\*\*", "", fill_blanks(text, False))
