"""make_hwpx.py의 표 칸 디자인. 표준 라이브러리만 쓴다.

칸에 쓸 수 있는 값:
    "fill": "#1F3A5F"            칸 바탕색
    "fill_to": "#2E6DB4"         바탕을 fill에서 이 색으로 번지게(그라데이션). "fill_angle": 0(왼→오)~90(위→아래)
    "color": "#FFFFFF"           글자색
    "size": "large"              글자 크기 (small/normal/large/xlarge/title) 또는 pt 숫자(10.5)
    "font": "serif"              글꼴 (명조 계열 함초롬바탕). 없으면 맑은 고딕
    "ratio": 88                  장평 % (글자 너비). 없으면 100
    "track": -3                  자간 % (글자 사이). 없으면 0
    "font_space": true           글꼴 고유 빈칸 너비 사용(낱말 사이가 좁아짐)
    "edges": "bottom_dot"        테두리 (all/none/bottom/bottom_dot/bottom_thick/top_bottom/all_dot)
                                 또는 {"left": ["SOLID", 1.5, "#2E6DB4"], "bottom": ["DASH", 0.25, "#C9D3DF"]}
                                 (변: [선 종류, 굵기 mm, 색]. 안 쓴 변은 선 없음)
    "edge_color": "#8899AA"      테두리 색
    "mark_color": "#0000FF"      칸 글 속 **표시**의 글자색 (굵게와 함께. 문장 속 답을 칠할 때)
    "blank": true                칸 글 속 ~~빈칸~~ 을 빈칸(음영 + 밑줄)으로 읽음. 앱 학습지(page "app")는 모든 칸이 읽음
    "blank_fill": "#FFEFC2"      칸 글 속 ~~빈칸~~ 의 글자 음영색 (밑줄과 함께. 기본 연노랑)
    "spacing": 145               줄 간격 %
    "pad_px": [왼, 오른, 위, 아래]  칸 안쪽 여백 (px)
    "height_px": 24              행 최소 높이 (px)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from make_hwpx_options import _choice

COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}")
DEFAULT_EDGE_COLOR = "#000000"
DEFAULT_BLANK_FILL = "#FFEFC2"
SIZES = {"small": 900, "normal": 1000, "large": 1400, "xlarge": 1800, "title": 2200}
FONTS = ("serif", "myeongjo", "headline")     # serif 함초롬바탕, myeongjo HY견명조, headline HY헤드라인M
SIDES = ("left", "right", "top", "bottom")
THIN, THICK = "0.12 mm", "0.5 mm"
SOLID, DOT, NONE, BOLD_LINE = ("SOLID", THIN), ("DOT", THIN), ("NONE", THIN), ("SOLID", THICK)
# 이름: 왼쪽, 오른쪽, 위, 아래 (선 종류, 굵기)
EDGES = {
    "all": (SOLID, SOLID, SOLID, SOLID), "none": (NONE, NONE, NONE, NONE),
    "bottom": (NONE, NONE, NONE, SOLID), "bottom_dot": (NONE, NONE, NONE, DOT),
    "bottom_thick": (NONE, NONE, NONE, BOLD_LINE), "top_bottom": (NONE, NONE, SOLID, SOLID),
    "all_dot": (DOT, DOT, DOT, DOT),
}
LINE_KINDS = ("SOLID", "DASH", "DOT", "DASH_DOT", "LONG_DASH")
# 한글이 받는 선 굵기(mm)
LINE_WIDTHS = (0.1, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0)
MAX_SPACING = 300
RUN_SIZE = 10                           # content 글 조각의 기본 글자 크기(pt)


@dataclass(frozen=True)
class CharLook:
    height: int
    bold: bool
    underline: bool
    color: str
    shade: str | None = None
    font: str | None = None
    ratio: int = 100
    spacing: int = 0
    font_space: bool = False


def size_height(size) -> int:
    """글자 크기 이름 또는 pt 숫자를 한글 글자 크기(1/100pt)로."""
    if isinstance(size, str) and size in SIZES:
        return SIZES[size]
    try:
        points = float(size)
    except (TypeError, ValueError):
        raise ValueError(f"size는 {', '.join(SIZES)} 또는 pt 숫자여야 함 (받은 값: {size!r})") from None
    if isinstance(size, bool) or not 1 <= points <= 100:
        raise ValueError(f"size는 {', '.join(SIZES)} 또는 1~100 사이 pt 숫자여야 함 (받은 값: {size!r})")
    return round(points * 100)


def look_key(size="normal", color: str = "#000000", bold: bool = False, mark: str | None = None,
             font: str | None = None, underline: bool = False, shade: str | None = None,
             ratio: int | None = None, spacing: int | None = None, font_space: bool = False) -> str:
    """글자 디자인 이름. 크기·색·굵기(·표시색) 뒤에 글꼴·밑줄·음영·장평이 `|`로 붙는다."""
    key = f"design:{size}:{color}:{int(bold)}" + (f":{mark}" if mark else "")
    extras = [f"font={font}" if font else "", "ul=1" if underline else "", f"shade={shade}" if shade else "",
              f"ratio={ratio}" if ratio and ratio != 100 else "", f"sp={spacing}" if spacing else "",
              "fs=1" if font_space else ""]
    return key + "".join(f"|{extra}" for extra in extras if extra)


def _split_key(key: str) -> tuple[list[str], dict[str, str]]:
    base, *extras = key.split("|")
    return base.split(":"), dict(extra.split("=", 1) for extra in extras)


def char_look(key: str) -> CharLook:
    """글자 디자인 이름을 글자 모양 값으로 푼다."""
    parts, extras = _split_key(key)
    return CharLook(size_height(parts[1]), parts[3] == "1", extras.get("ul") == "1", parts[2],
                    extras.get("shade"), extras.get("font"), int(extras.get("ratio", 100)),
                    int(extras.get("sp", 0)), extras.get("fs") == "1")


def char_style(key: str) -> tuple[tuple, str]:
    """글자 디자인 이름을 (make_hwpx 글자 모양, 글자색)으로 푼다."""
    look = char_look(key)
    return (look.height, look.bold, look.underline), look.color


WIDE_DOT_FONTS = ("myeongjo", "headline")          # 가운뎃점·화살표 폭이 한 글자 너비인 글꼴
DOT_MARKS = "·→↔"


def plain_dot_style(key: str) -> str:
    """글꼴이 맑은 고딕인 같은 모양의 글자 디자인 이름 (가운뎃점·화살표만 좁게 쓸 때)."""
    parts, extras = _split_key(key)
    extras.pop("font", None)
    return look_key(parts[1], parts[2], parts[3] == "1", parts[4] if len(parts) == 5 else None, None,
                    extras.get("ul") == "1", extras.get("shade"), int(extras.get("ratio", 100)),
                    int(extras.get("sp", 0)), extras.get("fs") == "1")


def _rebuild(parts: list[str], extras: dict, color=None, bold=None, mark=None, underline=None, shade=None) -> str:
    """글자 디자인 이름의 일부(색·굵기·표시색·밑줄·음영)만 바꾸고 나머지(글꼴·장평·자간)는 그대로 둔다."""
    extras = dict(extras)
    if underline:
        extras["ul"] = "1"
    if shade:
        extras["shade"] = shade
    return look_key(parts[1], color or parts[2], parts[3] == "1" if bold is None else bold, mark, extras.get("font"),
                    extras.get("ul") == "1", extras.get("shade"), int(extras.get("ratio", 100)),
                    int(extras.get("sp", 0)), extras.get("fs") == "1")


def marked_style(key: str) -> str | None:
    """mark_color가 있는 글자 디자인에서 **표시** 글의 디자인 이름을 만든다. 없으면 None."""
    parts, extras = _split_key(key)
    return _rebuild(parts, extras, color=parts[4], bold=True) if len(parts) == 5 else None


def blank_style(key: str, shade: str) -> str:
    """~~빈칸~~ 글의 디자인 이름: 음영 + 밑줄. mark_color가 있으면 그 색 굵은 글자(교사용 답)."""
    parts, extras = _split_key(key)
    if len(parts) == 5:
        return _rebuild(parts, extras, color=parts[4], bold=True, underline=True, shade=shade)
    return _rebuild(parts, extras, underline=True, shade=shade)


@dataclass(frozen=True)
class CellDesign:
    fill: str | None
    color: str | None
    size: str | None
    edges: object
    edge_color: str
    mark_color: str | None = None
    fill_to: str | None = None
    fill_angle: int = 0
    font: str | None = None
    ratio: int | None = None
    track: int | None = None
    font_space: bool = False
    blank_fill: str = DEFAULT_BLANK_FILL
    spacing: int | None = None
    pad: tuple | None = None
    height_px: float | None = None
    blank: bool = False

    @property
    def border_key(self) -> tuple | None:
        if (self.fill is None and self.edges == "all" and self.edge_color == DEFAULT_EDGE_COLOR
                and self.fill_to is None):
            return None
        return self.fill, self.edges, self.edge_color, self.fill_to, self.fill_angle

    def char_key(self, bold: bool, force: bool = False) -> str | None:
        """글자 디자인 이름. 기본 글자(맑은 고딕 10pt 검정)면 None. force는 기본 글자도 이름을 만든다."""
        if (not force and self.color is None and self.size is None and self.mark_color is None and self.font is None
                and self.ratio is None and self.track is None and not self.font_space):
            return None
        return look_key(self.size or "normal", self.color or "#000000", bold, self.mark_color, self.font,
                        ratio=self.ratio, spacing=self.track, font_space=self.font_space)

    def blank_key(self, bold: bool) -> str:
        return blank_style(self.char_key(bold, force=True), self.blank_fill)


def _color(value, name: str) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and COLOR_PATTERN.fullmatch(value):
        return value.upper()
    raise ValueError(f"{name}는 #1F3A5F처럼 색 코드 6자리여야 함 (받은 값: {value!r})")


def _size(value, name: str) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.lower() in SIZES:
        return value.lower()
    size_height(value)
    return f"{float(value):g}"


def _custom_edges(value: dict, name: str) -> tuple:
    """{"left": ["SOLID", 1.5, "#2E6DB4"]} 꼴을 (왼, 오른, 위, 아래) 선 값으로. 안 쓴 변은 선 없음."""
    if not set(value) <= set(SIDES):
        raise ValueError(f"{name}의 변은 {', '.join(SIDES)} 중에서 골라야 함 (받은 값: {sorted(value)})")
    sides = []
    for side in SIDES:
        spec = value.get(side)
        if spec is None:
            sides.append(("NONE", THIN, DEFAULT_EDGE_COLOR))
            continue
        if not isinstance(spec, (list, tuple)) or len(spec) != 3:
            raise ValueError(f"{name}.{side}는 [선 종류, 굵기 mm, 색] 이어야 함 (받은 값: {spec!r})")
        kind, width, color = spec
        if kind not in LINE_KINDS or isinstance(width, bool) or not isinstance(width, (int, float)) or width <= 0:
            raise ValueError(f"{name}.{side}는 선 종류({'/'.join(LINE_KINDS)})와 0보다 큰 굵기(mm)가 필요함")
        nearest = min(LINE_WIDTHS, key=lambda candidate: abs(candidate - width))
        sides.append((kind, f"{nearest:g} mm", _color(color, f"{name}.{side}") or DEFAULT_EDGE_COLOR))
    return tuple(sides)


def _edges(value, name: str):
    if isinstance(value, dict):
        return _custom_edges(value, name)
    return _choice(value, name, tuple(EDGES), "all")


def _ratio(value, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 50 <= value <= 200:
        raise ValueError(f"{name}는 50~200 사이의 정수(%)여야 함 (받은 값: {value!r})")
    return value


def _track(value, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not -50 <= value <= 50:
        raise ValueError(f"{name}는 -50~50 사이의 정수(%)여야 함 (받은 값: {value!r})")
    return value


def _spacing(value, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 50 <= value <= MAX_SPACING:
        raise ValueError(f"{name}는 50~{MAX_SPACING} 사이의 정수(%)여야 함 (받은 값: {value!r})")
    return value


def _pad(value, name: str) -> tuple | None:
    if value is None:
        return None
    ok = isinstance(value, (list, tuple)) and len(value) == 4 and all(
        not isinstance(v, bool) and isinstance(v, (int, float)) and 0 <= v <= 400 for v in value)
    if not ok:
        raise ValueError(f"{name}는 [왼, 오른, 위, 아래] px 숫자 4개여야 함 (받은 값: {value!r})")
    return tuple(float(v) for v in value)


def _height(value, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 1200:
        raise ValueError(f"{name}는 1~1200 사이 px 숫자여야 함 (받은 값: {value!r})")
    return float(value)


def read_design(spec: dict, where: str) -> CellDesign:
    angle = spec.get("fill_angle", 0)
    if isinstance(angle, bool) or not isinstance(angle, int) or not 0 <= angle <= 360:
        raise ValueError(f"{where}: fill_angle은 0~360 사이의 정수여야 함 (받은 값: {angle!r})")
    return CellDesign(
        fill=_color(spec.get("fill"), f"{where}: fill"),
        color=_color(spec.get("color"), f"{where}: color"),
        size=_size(spec.get("size"), f"{where}: size"),
        edges=_edges(spec.get("edges"), f"{where}: edges"),
        edge_color=_color(spec.get("edge_color"), f"{where}: edge_color") or DEFAULT_EDGE_COLOR,
        mark_color=_color(spec.get("mark_color"), f"{where}: mark_color"),
        fill_to=_color(spec.get("fill_to"), f"{where}: fill_to"), fill_angle=angle,
        font=_choice(spec.get("font"), f"{where}: font", FONTS, None), ratio=_ratio(spec.get("ratio"), f"{where}: ratio"),
        track=_track(spec.get("track"), f"{where}: track"), font_space=bool(spec.get("font_space")),
        blank_fill=_color(spec.get("blank_fill"), f"{where}: blank_fill") or DEFAULT_BLANK_FILL,
        spacing=_spacing(spec.get("spacing"), f"{where}: spacing"),
        pad=_pad(spec.get("pad_px"), f"{where}: pad_px"),
        height_px=_height(spec.get("height_px"), f"{where}: height_px"),
        blank=bool(spec.get("blank")),
    )


def _table_cells(blocks: list):
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "table":
            continue
        header = block.get("header")
        rows = [row for row in (block.get("rows") or []) if isinstance(row, list)]
        for row in ([header] if isinstance(header, list) else []) + rows:
            yield from (cell if isinstance(cell, dict) else {"text": cell} for cell in row)


def item_look_key(item: dict, default_size=9) -> str:
    """칸 content의 도형(shape)·글 조각(run)에 쓰는 글자 디자인 이름. collect_designs가 등록한 것과 같다."""
    return look_key(size=_size(item.get("size", default_size), "content") or str(default_size),
                    color=_color(item.get("color"), "content: color") or "#000000", bold=bool(item.get("bold")),
                    mark=_color(item.get("mark_color"), "content: mark_color"), underline=bool(item.get("underline")), font=_choice(item.get("font"), "content: font", FONTS, None),
                    ratio=_ratio(item.get("ratio"), "content: ratio"),
                    spacing=_track(item.get("track"), "content: track"), font_space=bool(item.get("font_space")))


def _item_looks(cell: dict) -> list[str]:
    """칸 content의 도형 안 글·글 조각에 쓰는 글자 디자인 이름."""
    return [item_look_key(item, RUN_SIZE if "run" in item else 9) for item in cell.get("content") or []
            if isinstance(item, dict) and (item.get("text") or item.get("run") or item.get("page_number"))]


def collect_designs(spec: dict | None) -> tuple[list[tuple], list[str], list[int]]:
    """문서에 쓰인 테두리·글자 디자인·줄 간격을 겹치지 않게 모은다."""
    borders: dict[tuple, None] = {}
    chars: dict[str, None] = {}
    spacings: dict[int, None] = {}
    blocks = spec.get("blocks") if isinstance(spec, dict) else None
    footer = spec.get("footer") if isinstance(spec, dict) else None       # 꼬리말 표의 칸 디자인도 등록한다
    app = isinstance(spec, dict) and spec.get("page") == "app"      # 앱 학습지는 모든 칸이 ~~빈칸~~을 읽는다
    for cell in _table_cells((blocks if isinstance(blocks, list) else []) + (footer if isinstance(footer, list) else [])):
        design = read_design(cell, "표 칸")
        if design.border_key:
            borders[design.border_key] = None
        if design.spacing:
            spacings[design.spacing] = None
        has_blank = "~~" in _cell_text(cell) and (app or design.blank)
        for bold in (False, True):      # 머리칸은 기본이 굵게라 두 모양을 모두 등록한다
            key = design.char_key(bold, force=has_blank)
            if key:
                chars[key] = None
            if key and design.mark_color:
                chars[marked_style(key)] = None
            if has_blank:
                chars[design.blank_key(bold)] = None
        for key in _item_looks(cell):
            chars[key] = None
            if marked_style(key):
                chars[marked_style(key)] = None
            if has_blank:       # 글 조각(run) 속 ~~빈칸~~도 읽는다
                chars[blank_style(key, design.blank_fill)] = None
    for key in [key for key in chars if char_look(key).font in WIDE_DOT_FONTS]:
        chars[plain_dot_style(key)] = None
    return list(borders), list(chars), list(spacings)


def _cell_text(cell: dict) -> str:
    content = cell.get("content")
    if content:
        return "".join(item if isinstance(item, str) else str(item.get("run", "")) for item in content)
    return str(cell.get("text") or "")


def gradient_xml(fill: str, fill_to: str, angle: int) -> str:
    return (f'<hc:fillBrush><hc:gradation type="LINEAR" angle="{angle}" centerX="0" centerY="0" step="50" '
            f'colorNum="2" stepCenter="50" alpha="0"><hc:color value="{fill}"/><hc:color value="{fill_to}"/>'
            '</hc:gradation></hc:fillBrush>')


def border_fill_xml(fill_id: int, key: tuple) -> str:
    fill, edges, edge_color, fill_to, angle = key
    if isinstance(edges, tuple):
        sides = "".join(f'<hh:{side}Border type="{kind}" width="{width}" color="{color}"/>'
                        for side, (kind, width, color) in zip(SIDES, edges))
    else:
        sides = "".join(f'<hh:{side}Border type="{kind}" width="{width}" color="{edge_color}"/>'
                        for side, (kind, width) in zip(SIDES, EDGES[edges]))
    brush = (gradient_xml(fill, fill_to, angle) if fill and fill_to else
             f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#999999" alpha="0"/></hc:fillBrush>'
             if fill else "")
    return (
        f'<hh:borderFill id="{fill_id}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
        '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        f'{sides}<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>{brush}</hh:borderFill>'
    )


# ---------------------------------------------------------------- header.xml 조각

def _margin(left: int, prev: int, after: int, line_spacing: int, intent: int = 0) -> str:
    return (
        f'<hh:margin><hc:intent value="{intent}" unit="HWPUNIT"/><hc:left value="{left}" unit="HWPUNIT"/>'
        f'<hc:right value="0" unit="HWPUNIT"/><hc:prev value="{prev}" unit="HWPUNIT"/>'
        f'<hc:next value="{after}" unit="HWPUNIT"/></hh:margin>'
        f'<hh:lineSpacing type="PERCENT" value="{line_spacing}" unit="HWPUNIT"/>'
    )


def _para_pr(para_id: int, style: tuple) -> str:
    align, line_spacing, prev, after, left, keep_with_next = style[:6]
    hang = style[6] if len(style) > 6 else 0         # 내어쓰기: 둘째 줄부터 글머리 뒤 글 시작에 맞춘다
    # 한글은 hp:default 쪽 여백을 hp:case 값의 2배로 저장한다 (골격 문단 모양 1번 참고)
    return (
        f'<hh:paraPr id="{para_id}" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="1" '
        'suppressLineNumbers="0" checked="0" textDir="LTR">'
        f'<hh:align horizontal="{align}" vertical="BASELINE"/><hh:heading type="NONE" idRef="0" level="0"/>'
        # breakNonLatinWord: BREAK_WORD가 어절 단위 줄바꿈이다 (KEEP_WORD는 글자 단위로 잘림, 한글에서 확인)
        '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="BREAK_WORD" widowOrphan="0" '
        f'keepWithNext="{int(keep_with_next)}" keepLines="1" pageBreakBefore="0" lineWrap="BREAK"/>'
        '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/><hp:switch>'
        '<hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">'
        f'{_margin(left, prev, after, line_spacing, -hang)}</hp:case>'
        f'<hp:default>{_margin(left * 2, prev * 2, after * 2, line_spacing, -hang * 2)}</hp:default></hp:switch>'
        '<hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" '
        'connect="0" ignoreMargin="0"/></hh:paraPr>'
    )


def _border_fill(fill_id: int, face_color: str | None, line_type: str = "SOLID") -> str:
    sides = "".join(f'<hh:{side}Border type="{line_type}" width="0.12 mm" color="#000000"/>'
                    for side in ("left", "right", "top", "bottom"))
    brush = (f'<hc:fillBrush><hc:winBrush faceColor="{face_color}" hatchColor="#999999" alpha="0"/>'
             '</hc:fillBrush>') if face_color else ""
    return (
        f'<hh:borderFill id="{fill_id}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
        '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        f'{sides}<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>{brush}</hh:borderFill>'
    )
