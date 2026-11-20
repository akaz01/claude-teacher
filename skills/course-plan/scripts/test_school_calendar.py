"""school_calendar.py 시험: 학사일정에서 주별 기간·공제일수·예정 시간·누계 세기."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from school_calendar import CalendarError, holiday_warnings, plan_weeks, span_warnings  # noqa: E402

SPRING = {"start": "2026-03-03", "end": "2026-07-17", "weekly_hours": 4,
          "no_class": [{"date": "2026-03-02", "label": "대체공휴일(삼일절)"},
                       {"date": "2026-05-05", "label": "어린이날"},
                       {"from": "2026-04-27", "to": "2026-04-30", "label": "1회 정기시험"}],
          "events": [{"date": "2026-03-03", "label": "개학식"}]}


def test_first_week_starts_on_the_opening_day():
    weeks = plan_weeks({**SPRING})
    first = weeks[0]
    assert (first["week"], first["start"], first["end"]) == ("1", date(2026, 3, 3), date(2026, 3, 6))
    assert first["class_days"] == 4 and first["deducted"] == 0       # 3월 2일은 개학 전이라 공제가 아니다


def test_holiday_on_a_weekday_is_deducted_with_its_label():
    week = next(w for w in plan_weeks({**SPRING}) if w["start"] <= date(2026, 5, 5) <= w["end"])
    assert week["deducted"] == 1 and "5.5. 어린이날" in week["notes"]


def test_range_of_no_class_days_is_deducted():
    week = next(w for w in plan_weeks({**SPRING}) if w["start"] <= date(2026, 4, 28) <= w["end"])
    assert week["deducted"] == 4 and week["class_days"] == 1 and week["hours"] == 1


def test_cumulative_hours_follow_weekly_hours_times_class_days():
    weeks = plan_weeks({**SPRING})
    class_days = sum(w["class_days"] for w in weeks)
    assert weeks[-1]["cumulative"] == round(4 * class_days / 5)
    assert all(w["cumulative"] == sum(x["hours"] for x in weeks[:i + 1]) for i, w in enumerate(weeks))


def test_full_week_gets_the_weekly_hours():
    week = next(w for w in plan_weeks({**SPRING}) if w["start"] == date(2026, 3, 9))
    assert week["class_days"] == 5 and week["hours"] == 4


def test_two_week_rows():
    rows = plan_weeks({**SPRING, "group": 2})
    assert rows[0]["week"] == "1~2" and rows[0]["start"] == date(2026, 3, 3) and rows[0]["end"] == date(2026, 3, 13)
    assert rows[-1]["cumulative"] == plan_weeks({**SPRING})[-1]["cumulative"]


def test_period_text_uses_school_date_style():
    from school_calendar import period_text
    assert period_text(date(2026, 3, 3), date(2026, 3, 13)) == "3.3.~3.13."


def test_events_are_listed_in_their_week():
    assert "3.3. 개학식" in plan_weeks({**SPRING})[0]["notes"]


@pytest.mark.parametrize("spec, message", [
    ({**SPRING, "start": "2026-07-20"}, "개학일"),
    ({**SPRING, "weekly_hours": 0}, "주당 수업 시수"),
    ({**SPRING, "weekly_hours": 40}, "주당 수업 시수"),
    ({**SPRING, "start": "2026-3-3"}, "YYYY-MM-DD"),
    ({**SPRING, "end": "2027-12-31"}, "너무 김"),
    ({**SPRING, "no_class": [{"date": "2026-02-30"}]}, "YYYY-MM-DD"),
    ({**SPRING, "no_class": [{"from": "2026-05-10", "to": "2026-05-01"}]}, "앞서야"),
    ({**SPRING, "group": 3}, "group"),
])
def test_wrong_input_is_a_clear_error(spec, message):
    with pytest.raises(CalendarError, match=message):
        plan_weeks(spec)


def test_missing_public_holiday_is_reported():
    spec = {**SPRING, "no_class": [n for n in SPRING["no_class"] if n["label"] != "어린이날"]}
    warnings = holiday_warnings(spec)
    assert any("5.5." in w and "어린이날" in w for w in warnings)
    assert not any("3.2." in w for w in warnings)           # 개학 전 공휴일은 알리지 않는다


def test_listed_holidays_raise_no_warning():
    assert not any("어린이날" in w for w in holiday_warnings({**SPRING}))


@pytest.mark.parametrize("spec, message", [
    ({**SPRING, "start": "2026-03-07", "end": "2026-03-08"}, "평일이 하루도 없음"),
    ({**SPRING, "group": 2.0}, "정수 1 또는 2"),
    ({**SPRING, "group": True}, "정수 1 또는 2"),
    ({**SPRING, "start": "２０２６-０３-０３"}, "YYYY-MM-DD"),
    ({**SPRING, "events": [{"date": "2026-03-03", "label": {"a": 1}}]}, "글자여야"),
    ({**SPRING, "events": [{"date": "2026-03-03"}]}, "비어 있음"),
    ({**SPRING, "events": [{"date": "2026-03-03", "label": "가" * 3001}]}, "너무 김"),
    ({**SPRING, "no_class": [{"date": "2026-05-05", "label": "어린이날"}] * 101}, "너무 많음"),
    ({**SPRING, "no_class": [{"date": "2026-05-05", "label": ["어린이날"]}]}, "글자여야"),
])
def test_more_wrong_input_is_a_clear_error(spec, message):
    with pytest.raises(CalendarError, match=message):
        plan_weeks(spec)


def test_very_long_no_class_span_is_clipped_to_the_term():
    spec = {**SPRING, "no_class": [{"from": "2000-01-01", "to": "2099-12-31", "label": "휴업"}]}
    weeks = plan_weeks(spec)
    assert weeks[-1]["cumulative"] == 0 and weeks[0]["notes"][0] == "3.3.~3.6. 휴업"


def test_no_class_outside_the_term_or_on_a_weekend_is_reported():
    spec = {**SPRING, "no_class": [{"from": "2025-04-27", "to": "2025-04-30", "label": "1회 정기시험"},
                                   {"date": "2026-03-07", "label": "토요 행사"}, {"date": "2026-05-05", "label": "어린이날"}]}
    warnings = span_warnings(spec)
    assert any("1회 정기시험" in w and "학기" in w and "밖" in w for w in warnings)
    assert any("토요 행사" in w and "평일이 없음" in w for w in warnings)
    assert not any("어린이날" in w for w in warnings)


def test_span_inside_a_two_week_row_is_written_once():
    spec = {"start": "2026-03-02", "end": "2026-04-30", "weekly_hours": 4, "group": 2,
            "no_class": [{"from": "2026-03-12", "to": "2026-03-18", "label": "시험"}]}
    assert plan_weeks(spec)[0]["notes"] == ["3.12.~3.13. 시험"] and plan_weeks(spec)[1]["notes"] == ["3.16.~3.18. 시험"]
    spec = {**spec, "no_class": [{"from": "2026-03-04", "to": "2026-03-11", "label": "시험"}]}
    assert plan_weeks(spec)[0]["notes"] == ["3.4.~3.11. 시험"]


def test_odd_number_of_weeks_leaves_a_single_last_row():
    rows = plan_weeks({**SPRING, "group": 2, "end": "2026-07-21"})
    assert rows[-1]["week"] == "21" and rows[-1]["start"] == date(2026, 7, 20)
    assert rows[-2]["week"] == "19~20"


def test_2027_holidays_are_checked():
    spec = {"start": "2027-03-02", "end": "2027-07-16", "weekly_hours": 3}
    warnings = holiday_warnings(spec)
    assert any("5.5. 어린이날" in w for w in warnings)
    assert any("5.13. 부처님오신날" in w and "확인" in w for w in warnings)

