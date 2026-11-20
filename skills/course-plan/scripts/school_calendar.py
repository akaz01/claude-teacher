"""학사일정에서 주별 진도표의 기간·공제일수·예정 시간·누계를 센다.

입력(dict, JSON 그대로):
    start, end      개학일(첫 수업일)과 마지막 수업일, "YYYY-MM-DD"
    weekly_hours    이 과목의 주당 수업 시수 (1~35)
    no_class        수업이 없는 평일: [{"date": "2026-05-05", "label": "어린이날"},
                                        {"from": "2026-04-27", "to": "2026-04-30", "label": "1회 정기시험"}]
    events          비고 칸에만 적을 일: [{"date": "2026-03-03", "label": "개학식"}] (수업일은 줄지 않는다)
    group           진도표 한 줄에 묶을 주 수 (1 또는 2, 기본 1)

세는 법: 주는 월~금. 개학일이 든 주가 1주다. 수업이 없는 평일은 공제일이다.
예정 시간은 한 반 기준 "주당 시수 × 수업일 ÷ 5"를 누계 기준으로 반올림해 나눈다(주마다 반올림해도 누계가
틀어지지 않는다). 여러 반을 맡아도 반마다 요일이 달라 한 반 기준으로 세고, 요일은 쓰지 않는다(교사 지시).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

ISO = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})$")      # \d는 전각 숫자도 받으므로 [0-9]
MAX_DAYS = 200                 # 한 학기(약 5개월)를 넉넉히 넘는 길이
MAX_WEEKLY = 35                # 주당 수업 시수 한도
GROUPS = (1, 2)
MAX_ITEMS = 100                # no_class·events 개수 한도 (입력 검사의 MAX_LIST와 같음)
MAX_LABEL = 3000               # label 글자 수 한도 (입력 검사의 MAX_TEXT와 같음)

# 법정 공휴일 (평일만 뜻이 있다). certain=False는 공휴일 여부나 날짜를 학교 학사일정으로 확인할 것
HOLIDAYS: dict[date, tuple[str, bool]] = {
    date(2026, 1, 1): ("신정", True), date(2026, 2, 16): ("설 연휴", True), date(2026, 2, 17): ("설날", True),
    date(2026, 2, 18): ("설 연휴", True), date(2026, 3, 2): ("대체공휴일(삼일절)", True),
    date(2026, 5, 5): ("어린이날", True), date(2026, 5, 25): ("대체공휴일(부처님오신날)", True),
    date(2026, 6, 3): ("전국동시지방선거", True), date(2026, 7, 17): ("제헌절", False),
    date(2026, 8, 17): ("대체공휴일(광복절)", True), date(2026, 9, 24): ("추석 연휴", True),
    date(2026, 9, 25): ("추석", True), date(2026, 10, 5): ("대체공휴일(개천절)", True),
    date(2026, 10, 9): ("한글날", True), date(2026, 12, 25): ("성탄절", True),
    date(2027, 1, 1): ("신정", True), date(2027, 2, 8): ("설 연휴", False), date(2027, 2, 9): ("대체공휴일(설날)", False),
    date(2027, 3, 1): ("삼일절", True), date(2027, 5, 5): ("어린이날", True), date(2027, 5, 13): ("부처님오신날", False),
    date(2027, 8, 16): ("대체공휴일(광복절)", True), date(2027, 9, 14): ("추석 연휴", False),
    date(2027, 9, 15): ("추석", False), date(2027, 9, 16): ("추석 연휴", False),
    date(2027, 10, 4): ("대체공휴일(개천절)", True), date(2027, 10, 11): ("대체공휴일(한글날)", True),
    date(2027, 12, 27): ("대체공휴일(성탄절)", True),
}
HOLIDAY_YEARS = {day.year for day in HOLIDAYS}


class CalendarError(ValueError):
    """학사일정 입력이 형식에 맞지 않을 때."""


def _day(value, field: str) -> date:
    text = str(value or "").strip()
    match = ISO.match(text)
    try:
        if not match:
            raise ValueError
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        raise CalendarError(f"{field} '{text[:20]}'은 YYYY-MM-DD 꼴의 있는 날짜여야 함 (예: 2026-03-03)") from None


def short(day: date) -> str:
    """학교 문서식 짧은 날짜: 3.3."""
    return f"{day.month}.{day.day}."


def period_text(start: date, end: date) -> str:
    return short(start) if start == end else f"{short(start)}~{short(end)}"


def _label(value, field: str, default: str | None) -> str:
    """label은 글자만. 비어 있으면 default (None이면 오류)."""
    if value is not None and not isinstance(value, str):
        raise CalendarError(f"{field}은 글자여야 함 (받은 형식: {type(value).__name__})")
    text = (value or "").strip()
    if len(text) > MAX_LABEL:
        raise CalendarError(f"{field}이 너무 김 ({len(text)}자, {MAX_LABEL}자까지)")
    if not text and default is None:
        raise CalendarError(f"{field}이 비어 있음 (행사 이름을 적어 주세요)")
    return text or default


def _items(spec: dict, key: str) -> list:
    items = spec.get(key) or []
    if not isinstance(items, list):
        raise CalendarError(f"{key}는 [{{...}}, ...] 목록이어야 함")
    if len(items) > MAX_ITEMS:
        raise CalendarError(f"{key}가 너무 많음 ({len(items)}개, {MAX_ITEMS}개까지)")
    return items


def _span(item: dict, index: int) -> tuple[date, date, str]:
    if not isinstance(item, dict):
        raise CalendarError(f"no_class의 {index}번째 값은 {{\"date\": ..., \"label\": ...}} 객체여야 함")
    label = _label(item.get("label"), f"no_class {index}번째 label", "수업 없음")
    if item.get("date"):
        day = _day(item["date"], f"no_class {index}번째 date")
        return day, day, label
    first, last = _day(item.get("from"), f"no_class {index}번째 from"), _day(item.get("to"), f"no_class {index}번째 to")
    if first > last:
        raise CalendarError(f"no_class {index}번째: from({first})이 to({last})보다 앞서야 함")
    return first, last, label


def _no_class(spec: dict) -> list[tuple[date, date, str]]:
    return [_span(item, number) for number, item in enumerate(_items(spec, "no_class"), 1)]


def _off_days(spans: list[tuple[date, date, str]], start: date, end: date) -> set[date]:
    """수업이 없는 날 집합. 기간을 학기 안으로 잘라 펼친다 (아주 긴 기간도 학기 길이만큼만)."""
    days: set[date] = set()
    for first, last, _ in spans:
        low, high = max(first, start), min(last, end)
        days |= {low + timedelta(days=i) for i in range((high - low).days + 1)} if low <= high else set()
    return days


def _weekly(spec: dict) -> int:
    hours = spec.get("weekly_hours")
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= MAX_WEEKLY:
        raise CalendarError(f"주당 수업 시수(weekly_hours)는 1~{MAX_WEEKLY} 사이의 정수여야 함 (받은 값: {hours!r})")
    return hours


def term(spec: dict) -> tuple[date, date]:
    """학기 첫날과 끝날 (검사한 값)."""
    start, end = _day(spec.get("start"), "개학일(start)"), _day(spec.get("end"), "마지막 수업일(end)")
    if start > end:
        raise CalendarError(f"개학일({start})이 마지막 수업일({end})보다 앞서야 함")
    if (end - start).days > MAX_DAYS:
        raise CalendarError(f"학기가 너무 김: {start}~{end} (한 학기는 {MAX_DAYS}일까지)")
    return start, end


def _group(spec: dict) -> int:
    group = spec.get("group", 1)
    if isinstance(group, bool) or not isinstance(group, int) or group not in GROUPS:
        raise CalendarError(f"group은 정수 1 또는 2여야 함 (받은 값: {group!r})")
    return group


def _events(spec: dict) -> list[tuple[date, str]]:
    events = []
    for number, item in enumerate(_items(spec, "events"), 1):
        if not isinstance(item, dict):
            raise CalendarError(f"events의 {number}번째 값은 {{\"date\": ..., \"label\": ...}} 객체여야 함")
        events.append((_day(item.get("date"), f"events {number}번째 date"),
                       _label(item.get("label"), f"events {number}번째 label", None)))
    return events


def _notes(first: date, last: date, spans: list[tuple[date, date, str]], events: list[tuple[date, str]]) -> list[str]:
    """비고 칸 글: 줄의 기간 안에 걸친 수업 없는 날(기간은 한 줄로)과 행사."""
    notes = [f"{period_text(max(a, first), min(b, last))} {label}" for a, b, label in spans if a <= last and b >= first]
    notes += [f"{short(day)} {label}" for day, label in events if first <= day <= last]
    return notes


def _single_weeks(spec: dict) -> list[dict]:
    start, end = term(spec)
    weekly = _weekly(spec)
    off = _off_days(_no_class(spec), start, end)
    weeks, monday, cum_days, cum_hours = [], start - timedelta(days=start.weekday()), 0, 0
    while monday <= end:
        days = [d for d in (monday + timedelta(days=i) for i in range(5)) if start <= d <= end]
        monday += timedelta(days=7)
        if not days:
            continue
        class_days = sum(d not in off for d in days)
        cum_days += class_days
        total = (2 * weekly * cum_days + 5) // 10           # 주당 시수 × 누계 수업일 ÷ 5, 반올림
        weeks.append({"week": str(len(weeks) + 1), "start": days[0], "end": days[-1], "class_days": class_days,
                      "deducted": len(days) - class_days, "hours": total - cum_hours, "cumulative": total})
        cum_hours = total
    if not weeks:
        raise CalendarError(f"학기({start}~{end})에 평일이 하루도 없음: start와 end를 확인해 주세요")
    return weeks


def _merge(pair: list[dict]) -> dict:
    first, last = pair[0], pair[-1]
    label = first["week"] if len(pair) == 1 else f"{first['week']}~{last['week']}"
    return {"week": label, "start": first["start"], "end": last["end"],
            "class_days": sum(w["class_days"] for w in pair), "deducted": sum(w["deducted"] for w in pair),
            "hours": sum(w["hours"] for w in pair), "cumulative": last["cumulative"]}


def plan_weeks(spec: dict) -> list[dict]:
    """주(또는 2주) 한 줄씩: week, start, end, class_days, deducted, hours, cumulative, notes."""
    if not isinstance(spec, dict):
        raise CalendarError("학사일정 입력은 {...} 객체여야 함")
    group, weeks = _group(spec), _single_weeks(spec)
    spans, events = _no_class(spec), _events(spec)
    rows = [_merge(weeks[i:i + group]) for i in range(0, len(weeks), group)]
    return [{**row, "notes": _notes(row["start"], row["end"], spans, events)} for row in rows]


def holiday_warnings(spec: dict) -> list[str]:
    """학기 안의 평일 공휴일이 no_class에 없으면 알린다. 표에 없는 해는 그 사실을 알린다."""
    start, end = term(spec)
    off = _off_days(_no_class(spec), start, end)
    warnings = [f"{year}년 공휴일 표가 없음: 학사일정의 공휴일을 그대로 씀 (빠진 공휴일이 없는지 확인)"
                for year in sorted({start.year, end.year} - HOLIDAY_YEARS)]
    for day, (label, certain) in sorted(HOLIDAYS.items()):
        if start <= day <= end and day.weekday() < 5 and day not in off:
            sure = "" if certain else " (공휴일 여부·날짜를 학사일정으로 확인)"
            warnings.append(f"{short(day)} {label}: 학사일정의 수업이 없는 날에 없음{sure}")
    return warnings


def span_warnings(spec: dict) -> list[str]:
    """학기 밖에 있거나 평일이 하루도 없는 no_class 항목 (연도를 잘못 쓴 정기시험 등)."""
    start, end = term(spec)
    warnings = []
    for first, last, label in _no_class(spec):
        where = f"{first}" if first == last else f"{first}~{last}"
        if last < start or first > end:
            warnings.append(f"수업 없는 날 '{label}'({where})이 학기({start}~{end}) 밖에 있음: 날짜를 확인해 주세요")
        elif not any(day.weekday() < 5 for day in _off_days([(first, last, label)], start, end)):
            warnings.append(f"수업 없는 날 '{label}'({where})에 학기 안 평일이 없음: 날짜를 확인해 주세요")
    return warnings
