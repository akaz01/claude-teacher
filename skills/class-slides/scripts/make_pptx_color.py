"""make_pptx.py가 쓰는 색 도우미: 글자와 배경의 대비, 교사 템플릿의 테마 색과 배경 읽기."""

from __future__ import annotations

from dataclasses import replace

from lxml import etree
from pptx.enum.dml import MSO_COLOR_TYPE, MSO_FILL, MSO_THEME_COLOR
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn

LIGHT_TEXT, DARK_TEXT = "FFFFFF", "232A35"
MIN_ACCENT_CONTRAST = 3.0               # 강조색이 템플릿 배경 위에서 보이려면 필요한 대비
MIN_TEXT_CONTRAST = 4.5
PALETTE_KEYS = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6")
ACCENT_CANDIDATES = ("accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "dk2")
SCHEME_ALIASES = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
THEME_COLOR_KEYS = {
    MSO_THEME_COLOR.BACKGROUND_1: "lt1", MSO_THEME_COLOR.TEXT_1: "dk1", MSO_THEME_COLOR.BACKGROUND_2: "lt2",
    MSO_THEME_COLOR.TEXT_2: "dk2", MSO_THEME_COLOR.ACCENT_1: "accent1", MSO_THEME_COLOR.ACCENT_2: "accent2",
    MSO_THEME_COLOR.ACCENT_3: "accent3", MSO_THEME_COLOR.ACCENT_4: "accent4", MSO_THEME_COLOR.ACCENT_5: "accent5",
    MSO_THEME_COLOR.ACCENT_6: "accent6",
}


def luminance(hex_color: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def readable_on(background: str) -> str:
    """배경 위에서 더 잘 보이는 글자색(흰색 또는 짙은 남색)."""
    return LIGHT_TEXT if contrast(LIGHT_TEXT, background) >= contrast(DARK_TEXT, background) else DARK_TEXT


def text_color_on(background: str, preferred: str) -> str:
    return preferred if contrast(preferred, background) >= MIN_TEXT_CONTRAST else readable_on(background)


def _color_value(element) -> str | None:
    if element is None:
        return None
    srgb = element.find(qn("a:srgbClr"))
    if srgb is not None:
        return srgb.get("val")
    system = element.find(qn("a:sysClr"))
    return None if system is None else system.get("lastClr")


def template_palette(prs) -> dict[str, str]:
    """템플릿 테마의 색 이름(accent1, lt1 ...)과 6자리 값. 읽지 못하면 빈 사전."""
    try:
        root = etree.fromstring(prs.slide_master.part.part_related_by(RT.THEME).blob)
        scheme = root.find(".//" + qn("a:clrScheme"))
        found = {key: _color_value(scheme.find(qn(f"a:{key}"))) for key in PALETTE_KEYS}
    except (KeyError, ValueError, AttributeError, etree.XMLSyntaxError):
        return {}
    return {key: value.upper() for key, value in found.items() if value and len(value) == 6}


def _scheme_color(value: str, palette: dict[str, str]) -> str | None:
    return palette.get(SCHEME_ALIASES.get(value, value))


def template_background(prs, palette: dict[str, str]) -> str:
    """마스터 배경색. 알 수 없으면 테마의 밝은 색, 그것도 없으면 흰색."""
    background = prs.slide_master._element.find(".//" + qn("p:bg"))
    if background is not None:
        solid = background.find(".//" + qn("a:solidFill"))
        found = _color_value(solid)
        if solid is not None and found is None and solid.find(qn("a:schemeClr")) is not None:
            found = _scheme_color(solid.find(qn("a:schemeClr")).get("val"), palette)
        reference = background.find(qn("p:bgRef"))
        if found is None and reference is not None and reference.find(qn("a:schemeClr")) is not None:
            found = _scheme_color(reference.find(qn("a:schemeClr")).get("val"), palette)
        if found:
            return found.upper()
    return palette.get("lt1", "FFFFFF")


def restyle_for_template(theme, prs):
    """템플릿의 테마 색에서 읽기 쉬운 강조색 둘을 골라 테마에 입힌다. 읽지 못하면 theme을 그대로 돌려준다."""
    palette = template_palette(prs)
    background = template_background(prs, palette)
    usable = []
    for key in ACCENT_CANDIDATES:
        value = palette.get(key)
        if value and value not in usable and contrast(value, background) >= MIN_ACCENT_CONTRAST:
            usable.append(value)
    if not usable:
        return theme
    accent = usable[0]
    accent2 = usable[1] if len(usable) > 1 else theme.accent2
    return replace(theme, accent=accent, accent2=accent2, on_accent=readable_on(accent))


def _fill_hex(shape, palette: dict[str, str]) -> str | None:
    try:
        if shape.is_placeholder or shape.fill.type != MSO_FILL.SOLID:
            return None
        color = shape.fill.fore_color
        if color.type == MSO_COLOR_TYPE.RGB:
            return str(color.rgb)
        return palette.get(THEME_COLOR_KEYS.get(color.theme_color, ""))
    except (TypeError, AttributeError, ValueError, KeyError):
        return None


def backdrop_at(layers: list, x: int, y: int, background: str, palette: dict[str, str]) -> str:
    """마스터·레이아웃(아래에서 위 순서)의 색 있는 도형 중 (x, y)를 덮는 가장 위의 색. 없으면 배경색."""
    found = background
    for layer in layers:
        for shape in layer.shapes:
            if shape.left is None or shape.width is None:
                continue
            inside = shape.left <= x <= shape.left + shape.width and shape.top <= y <= shape.top + shape.height
            color = _fill_hex(shape, palette) if inside else None
            if color:
                found = color.upper()
    return found
