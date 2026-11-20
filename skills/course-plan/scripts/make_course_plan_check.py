"""교과진도평가계획 점검: 진도-평가 성취기준 연결, 반영 비율, 수행평가 배점, 평가 시기, 학사일정.

모두 경고 글 목록으로 돌려준다(만들기는 멈추지 않는다). 입력은 make_course_plan_input.read_plan이 정리한 값이다.
초등 점검(점수 말 섞임, 평가 단계 등)은 make_course_plan_check_elementary.py.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date

from make_course_plan_input import term_of
from make_course_plan_check_elementary import AI_WORDS, MONTH, elementary_warnings
from school_calendar import holiday_warnings, span_warnings

CODE_TEXT = r"[0-9]{1,2}[가-힣A-Za-z0-9]+[0-9]{0,2}-[0-9]{2}(?:-[0-9]{2})?"   # 10통사1-01-01, 6국02-01 (tools/test_standard_quotes.py와 같은 꼴)
CODE = re.compile(rf"\[({CODE_TEXT})\]")
RANGE = re.compile(rf"\[({CODE_TEXT})\]\s*[~∼]\s*\[({CODE_TEXT})\]")
CODE_PARTS = re.compile(r"^(.+?)([0-9]{2})-([0-9]{2})(?:-([0-9]{2}))?$")
NUMBER = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)")
PERCENT = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*%")
MAX_SHOWN = 8                  # 경고 한 줄에 보여 줄 코드 수
HIGH_SESSIONS = 16             # 고교 1학점 = 16회
SEMESTER_WEEKS = 17            # 중·초 기준 시수는 연간 34주(학기 17주) 기준
BASE_TOLERANCE = 1.0           # 기본점수 '8(32%)'의 % 차이 허용 (반올림)
SCORE_TOLERANCE = 1e-6         # 소수 배점 합 비교 허용 오차 (1.1 + 2.2 ≠ 3.3 문제)
ESTIMATED_WARNING = ("학사일정을 어림으로 넣음(calendar.estimated): 진도표의 기간·예정 시간·누계에 형광펜을 칠하고 첫 칸에 메모를 닮. "
                     "학교 학사일정을 받아 바꾸세요")


def same(a: float, b: float) -> bool:
    return math.isclose(a, b, abs_tol=SCORE_TOLERANCE)


def number_text(value: float) -> str:
    return f"{round(value, 6):g}"


# ---------------------------------------------------------------- 성취기준 코드

def code_key(code: str) -> tuple | None:
    found = CODE_PARTS.match(code)
    if not found:
        return None
    return (found.group(1), *(int(part) for part in found.groups()[1:] if part is not None))


def _between(first: str, last: str, known: set[str]) -> list[str]:
    """[A]~[B]를 펼친다: 아는 코드 가운데 사이에 있는 것 + 끝자리만 다르면 사이 번호를 만든다."""
    a, b = code_key(first), code_key(last)
    if a is None or b is None or a[0] != b[0] or len(a) != len(b):
        return [first, last]
    low, high = min(a, b), max(a, b)
    found = {code for code in known if (key := code_key(code)) and len(key) == len(a) and low <= key <= high}
    if a[:-1] == b[:-1]:
        stem = first[:first.rfind("-") + 1]
        found |= {f"{stem}{n:02d}" for n in range(low[-1], high[-1] + 1)}
    return sorted(found | {first, last}, key=lambda code: code_key(code) or (code,))


def raw_codes(lines: list[str]) -> set[str]:
    return set(CODE.findall(" ".join(lines)))


def expand(lines: list[str], known: set[str]) -> list[str]:
    """성취기준 줄들 → 코드 목록 (범위 펼침). 줄을 이어 읽으므로 '[A]', '~', '[B]'처럼 나뉜 범위도 읽는다.
    '[전 범위]'처럼 코드 꼴이 아닌 괄호 글은 세지 않는다."""
    text = " ".join(lines)
    codes: list[str] = []
    for found in RANGE.finditer(text):
        codes += _between(found.group(1), found.group(2), known)
    codes += CODE.findall(RANGE.sub(" ", text))
    return list(dict.fromkeys(codes))


def _shown(codes: list[str]) -> str:
    listed = ", ".join(f"[{code}]" for code in codes[:MAX_SHOWN])
    return listed + (f" 외 {len(codes) - MAX_SHOWN}개" if len(codes) > MAX_SHOWN else "")


def _assessed_lines(evaluation: dict) -> list[list[str]]:
    lines = [kind["standards"] for kind in evaluation.get("kinds", [])]
    for task in evaluation.get("tasks", []) + evaluation.get("items", []):
        lines.append([quote["code"] for quote in task["standards"]])
    return lines


def _ordered(codes: set[str]) -> list[str]:
    return sorted(codes, key=lambda code: code_key(code) or (code,))


def standard_warnings(plan: dict) -> list[str]:
    taught_lines = [row["standards"] for row in plan["progress"]]
    assessed_lines = _assessed_lines(plan["evaluation"])
    known = set().union(*(raw_codes(lines) for lines in taught_lines + assessed_lines))
    taught = {c for lines in taught_lines for c in expand(lines, known)}
    assessed = {c for lines in assessed_lines for c in expand(lines, known)}
    warnings = []
    if missing := _ordered(taught - assessed):
        warnings.append(f"진도표에서 가르치지만 평가 계획에 없는 성취기준 {len(missing)}개: {_shown(missing)}")
    if extra := _ordered(assessed - taught):
        warnings.append(f"평가에 있지만 진도표에 없는 성취기준 {len(extra)}개: {_shown(extra)}")
    return warnings + level_warnings(plan["evaluation"].get("achievement_levels"), taught, known)


def level_warnings(levels: dict | None, taught: set[str], known: set[str]) -> list[str]:
    """Ⅺ 성취기준별 성취수준: 진도표의 성취기준이 모두 있는지, 수준 진술이 빈 곳이 있는지 (입력이 있을 때만)."""
    if not levels or not levels["units"]:
        return []
    standards = [standard for unit in levels["units"] for standard in unit["standards"]]
    listed = {code for standard in standards for code in expand([standard["code"]], known)}
    warnings = []
    if missing := _ordered(taught - listed):
        warnings.append(f"성취수준(Ⅺ)에 없는 성취기준 {len(missing)}개: {_shown(missing)}")
    empty = [standard["code"].strip("[]") for standard in standards
             if not standard["levels"] or any(not text for text in standard["levels"].values())]
    if empty:
        warnings.append(f"성취수준 진술이 빈 성취기준 {len(empty)}개: {_shown(empty)} (빈 칸은 그대로 둠)")
    return warnings


# ---------------------------------------------------------------- 비율·배점 (중·고)

def ratio_warnings(evaluation: dict) -> list[str]:
    kinds, rules = evaluation["kinds"], evaluation["rules"]
    if not kinds:
        return ["평가의 종류(evaluation.kinds)가 없음: Ⅳ 표를 비워 두고 비율·과제 이름 점검을 건너뜀"]
    total = sum(kind["ratio"] for kind in kinds)
    warnings = [] if same(total, 100) else [f"반영 비율 합이 {number_text(total)}%임 (100%가 되어야 함)"]
    performance = sum(kind["ratio"] for kind in kinds if kind["type"] == "수행평가")
    essay = sum(kind["essay_ratio"] for kind in kinds)
    if rules["performance_min"] is None or rules["essay_min"] is None:
        warnings.append("evaluation.rules(수행평가·서술형 하한)가 없어 비율 하한을 점검하지 않음")
    if rules["performance_min"] is not None and performance < rules["performance_min"] - SCORE_TOLERANCE:
        warnings.append(f"수행평가 비율 {number_text(performance)}%가 하한 {number_text(rules['performance_min'])}%보다 낮음")
    if rules["essay_min"] is not None and essay < rules["essay_min"] - SCORE_TOLERANCE:
        warnings.append(f"서술형 비율 합 {number_text(essay)}%가 하한 {number_text(rules['essay_min'])}%보다 낮음")
    return warnings


def _level_warnings(task: str, element: dict) -> list[str]:
    scores = [level["score"] for level in element["levels"]]
    name = f"'{task}' {element['name']}"
    warnings = []
    if any(upper <= lower for upper, lower in zip(scores, scores[1:])):
        warnings.append(f"{name}: 수준 점수가 위에서 아래로 줄어들지 않음 ({', '.join(map(number_text, scores))})")
    if not same(max(scores), element["points"]):
        warnings.append(f"{name}: 가장 높은 수준 점수 {number_text(max(scores))}가 요소 배점 "
                        f"{number_text(element['points'])}과 다름")
    return warnings


def _base_warnings(task: dict, total: float) -> list[str]:
    if not task["base"]:
        return [f"'{task['name']}' 기본점수 줄(base)이 없음: 학교 규정 확인 (기본점수를 주지 않는 학교면 무시)"]
    warnings = []
    for row in task["base"]:
        number, percent = NUMBER.match(row["score"]), PERCENT.search(row["score"])
        if not (number and percent and total):
            continue
        actual = float(number.group(1)) / total * 100
        if abs(actual - float(percent.group(1))) > BASE_TOLERANCE:
            warnings.append(f"'{task['name']}' 기본점수 '{row['score']}': 만점 {number_text(total)}점의 "
                            f"{number_text(round(actual, 1))}%임")
    return warnings


def task_score_warnings(task: dict, kinds: dict[str, dict]) -> list[str]:
    warnings: list[str] = []
    for area in task["areas"]:
        summed = sum(element["points"] for element in area["elements"])
        if not same(summed, area["points"]):
            warnings.append(f"'{task['name']}' {area['area']}: 요소 배점 합 {number_text(summed)}이 영역 배점 "
                            f"{number_text(area['points'])}과 다름")
        for element in area["elements"]:
            warnings += _level_warnings(task["name"], element)
    total = sum(area["points"] for area in task["areas"])
    kind = kinds.get(task["name"])
    if kind and not same(total, kind["max_score"]):
        warnings.append(f"'{task['name']}': 영역 배점 합 {number_text(total)}이 Ⅳ 표의 영역 만점 "
                        f"{number_text(kind['max_score'])}과 다름")
    return warnings + _base_warnings(task, total)


def _name_warnings(evaluation: dict) -> list[str]:
    """과제 수·이름이 Ⅳ 표의 수행평가와 맞는지. Ⅳ 표가 비면 ratio_warnings 한 줄로 알리고 건너뛴다."""
    if not evaluation["kinds"]:
        return []
    kinds = [kind["name"] for kind in evaluation["kinds"] if kind["type"] == "수행평가"]
    names = [task["name"] for task in evaluation["tasks"]]
    warnings = [f"Ⅳ 표의 평가 이름이 겹침: '{name}'" for name, count in
                Counter(kind["name"] for kind in evaluation["kinds"]).items() if count > 1]
    warnings += [f"세부기준 과제 이름이 겹침: '{name}'" for name, count in Counter(names).items() if count > 1]
    if len(names) != len(kinds):
        warnings.append(f"수행평가 세부기준 과제 {len(names)}개와 Ⅳ 표의 수행평가 영역 {len(kinds)}개가 다름")
    warnings += [f"Ⅳ 표의 수행평가 '{name}'에 맞는 세부기준(tasks)이 없음" for name in dict.fromkeys(kinds)
                 if name not in names]
    warnings += [f"세부기준 과제 '{name}'가 Ⅳ 표의 수행평가 영역 이름과 맞지 않음" for name in dict.fromkeys(names)
                 if name not in kinds]
    return warnings


def task_warnings(evaluation: dict) -> list[str]:
    kinds = {kind["name"]: kind for kind in evaluation["kinds"] if kind["type"] == "수행평가"}
    warnings = _name_warnings(evaluation)
    for task in evaluation["tasks"]:
        warnings += task_score_warnings(task, kinds)
        if not any(word in " ".join(task["notes"]) for word in AI_WORDS):
            warnings.append(f"'{task['name']}' 학생 유의사항에 AI 활용 안내가 없음")
    return warnings


# ---------------------------------------------------------------- 시기, 학사일정, 시수

def term_months(start: date, end: date) -> list[int]:
    """학기의 달을 순서대로 (해를 넘기면 12, 1, 2처럼)."""
    months, year, month = [], start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(month)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def _timed(evaluation: dict) -> tuple[list[tuple[str, str]], list[str]]:
    """시기를 볼 (이름, 시기) 목록. Ⅳ 표와 세부기준에 같은 이름이 있으면 한 번만 보고, 시기가 다르면 알린다."""
    kinds = {kind["name"]: kind["timing"] for kind in evaluation.get("kinds", [])}
    named = list(kinds.items())
    differ = []
    for task in evaluation.get("tasks", []):
        if task["name"] not in kinds:
            named.append((task["name"], task["timing"]))
        elif task["timing"] and kinds[task["name"]] and task["timing"] != kinds[task["name"]]:
            differ.append(f"'{task['name']}'의 평가 시기가 Ⅳ 표('{kinds[task['name']]}')와 세부기준"
                          f"('{task['timing']}')에서 다름")
    named += [(item["element"] or item["unit"] or f"{n}번째 평가", item["timing"])
              for n, item in enumerate(evaluation.get("items", []), 1)]
    return named, differ


def timing_warnings(plan: dict) -> list[str]:
    months = term_months(*term_of(plan["calendar"]))
    span = f"{months[0]}~{months[-1]}월" if months[0] <= months[-1] else f"{months[0]}월~다음 해 {months[-1]}월"
    named, warnings = _timed(plan["evaluation"])
    for name, timing in named:
        if not timing:
            warnings.append(f"'{name}'의 평가 시기가 비어 있음")
        elif any(int(m) not in months for m in MONTH.findall(timing)):
            warnings.append(f"'{name}'의 평가 시기 '{timing}'가 학기({span}) 밖에 있음")
    return warnings


def calendar_warnings(plan: dict) -> list[str]:
    info, weeks, calendar = plan["info"], plan["weeks"], plan["calendar"]
    start, _ = term_of(calendar)
    warnings = [f"학사일정: {warning}" for warning in holiday_warnings(calendar) + span_warnings(calendar)]
    if start.year != info["year"] and info["semester"] == 1:
        warnings.append(f"학사일정 개학일({start.year}년)이 학년도({info['year']})와 다름")
    used = {row["weeks"] for row in plan["progress"]}
    empty = [week["week"] for week in weeks if week["week"] not in used and week["class_days"] > 0]
    if empty:
        warnings.append(f"진도 내용이 없는 주: {', '.join(empty)} (진도표에 빈칸으로 둠)")
    return warnings + hours_warnings(info, weeks[-1]["cumulative"])


def hours_warnings(info: dict, total: int) -> list[str]:
    """누계(한 반 기준 주당 시수로 센 값)를 기준 수업량과 견준다."""
    if info["level"] == "고":
        standard, basis = info["credits"] * HIGH_SESSIONS, f"{info['credits']}학점 × {HIGH_SESSIONS}회"
    else:
        standard, basis = info["weekly_hours"] * SEMESTER_WEEKS, f"주당 {info['weekly_hours']}시간 × {SEMESTER_WEEKS}주"
    warnings = [f"예정 시간은 한 반 기준 '주당 시수 × 수업일 ÷ 5'로 셈: 누계 {total}시간 "
                f"(기준 {basis} = {standard}시간)"]
    if total < standard:
        warnings.append(f"예정 시간 누계 {total}시간이 기준 수업량 {standard}시간보다 {standard - total}시간 적음")
    if info["level"] == "고" and info["credits"] != info["weekly_hours"]:
        warnings.append(f"학점({info['credits']})과 주당 시수({info['weekly_hours']})가 다름: 예정 시간은 주당 시수로 셈")
    return warnings


def plan_warnings(plan: dict) -> list[str]:
    """점검 경고 전체 (형광펜·메모 수 줄은 make_course_plan이 맨 앞에 붙인다). 어림 학사일정이 첫 줄."""
    warnings = [ESTIMATED_WARNING] if plan["calendar"].get("estimated") else []
    warnings += standard_warnings(plan)
    if plan["info"]["level"] == "초":
        warnings += elementary_warnings(plan)
    else:
        evaluation = plan["evaluation"]
        warnings += ratio_warnings(evaluation) + task_warnings(evaluation)
        if plan["info"]["course_type"] == "자유학기" and any(k["type"] == "정기시험" for k in evaluation["kinds"]):
            warnings.append("자유학기에는 일제식 정기시험을 보지 않음: 정기시험을 빼 주세요")
    return warnings + timing_warnings(plan) + calendar_warnings(plan)
