"""3차 평가 뒤의 시험: 같은 스킬 안에서 기본값·규칙이 어긋나지 않고, 여러 스킬에 걸친 규칙이 대상 스킬 모두에 있다.

승인된 교사 안내 문구는 문장 그대로(skill_rules.APPROVED), 내부 규칙은 한 줄에 든 핵심 낱말로 본다.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402
from skill_rules import (ALL_SKILLS, APPROVED, LESSON_SKILLS, OUTPUT_HEADINGS, RECORD_SKILLS, ROOT,  # noqa: E402
                         YEAR_QUESTION_SKILLS, description, has_rule, missing_rules, numbered_items, read,
                         rule_line, section, skill)


class AssessmentItemsConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.text = skill("assessment-items")

    def test_two_columns_is_the_default_without_asking(self):
        self.assertTrue(has_rule(self.text, "양식이 없으면", "묻지 않고", "2단", "기본값"))
        self.assertFalse(has_rule(self.text, "1단·2단 중", "묻는다"))

    def test_file_counts_match_the_listed_outputs(self):
        self.assertTrue(has_rule(self.text, "정기시험", "4개", "형성평가", "문항정보표", "3개"))
        self.assertNotIn("정기시험은 3개, 형성평가는 문항정보표를 뺀 2개", self.text)

    def test_answer_distribution_rule_is_written_once(self):
        lines = self.text.splitlines()
        self.assertEqual(sum("번호별 개수 차이" in line and "1을 넘지" in line for line in lines), 1)
        self.assertEqual(sum("2015 개정 수능 실측" in line for line in lines), 1)
        self.assertIn("학교 학년도", self.text)


class WorksheetConsistencyTest(unittest.TestCase):
    def test_review_type_has_no_one_line_summary(self):
        text = skill("worksheet")
        self.assertNotIn("→ 한 줄 정리", text)
        self.assertTrue(has_rule(text, "한 줄 정리", "두지 않는다"))
        self.assertIn("`topics` 모드", text)


class RecordSkillConsistencyTest(unittest.TestCase):
    def test_term_start_date_follows_the_guide(self):
        # 기재요령 임원 재임기간 예시는 03.01.로 시작한다 (인천 고 p.89, 경기 중 p.84)
        for name in RECORD_SKILLS:
            self.assertIn("(2026.03.01.-2027.02.28.)", skill(name), name)
            self.assertNotIn("(2026.03.02.-", skill(name), name)
        self.assertNotIn("(2026.03.02.-", read("shared/record-activity-admission.md"))

    def test_behavior_skill_has_no_subject_record_leftovers(self):
        text = skill("behavior-record")
        for leftover in ("평가 요소인 오차 원인 분석", "다시 측정함", "기구 조작", "나눗셈"):
            self.assertNotIn(leftover, text)

    def test_privacy_request_asks_for_random_symbols_not_seat_numbers(self):
        for name in RECORD_SKILLS:
            text = skill(name)
            self.assertIn(APPROVED["기호 요청"], text, name)
            self.assertNotIn('"1번"', text, name)
            self.assertNotIn("1번 = 누구", text, name)
        self.assertTrue(has_rule(read("shared/privacy.md"), "출석번호", "가명으로 쓰지 않는다"))


class DesignSystemConsentTest(unittest.TestCase):
    def test_account_save_is_asked_once_before_creating(self):
        text = read("shared/design-system-setup.md")
        question = APPROVED["수업 디자인 저장"]
        self.assertIn(question, text)
        self.assertEqual(missing_rules(text, {"거절": ("거절하면", "저장하지 않는다"),
                                              "이미 있으면": ("이미 있으면", "묻지 않"),
                                              "하우스 스타일": ("house-style.md",)}), [])
        self.assertLess(text.index(question), text.index(rule_line(text, "Design System", "만든다")))   # 묻고 나서 만든다


class SlideStudentCopyTest(unittest.TestCase):
    def test_fourth_question_and_default(self):
        text = skill("class-slides")
        self.assertIn("> 4. 학생에게 나눠 줄 파일인가요? (그렇다면 정답과 노트를 뺀 학생용 사본을 함께 만듭니다)", text)
        self.assertRegex(text, r"\| 학생용 사본 \| 만들지 않는다 \(교사용만\)")
        self.assertIn("--student", text)
        self.assertTrue(has_rule(text, "app-slides.md", "7절"))
        self.assertTrue(has_rule(read("skills/class-slides/references/app-slides.md"), "1절", "4번 질문"))


class AnswerOrderTest(unittest.TestCase):
    """평가에서 '맨 위' 조건이 책임 안내와 부딪쳤다. 답변 순서를 한 문서로 정하고 모든 스킬이 가리킨다."""

    def setUp(self):
        self.order = read("shared/answer-order.md")

    def test_order_document_names_the_four_parts_in_order(self):
        parts = ("**책임 안내**", "**기본값으로 정한 내용**", "**본문·파일**", "**확인 필요**")
        positions = [self.order.index(part) for part in parts]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(missing_rules(self.order, {
            "기본값 자리": ("기본값으로 정한 내용", "책임 안내 바로 아래"),
            "학생부 순서": ("학생부 세 스킬", "책임 안내 바로 다음"),
            "목록 제목 고정": ("목록 제목", "기본값으로 정한 내용", "확인 필요", "그대로"),
            "첫 질문 앞에 붙이지 않음": ("첫 질문", "승인된 질문 문구", "붙이지 않는다"),
            "진행 문장": ("중입니다", "맨 위"),
        }), [])

    def test_every_skill_points_to_it_and_carries_it(self):
        manifests, _ = build.check(ROOT)
        for name in ALL_SKILLS:
            with self.subTest(skill=name):
                line = rule_line(skill(name), "답변 순서", "references/answer-order.md")
                self.assertIsNotNone(line)
                self.assertIn("맨 위", line)                     # 작업 중 문장을 맨 위에 쓰지 않는다는 덧말
                self.assertIn("references/answer-order.md", manifests[name])

    def test_every_output_section_ends_with_the_check_list(self):
        for name, heading in OUTPUT_HEADINGS.items():
            part = skill(name).split(heading, 1)[1].split("\n## ", 1)[0]
            items = numbered_items(part)
            with self.subTest(skill=name):
                self.assertTrue(items and items[-1].startswith("확인 필요"), items[-1:] or "번호 목록 없음")
                if name in LESSON_SKILLS:
                    self.assertTrue(items[0].startswith("기본값으로 정한 내용"), items[0])

    def test_assessment_skills_keep_their_own_title_rule(self):
        # 평가에서 "확인할 것", "제가 정한 기본값"으로 바꿔 쓴 두 스킬은 자기 문서에도 규칙을 둔다
        for name in ("rubric", "assessment-items"):
            self.assertTrue(has_rule(skill(name), "목록 제목", "그대로", "확인할 것"), name)


class SchoolYearInFirstRequestTest(unittest.TestCase):
    """학습지 평가 #2: 11월 요청에 학년도를 묻지 않고 '두 학년도 모두 2022 개정'이라고 안내했다."""

    def test_year_question_goes_into_the_first_request_even_when_curricula_match(self):
        guide = read("shared/curriculum-transition.md")
        self.assertEqual(missing_rules(guide, {"맨 앞 번호": ("목록 맨 앞",), "같아도 묻기": ("같아도 묻는다",),
                                               "대신하지 않음": ("이 질문을 대신하지 않는다",)}), [])
        for name in YEAR_QUESTION_SKILLS:
            part = section(skill(name), "## 1.", "\n## 2.")
            with self.subTest(skill=name):
                line = rule_line(part, "11~2월", "학년도 질문", "curriculum-transition.md")
                self.assertIsNotNone(line)
                self.assertIn("같아도 묻는다", line)


class WorksheetDefaultsTest(unittest.TestCase):
    def test_concept_format_still_gets_a_same_page_challenge(self):
        # 학습지 평가 #3: 개념 정리 형식에 칸이 없다며 도전 과제를 넣지 않았다
        text = skill("worksheet")
        row = next(line for line in text.splitlines() if line.startswith("| 같은 쪽 도전 과제 (기본) |"))
        for word in ("`topics`", "`challenge`", '"도전 과제" 칸', "건너뛰지 않는다"):
            self.assertIn(word, row)

    def test_first_request_wording_is_kept(self):
        self.assertTrue(has_rule(section(skill("worksheet"), "## 1. 한 번에 요청하기", "\n## 2."),
                                 "그대로", "다른 말을 더하지 않는다"))

    def test_rare_hwpx_input_lives_in_its_reference(self):
        text = skill("worksheet")
        self.assertIn("references/worksheet-hwpx-input.md", text)
        self.assertNotIn("```json", text)
        self.assertIn('"model"', read("skills/worksheet/references/worksheet-hwpx-input.md"))


class SkillBoundaryTest(unittest.TestCase):
    """스킬 고르기 평가: 진도표·단원 설계를 지도안이, 수행과제 설계를 루브릭이 가져갔다."""

    def test_lesson_plan_names_what_it_does_not_do(self):
        text = description("lesson-plan")
        line = rule_line(text, "진도표", "백워드", "GRASPS", "맡지 않는다")
        self.assertIsNotNone(line)
        self.assertIn("교수학습 및 평가 운영 계획", line)

    def test_rubric_leaves_task_scenario_design_out(self):
        text = description("rubric")
        self.assertTrue(has_rule(text, "채점 기준", "GRASPS", "맡지 않는다"))

    def test_no_skill_makes_student_checklists(self):
        # 사용자 지시(2026-11-17): 학생용 체크리스트와 채점 기록표는 아예 만들지 않는다
        text = description("worksheet")
        self.assertTrue(has_rule(text, "학생용 체크리스트", "채점 기록표", "다른 스킬도 만들지 않는다"))
        for name in ALL_SKILLS:
            self.assertNotIn("체크리스트도 이 스킬이 맡", description(name), name)
        self.assertNotIn("| 자기평가 체크리스트 |", skill("worksheet"))

    def test_every_description_keeps_the_build_rules(self):
        for name in ALL_SKILLS:
            text = description(name)
            with self.subTest(skill=name):
                self.assertLessEqual(len(text), build.MAX_DESCRIPTION_LENGTH)
                self.assertEqual(build.plain_value_errors(skill(name)), [])
                self.assertNotRegex(text, r"[<>]")


class SlideCountTest(unittest.TestCase):
    def test_default_count_has_a_cap_and_a_reason_line(self):
        # PPT 평가 #2: 기본값인데 16장이 나왔다
        self.assertEqual(missing_rules(skill("class-slides"), {
            "세는 법": ("정답 장까지", "전체로 센다"), "상한": ("상한", "14장"), "넘기지 않음": ("16장을 넘기지",),
            "늘 적는 값": ("장 수", "인터넷 자료", "늘 적는다")}), [])

    def test_first_request_starts_with_its_first_line(self):
        line = rule_line(skill("class-slides"), "첫 응답", "첫 줄", "시작")
        self.assertIsNotNone(line)
        self.assertIn('"수업 PPT를 만들기 위해 알려 주세요."', line)


class HouseStyleScopeTest(unittest.TestCase):
    def test_subject_colors_are_the_named_pptx_exception(self):
        self.assertEqual(missing_rules(read("shared/house-style.md"), {
            "예외 수": ("예외는 세 가지",), "pptx 교과 색": (".pptx 생성기", "교과마다")}), [])
        self.assertTrue(has_rule(skill("class-slides"), "house-style.md", "예외 3"))


class AlignmentChecklistTest(unittest.TestCase):
    """정렬 점검표를 가리키는 스킬은 모두 새 항목 C8까지 본다 (C1~C7에서 멈추지 않는다)."""

    def test_every_skill_using_the_checklist_names_c8(self):
        users = [name for name in ALL_SKILLS if "curriculum-alignment.md" in skill(name)]
        self.assertGreaterEqual(len(users), 4)
        for name in users:
            self.assertRegex(skill(name), r"C(1~)?8|C\d~C8|, C8", name)


if __name__ == "__main__":
    unittest.main()
