"""교과진도평가계획 입력 읽기: 칸마다 형식을 보고 정리한 새 dict를 돌려준다. 받은 입력은 바꾸지 않는다.

틀린 형식은 칸 이름을 넣어 CoursePlanError로 알린다(목록·객체 종류, null, 아주 긴 글, 큰 수, NaN).
입력 형식 설명과 예시: references/course-plan-input.md
"""

from __future__ import annotations

import math
from datetime import date

from school_calendar import CalendarError, plan_weeks, term

LEVELS = ("고", "중", "초")
LEVEL_NAMES = {"고": "고등학교", "중": "중학교", "초": "초등학교"}
COURSE_TYPES = {"고": ("공통", "선택", "체육·예술", "교양"),
                "중": ("중학교", "체육·예술", "자유학기", "교양"), "초": ("초등",)}
DEFAULT_TYPE = {"중": "중학교", "초": "초등"}
TOP_GRADE = {"고": 3, "중": 3, "초": 6}
KIND_TYPES = ("정기시험", "수행평가")
SECONDARY_ONLY = ("kinds", "rules", "tasks", "achievement_levels")      # 초등 입력에 있으면 오류
ELEMENTARY_ONLY = ("scale", "items")              # 중·고 입력에 있으면 오류
TEXT_LISTS = ("purpose", "direction", "policy", "cautions", "absence", "use", "remote")
MAX_TEXT = 3000          # 칸 하나의 글자 수 한도 (한 쪽을 넘는 글은 받지 않는다)
MAX_LIST = 100           # 문장 목록 한도
MAX_PROGRESS = 300       # 진도 줄 한도 (21주 × 여러 담당)
MAX_KINDS = 12           # 평가 종류 (Ⅳ 표 열 수 한도 30 안)
MAX_TASKS = 12
MAX_AREAS = 12
MAX_ELEMENTS = 40
MAX_LEVELS = 10
MAX_ITEMS = 100          # 초등 성취기준별 평가 줄
MAX_SCORE = 1000
MAX_TEACHERS = 30
MAX_NUMBER_TEXT = 10 ** 15     # 글 칸에 넣을 수 있는 수의 크기 (아주 큰 정수는 글로 바꾸지 못한다)
RULE_DEFAULT = {"absence"}     # rule을 적지 않아도 학교 규정 값으로 표시(형광펜·메모)되는 칸 (결시 처리는 거의 모두 학교 규정)
SCALE_SIZES = (2, 5)


class CoursePlanError(ValueError):
    """입력이 교과진도평가계획 형식에 맞지 않을 때."""


# ---------------------------------------------------------------- 기본 값 읽기

MARK_CHARS = dict.fromkeys(range(0xE000, 0xE010))     # 형광펜·메모 표식으로 쓰는 사용자 영역 문자 (course_form_marks.py)


def _scalar_text(value, field: str) -> str:
    """글·수 하나 → 글. 목록·객체(겹친 목록 포함)는 오류라 아주 깊게 겹친 입력도 되부름 없이 막힌다."""
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise CoursePlanError(f"'{field}'는 글이어야 함 (받은 형식: {type(value).__name__})")
    if isinstance(value, float) and not math.isfinite(value):
        raise CoursePlanError(f"'{field}'에 숫자가 아닌 값({value})이 있음")
    if isinstance(value, int) and abs(value) > MAX_NUMBER_TEXT:
        raise CoursePlanError(f"'{field}'의 수가 너무 큼")
    return str(value).translate(MARK_CHARS)


def read_text(value, field: str, required: bool = False, limit: int = MAX_TEXT) -> str:
    """글 칸. 숫자는 글로, 글의 목록(한 겹만)은 줄바꿈으로 잇는다. null은 빈 글."""
    if isinstance(value, list):
        read_list(value, field, MAX_LIST)
        value = "\n".join(_scalar_text(item, f"{field}의 {n}번째 줄") for n, item in enumerate(value, 1))
    else:
        value = _scalar_text(value, field)
    text = value.strip()
    if len(text) > limit:
        raise CoursePlanError(f"'{field}' 글이 너무 김 ({len(text)}자, {limit}자까지)")
    if required and not text:
        raise CoursePlanError(f"'{field}'가 비어 있음")
    return text


def read_number(value, field: str, low: float, high: float, integer: bool = False) -> int | float:
    """수 칸. 참/거짓, NaN·무한대, 범위 밖 값은 오류."""
    kind = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, kind):
        need = "정수" if integer else "수"
        raise CoursePlanError(f"'{field}'는 {need}여야 함 (받은 값: {value!r})")
    # 범위를 먼저 본다: 아주 큰 정수(10**400)는 math.isfinite에서 OverflowError가 난다
    if not low <= value <= high or not math.isfinite(value):
        shown = repr(value) if len(repr(value)) <= 20 else f"{repr(value)[:20]}…"
        raise CoursePlanError(f"'{field}'는 {low:g}~{high:g} 사이여야 함 (받은 값: {shown})")
    return int(value) if float(value).is_integer() else value


def read_object(value, field: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CoursePlanError(f"'{field}'는 {{...}} 객체여야 함 (받은 형식: {type(value).__name__})")
    return value


def read_list(value, field: str, limit: int, objects: bool = False) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CoursePlanError(f"'{field}'는 [...] 목록이어야 함 (받은 형식: {type(value).__name__})")
    if len(value) > limit:
        raise CoursePlanError(f"'{field}'가 너무 많음 ({len(value)}개, {limit}개까지)")
    if objects and not all(isinstance(item, dict) for item in value):
        raise CoursePlanError(f"'{field}'는 {{...}} 객체들의 목록이어야 함")
    return value


def read_flag(value, field: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise CoursePlanError(f"'{field}'는 true 또는 false여야 함 (받은 값: {value!r})")
    return value


def read_lines(value, field: str, rule_default: bool = False) -> list[dict]:
    """문장 목록: 글 또는 {"text": ..., "rule": true}. rule이 참이면 형광펜과 메모로 표시한다.
    rule을 적지 않은 문장은 rule_default를 따른다 (결시생 처리처럼 거의 모두 학교 규정인 칸은 참)."""
    lines = []
    for number, item in enumerate(read_list(value, field, MAX_LIST), 1):
        where = f"{field}의 {number}번째"
        spec = item if isinstance(item, dict) else {"text": item}
        rule = spec.get("rule")
        lines.append({"text": read_text(spec.get("text"), where, required=True),
                      "rule": rule_default if rule is None else read_flag(rule, f"{where} rule")})
    return lines


def read_codes(value, field: str) -> list[str]:
    """성취기준 칸: 글 하나 또는 글의 목록 → 줄 목록 ("[코드]", "[코드]~[코드]")."""
    if isinstance(value, list):
        read_list(value, field, MAX_LIST)
        return [line for n, item in enumerate(value, 1) if (line := read_text(item, f"{field}의 {n}번째"))]
    text = read_text(value, field)
    return [text] if text else []


def read_quotes(value, field: str) -> list[dict]:
    """코드와 원문: [{"code": "[..]", "text": "..."}] 또는 "[..] 원문" 글의 목록."""
    quotes = []
    for number, item in enumerate(read_list(value, field, MAX_LIST), 1):
        where = f"{field}의 {number}번째"
        spec = item if isinstance(item, dict) else {"code": item}
        quotes.append({"code": read_text(spec.get("code"), f"{where} code", required=True),
                       "text": read_text(spec.get("text"), f"{where} text")})
    return quotes


# ---------------------------------------------------------------- info, 학사일정, 진도

def _course_type(info: dict, level: str) -> str:
    kind = read_text(info.get("course_type"), "info.course_type") or DEFAULT_TYPE.get(level, "")
    if kind not in COURSE_TYPES[level]:
        allowed = ", ".join(COURSE_TYPES[level])
        raise CoursePlanError(f"'info.course_type'은 {LEVEL_NAMES[level]}에서 {allowed} 가운데 하나여야 함"
                              f" (받은 값: {kind or '없음'})")
    return kind


def _teachers(value) -> list[str]:
    names = read_list(value, "info.teachers", MAX_TEACHERS)
    return [name for n, item in enumerate(names, 1) if (name := read_text(item, f"info.teachers의 {n}번째", limit=40))]


def read_info(spec: dict) -> dict:
    info = read_object(spec.get("info"), "info")
    level = read_text(info.get("level"), "info.level", required=True)
    if level not in LEVELS:
        raise CoursePlanError(f"'info.level'은 고, 중, 초 가운데 하나여야 함 (받은 값: {level})")
    credits = info.get("credits")
    if level == "초" and credits is not None:
        raise CoursePlanError("초등 계획서에는 학점이 없음: 'info.credits'를 빼 주세요")
    if level == "고" and credits is None:
        raise CoursePlanError("고등학교 계획서에는 'info.credits'(학점)가 있어야 함")
    return {
        "year": read_number(info.get("year"), "info.year", 2000, 2100, integer=True),
        "semester": read_number(info.get("semester"), "info.semester", 1, 2, integer=True),
        "level": level, "course_type": _course_type(info, level),
        "school": read_text(info.get("school"), "info.school", limit=60),
        "grade": read_number(info.get("grade"), "info.grade", 1, TOP_GRADE[level], integer=True),
        "subject": read_text(info.get("subject"), "info.subject", required=True, limit=40),
        "classes": read_text(info.get("classes"), "info.classes", limit=60),
        "credits": None if credits is None else read_number(credits, "info.credits", 1, 12, integer=True),
        "weekly_hours": read_number(info.get("weekly_hours"), "info.weekly_hours", 1, 35, integer=True),
        "teachers": _teachers(info.get("teachers")),
        "curriculum": read_text(info.get("curriculum"), "info.curriculum", limit=40),
    }


def read_calendar(spec: dict, info: dict) -> tuple[dict, list[dict]]:
    """학사일정 입력과 주별 줄(school_calendar.plan_weeks). 주당 시수는 info에서 넣는다."""
    calendar = read_object(spec.get("calendar"), "calendar")
    if not calendar:
        raise CoursePlanError("'calendar'(학사일정: start, end, no_class, events)가 있어야 함")
    given = calendar.get("weekly_hours")
    if given is not None and given != info["weekly_hours"]:
        raise CoursePlanError(f"'calendar.weekly_hours'({given!r})가 'info.weekly_hours'({info['weekly_hours']})와 다름: "
                              "주당 시수는 info에만 적어 주세요")
    estimated = read_flag(calendar.get("estimated"), "calendar.estimated")
    merged = {**{k: v for k, v in calendar.items() if k != "estimated"}, "weekly_hours": info["weekly_hours"],
              "estimated": estimated}
    try:
        return merged, plan_weeks(merged)
    except CalendarError as error:
        raise CoursePlanError(f"학사일정(calendar): {error}") from None


def week_label(value, field: str) -> str:
    """'1~2', '1 ~ 2주', 3 → '1~2', '3'."""
    text = read_text(value, field, required=True, limit=20)
    return text.replace("∼", "~").replace(" ", "").removesuffix("주")


MAX_EDUCATION = 100          # 학교 안내 교육 한 줄 글자 수 한도 ('[교육명(시간)]')


def _education(value, field: str) -> list[str]:
    """학교가 배정해 안내한 교육: 줄마다 '[교육명(시간)]' 하나 (줄바꿈·겹친 대괄호는 정리한다)."""
    lines = []
    for line in _text_lines(value, field):
        name = " ".join(line.split()).strip("[] ")
        if len(name) > MAX_EDUCATION:
            raise CoursePlanError(f"'{field}'의 교육 이름이 너무 김 ({len(name)}자, {MAX_EDUCATION}자까지)")
        if name:
            lines.append(f"[{name}]")
    return lines


def read_progress(spec: dict, weeks: list[dict]) -> list[dict]:
    labels = [week["week"] for week in weeks]
    rows = []
    for number, item in enumerate(read_list(spec.get("progress"), "progress", MAX_PROGRESS, objects=True), 1):
        where = f"progress의 {number}번째"
        label = week_label(item.get("weeks"), f"{where} weeks")
        if label not in labels:
            raise CoursePlanError(f"{where} weeks '{label}'가 학사일정의 줄 이름과 맞지 않음 "
                                  f"(쓸 수 있는 값: {', '.join(labels)})")
        rows.append({"weeks": label, "unit": read_text(item.get("unit"), f"{where} unit"),
                     "standards": read_codes(item.get("standards"), f"{where} standards"),
                     "methods": read_text(item.get("methods"), f"{where} methods"),
                     "focus": read_text(item.get("focus"), f"{where} focus"),
                     "education": _education(item.get("education"), f"{where} education")})
    return rows


def term_of(calendar: dict) -> tuple[date, date]:
    """학기 첫날과 끝날 (school_calendar와 같은 방법으로 읽는다)."""
    try:
        return term(calendar)
    except CalendarError as error:
        raise CoursePlanError(f"학사일정(calendar): {error}") from None


# ---------------------------------------------------------------- 평가 (중·고)

def _kind(item: dict, number: int) -> dict:
    where = f"evaluation.kinds의 {number}번째"
    kind = read_text(item.get("type"), f"{where} type", required=True)
    if kind not in KIND_TYPES:
        raise CoursePlanError(f"'{where} type'은 정기시험 또는 수행평가여야 함 (받은 값: {kind})")
    ratio = read_number(item.get("ratio"), f"{where} ratio", 0, 100)
    essay = item.get("essay_ratio")
    essay = 0 if essay is None else read_number(essay, f"{where} essay_ratio", 0, 100)
    if essay > ratio:
        raise CoursePlanError(f"'{where} essay_ratio'({essay})가 반영 비율 ratio({ratio})보다 큼")
    return {"name": read_text(item.get("name"), f"{where} name", required=True, limit=60), "type": kind,
            "method": read_text(item.get("method"), f"{where} method", limit=200),
            "max_score": read_number(item.get("max_score"), f"{where} max_score", 1, MAX_SCORE),
            "ratio": ratio, "essay_ratio": essay,
            "standards": read_codes(item.get("standards"), f"{where} standards"),
            "timing": read_text(item.get("timing"), f"{where} timing", limit=100)}


def _rules(value) -> dict:
    rules = read_object(value, "evaluation.rules")
    return {key: None if rules.get(key) is None else read_number(rules[key], f"evaluation.rules.{key}", 0, 100)
            for key in ("performance_min", "essay_min")}


def _levels(value, where: str) -> list[dict]:
    levels = read_list(value, f"{where} levels", MAX_LEVELS, objects=True)
    if not levels:
        raise CoursePlanError(f"'{where} levels'(채점 기준 수준)가 하나 이상 있어야 함")
    return [{"text": read_text(level.get("text"), f"{where} levels의 {n}번째 text", required=True),
             "score": read_number(level.get("score"), f"{where} levels의 {n}번째 score", 0, MAX_SCORE)}
            for n, level in enumerate(levels, 1)]


def _elements(value, where: str) -> list[dict]:
    elements = read_list(value, f"{where} elements", MAX_ELEMENTS, objects=True)
    if not elements:
        raise CoursePlanError(f"'{where} elements'(평가 요소)가 하나 이상 있어야 함")
    result = []
    for number, element in enumerate(elements, 1):
        place = f"{where} elements의 {number}번째"
        result.append({"name": read_text(element.get("name"), f"{place} name", required=True, limit=60),
                       "group": read_text(element.get("group"), f"{place} group", limit=60),
                       "points": read_number(element.get("points"), f"{place} points", 0, MAX_SCORE),
                       "levels": _levels(element.get("levels"), place)})
    return result


def _areas(value, where: str) -> list[dict]:
    areas = read_list(value, f"{where} areas", MAX_AREAS, objects=True)
    if not areas:
        raise CoursePlanError(f"'{where} areas'(평가 영역)가 하나 이상 있어야 함")
    return [{"area": read_text(area.get("area"), f"{where} areas의 {n}번째 area", required=True, limit=60),
             "points": read_number(area.get("points"), f"{where} areas의 {n}번째 points", 0, MAX_SCORE),
             "elements": _elements(area.get("elements"), f"{where} areas의 {n}번째")}
            for n, area in enumerate(areas, 1)]


def _base(value, where: str) -> list[dict]:
    """기본점수 줄. 학교 규정에 따라 정하는 값이라 rule을 따로 적지 않으면 형광펜과 메모로 표시한다."""
    rows = []
    for number, item in enumerate(read_list(value, f"{where} base", MAX_LEVELS, objects=True), 1):
        place = f"{where} base의 {number}번째"
        rule = item.get("rule")
        rows.append({"text": read_text(item.get("text"), f"{place} text", required=True),
                     "score": read_text(item.get("score"), f"{place} score", limit=40),
                     "rule": True if rule is None else read_flag(rule, f"{place} rule")})
    return rows


def _methods(value, where: str) -> list[str]:
    if isinstance(value, str):
        value = value.replace("，", ",").split(",")
    return [m for n, item in enumerate(read_list(value, where, 20), 1) if (m := read_text(item, f"{where}의 {n}번째"))]


def _task(item: dict, number: int) -> dict:
    where = f"evaluation.tasks의 {number}번째"
    notes = read_list(item.get("notes"), f"{where} notes", MAX_LIST)
    return {"name": read_text(item.get("name"), f"{where} name", required=True, limit=60),
            "standards": read_quotes(item.get("standards"), f"{where} standards"),
            "methods": _methods(item.get("methods"), f"{where} methods"),
            "timing": read_text(item.get("timing"), f"{where} timing", limit=100),
            "areas": _areas(item.get("areas"), where), "base": _base(item.get("base"), where),
            "notes": [note for n, raw in enumerate(notes, 1) if (note := read_text(raw, f"{where} notes의 {n}번째"))]}


def _text_lines(value, field: str) -> list[str]:
    """글 하나 또는 글 목록 → 줄 목록 (빈 줄은 뺀다)."""
    items = value if isinstance(value, list) else [value]
    read_list(items, field, MAX_LIST)
    return [line for n, item in enumerate(items, 1) if (line := read_text(item, f"{field}의 {n}번째"))]


def _achievement_levels(value) -> dict | None:
    """Ⅺ 성취기준 및 성취수준: units(단원별 성취기준과 수준 진술), semester(학기단위), minimum(최소 성취수준)."""
    spec = read_object(value, "evaluation.achievement_levels")
    if not spec:
        return None
    where = "evaluation.achievement_levels"
    units = []
    for n, unit in enumerate(read_list(spec.get("units"), f"{where}.units", MAX_AREAS, objects=True), 1):
        place = f"{where}.units의 {n}번째"
        standards = read_list(unit.get("standards"), f"{place} standards", MAX_ELEMENTS, objects=True)
        if not standards:
            raise CoursePlanError(f"'{place} standards'(성취기준과 수준 진술)가 하나 이상 있어야 함")
        units.append({"name": read_text(unit.get("name"), f"{place} name", required=True, limit=60),
                      "standards": [{"code": read_text(item.get("code"), f"{place} standards의 {m}번째 code",
                                                       required=True, limit=40),
                                     "text": read_text(item.get("text"), f"{place} standards의 {m}번째 text"),
                                     "levels": _level_texts(item.get("levels"),
                                                            f"{place} standards의 {m}번째 levels")}
                                    for m, item in enumerate(standards, 1)]})
    unknown = sorted(set(spec) - {"units", "semester", "minimum"})
    if unknown:
        raise CoursePlanError(f"'{where}'에 모르는 칸이 있음: {', '.join(unknown)} (units, semester, minimum만 씀)")
    semester = read_object(spec.get("semester"), f"{where}.semester")
    if len(semester) > SCALE_SIZES[1]:
        raise CoursePlanError(f"'{where}.semester'의 수준이 너무 많음 ({len(semester)}개, {SCALE_SIZES[1]}개까지)")
    names = [read_text(key, f"{where}.semester의 수준 이름", required=True, limit=10) for key in semester]
    if len(set(names)) != len(names):
        raise CoursePlanError(f"'{where}.semester'의 수준 이름이 겹침: {', '.join(names)}")
    return {"units": units,
            "semester": {name: _text_lines(lines, f"{where}.semester.{name}")
                         for name, lines in zip(names, semester.values())},
            "minimum": _text_lines(spec.get("minimum") or [], f"{where}.minimum")}


# ---------------------------------------------------------------- 평가 (초등)

def _scale(value) -> list[str]:
    scale = read_list(value, "evaluation.scale", SCALE_SIZES[1] + 1)
    names = [read_text(name, f"evaluation.scale의 {n}번째", required=True, limit=10) for n, name in enumerate(scale, 1)]
    if not SCALE_SIZES[0] <= len(names) <= SCALE_SIZES[1] or len(set(names)) != len(names):
        raise CoursePlanError("'evaluation.scale'(평가 단계)은 서로 다른 단계 이름 2~5개여야 함 "
                              '(예: ["잘함", "보통", "노력요함"])')
    return names


def _level_texts(value, field: str) -> dict[str, str]:
    levels = read_object(value, field)
    if len(levels) > SCALE_SIZES[1]:
        raise CoursePlanError(f"'{field}'의 단계가 너무 많음 ({len(levels)}개, {SCALE_SIZES[1]}개까지)")
    names = [read_text(key, f"{field}의 단계 이름", required=True, limit=10) for key in levels]
    if len(set(names)) != len(names):
        raise CoursePlanError(f"'{field}'의 단계 이름이 겹침: {', '.join(names)}")
    return {name: read_text(text, f"{field}.{name}") for name, text in zip(names, levels.values())}


def _item(item: dict, number: int) -> dict:
    where = f"evaluation.items의 {number}번째"
    return {"timing": read_text(item.get("timing"), f"{where} timing", limit=100),
            "standards": read_quotes(item.get("standards"), f"{where} standards"),
            "unit": read_text(item.get("unit"), f"{where} unit", limit=200),
            "area": read_text(item.get("area"), f"{where} area", limit=60),
            "element": read_text(item.get("element"), f"{where} element"),
            "method": read_text(item.get("method"), f"{where} method"),
            "levels": _level_texts(item.get("levels"), f"{where} levels"),
            "criteria": _level_texts(item.get("criteria"), f"{where} criteria")}


def _refuse(evaluation: dict, keys: tuple[str, ...], message: str) -> None:
    found = [key for key in keys if evaluation.get(key) not in (None, [], {})]
    if found:
        raise CoursePlanError(f"{message}: evaluation.{', evaluation.'.join(found)}를 빼 주세요")


def read_evaluation(spec: dict, level: str) -> dict:
    evaluation = read_object(spec.get("evaluation"), "evaluation")
    lines = {key: read_lines(evaluation.get(key), f"evaluation.{key}", key in RULE_DEFAULT) for key in TEXT_LISTS}
    if level == "초":
        _refuse(evaluation, SECONDARY_ONLY, "초등 계획서에는 정기시험·반영 비율·점수 배점이 없음")
        items = read_list(evaluation.get("items"), "evaluation.items", MAX_ITEMS, objects=True)
        return {**lines, "scale": _scale(evaluation.get("scale")),
                "items": [_item(item, n) for n, item in enumerate(items, 1)]}
    _refuse(evaluation, ELEMENTARY_ONLY, "평가 단계(scale)와 성취기준별 평가(items)는 초등 계획서 칸임")
    kinds = read_list(evaluation.get("kinds"), "evaluation.kinds", MAX_KINDS, objects=True)
    tasks = read_list(evaluation.get("tasks"), "evaluation.tasks", MAX_TASKS, objects=True)
    return {**lines, "kinds": [_kind(item, n) for n, item in enumerate(kinds, 1)],
            "rules": _rules(evaluation.get("rules")), "tasks": [_task(item, n) for n, item in enumerate(tasks, 1)],
            "achievement_levels": _achievement_levels(evaluation.get("achievement_levels"))}


def read_plan(spec) -> dict:
    """입력 전체를 읽어 정리한 새 dict: info, calendar, weeks, progress, evaluation."""
    if not isinstance(spec, dict):
        raise CoursePlanError("입력은 {...} JSON 객체여야 함")
    for key in ("info", "calendar", "progress", "evaluation"):
        if key not in spec:
            raise CoursePlanError(f"'{key}'가 없음 (info, calendar, progress, evaluation은 꼭 있어야 함)")
    info = read_info(spec)
    calendar, weeks = read_calendar(spec, info)
    return {"info": info, "calendar": calendar, "weeks": weeks, "progress": read_progress(spec, weeks),
            "evaluation": read_evaluation(spec, info["level"])}
