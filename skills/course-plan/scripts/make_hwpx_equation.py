"""make_hwpx.py의 글 속 수식. 표준 라이브러리만 쓴다.

글자 안의 {{...}}는 한글 수식(hp:equation)이 된다 (한 줄 안, 한글이 없고 비어 있지 않을 때). 안쪽은 한글 수식 문법을 그대로 쓰고,
숫자/숫자는 분수로 바꾼다: {{2/3}} → {2} over {3}, {{1 7/12}} → 1 {7} over {12} (대분수).
hp:sz는 어림값이다. 한글 2024는 열 때 너비를 다시 계산하지 않으므로 equation_width를 실측에 맞춰 넉넉히 잡는다.
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


def equation_width(script: str, base_unit: int = EQUATION_BASE_UNIT) -> int:
    """수식 너비 어림 (HWPUNIT).

    한글 2024는 파일을 열 때 이 너비를 다시 계산하지 않고 그대로 쓴다. 실제보다 좁으면 뒤 글자와 겹치므로
    한글이 EquationCreate로 만든 수식의 너비(baseUnit 1000)를 재어 기호마다 폭을 맞췄다 (2026-11-18 실측).
    """
    items, _ = _width_items(_EQ_TOKEN.findall(script), 0)
    return max(round(sum(items) * WIDTH_SAFETY * base_unit / 1000), EQUATION_CHAR_WIDTH * base_unit // 1000)


_EQ_TOKEN = re.compile(r"[A-Za-z]+|\d+(?:\.\d+)?|\S")
EQ_WORDS = {"LEQ": 1050, "GEQ": 1050, "NEQ": 1050, "leq": 1050, "geq": 1050, "times": 1120, "cdot": 700,
            "inf": 900, "INF": 900, "le": 1050, "ge": 1050, "pm": 1120, "therefore": 900, "because": 900}
EQ_ROMAN = {"sin", "cos", "tan", "log", "ln", "lim", "max", "min", "sum", "int", "exp", "det"}
EQ_STYLES = {"bold", "it", "rm"}
EQ_SPACE = {"`": 250, "~": 500}
EQ_SYMBOLS = {"×": 1120, "÷": 1120, "±": 1120, "≤": 1050, "≥": 1050, "≠": 1050, "→": 1200, "∞": 900, "°": 400,
              "+": 1120, "-": 1120, "=": 1200, "<": 1200, ">": 1200, "(": 420, ")": 420, "[": 420, "]": 420,
              ",": 500, "|": 400, ".": 300, ":": 400, "!": 400}
EQ_DIGIT, EQ_LOWER, EQ_UPPER, EQ_OTHER = 525, 620, 780, 650
SCRIPT_RATIO = 0.7                     # 위·아래첨자는 본문 글자의 약 0.7배
FRACTION_PAD = 450                     # 분수 가로줄 좌우 여유
SQRT_EXTRA = 800                       # 근호 기호 폭
WIDTH_SAFETY = 1.03                    # 어림이 모자라 뒤 글자와 겹치지 않게 두는 여유


def _token_width(token: str) -> int:
    if token in EQ_WORDS:
        return EQ_WORDS[token]
    if token in EQ_ROMAN:
        return 500 * len(token)
    if token in GREEK_NAMES or token.lower() in GREEK_NAMES:
        return EQ_UPPER if token.isupper() else EQ_LOWER
    if token[0].isdigit():
        return EQ_DIGIT * len(token.replace(".", "")) + (EQ_SYMBOLS["."] if "." in token else 0)
    if token[0].isalpha():
        return sum(EQ_UPPER if char.isupper() else EQ_LOWER for char in token)
    return EQ_SYMBOLS.get(token, EQ_SPACE.get(token, EQ_OTHER))


def _width_items(tokens: list[str], start: int, nested: bool = False) -> tuple[list[float], int]:
    """tokens[start:]를 닫는 } 앞까지 읽어 덩어리마다 너비를 낸다. (너비 목록, 다음 위치)
    맨 바깥(nested가 아님)의 짝 없는 }는 건너뛴다."""
    items: list[float] = []
    index = start
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token == "}":
            if nested:
                break
            continue
        if token in EQ_STYLES:
            continue
        if token == "{":
            inner, index = _width_items(tokens, index, True)
            items.append(sum(inner))
        elif token == "over" and items:
            following, index = _one_item(tokens, index)
            items[-1] = max(items[-1], following) + FRACTION_PAD
        elif token in ("^", "_"):
            following, index = _one_item(tokens, index)
            items.append(following * SCRIPT_RATIO)
        elif token == "sqrt":
            following, index = _one_item(tokens, index)
            items.append(following + SQRT_EXTRA)
        else:
            items.append(_token_width(token))
    return items, index


def _one_item(tokens: list[str], index: int) -> tuple[float, int]:
    """다음 덩어리 하나({...} 또는 낱말 하나)의 너비."""
    if index >= len(tokens):
        return 0.0, index
    if tokens[index] == "{":
        inner, index = _width_items(tokens, index + 1, True)
        return sum(inner), index
    return float(_token_width(tokens[index])), index + 1


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


def equation_xml(equation_id: int, script: str, color: str = DEFAULT_COLOR, bold: bool = False,
                 base_unit: int = EQUATION_BASE_UNIT) -> str:
    """글자처럼 취급하는(treatAsChar) 한글 수식 개체. script는 XML에 넣기 전의 수식 문법."""
    width = equation_width(script, base_unit)
    height = FRACTION_HEIGHT if re.search(r"\bover\b", script) else EQUATION_HEIGHT
    if bold:
        script = f"bold {{{script}}}"
    return (
        f'<hp:equation id="{equation_id}" zOrder="0" numberingType="EQUATION" textWrap="TOP_AND_BOTTOM" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" version="Equation Version 60" baseLine="66" '
        f'textColor="{color}" baseUnit="{base_unit}" lineMode="CHAR" font="HancomEQN">'
        f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" '
        'vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="{EQUATION_MARGIN}" right="{EQUATION_MARGIN}" top="0" bottom="0"/>'
        f'<hp:shapeComment>수식입니다.</hp:shapeComment><hp:script>{escape(script)}</hp:script></hp:equation>'
    )
