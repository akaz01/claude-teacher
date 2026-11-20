"""초등 교수학습 및 평가 계획의 모양. 점수·반영 비율·성취도(A~E)·정기시험이 없다.

차례(2026 학교생활기록부 기재요령 별표9의 필수 항목을 모두 담는다, references/elementary-plan.md 3-1):
Ⅰ 교수학습 운영계획 · Ⅱ 평가의 목적 · Ⅲ 평가의 방향과 방침 · Ⅳ 성취기준별 평가 계획(영역·요소·방법·시기·성취수준)
· Ⅴ 평가 세부 기준(채점 기준) · Ⅵ 결시자·학적변동자 처리 · Ⅶ 평가 결과 활용과 통지 · Ⅷ 평가 시 유의 사항(AI 포함)
"""

from __future__ import annotations

from make_course_plan_layout import (
    TODO, cell, col_inner, direction_section, head, head_blocks, kept_tables, lines_section, note,
    progress_blocks, section, text_height, wrap_wide)

from course_form_marks import pen, rule

ITEM_HEAD = ["시기", "성취기준", "단원명\n(영역)", "평가 요소", "수업·평가 방법\n(연계 주안점)", "단계", "성취수준"]
ITEM_WIDTHS = [9, 15, 15, 14, 17, 10, 20]
CRITERIA_HEAD = ["성취기준", "평가 요소", "단계", "채점 기준"]
CRITERIA_WIDTHS = [14, 22, 10, 54]


def _codes(item: dict, inner: int) -> str:
    return wrap_wide("\n".join(quote["code"] for quote in item["standards"]), inner) or TODO


def _unit(item: dict) -> str:
    return "\n".join(part for part in (item["unit"], f"({item['area']})" if item["area"] else "") if part) or TODO


def _item_group(lead: list[dict], texts: dict[str, str], scale: list[str],
                widths: list[float], names: list[str] | None = None) -> tuple[list[list[dict]], int]:
    """평가 하나의 행 묶음(단계마다 한 행, 앞 칸들은 합침)과 높이 어림. names: 단계 칸에 보일 글(표시 포함)."""
    names = names or scale
    rows = [([cell(names[depth])] if depth else [*lead, cell(names[depth])])
            + [cell(texts.get(level) or TODO, align="left")] for depth, level in enumerate(scale)]
    last = len(widths) - 1
    levels = sum(text_height(texts.get(level) or TODO, col_inner(widths, last)) for level in scale)
    leads = max(text_height(c["text"], col_inner(widths, n)) for n, c in enumerate(lead))
    return rows, max(levels, leads)


def items_tables(evaluation: dict) -> list[dict]:
    scale, groups = evaluation["scale"], []
    for index, item in enumerate(evaluation["items"]):
        span = len(scale)
        # 단계의 수와 이름은 학교 규정: 형광펜, 첫 평가의 첫 단계에 메모
        names = [rule(level) if index == 0 and depth == 0 else pen(level) for depth, level in enumerate(scale)]
        lead = [cell(item["timing"] or TODO, rowspan=span), cell(_codes(item, col_inner(ITEM_WIDTHS, 1)), rowspan=span),
                cell(_unit(item), rowspan=span), cell(item["element"] or TODO, rowspan=span),
                cell(item["method"] or TODO, rowspan=span, align="left")]
        groups.append(_item_group(lead, item["levels"], scale, ITEM_WIDTHS, names))
    return kept_tables([head(text) for text in ITEM_HEAD], groups, ITEM_WIDTHS)


def criteria_tables(evaluation: dict) -> list[dict]:
    scale, groups = evaluation["scale"], []
    for item in evaluation["items"]:
        lead = [cell(_codes(item, col_inner(CRITERIA_WIDTHS, 0)), rowspan=len(scale)),
                cell(item["element"] or TODO, rowspan=len(scale))]
        groups.append(_item_group(lead, item["criteria"], scale, CRITERIA_WIDTHS))
    return kept_tables([head(text) for text in CRITERIA_HEAD], groups, CRITERIA_WIDTHS)


def _items_blocks(evaluation: dict) -> list[dict]:
    blocks = [section("Ⅳ", "성취기준별 평가 계획")]
    if not evaluation["items"]:
        return blocks + [{"type": "paragraph", "text": TODO},
                         section("Ⅴ", "평가 세부 기준"), {"type": "paragraph", "text": TODO}]
    return blocks + [*items_tables(evaluation),
                     section("Ⅴ", "평가 세부 기준"), *criteria_tables(evaluation)]


def elementary_blocks(plan: dict, warnings: list[str]) -> list[dict]:
    info, evaluation = plan["info"], plan["evaluation"]
    if evaluation["remote"]:
        warnings.append("초등 차례에는 원격수업 항이 없어 evaluation.remote는 넣지 않음")
    return [*head_blocks(info), *progress_blocks(plan),
            *lines_section("Ⅱ", "평가의 목적", evaluation["purpose"], "평가의 목적(evaluation.purpose)", warnings),
            *direction_section("Ⅲ", evaluation, warnings), *_items_blocks(evaluation),
            *lines_section("Ⅵ", "결시자·학적변동자 처리", evaluation["absence"],
                           "결시자·학적변동자 처리(evaluation.absence)", warnings),
            *lines_section("Ⅶ", "평가 결과 활용과 통지", evaluation["use"], "평가 결과 활용과 통지(evaluation.use)",
                           warnings),
            *lines_section("Ⅷ", "평가 시 유의 사항", evaluation["cautions"], "평가 시 유의 사항(evaluation.cautions)",
                           warnings)]
