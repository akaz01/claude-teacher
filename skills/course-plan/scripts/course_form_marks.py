"""학교 환경에 따라 바꿀 곳 표시: 노란 형광펜과 한글 메모 (원안지 정답 형광펜처럼).

채우는 동안에는 글에 보이지 않는 표식 글자(사용자 영역 문자)를 넣고, 다 채운 뒤 apply_marks가 한 번에
형광펜(hp:markpenBegin/End)과 메모(hp:fieldBegin type="MEMO" … hp:fieldEnd)로 바꾼다.
- rule(): 학교 학업성적관리규정에 따라 바꿀 곳. 형광펜 + 메모(RULE_MEMO).
- check(): 학사일정으로 어림한 값. 형광펜 + 메모(CHECK_MEMO). 진도표에서는 첫 칸에만 쓰고 나머지는 pen().
- edu(): 학교 안내 교육을 받지 못했을 때 진도표 첫 비고 칸의 자리. 형광펜 + 메모(EDU_MEMO).
- pen(): 형광펜만.
표식은 한 문단 안에서 열고 닫는다(메모는 한 문단 안의 글에 달린다).
메모 짜임은 학교가 낸 교과진도평가계획 hwpx의 메모를 따랐고, 한글 2024에서 열기·저장·다시 열기·PDF를 확인했다.
메모 문구는 교사 승인을 받은 것이다(2026-11-21).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from course_form_xml import xml_text

RULE_OPEN, CHECK_OPEN, PEN_OPEN = "\ue000", "\ue001", "\ue002"
MEMO_CLOSE, PEN_CLOSE = "\ue003", "\ue004"
EDU_OPEN = "\ue005"            # 표식은 U+E000~E00F 안에서 쓴다 (다른 파일도 이 범위를 지운다)
MARK_RE = re.compile("[\ue000-\ue00f]")
PEN_COLOR = "#FFFF00"
AUTHOR = "teacher-kit"
MEMO_FIELD_ID = 623209829              # 한글이 메모에 쓰는 fieldid (학교 hwpx와 한글 2024 저장본에서 같음)
FIRST_MEMO_ID = 2000000001

HOW_TO = ["[형광펜 지우기] 글자를 블록으로 잡고 형광펜 단추 옆 ▼ → '색 없음'. "
          "Ctrl+A로 문서 전체를 잡으면 한 번에 지워집니다.",
          "[메모 지우기] 메모를 마우스 오른쪽 단추로 눌러 '메모 지우기'."]
RULE_MEMO = ["학교 학업성적관리규정에 맞게 바꿀 곳입니다(예시 값). 고친 뒤 형광펜을 지우세요.", *HOW_TO]
CHECK_MEMO = ["학교 학사일정에 맞게 확인할 곳입니다(어림한 값). "
              "형광펜을 칠한 기간·시수·누계를 확인하고 고친 뒤 형광펜을 지우세요.", *HOW_TO]
EDU_MEMO = ["학교에서 이 과목에 배정해 안내한 교육(안전교육, 성교육·양성평등교육 등)을 그 주 비고 칸에 "
            "[교육명(시간)]으로 적고, 이 자리는 지우세요.", *HOW_TO]
EDU_PLACE = "[학교 안내 교육]"
MEMOS = {RULE_OPEN: RULE_MEMO, CHECK_OPEN: CHECK_MEMO, EDU_OPEN: EDU_MEMO}


def rule(text: str) -> str:
    return f"{RULE_OPEN}{text}{MEMO_CLOSE}" if text else text


def check(text: str) -> str:
    return f"{CHECK_OPEN}{text}{MEMO_CLOSE}" if text else text


def edu(text: str = EDU_PLACE) -> str:
    """학교 안내 교육 자리 (진도표 첫 비고 칸)."""
    return f"{EDU_OPEN}{text}{MEMO_CLOSE}"


def rule_lines(text: str) -> list[str]:
    """여러 줄 글(칸 안에서 줄마다 문단이 되는 글): 첫 줄에 메모, 나머지 줄은 형광펜만.
    메모는 한 문단 안에서 열고 닫아야 한다."""
    lines = text.split(chr(10))
    return [rule(lines[0]), *(pen(line) for line in lines[1:])]


def pen(text: str) -> str:
    return f"{PEN_OPEN}{text}{PEN_CLOSE}" if text else text


def unmarked(text: str) -> str:
    """표식 글자를 뺀 글 (높이 어림, 글 비교용)."""
    return MARK_RE.sub("", text)


def count_marks(text: str) -> tuple[int, int]:
    """(형광펜 수, 메모 수). 메모가 달린 형광펜도 형광펜 수에 든다."""
    memos = sum(text.count(mark) for mark in MEMOS)
    return memos + text.count(PEN_OPEN), memos


def memo_style(header: str) -> tuple[str, str, str]:
    """(문단 모양, 스타일, 글자 모양) 번호: 양식 header의 '메모' 스타일. 없으면 바탕글(0)."""
    found = re.search(r'<hh:style [^>]*engName="Memo"[^>]*>', header)
    if not found:
        return "0", "0", "0"
    tag = found.group(0)
    return (re.search(r'paraPrIDRef="(\d+)"', tag).group(1), re.search(r' id="(\d+)"', tag).group(1),
            re.search(r'charPrIDRef="(\d+)"', tag).group(1))


def _memo_begin(number: int, lines: list[str], style: tuple[str, str, str], stamp: str) -> str:
    para_pr, style_id, char_pr = style
    body = "".join(f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="{style_id}" pageBreak="0" columnBreak="0" '
                   f'merged="0"><hp:run charPrIDRef="{char_pr}"><hp:t>{xml_text(line)}</hp:t></hp:run></hp:p>'
                   for line in lines)
    return (f'<hp:ctrl><hp:fieldBegin id="{FIRST_MEMO_ID + number}" type="MEMO" name="" editable="1" dirty="1" '
            f'zorder="{number + 1}" fieldid="{MEMO_FIELD_ID}"><hp:parameters cnt="7" name="">'
            f'<hp:integerParam name="Prop">0</hp:integerParam>'
            f'<hp:stringParam name="Command">MEMO/65535/{number + 1}/0/0/{AUTHOR}/\\;;</hp:stringParam>'
            f'<hp:stringParam name="ID">memo{number + 1}</hp:stringParam>'
            f'<hp:integerParam name="Number">{number + 1}</hp:integerParam>'
            f'<hp:stringParam name="Author">{AUTHOR}</hp:stringParam>'
            f'<hp:stringParam name="MemoShapeIDRef">65535</hp:stringParam>'
            f'<hp:stringParam name="CreateDateTime">{stamp}</hp:stringParam></hp:parameters>'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
            f'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{body}</hp:subList>'
            f'</hp:fieldBegin></hp:ctrl>')


def _first_number(section: str) -> int:
    """양식에 이미 있는 메모와 번호가 겹치지 않게, 새 메모의 첫 순번."""
    ids = [int(found) - FIRST_MEMO_ID for found in re.findall(r'<hp:fieldBegin id="(\d+)" type="MEMO"', section)]
    return max([number + 1 for number in ids if number >= 0] + [section.count('type="MEMO"')])


def apply_marks(section: str, header: str) -> str:
    """구역 XML의 표식 글자를 형광펜과 메모로 바꾼다. 표식은 <hp:t> 안에 있어야 한다.
    짝이 맞지 않는 표식(입력에 섞여 든 글자 등)이 있으면 표식을 모두 지운다."""
    if not _balanced(section):
        section = MARK_RE.sub("", section)
    style = memo_style(header)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pen_begin = f'<hp:markpenBegin color="{PEN_COLOR}"/>'
    opened: list[int] = []
    numbers = iter(range(_first_number(section), 10 ** 6))

    def swap(match: re.Match) -> str:
        mark = match.group(0)
        if mark == PEN_OPEN:
            return pen_begin
        if mark == PEN_CLOSE:
            return "<hp:markpenEnd/>"
        if mark in MEMOS:
            number = next(numbers)
            opened.append(number)
            begin = _memo_begin(number, MEMOS[mark], style, stamp)
            return f"</hp:t>{begin}<hp:t>{pen_begin}"
        number = opened.pop()
        end = f'<hp:ctrl><hp:fieldEnd beginIDRef="{FIRST_MEMO_ID + number}" fieldid="{MEMO_FIELD_ID}"/></hp:ctrl>'
        return f"<hp:markpenEnd/></hp:t>{end}<hp:t>"
    return MARK_RE.sub(swap, section)


def _balanced(text: str) -> bool:
    """여는 표식과 닫는 표식이 차례대로 짝이 맞는지."""
    memos = pens = 0
    for mark in MARK_RE.findall(text):
        if mark in MEMOS:
            memos += 1
        elif mark == PEN_OPEN:
            pens += 1
        elif mark == MEMO_CLOSE:
            memos -= 1
        else:
            pens -= 1
        if memos < 0 or pens < 0:
            return False
    return memos == 0 and pens == 0


CTRL_TOKEN_RE = re.compile(r"<hp:ctrl>|</hp:ctrl>|<hp:t>|</hp:t>")


def _body_text_spans(paragraph: str) -> tuple[list[int], list[int]]:
    """메모·필드 같은 <hp:ctrl> 안을 뺀 본문 <hp:t>의 (글 시작 위치들, 글 끝 위치들)."""
    depth, starts, ends = 0, [], []
    for match in CTRL_TOKEN_RE.finditer(paragraph):
        token = match.group(0)
        if token == "<hp:ctrl>":
            depth += 1
        elif token == "</hp:ctrl>":
            depth -= 1
        elif depth == 0 and token == "<hp:t>":
            starts.append(match.end())
        elif depth == 0:
            ends.append(match.start())
    return starts, ends


def wrap_paragraph(paragraph: str, opener: str, closer: str) -> str:
    """양식에 있던 문단(글이 여러 run에 나뉜 것)의 본문 글 전체를 표식으로 감싼다. 메모 안 글은 건드리지 않는다.
    본문 글이 없으면 그대로."""
    starts, ends = _body_text_spans(paragraph)
    body = "".join(paragraph[a:b] for a, b in zip(starts, ends))
    if not starts or not ends or not re.sub(r"<[^>]+>", "", body).strip():
        return paragraph
    return paragraph[:starts[0]] + opener + paragraph[starts[0]:ends[-1]] + closer + paragraph[ends[-1]:]

