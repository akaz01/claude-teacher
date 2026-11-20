"""스킬 사이 연결 시험: 양식 채우기, 빌드에 들어가는 파일, 스킬 이름, 학생부 공통 규칙, 코드 크기 한도를 본다.

승인된 교사 안내 문구는 문장 그대로(skill_rules.APPROVED), 내부 규칙은 한 줄에 든 핵심 낱말로 본다.
"""

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_rules import (APPROVED, RECORD_SKILLS, RESPONSIBILITY_SKILLS, ROOT, has_rule,  # noqa: E402
                         missing_rules, read, rule_line, skill)

SHARED_SCRIPTS = ROOT / "shared" / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

import build  # noqa: E402
import fill_hwpx  # noqa: E402
from make_hwpx import build_hwpx  # noqa: E402

skill_text = skill
FORM_SKILLS = ("lesson-plan", "worksheet", "rubric", "assessment-items", "unit-design")
FORM_FILES = ("scripts/fill_hwpx.py", "scripts/fill_hwpx_parse.py", "scripts/make_hwpx.py",
              "scripts/make_hwpx_check.py", "references/form-fill.md")
REMOVED_SKILLS = ("annual-plan", "counseling-log", "curriculum-lookup-skill", "differentiation", "meeting-minutes",
                  "official-doc", "parent-letter", "privacy-rules", "school-writing-style", "student-feedback",
                  "student-record")   # unit-design은 2026-11-05에 지웠다가 2026-11-20 사용자 요청으로 다시 만들었다
OLD_FORM_PROMISE = re.compile(r"구성에 맞춰|구성에 맞춘다|그 양식에 맞춤")
SKILL_MENTION = re.compile(r"`([a-z]+(?:-[a-z]+)*)` 스킬")
MAX_PYTHON_LINES = 800
AWKWARD = r"까닭|짚|이어 감|이어 가며|넓혀|나누어 맡|고쳐|고침|고친|찾아 읽|따져|되짚"  # 교사 기록 928문장에 없는 말
# 학생부 예문에 쓰면 안 되는 말: 이전의 부족을 짐작하게 하는 말, 사건, 다른 학생의 부족, 덧붙인 평가
NEGATIVE = (r"늘어남|늘어난|늘자|줄었|줄어듦|다툼|다투|바로잡|했으나|했지만|지키지 않|지키지 못|어색해하|어려워하|"
            r"헷갈려|저조|아쉬운|활동임\.|대부분의 과제|썼음|아직 말이|실수 후|" + AWKWARD)


def common_rules_text() -> str:
    return read("shared/record-common-rules.md")


def record_text() -> str:
    """학생부 세 스킬(세특·창체·행특)의 SKILL.md와 공통 규칙 파일을 이어 붙인 글. 규칙이 어느 한 곳에 있으면 된다."""
    return "\n".join([*(skill(name) for name in RECORD_SKILLS), common_rules_text()])


def teacher_documents() -> list[Path]:
    documents = [*ROOT.glob("skills/**/*.md"), *ROOT.glob("shared/*.md"), *ROOT.glob("shared/checklists/*.md"),
                 *ROOT.glob("shared/item-patterns/*.md"), ROOT / "README.md"]
    return [path for path in documents if "__pycache__" not in path.parts]


def local_imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return {name for name in names if (SHARED_SCRIPTS / f"{name}.py").exists()}


def copy_scripts(manifest: dict, folder: Path) -> None:
    for target, source in manifest.items():
        if target.startswith("scripts/"):
            destination = folder / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


class FormFillWiringTest(unittest.TestCase):
    def test_skills_and_readme_point_to_the_fill_tool_and_guide(self):
        for name in FORM_SKILLS:
            with self.subTest(skill=name):
                text = skill(name)
                for word in ("scripts/fill_hwpx.py", "scripts/make_hwpx.py", "references/form-fill.md", "그 파일에",
                             "hwpx로 저장"):
                    self.assertIn(word, text)
        readme = read("README.md")
        for word in ("그 파일에", "hwpx로 저장", "fill_hwpx.py"):
            self.assertIn(word, readme)

    def test_old_promise_is_gone(self):
        for path in [ROOT / "README.md", *(ROOT / "skills" / name / "SKILL.md" for name in FORM_SKILLS)]:
            with self.subTest(path=path.name):
                self.assertIsNone(OLD_FORM_PROMISE.search(path.read_text(encoding="utf-8")))

    def test_build_carries_everything_the_tool_needs(self):
        manifests, errors = build.check(ROOT)
        self.assertEqual(errors, [])
        for name in FORM_SKILLS:
            with self.subTest(skill=name):
                self.assertLessEqual(set(FORM_FILES), set(manifests[name]))
                self.assertLessEqual({"scripts/fill_xlsx.py", "scripts/fill_xlsx_parse.py"}, set(manifests[name]))

    def test_guide_repeats_the_tool_sentence_and_names_its_limits(self):
        guide = read("shared/form-fill.md")
        self.assertIn(fill_hwpx.HWP_GUIDE, guide)
        for limit in ("행", "수식", "**", "덮어쓰지"):
            with self.subTest(limit=limit):
                self.assertIn(limit, guide)

    def test_packaged_tool_runs_from_each_skill_folder(self):
        manifests, _ = build.check(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            form = Path(temp) / "양식.hwpx"
            build_hwpx({"blocks": [{"type": "paragraph", "text": "○○ 단원"}]}, form)
            for name in FORM_SKILLS:
                with self.subTest(skill=name):
                    folder = Path(temp) / name
                    copy_scripts(manifests[name], folder)
                    done = subprocess.run([sys.executable, str(folder / "scripts" / "fill_hwpx.py"), "--inspect", str(form)],
                                          capture_output=True, encoding="utf-8", check=False, cwd=temp)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertIn("○○ 단원", done.stdout)


class ExamFormWiringTest(unittest.TestCase):
    def test_skill_uses_the_exam_tool_instead_of_splitting_the_paper(self):
        text = skill("assessment-items")
        for word in ("scripts/fill_exam.py", "--inspect", "--student"):
            self.assertIn(word, text)
        self.assertNotIn("<보기>` 상자, 표가 든 문항은 넣을 수 없다", text)

    def test_guide_has_the_exam_section_and_its_limits(self):
        guide = read("shared/exam-form-fill.md")
        part = guide[guide.index("## 시험지 양식 채우기"):]
        for phrase in ("--inspect", "--student", "`short_table`", "`combo_table`", "`grid_table`", "`paragraphs`",
                       "그림 넣기", "수식", "오류로 막는다"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, part)

    def test_every_skill_stays_under_the_upload_limit(self):
        manifests, errors = build.check(ROOT)
        self.assertEqual(errors, [])
        self.assertLessEqual({"scripts/fill_exam.py", "scripts/fill_exam_parse.py"}, set(manifests["assessment-items"]))
        for name, files in manifests.items():
            with self.subTest(skill=name):
                self.assertLessEqual(len(files), build.MAX_SKILL_FILES)

    def test_packaged_exam_tool_runs_from_the_skill_folder(self):
        manifests, _ = build.check(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "assessment-items"
            copy_scripts(manifests["assessment-items"], folder)
            done = subprocess.run([sys.executable, str(folder / "scripts" / "fill_exam.py")],
                                  capture_output=True, encoding="utf-8", check=False, cwd=temp)
            self.assertEqual(done.returncode, 2, done.stderr)
            self.assertIn("fill_exam.py --inspect", done.stdout)


class ExcelFormWiringTest(unittest.TestCase):
    def test_rubric_makes_no_score_sheet_and_keeps_the_guide_section(self):
        # 사용자 지시(2026-11-16): 수행평가는 채점 기록표(엑셀)와 학생용 체크리스트를 만들지 않는다
        text = skill("rubric")
        self.assertNotIn("make_score_sheet", text)
        self.assertTrue(has_rule(text, "학생용 체크리스트", "채점 기록표", "만들지 않는다"))
        self.assertIn("form-fill.md", text)
        guide = read("shared/form-fill.md")
        self.assertIn("scripts/fill_xlsx.py", guide)
        self.assertNotIn("이 도구로 채울 수 없다. 항목과 순서만", guide)


class RealNameStopTest(unittest.TestCase):
    """학생 실명이 오면 가명으로 바꿔 계속하지 않고 멈춘다."""

    def setUp(self):
        self.privacy, self.tasks, self.skill = read("shared/privacy.md"), read("shared/privacy-tasks.md"), record_text()
        self.stop = self.privacy.split("## 3.")[0]

    def test_stop_rule_replaces_the_old_continue_rule(self):
        self.assertIn("작업을 멈춘다", self.privacy)
        for text in (self.privacy, self.tasks, self.skill):
            for old in ("작업을 거부하지 않는다", "바꿔서 작성할게요", "가명으로 바꾸고 한 번 짧게 안내"):
                self.assertNotIn(old, text)

    def test_stop_outranks_no_question_requests_and_asks_for_a_new_chat(self):
        for word in ("질문 없이 진행", "이 대화를 삭제", "새 대화"):
            self.assertIn(word, self.stop)

    def test_stop_notice_uses_the_approved_sentences_verbatim(self):
        notice = self.stop.split("**안내 문장:**")[1]
        for key in ("멈춤 안내 첫 줄", "멈춤 안내 새 대화", "멈춤 안내 까닭"):
            self.assertIn(APPROVED[key], notice, key)
        self.assertLess(notice.index(APPROVED["멈춤 안내 첫 줄"]), notice.index(APPROVED["멈춤 안내 새 대화"]))
        self.assertLess(notice.index(APPROVED["멈춤 안내 새 대화"]), notice.index(APPROVED["멈춤 안내 까닭"]))

    def test_how_to_remove_guide_reaches_teachers(self):
        self.assertIn("## 7. 올리기 전에 지우는 법", self.privacy)
        for text in (self.privacy, read("README.md")):
            for word in ("찾아 바꾸기", "숨긴 시트", "문서 정보", "대조표"):
                self.assertIn(word, text)

    def test_teachers_are_told_why_they_must_remove_it_themselves(self):
        for text in (self.stop, self.skill, read("README.md")):
            self.assertIn(APPROVED["개인정보 까닭"], text)
            self.assertIn("되돌릴 수 없", text)

    def test_skill_checks_privacy_before_anything_else(self):
        for name in RECORD_SKILLS:
            with self.subTest(skill=name):
                text = skill(name)
                self.assertTrue(has_rule(text, "개인정보 확인", "다른 일보다 먼저"))
                self.assertLess(text.index("첫 메시지에 자료"), text.index("학생부 문장을 쓰기 위해"))


# 학생부 내부 규칙: 이름 → 한 줄에 함께 있어야 할 핵심 낱말. 세 SKILL.md와 공통 규칙 파일 가운데 어디에 있어도 된다
RECORD_RULES = {
    "걸러 낸 값은 종류만": ("종류와 이유만",), "걸러 낼 값": ("공인어학시험 성적",),
    "장면 하나면 임시 초안": ("장면", "임시 초안"), "입력에 없는 내용": ("입력에 없는 내용", "더하지 않는다"),
    "초안 안내 조건": ("문장을 낸 답변에만",), "점검표 통과 줄": ("그 외 통과",), "빠진 것만": ("빠진 것만 묻는다",),
    "분량 몰라도 씀": ("입력 분량", "막지 않는다"), "근거로 먼저": ("있는 근거로 먼저",), "비교표": ("비교표", "기다리지 않는다"),
    "수업에서 쌓기": ("이어 붙이지 않고", "문장을 쌓는다"), "더하지 않음": ("메모에 없는 행동", "더하는 것은 안 된다"),
    "과목이 보임": ("어떤 과목의 어떤 탐구",), "부정 서술": ("부정적 서술을 쓰지 않는다",),
    "실패한 측정": ("실패한 측정", "쓰지 않고"), "가설과 다른 결과": ("가설과 다른 결과",), "뒤집지 않음": ("앞을 뒤집는 말",),
    "부족 뒤집기 구조": ("부족한 모습을 앞에 두고", "뒤집는"), "넣을지 묻지 않음": ("넣을지 묻지 않는다",),
    "통째로 뺌": ("순화하지 말고", "뺀다"), "문장 먼저": ("문장을 맨 먼저 낸다",), "짧은 메모 단계": ("메모가 짧은 학생일수록",),
    "쌓은 문장 예": ("쌓은 문장:",), "성과 단정": ("성과를 단정하는 말", "결과가 있을 때만"), "내부 사정": ("내부 사정은 쓰지 않는다",),
    "맡은 일은 맥락 아님": ("맡은 일을 맥락처럼 쓰지 않는다",), "주제 유지": ("겹침을 피하려고", "주제를 빼지 않는다"),
    "제출함으로 끝내지 않음": ('"제출함"으로 끝내지 않고',), "하지 않은 단계": ("메모가 하지 않았다고 한 단계",),
    "너무 짧게 끝내지 않음": ("너무 짧게 끝내지 않는다",), "100자 미만": ("100자 미만", "새 내용"),
    "말만 바꿔 되풀이": ("말만 바꿔 되풀이하지 않는다",), "고치기 전 잘못": ("고치기 전의 잘못",),
    "시점 표현": ("시점 표현", "이전의 부족"), "한도의 절반": ("남은 한도의 절반 이상",), "참여 확인": ("교사가 참여를 확인",),
    "고유 행동": ("학생 고유의 행동과 결과", "지어내지 않는다"), "날짜순 아님": ("날짜순으로 나열하지 않는다",),
    "평가어를 긍정으로": ("메모의 평가어", "긍정적인 말로"), "변화도 긍정": ("변화도 긍정적으로",),
    "사건 짐작": ("사건을 짐작하게 하는 말",), "상황 붙이지 않음": ("메모에 없는 상황을 붙이지 않는다",),
    "장면 하나도 100자": ("장면이 하나뿐인 학생도", "100자 이상"), "시상 여부": ("시상 여부",),
    "월별 나열 아님": ("월별로 늘어놓지 않는다",), "되풀이 맺음": ("앞 문장의 뜻을 되풀이",),
    "공통 활동 묶기": ("공통 활동", "월을 빼고", "한 문장으로 묶어"), "참여 사실뿐": ("참여 사실뿐이어도", "막지 않는다"),
    "이수시간": ("이수시간",), "재임기간": ("재임기간의 날짜를 지어내지 않는다",),
    "시상 행사": ("축제, 체육대회", "시상이 있을 수 있는 행사"), "책임 안내 다음 문장": ("책임 안내 바로 다음이 문장이다",),
    "학생당 한 줄": ("학생당 한 줄",), "두 곳에 쓰지 않음": ("같은 내용을 두 곳에 쓰지 않는다",),
    "보충 질문 묶기": ("보충 질문을 한 목록으로",), "과정 설명 없음": ("작성 과정은 설명하지 않는다",),
    "되풀이 맺음 금지": ("앞 문장을 되풀이하는 맺음",), "약점 빼고 좋게": ("약점을 빼서", "메모보다 좋게"),
    "태도를 보임 한 명": ('"~ 태도를 보임"', "한 명까지만"), "한 번은 보이게": ("모든 학생의 문장에 한 번은",),
    "성취기준 조회": ("references/curriculum-lookup.md",), "성취기준 넣지 않음": ("성취기준의 코드와 문장", "넣지 않는다"),
}
# 사라져야 할 옛 규칙
RECORD_GONE = ("넣어 달라고", '답변 맨 위에 "기본값으로 정한 내용"', "300자를 채우려 늘리지 않는다", "과목명 색인")


class StudentRecordRulesTest(unittest.TestCase):
    """학생부 스킬: 걸러 낸 값 비공개, 임시 초안, 끝 줄 조건, 짧은 표, 성취기준 안내."""

    def setUp(self):
        self.skill = record_text()

    def test_record_rules_are_kept(self):
        self.assertEqual(missing_rules(self.skill, RECORD_RULES), [])
        for old in RECORD_GONE:
            self.assertNotIn(old, self.skill)

    def test_guide_and_audit_agree(self):
        self.assertTrue(has_rule(read("shared/record-guide.md"), "종류와 이유만"))
        self.assertIn("공인어학시험 성적", read("shared/record-guide.md"))
        audit = read("shared/checklists/record-audit.md")
        self.assertIn("그 외 통과", audit)
        self.assertNotIn("| R1 기재 금지 | 통과", audit)

    def test_first_request_uses_the_approved_wording(self):
        for sentence in (APPROVED["세특 첫 요청"], APPROVED["세특 반 전체 안내"], APPROVED["세특 메모 안내"],
                         APPROVED["개인정보 지우기"], APPROVED["초안 안내"]):
            self.assertIn(sentence, self.skill)

    def test_subject_patterns_are_wired_and_clean(self):
        manifests, _ = build.check(ROOT)
        self.assertIn("references/record-subject-patterns.md", manifests["subject-record"])
        text = read("shared/record-subject-patterns.md")
        for subject in ("## 국어", "## 수학", "## 영어", "## 사회", "## 역사", "## 과학", "## 정보",
                        "## 체육", "## 음악", "## 미술", "## 기술·가정", "## 제2외국어"):
            self.assertIn(subject, text)
        examples = [line[2:] for line in text.splitlines() if line.startswith("> ") and line.endswith(".")
                    and "근거와 한계" not in line and "KICE" not in line and "2026 기재요령" not in line
                    and "예문의 학생" not in line]
        self.assertGreaterEqual(len(examples), 50)
        for example in examples:
            self.assertNotRegex(example, r"대회|수상|토익|특허|교외|\[\d")
            self.assertLessEqual(len(example.encode("utf-8")), 1500)

    def test_behavior_activity_patterns_are_wired_and_clean(self):
        manifests, _ = build.check(ROOT)
        for name in ("activity-record", "behavior-record"):
            self.assertIn("references/record-behavior-activity.md", manifests[name])
        text = read("shared/record-behavior-activity.md")
        for heading in ("## 행동특성 및 종합의견", "### 자율·자치활동", "### 동아리활동", "### 진로활동"):
            self.assertIn(heading, text)
        self.assertIn("참고용 가설", text)
        self.assertNotRegex(text, r"중고-[A-Z]")

    def test_survey_findings_are_kept_as_cautions_only(self):
        examples = read("shared/record-examples.md")
        self.assertEqual(missing_rules(examples, {"위장형": ("위장형 금지 소재",), "근거 아님": ("우수 사례의 근거는 아니다",),
                                                  "도달 정도": ("수업 목표에 얼마나 도달했는지",)}), [])


class RecordSkillSplitTest(unittest.TestCase):
    """학생부는 세특·창체·행특 세 스킬로 나뉘고, 모두 같은 기본 규칙을 지닌다."""

    # 첫 응답에 바로 필요한 말은 SKILL.md마다 남긴다 (승인 문구는 그대로, 나머지는 핵심 낱말)
    COMMON_APPROVED = (APPROVED["책임 안내"], APPROVED["초안 안내"], APPROVED["계정 안전"])
    COMMON = {"지어내지 않음": ("메모에 없는 내용", "지어내지 않는다"), "부정 서술": ("부정적 서술을 쓰지 않는다",),
              "초안 안내 조건": ("문장을 낸 답변에만",), "근거로 먼저": ("있는 근거로 먼저",), "통과 줄": ("그 외 통과",),
              "빠진 것만": ("빠진 것만 묻는다",), "실명 멈춤": ("작업을 멈추고",), "질문 없이": ("질문 없이 진행",),
              "날짜 표기": ("`내용(0000.00.00.)`",), "사유 문구": ("사유 문구",),
              "공통 규칙": ("references/record-common-rules.md",), "학부모 요구 금지": ("학부모에게", "요구하면 안 된다")}
    # 세 스킬이 따로 베끼던 규칙은 공통 규칙 파일에 한 번만 둔다
    SHARED_ONLY = (("고치기 전의 잘못",), ("시점 표현이 이전의 부족",), ("같은 사실을 말만 바꿔 되풀이",),
                   ("메모에 없는 행동, 결과, 감정",), ("종류와 이유만",), ("`---` 줄로 구분",), ("낱말만 바꿔",),
                   ("빈칸은 지어내지 않고",), ("순화하지 말고",), ("메모에 없는 상황을 붙이지 않는다",), ("각오, 다짐, 소감",),
                   ("짐작으로 행동을",))
    CALLS = {"subject-record": ("세특:", "교과세특:", "과세특:", "과목세특:", "세부능력:", "교과발달:"),
             "activity-record": ("창체:", "창체특기:", "자율:", "자치:", "자율자치:", "동아리:", "진로:"),
             "behavior-record": ("행특:", "행동특성:", "종합의견:", "행발:", "행종:")}

    def test_old_skill_is_gone(self):
        self.assertFalse((ROOT / "skills" / "student-record").exists())

    def test_common_rules_live_in_one_file(self):
        lines = common_rules_text().splitlines()
        for words in self.SHARED_ONLY:
            with self.subTest(rule=words):
                self.assertEqual(sum(all(word in line for word in words) for line in lines), 1)
                for name in RECORD_SKILLS:
                    self.assertFalse(has_rule(skill(name), *words), name)

    def test_common_rules_are_built_into_each_record_skill(self):
        manifests, _ = build.check(ROOT)
        for name in RECORD_SKILLS:
            self.assertIn("references/record-common-rules.md", manifests[name])
        for name in ("assessment-items", "class-slides", "lesson-plan", "rubric", "worksheet"):
            self.assertNotIn("references/record-common-rules.md", skill(name))

    def test_descriptions_route_char_counts_and_privacy_to_all_three(self):
        # 설명 길이·꺾쇠·따옴표 규칙은 test_skill_consistency가 모든 스킬에서 본다
        for name in RECORD_SKILLS:
            description = build.parse_frontmatter(skill(name))["description"]
            self.assertTrue(has_rule(description, "항목이 분명하지 않으면", "먼저 항목을 묻는다"), name)
            self.assertTrue(has_rule(description, "개인정보 지우기", "가명 처리", "세 학생부 스킬이 모두"), name)
            self.assertNotIn("생기부", description, name)

    def test_every_record_skill_keeps_the_common_rules(self):
        for name in RECORD_SKILLS:
            text = skill(name)
            with self.subTest(skill=name):
                self.assertEqual(missing_rules(text, self.COMMON), [])
                for sentence in self.COMMON_APPROVED:
                    self.assertIn(sentence, text)

    def test_call_names_are_in_each_description(self):
        for name, calls in self.CALLS.items():
            description = build.parse_frontmatter(skill(name))["description"]
            for call in (*calls, "학생부:"):
                with self.subTest(skill=name, call=call):
                    self.assertIn(f'"{call}"', description)

    def test_admission_patterns_are_wired_and_clean(self):
        manifests, _ = build.check(ROOT)
        for name, ref in (("subject-record", "record-subject-admission.md"),
                          ("activity-record", "record-activity-admission.md"),
                          ("behavior-record", "record-behavior-admission.md")):
            with self.subTest(skill=name):
                self.assertIn(f"references/{ref}", manifests[name])
                text = read(f"shared/{ref}")
                self.assertIn("가상", text)
                self.assertIn("대학 공통 평가요소", text)
                examples = [line[2:] for line in text.splitlines() if line.startswith("> ")]
                self.assertGreaterEqual(len(examples), 6)
                for example in examples:
                    self.assertNotRegex(example, r"대회|수상|토익|했으나|했지만|처음에는|줄어|늘어|사과|다툼|" + AWKWARD)
                    self.assertLessEqual(len(example.encode("utf-8")), 1500)

    def test_service_club_and_writer_rules_follow_the_2026_guide(self):
        self.assertTrue(has_rule(read("shared/record-activity-admission.md"), "클럽명만", "특기사항은 쓰지 않는다"))
        for name in ("activity-record", "behavior-record"):
            self.assertTrue(has_rule(skill(name), "봉사활동", "쓰지 않는다"), name)
            self.assertTrue(has_rule(skill(name), "작성 주체는 담임교사"), name)

    def test_records_follow_korean_teacher_style(self):
        manifests, _ = build.check(ROOT)
        for name in RECORD_SKILLS:
            examples = re.findall(r"(?:쓸 말|쌓은 문장): `([^`]+)`", skill(name))
            self.assertTrue(examples, name)
            for example in examples:
                self.assertNotRegex(example, AWKWARD, name)
            self.assertIn("references/record-korean-style.md", manifests[name])
            self.assertIn("K1~K7", skill(name))
        for path in sorted((ROOT / "shared").glob("record-*.md")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                found = re.match(r"\s*(?:> |- (?:고친 예|쓸 말|쌓은 문장): )(.*)", line)
                if found:
                    self.assertNotRegex(found[1], NEGATIVE, f"{path.name}:{number}")

    def test_example_length_notes_match_the_sentences(self):
        from neis_bytes import count_bytes, count_chars
        for ref in ("record-examples.md", "record-behavior-activity.md"):
            lines = read(f"shared/{ref}").splitlines()
            for i, line in enumerate(lines):
                if not line.startswith("> ") or i < 2:
                    continue
                head = lines[i - 1] if lines[i - 1].strip() else lines[i - 2]
                both = re.search(r"(\d+)자/(\d+)바이트", head)
                only = re.search(r"\((\d+)바이트", head)
                with self.subTest(ref=ref, line=i + 1):
                    if both:
                        self.assertEqual((int(both[1]), int(both[2])), (count_chars(line[2:]), count_bytes(line[2:])))
                    elif only and head.startswith("**"):
                        self.assertEqual(int(only[1]), count_bytes(line[2:]))

    def test_each_skill_keeps_its_own_part(self):
        self.assertTrue(has_rule(skill("subject-record"), "입력 분량", "막지 않는다"))
        self.assertTrue(has_rule(skill("activity-record"), "월별로 늘어놓지 않는다"))
        self.assertIn("## 6. 행특 작성", skill("behavior-record"))
        for name in ("activity-record", "behavior-record"):
            self.assertNotIn("curriculum-lookup", skill(name))


class ResponsibilityNoticeTest(unittest.TestCase):
    """평가와 학생부는 첫 응답에서 초안과 교사의 책임을 알린다 (승인 문구)."""

    def test_notice_comes_before_the_first_request(self):
        for name in RESPONSIBILITY_SKILLS:
            text = skill(name)
            self.assertIn(APPROVED["책임 안내"], text, name)
            self.assertLess(text.index(APPROVED["책임 안내"]), text.index("## 1."), name)

    def test_assessment_skills_name_what_to_check(self):
        self.assertIn(APPROVED["평가 확인 항목"], skill("assessment-items"))
        self.assertIn(APPROVED["수행평가 확인 항목"], skill("rubric"))
        self.assertNotIn("문항, 정답", skill("rubric").split("## 참고 자료")[0])   # 수행평가에는 문항·정답이 없다

    def test_record_notice_is_skipped_when_work_stops(self):
        for name in RECORD_SKILLS:
            self.assertTrue(has_rule(skill(name), "작업을 멈춘 답변", "쓰지 않"), name)


class FirstRequestTest(unittest.TestCase):
    """첫 응답은 승인받은 짧은 문구로 묻고, 같은 요청을 두 번 하지 않는다."""

    @staticmethod
    def first_request(text: str) -> list[str]:
        """1절 첫 요청 문구의 번호 항목들 (1부터 이어지는 첫 목록만, 뒤의 점검 목록은 빼고)."""
        part = text[text.index("## 1. 한 번에 요청하기"):text.index("\n## 2.")]
        first = []
        for number in re.findall(r"^(?:> )?(\d+)\. ", part, re.M):
            if number != str(len(first) + 1):
                break
            first.append(number)
        return first

    def test_rubric_asks_three_grouped_items_and_defers_the_rest(self):
        text = skill("rubric")
        self.assertEqual(self.first_request(text), ["1", "2", "3"])
        for sentence in ("> 2. 점수: 총점, 평가 영역 수와 영역별 점수", "수행평가에 참여하지 않은 학생의 점수",
                         APPROVED["규정 문장 요청"], APPROVED["기본점수 질문"],
                         APPROVED["나머지 제안"]):
            self.assertIn(sentence, text)
        for old in ("> 4. 미참여 학생 점수", "[2. 점수 구조]", "최저 단계까지 한 학생과"):
            self.assertNotIn(old, text)

    def test_worksheet_and_items_ask_three_grouped_questions(self):
        sheet, items = skill("worksheet"), skill("assessment-items")
        self.assertEqual(self.first_request(sheet), ["1", "2", "3"])
        self.assertEqual(self.first_request(items), ["1", "2", "3"])
        self.assertIn("3. 학생 수준 차이: 같은 쪽 도전 과제 / 기초·기본·심화 따로", sheet)
        self.assertNotIn("어떻게 쓰시나요?", sheet)
        self.assertIn("2. 문항 구성: 총 ○문항 = 선택형 ○문항(○지선다) + 서답형 ○문항 + 서술형 ○문항", items)

    def test_absent_students_get_the_approved_notice(self):
        for name in ("subject-record", "activity-record"):
            self.assertIn(APPROVED["장기결석"], skill(name), name)

    def test_readme_lists_how_to_call_every_skill(self):
        readme = read("README.md")
        for start in ("학습지:", "PPT:", "문항:", "수행평가:", "지도안:", "세특:", "창체:", "행특:"):
            self.assertIn(f"`{start} ", readme)
        self.assertIn("질문 없이 바로 만들어 달라고 하시면 기본값으로 만들고, 쓴 값은 답변 맨 위에 알려 드립니다.", readme)

    def test_rubric_one_line_request_gets_a_default_draft_first(self):
        # 사용자 결정(2026-11-17): 문항 스킬처럼 한 줄 요청이면 기본값 초안을 먼저 만들고 값은 나중에 확인한다
        text = skill("rubric")
        part = text[text.index("## 1. 한 번에 요청하기"):text.index("\n## 2.")]
        start, end = rule_line(part, "한 줄 요청이면", "초안을 먼저 만든다"), rule_line(part, "꼭 확인받아야")
        rule = part[part.index(start):part.index(end)]
        self.assertEqual(missing_rules(rule, {
            "먼저 묻지 않음": ("위 문구로 먼저 묻지 않는다",), "점수 기본값": ("수준별 점수 기본값",),
            "규정 값 비움": ("`○점 [확인 필요]`",), "기본값 자리": ("책임 안내 바로 아래", "기본값으로 정한 내용"),
            "받지 못한 것만": ("받지 못한 항목만", "문구 그대로 묻는다"), "기본값 표시": ("`(기본값)`",),
            "평가계획은 예외": ("평가계획 요청은", "쓰지 않")}), [])
        self.assertTrue(has_rule(part, "초안 뒤에", "네 값", "확인받는다"))
        self.assertNotIn("이 순서로 묻고, 네 값을 받기 전에는 자료를 만들지 않는다.", part)   # 옛 무조건 규칙
        self.assertNotIn("**핵심 수치는 교사에게 묻는다** (질문 없이 진행해 달라고 한 경우만", part)
        self.assertTrue(has_rule(text.split("\n---", 1)[0], "한 줄 요청이면", "초안을 먼저", "묻는다"))
        self.assertTrue(has_rule(text, "학교 규정 값", "제안하지 않는다"))

    def test_lesson_plan_puts_form_and_textbook_in_the_request(self):
        text = skill("lesson-plan")
        self.assertIn("> 3. 쓰시는 학교 양식(hwpx)과 교과서 해당 쪽 PDF", text)
        self.assertIn(APPROVED["질문 없이"], text)
        self.assertTrue(has_rule(text, "후보를 같은 응답에"))
        self.assertNotIn("| 필수 | 선택", text)
        self.assertTrue(has_rule(text, "개수를 줄이지 않고 모두"))
        self.assertTrue(has_rule(text, "해설과 고른 이유는 쓰지 않는다"))

    def test_partial_material_wording_is_fixed(self):
        slides, plan = skill("class-slides"), skill("lesson-plan")
        self.assertTrue(has_rule(slides, "이미 받은 자료는", "1번 괄호에서 빼고"))
        self.assertIn("쓰시는 학교 양식(hwpx) (주시면 그 파일에 내용을 채웁니다. "
                      "hwp 파일이면 한글에서 hwpx로 저장해 주세요)", plan)
        self.assertIn("교과서 해당 쪽 PDF (주시면 내용과 쪽수를 맞춥니다)", plan)
        for text in (slides, plan):
            self.assertTrue(has_rule(text, "문구에 다른 말을 더하지 않는다"))


class TestFindingsTest(unittest.TestCase):
    """교사 요청 시험에서 나온 결함이 다시 생기지 않게 한다."""

    def test_rubric_findings_stay_fixed(self):
        text = skill("rubric")
        self.assertEqual(missing_rules(text, {
            "방식 이름 안 씀": ("방식 이름을 쓰지도 묻지도 않는다",), "점수 겹침": ("같은 점수가 겹치면", "1점씩 내려"),
            "점수 예": ("7 / 6 / 4 / 3",), "질문 3개 이내": ("설계 뒤의 질문은 3개 이내",),
            "성취기준 줄": ("성취기준 줄에는 코드와 문장만",), "차이 다시 묻지 않음": ("이 둘의 차이", "다시 묻지 않는다"),
            "영역별 또는 총점": ("평가 영역마다", "총점 기준")}), [])
        for old in ("- 기본점수: 대체 점수형, 14점", "(학교 방식 표시)", "보여 줄지 교사에게 묻는다"):
            self.assertNotIn(old, text)

    def test_slide_findings_stay_fixed(self):
        text = skill("class-slides")
        self.assertEqual(missing_rules(text, {
            "공개 자료만": ("퍼블릭 도메인", "CC 라이선스"), "원할 때만": ("교사가 원한다고 했을 때만",),
            "표지 노트": ("표지 장의 발표자 노트",), "첫 주기": ("첫 주기", "수업 안내 장"),
            "점검 도구": ("scripts/slide_check.py",)}), [])
        scripts = ROOT / "skills" / "class-slides" / "scripts"
        for name in ("make_deck.py", "make_pptx.py"):
            self.assertIn("polish(deck.prs", (scripts / name).read_text(encoding="utf-8"), name)

    def test_slides_and_records_carry_the_full_standards_data(self):
        manifests, _ = build.check(ROOT)
        self.assertIn("references/curriculum-lookup.md", manifests["class-slides"])
        for name in ("class-slides", "subject-record"):
            self.assertIn("references/curriculum/2022/middle/m001.md", manifests[name], name)

    def test_learning_problem_changes_the_cell_name(self):
        self.assertTrue(has_rule(skill("lesson-plan"), "칸 이름을 `학습 문제`로"))


class AnswerBalanceTest(unittest.TestCase):
    """정기고사 정답 번호는 문항 수와 상관없이 균등하게 맞춘다."""

    def test_rule_is_always_within_one(self):
        checklist = read("shared/checklists/item-quality.md")
        items = skill("assessment-items")
        self.assertTrue(has_rule(items, "번호별 개수 차이", "1을 넘지 않는다"))
        self.assertTrue(has_rule(checklist, "차이가 1을 넘지 않는가"))
        for text in (items, checklist):
            self.assertNotIn("10문항 미만", text)
            self.assertNotIn("절반을 넘지", text)

    def test_pattern_files_do_not_keep_the_old_allowance(self):
        for path in (ROOT / "shared" / "item-patterns").glob("*.md"):
            self.assertNotIn("허용 2", path.read_text(encoding="utf-8"), path.name)


class BuildContentsTest(unittest.TestCase):
    def test_every_script_finds_its_local_imports_in_the_package(self):
        manifests, _ = build.check(ROOT)
        for name, files in manifests.items():
            for target, source in files.items():
                if target.startswith("scripts/") and target.endswith(".py"):
                    with self.subTest(skill=name, script=target):
                        wanted = {f"scripts/{module}.py" for module in local_imports(source)}
                        self.assertLessEqual(wanted, set(files))


class SkillNamesTest(unittest.TestCase):
    def test_removed_skills_are_not_mentioned(self):
        for path in teacher_documents():
            text = path.read_text(encoding="utf-8")
            for name in REMOVED_SKILLS:
                with self.subTest(path=path.name, skill=name):
                    self.assertNotIn(name, text)

    def test_named_skills_exist(self):
        existing = {path.parent.name for path in ROOT.glob("skills/*/SKILL.md")}
        for path in teacher_documents():
            with self.subTest(path=path.name):
                self.assertLessEqual(set(SKILL_MENTION.findall(path.read_text(encoding="utf-8"))), existing)


class SlideDeckExampleTest(unittest.TestCase):
    """앱 슬라이드 예시(deck.css)가 하우스 스타일(글자 40px 이상, 디자인 시스템 색)을 지키고, 정답 안내가 문서에 있다."""

    MIN_BODY_PX = 40
    # 칩·머리말·번호 원처럼 house-style.md 3절이 40px 밑으로 정해 둔 작은 표시 글자
    SMALL_LABELS = {".eyebrow", ".course", ".pg", ".cv-chip", ".chip", ".c-tag", ".reveal-mark", ".now", ".num", ".card-n"}
    HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
    CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
    NUMBER_WORDS = {2: "두", 3: "세", 4: "네", 5: "다섯"}

    @staticmethod
    def class_slides_file(name: str) -> str:
        return read(f"skills/class-slides/references/{name}")

    def deck_css(self) -> str:
        match = re.search(r"```css\n(.*?)\n```", self.class_slides_file("app-deck-example.md"), re.S)
        self.assertIsNotNone(match, "app-deck-example.md에 deck.css 블록이 없음")
        return match.group(1)

    def test_text_is_at_least_40px_except_the_small_labels(self):
        for selectors, body in self.CSS_RULE.findall(self.deck_css()):
            size = re.search(r"font-size:(\d+)px", body)
            if not size or int(size.group(1)) >= self.MIN_BODY_PX:
                continue
            names = {name.strip() for name in selectors.split(",")}
            with self.subTest(selectors=selectors.strip()):
                self.assertTrue(names <= self.SMALL_LABELS, f"{size.group(1)}px는 칩·표시 글자가 아니면 40px 이상이어야 함")

    def test_colors_are_design_system_tokens(self):
        bundle = json.loads(read("shared/teacher-kit-design-system.json"))
        tokens = json.loads(bundle["files"]["tokens.json"])["color"]["tokens"]
        allowed = {token["value"].upper() for token in tokens}
        used = {color.upper() for color in self.HEX.findall(self.deck_css())}
        self.assertLessEqual(used, allowed, f"토큰에 없는 색: {sorted(used - allowed)}")
        self.assertNotIn(".li-off{opacity", self.deck_css())          # 글자를 투명도로 흐리게 하지 않는다

    def test_answer_notice_wording_is_fixed(self):
        slides = self.class_slides_file("app-slides.md")
        self.assertIn("링크와 내려받은 파일에는 정답(클릭해야 나오는 답, 연습 답 장, 발표자 노트)이 들어 있습니다. "
                      "학생에게 나눠 줄 파일이 필요하면 말씀해 주세요. 정답을 뺀 학생용 사본을 만들어 드립니다.", slides)
        self.assertIn("## 7. 학생용 사본 만들기", slides)
        self.assertIn(APPROVED["PPT 정답 안내"], skill("class-slides"))

    def test_guidance_line_count_matches_section_six(self):
        part = self.class_slides_file("app-slides.md").split("## 6.", 1)[1].split("## 7.", 1)[0]
        guidance_lines = len(re.findall(r"^\d+\. ", part, re.M)) - 1      # 첫 항목은 링크
        self.assertIn(f"6절의 링크와 안내 {self.NUMBER_WORDS[guidance_lines]} 줄", skill("class-slides"))

    def test_alignment_rules_are_scoped_to_pptx_generators(self):
        self.assertTrue(has_rule(self.class_slides_file("visual-design.md"), "앱 슬라이드는", "app-slides.md", "우선"))
        self.assertTrue(has_rule(skill("class-slides"), "앱 슬라이드는", "references/house-style.md"))


class SourceSizeTest(unittest.TestCase):
    def test_python_files_stay_within_the_ceiling(self):
        sources = [*ROOT.glob("tools/*.py"), *ROOT.glob("shared/scripts/*.py"), *ROOT.glob("skills/*/scripts/*.py")]
        for path in sources:
            with self.subTest(path=path.name):
                self.assertLessEqual(len(path.read_text(encoding="utf-8").splitlines()), MAX_PYTHON_LINES)


if __name__ == "__main__":
    unittest.main()
