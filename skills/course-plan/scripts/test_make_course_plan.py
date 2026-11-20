"""교과진도평가계획 생성기 시험: 문서 차례, 진도표 계산, 규정 표시, 점검 경고, 초등 분기, 잘못된 입력, CLI."""
import copy
import html
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "shared" / "scripts"))
sys.path.insert(0, str(HERE))
from make_hwpx import validate_package  # noqa: E402

TEACHING_FORM = HERE / "testdata" / "course_plan_form_1.hwpx"   # 진도표에 수업 방법 칸이 있는 학교 양식 예 (배포하지 않음)
from make_course_plan import CoursePlanError, build, main  # noqa: E402
from make_course_plan_check import expand, plan_warnings  # noqa: E402
from make_course_plan_input import read_plan  # noqa: E402
from make_course_plan_elementary import items_tables  # noqa: E402
from make_course_plan_layout import wrap_wide  # noqa: E402
from make_course_plan_rubric import CHUNK_LIMIT, method_line, rubric_tables  # noqa: E402

REFERENCE = HERE.parent / "references" / "course-plan-input.md"
A, B, C, D = "[10통사1-01-01]", "[10통사1-01-02]", "[10통사1-02-01]", "[10통사1-04-01]"


def levels(*scores):
    return [{"text": f"{score}점 수준의 채점 기준", "score": score} for score in scores]


HIGH = {
    "info": {"year": 2026, "semester": 1, "level": "고", "school": "OO고등학교", "grade": 1, "subject": "통합사회1",
             "classes": "1반 ~ 10반", "credits": 4, "weekly_hours": 4, "teachers": ["OOO", "OOO"],
             "curriculum": "2022 개정", "course_type": "공통"},
    "calendar": {"start": "2026-03-02", "end": "2026-04-10", "group": 2,
                 "no_class": [{"date": "2026-03-02", "label": "대체공휴일(삼일절)"}],
                 "events": [{"date": "2026-03-03", "label": "개학식"}]},
    "progress": [
        {"weeks": "1~2", "unit": "Ⅰ-1. 다양한 관점", "standards": [A], "methods": "[강의식 수업]\n- 관점 살펴보기",
         "focus": "[형성평가] 퀴즈"},
        {"weeks": "1~2", "unit": "Ⅳ-1. 문화권", "standards": [D], "methods": "[강의식 수업]", "focus": ""},
        {"weeks": "3~4", "unit": "Ⅰ-2. 통합적 관점", "standards": [B], "methods": "[주제탐구활동]",
         "focus": "[수행평가] 탐구 보고서"},
        {"weeks": "5~6", "unit": "Ⅱ-1. 행복의 기준", "standards": [C], "methods": "[모둠협력수업]", "focus": ""},
    ],
    "evaluation": {
        "purpose": ["성취기준 도달 정도를 확인한다."], "direction": ["핵심 개념을 이해하고 적용하는 능력을 평가한다."],
        "policy": ["평가 계획은 학기 초에 공지한다.", {"text": "정기시험은 학기당 1회 실시한다.", "rule": True}],
        "kinds": [
            {"name": "1회 정기시험", "type": "정기시험", "method": "선택형, 서술형", "max_score": 100, "ratio": 60,
             "essay_ratio": 10, "standards": [f"{A}~{C}", D], "timing": "4월 1주"},
            {"name": "탐구 보고서", "type": "수행평가", "method": "서술형", "max_score": 10, "ratio": 40, "essay_ratio": 30,
             "standards": [B], "timing": "3월 3주"}],
        "rules": {"performance_min": 40, "essay_min": 30},
        "tasks": [{"name": "탐구 보고서", "standards": [{"code": B, "text": "통합적 관점 원문"}], "methods": ["프로젝트"],
                   "timing": "3월 3주",
                   "areas": [{"area": "보고서", "points": 10, "elements": [
                       {"name": "자료 선정", "points": 4, "levels": levels(4, 3, 2)},
                       {"group": "자료 분석", "name": "시간적 관점", "points": 3, "levels": levels(3, 2, 1)},
                       {"group": "자료 분석", "name": "공간적 관점", "points": 3, "levels": levels(3, 2, 1)}]}],
                   "base": [{"text": "수행과정 미참여(기본점수)", "score": "2(20%)"}],
                   "notes": ["AI는 교사가 허용한 범위 안에서만 씀"]}],
        "cautions": ["수업 시간 안에서만 평가한다."], "absence": [{"text": "미인정 결시는 최하점의 차하점을 준다.", "rule": True}],
        "use": ["피드백에 활용한다."], "remote": ["정기시험은 등교하여 실시한다."]},
}

ELEMENTARY = {
    "info": {"year": 2026, "semester": 1, "level": "초", "grade": 5, "subject": "국어", "classes": "1반 ~ 4반",
             "weekly_hours": 6, "teachers": ["OOO"]},
    "calendar": {"start": "2026-03-03", "end": "2026-04-10"},
    "progress": [{"weeks": str(n), "unit": "2. 글의 구조", "standards": ["[6국02-01]"], "methods": "[직접 교수 학습]"}
                 for n in range(1, 7)],
    "evaluation": {
        "scale": ["잘함", "보통", "노력요함"],
        "purpose": ["도달 정도를 확인한다."], "direction": ["과정 중심 평가를 한다."], "policy": ["학기 초에 공개한다."],
        "items": [{"timing": "4월 1주", "standards": [{"code": "[6국02-01]", "text": "원문"}], "unit": "2. 글의 구조",
                   "area": "읽기", "element": "글의 구조에 맞게 요약하기", "method": "[논술형] 요약하기",
                   "levels": {"잘함": "정확히 요약한다.", "보통": "요약한다.", "노력요함": "도움을 받아 찾는다."},
                   "criteria": {"잘함": "핵심 내용을 모두 씀", "보통": "일부 빠짐", "노력요함": "그대로 옮겨 씀"}}],
        "absence": ["결시자는 등교 후 다시 평가한다.", "전입생 등 학적변동자는 전 학교 결과를 반영한다."],
        "use": [{"text": "학기 말에 문장으로 통지한다.", "rule": True}],
        "cautions": ["AI 도구 사용 범위를 안내한다."]},
}


def section(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        return package.read("Contents/section0.xml").decode("utf-8")


MEMO_RE = re.compile(r"<hp:ctrl><hp:fieldBegin [^>]*type=\"MEMO\".*?</hp:fieldBegin></hp:ctrl>", re.S)
PEN_RE = re.compile(r"<hp:markpen(?:Begin [^>]*|End)/>")
PEN = 'markpenBegin color="#FFFF00"/>'


def clean(xml: str) -> str:
    """메모 글과 형광펜 표시를 뺀 XML (본문 글만 읽으려고)."""
    return PEN_RE.sub("", MEMO_RE.sub("", xml))


def texts(xml: str) -> str:
    xml = clean(xml)
    return html.unescape("".join(re.findall(r"<hp:t>([^<]*)</hp:t>", xml.replace("<hp:lineBreak/>", "\n"))))


def lines(xml: str) -> str:
    """가장 안쪽 문단마다 한 줄 (학교 양식은 칸 안 줄마다 문단이다)."""
    paragraphs = re.findall(r"<hp:p [^>]*>((?:(?!<hp:p ).)*?)</hp:p>", clean(xml), re.S)
    return "\n".join(texts(paragraph) for paragraph in paragraphs)


def make(tmp_path: Path, spec: dict, name: str = "out.hwpx", form: Path | None = None) -> tuple[str, list[str], str]:
    """(본문, 경고, XML). 중·고는 form(없으면 기본 양식)에 채워 문단마다 한 줄로, 초등은 보통 양식 글로."""
    out = tmp_path / name
    warnings = build(spec, out, form)
    assert not validate_package(out)
    xml = section(out)
    return (texts(xml) if spec["info"]["level"] == "초" else lines(xml)), warnings, xml


def changed(spec: dict, path: str, value) -> dict:
    """spec을 깊이 복사해 'evaluation.kinds.0.ratio' 자리에 value를 넣는다."""
    copied = copy.deepcopy(spec)
    *parents, last = path.split(".")
    target = copied
    for key in parents:
        target = target[int(key)] if isinstance(target, list) else target[key]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value
    return copied


# ---------------------------------------------------------------- 문서 차례

def test_high_school_document_has_all_ten_parts_in_order(tmp_path):
    body, _, _ = make(tmp_path, HIGH)
    titles = ["2026학년도 1학기 <통합사회1>", "교수학습 및 평가 운영계획", "◆ 대상 학년 : 1학년 (1반 ~ 10반)",
              "◆ 학점 : 4학점", "◆ 지도 교사 : OOO (인), OOO (인)", "Ⅰ\n 교수학습 운영계획", "Ⅱ\n 평가의 목적",
              "Ⅲ\n 평가의 방향과 방침", "1. 평가의 기본 방향", "2. 평가의 방침", "Ⅳ\n 평가의 종류와 방법",
              "Ⅴ\n 기준 성취율과 성취도", "Ⅵ\n 수행평가 세부기준", "Ⅶ\n 수행평가 시 유의 사항", "Ⅷ\n 결시생의 성적 처리",
              "Ⅸ\n 평가 결과의 활용 방안", "Ⅹ\n 원격수업 운영 시 평가 계획", "성취기준 및 성취수준"]
    order = [body.index(title) for title in titles]
    assert order == sorted(order)
    assert "변경하여 운영할 수 있음" in body and "최소 성취수준 보장지도" in body
    assert "가. 성취기준 도달 정도를 확인한다." in body and "나. 정기시험은 학기당 1회 실시한다." in body


def test_kinds_table_shows_groups_ratios_and_sums(tmp_path):
    body, _, _ = make(tmp_path, HIGH)
    for word in ("정기시험(60%)", "수행평가(40%)", "영역 만점", "반영 비율", "평가 시기", "100%",
                 "40%", "1\n학기", "100점", "10점", "[10통사1-01-01]\n~[10통사1-02-01]"):
        assert word in body


def test_rubric_table_groups_elements_and_lists_scale(tmp_path):
    body, _, xml = make(tmp_path, HIGH)
    assert "[자료 분석]\n시간적 관점\n(3점)" in body and "자료 선정\n(4점)" in body and "보고서\n(10점)" in body
    assert "10\n9\n8\n7\n6\n5\n4" in body                    # 평가 척도: 수준 점수를 골라 더한 합 10 ~ 4
    assert "■프로젝트" in body and "□서술·논술" in body and "‣ AI는" in body
    assert "1. 탐구 보고서" in body and "수학자" not in body and "방정식과 부등식" not in body   # 양식 원래 글이 남지 않음


def test_long_rubric_is_split_into_tables_that_each_keep_their_header():
    """영역·척도 칸이 모든 행을 합쳐 한글이 행 단위로 나누지 못한다: 표마다 통째로 옮기고 묶음 경계에서 나눈다."""
    long_text = "채점 기준을 길게 적은 문장입니다. " * 6
    elements = [{"group": f"묶음{n // 2}", "name": f"요소{n}", "points": 3,
                 "levels": [{"text": long_text, "score": s} for s in (3, 2, 1)]} for n in range(12)]
    task = read_plan(changed(HIGH, "evaluation.tasks.0.areas", [{"area": "보고서", "points": 36, "elements": elements}]))
    tables = rubric_tables(task["evaluation"]["tasks"][0])
    assert len(tables) > 1 and all(t["keep_together"] and t["header"] for t in tables)
    texts_of = [[c["text"] for row in t["rows"] for c in row] for t in tables]
    assert any(text.startswith("36\n") for text in texts_of[0])                      # 척도는 첫 표에만
    assert not any(text.startswith("36\n") for t in texts_of[1:] for text in t)
    assert all(not any("기본점수" in text for text in t) for t in texts_of[:-1])
    assert any("기본점수" in text for text in texts_of[-1])
    groups = [{text for text in t if text.startswith("묶음")} for t in texts_of]
    assert all(not (a & b) for a, b in zip(groups, groups[1:]))                       # 묶음은 쪼개지지 않음
    assert CHUNK_LIMIT < 65000


def test_method_line_maps_common_names_and_others():
    line = method_line(["서술형", "발표", "보고서"])
    assert "■서술·논술" in line and "■구술·발표" in line and "■기타(보고서)" in line and "□프로젝트" in line


# ---------------------------------------------------------------- 진도표

def test_progress_rows_follow_the_school_calendar(tmp_path):
    body, _, xml = make(tmp_path, HIGH, form=TEACHING_FORM)          # 수업 방법 칸이 있는 학교 양식
    assert "1~2\n3.2.~3.13.\n(1)" in body                   # 3.2. 대체공휴일이 공제일
    assert "3.16.~3.27." in body and "3.30.~4.10." in body
    assert "3.2. 대체공휴일(삼일절)\n3.3. 개학식" in body        # 행사는 날짜 순서
    assert "Ⅰ-1. 다양한 관점\nⅣ-1. 문화권" in body               # 같은 주의 두 진도는 한 칸에 이어 쓴다
    assert "[강의식 수업]\n- 관점 살펴보기\n[형성평가] 퀴즈" in body
    plan = read_plan(HIGH)
    assert [w["hours"] for w in plan["weeks"]] == [7, 8, 8] and plan["weeks"][-1]["cumulative"] == 23
    assert "\n15\n" in body and "\n23\n" in body                # 예정 시간·누계 대각선 칸


def test_words_wider_than_the_cell_break_before_a_bracket_or_tilde():
    assert wrap_wide("3.2. 대체공휴일(삼일절)", 6000) == "3.2. 대체공휴일\n(삼일절)"
    assert wrap_wide(f"{A}~{C}", 9000) == f"{A}\n~{C}"
    assert wrap_wide(f"{A}~{C}", 7500) == f"{A}\n~\n{C}"           # '~[코드]'도 넓으면 '~'만 한 줄
    assert wrap_wide("짧은 글", 6000) == "짧은 글"


def test_week_without_progress_is_left_blank_with_a_warning(tmp_path):
    spec = copy.deepcopy(HIGH)
    spec["progress"] = [row for row in spec["progress"] if row["weeks"] != "5~6"]
    _, warnings, _ = make(tmp_path, spec)
    assert any("진도 내용이 없는 주: 5~6" in w for w in warnings)


def test_unknown_week_label_is_an_error():
    with pytest.raises(CoursePlanError, match="쓸 수 있는 값: 1~2, 3~4, 5~6"):
        read_plan(changed(HIGH, "progress.0.weeks", "1~3"))


def test_hours_are_counted_for_one_class_and_short_totals_are_reported(tmp_path):
    _, warnings, _ = make(tmp_path, HIGH)
    assert any("한 반 기준" in w and "누계 23시간" in w for w in warnings)
    assert any("기준 수업량 64시간보다 41시간 적음" in w for w in warnings)


def test_missing_public_holiday_is_reported(tmp_path):
    spec = changed(HIGH, "calendar.no_class", [])
    _, warnings, _ = make(tmp_path, spec)
    assert any(w.startswith("학사일정: 3.2.") for w in warnings)


# ---------------------------------------------------------------- 학교 규정 표시

def test_rule_sentences_get_a_highlight_and_a_memo_and_the_count_comes_first(tmp_path):
    body, warnings, xml = make(tmp_path, HIGH)
    assert "[학교 규정 확인]" not in body and "기본점수는 예시 값입니다" not in body   # 글자 표시·Ⅳ 안내 대신 형광펜·메모
    for text in ("정기시험은 학기당 1회 실시한다.", "수행과정 미참여(기본점수)"):     # 기본점수 줄은 기본으로 표시
        assert PEN + text in xml
    # 문장 1 + 결시 1 + 기본점수 1 + Ⅳ 반영 비율 1 + 양식의 Ⅷ 결시 처리 표 1 + 학교 안내 교육 자리 1
    assert xml.count('type="MEMO"') == 6 and xml.count("markpenBegin") == xml.count("markpenEnd")
    assert warnings[0].startswith("형광펜 표시") and "(메모 6개)" in warnings[0]
    assert "학교 학업성적관리규정에 맞게 바꿀 곳입니다" in xml and "[형광펜 지우기]" in xml and "[메모 지우기]" in xml


def test_base_rows_can_turn_off_the_mark():
    spec = changed(HIGH, "evaluation.tasks.0.base.0.rule", False)
    assert read_plan(spec)["evaluation"]["tasks"][0]["base"][0]["rule"] is False


# ---------------------------------------------------------------- 점검

def test_clean_input_has_no_alignment_or_score_warnings():
    warnings = plan_warnings(read_plan(HIGH))
    assert not [w for w in warnings if "성취기준" in w or "비율" in w or "배점" in w or "점수" in w]


def test_ranges_are_expanded_with_known_codes():
    known = {"10통사1-01-01", "10통사1-01-02", "10통사1-02-01"}
    assert expand([f"{A}~{C}"], known) == ["10통사1-01-01", "10통사1-01-02", "10통사1-02-01"]
    assert expand(["[9역08-01]", "~", "[9역08-03]"], set()) == ["9역08-01", "9역08-02", "9역08-03"]


def test_standards_taught_but_not_assessed_and_the_reverse():
    spec = changed(HIGH, "evaluation.kinds.0.standards", [A, "[10통사1-05-01]"])
    warnings = plan_warnings(read_plan(spec))
    assert any("평가 계획에 없는 성취기준 2개: [10통사1-02-01], [10통사1-04-01]" in w for w in warnings)
    assert any("진도표에 없는 성취기준 1개: [10통사1-05-01]" in w for w in warnings)


@pytest.mark.parametrize("path, value, message", [
    ("evaluation.kinds.0.ratio", 50, "반영 비율 합이 90%"),
    ("evaluation.rules.performance_min", 50, "수행평가 비율 40%가 하한 50%보다 낮음"),
    ("evaluation.kinds.1.essay_ratio", 10, "서술형 비율 합 20%가 하한 30%보다 낮음"),
    ("evaluation.rules", None, "비율 하한을 점검하지 않음"),
])
def test_ratio_checks(path, value, message):
    assert any(message in w for w in plan_warnings(read_plan(changed(HIGH, path, value))))


@pytest.mark.parametrize("path, value, message", [
    ("evaluation.tasks.0.areas.0.elements.0.points", 5, "요소 배점 합 11이 영역 배점 10과 다름"),
    ("evaluation.tasks.0.areas.0.points", 12, "영역 배점 합 12이 Ⅳ 표의 영역 만점 10과 다름"),
    ("evaluation.tasks.0.areas.0.elements.0.levels", levels(4, 4, 2), "줄어들지 않음 (4, 4, 2)"),
    ("evaluation.tasks.0.areas.0.elements.0.levels", levels(3, 2, 1), "가장 높은 수준 점수 3가 요소 배점 4과 다름"),
    ("evaluation.tasks.0.base.0.score", "2(30%)", "기본점수 '2(30%)': 만점 10점의 20%임"),
    ("evaluation.tasks.0.notes", ["수업 시간에만 씀"], "AI 활용 안내가 없음"),
])
def test_task_score_checks(path, value, message):
    assert any(message in w for w in plan_warnings(read_plan(changed(HIGH, path, value))))


def test_task_names_and_count_must_match_the_kinds_table():
    warnings = plan_warnings(read_plan(changed(HIGH, "evaluation.tasks.0.name", "보고서")))
    assert any("'탐구 보고서'에 맞는 세부기준(tasks)이 없음" in w for w in warnings)
    assert any("'보고서'가 Ⅳ 표의 수행평가 영역 이름과 맞지 않음" in w for w in warnings)
    warnings = plan_warnings(read_plan(changed(HIGH, "evaluation.tasks", [])))
    assert any("과제 0개와 Ⅳ 표의 수행평가 영역 1개가 다름" in w for w in warnings)


def test_timing_outside_the_semester_is_reported():
    warnings = plan_warnings(read_plan(changed(HIGH, "evaluation.kinds.0.timing", "9월 2주")))
    assert any("'1회 정기시험'의 평가 시기 '9월 2주'가 학기(3~4월) 밖" in w for w in warnings)


@pytest.mark.parametrize("course_type, shown, hidden", [
    ("선택", "60% 미만", "보장지도"), ("체육·예술", "60% 이상~80% 미만", "40% 이상~60% 미만"), ("교양", "P", "90% 이상"),
])
def test_achievement_table_follows_the_course_type(tmp_path, course_type, shown, hidden):
    body, _, _ = make(tmp_path, changed(HIGH, "info.course_type", course_type))
    part = body[body.index("기준 성취율과 성취도"):body.index("수행평가 세부기준")]
    assert shown in part and hidden not in part


def test_middle_school_shows_weekly_hours_and_free_semester_rejects_exams(tmp_path):
    spec = changed(changed(HIGH, "info.level", "중"), "info.credits", None)
    spec = changed(spec, "info.course_type", "자유학기")
    body, warnings, _ = make(tmp_path, spec)
    assert "◆ 주당 시수 : 4시간" in body and "학점" not in body.split("교수학습 운영계획")[0]
    assert any("자유학기에는 일제식 정기시험을 보지 않음" in w for w in warnings)


# ---------------------------------------------------------------- 초등

def test_elementary_document_has_its_own_parts_and_no_scores(tmp_path):
    body, warnings, xml = make(tmp_path, ELEMENTARY)
    titles = ["2026학년도 1학기 5학년 <국어>", "◆ 주당 시수 : 6시간", "Ⅰ. 교수학습 운영계획", "Ⅱ. 평가의 목적",
              "Ⅲ. 평가의 방향과 방침", "Ⅳ. 성취기준별 평가 계획", "Ⅴ. 평가 세부 기준", "Ⅵ. 결시자·학적변동자 처리",
              "Ⅶ. 평가 결과 활용과 통지", "Ⅷ. 평가 시 유의 사항"]
    order = [body.index(title) for title in titles]
    assert order == sorted(order)
    for word in ("반영 비율", "정기시험", "성취율", "영역 만점", "원격수업"):
        assert word not in body
    for word in ("2. 글의 구조\n(읽기)", "잘함", "노력요함", "정확히 요약한다.", "핵심 내용을 모두 씀"):
        assert word in body
    # 메모: use 1 + 결시 2(rule 기본값 참) + 단계 이름 첫 칸 1 + 학교 안내 교육 자리 1. 글자 표시와 ※ 안내 줄은 없음
    assert warnings[0].startswith("형광펜 표시") and "(메모 5개)" in warnings[0]
    assert "[학교 규정 확인]" not in body and "평가 단계의 수와 이름" not in body
    assert xml.count('type="MEMO"') == 5 and PEN + "잘함" in xml
    assert xml.count("markpenBegin") == xml.count("markpenEnd")
    assert not [w for w in warnings if "단계" in w or "필수" in w or "성취기준" in w]


@pytest.mark.parametrize("path, value, message", [
    ("evaluation.kinds", [{"name": "1회 정기시험"}], "evaluation.kinds"),
    ("evaluation.rules", {"performance_min": 40}, "evaluation.rules"),
    ("info.credits", 4, "학점이 없음"),
    ("info.course_type", "공통", "초등학교에서 초등"),
    ("evaluation.scale", ["잘함"], "2~5개"),
    ("evaluation.scale", ["잘함", "잘함"], "서로 다른"),
])
def test_elementary_rejects_secondary_input(path, value, message):
    with pytest.raises(CoursePlanError, match=message):
        read_plan(changed(ELEMENTARY, path, value))


def test_secondary_rejects_elementary_items():
    with pytest.raises(CoursePlanError, match="초등 계획서 칸"):
        read_plan(changed(HIGH, "evaluation.scale", ["잘함", "보통"]))


@pytest.mark.parametrize("path, value, message", [
    ("evaluation.items.0.levels", {"잘함": "가", "보통": "나"}, "성취수준(levels)의 단계"),
    ("evaluation.items.0.area", "", "평가 영역(area)이 비어"),
    ("evaluation.cautions", ["수업 중에 평가한다."], "AI 도구 활용 안내가 없음"),
    ("evaluation.absence", ["결시자는 다시 평가한다."], "학적변동"),
])
def test_elementary_checks(path, value, message):
    assert any(message in w for w in plan_warnings(read_plan(changed(ELEMENTARY, path, value))))


def test_elementary_tables_split_between_items_and_move_whole():
    item = ELEMENTARY["evaluation"]["items"][0]
    long_item = {**item, "method": "수업 중 관찰하여 기록하는 긴 설명 " * 8}
    plan = read_plan(changed(ELEMENTARY, "evaluation.items", [long_item] * 8))
    tables = items_tables(plan["evaluation"])
    assert len(tables) > 1 and all(t["keep_together"] and t["header"] for t in tables)
    assert sum(len(t["rows"]) for t in tables) == 8 * 3 and all(len(t["rows"]) % 3 == 0 for t in tables)


def test_elementary_missing_level_text_is_marked(tmp_path):
    body, _, _ = make(tmp_path, changed(ELEMENTARY, "evaluation.items.0.criteria", {"잘함": "다 씀"}))
    assert "[작성 필요]" in body


# ---------------------------------------------------------------- 잘못된 입력

@pytest.mark.parametrize("spec, message", [
    ([], "JSON 객체"),
    ({k: v for k, v in HIGH.items() if k != "calendar"}, "'calendar'가 없음"),
    (changed(HIGH, "progress", {"weeks": "1~2"}), "'progress'는 \\[...\\] 목록"),
    (changed(HIGH, "progress", ["1~2"]), "객체들의 목록"),
    (changed(HIGH, "info", None), "info.level"),
    (changed(HIGH, "info.level", "대"), "고, 중, 초"),
    (changed(HIGH, "info.course_type", "중학교"), "고등학교에서 공통, 선택"),
    (changed(HIGH, "info.credits", None), "info.credits"),
    (changed(HIGH, "info.year", 1.5), "info.year"),
    (changed(HIGH, "info.grade", 4), "1~3"),
    (changed(HIGH, "info.teachers", "OOO"), "info.teachers"),
    (changed(HIGH, "info.subject", "가" * 41), "너무 김"),
    (changed(HIGH, "evaluation.purpose", ["가" * 3001]), "너무 김"),
    (changed(HIGH, "evaluation.policy", [{"text": "가", "rule": "yes"}]), "true 또는 false"),
    (changed(HIGH, "evaluation.kinds.0.max_score", True), "max_score"),
    (changed(HIGH, "evaluation.kinds.0.max_score", float("nan")), "max_score"),
    (changed(HIGH, "evaluation.kinds.0.max_score", 10 ** 12), "1~1000"),
    (changed(HIGH, "evaluation.kinds.0.ratio", 120), "0~100"),
    (changed(HIGH, "evaluation.kinds.0.essay_ratio", 70), "보다 큼"),
    (changed(HIGH, "evaluation.kinds.0.type", "지필"), "정기시험 또는 수행평가"),
    (changed(HIGH, "evaluation.tasks.0.areas", []), "평가 영역"),
    (changed(HIGH, "evaluation.tasks.0.areas.0.elements.0.levels", []), "채점 기준 수준"),
    (changed(HIGH, "evaluation.tasks.0.areas.0.elements.0.levels", [{"text": "가"}] * 11), "너무 많음"),
    (changed(HIGH, "calendar.start", "2026-3-2"), "학사일정\\(calendar\\).*YYYY-MM-DD"),
    (changed(HIGH, "calendar.weekly_hours", 3), "info에만"),
    (changed(HIGH, "calendar", "2026-03-02"), "'calendar'는"),
])
def test_wrong_input_is_a_clear_error(spec, message):
    with pytest.raises(CoursePlanError, match=message):
        read_plan(spec)


def test_reading_does_not_change_the_input():
    spec = copy.deepcopy(HIGH)
    read_plan(spec)
    assert spec == HIGH


# ---------------------------------------------------------------- 참고 예시와 명령줄

def reference_examples() -> list[dict]:
    blocks = re.findall(r"```json\n(.*?)\n```", REFERENCE.read_text(encoding="utf-8"), re.S)
    return [json.loads(block) for block in blocks]


def test_reference_has_three_examples_for_each_level():
    assert [spec["info"]["level"] for spec in reference_examples()] == ["고", "중", "초"]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_reference_examples_build_without_alignment_warnings(tmp_path, index):
    body, warnings, _ = make(tmp_path, reference_examples()[index])
    noisy = [w for w in warnings if not (w.startswith("형광펜 표시") or "주당 시수 × 수업일 ÷ 5" in w
                                         or "수업 방법·주안점 칸이 없어" in w)]
    assert noisy == []
    assert "[작성 필요]" not in body


def test_cli_builds_and_prints_checks(tmp_path, capsys):
    source, target = tmp_path / "plan.json", tmp_path / "plan.hwpx"
    source.write_text(json.dumps(HIGH, ensure_ascii=False), encoding="utf-8")
    assert main([str(source), str(target)]) == 0
    out = capsys.readouterr().out
    assert "만들었습니다" in out and "점검: 형광펜 표시" in out and "(메모 6개)" in out and target.exists()


def test_cli_reports_bad_json_wrong_input_and_usage(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text("{", encoding="utf-8")
    assert main([str(source), str(tmp_path / "x.hwpx")]) == 1
    source.write_text(json.dumps(changed(HIGH, "info.level", "대"), ensure_ascii=False), encoding="utf-8")
    assert main([str(source), str(tmp_path / "x.hwpx")]) == 1
    assert main([]) == 2
    out = capsys.readouterr().out
    assert "JSON을 읽지 못함" in out and "고, 중, 초" in out and "사용법" in out
    assert main([str(tmp_path / "없음.json"), str(tmp_path / "x.hwpx")]) == 1


# ---------------------------------------------------------------- 리뷰 반영 (2026-11-21)

@pytest.mark.parametrize("path, value, message", [
    ("evaluation.kinds.0.max_score", 10 ** 400, "1~1000"),
    ("evaluation.rules.performance_min", 10 ** 400, "0~100"),
    ("calendar.start", "２０２６-０３-０２", "YYYY-MM-DD"),
    ("calendar.group", 2.0, "정수 1 또는 2"),
    ("calendar.events", [{"date": "2026-03-03", "label": {"a": 1}}], "글자여야"),
    ("calendar.events", [{"date": "2026-03-03", "label": "가" * 200000}], "너무 김"),
    ("calendar", {"start": "2026-03-07", "end": "2026-03-08"}, "평일이 하루도 없음"),
    ("calendar.estimated", "yes", "true 또는 false"),
    ("evaluation.purpose", [{"text": [["겹친 목록"]]}], "글이어야"),
    ("evaluation.purpose", [{"text": 10 ** 400}], "너무 큼"),
])
def test_review_inputs_are_clear_errors(path, value, message):
    with pytest.raises(CoursePlanError, match=message):
        read_plan(changed(HIGH, path, value))


def test_very_deep_nesting_is_reported_in_korean(tmp_path):
    source = tmp_path / "deep.json"
    spec = changed(HIGH, "evaluation.purpose", [{"text": json.loads("[" * 900 + '"a"' + "]" * 900)}])
    source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    failure, _ = __import__("make_course_plan")._run(source, tmp_path / "x.hwpx")
    assert failure.startswith("입력 오류") and "글이어야" in failure


def warnings_of(spec: dict) -> list[str]:
    return plan_warnings(read_plan(spec))


def test_timing_is_checked_once_and_a_different_task_timing_is_reported():
    spec = changed(changed(HIGH, "evaluation.kinds.1.timing", "9월 1주"), "evaluation.tasks.0.timing", "9월 1주")
    assert sum("'탐구 보고서'의 평가 시기" in w for w in warnings_of(spec)) == 1
    spec = changed(HIGH, "evaluation.tasks.0.timing", "3월 4주")
    assert any("Ⅳ 표('3월 3주')와 세부기준('3월 4주')에서 다름" in w for w in warnings_of(spec))


def test_weeks_without_class_days_are_not_reported_as_empty():
    spec = changed(HIGH, "calendar.no_class", [{"date": "2026-03-02", "label": "대체공휴일(삼일절)"},
                                               {"from": "2026-03-30", "to": "2026-04-10", "label": "정기시험"}])
    spec["progress"] = [row for row in spec["progress"] if row["weeks"] != "5~6"]
    assert not any("진도 내용이 없는 주" in w for w in warnings_of(spec))


def test_absence_lines_are_rules_by_default_and_missing_base_is_reported(tmp_path):
    spec = changed(changed(HIGH, "evaluation.absence", ["미인정 결시는 최하점의 차하점을 준다."]),
                   "evaluation.tasks.0.base", [])
    body, warnings, xml = make(tmp_path, spec)
    assert PEN + "미인정 결시는 최하점의 차하점을 준다." in xml
    assert any("기본점수 줄(base)이 없음" in w for w in warnings)
    spec = changed(HIGH, "evaluation.absence", [{"text": "인정점은 학기 말에 준다.", "rule": False}])
    assert read_plan(spec)["evaluation"]["absence"][0]["rule"] is False


def test_float_scores_add_up_without_false_warnings():
    elements = [{"name": "가", "points": 1.1, "levels": [{"text": "a", "score": 1.1}, {"text": "b", "score": 0.5}]},
                {"name": "나", "points": 2.2, "levels": [{"text": "a", "score": 2.2}, {"text": "b", "score": 1}]}]
    spec = changed(HIGH, "evaluation.tasks.0.areas", [{"area": "보고서", "points": 3.3, "elements": elements}])
    spec = changed(changed(spec, "evaluation.kinds.1.max_score", 3.3), "evaluation.tasks.0.base", [{"text": "기본", "score": "1"}])
    assert not [w for w in warnings_of(spec) if "다름" in w]


def test_bracket_text_that_is_not_a_code_is_ignored():
    spec = changed(HIGH, "evaluation.kinds.0.standards", [f"{A}~{C}", D, "[전 범위]"])
    assert not [w for w in warnings_of(spec) if "성취기준" in w]


def test_semester_across_the_new_year_is_named_in_order():
    spec = changed(changed(HIGH, "info.semester", 2), "calendar", {"start": "2026-12-28", "end": "2027-01-08"})
    spec["progress"] = []
    spec = changed(spec, "evaluation.kinds.0.timing", "3월")
    assert any("학기(12월~다음 해 1월) 밖" in w for w in warnings_of(spec))


def test_empty_kinds_give_one_warning_and_duplicate_names_are_reported():
    warnings = warnings_of(changed(HIGH, "evaluation.kinds", []))
    assert sum("Ⅳ" in w or "kinds" in w for w in warnings) == 1
    spec = copy.deepcopy(HIGH)
    kind = spec["evaluation"]["kinds"][1]
    twin = {**kind, "ratio": 20, "essay_ratio": 15}
    spec["evaluation"]["kinds"] = [spec["evaluation"]["kinds"][0], twin, twin]
    spec["evaluation"]["tasks"] = spec["evaluation"]["tasks"] * 2
    warnings = warnings_of(spec)
    assert any("Ⅳ 표의 평가 이름이 겹침: '탐구 보고서'" in w for w in warnings)
    assert any("세부기준 과제 이름이 겹침" in w for w in warnings)


def test_no_class_outside_the_term_is_reported():
    spec = changed(HIGH, "calendar.no_class", [{"date": "2026-03-02", "label": "대체공휴일(삼일절)"},
                                               {"from": "2025-03-23", "to": "2025-03-27", "label": "1회 정기시험"}])
    assert any(w.startswith("학사일정: 수업 없는 날 '1회 정기시험'") for w in warnings_of(spec))


def test_estimated_calendar_marks_period_hours_and_totals(tmp_path):
    body, warnings, xml = make(tmp_path, changed(HIGH, "calendar.estimated", True))
    assert "3.2.~3.13.\n(1)\n7/7" in body and "[확인 필요]" not in body
    assert PEN + "3.2.~3.13." in xml and PEN + "7/7" in xml and PEN + "(1)" in xml
    assert xml.count("학사일정에 맞게 확인할 곳") == 1                # 메모는 첫 칸에만
    assert "calendar.estimated" in warnings[1]                          # 형광펜 표시 줄 바로 다음
    assert "학사일정에 맞게" not in make(tmp_path, HIGH, "plain.hwpx")[2]


@pytest.mark.parametrize("path, value, message", [
    ("evaluation.policy", ["지필평가 60%, 수행평가 40%를 반영한다."], "'60%', '40%', '지필평가'"),
    ("evaluation.use", ["성취도 A~E로 통지한다."], "'성취도', 'A~E'"),
    ("evaluation.items.0.method", "[논술형] 10점 만점으로 채점", "'10점'"),
    ("evaluation.scale", ["A", "B", "C"], "성취도 등급(A~E)처럼"),
])
def test_elementary_score_words_and_grade_names_are_reported(path, value, message):
    spec = changed(ELEMENTARY, path, value)
    if path == "evaluation.scale":
        item = spec["evaluation"]["items"][0]
        item["levels"] = item["criteria"] = {"A": "가", "B": "나", "C": "다"}
    assert any(message in w for w in warnings_of(spec))


def test_elementary_example_words_are_not_flagged():
    from make_course_plan_check_elementary import leak_warnings
    plan = read_plan(reference_examples()[2])
    assert leak_warnings(plan["evaluation"]) == []


def test_first_and_second_graders_are_not_assessed_in_march():
    spec = changed(changed(ELEMENTARY, "info.grade", 1), "evaluation.items.0.timing", "3월 4주")
    assert any("1학년 3월 평가" in w for w in warnings_of(spec))
    assert not any("3월 평가" in w for w in warnings_of(changed(ELEMENTARY, "evaluation.items.0.timing", "3월 4주")))
