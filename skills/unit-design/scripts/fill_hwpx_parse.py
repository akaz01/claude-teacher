"""fill_hwpx.py의 section XML 읽기. 표준 라이브러리만 쓴다.

XML을 나무로 바꿨다가 다시 쓰면 한글이 쓴 표기가 달라질 수 있다. 그래서 글자와 표 칸이
원문의 몇 번째 글자에 있는지만 기록하고, 고칠 때는 그 구간만 잘라 바꾼다.
입력은 이미 올바른 XML이라고 본다 (fill_hwpx.py가 먼저 검사한다).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple

OBJECT = "￼"           # 문단 안의 표·그림·수식 자리. 찾는 글이 이 자리를 넘지 못한다
SAME_AS_SPACE = str.maketrans({" ": " ", "　": " "})

TOKEN = re.compile(
    r"""<!--.*?-->|<\?.*?\?>|<!\[CDATA\[.*?\]\]>|<!.*?>"""
    r"""|<(/?)([\w:.\-]+)((?:[^<>"'/]+|"[^"]*"|'[^']*'|/(?!>))*)(/?)>""", re.S)
ENTITY = re.compile(r"&(#[0-9]+|#x[0-9a-fA-F]+|[a-z]+);")
NAMED_ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}
INLINE_CHARS = {"hp:lineBreak": "\n", "hp:tab": " ", "hp:nbSpace": " ", "hp:fwSpace": " ", "hp:hyphen": "-"}
NOT_OBJECTS = ("hp:t", "hp:ctrl", "hp:secPr")
KINDS = {"hp:tc": "표 칸", "hp:drawText": "글상자", "hp:header": "머리말", "hp:footer": "꼬리말",
         "hp:footNote": "각주", "hp:endNote": "미주", "hp:caption": "캡션", "hp:fieldBegin": "메모"}
BODY = "본문"
MEMO = "메모"


class Char(NamedTuple):
    """글자 하나와 원문 구간. 표·그림 자리는 start가 -1이다."""
    ch: str
    start: int
    end: int


@dataclass
class Paragraph:
    start: int
    kind: str
    section: int
    cell: "Cell | None" = None
    number: int = 0                         # 표 칸 밖 문단의 문서 전체 번호 (fill_hwpx.py가 매김)
    end: int = 0
    chars: list[Char] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    has_control: bool = False               # 칸을 통째로 지울 때 함께 지우면 안 되는 조판 부호
    line_layout: tuple[int, int] | None = None
    text_slot: tuple[int, int, bool] | None = None   # 첫 hp:t: 여는 태그 구간과 빈 태그 여부
    field_slot: int | None = None           # 누름틀 시작 부호 바로 뒤
    run_tag: tuple[int, int, bool] | None = None     # 첫 hp:run: 여는 태그 구간과 빈 태그 여부
    run_close: int | None = None            # 첫 hp:run 닫는 태그 앞

    @property
    def text(self) -> str:
        return "".join(item.ch for item in self.chars)


@dataclass
class Cell:
    start: int
    table: "Table"
    row: int = 0
    col: int = 0
    row_span: int = 1
    col_span: int = 1
    end: int = 0
    paragraphs: list[Paragraph] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(paragraph.text for paragraph in self.paragraphs)


@dataclass
class Table:
    start: int
    section: int
    rows: int
    cols: int
    number: int = 0                         # 문서 전체 번호 (fill_hwpx.py가 매김)
    cells: list[Cell] = field(default_factory=list)


def _attr(tag: str, name: str, default: int) -> int:
    found = re.search(rf'\b{name}="(\d+)"', tag)
    return int(found.group(1)) if found else default


class SectionReader:
    """section XML 한 개를 태그 순서대로 읽어 문단과 표 목록을 만든다."""

    def __init__(self, xml: str, section: int) -> None:
        self.xml = xml
        self.section = section
        self.stack: list[str] = []
        self.open_paragraphs: list[Paragraph] = []
        self.open_tables: list[Table] = []
        self.open_cells: list[Cell] = []
        self.paragraphs: list[Paragraph] = []
        self.tables: list[Table] = []

    def read(self) -> "SectionReader":
        position = 0
        for token in TOKEN.finditer(self.xml):
            if self.stack and self.stack[-1] == "hp:t" and token.start() > position:
                self._add_text(position, token.start())
            position = token.end()
            name = token.group(2)
            if name is None:
                if token.group(0).startswith(("<!DOCTYPE", "<!ENTITY")):
                    raise ValueError("문서 형식 선언(DTD, <!DOCTYPE·<!ENTITY)이 든 XML은 읽지 않음. 한글에서 다시 저장해 주세요")
                if token.group(0).startswith("<![CDATA[") and self.stack and self.stack[-1] == "hp:t":
                    raise ValueError("CDATA로 쓴 글은 읽을 수 없음. 한글에서 다시 저장해 주세요")
            elif token.group(1):
                self._close(name, token)
            else:
                self._open(name, token)
                if token.group(4):
                    self._close(name, token)
        return self

    def _add_text(self, start: int, end: int) -> None:
        chars = self.open_paragraphs[-1].chars
        raw = self.xml[start:end]
        position = 0
        for entity in ENTITY.finditer(raw):
            self._add_plain(chars, raw[position:entity.start()], start + position)
            value = _decode_entity(entity.group(1))
            chars.append(Char(value.translate(SAME_AS_SPACE), start + entity.start(), start + entity.end()))
            position = entity.end()
        self._add_plain(chars, raw[position:], start + position)

    @staticmethod
    def _add_plain(chars: list[Char], text: str, offset: int) -> None:
        cleaned = text.translate(SAME_AS_SPACE)
        chars.extend(Char(ch, offset + index, offset + index + 1) for index, ch in enumerate(cleaned))

    def _open(self, name: str, token: re.Match) -> None:
        parent = self.stack[-1] if self.stack else ""
        if parent == "hp:t":
            if name in INLINE_CHARS:
                self.open_paragraphs[-1].chars.append(Char(INLINE_CHARS[name], token.start(), token.end()))
        elif name == "hp:p":
            self._open_paragraph(token)
        elif name == "hp:tbl":
            self._note_child(parent, name, token)
            tag = token.group(0)
            table = Table(token.start(), self.section, _attr(tag, "rowCnt", 0), _attr(tag, "colCnt", 0))
            self.open_tables.append(table)
            self.tables.append(table)
        elif name == "hp:tc":
            cell = Cell(token.start(), self.open_tables[-1])
            self.open_cells.append(cell)
            self.open_tables[-1].cells.append(cell)
        elif name in ("hp:cellAddr", "hp:cellSpan") and self.open_cells:
            self._read_cell_tag(name, token.group(0))
        else:
            self._note_child(parent, name, token)
        self.stack.append(name)

    def _open_paragraph(self, token: re.Match) -> None:
        kind = next((KINDS[tag] for tag in reversed(self.stack) if tag in KINDS), BODY)
        direct_cell = len(self.stack) >= 2 and self.stack[-1] == "hp:subList" and self.stack[-2] == "hp:tc"
        paragraph = Paragraph(token.start(), kind, self.section, self.open_cells[-1] if direct_cell else None)
        if direct_cell:
            self.open_cells[-1].paragraphs.append(paragraph)
        self.open_paragraphs.append(paragraph)
        self.paragraphs.append(paragraph)

    def _read_cell_tag(self, name: str, tag: str) -> None:
        cell = self.open_cells[-1]
        if name == "hp:cellAddr":
            cell.row, cell.col = _attr(tag, "rowAddr", 0), _attr(tag, "colAddr", 0)
        else:
            cell.row_span, cell.col_span = _attr(tag, "rowSpan", 1), _attr(tag, "colSpan", 1)

    def _note_child(self, parent: str, name: str, token: re.Match) -> None:
        """문단이 가진 글 자리, 줄 배치 정보, 조판 부호, 표·그림을 기록한다."""
        paragraph = self.open_paragraphs[-1] if self.open_paragraphs else None
        if paragraph is None:
            return
        empty = bool(token.group(4))
        if name == "hp:run" and parent == "hp:p" and paragraph.run_tag is None:
            paragraph.run_tag = (token.start(), token.end(), empty)
        elif name == "hp:linesegarray" and parent == "hp:p":
            paragraph.line_layout = (token.start(), token.end())
        elif parent == "hp:run":
            if name == "hp:t" and paragraph.text_slot is None:
                paragraph.text_slot = (token.start(), token.end(), empty)
            elif name == "hp:ctrl":
                paragraph.has_control = True
            elif name not in NOT_OBJECTS:
                paragraph.chars.append(Char(OBJECT, -1, -1))
                paragraph.objects.append(name)
        elif name == "hp:fieldBegin" and paragraph.field_slot is None and 'type="CLICK_HERE"' in token.group(0):
            paragraph.field_slot = -1       # 이 hp:ctrl이 닫힐 때 자리를 적는다

    def _close(self, name: str, token: re.Match) -> None:
        self.stack.pop()
        if self.stack and self.stack[-1] == "hp:t" and name in INLINE_CHARS:
            chars = self.open_paragraphs[-1].chars
            chars[-1] = chars[-1]._replace(end=token.end())
        elif name == "hp:p":
            self.open_paragraphs.pop().end = token.end()
        elif name == "hp:tbl":
            self.open_tables.pop()
        elif name == "hp:tc":
            self.open_cells.pop().end = token.end()
        elif self.open_paragraphs:
            self._close_in_paragraph(name, token)

    def _close_in_paragraph(self, name: str, token: re.Match) -> None:
        paragraph = self.open_paragraphs[-1]
        if name == "hp:linesegarray" and paragraph.line_layout and self.stack[-1] == "hp:p":
            paragraph.line_layout = (paragraph.line_layout[0], token.end())
        elif name == "hp:run" and self.stack[-1] == "hp:p" and paragraph.run_close is None:
            paragraph.run_close = token.start()
        elif name == "hp:ctrl" and paragraph.field_slot == -1:
            paragraph.field_slot = token.end()


def _decode_entity(body: str) -> str:
    if body.startswith("#x"):
        return chr(int(body[2:], 16))
    if body.startswith("#"):
        return chr(int(body[1:]))
    if body not in NAMED_ENTITIES:      # 정의되지 않은 개체: 여러 글자로 돌려주면 글자 자리가 어긋난다
        raise ValueError(f"알 수 없는 개체 &{body};가 있어 읽지 않음. 한글에서 다시 저장해 주세요")
    return NAMED_ENTITIES[body]
