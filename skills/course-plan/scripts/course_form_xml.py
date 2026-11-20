"""학교 양식(hwpx) 채우기 도우미: 구역 XML을 문단·표·칸으로 나누고, 양식 칸을 복제해 글만 바꾼다.

양식의 문단 모양·글자 모양·테두리·열 너비는 그대로 두고 글과 행 수만 바꾼다. 줄 배치(linesegarray)는 빼서
한글이 다시 잡게 한다. 표 안에 표가 겹친 양식은 쓰지 않는다(기본 양식 두 개 모두 겹친 표가 없다).
"""

from __future__ import annotations

import html
import math
import re

from make_hwpx_text import _xml_text

ROW_RE = re.compile(r"<hp:tr>(.*?)</hp:tr>", re.S)
CELL_RE = re.compile(r"<hp:tc .*?</hp:tc>", re.S)
ADDR_RE = re.compile(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"/>')
LINESEG_RE = re.compile(r"<hp:linesegarray>.*?</hp:linesegarray>", re.S)
TOKEN_RE = re.compile(r"<hp:p |</hp:p>|<hp:tbl |</hp:tbl>")
CELL_PAD = 1020                  # 칸 왼쪽·오른쪽 안쪽 여백 합 (양식 칸 여백 510 × 2)
LINE_RATIO = 1.6                 # 글자 크기 대비 한 줄 높이 (줄 간격 160% 어림)
ROW_PAD = 600                    # 칸 위아래 여백과 여유
# 쪽 배치 어림 (HWPUNIT, 한글 2024 쪽 그림으로 맞춤): 표가 쪽 끝에서 머리행·소제목만 남기고 잘리지 않게 쓴다
HEADING_HEIGHT = 4500           # 절 제목 상자 문단
TITLE_HEIGHT = 3000             # 소제목 문단 ('1. 과제명', '가. …', '(1) 단원명')
GAP_HEIGHT = 1600               # 빈 줄
FIT_RATIO = 0.95                # 어림이 모자랄 때를 생각해 쪽 높이를 조금 줄여 잡는다


def xml_text(text: str) -> str:
    """XML에 넣을 글 (공용 생성기와 같게): 제어 문자를 지우고, 특수 문자를 바꾸고, 역슬래시는 전각으로,
    줄바꿈은 <hp:lineBreak/>로."""
    return _xml_text(text)


INNER_SPACE_RE = re.compile(r"<hp:(?:nbSpace|fwSpace|tab)[^>]*/>")


def plain(xml: str) -> str:
    """문단·칸의 글 (XML 이스케이프를 되돌린 글). 특수 공백은 빈칸, 줄바꿈 요소는 줄바꿈, 그 밖의 안쪽 요소는 뺀다."""
    texts = re.findall(r"<hp:t>(.*?)</hp:t>", xml, re.S)
    joined = "".join(re.sub(r"<[^>]+>", "", INNER_SPACE_RE.sub(" ", text).replace("<hp:lineBreak/>", "\n"))
                     for text in texts)
    return html.unescape(joined)


def first_table(xml: str) -> str:
    """xml(문단) 안 첫 바깥쪽 표. 없으면 빈 글."""
    spans = tables_in(xml)
    return xml[slice(*spans[0])] if spans else ""


# ---------------------------------------------------------------- 문단과 표 찾기

def top_paragraphs(xml: str) -> list[tuple[int, int]]:
    """구역 XML의 맨 위 문단(표 안 문단 제외)들의 (시작, 끝) 위치."""
    spans, depth_p, depth_t, start = [], 0, 0, 0
    for match in TOKEN_RE.finditer(xml):
        token = match.group(0)
        if token == "<hp:p ":
            if depth_p == 0 and depth_t == 0:
                start = match.start()
            depth_p += 1
        elif token == "</hp:p>":
            depth_p -= 1
            if depth_p == 0 and depth_t == 0:
                spans.append((start, match.end()))
        else:
            depth_t += 1 if token == "<hp:tbl " else -1
    return spans


def tables_in(xml: str) -> list[tuple[int, int]]:
    """xml 안 바깥쪽 표들의 (시작, 끝) 위치."""
    spans, depth, start = [], 0, 0
    for match in re.finditer(r"<hp:tbl |</hp:tbl>", xml):
        if match.group(0) == "<hp:tbl ":
            if depth == 0:
                start = match.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                spans.append((start, match.end()))
    return spans


def table_shape(table: str) -> tuple[int, int]:
    rows, cols = re.search(r'rowCnt="(\d+)" colCnt="(\d+)"', table).groups()
    return int(rows), int(cols)


def cell_map(table: str) -> dict[tuple[int, int], str]:
    """(열, 행) → 칸 XML."""
    found = {}
    for tc in CELL_RE.findall(table):
        col, row = ADDR_RE.search(tc).groups()
        found[(int(col), int(row))] = tc
    return found


def cell_paragraphs(tc: str) -> list[str]:
    return [tc[start:end] for start, end in top_paragraphs(tc)]     # 메모 안 문단(깊이 1)은 빼고 칸 문단만


def cell_width(tc: str) -> int:
    return int(re.search(r'<hp:cellSz width="(\d+)"', tc).group(1))


def cell_height(tc: str) -> int:
    return int(re.search(r'<hp:cellSz width="\d+" height="(\d+)"', tc).group(1))


# ---------------------------------------------------------------- 문단 만들기

def run_chars(paragraph: str) -> list[tuple[str, str]]:
    """문단의 (글자 모양 번호, 글) 목록."""
    return [(char, plain(body)) for char, body in
            re.findall(r'<hp:run charPrIDRef="(\d+)"(?:/>|>(.*?)</hp:run>)', paragraph, re.S)]


def first_char(paragraph: str) -> str:
    return re.search(r'<hp:run charPrIDRef="(\d+)"', paragraph).group(1)


def char_with(paragraph: str, needle: str) -> str | None:
    """글에 needle이 든 첫 실행(run)의 글자 모양 번호."""
    for char, text in run_chars(paragraph):
        if needle in text:
            return char
    return None


def para(template: str, runs: list[tuple[str, str]] | str, char: str | None = None) -> str:
    """template 문단 모양으로 새 문단. runs가 글이면 char(없으면 template 첫 글자 모양) 하나로 쓴다.

    쪽 나눔(pageBreak)과 줄 배치는 template에서 가져오지 않는다."""
    opening = re.match(r"<hp:p [^>]*>", template).group(0)
    opening = opening.replace('pageBreak="1"', 'pageBreak="0"')
    if isinstance(runs, str):
        runs = [(char or first_char(template), runs)]
    body = "".join(f'<hp:run charPrIDRef="{c}"><hp:t>{xml_text(t)}</hp:t></hp:run>' if t
                   else f'<hp:run charPrIDRef="{c}"/>' for c, t in runs)
    return f"{opening}{body}</hp:p>"


def lines_paras(templates: list[str], lines: list[str], char: str | None = None) -> list[str]:
    """줄마다 문단. i번째 줄은 templates[i] 모양(모자라면 마지막)."""
    lines = lines or [""]
    return [para(templates[min(i, len(templates) - 1)], line, char) for i, line in enumerate(lines)]


# ---------------------------------------------------------------- 칸과 표

def fill_cell(tc: str, paragraphs: list[str], *, col: int | None = None, row: int | None = None,
              colspan: int | None = None, rowspan: int | None = None,
              width: int | None = None, height: int | None = None) -> str:
    """양식 칸 tc의 글 문단을 paragraphs로 바꾸고, 주소·합침·크기를 고친 새 칸."""
    body = re.search(r"(<hp:subList [^>]*>).*(</hp:subList>)", tc, re.S)
    tc = tc[:body.start()] + body.group(1) + "".join(paragraphs) + body.group(2) + tc[body.end():]
    old_col, old_row = ADDR_RE.search(tc).groups()
    tc = ADDR_RE.sub(f'<hp:cellAddr colAddr="{old_col if col is None else col}" '
                     f'rowAddr="{old_row if row is None else row}"/>', tc, count=1)
    if colspan is not None:
        tc = re.sub(r'(<hp:cellSpan colSpan=")\d+', rf"\g<1>{colspan}", tc, count=1)
    if rowspan is not None:
        tc = re.sub(r'(<hp:cellSpan colSpan="\d+" rowSpan=")\d+', rf"\g<1>{rowspan}", tc, count=1)
    if width is not None:
        tc = re.sub(r'(<hp:cellSz width=")\d+', rf"\g<1>{width}", tc, count=1)
    if height is not None:
        tc = re.sub(r'(<hp:cellSz width="\d+" height=")\d+', rf"\g<1>{height}", tc, count=1)
    return tc


def text_cell(tc: str, lines: list[str] | str, char: str | None = None, **where) -> str:
    """양식 칸 모양 그대로 글만 바꾼 칸 (줄마다 문단, 양식 칸의 같은 순서 문단 모양)."""
    lines = lines.split("\n") if isinstance(lines, str) else lines
    return fill_cell(tc, lines_paras(cell_paragraphs(tc), lines, char), **where)


def build_table(base: str, rows: list[list[str]], heights: list[int], cols: int | None = None,
                width: int | None = None, page_break: str = "TABLE") -> str:
    """base 표의 머리(속성·위치·여백)에 새 행들을 넣은 표. 표 높이는 행 높이의 합.

    page_break: 쪽 경계에서 표를 나누는 법. TABLE은 행 단위(행 가운데가 갈라지지 않음), CELL은 칸 안 글까지
    나눔(양식 기본값, 키 큰 행이 두 쪽에 걸쳐 갈라짐), NONE은 나누지 않음 (한글 2024에서 확인)."""
    opening = re.match(r"<hp:tbl [^>]*>", base).group(0)
    opening = re.sub(r'rowCnt="\d+"', f'rowCnt="{len(rows)}"', opening)
    opening = re.sub(r'pageBreak="\w+"', f'pageBreak="{page_break}"', opening, count=1)
    if cols is not None:
        opening = re.sub(r'colCnt="\d+"', f'colCnt="{cols}"', opening)
    sizes = re.search(r"<hp:sz [^>]*/>.*?<hp:inMargin [^>]*/>", base, re.S).group(0)
    new_width = table_width(base) if width is None else width
    sizes = re.sub(r'(<hp:sz width=")\d+(" widthRelTo="\w+" height=")\d+',
                   lambda m: f"{m.group(1)}{new_width}{m.group(2)}{sum(heights)}", sizes, count=1)
    return opening + sizes + "".join(f"<hp:tr>{''.join(row)}</hp:tr>" for row in rows) + "</hp:tbl>"


RANGE_RE = re.compile(r"^\s*(\[[^\]]+\])\s*[~∼]\s*(\[[^\]]+\])\s*$")


def split_ranges(lines: list[str], alone: bool = False) -> list[str]:
    """'[A]~[B]' 줄을 '[A]', '~[B]'(alone이면 '[A]', '~', '[B]')로 나눈다. 좁은 칸에서 코드 중간이 끊기지 않게."""
    out = []
    for line in lines:
        found = RANGE_RE.match(line)
        if not found:
            out.append(line)
        elif alone:
            out += [found.group(1), "~", found.group(2)]
        else:
            out += [found.group(1), f"~{found.group(2)}"]
    return out


def table_width(table: str) -> int:
    return int(re.search(r'<hp:sz width="(\d+)"', table).group(1))


def table_height(table: str) -> int:
    return int(re.search(r'<hp:sz width="\d+" widthRelTo="\w+" height="(\d+)"', table).group(1))


def body_height(section: str) -> int:
    """쪽에서 본문이 차지하는 높이: 용지 높이 - 위·아래 여백 - 머리말·꼬리말 여백."""
    page = re.search(r'<hp:pagePr [^>]*>', section)
    margin = re.search(r'<hp:margin [^>]*/>', section)
    if not page or not margin:
        return 0
    size = dict(re.findall(r'(\w+)="(\w+)"', page.group(0)))
    long_side = "width" if size.get("landscape") == "NARROWLY" else "height"     # NARROWLY: 가로 용지
    taken = sum(int(re.search(f'{name}="(\\d+)"', margin.group(0)).group(1))
                for name in ("header", "footer", "top", "bottom"))
    return max(0, int(size.get(long_side, 0)) - taken)


def page_break_before(paragraph: str) -> str:
    """문단 앞에서 쪽을 나눈다 (문단 여는 태그의 pageBreak만 바꾼다. 표 안 문단은 건드리지 않는다)."""
    opening = re.match(r"<hp:p [^>]*>", paragraph).group(0)
    return opening.replace('pageBreak="0"', 'pageBreak="1"') + paragraph[len(opening):]


def split_widths(total: int, count: int) -> list[int]:
    """total을 count칸으로 나눈 정수 너비 (합이 total)."""
    base = total // count
    return [base + (1 if index < total - base * count else 0) for index in range(count)]


# ---------------------------------------------------------------- 높이 어림

def line_count(text: str, inner: int, size: int) -> int:
    """칸 안쪽 너비 inner에 글이 몇 줄로 들어갈지 (한글 1자 = 글자 크기, 그 밖 = 절반 남짓)."""
    total = 0
    text = re.sub("[\ue000-\ue00f]", "", text)                    # 형광펜·메모 표식 (course_form_marks.py)
    for line in text.split("\n"):
        units = sum(size if ord(ch) > 0x2E7F else size * 0.55 for ch in line)
        total += max(1, math.ceil(units / max(size, inner)))
    return total


def text_height(text: str, width: int, size: int = 900, minimum: int = 0) -> int:
    """칸 너비 width(바깥)에 text를 넣을 때 행 높이 어림 (HWPUNIT)."""
    lines = line_count(text, width - CELL_PAD, size)
    return max(minimum, round(lines * size * LINE_RATIO) + ROW_PAD)
