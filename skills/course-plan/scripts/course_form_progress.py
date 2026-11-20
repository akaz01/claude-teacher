"""학교 양식 Ⅰ 진도표 채우기. 기본 양식 두 가지를 열 수로 가른다.

- 7열(1학기 양식): 주 | 기간(공제일수) | 단원명 | 교육과정 성취기준 | 수업 방법 및 수업·평가 연계의 주안점 |
  예정시간/실시누계(대각선 칸) | 행사
- 5열(2학기 양식): 시기 | 시수/누계 | 단원명 | 교육과정 성취기준 | 비고

학사일정 한 줄(1주 또는 2주)이 표 한 행이다. 같은 줄에 진도가 여럿이면 한 칸에 이어 쓴다.
공휴일·휴업일 행사는 양식에서 빨간 글자로 쓴 모양을, 그 밖의 행사는 검은 글자 모양을 따른다.
"""

from __future__ import annotations

import re

from school_calendar import period_text

from course_form_marks import check, edu, pen
from course_form_xml import (ADDR_RE, build_table, cell_height, cell_map, cell_paragraphs, cell_width, char_with,
                             fill_cell, first_char, para, plain, split_ranges, text_height)

BLACK_WORDS = ("고사", "시험", "평가")          # 공제일이어도 검은 글자로 쓰는 행사 (학교 양식에서 정기시험은 검은 글자)
MIN_ROW = 2800
SIZE = 900                                        # 진도표 글자 크기 어림 (9pt)
PERIOD_ONE_LINE = 11                              # 이보다 긴 기간 글은 두 줄로 (한글에서 '10.5.~10.16.'이 넘침)
NOTE_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.")


def has_teaching_column(base: str) -> bool:
    """수업 방법·주안점 칸이 있는 양식(1학기 7열)인지."""
    return "수업 방법" in plain(base[:base.find("</hp:tr>")])


def _entries(plan: dict, week: dict) -> list[dict]:
    return [row for row in plan["progress"] if row["weeks"] == week["week"]]


def _holiday_labels(calendar: dict) -> set[str]:
    labels = set()
    for item in calendar.get("no_class") or []:
        label = str(item.get("label") or "")
        if label and not any(word in label for word in BLACK_WORDS):
            labels.add(label)
    return labels


def _found_char(cells: list[str], word: str) -> str | None:
    return next((char for tc in cells if (char := char_with(tc, word))), None)


def _context(base: str, plan: dict) -> dict:
    """글자 모양: 공휴일(빨강)·보통 행사, 공제일수 '(n)'(빨강). 양식에서 그런 글을 쓴 칸을 찾아 따른다."""
    cells = cell_map(base)
    last = max(col for col, _ in cells)
    period = 1 if last == 6 else 0
    events = [tc for (col, row), tc in cells.items() if row > 0 and col == last]
    periods = [tc for (col, row), tc in cells.items() if row > 0 and col == period]
    fallback = first_char(cell_paragraphs(events[0])[0])
    return {"estimated": bool(plan["calendar"].get("estimated")), "holidays": _holiday_labels(plan["calendar"]),
            "no_education": not any(row.get("education") for row in plan["progress"]),
            "red": _found_char(events, "공휴일") or fallback, "normal": _found_char(events, "개학식") or fallback,
            "red_number": _found_char(periods, "(") or first_char(cell_paragraphs(periods[0])[0])}


def _note_key(note: str) -> tuple[int, int]:
    """행사 글 앞의 'M.D.'로 학년도 안 날짜 순서 (1·2월은 12월 뒤)."""
    found = NOTE_DATE.match(note)
    if not found:
        return (99, 99)
    month, day = int(found.group(1)), int(found.group(2))
    return (month + 12 if month < 3 else month, day)


def education_lines(entries: list[dict]) -> list[str]:
    """학교가 배정해 안내한 교육: '[교육명(시간)]' (대괄호가 없으면 붙인다, 학교 양식의 쓰는 법)."""
    lines = [line for entry in entries for line in entry.get("education", [])]
    return [line if line.startswith("[") else f"[{line}]" for line in lines]


def _note_paras(template_tc: str, notes: list[str], ctx: dict, extra: list[str] = ()) -> list[str]:
    """비고(행사) 칸: 학사일정 행사(날짜 순서, 공휴일은 빨간 글자) 뒤에 학교 안내 교육 줄."""
    template = cell_paragraphs(template_tc)[0]
    paragraphs = [para(template, note, ctx["red"] if any(note.endswith(f" {label}") for label in ctx["holidays"])
                       else ctx["normal"]) for note in sorted(notes, key=_note_key)]
    paragraphs += [para(template, line, ctx["normal"]) for line in extra]
    return paragraphs or [para(template, "", ctx["normal"])]


def _extra_notes(entries: list[dict], ctx: dict, row_no: int) -> list[str]:
    """그 주 학교 안내 교육. 진도표 어디에도 없으면 첫 줄에 형광펜 자리와 메모(지어내지 않는다)."""
    if ctx["no_education"] and row_no == 1:
        return [edu()]
    return education_lines(entries)


def _lines(entries: list[dict], key: str) -> list[str]:
    lines = []
    for entry in entries:
        value = entry[key]
        lines += value if isinstance(value, list) else [part for part in value.split("\n") if part]
    return lines


def _teaching_lines(entries: list[dict]) -> list[str]:
    """수업 방법은 [대괄호]로, 주안점은 줄마다 '-'로 시작한다 (학교 양식의 쓰는 법)."""
    lines = []
    for entry in entries:
        method_lines = [part.strip() for part in entry["methods"].split("\n") if part.strip()]
        if method_lines:                                  # 첫 줄은 수업 방법, 이어지는 줄은 활동 ('- …')
            first = method_lines[0]
            lines.append(first if first.startswith("[") else f"[{first}]")
            lines += [part if part[0] in "-[※·•" else f"-{part}" for part in method_lines[1:]]
        for part in entry["focus"].split("\n"):
            part = part.strip()
            if part:
                lines.append(part if part[0] in "-[※·•" else f"-{part}")
    return lines


def _height(columns: list[tuple[list[str], int]]) -> tuple[int, int]:
    """(행 높이, 가장 긴 칸의 줄 수 어림)."""
    height = max([MIN_ROW] + [text_height("\n".join(lines) or " ", width, SIZE) for lines, width in columns])
    return height, max(1, round((height - 600) / (SIZE * 1.6)))


def _plain_paras(tc: str, lines: list[str]) -> list[str]:
    template = cell_paragraphs(tc)[0]
    return [para(template, line) for line in lines or [""]]


def period_lines(week: dict) -> list[str]:
    """기간 글. 칸이 좁아 긴 기간(10.19.~10.30.)은 '~' 뒤에서 줄을 바꾼다."""
    text = period_text(week["start"], week["end"])
    if len(text) <= PERIOD_ONE_LINE or "~" not in text:
        return [text]
    start, end = text.split("~", 1)
    return [f"{start}~", end]


def estimated_mark(text: str, ctx: dict, memo: bool = False) -> str:
    """학사일정을 어림으로 넣었으면 형광펜(memo면 메모까지). 아니면 그대로."""
    if not ctx["estimated"]:
        return text
    return check(text) if memo else pen(text)


def _period_paras(tc: str, week: dict, ctx: dict, first_row: bool = False) -> list[str]:
    first = cell_paragraphs(tc)[0]
    lines = period_lines(week)
    paragraphs = [para(first, estimated_mark(line, ctx, memo=first_row and index == 0))
                  for index, line in enumerate(lines)]
    if week["deducted"]:
        paragraphs.append(para(first, estimated_mark(f"({week['deducted']})", ctx), ctx["red_number"]))
    return paragraphs


# ---------------------------------------------------------------- 2학기 양식 (5열)

def _row5(cells: dict, week: dict, entries: list[dict], ctx: dict, row_no: int) -> tuple[list[str], int]:
    get = lambda col: cells[(col, 1 if row_no == 1 else 2)]          # noqa: E731  첫 행은 위 굵은 선 칸
    units, codes = _lines(entries, "unit"), _lines(entries, "standards")
    hours = [estimated_mark(f"{week['hours']}/{week['cumulative']}", ctx)]
    height, _ = _height([(["0.00.~00.00.", "(0)"], cell_width(get(0))), (hours, cell_width(get(1))),
                         (units, cell_width(get(2))), (codes, cell_width(get(3))), (week["notes"], cell_width(get(4)))])
    where = {"row": row_no, "height": height}
    return [fill_cell(get(0), _period_paras(get(0), week, ctx, row_no == 1), **where),
            fill_cell(get(1), _plain_paras(get(1), hours), **where),
            fill_cell(get(2), _plain_paras(get(2), units), **where),
            fill_cell(get(3), _plain_paras(get(3), codes), **where),
            fill_cell(get(4), _note_paras(get(4), week["notes"], ctx, _extra_notes(entries, ctx, row_no)),
                      **where)], height


# ---------------------------------------------------------------- 1학기 양식 (7열)

def _diagonal(tc: str, hours: str, total: str, blank_lines: int) -> list[str]:
    """예정 시간(왼쪽 위)과 실시 누계(오른쪽 아래) 사이를 빈 문단으로 띄운다 (양식의 대각선 칸)."""
    paragraphs = cell_paragraphs(tc)
    middle = paragraphs[min(2, len(paragraphs) - 1)]
    return [para(paragraphs[0], hours)] + [para(middle, "") for _ in range(blank_lines)] + [para(paragraphs[-1], total)]


def _row7(cells: dict, week: dict, entries: list[dict], ctx: dict, row_no: int) -> tuple[list[str], int]:
    get = lambda col: cells[(col, 1 if row_no == 1 else 2)]          # noqa: E731
    units, teaching = _lines(entries, "unit"), _teaching_lines(entries)
    codes = split_ranges(_lines(entries, "standards"), alone=True)        # 좁은 성취기준 칸 (양식처럼 세 줄)
    height, lines = _height([(["0.00.~00.00.", "(0)"], cell_width(get(1))), (units, cell_width(get(2))),
                             (codes, cell_width(get(3))), (teaching, cell_width(get(4))),
                             (week["notes"], cell_width(get(6)))])
    where = {"row": row_no, "height": height}
    return [fill_cell(get(0), _plain_paras(get(0), [week["week"]]), **where),
            fill_cell(get(1), _period_paras(get(1), week, ctx, row_no == 1), **where),
            fill_cell(get(2), _plain_paras(get(2), units), **where),
            fill_cell(get(3), _plain_paras(get(3), codes), **where),
            fill_cell(get(4), _plain_paras(get(4), teaching), **where),
            fill_cell(get(5), _diagonal(get(5), estimated_mark(str(week["hours"]), ctx),
                                        estimated_mark(str(week["cumulative"]), ctx),
                                        max(1, lines - 2)), **where),
            fill_cell(get(6), _note_paras(get(6), week["notes"], ctx, _extra_notes(entries, ctx, row_no)),
                      **where)], height


# ---------------------------------------------------------------- 표

def progress_table(base: str, plan: dict) -> str:
    """양식 진도표 base를 학사일정 줄 수만큼 행을 늘리거나 줄여 채운 표."""
    cells = cell_map(base)
    ctx = _context(base, plan)
    header = sorted((tc for (col, row), tc in cells.items() if row == 0),
                    key=lambda tc: int(ADDR_RE.search(tc).group(1)))
    rows, heights = [header], [max(cell_height(tc) for tc in header)]
    make = _row7 if has_teaching_column(base) else _row5
    for number, week in enumerate(plan["weeks"], 1):
        row, height = make(cells, week, _entries(plan, week), ctx, number)
        rows.append(row)
        heights.append(height)
    return build_table(base, rows, heights)
