"""fill_template.py의 add 항목: 양식 위에 카드·원·흐름 화살표·선을 그려 인포그래픽을 만든다."""

from __future__ import annotations

import io
import re

from PIL import Image as PILImage
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from make_pptx_base import split_bold
from pptx_safety import check_image_size

ADD_SHAPES = {
    "box": MSO_SHAPE.RECTANGLE,
    "rounded": MSO_SHAPE.ROUNDED_RECTANGLE,
    "circle": MSO_SHAPE.OVAL,
    "chevron": MSO_SHAPE.CHEVRON,
    "arrow": MSO_SHAPE.RIGHT_ARROW,
    "line": None,
    "image": None,
}
ALIGNS = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")
GEOMETRY_KEYS = ("left", "top", "width", "height")
DEFAULT_PT = 18
DEFAULT_LINE_PT = 1.5
DEFAULT_TEXT_COLOR = "292929"
ROUNDED_ADJUST = 0.12
TEXT_MARGIN = Emu(91440)


def style_runs(shape, size=None) -> None:
    """모든 글자를 한국어로 지정하고(어절 단위 줄바꿈), size가 있으면 크기를 바꾼다."""
    for props in shape.text_frame._txBody.iter(qn("a:rPr")):
        props.set("lang", "ko-KR")
        props.set("altLang", "en-US")
        if size:
            props.set("sz", str(int(float(size) * 100)))


def check_add(where: str, entry) -> None:
    if not isinstance(entry, dict) or entry.get("shape") not in ADD_SHAPES:
        raise ValueError(f"{where}: add의 shape는 {', '.join(ADD_SHAPES)} 중 하나여야 함")
    for key in GEOMETRY_KEYS:
        value = entry.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{where}: add 도형에 {key}(EMU 숫자)가 필요함")
    for key in ("fill", "line", "color"):
        if key in entry and not COLOR.match(str(entry[key])):
            raise ValueError(f"{where}: add의 {key}는 RRGGBB 형식 색이어야 함 (받은 값: {entry[key]})")
    if entry.get("align", "center") not in ALIGNS:
        raise ValueError(f"{where}: add의 align은 {', '.join(ALIGNS)} 중 하나여야 함")
    if entry["shape"] == "image":
        if not isinstance(entry.get("path"), str) or not entry["path"]:
            raise ValueError(f"{where}: add의 image에는 path(그림 경로)가 필요함")
        if "crop" in entry:
            check_crop(where, entry["crop"])


def check_crop(where: str, crop) -> None:
    valid = (isinstance(crop, list) and len(crop) == 4
             and all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in crop)
             and crop[0] < crop[2] and crop[1] < crop[3])
    if not valid:
        raise ValueError(f"{where}: crop은 0~1 사이 숫자 4개 [왼쪽, 위, 오른쪽, 아래]여야 함")


def open_cropped(path, crop):
    check_image_size(path)
    image = PILImage.open(path)
    if crop:
        w, h = image.size
        image = image.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    return image


def _add_image(slide, entry: dict, left: int, top: int, width: int, height: int):
    """그림을 상자 안에 비율을 지켜 가운데 맞춤으로 넣는다 (지도·도표처럼 잘리면 안 되는 그림)."""
    image = open_cropped(entry["path"], entry.get("crop"))
    scale = min(width / image.width, height / image.height)
    pic_w, pic_h = int(image.width * scale), int(image.height * scale)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    return slide.shapes.add_picture(buffer, Emu(left + (width - pic_w) // 2), Emu(top + (height - pic_h) // 2),
                                    Emu(pic_w), Emu(pic_h))


def _apply_line(line_format, entry: dict, default_color: str | None) -> None:
    color = entry.get("line", default_color)
    if color:
        line_format.color.rgb = RGBColor.from_string(color)
        line_format.width = Pt(entry.get("line_width", DEFAULT_LINE_PT))
    else:
        line_format.fill.background()


def _set_typeface(run, typeface: str) -> None:
    run.font.name = typeface
    props = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        node = props.find(qn(tag))
        if node is None:
            node = props.makeelement(qn(tag), {})
            props.append(node)
        node.set("typeface", typeface)


def _write_text(shape, entry: dict, font: str | None) -> None:
    frame = shape.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = TEXT_MARGIN
    value = entry["text"]
    lines = [str(v) for v in value] if isinstance(value, list) else [str(value)]
    typeface = entry.get("font") or font
    for index, text in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = ALIGNS[entry.get("align", "center")]
        for part, bold in split_bold(text):
            run = paragraph.add_run()
            run.text = part
            run.font.size = Pt(entry.get("size", DEFAULT_PT))
            run.font.bold = bold or bool(entry.get("bold"))
            run.font.color.rgb = RGBColor.from_string(entry.get("color", DEFAULT_TEXT_COLOR))
            if typeface:
                _set_typeface(run, typeface)
    style_runs(shape)


def _add_one(slide, entry: dict, font: str | None):
    left, top, width, height = (int(entry[key]) for key in GEOMETRY_KEYS)
    if entry["shape"] == "image":
        return _add_image(slide, entry, left, top, width, height)
    if entry["shape"] == "line":
        line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(left), Emu(top),
                                          Emu(left + width), Emu(top + height))
        _apply_line(line.line, entry, DEFAULT_TEXT_COLOR)
        return line
    shape = slide.shapes.add_shape(ADD_SHAPES[entry["shape"]], Emu(left), Emu(top), Emu(width), Emu(height))
    if entry["shape"] == "rounded":
        shape.adjustments[0] = ROUNDED_ADJUST
    if entry.get("fill"):
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(entry["fill"])
    else:
        shape.fill.background()
    _apply_line(shape.line, entry, None)
    shape.shadow.inherit = False
    if entry.get("text") not in (None, "", []):
        _write_text(shape, entry, font)
    return shape


def add_shapes(slide, entries: list, font: str | None) -> list:
    """그린 도형 목록을 돌려준다 (줄바꿈 검사에 쓴다)."""
    shapes = []
    for entry in entries:
        shape = _add_one(slide, entry, font)
        if entry.get("name"):
            shape.name = str(entry["name"])
        shapes.append(shape)
    return shapes
