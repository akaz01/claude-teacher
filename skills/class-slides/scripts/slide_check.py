"""저장하기 전에 슬라이드를 마지막으로 다듬는다. make_deck.py와 make_pptx.py가 쓴다.

- 슬라이드 밖으로 나간 도형은 크기를 지켜 안으로 옮긴다. 슬라이드보다 크면 비율을 지켜 줄인다.
- 글이 상자보다 길거나 끝 줄에 몇 글자만 남으면 글자를 조금 줄여 없앤다. 같은 장에서 크기와 폭이
  같은 글은 함께 줄여 크기를 맞춘다.
- 줄여도 끝 줄이 남으면 어절 사이에 줄바꿈을 넣어 줄 길이를 고르게 한다. 글꼴이 조금 달라도 그대로 유지된다.
- 고치지 못한 것은 경고로 돌려준다. 줄바꿈은 어절 단위로 어림한 값이다.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Pt

EMU_PER_PT = 12700
HANGUL_EM, LATIN_EM, SPACE_EM = 1.0, 0.55, 0.3   # 맑은 고딕을 재어 본 글자 폭
FIT_SLACK = 0.97        # 실제 글꼴이 어림보다 조금 넓어도 꺾이지 않게 폭을 덜 쓴다
WIDTH_GUESSES = (FIT_SLACK, 1.0, 1.06)  # PowerPoint로 재어 보니 어림과 몇 %씩 달라 이 폭들을 모두 본다
LINE_FACTOR = 1.2
OVERFLOW_ROOM = 1.05    # 맑은 고딕의 실제 줄 높이가 어림보다 조금 낮아 이만큼은 넘친 것으로 보지 않는다
SHORT_TAIL_RATIO = 0.3  # 끝 줄이 첫 줄의 이 비율 이하면 "몇 글자만 남은 줄"로 본다. 생성기·양식 복제·check_wrap.ps1·문서가 모두 같은 값(30%)을 쓴다
SHORT_TAIL = SHORT_TAIL_RATIO
MAX_TRIM = 0.15         # 글자를 줄이는 한도
HEAD_LENGTH = 16
LINE_BREAK = re.compile("\x0b|\n")     # paragraph.text는 줄바꿈 자리를 x0b 문자로 돌려준다


@dataclass(frozen=True)
class TextSpot:
    """글이 들어가는 자리. height가 None이면 칸이 글에 맞춰 늘어난다 (표)."""
    frame: object
    width: int
    height: int | None


def units(text: str) -> float:
    return sum(SPACE_EM if ch == " " else LATIN_EM if ord(ch) < 128 else HANGUL_EM for ch in text)


def wrap_widths(text: str, per_line: float) -> list[float]:
    """어절을 지키며 줄을 나누고 줄마다 폭(em)을 돌려준다. 한 줄보다 긴 어절만 가운데서 끊는다."""
    lines: list[float] = []
    current = 0.0
    for word in text.split(" "):
        width = units(word)
        if current and current + SPACE_EM + width > per_line:
            lines.append(current)
            current = width
        else:
            current += (SPACE_EM if current else 0.0) + width
        while current > per_line:
            lines.append(per_line)
            current -= per_line
    lines.append(current)
    return lines


def _paragraph_size(paragraph) -> float | None:
    sizes = [run.font.size.pt for run in paragraph.runs if run.font.size is not None]
    return max(sizes) if sizes and len(sizes) == len(paragraph.runs) else None


def _indent(paragraph) -> int:
    props = paragraph._p.pPr
    return int(props.get("marL", 0)) if props is not None else 0


def _paragraphs(spot: TextSpot) -> list:
    return [paragraph for paragraph in spot.frame.paragraphs if paragraph.text.strip()]


def _adjustable(spot: TextSpot) -> bool:
    return bool(_paragraphs(spot)) and all(_paragraph_size(item) for item in _paragraphs(spot))


def _line_room(spot: TextSpot, paragraph, size: float) -> float:
    """한 줄에 들어가는 폭(em)."""
    inner = spot.width - spot.frame.margin_left - spot.frame.margin_right - _indent(paragraph)
    return max(1.0, inner / EMU_PER_PT / size)


def _has_tail(text: str, per_line: float) -> bool:
    widths = wrap_widths(text, per_line)
    return len(widths) >= 2 and widths[-1] <= widths[0] * SHORT_TAIL


def _problem(spot: TextSpot, scale: float = 1.0) -> str | None:
    """글자를 scale배로 했을 때의 문제: "tail", "overflow", 없으면 None."""
    total = 0.0
    tail = False
    for paragraph in _paragraphs(spot):
        size = _paragraph_size(paragraph) * scale
        room = _line_room(spot, paragraph, size)
        pieces = [piece for piece in LINE_BREAK.split(paragraph.text.strip()) if piece.strip()]
        total += sum(len(wrap_widths(piece, room * FIT_SLACK)) for piece in pieces) * size * LINE_FACTOR
        tail = tail or any(_has_tail(piece, room * guess) for piece in pieces for guess in WIDTH_GUESSES)
    if spot.height is not None:
        room = (spot.height - spot.frame.margin_top - spot.frame.margin_bottom) / EMU_PER_PT
        if total > room * OVERFLOW_ROOM:
            return "overflow"
    return "tail" if tail else None


def _scale_text(spot: TextSpot, scale: float) -> None:
    for paragraph in spot.frame.paragraphs:
        for run in paragraph.runs:
            if run.font.size is not None:
                run.font.size = Pt(round(run.font.size.pt * scale * 2) / 2)


def _break_at(paragraph, index: int) -> None:
    """글의 index 자리에 있는 띄어쓰기를 줄바꿈으로 바꾼다. 앞뒤 글의 모양은 그대로 둔다."""
    for run in paragraph.runs:
        if index >= len(run.text):
            index -= len(run.text)
            continue
        after = copy.deepcopy(run._r)
        after.find(qn("a:t")).text = run.text[index + 1:]
        run.text = run.text[:index]
        line_break = OxmlElement("a:br")
        props = run._r.find(qn("a:rPr"))
        if props is not None:
            line_break.append(copy.deepcopy(props))
        run._r.addnext(line_break)
        line_break.addnext(after)
        return


def _even_breaks(text: str, per_line: float) -> list[int] | None:
    """줄 길이가 고르게 되는 띄어쓰기 자리를 돌려준다. 어느 줄이든 한 줄을 넘으면 None."""
    count = len(wrap_widths(text, per_line))
    spaces = [index for index, ch in enumerate(text) if ch == " "]
    if count < 2 or len(spaces) < count - 1:
        return None
    total = units(text)
    chosen = sorted({min(spaces, key=lambda index: abs(units(text[:index]) - total * part / count))
                     for part in range(1, count)})
    edges = [-1, *chosen, len(text)]
    lengths = [units(text[start + 1:end]) for start, end in zip(edges, edges[1:])]
    return chosen if len(chosen) == count - 1 and max(lengths) <= per_line else None


def _balance(spot: TextSpot) -> None:
    """끝 줄에 몇 글자만 남는 문단의 줄 길이를 고르게 한다."""
    for paragraph in _paragraphs(spot):
        text = paragraph.text
        room = _line_room(spot, paragraph, _paragraph_size(paragraph))
        if LINE_BREAK.search(text) or not any(_has_tail(text, room * guess) for guess in WIDTH_GUESSES):
            continue
        for index in reversed(_even_breaks(text, room * FIT_SLACK) or []):
            _break_at(paragraph, index)


def _spots(slide) -> list[TextSpot]:
    spots = []
    for shape in slide.shapes:
        if shape.rotation:
            continue
        if shape.has_text_frame and shape.text_frame.word_wrap is not False:
            spots.append(TextSpot(shape.text_frame, shape.width, shape.height))
        elif getattr(shape, "has_table", False):
            widths = [column.width for column in shape.table.columns]
            spots += [TextSpot(cell.text_frame, widths[index], None)
                      for row in shape.table.rows for index, cell in enumerate(row.cells)
                      if not cell.is_spanned and not cell.is_merge_origin]
    return [spot for spot in spots if _adjustable(spot)]


def _peer_key(spot: TextSpot) -> tuple:
    return spot.width, max(_paragraph_size(item) for item in _paragraphs(spot))


def _smallest_fix(group: list[TextSpot]) -> float | None:
    """모든 글의 문제가 사라지는 가장 작은 변화(배율)를 찾는다."""
    size = _peer_key(group[0])[1]
    for trim in range(1, int(size * MAX_TRIM) + 1):
        scale = (size - trim) / size
        if not any(_problem(spot, scale) for spot in group):
            return scale
    return None


def _report(spot: TextSpot, where: str) -> str:
    head = _paragraphs(spot)[0].text.strip()[:HEAD_LENGTH]
    if _problem(spot) == "overflow":
        return f"{where}: '{head}' 글이 상자를 넘칠 수 있음. 글을 줄이거나 장을 나누세요"
    return f"{where}: '{head}' 끝 줄에 몇 글자만 남음. 글을 다듬어 한 줄로 만들거나 두 문단으로 나누세요"


def _tidy_text(slide, where: str) -> list[str]:
    groups: dict[tuple, list[TextSpot]] = {}
    for spot in _spots(slide):
        groups.setdefault(_peer_key(spot), []).append(spot)
    warnings = []
    for group in groups.values():
        if not any(_problem(spot) for spot in group):
            continue
        scale = _smallest_fix(group)
        if scale is not None:
            for spot in group:
                _scale_text(spot, scale)
            continue
        for spot in group:
            _balance(spot)
        warnings += [_report(spot, where) for spot in group if _problem(spot)]
    return warnings[:1]     # 고쳐서 다시 만들면 다음 것이 보이므로 장마다 하나만 알린다


def _keep_inside(shape, slide_width: int, slide_height: int, where: str) -> str | None:
    left, top, width, height = shape.left, shape.top, shape.width, shape.height
    if None in (left, top, width, height) or shape.rotation:
        return None
    ratio = min(1.0, slide_width / width if width else 1.0, slide_height / height if height else 1.0)
    new_width, new_height = int(width * ratio), int(height * ratio)
    new_left = min(max(left, 0), slide_width - new_width)
    new_top = min(max(top, 0), slide_height - new_height)
    if (new_left, new_top, new_width, new_height) == (left, top, width, height):
        return None
    shape.left, shape.top, shape.width, shape.height = new_left, new_top, new_width, new_height
    return f"{where}: '{shape.name}'이(가) 슬라이드 밖으로 나가 안으로 옮김. 다른 것과 겹치지 않는지 보세요"


def polish(prs, known: list[str] | tuple = ()) -> list[str]:
    """모든 장을 다듬고 교사가 확인할 경고를 돌려준다. known에서 이미 넘침을 알린 장은 글 경고를 더하지 않는다."""
    warnings = []
    for number, slide in enumerate(prs.slides, 1):
        where = f"{number}번째 장"
        for shape in slide.shapes:
            moved = _keep_inside(shape, prs.slide_width, prs.slide_height, where)
            if moved:
                warnings.append(moved)
        found = _tidy_text(slide, where)
        if not any(item.startswith(where) and "넘칠" in item for item in known):
            warnings += found
    return warnings
