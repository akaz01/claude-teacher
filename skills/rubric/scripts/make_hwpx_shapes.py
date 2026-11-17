"""make_hwpx.py의 도형(글상자) 개체. 표준 라이브러리만 쓴다.

표 칸 안 글 사이에 글자처럼 취급하는 도형을 끼워 넣는다. 한글에서 도형을 눌러 글자·크기·색을 고칠 수 있다.
칸의 "content" 목록에 글 대신 이 값을 쓴다:
    {"shape": "round", "w": 60, "h": 18, "fill": "#E3EDF9", "line": "#B9CDE6", "line_px": 1,
     "text": "1961~1963", "color": "#1F3F7A", "size": 9, "bold": true, "font": "serif", "corner": 50, "ratio": 90}
shape: round(둥근 사각형) | ellipse(타원) | rect(사각형). w·h는 px(앱 화면 단위, 1px = 0.75pt = 75 HWPUNIT).
fill이 없으면 속이 비고, line이 없으면 테두리가 없다. text는 도형 가운데에 들어간다(한글 글상자).
corner는 둥근 사각형의 모서리 비율(0~50), ratio는 도형 안 글자의 장평(%), ml_px·mr_px는 도형 좌우 바깥 여백이다.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from make_hwpx_design import _color, gradient_xml
from make_hwpx_options import _bool_option, _choice

PX = 75                                 # 1px = 0.75pt = 75 HWPUNIT
SHAPE_KINDS = ("round", "ellipse", "rect")
DEFAULT_SHAPE_TEXT_SIZE = 9
MAX_SHAPE_PX = 800
ROUND_RATIO = 50                        # 둥근 사각형 모서리 비율 (50이면 양끝이 반원)
NO_LINE = '<hp:lineShape color="#FFFFFF" width="0" style="NONE" endCap="FLAT" headStyle="NORMAL" tailStyle="NORMAL" ' \
          'headfill="0" tailfill="0" headSz="SMALL_SMALL" tailSz="SMALL_SMALL" outlineStyle="NORMAL" alpha="0"/>'


def px_to_unit(value) -> int:
    return round(float(value) * PX)


def _number(value, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise ValueError(f"{name}는 {minimum}~{maximum} 사이의 숫자여야 함 (받은 값: {value!r})")
    return float(value)


COLOR_KEYS = ("fill", "fill_to", "line")
NUMBER_KEYS = {"pad_px": (0, 100), "ml_px": (0, 400), "mr_px": (0, 400), "line_px": (0.1, 20)}


def read_shape(spec: dict, where: str) -> dict:
    """칸 content의 도형 값을 검사해 돌려준다. 색은 #RRGGBB, 각도는 0~360 정수, 나머지 숫자는 범위 안이어야 한다."""
    kind = _choice(spec.get("shape"), f"{where}: shape", SHAPE_KINDS, None)
    width = _number(spec.get("w"), f"{where}: w", 1, MAX_SHAPE_PX)
    height = _number(spec.get("h"), f"{where}: h", 1, MAX_SHAPE_PX)
    corner = spec.get("corner")
    checked = {key: _color(spec.get(key), f"{where}: {key}") for key in (*COLOR_KEYS, "color") if key in spec}
    checked.update({key: _number(spec[key], f"{where}: {key}", low, high)
                    for key, (low, high) in NUMBER_KEYS.items() if spec.get(key) is not None})
    if spec.get("fill_angle") is not None:
        angle = spec["fill_angle"]
        if isinstance(angle, bool) or not isinstance(angle, int) or not 0 <= angle <= 360:
            raise ValueError(f"{where}: fill_angle은 0~360 사이의 정수여야 함 (받은 값: {angle!r})")
    return {**spec, **{key: value for key, value in checked.items() if value is not None}, "shape": kind,
            "w": width, "h": height,
            "corner": ROUND_RATIO if corner is None else int(_number(corner, f"{where}: corner", 0, 50)),
            "bold": _bool_option(spec.get("bold"), f"{where}: bold", False)}


def _fill_xml(color: str | None, color_to: str | None = None, angle: int = 0) -> str:
    if not color:
        return ""
    if color_to:
        return gradient_xml(color, color_to, angle)
    return f'<hc:fillBrush><hc:winBrush faceColor="{color}" hatchColor="#999999" alpha="0"/></hc:fillBrush>'


def _line_xml(color: str | None, width_px: float) -> str:
    if not color:
        return NO_LINE
    width = max(1, px_to_unit(width_px or 1) * 2 // 5)      # 선 굵기 HWPUNIT (1px ≈ 0.26mm ≈ 75)
    return (f'<hp:lineShape color="{color}" width="{width}" style="SOLID" endCap="FLAT" headStyle="NORMAL" '
            'tailStyle="NORMAL" headfill="1" tailfill="1" headSz="MEDIUM_MEDIUM" tailSz="MEDIUM_MEDIUM" '
            'outlineStyle="NORMAL" alpha="0"/>')


def _matrix(tag: str) -> str:
    return f'<hc:{tag} e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'


def shape_xml(shape: dict, shape_id: int, paragraph: str) -> str:
    """글자처럼 취급하는 도형 개체 하나. paragraph는 도형 안 글 문단 XML (글이 없으면 빈 문단)."""
    width, height = px_to_unit(shape["w"]), px_to_unit(shape["h"])
    kind = shape["shape"]
    tag = "ellipse" if kind == "ellipse" else "rect"
    ratio = shape["corner"] if kind == "round" else 0
    extra = ' intervalDirty="0" hasArcPr="0" arcType="NORMAL"' if kind == "ellipse" else f' ratio="{ratio}"'
    paper = shape.get("paper")
    head = (f'<hp:{tag} id="{shape_id}" zOrder="{shape.get("z", shape_id)}" numberingType="PICTURE" '
            f'textWrap="{"BEHIND_TEXT" if paper else "TOP_AND_BOTTOM"}" '
            f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="{shape_id}"{extra}>'
            '<hp:offset x="0" y="0"/>'
            f'<hp:orgSz width="{width}" height="{height}"/><hp:curSz width="{width}" height="{height}"/>'
            '<hp:flip horizontal="0" vertical="0"/>'
            f'<hp:rotationInfo angle="0" centerX="{width // 2}" centerY="{height // 2}" rotateimage="1"/>'
            f'<hp:renderingInfo>{_matrix("transMatrix")}{_matrix("scaMatrix")}{_matrix("rotMatrix")}</hp:renderingInfo>'
            f'{_line_xml(shape.get("line"), shape.get("line_px", 1))}{_fill_xml(shape.get("fill"), shape.get("fill_to"), shape.get("fill_angle", 0))}'
            '<hp:shadow type="NONE" color="#B2B2B2" offsetX="0" offsetY="0" alpha="0"/>')
    comment = f'<hp:shapeComment>{escape(shape["comment"])}</hp:shapeComment>' if shape.get("comment") else ""
    margin = px_to_unit(shape.get("pad_px", 2))
    text = (f'<hp:drawText lastWidth="{width}" name="" editable="0"><hp:subList id="" textDirection="HORIZONTAL" '
            'lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" '
            f'textHeight="0" hasTextRef="0" hasNumRef="0">{paragraph}</hp:subList>'
            f'<hp:textMargin left="{margin}" right="{margin}" top="0" bottom="0"/></hp:drawText>')
    return head + text + _points(kind, width, height) + (
        f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'{_position(paper)}'
        f'<hp:outMargin left="{px_to_unit(shape.get("ml_px", 0))}" right="{px_to_unit(shape.get("mr_px", 0))}" '
        f'top="0" bottom="0"/>{comment}</hp:{tag}>')


def _position(paper: dict | None) -> str:
    if paper:       # 종이 기준으로 글 뒤에 깐다 (머리 띠 바탕)
        return ('<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="0" allowOverlap="1" holdAnchorAndSO="0" '
                f'vertRelTo="PAPER" horzRelTo="PAPER" vertAlign="TOP" horzAlign="LEFT" '
                f'vertOffset="{px_to_unit(paper["y"])}" horzOffset="{px_to_unit(paper["x"])}"/>')
    return ('<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" '
            f'vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>')


def _points(kind: str, width: int, height: int) -> str:
    if kind != "ellipse":
        return (f'<hc:pt0 x="0" y="0"/><hc:pt1 x="{width}" y="0"/><hc:pt2 x="{width}" y="{height}"/>'
                f'<hc:pt3 x="0" y="{height}"/>')
    cx, cy = width // 2, height // 2
    return (f'<hc:center x="{cx}" y="{cy}"/><hc:ax1 x="{width}" y="{cy}"/><hc:ax2 x="{cx}" y="{height}"/>'
            f'<hc:start1 x="{width}" y="{cy}"/><hc:end1 x="{width}" y="{cy}"/>'
            f'<hc:start2 x="{cx}" y="{height}"/><hc:end2 x="{cx}" y="{height}"/>')
