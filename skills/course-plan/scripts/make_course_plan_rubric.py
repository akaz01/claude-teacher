"""중·고 Ⅵ 수행평가 세부기준: 과제마다 성취기준·평가 방법·시기 표, 채점 기준 표, 학생 유의사항 표.

채점 기준 표는 평가 영역·평가 척도 칸이 여러 행을 합치고 있어, 한글에서 행 단위로 나누면 머리행만 쪽 끝에 남는다
(한글 2024에서 확인). 그래서 표를 통째로 옮기고(keep_together), 한 쪽에 들어가지 않을 만큼 길면
평가 요소 묶음 경계에서 여러 표로 나눈다(표마다 머리행이 있다).
"""

from __future__ import annotations

import re

from make_course_plan_check import number_text
from make_course_plan_layout import CHUNK_LIMIT, TODO, cell, col_inner, head, marked, section, text_height

METHOD_BOXES = ("서술·논술", "구술·발표", "토의·토론", "프로젝트", "실험·실습", "포트폴리오", "기타")
GROUPED_WIDTHS = [13, 12, 13, 56, 8, 9]
PLAIN_WIDTHS = [14, 18, 60, 8, 9]


# ---------------------------------------------------------------- 성취기준·방법·시기

def _plain(name: str) -> str:
    return re.sub(r"(형|평가|법)$", "", re.sub(r"[\s·⋅]", "", name))


def method_line(methods: list[str]) -> str:
    """□서술·논술  ■프로젝트 … 고른 방법은 ■. 칸에 없는 방법은 ■기타(이름)."""
    chosen, others = set(), []
    for method in methods:
        name = _plain(method)
        found = [box for box in METHOD_BOXES[:-1] if name and (name in _plain(box) or _plain(box) in name)]
        if found:
            chosen.update(found)
        else:
            others.append(method)
    if others:
        chosen.add("기타")
    marks = [f"{'■' if box in chosen else '□'}{box}" for box in METHOD_BOXES]
    if others:
        marks[-1] += f"({', '.join(others)})"
    return "  ".join(marks)


def task_info_table(task: dict) -> dict:
    quotes = "\n".join(f"{q['code']} {q['text']}".strip() for q in task["standards"]) or TODO
    return {"type": "table", "widths": [12, 88], "rows": [
        [head("성취기준"), cell(quotes, align="left")], [head("평가 방법"), cell(method_line(task["methods"]))],
        [head("평가 시기"), cell(task["timing"] or TODO)]]}


def notes_table(task: dict) -> list[dict]:
    """학생 유의사항(AI 활용 포함). 채점 기준 표를 한 쪽 안에 두려고 따로 둔다."""
    if not task["notes"]:
        return []
    lines = "\n".join(f"‣ {text}" for text in task["notes"])
    return [{"type": "table", "widths": [12, 88], "rows": [[head("학생\n유의사항"), cell(lines, align="left")]]}]


# ---------------------------------------------------------------- 채점 기준 표

def _scale_text(task: dict, rows: int) -> str:
    elements = [element for area in task["areas"] for element in area["elements"]]
    top = sum(max(level["score"] for level in element["levels"]) for element in elements)
    low = sum(min(level["score"] for level in element["levels"]) for element in elements)
    if not (float(top).is_integer() and float(low).is_integer()) or top - low > 2 * rows:
        return f"{number_text(top)}\n~\n{number_text(low)}"
    return "\n".join(str(score) for score in range(int(top), int(low) - 1, -1))


def _group_runs(elements: list[dict]) -> dict[int, tuple[int, float]]:
    """같은 group이 이어진 요소 묶음: 시작 번호 → (요소 수, 배점 합). group이 없는 요소는 혼자 한 묶음."""
    runs, index = {}, 0
    while index < len(elements):
        end = index + 1
        while elements[index]["group"] and end < len(elements) and elements[end]["group"] == elements[index]["group"]:
            end += 1
        runs[index] = (end - index, sum(e["points"] for e in elements[index:end]))
        index = end
    return runs


def _element_rows(elements: list[dict], grouped: bool) -> list[list[dict]]:
    rows, runs = [], _group_runs(elements)
    for number, element in enumerate(elements):
        for depth, level in enumerate(element["levels"]):
            row = []
            if depth == 0 and grouped and element["group"] and number in runs:
                count, points = runs[number]
                span = sum(len(e["levels"]) for e in elements[number:number + count])
                row.append(cell(f"{element['group']}\n({number_text(points)}점)", rowspan=span))
            if depth == 0:
                label = f"{element['name']}\n({number_text(element['points'])}점)"
                row.append(cell(label, rowspan=len(element["levels"]), colspan=2 if grouped and not element["group"] else 1))
            rows.append(row + [cell(level["text"], align="left"), cell(number_text(level["score"]))])
    return rows


def _chunks(task: dict, inner: int) -> list[list[tuple[dict, list[dict]]]]:
    """(영역, 요소 묶음) 단위를 높이 한도 안에서 표 덩이로 모은다. 묶음은 쪼개지 않는다."""
    chunks: list[list[tuple[dict, list[dict]]]] = [[]]
    height = 0
    for area in task["areas"]:
        for start, (count, _) in _group_runs(area["elements"]).items():
            part = area["elements"][start:start + count]
            size = sum(text_height(level["text"], inner) for element in part for level in element["levels"])
            if chunks[-1] and height + size > CHUNK_LIMIT:
                chunks.append([])
                height = 0
            chunks[-1].append((area, part))
            height += size
    return chunks


def _chunk_rows(units: list[tuple[dict, list[dict]]], grouped: bool) -> list[list[dict]]:
    merged: list[tuple[dict, list[dict]]] = []
    for area, part in units:
        if merged and merged[-1][0] is area:
            merged[-1] = (area, merged[-1][1] + part)
        else:
            merged.append((area, part))
    rows: list[list[dict]] = []
    for area, part in merged:
        body = _element_rows(part, grouped)
        body[0].insert(0, cell(f"{area['area']}\n({number_text(area['points'])}점)", rowspan=len(body)))
        rows += body
    return rows


def rubric_tables(task: dict) -> list[dict]:
    """채점 기준 표(들). 기본점수 줄은 마지막 표에 둔다."""
    grouped = any(element["group"] for area in task["areas"] for element in area["elements"])
    widths = GROUPED_WIDTHS if grouped else PLAIN_WIDTHS
    header = [head("평가 영역"), head("평가 요소", colspan=2 if grouped else 1), head("채점 기준"), head("배점"),
              head("평가\n척도")]
    chunks = _chunks(task, col_inner(widths, len(widths) - 3))
    tables = []
    for index, units in enumerate(chunks):
        rows = _chunk_rows(units, grouped)
        rows[0].append(cell(_scale_text(task, len(rows)) if index == 0 else "", rowspan=len(rows)))
        if index == len(chunks) - 1:
            rows += [[cell(marked(base), colspan=len(widths) - 2), cell(base["score"], colspan=2)]
                     for base in task["base"]]
        tables.append({"type": "table", "header": header, "rows": rows, "widths": widths, "keep_together": True})
    return tables


def tasks_blocks(evaluation: dict, warnings: list[str]) -> list[dict]:
    blocks = [section("Ⅵ", "수행평가 세부기준")]
    if not evaluation["tasks"]:
        warnings.append(f"수행평가 세부기준(evaluation.tasks)이 없어 {TODO}로 둠")
        return blocks + [{"type": "paragraph", "text": TODO}]
    for number, task in enumerate(evaluation["tasks"], 1):
        blocks += [{"type": "heading", "text": f"{number}. {task['name']}", "level": 2},
                   task_info_table(task), *rubric_tables(task), *notes_table(task)]
    return blocks
