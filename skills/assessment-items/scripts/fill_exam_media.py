"""fill_exam.py의 대화 장면(dialogue)과 그림(picture) 자료. 표준 라이브러리만 쓴다.

대화 장면은 수능 사회탐구 문항처럼 인물 클립아트를 가로로 세우고 머리 위에 네모 말풍선을 얹는다.
말풍선은 한글 글상자(글자처럼 취급하는 사각형)라서 교사가 한글에서 글을 바로 고칠 수 있다.
인물 그림은 이 폴더의 fill_exam_figure_<이름>.png이고, 교사가 준 그림 파일 경로도 쓸 수 있다.

    "dialogue": [{"who": "교사", "figure": "teacher_f", "text": "말"}, {"who": "갑", "text": "말"}]
    "picture": {"file": "그림.png", "width_mm": 60, "caption": "<그림> 설명"}   # 또는 "그림.png"
    "picture": [그림 둘]   # 한 줄에 나란히. 칸 있는 표 "table"과 함께 fill_exam_grid.py 상단 설명

그림 파일은 결과 hwpx의 BinData에 압축 없이 넣고 Contents/content.hpf 목록에 올린다
(한글 2024가 InsertPicture 뒤 저장한 꼴을 따름).
그림의 상대 경로는 지시 JSON이 있는 폴더에서 먼저 찾고, 없으면 실행한 폴더 기준이다.
세로로 긴 그림은 단 높이의 60%를 넘지 않게 비율을 지켜 줄인다.
"""

from __future__ import annotations

import math
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fill_exam_parse import _text_width, box_body
from make_hwpx_equation import FRACTION_HEIGHT, equation_script, equation_width, split_equations
from fill_hwpx import FillError
from make_hwpx_shapes import PX, shape_xml

HERE = Path(__file__).resolve().parent
FIGURES = ("student_m1", "student_m2", "student_f1", "student_f2", "teacher_f", "teacher_m", "elder_m", "elder_f")
DEFAULT_FIGURES = ("student_m1", "student_f1", "student_m2", "student_f2")     # figure를 안 적은 사람의 차례
MAX_SPEAKERS = 4
MM = 7200 / 25.4                        # 1mm의 HWPUNIT
FIGURE_WIDTH = round(15 * MM)           # 인물 그림 너비 15mm
DEFAULT_PICTURE_SHARE = 0.8             # width_mm가 없으면 단 너비의 80%까지
TABLE_SIDE = 400                        # 대화 표를 단 너비보다 줄이는 양 (좌우 합)
FALLBACK_WIDTH = 25000                  # 단 너비를 읽지 못했을 때의 표 너비
CELL_MARGIN = 141
BUBBLE_GAP = 200                        # 말풍선과 칸 안쪽 가장자리 사이 (좌우 각각)
BUBBLE_PAD = 425                        # 말풍선 안 글과 테두리 사이 (좌우 각각, 약 1.5mm)
BUBBLE_EXTRA = 450                      # 말풍선 위아래 여유 합
BUBBLE_SLACK = 1.12                     # 글 폭 어림의 여유 (넘치면 한글에서 글이 잘리므로 넉넉히)
BUBBLE_LINE = "#333333"
ROW_MAX_LINES = 4                       # 가로 배치 말풍선이 이 줄 수를 넘으면 세로 배치
FIGURE_RATIO = 1.1                      # 인물 그림 세로/가로 (300x330)
PICTURE_MAX_SHARE = 0.6                 # 그림 높이는 단 높이의 60%까지
FALLBACK_HEIGHT = round(240 * MM)       # 단 높이를 읽지 못했을 때 (약 240mm)
DEFAULT_EM = 1000
DEFAULT_SPACING = 160
MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpg", ".jpeg": "image/jpg", ".gif": "image/gif",
               ".bmp": "image/bmp"}
MAX_PICTURE_BYTES = 20 * 1024 * 1024
MANIFEST = "Contents/content.hpf"
LINE_SPACING = re.compile(r'<hh:lineSpacing type="PERCENT" value="(\d+)"')
BORDER_FILL = re.compile(r'<hh:borderFill id="(\d+)".*?</hh:borderFill>', re.S)
BORDER_SIDES = re.compile(r"<hh:(?:left|right|top|bottom)Border\b[^>]*>")
DIAGONALS = re.compile(r'<hh:(?:slash|backSlash)\b[^>]*?\btype="(\w+)"')
PAGE_HEIGHT = re.compile(r'<hp:pagePr\b[^>]*?\bheight="(\d+)"')
PAGE_MARGIN_VERTICAL = re.compile(r'<hp:margin\b[^>]*?\btop="(\d+)"[^>]*?\bbottom="(\d+)"')
MANIFEST_IDS = re.compile(r'<opf:item\b[^>]*?\bid="([^"]+)"')
PARA_REF = re.compile(r'(\bparaPrIDRef=")\d+(")')
BLANK_RUN = re.compile(r"(?<!_)_{3,}(?!_)")
FULL_SPACE = "　"


@dataclass(frozen=True)
class Picture:
    item_id: str
    entry: str
    media_type: str
    data: bytes


# ---------------------------------------------------------------- 그림 파일

def image_size(data: bytes, where: str) -> tuple[int, int]:
    """그림의 (가로, 세로) 픽셀. PNG, JPEG, GIF, BMP만 읽는다."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if data[:2] == b"BM" and len(data) >= 26:
        width, height = struct.unpack("<ii", data[18:26])
        return width, abs(height)
    if data[:2] == b"\xff\xd8":
        return _jpeg_size(data, where)
    raise FillError(f"{where}: 그림은 PNG, JPG, GIF, BMP 파일이어야 함")


def _jpeg_size(data: bytes, where: str) -> tuple[int, int]:
    position = 2
    while position + 9 < len(data):
        if data[position] != 0xFF:
            position += 1
            continue
        marker = data[position + 1]
        length = struct.unpack(">H", data[position + 2:position + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[position + 5:position + 9])
            return width, height
        position += 2 + length
    raise FillError(f"{where}: JPG 그림의 크기를 읽지 못함")


def split_blanks(text: str) -> list[tuple[str, bool]]:
    """밑줄 문자 3개 이상의 연속을 밑줄 친 빈칸(전각 빈칸)으로 가른다. (조각, 빈칸인지) 목록."""
    pieces, position = [], 0
    for found in BLANK_RUN.finditer(text):
        if found.start() > position:
            pieces.append((text[position:found.start()], False))
        pieces.append((FULL_SPACE * max(3, math.ceil(len(found.group(0)) / 2)), True))
        position = found.end()
    if position < len(text):
        pieces.append((text[position:], False))
    return pieces


def max_picture_height(xml: str) -> int:
    """그림 높이 상한: 단 높이(쪽 높이 - 위·아래 여백)의 60%. 읽지 못하면 약 240mm 기준."""
    page, margin = PAGE_HEIGHT.search(xml), PAGE_MARGIN_VERTICAL.search(xml)
    height = int(page.group(1)) - int(margin.group(1)) - int(margin.group(2)) if page and margin else FALLBACK_HEIGHT
    return round(max(height, 1) * PICTURE_MAX_SHARE)


def figure_path(value: str, where: str) -> Path:
    """인물 이름(teacher_f 등)이면 도구에 든 그림, 아니면 그림 파일 경로."""
    if value in FIGURES:
        return HERE / f"fill_exam_figure_{value}.png"
    path = Path(value)
    if path.suffix.lower() not in MEDIA_TYPES:
        raise FillError(f"{where}: figure는 {', '.join(FIGURES)} 가운데 하나이거나 그림 파일 경로여야 함 "
                        f"(받은 값: {value})")
    return path


def read_picture(path: Path, where: str) -> bytes:
    try:
        if path.stat().st_size > MAX_PICTURE_BYTES:
            raise FillError(f"{where}: 그림 파일이 20MB보다 큼: {path.name}")
        return path.read_bytes()
    except OSError as error:
        raise FillError(f"{where}: 그림 파일을 읽을 수 없음: {path} ({error.strerror or error})") from error


def picture_xml(pic_id: int, z_order: int, item_id: str, width: int, height: int) -> str:
    """글자처럼 취급하는 그림 하나. 한글 2024가 InsertPicture로 저장한 꼴과 같다."""
    rect = (f'<hc:pt0 x="0" y="0"/><hc:pt1 x="{width}" y="0"/><hc:pt2 x="{width}" y="{height}"/>'
            f'<hc:pt3 x="0" y="{height}"/>')
    matrix = "".join(f'<hc:{tag} e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
                     for tag in ("transMatrix", "scaMatrix", "rotMatrix"))
    return (f'<hp:pic id="{pic_id}" zOrder="{z_order}" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" '
            f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="{pic_id}" reverse="0">'
            f'<hp:offset x="0" y="0"/><hp:orgSz width="{width}" height="{height}"/>'
            f'<hp:curSz width="{width}" height="{height}"/><hp:flip horizontal="0" vertical="0"/>'
            f'<hp:rotationInfo angle="0" centerX="{width // 2}" centerY="{height // 2}" rotateimage="1"/>'
            f'<hp:renderingInfo>{matrix}</hp:renderingInfo>'
            f'<hc:img binaryItemIDRef="{item_id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
            f'<hp:imgRect>{rect}</hp:imgRect><hp:imgClip left="0" right="0" top="0" bottom="0"/>'
            '<hp:inMargin left="0" right="0" top="0" bottom="0"/><hp:imgDim dimwidth="0" dimheight="0"/><hp:effects/>'
            f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
            '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" '
            'vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
            '<hp:outMargin left="0" right="0" top="0" bottom="0"/></hp:pic>')


def add_pictures(infos: tuple[zipfile.ZipInfo, ...], entries: dict[str, bytes], pictures: list[Picture]
                 ) -> tuple[tuple[zipfile.ZipInfo, ...], dict[str, bytes]]:
    """그림을 BinData에 넣고 content.hpf 목록에 올린다. 한글처럼 압축하지 않고 넣는다."""
    if not pictures:
        return infos, entries
    manifest = entries[MANIFEST].decode("utf-8")
    if "</opf:manifest>" not in manifest:
        raise FillError("양식의 content.hpf에 그림 목록(opf:manifest)이 없어 그림을 넣지 못함")
    added = "".join(f'<opf:item id="{p.item_id}" href="{p.entry}" media-type="{p.media_type}" isEmbeded="1"/>'
                    for p in pictures)
    manifest = manifest.replace("</opf:manifest>", f"{added}</opf:manifest>", 1)
    clash = {info.filename for info in infos} & {p.entry for p in pictures}
    if clash:
        raise FillError(f"양식에 같은 이름의 그림 파일이 있어 그림을 넣지 못함: {', '.join(sorted(clash))}")
    new_infos = []
    for picture in pictures:
        info = zipfile.ZipInfo(picture.entry, (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        new_infos.append(info)
    updated = {**entries, MANIFEST: manifest.encode("utf-8"), **{p.entry: p.data for p in pictures}}
    return (*infos, *new_infos), updated


# ---------------------------------------------------------------- 양식 모양 빌리기

def _is_plain(fill: str, sides: list[str]) -> bool:
    """네 변이 없고 칠·빗금·그러데이션·그림 채우기가 없는 칸 모양인가."""
    if len(sides) != 4 or not all('type="NONE"' in side for side in sides):
        return False
    if 'faceColor="#' in fill or "gradation" in fill or "imgBrush" in fill:
        return False
    return all(kind == "NONE" for kind in DIAGONALS.findall(fill))


def borderless_fill(header_xml: str) -> tuple[str, str]:
    """네 변이 모두 없고 칠도 없는 칸 모양 번호. 양식에 없으면 하나 더한다. (번호, 고친 header)"""
    for found in BORDER_FILL.finditer(header_xml):
        sides = BORDER_SIDES.findall(found.group(0))
        if _is_plain(found.group(0), sides):
            return found.group(1), header_xml
    number = str(max((int(n) for n in re.findall(r'<hh:borderFill id="(\d+)"', header_xml)), default=0) + 1)
    sides = "".join(f'<hh:{side}Border type="NONE" width="0.1 mm" color="#000000"/>'
                    for side in ("left", "right", "top", "bottom"))
    fill = (f'<hh:borderFill id="{number}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            f'{sides}<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/></hh:borderFill>')
    if "</hh:borderFills>" not in header_xml:
        raise FillError("양식 header.xml에 칸 모양 목록이 없어 대화 장면 표를 만들지 못함")
    header_xml = header_xml.replace("</hh:borderFills>", f"{fill}</hh:borderFills>", 1)
    header_xml = re.sub(r'(<hh:borderFills\b[^>]*?\bitemCnt=")(\d+)',
                        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}", header_xml, count=1)
    return number, header_xml


def plain_shape(shape: str, new_id: str, align: str) -> str:
    """문단 모양을 복제해 정렬만 바꾸고 들여쓰기·왼쪽·오른쪽 여백과 "다음 문단과 함께"를 끈다."""
    shape = re.sub(r'(<hh:paraPr\b[^>]*?\bid=")\d+', rf"\g<1>{new_id}", shape, count=1)
    shape = re.sub(r'(<hh:align horizontal=")[A-Z_]+', rf"\g<1>{align}", shape)
    shape = re.sub(r'(<hc:(?:intent|left|right) value=")-?\d+', r"\g<1>0", shape)
    return shape.replace('keepWithNext="1"', 'keepWithNext="0"')


# ---------------------------------------------------------------- 표와 말풍선

def _cell(col: int, row: int, width: int, height: int, fill: str, body: str, valign: str) -> str:
    return (f'<hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{fill}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="{valign}" linkListIDRef="0" '
            'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            f'{body}</hp:subList><hp:cellAddr colAddr="{col}" rowAddr="{row}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="{width}" height="{height}"/>'
            f'<hp:cellMargin left="{CELL_MARGIN}" right="{CELL_MARGIN}" top="{CELL_MARGIN}" bottom="{CELL_MARGIN}"/>'
            '</hp:tc>')


def table_xml(table_id: int, z_order: int, fill: str, rows: list[list[tuple[str, str]]], widths: list[int],
              heights: list[int]) -> str:
    """표. rows[행][칸] = (칸 안 문단 XML, 세로 정렬[, 그 칸의 칸 모양 번호]). 칸 모양을 안 적으면 fill. 쪽 끝에서 나뉘지 않는다."""
    body = "".join(
        "<hp:tr>" + "".join(_cell(col, row, widths[col], heights[row], own[0] if own else fill, xml, valign)
                            for col, (xml, valign, *own) in enumerate(cells)) + "</hp:tr>"
        for row, cells in enumerate(rows))
    return (f'<hp:tbl id="{table_id}" zOrder="{z_order}" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
            'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
            f'rowCnt="{len(rows)}" colCnt="{len(widths)}" cellSpacing="0" borderFillIDRef="{fill}" noAdjust="0">'
            f'<hp:sz width="{sum(widths)}" widthRelTo="ABSOLUTE" height="{sum(heights)}" heightRelTo="ABSOLUTE" '
            'protect="0"/><hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
            'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" '
            'horzOffset="0"/><hp:outMargin left="0" right="0" top="142" bottom="142"/>'
            f'<hp:inMargin left="{CELL_MARGIN}" right="{CELL_MARGIN}" top="{CELL_MARGIN}" bottom="{CELL_MARGIN}"/>'
            f'{body}</hp:tbl>')


def _words(part: str, em: int) -> list[tuple[float, bool]]:
    """한 줄 글을 낱말(어절)별 (너비, 분수 수식이 있는지)로 나눈다. 수식은 쪼개지 않는 덩어리다."""
    words: list[tuple[float, bool]] = []
    width, fraction = 0.0, False
    for piece, is_equation in split_equations(part):
        if is_equation:
            script = equation_script(piece)
            width += equation_width(script, em)
            fraction = fraction or " over " in f" {script} "
            continue
        for token in re.split(r"(\s+)", piece):
            if token.isspace():
                if width:
                    words.append((width, fraction))
                width, fraction = 0.0, False
            elif token:
                width += _text_width(token, em) * BUBBLE_SLACK
    if width:
        words.append((width, fraction))
    return words


def wrap_layout(text: str, inner_width: int, em: int) -> tuple[int, int]:
    """(줄 수, 분수 수식이 든 줄 수). 한글이 낱말 단위로 줄을 바꿀 때의 어림. 칸보다 긴 낱말은 글자 단위로 끊긴다."""
    shown = text.replace("**", "").replace("__", "")
    room = max(inner_width, em)
    space = _text_width(" ", em) * BUBBLE_SLACK
    lines = fraction_lines = 0
    for part in shown.split("\n"):
        used, has_fraction = 0.0, False
        lines += 1
        for width, fraction in _words(part, em):
            if used and used + space + width > room:
                lines += 1
                fraction_lines += has_fraction
                used, has_fraction = 0.0, False
            used = used + space + width if used else width
            has_fraction = has_fraction or fraction
            while used > room:                  # 칸보다 긴 낱말
                lines += 1
                used -= room
        fraction_lines += has_fraction
    return lines, fraction_lines


def wrapped_lines(text: str, inner_width: int, em: int) -> int:
    return wrap_layout(text, inner_width, em)[0]


def bubble_height(text: str, inner_width: int, em: int, spacing: int) -> int:
    """말풍선 높이 어림. 한글 글상자는 글에 맞춰 늘지 않으므로 줄 수를 넉넉히 센다. 분수가 든 줄은 더 높다."""
    lines, fractions = wrap_layout(text, inner_width, em)
    line = em * spacing // 100
    return lines * line + fractions * max(0, FRACTION_HEIGHT * em // 1000 - line) + BUBBLE_EXTRA


def speakers(value: list[dict]) -> list[dict]:
    """figure를 안 적은 사람에게 차례대로 학생 그림을 준다. 같은 그림이 겹치지 않게 고른다."""
    used = {person.get("figure") for person in value}
    spare = iter([name for name in (*DEFAULT_FIGURES, *FIGURES) if name not in used])
    return [person if person.get("figure") else {**person, "figure": next(spare, DEFAULT_FIGURES[0])}
            for person in value]


def next_item_ids(manifest: str, count: int) -> list[str]:
    """목록의 id와도, BinData의 파일 이름(image1.png 등)과도 겹치지 않는 그림 id."""
    taken = set(MANIFEST_IDS.findall(manifest))
    taken |= {Path(href).stem for href in re.findall(r'href="BinData/([^"]+)"', manifest)}
    ids, number = [], 1
    while len(ids) < count:
        if f"image{number}" not in taken:
            ids.append(f"image{number}")
        number += 1
    return ids


# ---------------------------------------------------------------- 문항에 넣기

class Media:
    """Writer 하나에 딸린 그림·대화 장면 쓰개. 쓴 그림은 pictures에 모아 마지막에 파일에 넣는다."""

    def __init__(self, writer, manifest: str, base_dir: Path | None = None) -> None:
        self.writer = writer
        self.base_dir = base_dir
        self.max_height = max_picture_height(writer.xml)
        self.manifest = manifest
        self.pictures: list[Picture] = []
        self.loaded: dict[Path, Picture] = {}
        self.aligned: dict[tuple[str, str], str] = {}
        self.fill: str | None = None
        self.ruled: tuple[str, str] | None = None            # 표의 (글 칸, 머리 칸) 칸 모양 번호
        self.fill_ops: list[tuple[object, str]] = []        # header에 칸 모양을 더한 일과 그때 받은 번호
        self.fill_header = writer.header_xml                # 칸 모양을 더해 가며 번호를 미리 정하는 header

    # 양식 모양
    def _base(self, stem) -> tuple[object, str]:
        """(문단 틀, 글자 모양). 자료 상자 본문이 있으면 그 글자, 없으면 문제 글자를 쓴다."""
        exam = self.writer.exam
        if exam.box is not None:
            paragraphs = box_body(exam.box.table).paragraphs
            return paragraphs[0], self.writer._main(paragraphs)
        return stem, self.writer._main([stem])

    def _aligned(self, template, align: str) -> str:
        number = re.search(r'paraPrIDRef="(\d+)"', self.writer._open(template))
        source = number.group(1) if number else "0"
        if (source, align) not in self.aligned:
            shape = self.writer.para_shapes.get(source)
            if shape is None:
                raise FillError("양식의 문단 모양을 읽지 못해 그림·대화 장면을 넣지 못함")
            new = str(next(self.writer.next_shape))
            made = plain_shape(shape, new, align)
            self.writer.new_shapes.append(made)
            self.writer.para_shapes[new] = made             # "다음 문단과 함께"를 켤 수 있게 등록
            self.aligned[(source, align)] = new
        return self.aligned[(source, align)]

    def _paragraph(self, template, align: str, runs: str) -> str:
        opening = PARA_REF.sub(rf"\g<1>{self._aligned(template, align)}\g<2>", self.writer._open(template), count=1)
        return f"{opening}{runs}</hp:p>"

    def _em(self, char: str) -> int:
        found = re.search(rf'<hh:charPr id="{char}" height="(\d+)"', self.writer.header_xml)
        return int(found.group(1)) if found else DEFAULT_EM

    def _spacing(self, template) -> int:
        number = re.search(r'paraPrIDRef="(\d+)"', self.writer._open(template))
        found = LINE_SPACING.search(self.writer.para_shapes.get(number.group(1) if number else "0", ""))
        return int(found.group(1)) if found else DEFAULT_SPACING

    def _width(self) -> int:
        width = self.writer.column_width
        return (width - TABLE_SIDE) if width else FALLBACK_WIDTH

    def header(self, header_xml: str) -> str:
        """표에 쓴 칸 모양이 양식에 없었으면 header에 더한다. 번호를 정할 때와 같은 차례로 되풀이한다."""
        for operation, expected in self.fill_ops:
            number, header_xml = operation(header_xml)
            if number != expected:
                raise FillError("표의 칸 모양 번호가 어긋남. 파일을 만들지 않았습니다")
        return header_xml

    def add_fill(self, operation) -> str:
        """operation(header) -> (번호, 고친 header)를 기록하고 번호를 돌려준다."""
        number, self.fill_header = operation(self.fill_header)
        self.fill_ops.append((operation, number))
        return number

    def _borderless(self) -> str:
        if self.fill is None:
            self.fill = self.add_fill(borderless_fill)
        return self.fill

    # 그림
    def resolve(self, path: Path) -> Path:
        """상대 경로는 지시 파일이 있는 폴더에서 먼저 찾고, 없으면 실행한 폴더 기준 그대로."""
        if not path.is_absolute() and self.base_dir is not None and (self.base_dir / path).exists():
            return self.base_dir / path
        return path

    def _picture(self, path: Path, where: str) -> tuple[Picture, tuple[int, int]]:
        key = path.resolve() if path.exists() else path
        if key not in self.loaded:
            data = read_picture(path, where)
            image_size(data, where)
            mine = "".join(f'<opf:item id="{p.item_id}" href="{p.entry}"/>' for p in self.pictures)
            item_id = next_item_ids(self.manifest + mine, 1)[0]
            suffix = ".jpg" if path.suffix.lower() == ".jpeg" else path.suffix.lower()
            picture = Picture(item_id, f"BinData/{item_id}{suffix}", MEDIA_TYPES[path.suffix.lower()], data)
            self.pictures.append(picture)
            self.loaded[key] = picture
        picture = self.loaded[key]
        return picture, image_size(picture.data, where)

    def _picture_run(self, path: Path, width: int, char: str, where: str) -> str:
        picture, pixels = self._picture(path, where)
        height = max(1, round(width * pixels[1] / max(pixels[0], 1)))
        body = picture_xml(next(self.writer.ids), next(self.writer.orders), picture.item_id, width, height)
        return f'<hp:run charPrIDRef="{char}">{body}<hp:t/></hp:run>'

    def picture(self, value: object, stem, where: str) -> list[str]:
        """그림 문단(과 설명 문단). 문단마다 따로 돌려줘 모두 다음 문단과 함께 놓이게 한다."""
        spec = {"file": value} if isinstance(value, str) else dict(value)
        path = self.resolve(Path(spec["file"]))
        if path.suffix.lower() not in MEDIA_TYPES:
            raise FillError(f"{where}: picture는 PNG, JPG, GIF, BMP 파일이어야 함: {path.name}")
        template, char = self._base(stem)
        _, pixels = self._picture(path, where)
        limit = round(self._width() * DEFAULT_PICTURE_SHARE)
        width = round(float(spec["width_mm"]) * MM) if "width_mm" in spec else min(limit, round(pixels[0] * 75))
        width = min(width, self._width())
        if pixels[0] and width * pixels[1] / pixels[0] > self.max_height:
            width = max(1, round(self.max_height * pixels[0] / pixels[1]))
        parts = [self._paragraph(template, "CENTER", self._picture_run(path, width, char, where))]
        if spec.get("caption"):
            parts.append(self._paragraph(template, "CENTER", self.writer.runs(str(spec["caption"]), char)))
        return parts

    # 대화 장면
    def dialogue(self, people: list[dict], stem, where: str, layout: str | None = None) -> str:
        """layout이 없으면 말이 짧을 때 가로(머리 위 말풍선), 말풍선이 ROW_MAX_LINES줄을 넘으면 세로(옆 말풍선)."""
        template, char = self._base(stem)
        em, spacing = self._em(char), self._spacing(template)
        people = speakers(people)
        row_bubble = self._width() // len(people) - 2 * (CELL_MARGIN + BUBBLE_GAP)
        if layout is None:
            longest = max(wrapped_lines(str(p["text"]), row_bubble - 2 * BUBBLE_PAD, em) for p in people)
            layout = "row" if longest <= ROW_MAX_LINES else "column"
        if layout == "row":
            return self._row(people, template, char, (em, spacing), row_bubble, where)
        return self._column(people, template, char, (em, spacing), where)

    def _bubble(self, text: str, width: int, height: int, template, char: str) -> str:
        inside = self._paragraph(template, "LEFT", self.writer.runs(text, char))
        shape = {"shape": "rect", "w": width / PX, "h": height / PX, "fill": "#FFFFFF", "line": BUBBLE_LINE,
                 "line_px": 1, "corner": 0, "pad_px": BUBBLE_PAD / PX, "z": next(self.writer.orders)}
        bubble = f'<hp:run charPrIDRef="{char}">{shape_xml(shape, next(self.writer.ids), inside)}<hp:t/></hp:run>'
        return self._paragraph(template, "CENTER", bubble)

    def _person(self, person: dict, template, char: str, where: str) -> str:
        path = self.resolve(figure_path(str(person["figure"]), where))
        figure = self._paragraph(template, "CENTER", self._picture_run(path, FIGURE_WIDTH, char, where))
        return figure + self._paragraph(template, "CENTER", self.writer.runs(str(person["who"]), char))

    def _table(self, rows: list[list[tuple[str, ...]]], widths: list[int], heights: list[int], template,
               char: str, align: str = "CENTER", fill: str | None = None) -> str:
        table = table_xml(next(self.writer.ids), next(self.writer.orders), fill or self._borderless(), rows, widths,
                          heights)
        return self._paragraph(template, align, f'<hp:run charPrIDRef="{char}">{table}<hp:t/></hp:run>')

    @staticmethod
    def _figure_height(em: int, spacing: int) -> int:
        return round(FIGURE_WIDTH * FIGURE_RATIO) + em * spacing // 100 + 2 * CELL_MARGIN

    def _row(self, people: list[dict], template, char: str, metrics: tuple[int, int], bubble_width: int,
             where: str) -> str:
        """인물을 가로로 세우고 머리 위에 말풍선을 얹는다. 말풍선 아래 끝을 맞춘다."""
        em, spacing = metrics
        heights = [bubble_height(str(p["text"]), bubble_width - 2 * BUBBLE_PAD, em, spacing) for p in people]
        bubbles = [(self._bubble(str(p["text"]), bubble_width, h, template, char), "BOTTOM")
                   for p, h in zip(people, heights)]
        figures = [(self._person(p, template, char, where), "TOP") for p in people]
        widths = [self._width() // len(people)] * len(people)
        row_heights = [max(heights) + 2 * CELL_MARGIN, self._figure_height(em, spacing)]
        return self._table([bubbles, figures], widths, row_heights, template, char)

    def _column(self, people: list[dict], template, char: str, metrics: tuple[int, int], where: str) -> str:
        """사람마다 한 줄: 왼쪽에 인물, 오른쪽에 말풍선."""
        em, spacing = metrics
        left = FIGURE_WIDTH + 2 * CELL_MARGIN + 2 * BUBBLE_GAP
        right = self._width() - left
        bubble_width = right - 2 * (CELL_MARGIN + BUBBLE_GAP)
        rows, heights = [], []
        for person in people:
            height = bubble_height(str(person["text"]), bubble_width - 2 * BUBBLE_PAD, em, spacing)
            rows.append([(self._person(person, template, char, where), "CENTER"),
                         (self._bubble(str(person["text"]), bubble_width, height, template, char), "CENTER")])
            heights.append(max(height + 2 * CELL_MARGIN, self._figure_height(em, spacing)))
        return self._table(rows, [left, right], heights, template, char)
