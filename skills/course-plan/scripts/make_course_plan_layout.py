"""교과진도평가계획의 모양: 학교 공문서식 보통 양식(흑백, 표 중심). make_hwpx 블록을 만든다.

초등 보통 양식의 공통 부분(머리, 마디 제목, 문장 목록, 진도표)과, 중·고 기본 양식 채우기가 함께 쓰는 값
(학교 규정 표시, Ⅳ 아래 안내 문장, Ⅴ 성취도 표 ACHIEVEMENT).
표 안 글자는 가운데 정렬이 기본이고, 긴 설명 칸(수업 방법, 채점 기준, 유의사항)만 왼쪽 정렬이다.
머리칸 음영은 make_hwpx 기본 회색(#D9D9D9)이라 흑백 인쇄에서도 읽힌다.
"""

from __future__ import annotations

import math

from make_hwpx_layout import PAGE_WIDTH, SIDE_MARGINS
from make_hwpx_lint import _word_width, wide_words
from make_course_plan_check import CODE
from school_calendar import period_text

from course_form_marks import check, edu, pen, rule, unmarked  # noqa: E402

TODO = "[작성 필요]"
TEXT_WIDTH = PAGE_WIDTH - 2 * SIDE_MARGINS["narrow"]          # 좁은 여백(좌우 15mm) 본문 너비
CELL_PAD = 1020                                               # 칸 안쪽 좌우 여백 합
CHANGE_NOTE = "※ 학교의 학사일정이나 교사의 교수·학습 재구성에 따라 변경될 수 있음"
PROGRESS_HEAD = ["주", "기간\n(공제\n일수)", "단원명", "교육과정 성취기준", "수업 방법 및\n수업·평가 연계의 주안점",
                 "예정\n시간", "실시\n누계", "비고"]
NEWLINE = chr(10)
EVENT_INNER = (4000, 8200)     # 비고 칸 안쪽 너비 범위 (8200: 한글에서 "전국연합학력평가"가 한 줄로 들어간 너비)
MIN_TEACHING = 12000           # 단원명 + 수업 방법 칸의 최소 너비
UNIT_SHARE = 0.38              # 남는 너비 가운데 단원명 칸 몫 (나머지는 수업 방법 칸)
# 기준 성취율과 성취도 (grading-rules.md 1-9): (머리, 행들, 덧붙임)
ACHIEVEMENT = {
    "공통": (["성취율", "성취도"], [["90% 이상", "A"], ["80% 이상~90% 미만", "B"], ["70% 이상~80% 미만", "C"],
                                ["60% 이상~70% 미만", "D"], ["40% 이상~60% 미만", "E"]],
           "※ 성취율 40% 미도달자 중 최소 성취수준 보장지도 이수 시 성취도 'E' 부여함."),
    "선택": (["성취율", "성취도"], [["90% 이상", "A"], ["80% 이상~90% 미만", "B"], ["70% 이상~80% 미만", "C"],
                                ["60% 이상~70% 미만", "D"], ["60% 미만", "E"]], ""),
    "체육·예술": (["성취율", "성취도"], [["80% 이상", "A"], ["60% 이상~80% 미만", "B"], ["60% 미만", "C"]],
              "※ 체육·예술 과목은 성취도만 3단계(A·B·C)로 산출함."),
    "교양": (["이수 기준", "성취도"], [["과목 이수 기준(출석 등)을 충족함", "P"]], "※ 교양 과목은 이수 여부만 'P'로 기록함."),
    "자유학기": (["평가 방식", "성취도"], [["정기시험 없이 과정 중심 평가, 성취 특성을 문장으로 기록", "P"]],
             "※ 자유학기는 원점수·수강자 수를 쓰지 않고 성취도 'P'로 기록함."),
}
ACHIEVEMENT["중학교"] = (ACHIEVEMENT["선택"][0], ACHIEVEMENT["선택"][1], "")
SPLIT_BEFORE = ("(", "~")          # 칸보다 넓은 낱말은 이 글자 앞에서 줄을 바꿔 낱말 중간이 끊기지 않게 한다
WRAP_SAFETY = 0.9
LINE_HEIGHT, ROW_PAD, ROW_MIN = 1300, 282, 1800     # make_hwpx 칸 높이 어림과 같은 값 (10pt, 줄 간격 130%)
CHUNK_LIMIT = 52000     # 통째로 옮길 표 한 덩이 높이 한도 (약 183mm). make_hwpx 통째 옮기기 한도 65000보다 넉넉히 낮게


# ---------------------------------------------------------------- 공통 조각

def marked(line: dict) -> str:
    """학교 규정에 따라 바꿀 문장은 형광펜과 메모로 표시한다 (만든 뒤 course_form_marks.apply_marks가 바꿈)."""
    return rule(line["text"]) if line["rule"] else line["text"]


def cell(text: str, **options) -> dict:
    return {"text": text, "align": "center", **options}


def head(text: str, **options) -> dict:
    return cell(text, header=True, **options)


def col_inner(widths: list[float], index: int, span: int = 1) -> int:
    return round(TEXT_WIDTH * sum(widths[index:index + span]) / sum(widths)) - CELL_PAD


def _split_word(word: str, limit: int) -> str:
    for mark in SPLIT_BEFORE:
        at = word.find(mark, 1)
        if at > 0:
            tail = word[at:]
            if mark == "~" and wide_words(tail, limit):        # '~[코드]'도 넓으면 '~'를 따로 한 줄에
                tail = f"~\n{tail[1:]}"
            return f"{word[:at]}\n{tail}"
    return word


def wrap_wide(text: str, inner: int) -> str:
    """칸보다 넓은 낱말을 '(' 또는 '~' 앞에서 줄바꿈한다 ('[A]~[B]' → '[A]\\n~[B]').

    낱말 폭 어림(make_hwpx_lint)은 한글 화면보다 조금 좁게 나오므로 WRAP_SAFETY만큼 여유를 둔다
    (한글 2024에서 '~[10통사1-02-02]'의 ']'만 다음 줄로 넘어간 것을 보고 정함)."""
    limit = int(inner * WRAP_SAFETY)
    for word in wide_words(text, limit):
        text = text.replace(word, _split_word(word, limit), 1)
    return text


def text_height(text: str, inner: int) -> int:
    """칸 글 높이 어림 (HWPUNIT)."""
    lines = sum(max(1, math.ceil(_word_width(line) / max(inner, 1))) for line in text.split("\n"))
    return max(ROW_MIN, lines * LINE_HEIGHT + ROW_PAD)


def kept_tables(header: list, groups: list[tuple[list[list[dict]], int]], widths: list[float]) -> list[dict]:
    """함께 있어야 할 행 묶음(rowspan으로 합친 행들)과 높이 어림 → 통째로 옮기는 표들.

    여러 행을 합친 칸이 있는 표를 한글이 행 단위로 나누면 머리행만 쪽 끝에 남는다(한글 2024에서 확인).
    그래서 묶음 경계에서 CHUNK_LIMIT 높이로 표를 나누고, 표마다 머리행을 달아 통째로 옮긴다."""
    chunks: list[list[list[dict]]] = [[]]
    height = 0
    for rows, size in groups:
        if chunks[-1] and height + size > CHUNK_LIMIT:
            chunks.append([])
            height = 0
        chunks[-1] += rows
        height += size
    return [{"type": "table", "header": header, "rows": rows, "widths": widths, "keep_together": True}
            for rows in chunks if rows]


def section(mark: str, title: str) -> dict:
    return {"type": "heading", "text": f"{mark}. {title}", "level": 1}


def note(text: str) -> dict:
    return {"type": "paragraph", "text": text, "align": "left", "size": "small"}


def sub_items(lines: list[dict], name: str, warnings: list[str]) -> list[dict]:
    """가. 나. 항목들. 비어 있으면 [작성 필요]와 경고."""
    if not lines:
        warnings.append(f"{name}이 비어 있어 {TODO}로 둠")
        return [{"text": TODO, "level": 2}]
    return [{"text": marked(line), "level": 2} for line in lines]


def lines_section(mark: str, title: str, lines: list[dict], name: str, warnings: list[str]) -> list[dict]:
    return [section(mark, title), {"type": "outline", "items": sub_items(lines, name, warnings)}]


def direction_section(mark: str, evaluation: dict, warnings: list[str]) -> list[dict]:
    items = [{"text": "평가의 기본 방향", "level": 1},
             *sub_items(evaluation["direction"], "평가의 기본 방향(evaluation.direction)", warnings),
             {"text": "평가의 방침", "level": 1},
             *sub_items(evaluation["policy"], "평가의 방침(evaluation.policy)", warnings)]
    return [section(mark, "평가의 방향과 방침"), {"type": "outline", "items": items}]


def head_blocks(info: dict) -> list[dict]:
    """◆ 대상 학년, 학점(주당 시수), 지도 교사 줄."""
    grade = f"{info['grade']}학년" + (f" ({info['classes']})" if info["classes"] else "")
    hours = (f"◆ 학점 : {info['credits']}학점" if info["level"] == "고"
             else f"◆ 주당 시수 : {info['weekly_hours']}시간")
    teachers = ", ".join(f"{name} (인)" for name in info["teachers"]) or TODO
    return [{"type": "paragraph", "text": text, "align": "left"}
            for text in (f"◆ 대상 학년 : {grade}", hours, f"◆ 지도 교사 : {teachers}")]


def title_of(info: dict) -> str:
    grade = f" {info['grade']}학년" if info["level"] == "초" else ""
    return f"{info['year']}학년도 {info['semester']}학기{grade} <{info['subject']}>\n교수학습 및 평가 운영계획"


# ---------------------------------------------------------------- Ⅰ 진도표

def _period(week: dict, estimated: bool, first: bool = False) -> str:
    """기간 칸: '3.30.~' / '4.10.' 두 줄(칸을 좁게)과 공제일수. 학사일정이 어림이면 줄마다 형광펜,
    첫 줄의 첫 칸(first)에는 확인 메모."""
    lines = period_text(week["start"], week["end"]).replace("~", "~" + NEWLINE).split(NEWLINE)
    lines += [f"({week['deducted']})"] if week["deducted"] else []
    if estimated:
        lines = [check(line) if first and index == 0 else pen(line) for index, line in enumerate(lines)]
    return NEWLINE.join(lines)


def _widest(words: list[str], floor: float) -> float:
    return max([_word_width(unmarked(word)) for word in words if unmarked(word)] + [floor])


def _event_words(weeks: list[dict]) -> list[str]:
    return [part for week in weeks for note in week["notes"] for part in note.replace("(", " (").split()]


def progress_widths(plan: dict) -> list[int]:
    """진도표 열 너비 (HWPUNIT). 주·기간·예정 시간·누계·성취기준·비고 칸은 실제 글 폭에 맞춰 좁게 잡고,
    남는 너비를 단원명과 수업 방법 칸에 나눈다 (한글 2024 화면에 맞춘 여유 배율)."""
    weeks, estimated = plan["weeks"], bool(plan["calendar"].get("estimated"))
    codes = [f"[{code}]" for row in plan["progress"] for code in CODE.findall(" ".join(row["standards"]))]
    hours = _widest(["예정"], 2000) * 1.15
    fixed = [_widest([week["week"] for week in weeks], 1000) * 1.3,
             _widest([w for week in weeks for w in _period(week, estimated).split()], 2000) * 1.15,
             hours, hours, _widest(codes, 4000) * 1.08,
             min(max(_widest(_event_words(weeks), 3000) * 1.12, EVENT_INNER[0]), EVENT_INNER[1])]
    week, period, hour, total, code, event = (round(value) + CELL_PAD for value in fixed)
    rest = max(TEXT_WIDTH - sum((week, period, hour, total, code, event)), MIN_TEACHING)
    unit = round(rest * UNIT_SHARE)
    return [week, period, unit, code, rest - unit, hour, total, event]


def _week_cells(week: dict, span: int, widths: list[int], estimated: bool,
                education: list[str] = (), first: bool = False) -> tuple[list[dict], list[dict]]:
    """비고 칸: 학사일정 행사 뒤에 학교가 배정해 안내한 교육 줄('[교육명(시간)]')."""
    extra = [line if unmarked(line).startswith("[") else f"[{line}]" for line in education]
    events = wrap_wide("\n".join([*week["notes"], *extra]), col_inner(widths, 7))
    shown = pen if estimated else str
    lead = [cell(week["week"], rowspan=span), cell(_period(week, estimated, first), rowspan=span)]
    last = [cell(shown(str(week["hours"])), rowspan=span), cell(shown(str(week["cumulative"])), rowspan=span),
            cell(events, rowspan=span)]
    return lead, last


def _entry_cells(entry: dict | None, widths: list[int]) -> list[dict]:
    if entry is None:
        return [cell(""), cell(""), cell("", align="left")]
    standards = wrap_wide("\n".join(entry["standards"]), col_inner(widths, 3))
    teaching = "\n".join(part for part in (entry["methods"], entry["focus"]) if part)
    return [cell(entry["unit"]), cell(standards), cell(teaching, align="left")]


def progress_table(plan: dict) -> dict:
    """달력 줄마다 한 묶음. 같은 주에 진도가 여럿이면(담당 교사별 등) 주·기간·시간·비고 칸을 합친다."""
    widths, estimated, rows = progress_widths(plan), bool(plan["calendar"].get("estimated")), []
    for number, week in enumerate(plan["weeks"]):
        entries = [row for row in plan["progress"] if row["weeks"] == week["week"]] or [None]
        education = [line for entry in entries if entry for line in entry.get("education", [])]
        if number == 0 and not any(row.get("education") for row in plan["progress"]):
            education = [edu()]          # 받지 못했으면 지어내지 않고 형광펜 자리와 메모
        first, last = _week_cells(week, len(entries), widths, estimated, education, number == 0)
        rows.append(first + _entry_cells(entries[0], widths) + last)
        rows += [_entry_cells(entry, widths) for entry in entries[1:]]
    return {"type": "table", "header": [head(text) for text in PROGRESS_HEAD], "rows": rows, "widths": widths}


def progress_blocks(plan: dict) -> list[dict]:
    return [section("Ⅰ", "교수학습 운영계획"), progress_table(plan), note(CHANGE_NOTE)]
