"""make_hwpx.py의 쪽 설정(여백·단·쪽 번호·용지 방향) 읽기. 표준 라이브러리만 쓴다."""

from __future__ import annotations

import re
from dataclasses import dataclass

from make_hwpx_shapes import PX
from make_hwpx_options import _choice, _int_option

PAGE_WIDTH = 59528                      # A4 너비 (HWPUNIT, 1mm ≈ 283.465)
PAGE_HEIGHT = 84186                     # A4 높이 (가로 용지일 때 본문 너비의 기준)
# 용지 방향: 한글은 세로를 WIDELY로, 가로를 NARROWLY로 저장하고 width/height는 세로 값 그대로 둔다
# (한글에서 쪽 설정을 가로로 바꿔 저장한 파일로 확인)
ORIENTATIONS = {"portrait": "WIDELY", "landscape": "NARROWLY"}
PAGE_NUMBER_PARA = {"center": "center", "right": "right"}   # 쪽 번호 위치: 꼬리말 문단 모양
# app: 앱 학습지 여백 48px(= 3600)에서 표 바깥 여백 283을 뺀 값. 표 가장자리가 앱 여백 선에 맞는다
# sheet: 학교 시험지 편집 용지(기본 원안지 양식과 같다) 왼쪽·오른쪽 10mm
SIDE_MARGINS = {"normal": 8504, "narrow": 4252, "app": 3317, "sheet": 2834}
SUPPORTED_COLUMNS = (1, 2)
PAGES = ("normal", "compact", "app", "sheet")
APP_TOP, APP_BOTTOM, APP_HEADER, APP_FOOTER = 3000, 3300, 0, 850    # 앱 위 40px, 꼬리말 자리
# 학교 시험지 편집 용지(A4, assessment-items/assets/exam_form.hwpx 원안지와 같다):
# 위 15mm, 아래 8mm, 머리말 0mm, 꼬리말 17mm, 제본 0mm. 좌우는 SIDE_MARGINS["sheet"]
SHEET_TOP, SHEET_BOTTOM, SHEET_HEADER, SHEET_FOOTER, SHEET_GUTTER = 4251, 2267, 0, 4818, 0


@dataclass(frozen=True)
class Layout:
    margin: int
    columns: int
    header_blocks: int
    column_line: bool
    page_numbers: str | None
    orientation: str
    page: str = "normal"

    @property
    def page_width(self) -> int:
        """본문 너비 계산에 쓰는 용지 가로 길이 (가로 용지면 A4 높이)."""
        return PAGE_HEIGHT if self.orientation == "landscape" else PAGE_WIDTH


def _layout_options(spec: dict) -> Layout:
    # 글자 옵션은 _choice로 읽는다: 대소문자 구분 없음, 값이 없으면(null·빈 글자) 기본값, 목록에 없으면 한글 오류
    margin = SIDE_MARGINS[_choice(spec.get("margins"), "margins", tuple(SIDE_MARGINS), "normal")]
    columns = _int_option(spec.get("columns", 1), "columns", min(SUPPORTED_COLUMNS), max(SUPPORTED_COLUMNS))
    header_blocks = _int_option(spec.get("header_blocks", 0), "header_blocks", 0, len(spec.get("blocks") or []))
    column_line = spec.get("column_line") or False
    if not isinstance(column_line, bool):
        raise ValueError(f"column_line은 true 또는 false여야 함 (받은 값: {column_line!r})")
    if column_line and columns < 2:
        raise ValueError("column_line(단 구분선)은 columns가 2일 때만 쓸 수 있음")
    page_numbers = _choice(spec.get("page_numbers"), "page_numbers", tuple(PAGE_NUMBER_PARA), None)
    orientation = _choice(spec.get("orientation"), "orientation", tuple(ORIENTATIONS), "portrait")
    page = _choice(spec.get("page"), "page", PAGES, "normal")
    if page == "sheet":         # 시험지 용지는 좌우 여백도 정해져 있다 (margins 값과 상관없이 10mm)
        margin = SIDE_MARGINS["sheet"]
    return Layout(margin, columns, header_blocks, column_line, page_numbers, orientation, page)


def compact_margins(sec_run: str) -> str:
    """위아래 여백을 좁힌다 (본문 위쪽 약 10mm, 아래쪽 약 11mm)."""
    sec_run = re.sub(r'header="\d+" footer="\d+"', 'header="850" footer="1134"', sec_run, count=1)
    return re.sub(r'top="\d+" bottom="\d+"/>', 'top="1984" bottom="1984"/>', sec_run, count=1)


def app_margins(sec_run: str) -> str:
    """앱 학습지 위아래 여백: 위 40px, 아래는 꼬리말(선 + 쪽수 칩) 자리까지."""
    sec_run = re.sub(r'header="\d+" footer="\d+"', f'header="{APP_HEADER}" footer="{APP_FOOTER}"', sec_run, count=1)
    return re.sub(r'top="\d+" bottom="\d+"/>', f'top="{APP_TOP}" bottom="{APP_BOTTOM}"/>', sec_run, count=1)


def sheet_margins(sec_run: str) -> str:
    """학교 시험지 편집 용지: 위 15mm, 아래 8mm, 머리말 0mm, 꼬리말 17mm, 제본 0mm (원안지와 같다)."""
    sec_run = re.sub(r'header="\d+" footer="\d+" gutter="\d+"',
                     f'header="{SHEET_HEADER}" footer="{SHEET_FOOTER}" gutter="{SHEET_GUTTER}"', sec_run, count=1)
    return re.sub(r'top="\d+" bottom="\d+"/>', f'top="{SHEET_TOP}" bottom="{SHEET_BOTTOM}"/>', sec_run, count=1)


def _paper_option(paper) -> dict | None:
    """종이 기준 배치: {"x": px, "y": px, "width": px}. 쪽 여백과 상관없이 종이 위 그 자리에 놓는다."""
    if paper is None:
        return None
    ok = isinstance(paper, dict) and all(
        not isinstance(paper.get(key), bool) and isinstance(paper.get(key), (int, float)) for key in ("x", "y", "width"))
    if not ok or paper["width"] <= 0:
        raise ValueError(f"paper는 x, y, width(px 숫자)가 든 객체여야 함 (받은 값: {paper!r})")
    return paper


PAPER_WRAPS = {"top_bottom": "TOP_AND_BOTTOM", "front": "IN_FRONT_OF_TEXT", "behind": "BEHIND_TEXT"}


def _table_wrap(paper: dict | None) -> str:
    """종이 기준 표의 글 감싸기: 위아래(본문이 아래로 밀림), 글 앞(본문을 밀지 않음), 글 뒤."""
    return PAPER_WRAPS[_choice((paper or {}).get("wrap"), "paper.wrap", tuple(PAPER_WRAPS), "top_bottom")]


def _gap_px(value) -> tuple[int, int] | None:
    """표 위·아래 바깥 여백(px). 숫자 하나는 위아래 같게, [위, 아래]도 된다. 없으면 None."""
    if value is None:
        return None
    pair = [value, value] if not isinstance(value, (list, tuple)) else list(value)
    if len(pair) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 400 for v in pair):
        raise ValueError(f"gap_px는 0~400 사이 px 숫자 또는 [위, 아래] 이어야 함 (받은 값: {value!r})")
    return round(pair[0] * PX), round(pair[1] * PX)


def _table_position(inline: bool, paper: dict | None) -> str:
    if paper:
        return ('<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="0" '
                f'vertRelTo="PAPER" horzRelTo="PAPER" vertAlign="TOP" horzAlign="LEFT" '
                f'vertOffset="{round(paper["y"] * PX)}" horzOffset="{round(paper["x"] * PX)}"/>')
    return (f'<hp:pos treatAsChar="{int(inline)}" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
            'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" '
            'vertOffset="0" horzOffset="0"/>')


def _width_px(width_px, table_width: int) -> int:
    """표 너비. width_px(px)가 있으면 본문보다 좁은 표(예: 앱 학습지의 왼쪽 본문 칸)가 된다."""
    if width_px is None:
        return table_width
    if isinstance(width_px, bool) or not isinstance(width_px, (int, float)) or not 10 <= width_px <= 2000:
        raise ValueError(f"width_px는 10~2000 사이 px 숫자여야 함 (받은 값: {width_px!r})")
    return min(round(width_px * PX), table_width)
