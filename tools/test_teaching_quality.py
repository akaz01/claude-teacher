"""수업·평가 스킬 정비 시험: 사용자가 승인한 결정(학년도 판별, 문항 구성, PPT 첫 질문, 교사에게 보이는 말,
README, 개인별 세특)과 재평가에서 고친 문제(예시 불일치, 깨진 줄바꿈 표기, 단원명, 파일 수)가 되돌아가지 않게 한다.

승인된 교사 안내 문구는 문장 그대로, 내부 규칙은 한 줄에 든 핵심 낱말로 본다(skill_rules 참고).
"""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402
from skill_rules import (ALL_SKILLS, APPROVED, RECORD_SKILLS, ROOT, description, has_rule,  # noqa: E402
                         missing_rules, read, rule_line, section, skill)

OLD_LABEL = "가정한 내용"
NEW_LABEL = "기본값으로 정한 내용"
MIDDLE_SCIENCE = ROOT / "shared" / "curriculum" / "2022" / "middle" / "m001.md"


def teacher_documents() -> list[Path]:
    paths = [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("skills/*/references/*.md"),
             *ROOT.glob("shared/*.md"), *ROOT.glob("shared/checklists/*.md"),
             *ROOT.glob("shared/item-patterns/*.md"), ROOT / "shared" / "curriculum" / "README.md",
             ROOT / "README.md"]
    return sorted(paths)


class SchoolYearTest(unittest.TestCase):
    """결정 1: 학년도는 3월~다음 해 2월이고, 11~2월이면 이번 학년도인지 다음 학년도인지 한 번 묻는다."""

    def test_transition_guide_has_the_approved_rule(self):
        text = read("shared/curriculum-transition.md")
        self.assertIn(APPROVED["학년도 질문"], text)
        self.assertIn("이번 학년도(2026학년도) 자료인가요, 다음 학년도(2027학년도) 자료인가요?", text)
        self.assertEqual(missing_rules(text, {
            "학년도 범위": ("3월에 시작", "다음 해 2월"), "묻는 때": ("11~2월", "한 번 묻는다"),
            "기본 판단": ("11~12월", "이번 학년도", "1~2월", "다음 학년도"),
            "말했으면 묻지 않음": ("새 학년", "내년", "묻지 않는다")}), [])

    def test_old_today_rule_is_gone(self):
        for path in ("shared/curriculum-lookup.md", "shared/teacher-profile.md", "shared/curriculum-transition.md"):
            text = read(path)
            with self.subTest(path=path):
                for old in ("오늘 날짜로", "직전 학년도", "직전 연도"):
                    self.assertNotIn(old, text)
        self.assertIn(APPROVED["학년도 질문"], read("shared/teacher-profile.md"))
        self.assertTrue(has_rule(read("shared/curriculum-lookup.md"), "1~2월", "다음 학년도"))

    def test_table_reaches_every_grade_by_2027(self):
        rows = dict(re.findall(r"^\| \**(\d{4}(?: 이후)?)\** \| (.+?) \|", read("shared/curriculum-transition.md"), re.M))
        self.assertEqual(rows["2027 이후"], "전 학년")
        self.assertIn("중1", rows["2025"])
        self.assertIn("고1", rows["2025"])
        self.assertIn("중1~2, 고1~2", rows["2026"])


class ItemCompositionTest(unittest.TestCase):
    """결정 2: 정기시험은 먼저 묻고, 형성평가·단원평가 한 줄 요청은 기본 구성으로 초안부터 만든다."""

    COMPOSITION = re.compile(r"(\d+)문항 = 선택형 (\d+)문항\((\d)지선다\) \+ 서답형 (\d+)문항 \+ 서술형 (\d+)문항, ([^|]+?) \|")

    def test_rule_keeps_the_sentence_and_splits_by_use(self):
        self.assertEqual(missing_rules(skill("assessment-items"), {
            "반드시 묻기": ("문항 구성", "반드시", "묻는다"), "정기시험 먼저": ("**정기시험**", "만들기 전에"),
            "한 줄 요청": ("한 줄 요청", "형성평가"), "초안 먼저": ("초안을 먼저",),
            "밝히고 묻기": ("총 문항", "지선다", "배점", "바꿀 값")}), [])

    def test_default_compositions_add_up(self):
        table = section(skill("assessment-items"), "**형성평가·단원평가 기본 구성**", "\n\n- ")
        found = self.COMPOSITION.findall(table)
        self.assertEqual(len(found), 6)                      # 학교급 3 × 형성평가·단원평가
        for total, choice, _, short, essay, points in found:
            with self.subTest(total=total, points=points):
                self.assertEqual(int(total), int(choice) + int(short) + int(essay))
                each = re.match(r"문항당 (\d+)점\(총 100점\)", points)
                split = re.match(r"선택형 (\d+)점·서답형 (\d+)점·서술형 (\d+)점\(총 100점\)", points)
                self.assertTrue(each or split, points)
                if each:
                    self.assertEqual(int(total) * int(each[1]), 100)
                else:
                    self.assertEqual(int(choice) * int(split[1]) + int(short) * int(split[2])
                                     + int(essay) * int(split[3]), 100)


class SlideRequestTest(unittest.TestCase):
    """결정 3·9: PPT 첫 질문은 네 항목이고, 슬라이드 수 기본값은 12장 안팎이다. 4번은 학생용 사본 질문이다."""

    APPROVED_ITEMS = tuple(f"> {item}" for item in APPROVED["PPT 첫 질문"])

    def test_first_request_is_the_four_approved_items(self):
        request = section(skill("class-slides"), "> 수업 PPT를 만들기 위해 알려 주세요.", "\n\n")
        self.assertEqual(re.findall(r"^> \d\. .*$", request, re.M), list(self.APPROVED_ITEMS))
        self.assertNotIn("있으면 알려 주세요", request)
        self.assertEqual(skill("class-slides").count(self.APPROVED_ITEMS[0][2:]), 1)    # 같은 요청을 두 번 하지 않는다

    def test_template_and_textbook_are_not_asked_again(self):
        text = skill("class-slides")
        for old in ("쓰시는 PPT 템플릿(.pptx)과", "템플릿과 교과서를 한 번만 묻는다", "나머지 하나만 묻는다", "테마 질문",
                    "슬라이드 수, 테마"):
            self.assertNotIn(old, text)
        self.assertTrue(has_rule(text, "1번 질문", "다시 묻지 않는다"))
        self.assertIn(APPROVED["질문 없이"], text)

    def test_other_values_are_defaults_with_the_new_label(self):
        part = section(skill("class-slides"), "## 1. 요청하기", "\n## 2.")
        for row in ("| 함께 쓰는 학습지 |", "| 학생이 답할 도구 | 손들기와 공책 |", "| 슬라이드 수 | 12장 안팎"):
            self.assertIn(row, part)
        self.assertIn(NEW_LABEL, part)

    def test_slide_count_default_is_twelve_everywhere(self):
        text = skill("class-slides")
        self.assertTrue(has_rule(text, "기본값", "12장 안팎"))
        self.assertEqual(set(re.findall(r"(\d+)장 안팎", text)), {"12"})
        for old in ("10~14장", "12~16장", "12~18장"):
            self.assertNotIn(old, text)


class TeacherWordingTest(unittest.TestCase):
    """결정 4: 교사에게 보이는 말을 바꾼다."""

    def test_old_label_is_gone_everywhere(self):
        tests = [path for path in ROOT.glob("tools/test_*.py") if path.name != Path(__file__).name]
        for path in [*teacher_documents(), *tests]:
            with self.subTest(path=path.name):
                self.assertNotIn(OLD_LABEL, path.read_text(encoding="utf-8"))

    def test_every_skill_uses_the_new_label(self):
        for name in ALL_SKILLS:
            with self.subTest(skill=name):
                self.assertIn(NEW_LABEL, skill(name))

    def test_rubric_shows_the_level_criterion_in_plain_words(self):
        text = skill("rubric")
        self.assertIn("\"수준을 가르는 기준: ○○\"", text)
        self.assertTrue(has_rule(text, "'축'", "교사에게 보이는 글", "쓰지 않는다"))
        table = section(text, "### 표 형식", "**표 아래 줄을 고정한다.**")
        self.assertIn("수준을 가르는 기준: ", table)
        self.assertNotIn("축", table)


class ReadmeTest(unittest.TestCase):
    """결정 5: README 승인 문구."""

    def test_approved_sentences(self):
        readme = read("README.md")
        self.assertIn("한글에서 파일 열기 → [파일] → [다른 이름으로 저장] → 파일 형식을 '한글 문서(*.hwpx)'로 고르기", readme)
        self.assertIn("테마는 묻지 않고 교과에 맞게 고릅니다. 원하시면 말씀해 주세요", readme)
        self.assertNotIn("테마 5종", readme)

    def test_record_call_row(self):
        row = next(line for line in read("README.md").splitlines() if line.startswith("| 학생부("))
        for word in ("학생부(세특·창체·행특 중 무엇인지 모를 때)", "`학생부: ...`", "먼저 여쭤봅니다"):
            self.assertIn(word, row)
        for name in RECORD_SKILLS:
            self.assertIn("\"학생부:\"", description(name), name)


class PersonalRecordTest(unittest.TestCase):
    """결정 6: 담임이 쓰는 개인별 세특은 없다. 담임은 창체·행특을 쓰고 교과세특은 교과교사로서 쓴다."""

    def test_no_personal_record_item_is_mentioned(self):
        for name in ("shared/school-levels.md", "shared/record-guide.md", "skills/subject-record/SKILL.md"):
            with self.subTest(file=name):
                self.assertNotIn("개인별 세특", read(name))
        self.assertTrue(has_rule(read("shared/school-levels.md"), "담임교사", "창체·행특", "교과교사"))

    def test_lowest_rubric_level_sentence_is_not_carried_into_the_record(self):
        self.assertTrue(has_rule(skill("subject-record"), "가장 낮은 단계", "옮기지 않고", "한 일만"))


class RubricExampleTest(unittest.TestCase):
    """재평가: 1절 첫 요청 번호, 대체 점수형 예시의 최저 단계, 변인 예시, JSON 예시의 축."""

    def test_form_request_drops_item_three(self):
        text = skill("rubric")
        self.assertNotIn("6번은 뺀다", text)
        self.assertTrue(has_rule(text, "3번", "양식 파일", "뺀다"))
        request = section(text, "> 수행평가 자료를 만들기 위해", "나머지는 제가")
        self.assertIn("> 3. 학교 채점기준표·평가계획 양식 파일", request)

    def test_table_matches_the_design_example(self):
        text = skill("rubric")
        steps = re.search(r"평가 요소마다 4단계 \(([\d, ]+)점\), 가장 낮은 단계의 합 (\d+)점", text)
        base = int(re.search(r"- 기본점수: (\d+)점 \(채점할 내용이 없을 때 대신 주는 점수\)", text)[1])
        scores = [int(score) for score in steps[1].split(", ")]
        self.assertLess(base, int(steps[2]))                  # 대체 점수형
        table = section(text, "| 평가 영역 (만점) |", "\n\n")
        rows = re.findall(r"^\|.*\| (.+?) \| (\d+) \|$", table, re.M)
        self.assertEqual([int(score) for _, score in rows], scores)
        self.assertNotIn("참여함", rows[-1][0])                # 대체 점수형은 실제로 한 가장 낮은 수행
        for level, _ in rows:
            self.assertNotRegex(level, r"(조작|종속).{0,20}통제 방법")

    def test_json_example_follows_its_own_rules(self):
        # 3차 평가: 두 요소가 같은 행동(근거 대기)을 채점했고, 2단계뿐인 요소는 끝내지 못한 학생의 칸이 없었다
        data = json.loads(re.search(r"```json\n(.*?)```", skill("rubric"), re.S)[1])
        first, *others = data["areas"][0]["elements"]
        self.assertEqual(first["name"], "명제 판별")
        self.assertTrue(all("근거를 설명함" in level for level, _ in first["levels"][:-1]), first["levels"])
        for element in data["areas"][0]["elements"]:
            with self.subTest(element=element["name"]):
                levels = element["levels"]
                self.assertGreaterEqual(len(levels), 3)
                self.assertTrue(all(text.endswith(("함.", "씀.", "듦.", "힘.")) for text, _ in levels), levels)
                scores = [score for _, score in levels]
                self.assertEqual(scores, sorted(scores, reverse=True))
                self.assertEqual(len(set(scores)), len(scores))
                self.assertTrue(element.get("feedback"))                 # 중·고 기본: 가장 낮은 단계 피드백
        for element in others:
            self.assertFalse(any("근거" in text for text, _ in element["levels"]), element["name"])
        self.assertFalse(any("발표와 질의응답" == e["name"] for e in data["areas"][0]["elements"]))


class RubricLevelWordingTest(unittest.TestCase):
    """평가(105921 #3): 개수로 단계를 갈랐고 끝맺음이 섞였으며, 중·고 표에 피드백 계획이 없었다."""

    def test_counts_only_from_a_named_list(self):
        text = skill("rubric")
        self.assertTrue(has_rule(text, "개수로 가를 때", "셀 때만"))
        for example in ("\"2가지 이상 / 1가지뿐\"", "\"3회 이상 측정\"", "\"잦음\""):
            self.assertIn(example, text)
        self.assertTrue(has_rule(text, "\"부족함\"", "\"미흡함\"", "끝내지 않는다"))

    def test_feedback_line_is_default_for_every_level_of_school(self):
        text = skill("rubric")
        rows = section(text, "**표 아래 줄을 고정한다.**", "**수준별 점수 기본값**")
        self.assertTrue(has_rule(rows, "피드백 계획", "초·중·고"))
        self.assertIn("\"피드백(하)\"", rows)
        self.assertNotIn("표 옆에 피드백 계획 칸을 둘 수 있다", text)
        self.assertIn("`feedback`", text)
        self.assertIn("feedback", read("skills/rubric/scripts/make_rubric_form.py"))
        self.assertIn("피드백(하)", skill("lesson-plan"))                  # 지도안 평가 계획표와 같은 뜻

    def test_answer_order_and_plain_words(self):
        text = skill("rubric")
        self.assertIn(APPROVED["수행평가 끝 줄"], text)
        line = rule_line(text, "책임 안내 바로 아래", "평가계획서 양식")
        self.assertIsNotNone(line)
        self.assertIn("\"학교 평가계획서 양식 파일을 올려 주세요.", line)
        self.assertTrue(has_rule(text, "답변에 쓰는 말"))
        design = section(text, "[수행평가 설계]\n- 평가:", "```")
        self.assertNotIn("최저 합", design)
        self.assertNotIn("층", design)
        self.assertTrue(has_rule(text, "설계 뒤의 질문", "덧붙이지 않는다"))


class ItemCrossClueTest(unittest.TestCase):
    """평가(105921 #1·#5): 9번 <보기> ㄷ이 8번과 서술형 2(2)의 근거를 알려 주었고, 목록 이름이 지정 형식과 달랐다."""

    def test_every_item_pair_is_compared(self):
        self.assertEqual(missing_rules(skill("assessment-items"), {
            "모든 쌍": ("문항 간 단서", "모든 문항 쌍"), "횟수": ("n×(n-1)",), "<보기> 진술": ("<보기>", "정답 선지", "사실")}), [])
        checklist = read("shared/checklists/item-quality.md")
        row = next(line for line in checklist.splitlines() if line.startswith("| 문항 간 단서"))
        for word in ("모든 문항 쌍", "정답의 근거", "예시 답안", "<보기>", "n×(n-1)", "정답을 가린 채"):
            self.assertIn(word, row)
        self.assertTrue(has_rule(checklist, "정답이나 정답의 근거", "알려 주지 않는가"))

    def test_blind_review_is_required(self):
        """사용자 지시(2026-11-18): 다른 문항으로 답을 알 수 있게 하는 것은 절대 금지. 정답을 가린 검토를 따로 한다."""
        text = skill("assessment-items")
        self.assertTrue(has_rule(text, "문항 간 단서 차단", "절대 금지"))
        self.assertTrue(has_rule(text, "정답을 가린 검토", "다른 문항들만 읽고", "검토 에이전트"))

    def test_check_list_items_match_the_marks(self):
        self.assertTrue(has_rule(skill("assessment-items"), "목록의 항목", "`[확인 필요]`로 시작"))

    def test_ratio_line_has_a_fixed_place(self):
        self.assertTrue(has_rule(skill("assessment-items"), "3번 바로 아래", "예시 표보다 앞"))

    def test_school_year_is_named(self):
        text = skill("assessment-items")
        self.assertNotIn("학교학년도", text)
        self.assertTrue(has_rule(text, "2027학년도(학교 학년도)", "고3", "2022 개정"))
        self.assertTrue(has_rule(text, "수능 학년도", "1이 크다"))

    def test_rare_paper_rules_moved_to_a_reference(self):
        text, guide = skill("assessment-items"), read("shared/exam-paper-plain.md")
        self.assertIn("`references/exam-paper-plain.md`", text)
        for moved in ("너비 2:5:2", "감독 확인", "\"keep_with_next\": true", "\"column_line\": true", "\"page_numbers\": \"center\""):
            with self.subTest(moved=moved):
                self.assertNotIn(moved, text)
                self.assertIn(moved, guide)
        # 4지선다·3지선다도 원안지에 채운다 (선지 틀을 줄임). 원안지가 아닌 문제지로 돌리지 않는다
        self.assertTrue(has_rule(text, "4지선다", "3지선다", "`choices`"))
        self.assertFalse(has_rule(text, "4지선다", "원안지가 아닌 문제지"))
        self.assertTrue(has_rule(guide, "4지선다", "fill_exam.py"))
        manifests, _ = build.check(ROOT)
        self.assertIn("references/exam-paper-plain.md", manifests["assessment-items"])

    def test_record_output_order_uses_one_check_list(self):
        order = ("최종 문장", "기본값으로 정한 내용", "근거 표", "뺀 내용", "문장을 쓰지 못한 학생", "확인 필요", "마지막 한 줄")
        line = rule_line(read("shared/record-common-rules.md"), *order)
        self.assertIsNotNone(line)
        self.assertEqual([line.index(part) for part in order], sorted(line.index(part) for part in order))
        for name in RECORD_SKILLS:
            text = skill(name)
            with self.subTest(skill=name):
                line = rule_line(text, "문장 뒤에", *order[1:3], "문장을 쓰지 못한 학생", "확인 필요", "3개 이내")
                self.assertIsNotNone(line)
                self.assertLess(line.index("기본값으로 정한 내용"), line.index("확인 필요"))
                self.assertNotIn('"확인할 것"', text)

    def test_lesson_plan_leaves_performance_plans_to_rubric(self):
        self.assertTrue(has_rule(description("lesson-plan"), "수행평가 평가계획", "rubric"))

    def test_exam_form_scripts_are_excluded_from_other_skills(self):
        self.assertIn("scripts/fill_exam_spec.py", build._EXAM_FORM_ONLY)
        manifests, _ = build.check(ROOT)
        for name, files in manifests.items():
            if name != "assessment-items":
                with self.subTest(skill=name):
                    self.assertFalse([f for f in files if "fill_exam" in f])

    def test_plain_paper_uses_the_exam_form_page(self):
        guide = read("shared/exam-paper-plain.md")
        self.assertIn('"page": "sheet"', guide)
        self.assertTrue(has_rule(guide, "`margins`", "바꾸지 않는다"))
        self.assertTrue(has_rule(skill("assessment-items"), "exam-paper-plain.md", "문항정보표"))


class AlignmentC8Test(unittest.TestCase):
    """평가 방법이 성취기준 동사의 수행을 끌어내는지(C8)를 점검하고, 점검표를 가리키는 곳은 C1~C8로 맞춘다."""

    def test_checklist_has_c8(self):
        row = next(line for line in read("shared/checklists/curriculum-alignment.md").splitlines() if line.startswith("| C8 |"))
        for word in ("선택형/서술형/수행평가", "핵심 동사", "선택형 지식 문항"):
            self.assertIn(word, row)

    def test_no_reference_stops_at_c7(self):
        for path in [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("skills/*/references/*.md"), *ROOT.glob("shared/*.md")]:
            with self.subTest(path=path.name):
                self.assertNotIn("C1~C7", path.read_text(encoding="utf-8"))


class LessonPlanEscapeTest(unittest.TestCase):
    """재평가: 줄바꿈 기호가 실제 줄바꿈으로 들어가 백틱 표기가 깨졌다."""

    def test_newline_marks_are_shown_as_text(self):
        text = skill("lesson-plan")
        self.assertTrue(has_rule(text, "칸 안 줄은 `\\n`"))
        self.assertIn("`\"활동 1\\n명제\\n고르기\"`", text)
        self.assertNotIn("`\n`", text)
        self.assertIsNone(re.search(r"^`으로 자유롭게", text, re.M))


class ItemPatternScopeTest(unittest.TestCase):
    """재평가: 수능형 패턴 적용 기준, 행동 영역, 난이도 표기, 최소 성취수준 안내."""

    def test_suneung_scope_sentence_is_in_one_place(self):
        text = skill("assessment-items")
        lines = [line for line in text.splitlines() if "2015 개정 수능 실측" in line]
        self.assertEqual(len(lines), 1)   # 원본은 참고 자료 항목 하나, 고등학교 줄은 그 항목을 가리킨다
        self.assertTrue(lines[0].startswith("- `references/item-patterns/korean.md`"))
        for word in ("고3", "고1·2", "발문·선지", "학교 학년도"):
            self.assertIn(word, lines[0])
        high = next(line for line in text.splitlines() if line.startswith("- **고등학교**: 자료 해석"))
        self.assertIn("`references/item-patterns/` 항목", high)
        self.assertNotIn("배점 위치)를 따르되", high)

    def test_behavior_domains_follow_the_form_then_grounded_lists(self):
        text = skill("assessment-items")
        self.assertNotIn("- 행동 영역: 지식, 이해, 적용, 분석, 평가 중에서 고른다.", text)
        self.assertTrue(has_rule(text, "문항정보표 양식", "교과협의회", "그 말을 쓴다"))
        self.assertIn("| 수학 | 계산, 이해, 추론, 문제해결 |", text)
        self.assertIn("계산, 이해, 추론, 문제해결", read("shared/item-patterns/math.md"))
        science = read("shared/item-patterns/science.md")
        for word in ("추리", "분석", "탐구", "암기"):
            self.assertIn(word, science)
        self.assertTrue(has_rule(text, "난이도 표기", "학교 양식"))

    def test_checklist_checks_domain_against_the_standard_verb(self):
        checklist = read("shared/checklists/item-quality.md")
        self.assertIn("| Q11 | 행동 영역 |", checklist)
        self.assertIn("성취기준 동사", checklist)
        self.assertIn("Q11", skill("assessment-items"))

    def test_minimum_level_note_is_in_both_assessment_skills(self):
        self.assertIn("최소 성취수준", skill("rubric"))
        self.assertTrue(has_rule(skill("assessment-items"), "공통국어·공통수학·공통영어", "최소 성취수준", "40%"))


class UnitNameTest(unittest.TestCase):
    """재평가: 확산은 2022 개정 [9과04] '물질의 상태 변화'다."""

    def area_of(self, code: str) -> str:
        area = ""
        for line in MIDDLE_SCIENCE.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                area = line[3:].strip()
            if line.startswith(f"| [{code}] |"):
                return area
        raise AssertionError(code)

    def test_data_puts_diffusion_in_state_change(self):
        self.assertEqual(self.area_of("9과04-01"), "물질의 상태 변화")

    def test_worksheet_example_uses_the_data_unit(self):
        # 학습지 입력 예시는 SKILL.md 본문에서 references/worksheet-hwpx-input.md로 옮겼다
        block = re.search(r"```json\n(.*?)```", read("skills/worksheet/references/worksheet-hwpx-input.md"), re.S)[1]
        data = json.loads(block)
        self.assertEqual(data["unit"], self.area_of("9과04-01"))
        self.assertIn("확산", json.dumps(data, ensure_ascii=False))
        self.assertTrue(data["standards"][0].startswith("[9과04-01] "))

    def test_item_table_example_uses_the_data_unit(self):
        table = section(skill("assessment-items"), "| 문항 | 유형 | 내용 영역 |", "\n\n")
        self.assertNotIn("물질의 구성", table)
        self.assertIn("물질의 상태 변화", table)


class CurriculumReadmeTest(unittest.TestCase):
    def test_file_count_matches_the_folder(self):
        count = sum(1 for path in (ROOT / "shared" / "curriculum" / "2022").rglob("*.md") if path.name != "INDEX.md")
        text = read("shared/curriculum/README.md")
        self.assertIn(f"과목 264개, 파일 {count}개 |", text)
        self.assertNotIn("파일 148개", text)


class FormativeBoundaryTest(unittest.TestCase):
    """재평가: 두 스킬 설명에 '형성평가'가 함께 있으므로 경계를 적는다 (설명 길이 규칙은 test_skill_consistency)."""

    def test_both_descriptions_name_the_boundary(self):
        sheet, items = description("worksheet"), description("assessment-items")
        self.assertTrue(has_rule(sheet, "형성평가지·복습지", "이 스킬이 맡", "assessment-items"))
        self.assertTrue(has_rule(items, "형성평가지·복습지", "worksheet"))


if __name__ == "__main__":
    unittest.main()
