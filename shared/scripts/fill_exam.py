"""학교 시험지 hwpx 양식의 문항 틀을 복제해 새 문항을 채운다. 표준 라이브러리만 쓴다.

머리 표, 유의사항, 단 편집, 꼬리 부분과 문단·글자 모양, 표 크기와 테두리는 양식 그대로 둔다.
문항은 양식에서 같은 유형의 틀을 복제하고 글자만 바꿔 지시한 수만큼 늘리거나 줄인다.
옛 문항의 글, 정답 표시, 그림은 결과 파일에 남기지 않는다.

사용법:
    python fill_exam.py --inspect 양식.hwpx                     # 머리, 문항 유형, 정답 표시를 보여 줌
    python fill_exam.py 양식.hwpx 지시.json 결과.hwpx           # 원안지 (정답 표시 있음)
    python fill_exam.py 양식.hwpx 지시.json 결과.hwpx --student # 학생용 (정답 표시 없음)

지시 JSON 형식:
{
  "fills": [                                              # 머리와 꼬리 고치기. fill_hwpx.py와 같다 (없어도 됨)
    {"find": "7쪽", "replace": "6쪽"},
    {"table": 1, "row": 3, "col": 3, "text": "내용"}
  ],
  "items": [
    {"type": "passage", "count": 2, "lead": "다음 글을 읽고 물음에 답하시오.",
     "paragraphs": [{"label": "(가)", "text": "지문"}, "표지 없는 지문"]},
    {"type": "short_table", "stem": "문제", "points": 3.2, "choices": ["가", "나", "다", "라", "마"], "answer": 2},
    {"type": "combo_table", "stem": "문제", "points": 3, "bogi": ["ㄱ 글", "ㄴ 글", "ㄷ 글"],
     "choices": ["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄱ, ㄷ", "ㄴ, ㄷ"], "answer": 3},
    {"type": "grid_table", "stem": "문제", "points": 3, "head": ["ⓐ", "ⓑ"],
     "rows": [["가", "나"], ["가", "다"], ["나", "다"], ["나", "라"], ["다", "라"]], "answer": 1},
    {"type": "paragraphs", "stem": "문제", "points": 4, "box": "자료 글", "choices": ["긴 문장 다섯 개"], "answer": 5},
    {"type": "combo_table", "stem": "문제", "points": 3, "layout": "5x1",
     "dialogue": [{"who": "교사", "figure": "teacher_f", "text": "말"}, {"who": "갑", "text": "말"}],
     "choices": ["가", "나", "다", "라", "마"], "answer": 4},
    {"type": "combo_table", "stem": "문제", "points": 3, "picture": {"file": "그래프.png", "width_mm": 60},
     "choices": ["가", "나", "다", "라", "마"], "answer": 1},
    {"type": "written", "stem": "서답형 문제", "points": 5}
  ]
}

- 번호는 다시 매긴다. stem과 choices에 번호와 ①를 쓰지 않아도 된다 (써도 지운다).
- box(자료 상자)와 bogi(<보기>)는 어느 선택지 유형에나 더할 수 있다. box는 글 하나나 문단 목록이다.
- 같은 유형·선택지 수의 틀이 여럿이면 "layout": "5x1"(선지 표 행x칸)로 고른다. 없으면 가장 긴 선지의 폭으로 1x5 → 2x3 → 5x1 중
  가장 좁은 틀을 고르고(fill_exam_text.py), <보기> 유무가 맞는 틀을 쓴다. 맞는 layout이 없으면 다른 배치를 쓰고 알린다.
- box와 passage 글은 문단마다 모양이 맞춰진다: 표지(교사:, (가), ○, ㄱ.)는 내어쓰기, 출처·각주는 오른쪽 정렬, 줄글은 첫 줄 들여쓰기.
- 자료 상자는 1칸 표나, 여백 칸으로 둘러싼 3x3 이하 표(글이 든 칸이 하나뿐)다. 글은 그 본문 칸에 들어간다.
- 문제 끝 배점("[3점]")은 마지막 낱말과 묶음 빈칸으로 붙인다. 자리가 모자라면 "것은? [3점]"이 함께 다음 줄로 간다.
- 선택지가 틀보다 적으면(4지·3지선다) 5개짜리 선지 틀의 남는 칸을 지워 쓴다. layout은 줄인 뒤의 행x칸이다. 5지 틀의 이름(2x3, 5x1, 1x5)도 줄인 배치(2x2, 4x1, 1x4)로 받는다 (fill_exam_reshape.py).
- 빈칸은 ___(밑줄 문자 3개 이상)로 쓰면 실선 빈칸(밑줄 친 전각 빈칸)이 된다.
- 글에는 **굵게**, __밑줄__, {{2/3}}(한글 수식)을 쓸 수 있다. \\n은 같은 문단의 줄바꿈이다.
- dialogue(대화 장면: 인물 그림 위 말풍선)와 picture(그림 파일)를 어느 선택지 유형에나 더할 수 있다.
  그림의 상대 경로는 지시 JSON이 있는 폴더에서 먼저 찾고 없으면 실행한 폴더에서 찾는다. 쓰는 법은 fill_exam_media.py 상단 설명. 순서는 문제 → picture → box → table → dialogue → bogi → 선택지다.
  table(칸 있는 표)과 picture 목록(그림 두 장 나란히)은 fill_exam_grid.py 상단 설명.
- 틀이 없는 유형이나 선택지 수가 틀보다 많거나 줄일 수 없는 문항은 한 번에 모아 오류로 알린다.
- 문제가 하나라도 있으면 파일을 만들지 않는다.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from xml.sax.saxutils import unescape

from fill_exam_parse import _column_width, _last_line_room, _text_width  # noqa: F401  (시험에서도 씀)
from fill_exam_parse import (box_body, choice_order_notes, fill_page_numbers, 
    CIRCLED, COMBO_TABLE, GRID_TABLE, ITEM_START, PARAGRAPHS, POINTS_AT_END, SHORT_TABLE, WRITTEN,
    CharShapes, ExamForm, Frame, PassageFrame, TableBlock, bogi_body, choice_cells, inspect_exam, is_bogi_label,
    plainest, read_exam, run_counts)
from fill_exam_grid import picture_parts, table_parts
from fill_exam_media import MANIFEST, Media, add_pictures, split_blanks
from fill_exam_frames import _pick_frame, _reduced
from fill_exam_reshape import reshape_table_xml
from fill_exam_rows import fit_choice_rows
from fill_exam_text import TextShapes, glue_marker
from make_hwpx_save import BLANK_PNG, PREVIEW_IMAGE, file_error_message
from fill_hwpx import (
    Edit, FillError, Form, apply_edits, changed_entries, is_count, is_text, plan_edits, publish, read_form, validate_spec)
from fill_hwpx_parse import MEMO, OBJECT, Cell, Paragraph, SectionReader
from make_hwpx import MARKUP
from make_hwpx_equation import equation_script, equation_text_warnings, equation_xml, split_equations
from make_hwpx_text import _clean, _xml_text
from fill_exam_spec import (  # noqa: F401  (시험과 다른 모듈도 여기서 가져다 씀)
    CHOICE_KINDS, COMMON_KEYS, ITEM_KEYS, LAYOUT, PASSAGE, PICTURE_GUIDE, SPEC_KEYS, _check_item, _numbered, _plain,
    _texts, _validate)

HEADER_ENTRY = "Contents/header.xml"
NBSP = "\u00a0"                     # 한글 묶음 빈칸(hp:nbSpace)으로 바꿔 쓴다
CHAR_WIDTH = 1000                       # 10pt 글자 하나의 폭 어림 (HWPUNIT)
CELL_SIDE_MARGIN = 326                  # 칸 안 여백 어림 (기본 원안지 선지 칸: 왼쪽 510 + 오른쪽 141의 반)
CHOICE_SLACK = 1.05                     # 선택지 폭 어림의 여유 (한글에서 칸에 들어간 것과 쪼개진 것으로 맞춤)
MIN_ROW_HEIGHT = 300                    # 글이 드는 행의 최소 높이. 한글이 글에 맞춰 늘린다
MIN_OLD_TEXT = 8                        # 이보다 짧은 글(<보 기> 같은 이름표)은 옛 글 검사에서 뺀다
PARA_SHAPE = re.compile(r'<hh:paraPr\b[^>]*?\bid="(\d+)"[^>]*>.*?</hh:paraPr>', re.S)
PARA_SHAPE_ID = re.compile(r'(<hh:paraPr\b[^>]*?\bid=")\d+')
PARA_REF = re.compile(r'(\bparaPrIDRef=")(\d+)(")')
PARA_LIST_TAG = re.compile(r"<hh:paraProperties\b[^>]*>")
TABLE_TAG = re.compile(r"<hp:tbl\b[^>]*>")                   # id와 zOrder를 따로 바꾼다. 속성 순서에 기대지 않는다
OBJECT_ID = re.compile(r'<hp:(?:tbl|pic|equation|rect|line|ellipse|container)\b[^>]*?\bid="(\d+)"')
Z_ORDER = re.compile(r'\bzOrder="(\d+)"')
CELL_SIZE = re.compile(r"<hp:cellSz\b[^>]*>")                  # 속성 순서에 기대지 않고 태그째 읽는다
TABLE_SIZE = re.compile(r"(<hp:tbl\b.*?)(<hp:sz\b[^>]*>)", re.S)
NO_WIDTH_NOTE = "{where}: 칸 너비를 읽지 못해 선택지 길이를 점검하지 못했습니다. 한글에서 줄 넘침을 확인해 주세요"
NO_KEEP_NOTE = ('양식의 문단 모양에서 "다음 문단과 함께" 설정을 찾지 못해 문제와 선택지가 단 끝에서 갈라질 수 있습니다. '
                "한글에서 단 끝을 확인해 주세요")
HEAD_COUNT = re.compile(r"(\d+)\s*문항")
HEAD_TOTAL = re.compile(r"\((\d+(?:\.\d+)?)\s*점\)")
MARKPEN_TAG = re.compile(r"</?hp:markpen(?:Begin|End)\b[^>]*>")
MANIFEST_ITEM = re.compile(r'<opf:item\b[^>]*?\bhref="(BinData/[^"]+)"[^>]*/>')
PICTURE_REF = re.compile(r'binaryItemIDRef="([^"]+)"')


@dataclass(frozen=True)
class Result:
    items: int
    notes: tuple[str, ...]



# ---------------------------------------------------------------- 글 쓰기

class Writer:
    """틀의 원문을 복제해 새 글을 쓴다. 문단과 글자 모양 번호는 양식의 것만 쓴다."""

    def __init__(self, exam: ExamForm, xml: str, header_xml: str, student: bool, manifest: str = "",
                 base_dir: Path | None = None) -> None:
        self.exam = exam
        self.xml = xml
        self.shapes = CharShapes(header_xml)
        self.mark = None if student else exam.mark
        self.ids = itertools.count(max(map(int, OBJECT_ID.findall(xml)), default=0) + 1)
        self.orders = itertools.count(max(map(int, Z_ORDER.findall(xml)), default=0) + 1)
        self.controls = self._kept_controls()
        self.para_shapes = {match.group(1): match.group(0) for match in PARA_SHAPE.finditer(header_xml)}
        self.next_shape = itertools.count(max(map(int, self.para_shapes), default=0) + 1)
        self.keep_shapes: dict[str, str] = {}
        self.keep_failed = False                # "다음 문단과 함께"를 켤 자리를 찾지 못했다
        self.new_shapes: list[str] = []
        self.header_xml = header_xml
        first_end = xml.find("</hp:p>", exam.body_start)             # 첫 문항 문단의 단 설정까지 읽는다
        self.column_width = _column_width(xml, first_end if first_end != -1 else exam.body_end)
        self.media = Media(self, manifest, base_dir)
        self.text = TextShapes(self)

    def _kept_controls(self) -> str:
        """첫 문항 문단에 있던 구역·단 설정. 문단을 새로 써도 잃으면 안 된다."""
        end = self.xml.find("</hp:p>", self.exam.body_start)
        first = self.xml[self.exam.body_start:end if end != -1 else self.exam.body_end]
        found = re.findall(r"<hp:secPr\b.*?</hp:secPr>|<hp:ctrl>.*?</hp:ctrl>", first, re.S)
        return "".join(found)

    # 글자 모양
    def _main(self, paragraphs: tuple[Paragraph, ...] | list[Paragraph], first: int = 0) -> str:
        return plainest(sum((run_counts(p, self.xml, first) for p in paragraphs), Counter()), self.shapes)

    def _styled(self, text: str, char: str) -> list[tuple[str, str]]:
        """___(밑줄 문자 3개 이상)은 밑줄 친 전각 빈칸으로 바꾸고, 나머지는 _marked로 읽는다."""
        pieces: list[tuple[str, str]] = []
        for part, is_blank in split_blanks(text):
            if not is_blank:
                pieces += self._marked(part, char)
                continue
            variant = self.shapes.variant(char, False, True)
            if variant is None:
                raise FillError("양식에 같은 글꼴의 밑줄 글자 모양이 없어 빈칸(___)을 넣을 수 없음")
            pieces.append((part, variant))
        return pieces

    def _marked(self, text: str, char: str) -> list[tuple[str, str]]:
        """글을 (조각, 글자 모양) 목록으로 나눈다. **굵게**와 __밑줄__은 양식의 같은 글꼴을 찾아 쓴다."""
        pieces: list[tuple[str, str]] = []
        position = 0
        for match in MARKUP.finditer(text):
            pieces.append((text[position:match.start()], char))
            bold = match.group(1) is not None
            variant = self.shapes.variant(char, bold, not bold)
            if variant is None:
                name = "굵은" if bold else "밑줄"
                raise FillError(f"양식에 같은 글꼴의 {name} 글자 모양이 없어 넣을 수 없음: {match.group(0)}")
            pieces.append((match.group(1) if bold else match.group(2), variant))
            position = match.end()
        pieces.append((text[position:], char))
        return [piece for piece in pieces if piece[0]]

    def _equation(self, part: str, char: str) -> str:
        script = equation_script(_clean(part))
        body = equation_xml(next(self.ids), script, base_unit=self.shapes.height(char))
        body = body.replace('zOrder="0"', f'zOrder="{next(self.orders)}"', 1)
        return f'<hp:run charPrIDRef="{char}">{body}<hp:t/></hp:run>'

    def runs(self, text: str, char: str, answer: bool = False) -> str:
        pen = answer and self.mark is not None and self.mark.kind == "markpen"
        if answer and self.mark is not None and self.mark.kind == "char":
            char = self.mark.value
        output = [self._equation(part, style) if is_equation
                  else f'<hp:run charPrIDRef="{style}"><hp:t>{_xml_text(part)}</hp:t></hp:run>'
                  for piece, style in self._styled(text, char)
                  for part, is_equation in split_equations(piece)]
        if not output:
            return f'<hp:run charPrIDRef="{char}"><hp:t/></hp:run>'
        if pen:
            begin = f'<hp:run charPrIDRef="{char}"><hp:t><hp:markpenBegin color="{self.mark.value}"/></hp:t></hp:run>'
            end = f'<hp:run charPrIDRef="{char}"><hp:t><hp:markpenEnd/></hp:t></hp:run>'
            output = [begin, *output, end]
        return "".join(output).replace(NBSP, "<hp:nbSpace/>")

    # 문단
    def _open(self, paragraph: Paragraph) -> str:
        tag = self.xml[paragraph.start:self.xml.index(">", paragraph.start) + 1]
        return re.sub(r'\b(pageBreak|columnBreak)="1"', r'\1="0"', tag)

    def paragraph(self, template: Paragraph, runs: str, shape: str | None = None) -> str:
        opening = self._open(template)         # shape: 이 문단만 쓸 문단 모양 번호 (fill_exam_text.py)
        if shape:
            opening = PARA_REF.sub(lambda m: f"{m.group(1)}{shape}{m.group(3)}", opening, count=1)
        return f"{opening}{runs}</hp:p>"

    def blank(self, template: Paragraph | None) -> str:
        if template is None:
            return ""
        return self.paragraph(template, self.runs("", self._main([template])))

    def _keep_shape(self, number: str) -> str:
        """같은 모양에 "다음 문단과 함께"와 "문단 보호"만 켠 문단 모양.

        문제와 선택지가 단 끝에서 갈라지지 않게 하고, 문두 문단 하나가 두 단에 쪼개지지 않게 한다."""
        if number not in self.keep_shapes:
            shape = self.para_shapes.get(number, "")
            if not shape or ('keepWithNext="1"' in shape and 'keepLines="0"' not in shape):
                self.keep_shapes[number] = number
            else:
                new = str(next(self.next_shape))
                self.keep_shapes[number] = new
                shape = PARA_SHAPE_ID.sub(rf"\g<1>{new}", shape, count=1)
                self.keep_failed = self.keep_failed or ('keepWithNext="0"' not in shape
                                                        and 'keepWithNext="1"' not in shape)
                shape = shape.replace('keepWithNext="0"', 'keepWithNext="1"', 1)
                self.new_shapes.append(shape.replace('keepLines="0"', 'keepLines="1"', 1))
        return self.keep_shapes[number]

    def _together(self, parts: list[str]) -> str:
        """문항의 문단들을 한 단에 함께 놓는다. 마지막 문단은 다음 문항과 이어 붙이지 않는다."""
        kept = [PARA_REF.sub(lambda m: f"{m.group(1)}{self._keep_shape(m.group(2))}{m.group(3)}", part, count=1)
                for part in parts[:-1]]
        return "".join(kept + parts[-1:])

    def header_with_shapes(self, header_xml: str) -> str:
        if not self.new_shapes:
            return header_xml
        added = "".join(self.new_shapes)
        header_xml = header_xml.replace("</hh:paraProperties>", f"{added}</hh:paraProperties>", 1)
        return PARA_LIST_TAG.sub(
            lambda m: _with_attribute(m.group(0), "itemCnt", (_attribute(m.group(0), "itemCnt") or 0) + len(self.new_shapes)),
            header_xml, count=1)

    def _take_controls(self, char: str) -> str:
        kept, self.controls = self.controls, ""
        return f'<hp:run charPrIDRef="{char}">{kept}</hp:run>' if kept else ""

    def stem(self, frame: Frame, item: dict, number: int) -> str:
        text = frame.stem.text
        found = ITEM_START.match(text)
        number_char = self._main([_slice(frame.stem, found.start(2), found.end(2))])
        body_char = self._main([frame.stem], found.end(3))
        label = f"{text[:found.start(2)]}{number}{text[found.end(2):found.end(3)]}"
        body = _keep_points(_stem_text(item, frame))
        runs = self.runs(f" {body}", body_char)
        return self.paragraph(frame.stem, self._take_controls(number_char) + self.runs(label, number_char) + runs)

    # 표
    def _cell(self, paragraphs: list[Paragraph], texts: list[str], char: str | None, answer: bool = False,
              shapes: list[str | None] | None = None) -> str:
        pieces = []
        for index, text in enumerate(texts):
            template = paragraphs[min(index, len(paragraphs) - 1)]
            use = char or self._main([template])
            pieces.append(self.paragraph(template, self.runs(text, use, answer), shapes[index] if shapes else None))
        return "".join(pieces)

    def table(self, block: TableBlock, writes: dict[tuple[int, int], str], shrink: int | None = None) -> str:
        """표를 복제한다. writes에 없는 칸의 글은 비운다. <보기> 이름표만 남긴다."""
        edits = []
        paragraph = block.paragraph
        for cell in block.table.cells:
            first, last = cell.paragraphs[0], cell.paragraphs[-1]
            new = writes.get((cell.row, cell.col))
            if new is None and not is_bogi_label(cell) and cell.text.strip():
                new = self.blank(first)
            if new is not None:
                edits.append(Edit(paragraph.section, first.start, last.end, new))
        if paragraph.line_layout:
            edits.append(Edit(paragraph.section, *paragraph.line_layout, ""))
        whole = apply_edits(self.xml[:paragraph.end], edits)[paragraph.start:]
        whole = self._open(paragraph) + whole[whole.index(">") + 1:]
        whole = TABLE_TAG.sub(self._new_table_id, whole)
        return whole if shrink is None else _shrink_row(whole, shrink)

    def _new_table_id(self, found: re.Match) -> str:
        tag = _with_attribute(found.group(0), "id", next(self.ids))
        return _with_attribute(tag, "zOrder", next(self.orders))

    def box(self, value: object) -> str:
        block = self.exam.box
        cell = box_body(block.table)
        texts = [glue_marker(_plain(text)) for text in (value if isinstance(value, list) else [value])]
        return self._text_block(block, cell, texts, self.text.box_shapes(cell.paragraphs, texts, self._main(cell.paragraphs)))

    def _text_block(self, block: TableBlock, cell: Cell, texts: list[str], shapes: list[str | None] | None = None) -> str:
        new = self._cell(cell.paragraphs, texts, self._main(cell.paragraphs), shapes=shapes)
        return self.table(block, {(cell.row, cell.col): new}, cell.row)

    def bogi(self, statements: list, notes: list[str], where: str) -> str:
        texts = [glue_marker(_bogi_line(index, text)) for index, text in enumerate(statements)]
        block = self.exam.bogi
        if block is None:
            if self.exam.box is None:
                raise FillError(f"{where}: 양식에 <보기> 틀도 자료 상자 틀도 없음")
            notes.append(f"{where}: <보기> 틀이 없어 자료 상자 틀을 썼습니다")
            return self.box(["<보 기>", *texts])
        return self._text_block(block, bogi_body(block.table), texts)

    def _slot_char(self, frame: Frame) -> str:
        mains = [self._main(slot) for slot in frame.slots if any(p.chars for p in slot)]
        return Counter(mains).most_common(1)[0][0]

    def choices(self, frame: Frame, item: dict) -> list[str]:
        if frame.kind == GRID_TABLE:
            return [self._grid(frame, item)]
        texts = [f"{CIRCLED[index]} {_no_circle(text)}" for index, text in enumerate(item["choices"])]
        char = self._slot_char(frame)
        answer = item["answer"] - 1
        if frame.kind == PARAGRAPHS:
            return [self.paragraph(frame.choice_paragraphs[index], self.runs(text, char, index == answer))
                    for index, text in enumerate(texts)]
        writes = {(cell.row, cell.col): self._cell(cell.paragraphs, [text], char, index == answer)
                  for index, (cell, text) in enumerate(zip(choice_cells(frame.choice_table.table), texts))}
        table = self.table(frame.choice_table, writes)
        size = _reduced(frame, len(texts))
        if size is not None:                    # 4지·3지선다: 남는 칸을 지우고 표를 다시 짠다
            old = frame.choice_table.table
            table = reshape_table_xml(table, (old.rows, old.cols), size, len(texts))
        return [fit_choice_rows(table, self.shapes.height(char), self.para_shapes)]   # 한글은 열 때 선지 칸 높이를 다시 재지 않는다

    def _grid(self, frame: Frame, item: dict) -> str:
        table = frame.choice_table.table
        by_place = {(cell.row, cell.col): cell for cell in table.cells}
        writes = {}
        for col, text in enumerate(item["head"], start=1):
            cell = by_place[(0, col)]
            writes[(0, col)] = self._cell(cell.paragraphs, [_plain(text)], None)
        for row, values in enumerate(item["rows"], start=1):
            is_answer = row == item["answer"]
            for col, text in enumerate([CIRCLED[row - 1], *values]):
                cell = by_place[(row, col)]
                writes[(row, col)] = self._cell(cell.paragraphs, [_plain(text)], None, is_answer)
        return self.table(frame.choice_table, writes)

    def item(self, item: dict, number: int, where: str, notes: list[str]) -> str:
        frame = _pick_frame(self.exam, item, where, notes)
        parts = [self.stem(frame, item, number)]
        if frame.kind == WRITTEN:
            if frame.box:
                parts.append(self.table(frame.box, {}))
            return self._together(parts) + self.blank(frame.spacer or self.exam.spacer)
        if "picture" in item:
            parts += picture_parts(self.media, item["picture"], frame.stem, where)
        if "box" in item:
            if self.exam.box is None:
                raise FillError(f"{where}: 양식에 자료 상자 틀이 없음")
            parts.append(self.box(item["box"]))
        if "table" in item:
            parts += table_parts(self.media, item["table"], frame.stem, where, notes)
        if "dialogue" in item:
            parts.append(self.media.dialogue(item["dialogue"], frame.stem, where, item.get("dialogue_layout")))
        if "bogi" in item:
            parts.append(self.bogi(item["bogi"], notes, where))
        parts += self.choices(frame, item)
        _note_long_choices(frame, item, where, notes, self.xml)
        return self._together(parts) + self.blank(frame.spacer or self.exam.spacer)

    def passage(self, item: dict, first: int, last: int, where: str) -> str:
        if not self.exam.passages:
            raise FillError(f"{where}: 양식에 공통 지문 틀이 없음. 지문은 box에 넣거나 지문 틀이 든 양식을 받아 주세요")
        frame: PassageFrame = self.exam.passages[0]
        close = frame.lead.text.find("]") + 1
        if not close:
            raise FillError(f"{where}: 양식의 공통 지문 틀 [번호~번호]를 읽지 못함")
        label_char = self._main([_slice(frame.lead, 0, close)])
        lead = self.runs(f"[{first}~{last}]", label_char)
        lead += self.runs(f" {_plain(item['lead'])}", self._main([frame.lead], close))
        parts = [self.paragraph(frame.lead, self._take_controls(label_char) + lead)]
        count = len(item["paragraphs"])
        for index, part in enumerate(item["paragraphs"]):
            parts.append(self._passage_part(frame, part, index))
            if index + 1 < count:
                parts.append(self.blank(frame.gap))
        return "".join(parts) + self.blank(frame.spacer)

    def _passage_part(self, frame: PassageFrame, part: object, index: int) -> str:
        label, text = (part.get("label"), part["text"]) if isinstance(part, dict) else (None, part)
        parts = []
        if label is not None:
            if not frame.labels:
                raise FillError("양식의 지문 틀에 (가) 같은 표지 문단이 없음. label을 빼 주세요")
            template = frame.labels[min(index, len(frame.labels) - 1)]
            parts.append(self.paragraph(template, self.runs(f" {_plain(label)}", self._main([template]))))
        if not frame.bodies:
            raise FillError("양식의 지문 틀에 본문 문단이 없음")
        template = frame.bodies[min(index, len(frame.bodies) - 1)]
        char, body = self._main([template]), _plain(text)
        shape = self.text.shape_for(template, body, True, self.media._em(char), keep_own=False)
        parts.append(self.paragraph(template, self.runs(body, char), shape))
        return "".join(parts)


def _attribute(tag: str, name: str) -> int | None:
    found = re.search(rf'\b{name}="(\d+)"', tag)
    return int(found.group(1)) if found else None


def _with_attribute(tag: str, name: str, value: int) -> str:
    return re.sub(rf'(\b{name}=")\d+(")', rf"\g<1>{value}\g<2>", tag, count=1)


def _cell_width(xml: str, start: int) -> int:
    """칸 너비. 읽지 못하면 0."""
    found = CELL_SIZE.search(xml, start)
    return (_attribute(found.group(0), "width") or 0) if found else 0


def _note_long_choices(frame: Frame, item: dict, where: str, notes: list[str], xml: str) -> None:
    """칸보다 긴 짧은 선택지는 표 안에서 줄이 넘어가 보기 흉하다. 막지 않고 알린다."""
    if frame.kind not in (SHORT_TABLE, COMBO_TABLE) or frame.choice_table.table.cols == 1:
        return                                  # 한 줄에 선지 하나인 표는 칸 안 두 줄이 내어쓰기로 맞춰진다
    cell_width = _cell_width(xml, choice_cells(frame.choice_table.table)[0].start)
    if cell_width <= 0:
        notes.append(NO_WIDTH_NOTE.format(where=where))
        return
    size = _reduced(frame, len(item["choices"]))
    if size is not None:                        # 줄인 표는 칸 수가 달라 칸 너비도 달라진다
        cell_width = cell_width * frame.choice_table.table.cols // size[1]
    width = cell_width - 2 * CELL_SIDE_MARGIN
    shown = [re.sub(r"\{\{.*?\}\}", "수", _no_circle(text)) for text in item["choices"]]     # 수식은 한 글자 폭으로 어림
    if any(_text_width(f"① {text}", CHAR_WIDTH) * CHOICE_SLACK > width for text in shown):
        notes.append(f"{where}: 선택지가 칸보다 길어 칸 안에서 줄이 넘어갑니다. 줄이거나 paragraphs 유형을 쓰세요")


def _slice(paragraph: Paragraph, start: int, end: int) -> Paragraph:
    return replace(paragraph, chars=paragraph.chars[start:end])


def _no_circle(value: object) -> str:
    return re.sub(rf"^\s*[{CIRCLED}]\s*", "", _plain(value))


def _bogi_line(index: int, value: object) -> str:
    text = _plain(value)
    return text if re.match(r"\s*[ㄱ-ㅎ]\s*\.", text) else f"{'ㄱㄴㄷㄹㅁㅂㅅ'[index]}. {text}"


def _stem_text(item: dict, frame: Frame) -> str:
    text = re.sub(r"^\s*\d{1,3}\s*\.\s+", "", _plain(item["stem"])).rstrip()
    wants_points = POINTS_AT_END.search(frame.stem.text) is not None
    if "points" in item:
        written = POINTS_AT_END.search(text)
        if written is None:
            return f"{text} [{item['points']}점]"
        if _points_value(written.group(0)) != float(item["points"]):
            raise FillError(f"문제 글의 배점 {written.group(0).strip()}과 points {item['points']}가 다릅니다. 하나로 맞춰 주세요")
        return text                             # 글에 같은 배점이 이미 있으면 다시 붙이지 않는다
    if wants_points and not POINTS_AT_END.search(text):
        raise FillError("양식이 문제 끝에 배점을 적습니다. points를 적어 주세요")
    return text


def _points_value(label: str) -> float:
    return float(re.search(r"\d+(?:\.\d+)?", label).group(0))


def _keep_points(body: str) -> str:
    """끝의 배점("[5점]") 앞을 보통 빈칸 하나로 맞춘다.

    묶음 빈칸으로 붙이면 "것은? [5점]"이 한 덩어리로 다음 줄로 내려가 윗줄 끝이 비었다(교사 지적 2026-11-18:
    "단락을 마음대로 떨궈 버리니까 어색해 … 사용자가 편집할 수 있게"). 글이 자연스럽게 흐르게 두고,
    배점이 혼자 떨어지면 교사가 한글에서 고친다. 줄을 강제로 바꾸지 않는다."""
    found = POINTS_AT_END.search(body)
    if found is None or "\n" in body[found.start():]:
        return body
    return f"{body[:found.start()].rstrip()} {body[found.start():].strip()}"


def _shrink_row(whole: str, row: int) -> str:
    """새 글이 옛 글보다 짧아도 상자가 옛 높이로 남지 않게 글이 드는 행의 높이를 줄인다.

    칸이 하나인 자료 상자·<보기>는 한글이 칸 높이를 최소값으로 보고 글에 맞춰 늘려 글이 잘리지 않았다 (한글에서 확인).
    여러 행인 선지 표는 열 때 늘리지 않아서 fill_exam_rows.fit_choice_rows가 높이를 정한다 (한글에서 확인)."""
    pieces = whole.split("<hp:tr>")
    heights = (_attribute(found.group(0), "height") or 0 for found in CELL_SIZE.finditer(pieces[row + 1]))
    removed = max(heights, default=MIN_ROW_HEIGHT)
    pieces[row + 1] = CELL_SIZE.sub(lambda found: _with_attribute(found.group(0), "height", MIN_ROW_HEIGHT),
                                    pieces[row + 1])

    def table_size(found: re.Match) -> str:
        old = _attribute(found.group(2), "height")
        if old is None:
            return found.group(0)
        new = max(old - removed + MIN_ROW_HEIGHT, MIN_ROW_HEIGHT)
        return found.group(1) + _with_attribute(found.group(2), "height", new)

    return TABLE_SIZE.sub(table_size, "<hp:tr>".join(pieces), count=1)


# ---------------------------------------------------------------- 본문 조립

def _build_body(writer: Writer, named: list[tuple[str, dict]], notes: list[str]) -> tuple[str, int]:
    """문항을 차례로 복제한다. 실패한 문항은 모아서 한 번에 알린다."""
    pieces: list[str] = []
    failures: list[str] = []
    counters: Counter = Counter()
    numbers = _assign_numbers(writer.exam, named)
    for position, (where, item) in enumerate(named):
        try:
            if item["type"] == PASSAGE:
                following = [numbers[i] for i in range(position + 1, len(named)) if i in numbers][:item["count"]]
                if len(following) < item["count"]:
                    raise FillError(f"{where}: count가 {item['count']}인데 뒤 문항이 {len(following)}개뿐임")
                pieces.append(writer.passage(item, following[0], following[-1], where))
            else:
                pieces.append(writer.item(item, numbers[position], where, notes))
                counters["items"] += 1
        except FillError as error:
            message = str(error)
            failures.append(message if message.startswith(where) else f"{where}: {message}")
    if failures:
        raise FillError("\n".join(failures))
    return "".join(pieces), counters["items"]


def _assign_numbers(exam: ExamForm, named: list[tuple[str, dict]]) -> dict[int, int]:
    """선택형은 1부터 잇고, 양식의 서답형이 "서답형 1"처럼 따로 세면 서답형도 1부터 잇는다."""
    written = exam.frame_of(WRITTEN)
    apart = written is not None and bool(written.prefix)
    counts: Counter = Counter()
    numbers = {}
    for position, (_, item) in enumerate(named):
        if item["type"] == PASSAGE:
            continue
        group = "written" if apart and item["type"] == WRITTEN else "choice"
        counts[group] += 1
        numbers[position] = counts[group]
    return numbers


def _outside_plan(form: Form, exam: ExamForm, fills: list[dict]) -> list[Edit]:
    """머리와 꼬리의 지시를 fill_hwpx.py 방식으로 푼다. 문항 안은 items로만 고친다."""
    if not fills:
        return []
    inside = [p for p in form.paragraphs if p.section == exam.section and exam.body_start <= p.start < exam.body_end]
    outside = tuple(p for p in form.paragraphs if p not in inside)
    edits, _ = plan_edits(replace(form, paragraphs=outside), fills)
    if any(e.section == exam.section and exam.body_start <= e.start < exam.body_end for e in edits):
        raise FillError("fills는 머리와 꼬리만 고칩니다. 문항 안의 표는 items로 적어 주세요")
    return edits


def _head_notes(form: Form, exam: ExamForm, outside: list[Edit], named: list[tuple[str, dict]], count: int) -> list[str]:
    """머리에 적힌 문항 수와 총점이 지시와 다르면 알린다. 고치는 것은 교사의 몫이다."""
    edits = [edit for edit in outside if edit.section == exam.section]
    xml = apply_edits(form.section_xml[exam.section], [*edits, Edit(exam.section, exam.body_start, exam.body_end, "")])
    text = "\n".join(p.text for p in SectionReader(xml, exam.section).read().paragraphs if p.kind != MEMO)
    notes = [f"머리에 적힌 {found}문항이 지시의 문항 수 {count}개와 다릅니다. fills로 고치거나 확인해 주세요"
             for found in dict.fromkeys(HEAD_COUNT.findall(text)) if int(found) != count]
    points = [float(item["points"]) for _, item in named if "points" in item]
    if len(points) == count:
        total = round(sum(points), 1)
        notes += [f"머리에 적힌 {found}점이 지시의 배점 합계 {total:g}점과 다릅니다. 확인해 주세요"
                  for found in dict.fromkeys(HEAD_TOTAL.findall(text)) if float(found) != total]
    return notes


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    return [str(value)]


def _bare(text: str) -> str:
    return re.sub(r"\s", "", text.replace(OBJECT, ""))


def _check_no_old_text(form: Form, exam: ExamForm, body: str, spec: dict) -> None:
    """복제가 옛 글을 끌고 오지 않았는지 마지막에 본다. 교사가 같은 글을 다시 쓴 경우는 뺀다."""
    old = {_bare(p.text) for p in form.paragraphs
           if p.section == exam.section and exam.body_start <= p.start < exam.body_end and p.kind != MEMO}
    new = _bare(unescape(re.sub(r"<[^>]+>", "", body)))
    given = _bare("".join(_strings(spec)))
    left = [text for text in old if len(text) >= MIN_OLD_TEXT and text in new and text not in given]
    if left:
        raise FillError(f"양식의 옛 문항 글이 결과에 남음({len(left)}곳). 이 양식은 도구가 지우지 못합니다")


def _drop_unused_pictures(form: Form, entries: dict[str, bytes]) -> tuple[Form, dict[str, bytes]]:
    """옛 문항 그림이 파일 안에 남지 않게, 어디서도 쓰지 않는 그림을 항목과 목록에서 지운다."""
    used = {ref for name, data in entries.items() if name.endswith(".xml") for ref in PICTURE_REF.findall(
        data.decode("utf-8", "ignore"))}
    manifest_name = "Contents/content.hpf"
    if manifest_name not in entries:
        raise FillError("양식에 Contents/content.hpf가 없어 채울 수 없음. 한글에서 hwpx로 다시 저장한 파일을 주세요")
    manifest = entries[manifest_name].decode("utf-8")
    dropped = set()
    for found in MANIFEST_ITEM.finditer(manifest):
        item_id = re.search(r'\bid="([^"]+)"', found.group(0))
        if item_id and item_id.group(1) not in used:
            dropped.add(found.group(1))
            manifest = manifest.replace(found.group(0), "")
    kept = {name: data for name, data in entries.items() if name not in dropped}
    kept[manifest_name] = manifest.encode("utf-8")
    infos = tuple(info for info in form.infos if info.filename not in dropped)
    return replace(form, infos=infos), kept


def _strip_marks(entries: dict[str, bytes], names: tuple[str, ...]) -> dict[str, bytes]:
    cleaned = dict(entries)
    for name in names:
        cleaned[name] = MARKPEN_TAG.sub("", entries[name].decode("utf-8")).encode("utf-8")
    return cleaned


def fill_exam(source: Path, spec: dict, target: Path, student: bool = False, base_dir: Path | None = None) -> Result:
    """양식의 문항 틀을 복제해 target에 새 파일을 만든다. 실패하면 FillError.

    그림의 상대 경로는 base_dir(지시 파일이 있는 폴더)에서 먼저 찾고, 없으면 실행한 폴더에서 찾는다."""
    source, target = Path(source), Path(target)
    if target.exists():
        if source.exists() and target.samefile(source):
            raise FillError("원본 양식을 덮어쓸 수 없음. 결과 파일 이름을 다르게 적어 주세요")
        raise FillError(f"이미 있는 파일이라 덮어쓰지 않음: {target.name}. 다른 이름을 적어 주세요")
    if not target.parent.is_dir():
        raise FillError(f"결과를 저장할 폴더가 없음: {target.parent}")
    fills, named = _validate(spec)
    form = read_form(source)
    exam = read_exam(form)
    xml = form.section_xml[exam.section]
    header_xml = form.entries[HEADER_ENTRY].decode("utf-8")
    notes = list(equation_text_warnings(spec.get("items")))
    notes += choice_order_notes(named)
    manifest = form.entries.get(MANIFEST, b"").decode("utf-8", "ignore")
    writer = Writer(exam, xml, header_xml, student, manifest, base_dir)
    body, count = _build_body(writer, named, notes)
    if writer.keep_failed:
        notes.append(NO_KEEP_NOTE)
    outside = _outside_plan(form, exam, fills)
    notes += _head_notes(form, exam, outside, named, count)
    entries = changed_entries(form, [*outside, Edit(exam.section, exam.body_start, exam.body_end, body)])
    entries[HEADER_ENTRY] = writer.media.header(writer.header_with_shapes(header_xml)).encode("utf-8")
    _check_no_old_text(form, exam, body, spec)
    entries = fill_page_numbers(entries, form.section_names)
    if student:
        entries = _strip_marks(entries, form.section_names)
        if any(b"hp:markpen" in entries[section] for section in form.section_names):
            raise FillError("학생용에 정답 표시가 남음. 파일을 만들지 않았습니다")
    if PREVIEW_IMAGE in entries:
        entries[PREVIEW_IMAGE] = BLANK_PNG
    form, entries = _drop_unused_pictures(form, entries)
    infos, entries = add_pictures(form.infos, entries, writer.media.pictures)
    form = replace(form, infos=infos)
    publish(source, form, entries, target)
    return Result(count, tuple(dict.fromkeys(notes)))


# ---------------------------------------------------------------- 명령줄

def _run_fill(source: str, spec_path: str, target: str, student: bool) -> str:
    try:
        spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise FillError(f"지시 파일을 읽을 수 없음: {error}") from error
    result = fill_exam(Path(source), spec, Path(target), student, Path(spec_path).resolve().parent)
    kind = "학생용, 정답 표시 없음" if student else "원안지"
    lines = [f"완료: {target} (문항 {result.items}개, {kind}). 쪽과 단이 넘어가는 자리는 한글에서 확인해 주세요",
             *(f"참고: {note}" for note in result.notes)]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """통과면 0, 실패면 1, 사용법이 틀리면 2."""
    args = list(sys.argv[1:] if argv is None else argv)
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    student = "--student" in args
    if student:
        args.remove("--student")
    try:
        if len(args) == 2 and args[0] == "--inspect" and not student:
            sys.stdout.write(inspect_exam(Path(args[1])))
        elif len(args) == 3 and not args[0].startswith("--"):
            sys.stdout.write(_run_fill(*args, student))
        else:
            sys.stdout.write("사용법: python fill_exam.py --inspect 양식.hwpx\n"
                             "        python fill_exam.py 양식.hwpx 지시.json 결과.hwpx [--student]\n")
            return 2
    except FillError as error:
        sys.stdout.write(f"{error}\n")
        return 1
    except OSError as error:
        sys.stdout.write(file_error_message(error) + "\n")
        return 1
    except Exception as error:  # 예상 밖 양식 구조도 추적 로그 대신 안내 문장으로 알린다
        sys.stdout.write(f"내부 오류: 예상하지 못한 양식입니다 ({type(error).__name__})\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
