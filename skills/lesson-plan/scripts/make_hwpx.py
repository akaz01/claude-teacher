"""한글(hwpx) 문서 생성기. 표준 라이브러리만 쓴다.

입력 JSON 형식:
{
  "title": "문서 제목 (선택, 맨 위 가운데 큰 글씨)",
  "doc_title": "문서 정보의 제목 (선택, 본문에는 안 보임. 없으면 title, 그다음 첫 heading)",
  "margins": "normal",            # normal(좌우 30mm) 또는 narrow(좌우 15mm, 넓은 표가 있을 때)
  "columns": 1,                   # 1단 또는 2단 (시험지). 2단이면 표 너비가 한 단에 맞춰짐
  "header_blocks": 0,             # 2단일 때 제목 뒤 몇 개 블록까지 1단(전체 너비)으로 둘지 (예: 이름 칸 표 1개)
  "column_line": false,           # true면 2단 사이에 세로 구분선 (columns가 2일 때만)
  "notes": [],                    # 만들며 돌려줄 경고 글 목록 (스킬 생성기가 어림 높이 경고를 넘길 때)
  "page_numbers": null,           # "center" 또는 "right": 꼬리말에 "1 / 4" 꼴 쪽 번호 (쪽 / 전체 쪽)
  "page": "normal",                # normal, compact(위아래 여백을 좁힘), sheet(학교 시험지 용지 = 원안지: 위 15mm,
                                  #  아래 8mm, 좌·우 10mm, 머리말 0mm, 꼬리말 17mm, 제본 0mm. 정답·문항정보표. margins는 무시)
  "orientation": "portrait",      # portrait(세로) 또는 landscape(가로 A4, 표가 가로 너비에 맞춰짐)
  "blocks": [
    {"type": "heading", "text": "1. 개요", "level": 1},          # level 1~6 (1은 큰 글씨, 2~6은 같은 작은 글씨)
    {"type": "paragraph", "text": "**굵게** 쓸 부분은 별표 두 개로", "align": "justify"},
                                                                 # {{2/3}}, {{1 7/12}}는 한글 수식(분수)으로 들어감
                                                                 #  (모든 글자에서 됨. 안쪽은 한글 수식 문법, 숫자/숫자는 분수,
                                                                 #  x^2+1처럼 ^·_ 뒤 낱말은 자동으로 {}로 묶임, 한글이나 \는 쓰지 않음)
                                                                 #  수식은 둘러싼 글자의 색·굵기를 따른다
                                                                 # align: justify/left/center/right
                                                                 # size: small/normal/large/xlarge (선택)
                                                                 # __밑줄__은 굵게+밑줄 (회신 기한 강조)
                                                                 # "keep_with_next": true면 다음 블록과 같은 쪽·단에 둠 (문제 문장)
    {"type": "outline", "items": [{"text": "목적", "level": 1}, {"text": "세부", "level": 2}]},
                                                                 # 공문서 항목 기호 1. 가. 1) 가) (1) (가) 자동
                                                                 # "start": 2 이면 2.부터 (표 뒤에 이어 쓸 때)
    {"type": "bullets", "items": ["항목", "항목"]},             # 항목은 글자 또는 {"text": ...} (null 항목은 오류)
    {"type": "numbered", "items": ["첫째", "둘째"]},             # "start": 3 이면 3.부터 (표 뒤에 이어 쓸 때)
    {"type": "table", "header": ["구분", "내용"], "rows": [["일시", "11. 10.(화)"]], "widths": [1, 3]},
                                                                 # 셀 안 줄바꿈은 \n, widths는 열 너비 비율(선택)
                                                                 # 칸은 글자 또는 {"text", "rowspan", "colspan",
                                                                 #  "shade", "bold", "align", "valign", "lines"}
                                                                 # 합쳐서 가려지는 칸은 행에서 뺀다 (HTML 표와 같음)
                                                                 # "header_rows": header 아래에 더할 머리행 수(음영), "border": "none" 테두리 없음
                                                                 # "keep_with_next": true면 다음 블록(선지)과 같은 쪽·단에 둠
                                                                 # 높이 약 53mm 이하의 짧은 표, 머리행이 있는 106mm 이하 표,
                                                                 #  행이 하나인 141mm 이하 표(빈 풀이 칸)는 쪽을 넘어 나뉘지 않고 통째로 옮겨진다
                                                                 #  더 긴 표는 행 단위로 나뉘고(머리행은 쪽마다 반복), 쪽보다 큰 행은 칸 안에서 나뉜다
                                                                 # valign: top/center/bottom, 칸 "header": true면 머리칸 음영
                                                                 # 칸 색·테두리는 make_hwpx_design.py, 표 "gap": normal|small|tight는 위아래 간격
    {"type": "stem", "number": 1, "text": "문두", "points": 3.2},   # 문제지 문두: 둘째 줄 내어쓰기(기준선), 배점은 마지막 낱말에 묶음 빈칸으로 붙음
    {"type": "choices", "items": ["가", "나", "다", "라", "마"], "layout": "auto"},
                                                                 # 문제지 선지(①은 자동): 테두리 없는 표, ①이 기준선에서 시작. layout: 1x5(한 줄 5칸),
                                                                 #  2x3(3+2), 5x1(한 줄에 하나), auto(가장 긴 선지로 고름). 두 줄 선지는 ① 뒤 글에 맞춤
    {"type": "box", "label": "<보 기>", "paragraphs": ["ㄱ. 진술", "ㄴ. 진술"]},   # 자료·<보기> 상자: 기준선에서 단 끝까지 (make_hwpx_exam.py)
    {"type": "answer_box", "lines": 3},                          # 학생 답 쓰는 빈 칸
    {"type": "blank"},                                           # 빈 줄
    {"type": "page_break"}                                       # 다음 블록부터 새 쪽
  ]
}

사용법:
    python make_hwpx.py 입력.json 출력.hwpx
    python make_hwpx.py --check 파일.hwpx        # 기존 hwpx 구조 검사

골격 파일 make_hwpx_skeleton.hwpx 는 python-hwpx(Apache-2.0)의 Skeleton.hwpx 이다.
라이선스: make_hwpx_LICENSE.txt, make_hwpx_NOTICE.txt
"""

from __future__ import annotations

import itertools
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import quoteattr

from make_hwpx_equation import (
    DEFAULT_COLOR, EQUATION_MARGIN, equation_preview, equation_script, equation_text_warnings, equation_width,
    equation_xml, split_equations)
from make_hwpx_layout import (  # noqa: F401  (PAGE_WIDTH 등은 여기서도 쓸 수 있게 다시 내보냄)
    ORIENTATIONS, PAGE_HEIGHT, PAGE_NUMBER_PARA, PAGE_WIDTH, SIDE_MARGINS, SUPPORTED_COLUMNS, Layout,
    _layout_options, app_margins, compact_margins, sheet_margins,
    _gap_px, _paper_option, _table_position, _table_wrap, _width_px)
from make_hwpx_design import (
    DOT_MARKS, RUN_SIZE, WIDE_DOT_FONTS, blank_style, plain_dot_style, border_fill_xml, char_look, char_style, collect_designs, item_look_key, marked_style)
from make_hwpx_design import _border_fill, _margin, _para_pr  # noqa: E402,F401  (헤더 XML 조각: 디자인 모듈에 둠)
from make_hwpx_shapes import PX, read_shape, shape_xml
from make_hwpx_text import BACKSLASH_FOR_HANGUL_FONTS, _clean, _xml_text, as_text, update_metadata, _outline_marker  # noqa: F401  (여기서도 쓸 수 있게 다시 내보냄)
from make_hwpx_cells import (  # noqa: F401  (표 칸 모양·크기 어림. 여기서도 쓸 수 있게 다시 내보냄)
    ANSWER_LINE_HEIGHT, CELL_ALIGNS, CELL_FULL_CHAR_WIDTH, CELL_HALF_CHAR_WIDTH, CELL_LINE_HEIGHT, CELL_MARGIN_X,
    CELL_MARGIN_Y, CELL_PADDING_X, CELL_PADDING_Y, CELL_VALIGNS, MAX_LINES, ROW_HEIGHT, MAX_SPAN, MAX_TABLE_COLS, MAX_TABLE_ROWS,
    TableCell, _estimated_rows, _make_cell, _row_heights, _span, _split_width, _text_lines, layout_table)
from make_hwpx_options import (  # noqa: F401
    _bool_option, _choice, _int_option, _item_spec, _list_or_empty, _start_option, _validate_spec)
from make_hwpx_exam import EXAM_PARA_STYLES, exam_handlers
from make_hwpx_lint import date_warnings, wide_words, with_auto_keep
from make_hwpx_check import LANG_ATTRS, MIMETYPE, refuse_foreign_target, validate_package  # noqa: F401  (validate_package는 여기서도 쓸 수 있게 다시 내보냄)
from make_hwpx_save import OWN_FILES_ONLY, hwpx_check, save_atomically

SKELETON = Path(__file__).with_name("make_hwpx_skeleton.hwpx")
FONT_FACE = "맑은 고딕"
# 칸·도형 글자의 font 값 → 글꼴 이름 (한컴오피스에 기본으로 들어 있는 글꼴만)
EXTRA_FACES = {"serif": "함초롬바탕", "myeongjo": "HY견명조", "headline": "HY헤드라인M"}
FOOTER_HEIGHT = 4252                    # 골격의 꼬리말 여백 15mm
COLUMN_LINE = '<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/>'   # 단 구분선 0.12mm 실선
COLUMN_GAP = 2268                       # 2단 편집 단 사이 간격 8mm
TABLE_OUT_MARGIN = 283
TABLE_OUT_MARGIN_V = 850                # 표 위아래 바깥 여백 3mm (제목이 표에 붙지 않게)
TABLE_GAPS = {"normal": TABLE_OUT_MARGIN_V, "small": 340, "tight": 0}
# 이보다 낮은 표는 글자처럼 취급해 앞 문단(문제)과 같은 쪽에 놓는다. 더 긴 표는 떠 있게 두어 쪽을 넘어 나눈다
# (글자처럼 취급한 표는 한글에서 쪽을 넘어 나뉘지 않는다. 한글에서 확인)
INLINE_TABLE_MAX_HEIGHT = 15000         # 약 53mm, 기본 행 높이로 8행 정도
# 행이 하나인 표(빈 풀이 칸 등)는 쪽 끝에서 쪼개지면 안 되고, 머리행이 있는 표는 머리행만 쪽 끝에 남으면 안 된다
# (한글은 머리행을 첫 행과 묶지 못한다). 그래서 쪽 높이의 절반 안쪽까지는 통째로 옮긴다
INLINE_ONE_ROW_MAX_HEIGHT = 40000       # 약 141mm
INLINE_HEADED_TABLE_MAX_HEIGHT = 30000  # 약 106mm
# 한 행이 쪽보다 크면 pageBreak="TABLE"에서 넘치는 내용이 사라진다 (한글에서 확인). 그런 표는 칸 안에서도 나눈다
ROW_SPLIT_LIMIT = 30000
SKELETON_SECTION_ERROR = "골격 section0.xml 형식이 예상과 다름"
BORDERS = ("solid", "none")
EQUATION_SHOWN = 20                     # 경고에 보여 줄 수식 글자 수
PREVIEW_LIMIT = 1024

# 이름: (글자 크기 1/100pt, 굵게, 밑줄)
CHAR_STYLES = {
    "body": (1100, False, False), "bold": (1100, True, False), "body_ul": (1100, True, True),
    "title": (1800, True, False), "h1": (1400, True, False), "h2": (1200, True, False),
    "cell": (1000, False, False), "cell_bold": (1000, True, False), "cell_ul": (1000, True, True),
    "small": (900, False, False), "small_bold": (900, True, False),
    "large": (1400, False, False), "large_bold": (1400, True, False),
    "xlarge": (1800, False, False), "xlarge_bold": (1800, True, False),
    "spacer": (100, False, False),
}
BOLD_OF = {"body": "bold", "cell": "cell_bold", "small": "small_bold", "large": "large_bold", "xlarge": "xlarge_bold"}
UNDERLINE_OF = {"body": "body_ul", "cell": "cell_ul"}   # __밑줄__은 굵게+밑줄 (회신 기한 강조용)
SIZE_TO_CHAR = {"small": "small", "normal": "body", "large": "large", "xlarge": "xlarge"}
OUTLINE_LEVELS = 6
OUTLINE_INDENT = 1200                   # 항목 번호 한 단계당 왼쪽 들여쓰기
# 이름: (정렬, 줄 간격 %, 문단 위, 문단 아래, 왼쪽 여백, 다음 문단과 함께[, 내어쓰기])
# 내어쓰기는 "• ", "1. ", "10. " 같은 글머리 폭(11pt 본문, 한글 2024 화면에서 픽셀로 잼). 두 줄로 넘어간 항목의 둘째 줄이 글 시작에 맞춰진다
ITEM_HANG = {"bullet": 1000, "num1": 1000, "num2": 1600}
PARA_STYLES = {
    "body": ("JUSTIFY", 160, 0, 300, 0, False), "left": ("LEFT", 160, 0, 300, 0, False),
    "center": ("CENTER", 160, 0, 300, 0, False), "right": ("RIGHT", 160, 0, 300, 0, False),
    "title": ("CENTER", 160, 0, 800, 0, False), "heading": ("LEFT", 160, 600, 300, 0, True),
    "item": ("LEFT", 160, 0, 150, 1000, False, ITEM_HANG["bullet"]),
    "item_num1": ("LEFT", 160, 0, 150, 1000, False, ITEM_HANG["num1"]),
    "item_num2": ("LEFT", 160, 0, 150, 1000, False, ITEM_HANG["num2"]),
    "spacer": ("LEFT", 100, 0, 0, 0, False), "chip": ("CENTER", 100, 0, 0, 0, False),
    "anchor": ("LEFT", 100, 0, 0, 0, False),
    "cell": ("LEFT", 130, 0, 0, 0, False), "cell_center": ("CENTER", 130, 0, 0, 0, False),
    "cell_right": ("RIGHT", 130, 0, 0, 0, False),
    **{f"outline{level}": ("LEFT", 160, 0, 150, (level - 1) * OUTLINE_INDENT, False)
       for level in range(1, OUTLINE_LEVELS + 1)},
}
# "keep_with_next": true인 문단용: 다음 문단(선지, 자료 표)과 같은 쪽·단에 놓인다
PARA_STYLES.update({f"{name}_keep": PARA_STYLES[name][:5] + (True,) for name in ("body", "left", "center", "right")})
PARA_STYLES.update(EXAM_PARA_STYLES)          # 문제지 블록(stem, choices, box)용 문단 모양: make_hwpx_exam.py
ALIGN_TO_PARA = {"justify": "body", "left": "left", "center": "center", "right": "right"}
HEADER_FILL_COLOR = "#D9D9D9"

TYPE_INFO = ('<hh:typeInfo familyType="FCAT_GOTHIC" weight="6" proportion="4" contrast="0" '
             'strokeVariation="1" armStyle="1" letterform="1" midline="1" xHeight="1"/>')
LANG_VALUES = 'hangul="{v}" latin="{v}" hanja="{v}" japanese="{v}" other="{v}" symbol="{v}" user="{v}"'


# ---------------------------------------------------------------- header.xml

def _char_pr(char_id: int, style: tuple, font_id: int, shade: str | None = None, ratio: int = 100,
             track: int = 0, font_space: bool = False) -> str:
    height, bold, underline = style
    return (
        f'<hh:charPr id="{char_id}" height="{height}" textColor="#000000" shadeColor="{shade or "none"}" '
        f'useFontSpace="{int(font_space)}" useKerning="0" symMark="NONE" borderFillIDRef="2">'
        f'<hh:fontRef {LANG_VALUES.format(v=font_id)}/><hh:ratio {LANG_VALUES.format(v=ratio)}/>'
        f'<hh:spacing {LANG_VALUES.format(v=track)}/><hh:relSz {LANG_VALUES.format(v=100)}/>'
        f'<hh:offset {LANG_VALUES.format(v=0)}/>{"<hh:bold/>" if bold else ""}'
        f'<hh:underline type="{"BOTTOM" if underline else "NONE"}" shape="SOLID" color="#000000"/>'
        '<hh:strikeout shape="NONE" color="#000000"/>'
        '<hh:outline type="NONE"/><hh:shadow type="NONE" color="#C0C0C0" offsetX="10" offsetY="10"/></hh:charPr>'
    )


def _next_id(header: str, item_tag: str) -> int:
    ids = [int(found) for found in re.findall(rf'<hh:{item_tag} id="(\d+)"', header)]
    return max(ids, default=-1) + 1


def _append_items(header: str, container: str, items: list[str]) -> str:
    opening = re.search(rf'<hh:{container} itemCnt="(\d+)">', header)
    if not opening:
        raise ValueError(f"골격 header.xml에 {container}가 없음")
    count = int(opening.group(1)) + len(items)
    header = f'{header[:opening.start()]}<hh:{container} itemCnt="{count}">{header[opening.end():]}'
    closing = header.index(f"</hh:{container}>")
    return header[:closing] + "".join(items) + header[closing:]


def _add_font(header: str) -> tuple[str, dict]:
    """모든 언어 글꼴 그룹에 맑은 고딕과 EXTRA_FACES 글꼴을 더한다. (header, {글꼴 값: 번호}), 맑은 고딕은 None 키."""
    group = re.compile(r'(<hh:fontface lang="[A-Z]+" fontCnt=")(\d+)(">)(.*?)(</hh:fontface>)', re.S)
    new_ids: list[int] = []
    faces = (FONT_FACE, *EXTRA_FACES.values())

    def add(match: re.Match) -> str:
        font_id = int(match.group(2))
        new_ids.append(font_id)
        fonts = "".join(f'<hh:font id="{font_id + offset}" face="{face}" type="TTF" isEmbedded="0">{TYPE_INFO}</hh:font>'
                        for offset, face in enumerate(faces))
        return f"{match.group(1)}{font_id + len(faces)}{match.group(3)}{match.group(4)}{fonts}{match.group(5)}"

    header = group.sub(add, header)
    if len(new_ids) != len(LANG_ATTRS) or len(set(new_ids)) != 1:
        raise ValueError("골격의 글꼴 그룹 구성이 예상과 다름")
    return header, {None: new_ids[0], **{name: new_ids[0] + 1 + index for index, name in enumerate(EXTRA_FACES)}}


@dataclass(frozen=True)
class Styles:
    char: dict
    para: dict
    border: int
    header_border: int
    no_border: int
    design_border: dict | None = None


SPACED_PARAS = ("cell", "cell_center", "cell_right")      # 줄 간격을 칸마다 정할 수 있는 문단 모양


def _spaced_para_styles(spacings: list[int]) -> dict:
    return {f"{name}@{spacing}": PARA_STYLES[name][:1] + (spacing,) + PARA_STYLES[name][2:]
            for spacing in spacings for name in SPACED_PARAS}


def prepare_header(header: str, spec: dict | None = None) -> tuple[str, Styles]:
    header, font_ids = _add_font(header)
    char_start, para_start = _next_id(header, "charPr"), _next_id(header, "paraPr")
    border_start = _next_id(header, "borderFill")
    design_borders, design_chars, design_spacings = collect_designs(spec)
    para_styles = {**PARA_STYLES, **_spaced_para_styles(design_spacings)}
    styles = Styles(
        char={name: char_start + i for i, name in enumerate([*CHAR_STYLES, *design_chars])},
        para={name: para_start + i for i, name in enumerate(para_styles)},
        border=border_start, header_border=border_start + 1, no_border=border_start + 2,
        design_border={key: border_start + 3 + i for i, key in enumerate(design_borders)},
    )
    header = _append_items(header, "borderFills", [
        _border_fill(styles.border, None), _border_fill(styles.header_border, HEADER_FILL_COLOR),
        _border_fill(styles.no_border, None, line_type="NONE"),
        *(border_fill_xml(styles.design_border[key], key) for key in design_borders)])
    header = _append_items(header, "charProperties", [
        *(_char_pr(styles.char[name], style, font_ids[None]) for name, style in CHAR_STYLES.items()),
        *(_design_char_pr(styles.char[key], key, font_ids) for key in design_chars)])
    header = _append_items(header, "paraProperties", [
        _para_pr(styles.para[name], style) for name, style in para_styles.items()])
    return header, styles


def _design_char_pr(char_id: int, key: str, font_ids: dict) -> str:
    look = char_look(key)
    return _char_pr(char_id, (look.height, look.bold, look.underline), font_ids[look.font],
                    look.shade, look.ratio, look.spacing, look.font_space).replace('textColor="#000000"', f'textColor="{look.color}"', 1)


# ---------------------------------------------------------------- section0.xml

# 영문·숫자에 붙은 짝(snake__case__name, 2**3**4)은 표기가 아니다. 한글 조사가 붙은 **도시락**과 는 표기다
_NOT_WORD_BEFORE = r"(?<![A-Za-z0-9])"
_NOT_WORD_AFTER = r"(?![A-Za-z0-9])"
MARKUP = re.compile(
    rf"{_NOT_WORD_BEFORE}\*\*(.+?)\*\*{_NOT_WORD_AFTER}|{_NOT_WORD_BEFORE}__(.+?)__{_NOT_WORD_AFTER}", re.S)
# 칸 글 속 ~~빈칸~~ (음영 + 밑줄)까지 읽는 표기. 칸에서만 쓴다
BLANK_MARKUP = re.compile(MARKUP.pattern + r"|~~(.+?)~~", re.S)


def _equation_look(style: str) -> tuple[str, bool]:
    """글자 모양 이름에서 수식의 (글자색, 굵게 여부). 칸·표시 색이 있으면 수식도 그 색을 따른다."""
    if style in CHAR_STYLES:
        return DEFAULT_COLOR, CHAR_STYLES[style][1]
    (_, bold, _), color = char_style(style)
    return color, bold


def plain_text(value) -> str:
    """미리 보기·문서 정보용 글: **굵게**·__밑줄__ 표기를 떼고 {{2/3}}은 2/3으로."""
    return equation_preview(MARKUP.sub(lambda m: m.group(1) or m.group(2), as_text(value)))


def _inline_limit(row_count: int, has_header: bool) -> int:
    """이 높이 이하인 표는 글자처럼 취급해 쪽을 넘어 나뉘지 않고 통째로 옮겨진다."""
    if row_count == 1:
        return INLINE_ONE_ROW_MAX_HEIGHT
    return INLINE_HEADED_TABLE_MAX_HEIGHT if has_header else INLINE_TABLE_MAX_HEIGHT


def _item_texts(block: dict) -> list[str]:
    """bullets·numbered 항목 글 (outline과 같이 {"text": ...} 객체도 받는다)."""
    items = _list_or_empty(block.get("items"), "items")
    return [as_text(_item_spec(item, number)["text"]) for number, item in enumerate(items, 1)]


class SectionWriter:
    def __init__(self, styles: Styles, body_width: int, app: bool = False):
        self.styles = styles
        self.app = app                      # 앱 학습지: 표를 줄 간격·문단 아래 간격 없는 문단에 놓아 간격을 gap_px로만 정한다
        self.table_width = body_width - 2 * TABLE_OUT_MARGIN
        self.preview: list[str] = []
        self.warnings: list[str] = []
        self._room: int | None = None       # 지금 쓰는 칸 안쪽 너비 (칸 밖이면 None: 본문 너비)
        self._para_ids = itertools.count(1)
        self._table_ids = itertools.count(1)
        self._page_break_pending = False
        self._handlers = {
            "heading": self._heading, "paragraph": self._paragraph_block, "outline": self._outline_block,
            "bullets": self._bullets, "numbered": self._numbered, "table": self._table_block,
            "answer_box": self._answer_box, "blank": self._blank, "page_break": self._request_page_break,
            "shape": self._shape_block,
            **exam_handlers(self, lambda: self.table_width + 2 * TABLE_OUT_MARGIN),
        }

    def runs(self, text, char: str = "body", blank_fill: str | None = None) -> str:
        """**굵게**와 __굵게+밑줄__ 표기를 글자 모양별 run으로 나눈다. blank_fill이 있으면 ~~빈칸~~도 읽는다."""
        text = as_text(text)
        pieces: list[tuple[str, str]] = []
        position = 0
        for match in (BLANK_MARKUP if blank_fill else MARKUP).finditer(text):
            pieces.append((text[position:match.start()], char))
            if len(match.groups()) > 2 and match.group(3) is not None:
                pieces.append((match.group(3), blank_style(char, blank_fill)))
            elif match.group(1) is not None:
                pieces.append((match.group(1), marked_style(char) or BOLD_OF.get(char, char)))
            else:
                pieces.append((match.group(2), UNDERLINE_OF.get(char, BOLD_OF.get(char, char))))
            position = match.end()
        pieces.append((text[position:], char))
        runs = [self._styled_runs(part, style) for part, style in pieces if part]
        return "".join(runs) or f'<hp:run charPrIDRef="{self.styles.char[char]}"><hp:t/></hp:run>'

    def _equation_run(self, part: str, style: str, char_id: int) -> str:
        """{{수식}} 하나를 글자처럼 취급하는 수식 run으로. 글자색·굵기는 둘러싼 글자 모양을 따른다."""
        script = equation_script(_clean(part))
        self._check_equation_width(script)
        color, bold = _equation_look(style)
        return (f'<hp:run charPrIDRef="{char_id}">'
                f'{equation_xml(next(self._table_ids), script, color, bold)}<hp:t/></hp:run>')

    def _check_equation_width(self, script: str) -> None:
        room = self.table_width + 2 * TABLE_OUT_MARGIN if self._room is None else self._room
        if equation_width(script) + 2 * EQUATION_MARGIN <= room:
            return
        where = "칸" if self._room is not None else "줄"
        self.warnings.append(
            f"주의: 수식 {{{{{script[:EQUATION_SHOWN]}…}}}}이 {where}보다 길어 잘리거나 쪽 밖으로 나갈 수 있음 "
            f"→ 수식이 든 칸은 넓게 하거나 수식을 둘로 나누세요")

    def _styled_runs(self, text: str, style: str) -> str:
        """한 글자 모양의 글을 run으로. {{수식}}은 글자처럼 취급하는 수식 run (id는 표와 같은 번호 줄)."""
        char_id = self.styles.char[style]
        if style.startswith("design:") and char_look(style).font in WIDE_DOT_FONTS:
            plain = plain_dot_style(style)
            return "".join(self._plain_runs(piece, plain, self.styles.char[plain]) if piece in tuple(DOT_MARKS)
                           else self._plain_runs(piece, style, char_id)
                           for piece in re.split(f"([{DOT_MARKS}])", text) if piece)
        return self._plain_runs(text, style, char_id)

    def _plain_runs(self, text: str, style: str, char_id: int) -> str:
        return "".join(
            self._equation_run(part, style, char_id) if is_equation
            else f'<hp:run charPrIDRef="{char_id}"><hp:t>{_xml_text(part)}</hp:t></hp:run>'
            for part, is_equation in split_equations(text))

    def outline(self, items: list, start: object = 1) -> str:
        """공문서 항목 기호: 1. → 가. → 1) → 가) → (1) → (가). 상위 번호가 바뀌면 하위 번호는 다시 시작.

        start: 첫 1단계 번호 (표 등으로 끊긴 목록을 이어 쓸 때)."""
        start = _start_option(start, "outline")
        items = _list_or_empty(items, "items")
        counters = [start - 1] + [0] * (OUTLINE_LEVELS - 1)
        rendered = []
        for number, item in enumerate(items, 1):
            spec = _item_spec(item, number)
            level = 1 if spec.get("level") is None else _int_option(
                spec["level"], f"items의 {number}번째 항목 level", 1, OUTLINE_LEVELS)
            counters[level - 1] += 1
            counters[level:] = [0] * (OUTLINE_LEVELS - level)
            marker = _outline_marker(level, counters[level - 1])
            rendered.append(self.text_paragraph(f"{marker} {as_text(spec.get('text'))}", f"outline{level}"))
        return "".join(rendered)

    def paragraph(self, runs: str, para: str = "body", in_cell: bool = False) -> str:
        page_break = self._page_break_pending and not in_cell
        if not in_cell:
            self._page_break_pending = False
        return (f'<hp:p id="{next(self._para_ids)}" paraPrIDRef="{self.styles.para[para]}" styleIDRef="0" '
                f'pageBreak="{int(page_break)}" columnBreak="0" merged="0">{runs}</hp:p>')

    def text_paragraph(self, text, para: str = "body", char: str = "body") -> str:
        self.preview.append(_clean(plain_text(text)))
        return self.paragraph(self.runs(text, char), para)

    def _cell_runs(self, cell: "TableCell", char: str) -> str:
        """칸 글 run. content가 있으면 글과 도형을 차례로 놓고, 없으면 text 하나."""
        shade = self._blank_shade(cell)
        if not cell.content:
            return self.runs(cell.text, char, shade)
        return "".join(self._content_run(item, char, shade) for item in cell.content)

    def _blank_shade(self, cell: "TableCell") -> str | None:
        """~~빈칸~~을 읽는 칸이면 빈칸 음영색. 앱 학습지(page "app")나 칸이 "blank": true로 켠 경우만 읽는다."""
        if cell.design and "~~" in cell.text and (self.app or cell.design.blank):
            return cell.design.blank_fill
        return None

    def _content_run(self, item, char: str, shade: str | None) -> str:
        if isinstance(item, str):
            return self.runs(item, char, shade)
        if "run" in item:
            return self.runs(item["run"], item_look_key(item, RUN_SIZE), shade)
        return self._shape_run(item)

    def _shape_run(self, shape: dict) -> str:
        """글자처럼 취급하는 도형(글상자) 하나를 담은 run."""
        key = item_look_key(shape)
        runs = (self._page_number_runs(key) if shape.get("page_number")
                else self.runs(shape["text"], key) if shape.get("text") else self.runs("", "spacer"))
        paragraph = self.paragraph(runs, "chip", in_cell=True)
        return (f'<hp:run charPrIDRef="{self.styles.char["spacer"]}">'
                f'{shape_xml(shape, next(self._table_ids), paragraph)}<hp:t/></hp:run>')

    def _cell(self, cell: "TableCell", width: int, height: int, default_valign: str, plain: bool = False) -> str:
        design = cell.design
        design_key = design.border_key if design else None
        border = (self.styles.design_border[design_key] if design_key
                  else self.styles.header_border if cell.shade
                  else self.styles.no_border if plain else self.styles.border)
        para = {"center": "cell_center", "right": "cell_right"}.get(cell.align, "cell")
        if design and design.spacing:
            para = f"{para}@{design.spacing}"
        has_blank = self._blank_shade(cell) is not None
        char = (design.char_key(cell.bold, force=has_blank) if design else None) or ("cell_bold" if cell.bold else "cell")
        left, right, top, bottom = ([round(value * PX) for value in design.pad] if design and design.pad
                                    else [CELL_MARGIN_X, CELL_MARGIN_X, CELL_MARGIN_Y, CELL_MARGIN_Y])
        self._room = width - left - right
        try:
            content = self.paragraph(self._cell_runs(cell, char), para, in_cell=True)
        finally:
            self._room = None
        valign = quoteattr((cell.valign or default_valign).upper())
        return (
            f'<hp:tc name="" header="{int(cell.header)}" hasMargin="{int(bool(design and design.pad))}" protect="0" '
            f'editable="0" dirty="0" '
            f'borderFillIDRef="{border}"><hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
            f'vertAlign={valign} linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" '
            f'hasTextRef="0" hasNumRef="0">{content}</hp:subList>'
            f'<hp:cellAddr colAddr="{cell.col}" rowAddr="{cell.row}"/>'
            f'<hp:cellSpan colSpan="{cell.colspan}" rowSpan="{cell.rowspan}"/>'
            f'<hp:cellSz width="{width}" height="{height}"/>'
            f'<hp:cellMargin left="{left}" right="{right}" top="{top}" bottom="{bottom}"/></hp:tc>'
        )

    def table(self, header: list | None, rows: list, widths: list | None = None,
              row_height: int = ROW_HEIGHT, valign: str = "CENTER", splittable: bool = True,
              header_rows: int = 0, border: str = "solid", keep_with_next: bool = False,
              gap: str | None = None, paper: dict | None = None, gap_px=None, width_px=None) -> str:
        plain = _choice(border, "border", BORDERS, "solid") == "none"
        out_top, out_bottom = _gap_px(gap_px) or (2 * (TABLE_GAPS[_choice(gap, "gap", tuple(TABLE_GAPS), "normal")],))
        header = _list_or_empty(header, "header")
        all_rows = ([header] if header else []) + _list_or_empty(rows, "rows")
        if not all_rows or not all_rows[0]:
            raise ValueError("표에 행이나 칸이 없음 (header나 rows를 채워 주세요)")
        cells, cols = layout_table(all_rows, (1 if header else 0) + header_rows)
        if widths and len(widths) != cols:
            raise ValueError(f"widths는 열 수와 같은 {cols}개여야 함 (받은 개수: {len(widths)})")
        paper = _paper_option(paper)
        in_x, in_y = (0, 0) if self.app else (CELL_MARGIN_X, CELL_MARGIN_Y)     # 앱 학습지는 칸마다 여백을 정한다
        total_width = round(paper["width"] * PX) if paper else _width_px(width_px, self.table_width)
        col_widths = _split_width(total_width, widths or [1] * cols)
        self._warn_wide_words(cells, col_widths, in_x)
        heights = _row_heights(cells, len(all_rows), row_height)
        by_row: list[list[TableCell]] = [[] for _ in all_rows]
        for c in cells:
            by_row[c.row].append(c)
        trs = "".join(
            "<hp:tr>" + "".join(
                self._cell(c, sum(col_widths[c.col:c.col + c.colspan]), sum(heights[c.row:c.row + c.rowspan]),
                           valign, plain)
                for c in row_cells) + "</hp:tr>"
            for row_cells in by_row)
        self.preview.extend(_clean(equation_preview(" | ".join(self._preview_text(c) for c in row_cells)))
                            for row_cells in by_row)
        repeat = int(any(c.header for c in cells))
        estimated = _estimated_rows(cells, heights, col_widths)
        inline = not paper and (not splittable or sum(estimated) <= _inline_limit(len(all_rows), bool(header)))
        page_break = "NONE" if inline else "CELL" if max(estimated) > ROW_SPLIT_LIMIT else "TABLE"
        table = (
            f'<hp:tbl id="{next(self._table_ids)}" zOrder="0" numberingType="TABLE" textWrap="{_table_wrap(paper)}" '
            f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="{page_break}" '
            f'repeatHeader="{repeat}" rowCnt="{len(all_rows)}" colCnt="{cols}" cellSpacing="0" '
            f'borderFillIDRef="{self.styles.no_border if plain else self.styles.border}" noAdjust="0">'
            f'<hp:sz width="{total_width}" widthRelTo="ABSOLUTE" height="{sum(heights)}" '
            'heightRelTo="ABSOLUTE" protect="0"/>'
            f'{_table_position(inline, paper)}'
            f'<hp:outMargin left="{0 if paper else TABLE_OUT_MARGIN}" right="{0 if paper else TABLE_OUT_MARGIN}" '
            f'top="{0 if paper else out_top}" bottom="{0 if paper else out_bottom}"/>'
            f'<hp:inMargin left="{in_x}" right="{in_x}" top="{in_y}" bottom="{in_y}"/>{trs}</hp:tbl>'
        )
        anchor = self.paragraph(f'<hp:run charPrIDRef="{self.styles.char["spacer" if paper else "body"]}">{table}<hp:t/></hp:run>',
                                "spacer" if paper else "anchor" if self.app else "left_keep" if keep_with_next else "left")
        return anchor if inline or paper else anchor + self._spacer()

    def _preview_text(self, cell: "TableCell") -> str:
        """미리 보기용 칸 글. 빈칸으로 읽는 ~~…~~는 괄호로 바꿔 표기가 글자 그대로 남지 않게 한다."""
        if self._blank_shade(cell) is None:
            return cell.text
        return re.sub(r"~~(.+?)~~", lambda found: f"({found.group(1)})", cell.text, flags=re.S)

    def _spacer(self) -> str:
        """쪽을 넘어 나뉘는 표 바로 뒤에 두는 1pt 빈 문단. 없으면 한글이 표 뒤 소제목의 '다음 문단과 함께'를
        무시해 소제목만 쪽 끝에 남는다 (한글에서 확인: 빈 문단이 사이에 있으면 소제목이 표와 함께 넘어간다)."""
        return self.paragraph(self.runs("", "spacer"), "spacer")

    def _heading(self, block: dict) -> str:
        level = 1 if block.get("level") is None else _int_option(block["level"], "level", 1, OUTLINE_LEVELS)
        return self.text_paragraph(block["text"], "heading", "h1" if level == 1 else "h2")

    def _paragraph_block(self, block: dict) -> str:
        align = _choice(block.get("align"), "align", tuple(ALIGN_TO_PARA), "justify")
        size = _choice(block.get("size"), "size", tuple(SIZE_TO_CHAR), "normal")
        keep = _bool_option(block.get("keep_with_next"), "keep_with_next", False)
        para = ALIGN_TO_PARA[align] + ("_keep" if keep else "")
        return self.text_paragraph(block["text"], para, SIZE_TO_CHAR[size])

    def _outline_block(self, block: dict) -> str:
        return self.outline(block.get("items"), block.get("start", 1))

    def _bullets(self, block: dict) -> str:
        return "".join(self.text_paragraph(f"• {text}", "item") for text in _item_texts(block))

    def _numbered(self, block: dict) -> str:
        texts = _item_texts(block)
        start = _start_option(block.get("start", 1), "numbered")
        para = "item_num1" if start + len(texts) - 1 < 10 else "item_num2"
        return "".join(self.text_paragraph(f"{i}. {text}", para) for i, text in enumerate(texts, start))

    def _warn_wide_words(self, cells: list, col_widths: list[int], in_x: int) -> None:
        """칸보다 넓은 낱말은 한글에서 낱말 중간("문/항", "선택형(5/지)")이 끊긴다. 막지 않고 알린다.

        앱 학습지(page "app")는 칸마다 여백을 따로 정하므로 이 어림을 쓰지 않는다."""
        if self.app:
            return
        found: dict[tuple[int, str], list[int]] = {}
        for c in cells:
            inner = sum(col_widths[c.col:c.col + c.colspan]) - 2 * (in_x or CELL_MARGIN_X)
            for word in wide_words(str(c.text), inner):
                found.setdefault((c.col, word), []).append(c.row + 1)
        for (col, word), rows in found.items():
            where = f"{rows[0]}행" if len(rows) == 1 else f"{rows[0]}~{rows[-1]}행 중 {len(rows)}곳"
            self.warnings.append(f"표 {col + 1}번째 칸({where})의 '{word}'가 칸보다 넓어 낱말 중간에서 줄이 바뀝니다. "
                                 "widths에서 그 칸을 넓히거나 낱말을 줄여 주세요")

    def _table_block(self, block: dict) -> str:
        rows = _list_or_empty(block.get("rows"), "rows")
        header_rows = block.get("header_rows")
        header_rows = 0 if header_rows is None else _int_option(header_rows, "header_rows", 0, len(rows))
        return self.table(block.get("header"), rows, block.get("widths"), header_rows=header_rows,
                          border=block.get("border"), gap=block.get("gap"), paper=block.get("paper"), gap_px=block.get("gap_px"), width_px=block.get("width_px"),
                          keep_with_next=_bool_option(block.get("keep_with_next"), "keep_with_next", False))

    def _shape_block(self, block: dict) -> str:
        """종이 기준으로 놓는 도형 하나(예: 머리 띠 바탕). paper: {x, y} px, w·h·fill·fill_to 는 도형 값."""
        shape = read_shape(block, "도형")
        if not isinstance(shape.get("paper"), dict):
            raise ValueError("shape 블록에는 paper({x, y} px)가 필요함")
        paragraph = self.paragraph(self.runs("", "spacer"), "chip", in_cell=True)
        run = (f'<hp:run charPrIDRef="{self.styles.char["spacer"]}">'
               f'{shape_xml(shape, next(self._table_ids), paragraph)}<hp:t/></hp:run>')
        return self.paragraph(run, "spacer")

    def _answer_box(self, block: dict) -> str:
        lines = 3 if block.get("lines") is None else _int_option(block["lines"], "lines", 1, MAX_LINES)
        return self.table(None, [[""]], row_height=ANSWER_LINE_HEIGHT * lines, valign="TOP", splittable=False)

    def _blank(self, block: dict) -> str:
        return self.paragraph(self.runs(""))

    def block(self, block: dict) -> str:
        kind = block.get("type")
        if kind not in self._handlers:
            raise ValueError(f"알 수 없는 블록 종류: {kind!r} (가능: {', '.join(self._handlers)})")
        return self._handlers[kind](block)

    def set_body_width(self, body_width: int) -> None:
        self.table_width = body_width - 2 * TABLE_OUT_MARGIN

    def column_switch(self, columns: int, body: str, line: bool = False) -> str:
        """한글의 '다단 설정 나누기': body의 첫 문단 맨 앞에 단 설정을 넣어 그 문단부터 단 수가 바뀐다.

        단 설정만 든 빈 문단을 따로 두면 왼쪽 단만 한 줄 내려간다 (한글에서 확인). body가 비면 빈 문단에 둔다.
        line이면 단 사이에 구분선."""
        attrs = f'id="" type="NEWSPAPER" layout="LEFT" colCount="{columns}" sameSz="1" sameGap="{COLUMN_GAP}"'
        col_pr = f'<hp:colPr {attrs}>{COLUMN_LINE}</hp:colPr>' if line else f'<hp:colPr {attrs}/>'
        run = f'<hp:run charPrIDRef="{self.styles.char["body"]}"><hp:ctrl>{col_pr}</hp:ctrl></hp:run>'
        if not body.startswith("<hp:p "):
            return self.paragraph(run) + body
        opening_end = body.index(">") + 1
        return body[:opening_end] + run + body[opening_end:]

    def _page_number_runs(self, char: str = "body") -> str:
        """"쪽 / 전체 쪽" 자동 번호 run."""
        number_format = '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar="" supscript="0"/>'
        return (f'<hp:run charPrIDRef="{self.styles.char[char]}">'
                f'<hp:ctrl><hp:autoNum num="1" numType="PAGE">{number_format}</hp:autoNum></hp:ctrl>'
                '<hp:t> / </hp:t>'
                f'<hp:ctrl><hp:autoNum num="1" numType="TOTAL_PAGE">{number_format}</hp:autoNum></hp:ctrl>'
                '</hp:run>')

    def page_number_footer(self, position: str, text_width: int, footer_blocks: list | None = None) -> str:
        """모든 쪽 꼬리말 run (첫 문단의 secPr run 바로 뒤에 둔다). 기본은 "쪽 / 전체 쪽" 번호이고,
        footer_blocks가 있으면 그 블록(표 등)이 꼬리말에 들어간다."""
        if footer_blocks:
            content = _render_blocks(self, footer_blocks)
        else:
            content = self.paragraph(self._page_number_runs(), PAGE_NUMBER_PARA[position], in_cell=True)
        return (
            f'<hp:run charPrIDRef="{self.styles.char["body"]}"><hp:ctrl>'
            '<hp:footer id="1" applyPageType="BOTH"><hp:subList id="" textDirection="HORIZONTAL" '
            'lineWrap="BREAK" vertAlign="BOTTOM" linkListIDRef="0" linkListNextIDRef="0" '
            f'textWidth="{text_width}" textHeight="{FOOTER_HEIGHT}" hasTextRef="0" hasNumRef="0">'
            f'{content}</hp:subList></hp:footer></hp:ctrl></hp:run>'
        )

    def _request_page_break(self, block: dict | None = None) -> str:
        self._page_break_pending = True
        return ""

    def finish(self) -> str:
        return self.paragraph(self.runs("")) if self._page_break_pending else ""


def _section_run(skeleton_section: str, margin: int, orientation: str = "portrait", page: str = "normal") -> str:
    found = re.search(r'<hp:run charPrIDRef="0"><hp:secPr.*?</hp:ctrl></hp:run>', skeleton_section, re.S)
    if found is None:
        raise ValueError(SKELETON_SECTION_ERROR)
    sec_run = found.group(0)
    sec_run = re.sub(r'<hp:pagePr landscape="[A-Z]+"', f'<hp:pagePr landscape="{ORIENTATIONS[orientation]}"',
                     sec_run)
    sec_run = re.sub(r'(<hp:margin header="\d+" footer="\d+" gutter="\d+" )left="\d+" right="\d+"',
                     rf'\1left="{margin}" right="{margin}"', sec_run)
    return {"compact": compact_margins, "app": app_margins, "sheet": sheet_margins}.get(page, lambda run: run)(sec_run)


def _render_body(writer: "SectionWriter", blocks: list, layout: Layout, full_width: int) -> str:
    columns, header_blocks = layout.columns, layout.header_blocks
    if columns == 1:
        return _render_blocks(writer, blocks)
    # 제목과 머리 블록은 1단(전체 너비), 그 뒤부터 다단
    head = _render_blocks(writer, blocks[:header_blocks])
    writer.set_body_width((full_width - COLUMN_GAP * (columns - 1)) // columns)
    body = _render_blocks(writer, blocks[header_blocks:], header_blocks + 1)
    return head + writer.column_switch(columns, body, layout.column_line)


def _render_blocks(writer: "SectionWriter", blocks: list, start: int = 1) -> str:
    rendered = []
    for number, block in enumerate(blocks, start):
        try:
            rendered.append(writer.block(block))
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            kind = block.get("type") if isinstance(block, dict) else type(block).__name__
            raise ValueError(f"{number}번째 블록({kind}): {error}") from error
    return "".join(rendered)


def build_section(spec: dict, styles: Styles, skeleton_section: str,
                  warnings: list[str] | None = None) -> tuple[str, str]:
    """section0.xml 글과 미리 보기 글. 만들며 생긴 경고(긴 수식 등)는 warnings에 더한다."""
    layout = _layout_options(spec)
    found = re.match(r"(.*?<hs:sec [^>]*>)", skeleton_section, re.S)
    if found is None:
        raise ValueError(SKELETON_SECTION_ERROR)
    opening = found.group(1)
    sec_run = _section_run(skeleton_section, layout.margin, layout.orientation, layout.page)

    full_width = layout.page_width - 2 * layout.margin
    writer = SectionWriter(styles, full_width, app=layout.page == "app")
    footer_blocks = spec.get("footer") or None
    if layout.page_numbers or footer_blocks:
        sec_run += writer.page_number_footer(layout.page_numbers or "center", full_width, footer_blocks)
    title = as_text(spec.get("title"))
    if title:
        writer.preview.append(_clean(title))
    empty = "spacer" if layout.page == "app" else "body"     # 앱 학습지는 첫 문단을 1pt로 둬 머리 띠 바로 밑에서 시작
    first = (f'<hp:p id="0" paraPrIDRef="{styles.para["title" if title else empty]}" styleIDRef="0" '
             f'pageBreak="0" columnBreak="0" merged="0">{sec_run}'
             f'{writer.runs(title, "title" if title else empty)}</hp:p>')
    body = _render_body(writer, with_auto_keep(spec.get("blocks") or []), layout, full_width) + writer.finish()
    preview = "\r\n".join(writer.preview)[:PREVIEW_LIMIT]
    if warnings is not None:
        warnings.extend(dict.fromkeys(writer.warnings))
    return f"{opening}{first}{body}</hs:sec>", preview


# ---------------------------------------------------------------- 패키지

def _doc_title(spec: dict) -> str:
    """문서 정보 제목: doc_title, 없으면 title, 그것도 없으면 첫 heading 글."""
    for key in ("doc_title", "title"):
        if as_text(spec.get(key)):
            return _clean(plain_text(spec[key]))
    heading = next((block for block in spec.get("blocks") or [] if block.get("type") == "heading"), None)
    return _clean(plain_text(heading.get("text"))) if heading else ""


def _write_package(path: Path, order: list[str], entries: dict) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE, compress_type=zipfile.ZIP_STORED)
        for name in order:
            if name != "mimetype":
                archive.writestr(name, entries[name], compress_type=zipfile.ZIP_DEFLATED)


def build_hwpx(spec: dict, out_path: Path, skeleton: Path = SKELETON) -> list[str]:
    """hwpx를 만들고 표기 경고 목록(날짜 형식 등)을 돌려준다."""
    _validate_spec(spec)
    with zipfile.ZipFile(skeleton) as archive:
        order = [info.filename for info in archive.infolist()]
        entries = {name: archive.read(name) for name in order}

    header, styles = prepare_header(entries["Contents/header.xml"].decode("utf-8"), spec)
    build_warnings: list[str] = []
    section, preview = build_section(spec, styles, entries["Contents/section0.xml"].decode("utf-8"), build_warnings)
    entries["Contents/header.xml"] = header.encode("utf-8")
    entries["Contents/section0.xml"] = section.encode("utf-8")
    entries["Contents/content.hpf"] = update_metadata(
        entries["Contents/content.hpf"].decode("utf-8"), _doc_title(spec), datetime.now(timezone.utc)).encode("utf-8")
    entries["Preview/PrvText.txt"] = (preview + "\r\n").encode("utf-8")
    entries["mimetype"] = MIMETYPE

    # 같은 폴더의 고유한 임시 파일에 쓰고 검사를 통과해야 결과 파일로 옮긴다 (실패한 파일이 남지 않게)
    save_atomically(Path(out_path), lambda path: _write_package(path, order, entries),
                    hwpx_check(RuntimeError, "생성한 hwpx 검사 실패:", (), validate_package), existing=OWN_FILES_ONLY)
    return date_warnings(spec) + equation_text_warnings(spec) + build_warnings + list(spec.get("notes") or [])


def _run(source: str, target: str) -> tuple[str | None, list[str]]:
    """JSON을 읽어 hwpx를 만든다. (실패하면 오류 문장, 성공하면 None) 과 표기 경고 목록을 돌려준다."""
    reading = True
    try:
        spec = json.loads(Path(source).read_text(encoding="utf-8-sig"))
        reading = False
        return None, build_hwpx(spec, Path(target))
    except PermissionError as error:
        failure = f"입력 오류: {error}" if reading else "출력 오류: 한글에서 파일이 열려 있으면 닫고 다시 실행해 주세요"
    except OSError as error:
        failure = f"{'입력' if reading else '출력'} 오류: {error}"
    except (ValueError, KeyError, TypeError, RuntimeError) as error:
        failure = f"입력 오류: {error}"
    except Exception as error:  # 예상 밖 입력(너무 깊은 중첩 등)도 추적 로그 대신 안내 문장으로 알린다
        failure = f"내부 오류: 예상하지 못한 입력입니다 ({type(error).__name__})"
    return failure, []


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    if len(args) == 2 and args[0] == "--check":
        problems = validate_package(Path(args[1]))
        sys.stdout.write("통과\n" if not problems else "\n".join(problems) + "\n")
        return 1 if problems else 0
    if len(args) != 2:
        sys.stdout.write("사용법: python make_hwpx.py 입력.json 출력.hwpx\n")
        return 2
    failure, warnings = _run(args[0], args[1])
    if failure:
        sys.stdout.write(failure + "\n")
        return 1
    sys.stdout.write(f"완료: {args[1]}\n" + "".join(f"{warning}\n" for warning in warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
