"""make_hwpx.py의 글 속 수식. 표준 라이브러리만 쓴다.

글자 안의 {{...}}는 한글 수식(hp:equation)이 된다 (한 줄 안, 한글이 없고 비어 있지 않을 때). 안쪽은 한글 수식 문법을 그대로 쓰고,
숫자/숫자는 분수로 바꾼다: {{2/3}} → {2} over {3}, {{1 7/12}} → 1 {7} over {12} (대분수).
한글은 문서를 열 때 수식 크기를 다시 계산하므로 hp:sz는 어림값이다 (한글에서 PDF로 바꿔 확인).
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

HANGUL = re.compile(r"[가-힣]")
# 숫자와 숫자 사이 분수. 소수(0.5/2)도 한 덩어리로 보고, 날짜(2024/12/25)처럼 슬래시가 이어지면 분수가 아니다
FRACTION = re.compile(r"(?<![\d/.])(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)(?![\d/]|\.\d)")
GREEK_NAMES = ("alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta", "theta", "vartheta",
               "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon",
               "phi", "varphi", "chi", "psi", "omega", "inf")
_GREEK_PATTERN = "|".join(sorted({*GREEK_NAMES, *(name.upper() for name in GREEK_NAMES)}, key=len, reverse=True))
# ^ 나 _ 바로 뒤의 낱말 하나(부호 + 숫자·소수, 그리스 문자 이름, 한 글자 변수)를 중괄호로 묶는다. 이미 { 이면 그대로 둔다
SCRIPT_TOKEN = re.compile(rf"([\^_])([-+]?(?:\d+(?:\.\d+)?|(?:{_GREEK_PATTERN})(?![A-Za-z])|[A-Za-z]))")
EQUATION_BASE_UNIT = 1100               # 수식 글자 크기 11pt (본문과 같게)
EQUATION_CHAR_WIDTH = 600               # 수식 너비 어림: 글자 하나 약 600 HWPUNIT
EQUATION_HEIGHT = 1300                  # 한 줄 수식 높이 어림
FRACTION_HEIGHT = 2500                  # 분수(over)가 있는 수식 높이 어림
EQUATION_MARGIN = 56                    # 수식 좌우 바깥 여백 0.2mm (한글 기본값)
DEFAULT_COLOR = "#000000"
WARNING_SHOW = 3                        # 경고에 보여 줄 예시 수
PREVIEW_CHARS = 24


def _closing_index(text: str, start: int) -> int | None:
    """start부터 한 줄 안에서 중괄호 짝을 세어 수식을 닫는 }} 의 위치를 찾는다. 짝이 안 맞으면 첫 }} ."""
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "\n":
            return None
        if char == "{":
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
            elif text[index + 1:index + 2] == "}":
                return index
    line_end = text.find("\n", start)
    first = text.find("}}", start)
    return first if first != -1 and (line_end == -1 or first < line_end) else None


def equation_spans(text: str) -> list[tuple[int, int, str]]:
    """{{수식}}의 (시작, 끝, 안쪽 글) 목록. 한 줄 안이고 비어 있지 않으며 한글이 없을 때만 수식이다.

    }}}로 끝나는 수식(x^{2}, sqrt{2})은 중괄호 짝을 세어 바른 끝을 찾는다."""
    spans: list[tuple[int, int, str]] = []
    position = 0
    while True:
        start = text.find("{{", position)
        if start == -1:
            return spans
        end = _closing_index(text, start + 2)
        content = text[start + 2:end] if end is not None else ""
        if end is None or not content.strip() or HANGUL.search(content):
            position = start + 1
            continue
        spans.append((start, end + 2, content))
        position = end + 2


def equation_script(content: str) -> str:
    """{{ }} 안쪽 글을 한글 수식 문법으로: 지수·아래첨자는 {}로 묶고, 숫자/숫자는 분수, 줄바꿈은 빈칸."""
    flat = " ".join(content.split())
    return FRACTION.sub(r"{\1} over {\2}", SCRIPT_TOKEN.sub(r"\1{\2}", flat))


def equation_preview(text: str) -> str:
    """미리 보기 글에서는 {{2/3}}을 2/3으로 보인다."""
    pieces = split_equations(text)
    return "".join(" ".join(part.split()) if is_equation else part for part, is_equation in pieces)


def split_equations(text: str) -> list[tuple[str, bool]]:
    """글을 (조각, 수식인지) 목록으로 나눈다. 빈 글 조각은 뺀다."""
    pieces: list[tuple[str, bool]] = []
    position = 0
    for start, end, content in equation_spans(text):
        pieces.append((text[position:start], False))
        pieces.append((content, True))
        position = end
    pieces.append((text[position:], False))
    return [(part, is_equation) for part, is_equation in pieces if part]


def equation_width(script: str) -> int:
    """수식 너비 어림 (한글이 문서를 열 때 다시 계산한다)."""
    visible = re.sub(r"\bover\b|[{}\s]", "", script)
    return max(len(visible), 1) * EQUATION_CHAR_WIDTH


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    return []


def _shown(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS] + "…"


def equation_text_warnings(spec) -> list[str]:
    """글자만 보고 알 수 있는 수식 문제: 수식 속 한글, LaTeX 역슬래시."""
    texts = _strings(spec)
    mixed: list[str] = []
    latex: list[str] = []
    for text in texts:
        for match in re.finditer(r"\{\{([^\n]*?)\}\}", text):
            inner = match.group(1)
            has_math = re.search(r"[0-9=+\-^_/<>]", HANGUL.sub("", inner))
            if HANGUL.search(inner) and has_math:
                mixed.append(match.group(0))
        latex.extend(_shown(content) for _, _, content in equation_spans(text) if "\\" in content)
    warnings = []
    if mixed:
        shown = ", ".join(dict.fromkeys(_shown(item) for item in mixed[:WARNING_SHOW]))
        warnings.append(f"주의: 수식 안에 한글이 있어 수식으로 바뀌지 않고 글자로 남음 ({shown}) "
                        "→ 수식은 {{x=1}}처럼 식만 쓰고 설명은 {{ }} 밖에 쓰세요")
    if latex:
        shown = ", ".join(dict.fromkeys(latex[:WARNING_SHOW]))
        warnings.append(f"주의: 수식 안의 역슬래시(\\)는 한글 수식에서 쓰이지 않음 ({shown}) "
                        "→ \\frac{1}{2}는 {1} over {2}, \\sqrt는 sqrt처럼 한글 수식 문법으로 쓰세요")
    return warnings


def equation_xml(equation_id: int, script: str, color: str = DEFAULT_COLOR, bold: bool = False) -> str:
    """글자처럼 취급하는(treatAsChar) 한글 수식 개체. script는 XML에 넣기 전의 수식 문법."""
    width = equation_width(script)
    height = FRACTION_HEIGHT if re.search(r"\bover\b", script) else EQUATION_HEIGHT
    if bold:
        script = f"bold {{{script}}}"
    return (
        f'<hp:equation id="{equation_id}" zOrder="0" numberingType="EQUATION" textWrap="TOP_AND_BOTTOM" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" version="Equation Version 60" baseLine="66" '
        f'textColor="{color}" baseUnit="{EQUATION_BASE_UNIT}" lineMode="CHAR" font="HancomEQN">'
        f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" '
        'vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="{EQUATION_MARGIN}" right="{EQUATION_MARGIN}" top="0" bottom="0"/>'
        f'<hp:shapeComment>수식입니다.</hp:shapeComment><hp:script>{escape(script)}</hp:script></hp:equation>'
    )
