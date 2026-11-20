"""학교 양식 머리(제목, ◆ 대상 학년·학점·지도 교사), 목록 절(가. 나. …), Ⅳ 평가의 종류와 방법 표,
Ⅴ 기준 성취율과 성취도 표 채우기.

목록 절은 양식의 첫 항목 문단 모양으로 항목을 다시 쓰고, 항목 사이에 있던 표(Ⅷ 결시 처리 표 등)는
양식에서 앞에 있던 항목 수만큼 뒤에 다시 놓는다.
"""

from __future__ import annotations

import re

from make_course_plan_check import number_text
from make_course_plan_layout import ACHIEVEMENT, TODO

from course_form_marks import MEMO_CLOSE, PEN_CLOSE, PEN_OPEN, RULE_OPEN, pen, rule, wrap_paragraph

from course_form_xml import (build_table, cell_height, cell_map, cell_paragraphs, cell_width, char_with, fill_cell,
                             first_char, first_table, page_break_before, para, plain, run_chars, split_ranges, split_widths, table_shape,
                             table_width, tables_in, text_cell, text_height)

LABELS = "가나다라마바사아자차카타파하"
ITEM_RE = re.compile(r"^\s*[가-하]\.\s?")
NUMBER_RE = re.compile(r"^\s*\d+\.\s")
HEIGHT_RE = re.compile(r'(<hp:cellSz width="\d+" height=")\d+')
SIZE = 900
MIN_KIND_WIDTH = 8800      # 평가 열 하나의 최소 너비: '[10공수2-01-01]'이 한 줄에 들어감 (한글 2024에서 8743은 들어감)
MIN_REMARK_WIDTH = 2800    # 비고 열의 최소 너비: '100%'가 한 줄에 들어감


def label(index: int) -> str:
    return LABELS[index] if index < len(LABELS) else f"{LABELS[-1]}{index - len(LABELS) + 2}"


def with_mark(line: dict) -> str:
    """학교 규정에 따라 바꿀 문장("rule": true)은 형광펜과 메모로 표시한다."""
    return rule(line["text"]) if line["rule"] else line["text"]


def set_height(tc: str, height: int) -> str:
    return HEIGHT_RE.sub(rf"\g<1>{height}", tc, count=1)


# ---------------------------------------------------------------- 머리

def title_paragraph(title_para: str, info: dict) -> str:
    """제목 표의 '학년도'가 든 칸 첫 문단을 'YYYY학년도 N학기 <과목> '으로 바꾼다."""
    cells = cell_map(first_table(title_para))
    tc = next(tc for tc in cells.values() if "학년도" in plain(tc))
    paragraphs = cell_paragraphs(tc)
    char = next((c for c, text in run_chars(paragraphs[0]) if text.strip()), first_char(paragraphs[0]))
    grade = f" {info['grade']}학년" if info["level"] == "초" else ""
    first = para(paragraphs[0], f"{info['year']}학년도 {info['semester']}학기{grade} <{info['subject']}> ", char)
    return title_para.replace(tc, fill_cell(tc, [first, *paragraphs[1:]]), 1)


def info_paragraph(box_para: str, info: dict) -> str:
    """◆ 상자(1×1 표): 대상 학년, 학점(중학교는 주당 시수), 지도 교사 세 줄."""
    table = first_table(box_para)
    tc = next(iter(cell_map(table).values()))
    template = cell_paragraphs(tc)[0]
    diamond = char_with(tc, "◆") or first_char(template)
    name_char = char_with(tc, "대상") or diamond
    value_char = char_with(tc, ":") or first_char(template)
    grade = f"{info['grade']}학년" + (f" ({info['classes']})" if info["classes"] else "")
    hours = (("학점", f"{info['credits']}학점") if info["level"] == "고"
             else ("주당 시수", f"{info['weekly_hours']}시간"))
    teachers = ", ".join(f"{name} (인)" for name in info["teachers"]) or TODO
    lines = [("대상 학년", grade), hours, ("지도 교사", teachers)]
    paragraphs = [para(template, [(diamond, "◆ "), (name_char, name), (value_char, f" : {value}")])
                  for name, value in lines]
    height = max(cell_height(tc), round(len(lines) * 1200 * 1.6) + 600)
    return box_para.replace(table, build_table(table, [[fill_cell(tc, paragraphs, height=height)]], [height]), 1)


# ---------------------------------------------------------------- 목록 절

def is_item(paragraph: str) -> bool:
    return not tables_in(paragraph) and bool(ITEM_RE.match(plain(paragraph)))


def item_paragraphs(template: str, lines: list[dict], name: str, warnings: list[str]) -> list[str]:
    """가. 나. 항목 문단들 (양식 첫 항목의 문단 모양과 들여쓰기). 비어 있으면 [작성 필요]와 경고."""
    text = plain(template)
    indent = text[:len(text) - len(text.lstrip())]
    char = first_char(template)
    if not lines:
        warnings.append(f"{name}이 비어 있어 {TODO}로 둠")
        return [para(template, f"{indent}{label(0)}. {TODO}", char)]
    return [para(template, f"{indent}{label(index)}. {with_mark(line)}", char) for index, line in enumerate(lines)]


def mark_table(paragraph: str) -> str:
    """양식에 있던 표(Ⅷ 결시 처리 표 등)의 본문 칸 글(그 학교 규정)에 형광펜을 칠하고, 첫 글에 메모를 단다.
    머리행과 첫 열(구분)은 그대로 둔다."""
    table = first_table(paragraph)
    first = True
    new_table = table
    for (col, row), tc in sorted(cell_map(table).items(), key=lambda item: (item[0][1], item[0][0])):
        if row == 0 or col == 0:
            continue
        marked = []
        for item in cell_paragraphs(tc):
            if first and plain(item).strip():
                marked.append(wrap_paragraph(item, RULE_OPEN, MEMO_CLOSE))
                first = False
            else:
                marked.append(wrap_paragraph(item, PEN_OPEN, PEN_CLOSE))
        new_table = new_table.replace(tc, fill_cell(tc, marked), 1)
    return paragraph.replace(table, new_table, 1)


def list_part(paragraphs: list[str], lines: list[dict], name: str, warnings: list[str],
              rule_tables: bool = False) -> list[str]:
    """절 제목 + 항목. 항목 사이의 표 문단은 양식에서 앞에 있던 항목 수만큼 뒤에 다시 놓는다.
    rule_tables가 참이면 그 표의 글에 형광펜과 메모를 단다(양식 학교의 규정 글이 그대로 남으므로)."""
    items = [index for index, paragraph in enumerate(paragraphs) if is_item(paragraph)]
    if not items:
        return paragraphs
    first, last = items[0], items[-1]
    kept = [(sum(1 for i in items if i < index), mark_table(paragraphs[index]) if rule_tables else paragraphs[index])
            for index in range(first, last + 1) if index not in items and tables_in(paragraphs[index])]
    new_items = item_paragraphs(paragraphs[first], lines, name, warnings)
    body: list[str] = []
    for position, item in enumerate(new_items, 1):
        body.append(item)
        body += [table for after, table in kept if min(after, len(new_items)) == position]
    return paragraphs[:first] + body + paragraphs[last + 1:]


def direction_part(paragraphs: list[str], evaluation: dict, warnings: list[str]) -> list[str]:
    """Ⅲ: '1. 평가의 기본 방향' 항목들과 '2. 평가의 방침' 항목들."""
    titles = [index for index, paragraph in enumerate(paragraphs)
              if not tables_in(paragraph) and NUMBER_RE.match(plain(paragraph))]
    if len(titles) < 2:
        return list_part(paragraphs, evaluation["direction"] + evaluation["policy"], "평가의 방향과 방침", warnings)
    head, second = titles[0], titles[1]
    upper = list_part(paragraphs[head:second], evaluation["direction"],
                      "평가의 기본 방향(evaluation.direction)", warnings)
    lower = list_part(paragraphs[second:], evaluation["policy"], "평가의 방침(evaluation.policy)", warnings)
    return paragraphs[:head] + upper + lower


# ---------------------------------------------------------------- Ⅳ 평가의 종류와 방법

def _kind_values(kind: dict) -> list[list[str]]:
    return [[kind["method"]], [f"{number_text(kind['max_score'])}점"], [pen(f"{number_text(kind['ratio'])}%")],
            [pen(f"{number_text(kind['essay_ratio'])}%")], split_ranges(kind["standards"]) or [""],
            kind["timing"].split("\n")]


def _kind_heads(cells: dict, exams: list[dict], tasks: list[dict], widths: list[int], remark: int) -> list[str]:
    """머리 첫 행: 구분, 평가영역, 정기시험(n%), 수행평가(n%), 비고."""
    last = max(col for col, _ in cells)
    head = [cells[(0, 0)], cells[(1, 0)]]
    col = 2
    for group, name in ((exams, "정기시험"), (tasks, "수행평가")):
        if group:
            ratio = number_text(sum(kind["ratio"] for kind in group))
            head.append(text_cell(cells[(2, 0)], f"{name}({ratio}%)", col=col, colspan=len(group),
                                  width=sum(widths[col - 2:col - 2 + len(group)])))
            col += len(group)
    return head + [fill_cell(cells[(last, 0)], cell_paragraphs(cells[(last, 0)]), col=col, width=remark)]


def kinds_table(base: str, evaluation: dict, semester: int) -> str:
    """양식 Ⅳ 표(8행)를 평가 종류 수만큼 열을 늘리거나 줄여 채운다. 행 이름 칸은 양식 그대로."""
    cells = cell_map(base)
    exams = [kind for kind in evaluation["kinds"] if kind["type"] == "정기시험"]
    tasks = [kind for kind in evaluation["kinds"] if kind["type"] == "수행평가"]
    kinds = exams + tasks
    last = max(col for col, _ in cells)
    value_col, remark_col = last - 1, 2 + len(kinds)       # 마지막 평가 열 칸 모양을 모든 평가 열에 쓴다
    labels = cell_width(cells[(0, 0)]) + cell_width(cells[(1, 0)])
    remark = cell_width(cells[(last, 0)])
    room = table_width(base) - labels - remark
    if room < MIN_KIND_WIDTH * len(kinds):                 # 평가 열이 좁으면 비고 열을 줄인다
        remark = max(MIN_REMARK_WIDTH, table_width(base) - labels - MIN_KIND_WIDTH * len(kinds))
    widths = split_widths(table_width(base) - labels - remark, len(kinds))
    name_height = max([cell_height(cells[(value_col, 1)])] +
                      [text_height(kind["name"], widths[n], SIZE) for n, kind in enumerate(kinds)])
    names = [text_cell(cells[(value_col, 1)], kind["name"], col=2 + n, width=widths[n], height=name_height)
             for n, kind in enumerate(kinds)]
    rows = [_kind_heads(cells, exams, tasks, widths, remark), names]
    heights = [cell_height(cells[(2, 0)]), name_height]
    values = [_kind_values(kind) for kind in kinds]
    remarks = {4: pen(f"{number_text(sum(kind['ratio'] for kind in kinds))}%"),
               5: pen(f"{number_text(sum(kind['essay_ratio'] for kind in kinds))}%")}
    values[0][2] = [rule(f"{number_text(kinds[0]['ratio'])}%")]     # 반영 비율 첫 칸에 메모 (나머지는 형광펜만)
    for index, row_no in enumerate(range(2, 8)):
        height = max([cell_height(cells[(value_col, row_no)])] +
                     [text_height("\n".join(value[index]), widths[n], SIZE) for n, value in enumerate(values)])
        row = [text_cell(cells[(0, 2)], f"{semester}\n학기")] if row_no == 2 else []
        row.append(set_height(cells[(1, row_no)], height))
        row += [text_cell(cells[(value_col, row_no)], value[index], col=2 + n, width=widths[n], height=height)
                for n, value in enumerate(values)]
        row.append(text_cell(cells[(last, row_no)], remarks.get(row_no, ""), col=remark_col, width=remark,
                             height=height))
        rows.append(row)
        heights.append(height)
    rows[2][0] = set_height(rows[2][0], sum(heights[2:]))
    return build_table(base, rows, heights, cols=remark_col + 1)


def kinds_part(paragraphs: list[str], evaluation: dict, semester: int, note_template: str,
               warnings: list[str]) -> list[str]:
    """Ⅳ 절: 새 쪽에서 시작하고(2학기 학교 양식처럼, 표 머리행만 쪽 끝에 남지 않게), 표를 바꾼다.
    학교 규정에 따라 바꿀 반영 비율·서술형 비율 칸은 형광펜으로 칠하고 첫 칸에 메모를 단다."""
    out = [page_break_before(paragraphs[0])]
    for paragraph in paragraphs[1:]:
        table = first_table(paragraph)
        if not table or table_shape(table)[0] < 6:
            out.append(paragraph)
            continue
        if evaluation["kinds"]:
            out.append(paragraph.replace(table, kinds_table(table, evaluation, semester), 1))
        else:
            warnings.append(f"평가의 종류(evaluation.kinds)가 없어 {TODO}로 둠")
            out.append(para(note_template, TODO))
    return out


# ---------------------------------------------------------------- Ⅴ 기준 성취율과 성취도

def achievement_table(base: str, course_type: str) -> str:
    header_texts, body, _ = ACHIEVEMENT[course_type]
    cells = cell_map(base)
    last_row = max(row for _, row in cells)
    rows = [[text_cell(cells[(0, 0)], header_texts[0]), text_cell(cells[(1, 0)], header_texts[1])]]
    heights = [cell_height(cells[(0, 0)])]
    for number, (rate, grade) in enumerate(body, 1):
        source = last_row if number == len(body) else 1          # 마지막 행은 아래 굵은 선 칸
        height = max(cell_height(cells[(0, source)]), text_height(rate, cell_width(cells[(0, source)]), SIZE))
        rows.append([text_cell(cells[(0, source)], rate, row=number, height=height),
                     text_cell(cells[(1, source)], grade, row=number, height=height)])
        heights.append(height)
    return build_table(base, rows, heights)


def achievement_part(paragraphs: list[str], course_type: str) -> list[str]:
    """Ⅴ 절: 표 행을 과목 유형에 맞추고, 표 아래 ※ 문단을 덧붙임 글로 바꾼다(없으면 뺀다)."""
    extra = ACHIEVEMENT[course_type][2]
    out = []
    for paragraph in paragraphs:
        table = first_table(paragraph)
        if table and table_shape(table)[0] >= 3:
            out.append(paragraph.replace(table, achievement_table(table, course_type), 1))
        elif not table and plain(paragraph).strip().startswith("※"):
            if extra:
                out.append(para(paragraph, extra))
        else:
            out.append(paragraph)
    return out
