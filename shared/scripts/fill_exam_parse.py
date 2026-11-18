"""fill_exam.py의 시험지 양식 읽기. 표준 라이브러리만 쓴다.

양식의 본문을 머리, 문항 틀, 꼬리로 나누고, 문항 틀이 어떤 유형인지(선택지를 어떤 표로 넣는지) 읽는다.
글자를 고치지 않고 원문 구간만 기록한다. 글자 읽기는 fill_hwpx_parse.py를 그대로 쓴다.
"""

from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction
from dataclasses import dataclass
from pathlib import Path

from fill_hwpx import FillError, Form, cell_line, paragraph_line, read_form
from fill_hwpx_parse import BODY, OBJECT, Cell, Paragraph, Table

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
SHORT_TABLE, COMBO_TABLE, GRID_TABLE, PARAGRAPHS, WRITTEN = (
    "short_table", "combo_table", "grid_table", "paragraphs", "written")
KIND_NAMES = {SHORT_TABLE: "짧은 선택지 표", COMBO_TABLE: "합답형 선택지 표", GRID_TABLE: "표형 선지",
              PARAGRAPHS: "문단 선택지", WRITTEN: "서답형"}
ITEM_START = re.compile(r"\s*(\[?\s*서[답술]형\s*)?(\d{1,3})(\s*[.)\]])")
PASSAGE_START = re.compile(r"\s*\[\s*\d{1,3}\s*[~∼～\-]\s*\d{1,3}\s*\]")
PASSAGE_LABEL = re.compile(r"\s*\(\S{1,2}\)\s*$")
POINTS_AT_END = re.compile(r"\[\s*\d+(?:\.\d+)?\s*점\s*\]\s*$")
MARKPEN = re.compile(r'<hp:markpenBegin\b[^>]*?color="([^"]*)"')
CHAR_SHAPE = re.compile(r'<hh:charPr id="(\d+)".*?</hh:charPr>', re.S)
RUN_TAG = re.compile(r'<hp:run charPrIDRef="(\d+)"')
COLUMN_SETTING = re.compile(r'<hp:colPr\b[^>]*?colCount="(\d+)"')
BOGI_LABEL = "<보기>"
MIN_CHOICES = 2


@dataclass(frozen=True)
class Mark:
    """양식의 정답 표시 방식. kind는 markpen(형광펜) 또는 char(정답만 다른 글자 모양)."""
    kind: str
    value: str


@dataclass(frozen=True)
class TableBlock:
    """표 하나를 담은 본문 문단."""
    paragraph: Paragraph
    table: Table


@dataclass(frozen=True)
class Frame:
    """양식의 문항 하나. 복제할 틀이 된다."""
    kind: str
    number: int
    prefix: str                             # "서답형 " 같은 번호 앞 글
    stem: Paragraph
    box: TableBlock | None
    bogi: TableBlock | None
    choice_table: TableBlock | None
    choice_paragraphs: tuple[Paragraph, ...]
    picture: bool
    spacer: Paragraph | None

    @property
    def slots(self) -> tuple[tuple[Paragraph, ...], ...]:
        """선택지 자리마다의 문단. 표형 선지는 한 행의 모든 칸이 한 자리다."""
        if self.kind == PARAGRAPHS:
            return tuple((paragraph,) for paragraph in self.choice_paragraphs)
        if self.kind == GRID_TABLE:
            rows = _rows(self.choice_table.table)[1:]
            return tuple(tuple(p for cell in row for p in cell.paragraphs) for row in rows)
        if self.kind in (SHORT_TABLE, COMBO_TABLE):
            return tuple(tuple(cell.paragraphs) for cell in choice_cells(self.choice_table.table))
        return ()


@dataclass(frozen=True)
class PassageFrame:
    """공통 지문 틀: [1~3] 문단, (가) 표지 문단들, 본문 문단들."""
    lead: Paragraph
    labels: tuple[Paragraph, ...]
    bodies: tuple[Paragraph, ...]
    gap: Paragraph | None
    spacer: Paragraph | None


@dataclass(frozen=True)
class ExamForm:
    section: int
    body_start: int
    body_end: int
    frames: tuple[Frame, ...]
    passages: tuple[PassageFrame, ...]
    tail: tuple[Paragraph, ...]
    columns: int
    mark: Mark | None
    marked_items: int
    other_marks: int                        # 머리와 꼬리의 형광펜 (정답 표시가 아니다)

    def frame_of(self, kind: str) -> Frame | None:
        return next((frame for frame in self.frames if frame.kind == kind), None)

    @property
    def box(self) -> TableBlock | None:
        """자료 상자 틀. 문단 하나로 된 상자를 먼저 쓴다 (특별한 문단 모양이 덜 섞여 있다)."""
        boxes = [frame.box for frame in self.frames if frame.box]
        simple = [box for box in boxes if len(box_body(box.table).paragraphs) == 1]
        return next(iter(simple + boxes), None)

    @property
    def bogi(self) -> TableBlock | None:
        return next((frame.bogi for frame in self.frames if frame.bogi), None)

    @property
    def spacer(self) -> Paragraph | None:
        return next((frame.spacer for frame in self.frames if frame.spacer), None)


class CharShapes:
    """header.xml의 글자 모양. 같은 모양의 굵은 글자, 밑줄 글자를 찾을 때 쓴다."""

    def __init__(self, header_xml: str) -> None:
        self.shapes = {match.group(1): match.group(0) for match in CHAR_SHAPE.finditer(header_xml)}

    def _attribute(self, char: str, name: str, default: str) -> str:
        found = re.search(rf'\b{name}="([^"]*)"', self.shapes.get(char, ""))
        return found.group(1) if found else default

    def height(self, char: str) -> int:
        return int(self._attribute(char, "height", "1000"))

    def spacing(self, char: str) -> int:
        found = re.search(r'<hh:spacing hangul="(-?\d+)"', self.shapes.get(char, ""))
        return abs(int(found.group(1))) if found else 0

    def look(self, char: str) -> tuple[str, str]:
        return self._attribute(char, "textColor", ""), self._attribute(char, "shadeColor", "")

    def _face(self, char: str, parts: str) -> tuple:
        """굵기와 밑줄을 뺀 생김새. parts는 비교할 항목의 이름들이다."""
        shape = self.shapes.get(char, "")
        return self.height(char), self.look(char), re.findall(rf"<hh:(?:{parts}) [^>]*>", shape)

    def variant(self, char: str, bold: bool, underline: bool) -> str | None:
        """char와 같고 굵기나 밑줄만 다른 글자 모양 번호. 자간까지 같은 것을 먼저, 없으면 글꼴이 같은 것. 없으면 None."""
        for parts in ("fontRef|ratio|spacing|relSz|offset", "fontRef"):
            base = self._face(char, parts)
            for number, shape in self.shapes.items():
                has_bold = re.search(r"<hh:bold\s*/>", shape) is not None
                has_line = re.search(r'<hh:underline type="(?!NONE)', shape) is not None
                if (has_bold, has_line) == (bold, underline) and self._face(number, parts) == base:
                    return number
        return None


# ---------------------------------------------------------------- 표와 문단 읽기

def _rows(table: Table) -> list[list[Cell]]:
    rows: dict[int, list[Cell]] = {}
    for cell in table.cells:
        rows.setdefault(cell.row, []).append(cell)
    return [sorted(rows[row], key=lambda cell: cell.col) for row in sorted(rows)]


def _is_blank(paragraph: Paragraph) -> bool:
    return not paragraph.text.strip()


def _circled(text: str) -> bool:
    return text.lstrip()[:1] in CIRCLED and bool(text.strip())


def choice_cells(table: Table) -> list[Cell]:
    return [cell for cell in sorted(table.cells, key=lambda cell: (cell.row, cell.col)) if _circled(cell.text)]


def _choice_kind(table: Table) -> str | None:
    """선택지를 담은 표면 유형을, 아니면 None을 돌려준다."""
    cells = choice_cells(table)
    if len(cells) < MIN_CHOICES:
        return None
    if table.rows >= 3 and table.cols >= 2 and all(cell.col == 0 for cell in cells) and cells[0].row == 1:
        return GRID_TABLE
    return SHORT_TABLE if table.rows == 1 else COMBO_TABLE


def _is_bogi(table: Table) -> bool:
    return any(BOGI_LABEL in re.sub(r"\s", "", cell.text) for cell in table.cells) and table.rows * table.cols > 1


def bogi_body(table: Table) -> Cell:
    """<보기> 표에서 ㄱ, ㄴ 글이 드는 칸. 글이 가장 긴 칸이다."""
    return max(table.cells, key=lambda cell: len(cell.text.strip()) if BOGI_LABEL not in
               re.sub(r"\s", "", cell.text) else -1)


def box_body(table: Table) -> Cell:
    """자료 상자에서 글이 드는 칸. 1칸 표는 그 칸, 여백 칸으로 둘러싼 상자는 글이 가장 긴 칸이다."""
    if len(table.cells) == 1:
        return table.cells[0]
    if not any(cell.text.strip() for cell in table.cells):      # 빈 답 상자: 가운데 칸
        middle = next((cell for cell in table.cells if (cell.row, cell.col) == (table.rows // 2, table.cols // 2)), None)
        return middle or table.cells[0]
    return max(table.cells, key=lambda cell: len(cell.text.strip()))


def _is_framed_box(table: Table) -> bool:
    """여백 줄·칸으로 둘러싼 자료 상자: 3x3 이하 표에서 글이 든 칸이 하나뿐이다."""
    if table.rows > 3 or table.cols > 3 or len(table.cells) < 2:
        return False
    return sum(1 for cell in table.cells if cell.text.strip()) <= 1


def is_bogi_label(cell: Cell) -> bool:
    return BOGI_LABEL in re.sub(r"\s", "", cell.text)


def _table_of(paragraph: Paragraph, tables: list[Table]) -> Table | None:
    return next((table for table in tables if paragraph.start < table.start < paragraph.end), None)


def _top_paragraphs(form: Form, section: int) -> list[Paragraph]:
    return [p for p in form.paragraphs if p.section == section and p.kind == BODY and p.cell is None]


def run_counts(paragraph: Paragraph, xml: str, first: int = 0) -> Counter:
    """문단의 글자 모양별 글자 수. first번째 글자부터 센다. 빈칸은 세지 않는다."""
    starts = [(match.start(), match.group(1)) for match in RUN_TAG.finditer(xml, paragraph.start, paragraph.end)]
    counts: Counter = Counter()
    for item in paragraph.chars[first:]:
        if item.ch.strip() and item.ch != OBJECT:
            owner = [char for start, char in starts if start < item.start]
            if owner:
                counts[owner[-1]] += 1
    if not counts and starts:
        counts[starts[0][1]] = 1
    return counts


def plainest(counts: Counter, shapes: CharShapes) -> str:
    """가장 평범한 글자 모양: 자간을 줄이지 않았고 많이 쓴 것. 양식이 칸에 맞춰 줄인 자리를 따라가지 않게."""
    return min(counts, key=lambda char: (shapes.spacing(char), -counts[char], int(char)))


# ---------------------------------------------------------------- 문항 틀 나누기

def _item_starts(top: list[Paragraph]) -> list[tuple[int, str, int]]:
    """(문단 위치, 번호 앞 글, 번호) 목록. 번호가 이어지거나 1로 돌아갈 때만 문항으로 본다.

    글 속의 "4. 19"처럼 번호처럼 보이는 문단을 문항으로 잘못 읽지 않게 한다. 지문은 번호가 -1이다."""
    starts: list[tuple[int, str, int]] = []
    expected: dict[str, int] = {}
    for index, paragraph in enumerate(top):
        text = paragraph.text
        if PASSAGE_START.match(text):
            starts.append((index, "", -1))
            continue
        found = ITEM_START.match(text)
        if not found:
            continue
        prefix, number = re.sub(r"\s", "", found.group(1) or ""), int(found.group(2))
        if number == 1 or number == expected.get(prefix):
            starts.append((index, prefix, number))
            expected[prefix] = number + 1
    return starts


def _classify(number: int, prefix: str, stem: Paragraph, members: list[Paragraph], tables: list[Table]) -> Frame:
    parts: dict = {"box": None, "bogi": None, "choice_table": None, "kind": WRITTEN}
    paragraphs: list[Paragraph] = []
    spacer = None
    picture = False
    for paragraph in members:
        table = _table_of(paragraph, tables)
        if table is not None:
            _classify_table(parts, TableBlock(paragraph, table))
        elif "hp:pic" in paragraph.objects:
            picture = True
        elif _circled(paragraph.text):
            paragraphs.append(paragraph)
        elif _is_blank(paragraph) and spacer is None:
            spacer = paragraph
    if parts["choice_table"] is None and len(paragraphs) >= MIN_CHOICES:
        parts["kind"] = PARAGRAPHS
    return Frame(parts["kind"], number, prefix, stem, parts["box"], parts["bogi"], parts["choice_table"],
                 tuple(paragraphs), picture, spacer)


def _classify_table(parts: dict, block: TableBlock) -> None:
    kind = _choice_kind(block.table)
    if kind is not None:
        parts.update(kind=kind, choice_table=block)
    elif _is_bogi(block.table):
        parts["bogi"] = parts["bogi"] or block
    elif block.table.rows == block.table.cols == 1 or _is_framed_box(block.table):
        parts["box"] = parts["box"] or block


def _passage(lead: Paragraph, members: list[Paragraph]) -> PassageFrame:
    labels, bodies, blanks = [], [], []
    for paragraph in members:
        if _is_blank(paragraph):
            blanks.append(paragraph)
        elif PASSAGE_LABEL.match(paragraph.text):
            labels.append(paragraph)
        elif not paragraph.objects:
            bodies.append(paragraph)
    gap = next((p for p in blanks[:-1]), blanks[0] if blanks else None)
    return PassageFrame(lead, tuple(labels), tuple(bodies), gap, blanks[-1] if blanks else None)


def _split_tail(members: list[Paragraph], xml: str) -> tuple[list[Paragraph], list[Paragraph]]:
    """마지막 문항 뒤의 꼬리(양식 안내 상자 등)를 가른다. 빈 문단 뒤에 있고 선택지와 정답 표시가 없어야 꼬리다."""
    last = len(members)
    while last and _is_blank(members[last - 1]):
        last -= 1
    start = last
    while start and not _is_blank(members[start - 1]):
        start -= 1
    if start == 0 or start == last:
        return members, []
    candidates = members[start:last]
    raw = xml[candidates[0].start:candidates[-1].end]
    if "markpenBegin" in raw or any(_circled(p.text) for p in candidates) or CIRCLED[0] in raw:
        return members, []
    return members[:start], candidates


def _find_section(form: Form) -> tuple[int, list[Paragraph], list[tuple[int, str, int]]]:
    found = []
    for section in range(len(form.section_names)):
        top = _top_paragraphs(form, section)
        starts = _item_starts(top)
        if any(number >= 0 for _, _, number in starts):
            found.append((section, top, starts))
    if not found:
        raise FillError('양식에서 문항을 찾지 못함. 문항은 "1." 처럼 번호로 시작하는 문단이어야 합니다')
    if len(found) > 1:
        raise FillError("문항이 여러 구역에 나뉜 양식은 채울 수 없음. 한글에서 한 구역으로 합쳐 저장해 주세요")
    return found[0]


def _drop_leading_notes(frames: list[Frame]) -> list[Frame]:
    """선택지 없는 번호 문단이 맨 앞에 있으면 문항이 아니라 유의사항이다."""
    while frames and frames[0].kind == WRITTEN and not frames[0].prefix:
        frames = frames[1:]
    return frames


def _exam_marks(frames: list[Frame], xml: str, shapes: CharShapes) -> tuple[Mark | None, int]:
    pens = []
    for frame in frames:
        pens += [found for slot in frame.slots for p in slot for found in MARKPEN.findall(xml[p.start:p.end])]
    if pens:
        count = sum(any("markpenBegin" in xml[p.start:p.end] for slot in frame.slots for p in slot)
                    for frame in frames)
        return Mark("markpen", Counter(pens).most_common(1)[0][0]), count
    return _char_mark(frames, xml, shapes)


def _char_mark(frames: list[Frame], xml: str, shapes: CharShapes) -> tuple[Mark | None, int]:
    """형광펜이 없는 양식: 선택지 하나만 글자색이나 음영이 다르면 그것이 정답 표시다."""
    found: Counter = Counter()
    for frame in frames:
        mains = [plainest(sum((run_counts(p, xml) for p in slot), Counter()), shapes)
                 for slot in frame.slots if any(p.chars for p in slot)]
        common = Counter(mains).most_common(1)[0][0] if mains else ""
        odd = [char for char in mains if shapes.look(char) != shapes.look(common)]
        if len(mains) >= MIN_CHOICES and len(odd) == 1:
            found[odd[0]] += 1
    return (Mark("char", found.most_common(1)[0][0]), sum(found.values())) if found else (None, 0)


def read_exam(form: Form) -> ExamForm:
    """양식을 머리, 문항 틀, 꼬리로 나눈다. 문항을 찾지 못하면 FillError."""
    section, top, starts = _find_section(form)
    xml = form.section_xml[section]
    shapes = CharShapes(form.entries["Contents/header.xml"].decode("utf-8"))
    tables = [table for table in form.tables if table.section == section]
    frames: list[Frame] = []
    passages: list[tuple[int, PassageFrame]] = []
    tail: list[Paragraph] = []
    for position, (index, prefix, number) in enumerate(starts):
        is_last = position + 1 == len(starts)
        members = top[index + 1:len(top) if is_last else starts[position + 1][0]]
        if is_last:
            members, tail = _split_tail(members, xml)
        if number < 0:
            passages.append((index, _passage(top[index], members)))
        else:
            frames.append(_classify(number, prefix, top[index], members, tables))
    frames = _drop_leading_notes(frames)
    if not frames:
        raise FillError('양식에서 문항을 찾지 못함. 문항은 "1." 처럼 번호로 시작하는 문단이어야 합니다')
    kept = [frame for _, frame in passages if frame.lead.start >= _first_start(frames, passages)]
    body_start = min([frames[0].stem.start, *(frame.lead.start for frame in kept)])
    body_end = tail[0].start if tail else top[-1].end
    _refuse_column_change(top, body_start, body_end, xml)
    mark, marked = _exam_marks(frames, xml, shapes)
    columns = COLUMN_SETTING.findall(xml[:body_end])
    outside = xml[:body_start] + xml[body_end:]
    return ExamForm(section, body_start, body_end, tuple(frames), tuple(kept), tuple(tail),
                    int(columns[-1]) if columns else 1, mark, marked, len(MARKPEN.findall(outside)))


def _first_start(frames: list[Frame], passages: list[tuple[int, PassageFrame]]) -> int:
    """첫 문항 바로 앞의 지문까지를 본문으로 본다."""
    stem = frames[0].stem.start
    before = [frame.lead.start for _, frame in passages if frame.lead.start < stem]
    return max(before) if before else stem


def _refuse_column_change(top: list[Paragraph], start: int, end: int, xml: str) -> None:
    inner = [p for p in top if start <= p.start < end]
    if any("<hp:colPr" in xml[p.start:p.end] for p in inner[1:]):
        raise FillError("문항 사이에서 단 설정이 바뀌는 양식은 채울 수 없음. 한글에서 단 설정을 문항 앞으로 옮겨 주세요")


# ---------------------------------------------------------------- 살펴보기

def _mark_line(exam: ExamForm) -> str:
    extra = f". 머리·꼬리의 형광펜 {exam.other_marks}곳은 정답 표시가 아님 (원안지는 그대로, 학생용은 지움)" \
        if exam.other_marks else ""
    if exam.mark is None:
        return f"정답 표시: 없음 (결과에도 표시하지 않음){extra}"
    name = f"형광펜 {exam.mark.value}" if exam.mark.kind == "markpen" else f"글자 모양 {exam.mark.value}번"
    return f"정답 표시: {name}, 문항 {exam.marked_items}개{extra}"


def _frame_line(frame: Frame) -> str:
    extras = [name for name, on in (("자료 상자", frame.box), ("<보기>", frame.bogi), ("그림", frame.picture)) if on]
    shape = ""
    if frame.choice_table is not None:
        shape = f" 표 {frame.choice_table.table.rows}×{frame.choice_table.table.cols}"
    more = f" + {', '.join(extras)}" if extras else ""
    return f"  {frame.prefix}{frame.number}번: {frame.kind}{shape}{more}"


def _in_body(exam: ExamForm, section: int, start: int) -> bool:
    return section == exam.section and exam.body_start <= start < exam.body_end


def _outside_lines(form: Form, exam: ExamForm) -> list[str]:
    items = [(p.section, p.start, paragraph_line(p)) for p in form.paragraphs
             if p.cell is None and not _in_body(exam, p.section, p.start) and p.text.strip()]
    for table in form.tables:
        if not _in_body(exam, table.section, table.start):
            items.append((table.section, table.start, f"표 {table.number} ({table.rows}행 × {table.cols}칸)"))
            items += [(table.section, cell.start, cell_line(cell)) for cell in table.cells]
    return [line for _, _, line in sorted(items, key=lambda item: item[:2])]


def inspect_exam(path: Path) -> str:
    """머리와 꼬리의 번호, 문항 틀의 유형을 보여 준다. 문항 글은 옮기지 않는다."""
    form = read_form(Path(path))
    exam = read_exam(form)
    counts = Counter(frame.kind for frame in exam.frames)
    lines = [f"단 수: {exam.columns}단", f"문항: {len(exam.frames)}개", f"공통 지문: {len(exam.passages)}곳",
             "유형별 틀:"]
    lines += [f"  {kind} ({KIND_NAMES[kind]}): {count}개" for kind, count in counts.items()]
    lines += [f"  자료 상자: {sum(1 for f in exam.frames if f.box)}개, <보기>: {sum(1 for f in exam.frames if f.bogi)}개, "
              f"그림: {sum(1 for f in exam.frames if f.picture)}개 (그림은 picture, 대화 장면은 dialogue로 넣을 수 있음)"]
    lines += [_mark_line(exam), "문항별 틀:"]
    lines += [_frame_line(frame) for frame in exam.frames]
    lines += ["머리와 꼬리 (fills에 이 번호를 씀):", *_outside_lines(form, exam)]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 줄 너비 어림 (배점이 줄 끝에서 쪼개지지 않게)

def _column_width(xml: str, upto: int | None = None) -> int | None:
    """본문 단 하나의 너비 (HWPUNIT). upto 앞(첫 문항 문단까지)에서 마지막으로 선 단 설정을 쓴다.
    머리는 1단이고 문항부터 2단인 양식도 맞는다. 구역 설정을 읽지 못하면 None."""
    page = re.search(r'<hp:pagePr\b[^>]*?\bwidth="(\d+)"', xml)
    margin = re.search(r'<hp:margin\b[^>]*?\bleft="(\d+)"[^>]*?\bright="(\d+)"', xml)
    if page is None or margin is None:
        return None
    width = int(page.group(1)) - int(margin.group(1)) - int(margin.group(2))
    settings = list(re.finditer(r'<hp:colPr\b[^>]*?\bcolCount="(\d+)"[^>]*?\bsameGap="(\d+)"',
                                xml if upto is None else xml[:upto]))
    columns = settings[-1] if settings else None
    if columns and int(columns.group(1)) > 1:
        count = int(columns.group(1))
        width = (width - int(columns.group(2)) * (count - 1)) // count
    return width


NARROW_LATIN, WIDE_LATIN = "iljtfrI'", "mwMW"     # 영문 글자 폭: 좁은 글자 0.3em, 넓은 글자 0.85em


def _text_width(text: str, em: int) -> float:
    """글 너비 어림 (HWPUNIT). 한글·한자·전각 1em, 빈칸 0.3em, 영문·숫자 0.55em, 문장 부호 0.35em."""
    total = 0.0
    for char in text:
        if char == " ":
            total += 0.3
        elif ord(char) > 0x2E7F or char in CIRCLED:
            total += 1.0
        elif char in NARROW_LATIN:
            total += 0.3
        elif char in WIDE_LATIN:
            total += 0.85
        elif char.isascii() and char.isupper():
            total += 0.65
        elif char.isalnum():
            total += 0.55
        else:
            total += 0.35
    return total * em


def _last_line_room(text: str, width: int, indent: int, em: int) -> float:
    """어절 단위로 줄을 채웠을 때 마지막 줄에 남는 너비. 둘째 줄부터는 내어쓰기만큼 좁다."""
    line, room = 0.0, float(width)
    for word in text.split(" "):
        size = _text_width(word, em)
        gap = _text_width(" ", em) if line else 0.0
        if line and line + gap + size > room:
            line, room = size, float(width - indent)
        else:
            line += gap + size
    return room - line


# ---------------------------------------------------------------- 선지 배치와 정답 분포 알림

LABEL_START = re.compile(r"\s*(?:[㉠-㉭ⓐ-ⓩ]|\([가-하A-Za-z0-9]\)|[갑을병정무]\b|학생\s*\d|[A-E]\s*[:.)])")
NUMBER_CHOICE = re.compile(r"\s*[-−]?\d+(?:[.,]\d+)?\s*(?:[^\s\d].{0,3})?\s*$")
CONSONANT_SET = re.compile(r"^[ㄱ-ㅎ](?:\s*,\s*[ㄱ-ㅎ])*$")
STEP_SLACK = 0.5                            # 이만큼(em)은 짧아져도 계단으로 본다 (어림 오차)


def _choice_plain(value: object) -> str:
    return re.sub(r"\*\*|__|\{\{|\}\}", "", str(value)).strip()


def _number_value(text: str) -> float | None:
    found = re.match(r"\s*([-−]?\d+(?:[.,]\d+)?)", text)
    return float(found.group(1).replace("−", "-").replace(",", "")) if found else None


EXACT_NUMBER = re.compile(r"([-−]?)\s*(?:(\d+)\s+)?(\d+)\s*/\s*(\d+)|([-−]?\d+(?:[.,]\d+)?)")


def _exact_value(raw: object) -> Fraction | None:
    """정수·소수·분수·대분수(음수 포함)를 정확한 값으로 읽는다. {{3/4}}, {{1 7/12}}, {{-2/3}}처럼 한글 수식 꼴도 받는다.
    제곱근 같은 수식이나 단위가 붙은 글은 읽지 못해 None."""
    text = _choice_plain(raw)
    found = EXACT_NUMBER.fullmatch(text)
    if found is None:
        return None
    sign, whole, top, bottom, plain = found.groups()
    if plain is not None:
        return Fraction(plain.replace("−", "-").replace(",", ""))
    if int(bottom) == 0:
        return None
    value = Fraction(int(whole or 0) * int(bottom) + int(top), int(bottom))
    return -value if sign else value


def _has_math(raw: object) -> bool:
    return "{{" in str(raw)


PAIR_SPLIT = re.compile(r"\s[-–—]\s")       # "(A) - (B)"처럼 칸을 나눈 짝 선지


def _heads_grouped(texts: list[str]) -> bool:
    """짝 선지의 앞 칸이 같은 것끼리 이어져 있는가 (cools, cools, warms, cleans, warms는 아니다)."""
    heads = [PAIR_SPLIT.split(text, maxsplit=1)[0].strip() for text in texts]
    seen: set[str] = set()
    for index, head in enumerate(heads):
        if head in seen and heads[index - 1] != head:
            return False
        seen.add(head)
    return True


REPEAT_MIN = 4                              # 되풀이로 볼 가장 짧은 정답 번호 순서
REPEAT_CHANCE = 0.1                         # 무작위 배열에서 우연히 되풀이가 나올 어림 확률이 이보다 크면 길이를 늘린다


def _repeat_min(count: int, size: int) -> int:
    """우연한 되풀이 알림을 줄이는 최소 길이. 20문항 5지선다는 5, 4지선다는 6 (무작위 2000회 흉내로 알림 비율을 확인)."""
    length = REPEAT_MIN
    while length < count and (count - length) ** 2 / 2 * size ** -length > REPEAT_CHANCE:
        length += 1
    return length


def _repeated_run(sequence: list[int], shortest: int = REPEAT_MIN) -> tuple[int, int, int] | None:
    """겹치지 않고 두 번 나오는 가장 긴 정답 번호 순서 (길이, 첫 자리, 둘째 자리). shortest보다 짧거나
    한 번호만 이어진 순서(③③③③, "이어짐" 알림이 따로 있음)면 None."""
    for length in range(len(sequence) // 2, shortest - 1, -1):
        for first in range(len(sequence) - 2 * length + 1):
            run = sequence[first:first + length]
            if len(set(run)) == 1:
                continue
            for second in range(first + length, len(sequence) - length + 1):
                if sequence[second:second + length] == run:
                    return length, first, second
    return None


def _order_note(where: str, choices: list) -> str | None:
    """선지 순서 알림 한 줄. 표지·합답형은 보지 않고, 수 선지는 크기, 짝 선지는 앞 칸 묶음, 나머지는 계단식을 본다."""
    texts = [_choice_plain(choice) for choice in choices]
    if any(LABEL_START.match(text) for text in texts) or all(CONSONANT_SET.match(text) for text in texts):
        return None
    exact = [_exact_value(choice) for choice in choices]
    if all(value is not None for value in exact):
        return None if exact == sorted(exact) else f"{where}: 수 선지는 작은 수부터 놓아 주세요"
    if any(_has_math(choice) for choice in choices):
        return None                             # 값으로 읽지 못하는 수식(제곱근 등)이 섞이면 순서를 점검하지 않는다
    if all(NUMBER_CHOICE.match(text) for text in texts):
        values = [_number_value(text) for text in texts]
        bad = all(value is not None for value in values) and values != sorted(values)
        return f"{where}: 수 선지는 작은 수부터 놓아 주세요" if bad else None
    if all(PAIR_SPLIT.search(text) for text in texts):
        return None if _heads_grouped(texts) else f"{where}: 짝 선지는 앞 칸이 같은 것끼리 붙여 놓아 주세요"
    widths = [_text_width(text, 1) for text in texts]
    if any(later < earlier - STEP_SLACK for earlier, later in zip(widths, widths[1:])):
        return f"{where}: 선지를 짧은 것부터 긴 것 순서(계단식)로 놓아 주세요. 정답 자리는 오답 길이를 고쳐 맞춥니다"
    return None


def _answer_notes(answered: list[tuple[str, int, int]]) -> list[str]:
    """(문항 이름, 선지 수, 정답) 목록으로 같은 번호 이어짐, 순서 되풀이, 번호 분포를 알린다."""
    notes: list[str] = []
    run_length, run_answer = 0, None
    for where, _, answer in answered:          # 이어짐은 선지 수와 상관없이 문항 순서대로 센다
        run_length = run_length + 1 if answer == run_answer else 1
        run_answer = answer
        if run_length == 4:
            notes.append(f"{where}: 정답 {CIRCLED[answer - 1]}이 4문항 이어짐. 자리를 바꿔 주세요")
    sequence = [answer for _, _, answer in answered]
    sizes = Counter(size for _, size, _ in answered)
    shortest = _repeat_min(len(sequence), sizes.most_common(1)[0][0]) if sizes else REPEAT_MIN
    repeat = _repeated_run(sequence, shortest)
    if repeat:
        length, first, second = repeat
        shown = "".join(CIRCLED[answer - 1] for answer in sequence[first:first + length])
        spans = [f"{answered[start][0]}~{answered[start + length - 1][0]}" for start in (first, second)]   # 실제 문항 이름
        notes.append(f"정답 번호 {shown}가 {spans[0]}과 {spans[1]}에서 같은 순서로 되풀이됨. 한쪽의 선지 자리를 바꿔 주세요")
    for size in sorted(sizes):
        group = Counter(answer for _, item_size, answer in answered if item_size == size)
        spread_values = [group.get(n, 0) for n in range(1, size + 1)]
        if sum(spread_values) >= 5 and max(spread_values) - min(spread_values) > 1:
            spread = " ".join(f"{CIRCLED[n - 1]}{group.get(n, 0)}" for n in range(1, size + 1))
            kind = "" if size == 5 else f"{size}지선다 "
            notes.append(f"{kind}정답 번호 분포가 고르지 않음({spread}). 번호마다 개수 차이가 1을 넘지 않게 맞춰 주세요")
    return notes


def choice_order_notes(named: list) -> list[str]:
    """선지 순서(계단식·수 크기·짝 선지 묶음)와 정답 번호(이어짐·되풀이·분포)를 알린다.

    표지(㉠, (가), 갑…)로 시작하는 선지, 합답형(ㄱ, ㄴ…) 선지는 길이로 보지 않는다."""
    notes: list[str] = []
    answered: list[tuple[str, int, int]] = []
    for where, item in named:
        choices = item.get("choices")
        if not choices or item.get("type") not in (SHORT_TABLE, COMBO_TABLE, PARAGRAPHS):
            continue
        answer = item.get("answer")
        if isinstance(answer, int) and len(choices) >= 3:
            answered.append((where, len(choices), answer))
        note = _order_note(where, choices)
        if note:
            notes.append(note)
    return notes + _answer_notes(answered)


# ---------------------------------------------------------------- 꼬리말 쪽 번호

FOOTER = re.compile(r"<hp:footer\b.*?</hp:footer>", re.S)
# 꼬리말의 "전체 (0)쪽 가운데 (0)쪽" 자리. 괄호가 없거나 "중"으로 적힌 양식도 받는다
PAGE_SLOT = re.compile(r"<hp:t>([^<]*?전체\s*\(?)0(\)?\s*쪽\s*(?:가운데|중)\s*\(?)0(\)?[^<]*)</hp:t>")
AUTO_NUM = ('<hp:ctrl><hp:autoNum num="1" numType="{}"><hp:autoNumFormat type="DIGIT" userChar="" '
            'prefixChar="" suffixChar="" supscript="0"/></hp:autoNum></hp:ctrl>')


def _page_number_text(found: re.Match) -> str:
    before, middle, after = found.groups()
    return (f"<hp:t>{before}</hp:t>{AUTO_NUM.format('TOTAL_PAGE')}<hp:t>{middle}</hp:t>"
            f"{AUTO_NUM.format('PAGE')}<hp:t>{after}</hp:t>")


def fill_page_numbers(entries: dict[str, bytes], names: tuple[str, ...]) -> dict[str, bytes]:
    """꼬리말의 "전체 (0)쪽 가운데 (0)쪽" 자리를 한글 자동 번호(전체 쪽 수, 지금 쪽)로 바꾼다.
    교사가 fills로 숫자를 적었거나 양식에 그 자리가 없으면 그대로 둔다."""
    filled = dict(entries)
    for name in names:
        xml = entries[name].decode("utf-8")
        filled[name] = FOOTER.sub(lambda footer: PAGE_SLOT.sub(_page_number_text, footer.group(0)), xml).encode("utf-8")
    return filled
