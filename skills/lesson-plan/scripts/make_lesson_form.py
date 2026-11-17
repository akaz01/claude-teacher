"""교수·학습 과정안(약안) 한글(hwpx) 만들기. 기본 양식 assets/lesson_plan_form.hwpx(학습과정안)를 바탕으로 한다.

양식의 머리 띠("Ⅰ" + 제목 줄), 수업 정보표, 교수·학습 활동표의 테두리·글꼴은 그대로 두고 칸과 행은 내용에 맞게 바꾼다.
- 활동표: 활동마다 한 행. 단계 칸(도입·전개·정리 등)은 세로로 합친다. 쪽을 넘어 나뉘고 머리행이 되풀이된다.
- 활동표 형식(layout): 분리형(split, 기본)은 단계|학습내용|교사|학생|자료 및 유의점|시간이고,
  통합형(integrated, 초등)은 단계|학습 형태|교수·학습 활동|시간|자료 및 유의점|평가이며 교수·학습 활동 한 칸에
  교사 발문(◉, ○)과 학생 예상 반응(-)을 함께 쓴다. 칸 너비 합과 선·음영·글꼴은 같다.
- 교사·학생·자료 칸은 줄마다 문단을 나누고, "◉ ", "○ ", "- " 뒤에 맞춰 내어쓴다.
- 수업 정보표: 학습 목표 아래에 성취기준·탐구 질문 같은 행을 더할 수 있다.
- 글 속 {{x^2+1}}은 한글 수식으로 들어간다.

입력 JSON:
{
  "title": "Ⅱ. 집합과 명제 – 2. 명제",            # 맨 위 "Ⅰ" 옆 제목 줄
  "mark": "Ⅰ",                                  # 제목 앞 상자 글 (선택, 기본 Ⅰ)
  "topic": "Ⅱ. 집합과 명제", "period": "1/8",      # 대주제, 차시
  "subtopic": "01 명제와 조건 (p.77~79)", "time": "50분",   # 소주제, 시간
  "goals": ["…를 설명할 수 있다.", "…를 구할 수 있다."], # 학습 목표 (번호는 자동)
  "rows": [{"label": "성취기준", "text": "[10공수2-02-04] …"}],   # 학습 목표 아래에 더할 행 (선택)
  "style": "전체 → 짝 → 개인",                       # 수업 형태
  "prep": {"teacher": "교과서, PPT", "student": "학습지"},
  "layout": "split",                                # 활동표 형식 (선택): "split"(분리형, 기본) 또는 "integrated"(통합형)
  "stages": [
    {"name": "도입", "steps": [
      {"content": "동기\\n유발", "teacher": "◉ …\\n“…?”", "student": "- …", "materials": "▣ PPT\\n※ …", "time": "3'"}]}
  ],
  # 통합형이면 활동마다 {"group": "전체", "activity": "◉ …\\n○ “…?”\\n- …", "time": "5'", "materials": "▣ …",
  # "assess": "관찰"}처럼 쓴다. activity에는 교사 발문과 학생 반응을 차례대로 한 칸에 쓰고, 없으면 teacher 글
  # 다음 줄에 student 글을 이어 쓴다. content(학습내용)를 주면 activity 첫 줄에 "◉ 학습내용"으로 들어간다. group은 학습 형태(전체·모둠·짝·개인), assess는 평가 방법(없으면 비움).
  "evaluation": [                                   # 평가 계획표 (선택). 없으면 표를 만들지 않는다
    {"element": "입자 운동으로 확산 설명", "method": "활동지",
     "levels": ["상 기준", "중 기준", "하 기준"],          # 단계 순서대로. 한 문장만 주면 칸을 합쳐 씀 (가치·태도 등)
     "feedback": "하 수준 학생에게 줄 다음 행동"}
  ],
  "evaluation_levels": ["상", "중", "하"]           # 평가 단계 이름 (선택, 기본 상·중·하)
}
글의 \\n은 새 문단(줄)이 된다. 평가 계획표의 빈 칸은 [확인 필요]로 둔다.

사용법:
    python make_lesson_form.py 입력.json 출력.hwpx
"""

from __future__ import annotations

import itertools
import json
import math
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SCRIPTS = Path(__file__).resolve().parent
for folder in (SCRIPTS, SCRIPTS.parents[2] / "shared" / "scripts"):      # 스킬 묶음 안, 저장소 안
    if (folder / "make_hwpx_equation.py").exists():
        sys.path.insert(0, str(folder))
        break
from make_hwpx_check import validate_package  # noqa: E402
from make_hwpx_equation import equation_xml, split_equations  # noqa: E402
from make_hwpx_save import file_error_message, hwpx_check, save_atomically, write_zip  # noqa: E402
from make_hwpx_text import _clean  # noqa: E402

FORM = SCRIPTS.parent / "assets" / "lesson_plan_form.hwpx"
SECTION, HEADER = "Contents/section0.xml", "Contents/header.xml"
TABLE_RE = re.compile(r"<hp:tbl .*?</hp:tbl>", re.S)
CELL_RE = re.compile(r"<hp:tc .*?</hp:tc>", re.S)
GOAL_NUMBER = re.compile(r"^\s*\d+[.)]\s*")
# 활동표 열 너비 (HWPUNIT, 합 48194 = 양식 표 너비): 단계, 학습내용, 교사, 학생, 자료 및 유의점, 시간
COLUMNS = (3800, 6000, 14400, 10600, 9700, 3694)
# 통합형 열 너비 (합 48194): 단계, 학습 형태, 교수·학습 활동, 시간, 자료 및 유의점, 평가
INTEGRATED_COLUMNS = (3800, 4400, 23000, 3694, 8300, 5000)
# 활동표 본문 칸: (본뜰 양식 칸의 열, 입력 키). 단계 칸(0열)은 따로 세로로 합친다.
# 양식의 안쪽 칸(1~4열)은 선이 같고 5열만 오른쪽 굵은 바깥선이라, 통합형의 시간 칸은 4열, 끝 칸(평가)은 5열을 본뜬다
BODY_CELLS = {"split": ((1, "content"), (2, "teacher"), (3, "student"), (4, "materials"), (5, "time")),
              "integrated": ((1, "group"), (2, "activity"), (4, "time"), (4, "materials"), (5, "assess"))}
LAYOUTS = tuple(BODY_CELLS)                  # 첫 값(분리형)이 기본
INTEGRATED_KEYS = ("group", "activity", "assess")   # 통합형에만 있는 입력 키: 학습 형태, 교수·학습 활동, 평가
# 통합형 머리칸: (본뜰 양식 머리칸의 열, 새 글). 새 글이 None이면 양식 머리칸 글을 그대로 쓴다
INTEGRATED_HEAD = ((0, None), (1, "학습\n형태"), (2, None), (4, "소요\n시간"), (4, None), (5, "평가"))
CENTER_KEYS = ("content", "group", "time", "assess")    # 가운데 정렬 칸
# 평가 계획표 열 너비 (합 48194): 평가 요소, 평가 방법, 평가 기준(단계 수로 나눔), 피드백
EVAL_COLUMNS = (7400, 6200, 25400, 9194)
DEFAULT_LEVELS = ("상", "중", "하")
MAX_LEVELS = 5
UNKNOWN = "[확인 필요]"
# 양식의 문단·글자 모양 번호
STAGE_PARA, STAGE_CHAR = "3", "1"           # 가운데, 11pt 굵게
CONTENT_PARA, CONTENT_CHAR = "13", "3"       # 가운데, 10pt 굵게
BODY_CHAR = "0"                              # 10pt
TIME_PARA = "13"
LEFT_PARA = "16"                             # 양쪽 정렬, 줄 간격 130%: 내어쓰기판의 바탕
INFO_PARA, INFO_CHAR = "2", "14"             # 정보표 값 (11pt)
GOAL_PARA, GOAL_CHAR = "16", "2"
PREP_PARA, PREP_CHAR = "4", "15"
LABEL_PARA, LABEL_CHAR = "3", "13"
HANG = 1000                                  # "◉ ", "- " 폭만큼 내어쓰기 (HWPUNIT)
LINE, PAD = 1300, 600                        # 10pt 한 줄 높이(130%), 칸 위아래 여백 어림


class FormError(ValueError):
    """입력이나 양식이 맞지 않음 (한국어 알림)."""


# ---------------------------------------------------------------- 글

class Writer:
    """글 조각과 문단을 쓴다. 양식 문단 모양을 본떠 어절 단위 줄바꿈판(내어쓰기판)을 머리 정보에 더한다."""

    def __init__(self, header: str) -> None:
        self.ids = itertools.count(1700000001)
        self.header = header
        self.count = int(re.search(r'<hh:paraProperties itemCnt="(\d+)"', header).group(1))
        self.made: dict[tuple[str, int], str] = {}
        self.hang_para = self.word_wrap(LEFT_PARA, HANG)

    def word_wrap(self, para: str, hang: int = 0) -> str:
        """para 문단 모양을 본떠, 왼쪽 정렬·어절 단위 줄바꿈(·내어쓰기)인 새 모양 번호를 돌려준다.

        한글은 breakNonLatinWord="BREAK_WORD"일 때 한글 낱말을 어절 단위로 넘기고, KEEP_WORD면 글자 단위로 끊는다."""
        key = (para, hang)
        if key not in self.made:
            base = re.search(rf'<hh:paraPr id="{para}".*?</hh:paraPr>', self.header, re.S).group(0)
            new_id = str(self.count)
            shape = base.replace(f'<hh:paraPr id="{para}"', f'<hh:paraPr id="{new_id}"', 1)
            shape = shape.replace('breakNonLatinWord="KEEP_WORD"', 'breakNonLatinWord="BREAK_WORD"', 1)
            shape = shape.replace('horizontal="JUSTIFY"', 'horizontal="LEFT"', 1)
            if hang:
                case, default = shape.split("<hp:default>")
                case = re.sub(r'<hc:intent value="-?\d+"', f'<hc:intent value="-{hang}"', case, count=1)
                default = re.sub(r'<hc:intent value="-?\d+"', f'<hc:intent value="-{hang * 2}"', default, count=1)
                shape = case + "<hp:default>" + default
            self.header = self.header.replace("</hh:paraProperties>", f"{shape}</hh:paraProperties>", 1)
            self.count += 1
            self.header = re.sub(r'<hh:paraProperties itemCnt="\d+"', f'<hh:paraProperties itemCnt="{self.count}"',
                                 self.header, count=1)
            self.made[key] = new_id
        return self.made[key]

    def runs(self, text: str, char: str) -> str:
        pieces = []
        for piece, is_equation in split_equations(text):
            if is_equation:
                pieces.append(f'<hp:run charPrIDRef="{char}">{equation_xml(next(self.ids), _clean(piece))}<hp:t/></hp:run>')
            elif _clean(piece):     # XML에 넣을 수 없는 제어 문자는 지운다 (한글이 파일을 열지 못함)
                pieces.append(f'<hp:run charPrIDRef="{char}"><hp:t>{escape(_clean(piece))}</hp:t></hp:run>')
        return "".join(pieces) or f'<hp:run charPrIDRef="{char}"/>'

    def paragraphs(self, text: str, para: str, char: str) -> str:
        lines = str(text or "").split("\n")
        return "".join(f'<hp:p id="0" paraPrIDRef="{para}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                        f'{self.runs(line, char)}</hp:p>' for line in lines)


def _lines(text: str, width: int) -> int:
    """칸 너비에 글이 몇 줄로 들어갈지 어림 (10pt: 한글 1000, 그 밖 520)."""
    total = 0
    for line in str(text or "").split("\n"):
        units = sum(1000 if ord(char) > 0x2E7F else 520 for char in re.sub(r"\{\{.*?\}\}", "수수", line))
        total += max(1, math.ceil(units / max(1000, width - 1020)))
    return total


# ---------------------------------------------------------------- 칸

def _cell(tc: str, col: int, row: int, width: int, height: int, body: str,
          col_span: int = 1, row_span: int = 1, header: bool = False) -> str:
    found = re.search(r"(<hp:subList [^>]*>).*(</hp:subList>)", tc, re.S)
    tc = tc[:found.start()] + found.group(1) + body + found.group(2) + tc[found.end():]
    tc = re.sub(r'<hp:cellAddr colAddr="\d+" rowAddr="\d+"/>', f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>', tc, count=1)
    tc = re.sub(r'<hp:cellSpan colSpan="\d+" rowSpan="\d+"/>', f'<hp:cellSpan colSpan="{col_span}" rowSpan="{row_span}"/>', tc, count=1)
    tc = re.sub(r'<hp:cellSz width="\d+" height="\d+"/>', f'<hp:cellSz width="{width}" height="{height}"/>', tc, count=1)
    return re.sub(r'(<hp:tc [^>]*?)header="\d"', rf'\g<1>header="{int(header)}"', tc, count=1)


def _cells(table: str) -> dict[tuple[int, int], str]:
    found = {}
    for tc in CELL_RE.findall(table):
        col, row = map(int, re.search(r'colAddr="(\d+)" rowAddr="(\d+)"', tc).groups())
        found[(col, row)] = tc
    return found


def _body_of(tc: str) -> str:
    return re.search(r"<hp:subList [^>]*>(.*)</hp:subList>", tc, re.S).group(1)


def _size(tc: str) -> tuple[int, int]:
    width, height = re.search(r'<hp:cellSz width="(\d+)" height="(\d+)"', tc).groups()
    return int(width), int(height)


def _resize(table: str, rows: list[str], heights: list[int], inline: bool = False) -> str:
    opening = re.sub(r'rowCnt="\d+"', f'rowCnt="{len(rows)}"', re.match(r"<hp:tbl [^>]*>", table).group(0))
    sizes = re.search(r"<hp:sz [^>]*/>.*?<hp:inMargin [^>]*/>", table, re.S).group(0)
    sizes = re.sub(r'(<hp:sz width="\d+" widthRelTo="\w+" height=")\d+', rf"\g<1>{sum(heights)}", sizes, count=1)
    if inline:          # 문단 바로 아래에 붙여 쪽을 넘어 나뉘게 한다 (글자처럼 놓은 표는 나뉘지 않는다)
        sizes = re.sub(r'treatAsChar="\d"', 'treatAsChar="0"', sizes, count=1)
        sizes = re.sub(r'vertOffset="\d+"', 'vertOffset="0"', sizes, count=1)
    return opening + sizes + "".join(f"<hp:tr>{row}</hp:tr>" for row in rows) + "</hp:tbl>"


# ---------------------------------------------------------------- 입력 검사

def _text(spec: dict, key: str) -> str:
    value = spec.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise FormError(f"'{key}'는 글이어야 함 (받은 값: {value!r})")
    return str(value)


def _check(spec) -> dict:
    if not isinstance(spec, dict):
        raise FormError("입력은 JSON 객체여야 함")
    stages = spec.get("stages")
    if not isinstance(stages, list) or not stages:
        raise FormError("'stages'(단계 목록: 도입·전개·정리 등)가 필요함")
    for index, stage in enumerate(stages, 1):
        if not isinstance(stage, dict) or not str(stage.get("name", "")).strip():
            raise FormError(f"단계 {index}: 'name'(단계 이름)이 필요함")
        steps = stage.get("steps")
        if not isinstance(steps, list) or not steps or not all(isinstance(step, dict) for step in steps):
            raise FormError(f"단계 {index}({stage['name']}): 'steps'(활동 목록)가 필요함")
    goals = spec.get("goals") or []
    if isinstance(goals, str):
        goals = [goals]
    if not isinstance(goals, list) or not all(isinstance(goal, str) for goal in goals):
        raise FormError("'goals'(학습 목표)는 글 목록이어야 함")
    rows = spec.get("rows") or []
    if not isinstance(rows, list) or not all(isinstance(r, dict) and str(r.get("label", "")).strip() for r in rows):
        raise FormError('\'rows\'는 {"label": 이름, "text": 내용} 목록이어야 함')
    prep = spec.get("prep") or {}
    if not isinstance(prep, dict):
        raise FormError('\'prep\'은 {"teacher": …, "student": …} 객체여야 함')
    layout = spec.get("layout") or LAYOUTS[0]
    if layout not in LAYOUTS:
        raise FormError(f"'layout'(활동표 형식)은 \"split\"(분리형, 기본) 또는 \"integrated\"(통합형)여야 함 (받은 값: {layout!r})")
    levels, evaluation = _check_evaluation(spec)
    return {**spec, "goals": goals, "rows": rows, "prep": prep, "layout": layout,
            "evaluation": evaluation, "evaluation_levels": levels}


def _check_evaluation(spec: dict) -> tuple[list[str], list[dict]]:
    """평가 계획: 단계 이름 목록과 평가 요소 목록. levels는 단계 수만큼 또는 한 문장(칸을 합침)."""
    names = spec.get("evaluation_levels", list(DEFAULT_LEVELS))
    if (not isinstance(names, list) or not 1 <= len(names) <= MAX_LEVELS
            or not all(isinstance(name, str) and name.strip() for name in names)):
        raise FormError(f"'evaluation_levels'(평가 단계 이름)는 글 1~{MAX_LEVELS}개 목록이어야 함 (예: [\"상\", \"중\", \"하\"])")
    evaluation = spec.get("evaluation") or []
    if not isinstance(evaluation, list) or not all(isinstance(item, dict) for item in evaluation):
        raise FormError('\'evaluation\'(평가 계획)은 {"element": …, "method": …, "levels": […], "feedback": …} 목록이어야 함')
    clean = []
    for index, item in enumerate(evaluation, 1):
        levels = item.get("levels") or []
        levels = [levels] if isinstance(levels, str) else levels
        if not isinstance(levels, list) or len(levels) not in (0, 1, len(names)):
            raise FormError(f"평가 요소 {index}: 'levels'는 단계 수({len(names)}개, {'·'.join(names)} 순서)만큼 "
                            "또는 한 문장(칸을 합쳐 씀)이어야 함")
        if not all(isinstance(level, (str, int, float)) and not isinstance(level, bool) for level in levels):
            raise FormError(f"평가 요소 {index}: 'levels'는 글 목록이어야 함")
        texts = {key: _text(item, key) for key in ("element", "method", "feedback")}
        clean.append({**texts, "levels": [str(level) for level in levels] or [""]})
    return [name.strip() for name in names], clean


# ---------------------------------------------------------------- 표

def _title_table(writer: Writer, table: str, spec: dict) -> str:
    cells = _cells(table)
    mark_body, title_body = _body_of(cells[(0, 0)]), _body_of(cells[(2, 0)])
    ids = [re.search(pattern, body).group(1) for body in (mark_body, title_body)
           for pattern in (r'paraPrIDRef="(\d+)"', r'charPrIDRef="(\d+)"')]
    row = (_cell(cells[(0, 0)], 0, 0, *_size(cells[(0, 0)]), writer.paragraphs(_text(spec, "mark") or "Ⅰ", ids[0], ids[1]))
           + cells[(1, 0)]
           + _cell(cells[(2, 0)], 2, 0, *_size(cells[(2, 0)]), writer.paragraphs(_text(spec, "title"), ids[2], ids[3])))
    return _resize(table, [row], [_size(cells[(0, 0)])[1]])


def _label(text: str) -> str:
    """정보표 머리칸: 한글 네 글자는 양식처럼 "성 취\\n기 준"으로, 나머지는 그대로."""
    plain = text.replace(" ", "")
    if len(plain) == 4 and all(ord(char) > 0x2E7F for char in plain):
        return f"{plain[0]} {plain[1]}\n{plain[2]} {plain[3]}"
    return text


def _info_table(writer: Writer, table: str, spec: dict) -> str:
    cells = _cells(table)
    label_w, value_w = _size(cells[(0, 2)])[0], _size(cells[(1, 2)])[0]
    goals = [f"{n}. {GOAL_NUMBER.sub('', goal)}" for n, goal in enumerate(spec["goals"], 1)] or [""]
    rows, heights = [], []

    def text_row(label_tc: str, label_body: str, text: str, para: str, char: str) -> None:
        row, h = len(rows), max(1565, _lines(text, value_w) * 1600 + PAD)
        rows.append(_cell(label_tc, 0, row, label_w, h, label_body)
                    + _cell(cells[(1, 2)], 1, row, value_w, h, writer.paragraphs(text, para, char), col_span=6))
        heights.append(h)

    for row, (left, right) in enumerate(((_text(spec, "topic"), _text(spec, "period")),
                                         (_text(spec, "subtopic"), _text(spec, "time")))):
        source = [cells[(col, row)] for col in (0, 1, 5, 6)]
        h = _size(source[0])[1]
        rows.append(source[0] + _cell(source[1], 1, row, _size(source[1])[0], h, writer.paragraphs(left, writer.word_wrap(INFO_PARA), INFO_CHAR), col_span=4)
                    + source[2] + _cell(source[3], 6, row, _size(source[3])[0], h, writer.paragraphs(right, LABEL_PARA, INFO_CHAR)))
        heights.append(h)
    text_row(cells[(0, 2)], _body_of(cells[(0, 2)]), "\n".join(goals), writer.word_wrap(GOAL_PARA), GOAL_CHAR)
    for extra in spec["rows"]:
        text_row(cells[(0, 2)], writer.paragraphs(_label(str(extra["label"])), LABEL_PARA, LABEL_CHAR),
                 str(extra.get("text", "") or ""), writer.word_wrap(GOAL_PARA), GOAL_CHAR)
    text_row(cells[(0, 3)], _body_of(cells[(0, 3)]), _text(spec, "style"), writer.word_wrap(INFO_PARA), INFO_CHAR)
    prep_row = len(rows)
    for offset, (key, source_row) in enumerate((("teacher", 4), ("student", 5))):
        text = str(spec["prep"].get(key, "") or "")
        h = max(1571, _lines(text, _size(cells[(2, source_row)])[0]) * 1600 + PAD)
        row_xml = ""
        if offset == 0:
            row_xml += _cell(cells[(0, 4)], 0, prep_row, label_w, 0, _body_of(cells[(0, 4)]), row_span=2)
        row_xml += _cell(cells[(1, source_row)], 1, prep_row + offset, *_size(cells[(1, source_row)]), _body_of(cells[(1, source_row)]))
        row_xml += _cell(cells[(2, source_row)], 2, prep_row + offset, _size(cells[(2, source_row)])[0], h,
                         writer.paragraphs(text, writer.word_wrap(PREP_PARA), PREP_CHAR), col_span=5)
        rows.append(row_xml)
        heights.append(h)
    both = heights[prep_row] + heights[prep_row + 1]
    rows[prep_row] = re.sub(r'(<hp:cellSz width="\d+" height=")0"', rf'\g<1>{both}"', rows[prep_row], count=1)
    return _resize(table, rows, heights)


def _activity_head(cells: dict, layout: str) -> tuple[list[str], list[int]]:
    """머리행. 분리형은 2행(교수·학습 활동 아래 교사·학생), 통합형은 같은 높이의 1행. 양식 머리칸을 본뜬다."""
    if layout == "integrated":
        row = "".join(_cell(cells[(source, 0)], col, 0, width, 564,
                            _body_of(cells[(source, 0)]) if text is None else _label_paragraphs(text), header=True)
                      for col, ((source, text), width) in enumerate(zip(INTEGRATED_HEAD, INTEGRATED_COLUMNS)))
        return [row], [564]
    w = COLUMNS
    head0 = (_cell(cells[(0, 0)], 0, 0, w[0], 564, _body_of(cells[(0, 0)]), row_span=2, header=True)
             + _cell(cells[(1, 0)], 1, 0, w[1], 564, _body_of(cells[(1, 0)]), row_span=2, header=True)
             + _cell(cells[(2, 0)], 2, 0, w[2] + w[3], 282, _body_of(cells[(2, 0)]), col_span=2, header=True)
             + _cell(cells[(4, 0)], 4, 0, w[4], 564, _body_of(cells[(4, 0)]), row_span=2, header=True)
             + _cell(cells[(5, 0)], 5, 0, w[5], 564, _body_of(cells[(5, 0)]), row_span=2, header=True))
    head1 = (_cell(cells[(2, 1)], 2, 1, w[2], 282, _body_of(cells[(2, 1)]), header=True)
             + _cell(cells[(3, 1)], 3, 1, w[3], 282, _body_of(cells[(3, 1)]), header=True))
    return [head0, head1], [282, 282]


def _step_texts(step: dict) -> dict[str, str]:
    """활동 한 행의 글. 통합형 칸(activity)을 주지 않으면 교사 글 다음 줄에 학생 글을 잇는다."""
    keys = ("content", "teacher", "student", "materials", "time", *INTEGRATED_KEYS)
    texts = {key: str(step.get(key, "") or "") for key in keys}
    if not texts["activity"].strip():
        texts["activity"] = "\n".join(text for text in (texts["teacher"], texts["student"]) if text.strip())
    return {**texts, "activity": _with_content_line(texts["content"], texts["activity"])}


def _with_content_line(content: str, activity: str) -> str:
    """통합형에는 학습내용 칸이 없으므로 학습내용을 활동 첫 줄에 "◉ 학습내용"으로 넣는다."""
    line = " ".join(content.split())
    if not line:
        return activity
    line = line if line.startswith("◉") else f"◉ {line}"
    return f"{line}\n{activity}" if activity.strip() else line


def _body_style(writer: Writer, key: str) -> tuple[str, str]:
    if key == "content":
        return CONTENT_PARA, CONTENT_CHAR
    if key in CENTER_KEYS:
        return TIME_PARA, BODY_CHAR
    return writer.hang_para, BODY_CHAR


def _activity_table(writer: Writer, table: str, spec: dict) -> str:
    cells, layout = _cells(table), spec["layout"]
    w = INTEGRATED_COLUMNS if layout == "integrated" else COLUMNS
    body = list(zip(BODY_CELLS[layout], w[1:]))          # ((양식 칸 열, 입력 키), 너비)
    rows, heights = _activity_head(cells, layout)
    stages = spec["stages"]
    for s_index, stage in enumerate(stages):
        # 테두리는 양식의 첫 단계(도입)·가운데 단계(전개)·끝 단계(정리) 행을 본뜬다
        source = 2 if s_index == 0 else 4 if s_index == len(stages) - 1 else 3
        steps = [_step_texts(step) for step in stage["steps"]]
        step_heights = [max(1500, max(_lines(texts[key], width) for (_, key), width in body if key != "time") * LINE + PAD)
                        for texts in steps]
        for t_index, texts in enumerate(steps):
            row_no, h = len(rows), step_heights[t_index]
            row = ""
            if t_index == 0:
                row += _cell(cells[(0, source)], 0, row_no, w[0], sum(step_heights),
                             writer.paragraphs(str(stage["name"]), STAGE_PARA, STAGE_CHAR), row_span=len(steps))
            for col, ((form_col, key), width) in enumerate(body, 1):
                row += _cell(cells[(form_col, source)], col, row_no, width, h,
                             writer.paragraphs(texts[key], *_body_style(writer, key)))
            rows.append(row)
            heights.append(h)
    resized = _resize(table, rows, heights, inline=True)
    return re.sub(r'colCnt="\d+"', f'colCnt="{len(w)}"', resized, count=1)


# ---------------------------------------------------------------- 평가 계획표

def _level_widths(count: int) -> list[int]:
    base = EVAL_COLUMNS[2] // count
    return [base] * (count - 1) + [EVAL_COLUMNS[2] - base * (count - 1)]


def _label_paragraphs(text: str) -> str:
    return "".join(f'<hp:p id="0" paraPrIDRef="{LABEL_PARA}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                   f'<hp:run charPrIDRef="{LABEL_CHAR}"><hp:t>{escape(_clean(line))}</hp:t></hp:run></hp:p>'
                   for line in text.split("\n"))


def _eval_head(cells: dict, names: list[str]) -> list[str]:
    """머리 2행: 평가 요소 | 평가 방법 | 평가 기준(단계들) | 피드백(마지막 단계). 활동표 머리칸을 본뜬다."""
    w, last = EVAL_COLUMNS, 2 + len(names)

    def head(source: tuple[int, int], col: int, row: int, width: int, height: int, text: str,
             col_span: int = 1, row_span: int = 1) -> str:
        return _cell(cells[source], col, row, width, height, _label_paragraphs(text),
                     col_span=col_span, row_span=row_span, header=True)

    row0 = (head((0, 0), 0, 0, w[0], 564, "평가 요소", row_span=2) + head((1, 0), 1, 0, w[1], 564, "평가 방법", row_span=2)
            + head((2, 0), 2, 0, w[2], 282, "평가 기준", col_span=len(names))
            + head((5, 0), last, 0, w[3], 564, f"피드백({names[-1]})", row_span=2))
    row1 = "".join(head((2, 1), 2 + i, 1, width, 282, name)
                   for i, (name, width) in enumerate(zip(names, _level_widths(len(names)))))
    return [row0, row1]


def _eval_row(writer: Writer, cells: dict, source: int, row_no: int, names: list[str], item: dict) -> tuple[str, int]:
    merged = len(item["levels"]) == 1 < len(names)          # 한 문장이면 단계 칸을 합친다 (가치·태도 등)
    level_widths = [EVAL_COLUMNS[2]] if merged else _level_widths(len(names))
    texts = [text if _clean(text).strip() else UNKNOWN for text in (item["element"], item["method"], *item["levels"], item["feedback"])]
    widths = [EVAL_COLUMNS[0], EVAL_COLUMNS[1], *level_widths, EVAL_COLUMNS[3]]
    h = max(1500, max(_lines(text, width) for text, width in zip(texts, widths)) * LINE + PAD)
    row = (_cell(cells[(0, source)], 0, row_no, widths[0], h, writer.paragraphs(texts[0], CONTENT_PARA, CONTENT_CHAR))
           + _cell(cells[(1, source)], 1, row_no, widths[1], h, writer.paragraphs(texts[1], CONTENT_PARA, BODY_CHAR)))
    for index, (text, width) in enumerate(zip(texts[2:-1], level_widths)):
        row += _cell(cells[(2, source)], 2 + index, row_no, width, h, writer.paragraphs(text, CONTENT_PARA, BODY_CHAR),
                     col_span=len(names) if merged else 1)
    row += _cell(cells[(5, source)], 2 + len(names), row_no, widths[-1], h,
                 writer.paragraphs(texts[-1], CONTENT_PARA, BODY_CHAR))
    return row, h


def _evaluation_table(writer: Writer, table: str, spec: dict) -> str:
    """활동표 아래 평가 계획표. 선·음영·글꼴은 활동표 칸(첫 열은 음영 칸, 끝 열은 굵은 바깥선)을 본뜬다."""
    cells, names, items = _cells(table), spec["evaluation_levels"], spec["evaluation"]
    rows, heights = _eval_head(cells, names), [282, 282]
    for index, item in enumerate(items):
        source = 4 if index == len(items) - 1 else 2 if index == 0 else 3    # 끝 행은 아래 굵은 바깥선
        row, height = _eval_row(writer, cells, source, len(rows), names, item)
        rows.append(row)
        heights.append(height)
    resized = _resize(table, rows, heights, inline=True)
    resized = re.sub(r'colCnt="\d+"', f'colCnt="{3 + len(names)}"', resized, count=1)
    return re.sub(r'<hp:tbl id="(\d+)" zOrder="\d+"', lambda found: f'<hp:tbl id="{int(found.group(1)) + 1}" zOrder="3"',
                  resized, count=1)


# ---------------------------------------------------------------- 문서

def build(spec: dict, out_path: Path, form: Path = FORM) -> None:
    spec = _check(spec)
    out_path = Path(out_path)
    if out_path.exists():
        raise FormError(f"이미 있는 파일이라 덮어쓰지 않음: {out_path.name}. 다른 이름을 적어 주세요")
    if not out_path.parent.is_dir():
        raise FormError(f"결과를 저장할 폴더가 없음: {out_path.parent}")
    with zipfile.ZipFile(form) as source:
        infos = source.infolist()
        entries = {info.filename: source.read(info.filename) for info in infos}
    section = entries[SECTION].decode("utf-8")
    writer = Writer(entries[HEADER].decode("utf-8"))
    tables = TABLE_RE.findall(section)
    if len(tables) != 3:
        raise FormError("기본 양식의 표 구성이 바뀜 (표 3개여야 함)")
    activity, title, info = tables
    first = section.index("<hp:p ")
    end = section.index("</hp:p>", section.index(info) + len(info)) + len("</hp:p>")      # 표 세 개를 담은 첫 문단의 끝
    head = section[first:end].replace(activity, "", 1)
    head = head.replace(title, _title_table(writer, title, spec), 1).replace(info, _info_table(writer, info, spec), 1)
    head = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", head, flags=re.S)
    holder = '<hp:p id="0" paraPrIDRef="2" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="6">'
    body = f"{holder}{_activity_table(writer, activity, spec)}<hp:t/></hp:run></hp:p>"
    if spec["evaluation"]:          # 빈 줄 하나를 두고 평가 계획표
        body += f"{holder}<hp:t/></hp:run></hp:p>{holder}{_evaluation_table(writer, activity, spec)}<hp:t/></hp:run></hp:p>"
    entries[SECTION] = (section[:first] + head + body + section[end:]).encode("utf-8")
    entries[HEADER] = writer.header.encode("utf-8")
    if "Preview/PrvText.txt" in entries:
        entries["Preview/PrvText.txt"] = _clean(_text(spec, "title")).encode("utf-8")
    # 같은 폴더의 임시 파일에 쓰고 hwpx 검사를 통과해야 결과 파일로 옮긴다 (깨진 파일이 남지 않게)
    save_atomically(out_path, lambda path: write_zip(path, infos, entries),
                    hwpx_check(FormError, "만든 hwpx 검사 실패:", (), validate_package))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(args) != 2:
        print("사용법: python make_lesson_form.py 입력.json 출력.hwpx")
        return 2
    try:
        build(json.loads(Path(args[0]).read_text(encoding="utf-8-sig")), Path(args[1]))
    except (FormError, ValueError) as error:      # JSON·글자 인코딩 오류도 ValueError
        print(f"만들지 못함: {error}")
        return 1
    except OSError as error:
        print(f"만들지 못함: {file_error_message(error)}")
        return 1
    print(f"완료: {args[1]}. 한글에서 열어 쪽이 넘어가는 자리를 확인해 주세요")
    return 0


if __name__ == "__main__":
    sys.exit(main())
