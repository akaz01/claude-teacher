"""lesson-plan 스킬의 문구, 예시 JSON, 역량·핵심 아이디어 자료가 약속대로인지 본다."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))

import build  # noqa: E402
from make_hwpx import CELL_PADDING_X, build_hwpx, validate_package  # noqa: E402
from skill_rules import has_rule  # noqa: E402

SKILL_DIR = ROOT / "skills" / "lesson-plan"
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
WIDE_FORM_REF = "references/lesson-plan-wide-form.md"   # 드물게 쓰는 넓은 지도안 예시는 본문에서 이 파일로 옮겼다
WIDE_FORM = (SKILL_DIR / WIDE_FORM_REF).read_text(encoding="utf-8")
COMPETENCIES = ROOT / "shared" / "subject-competencies.md"
CORE_IDEAS = ROOT / "shared" / "curriculum" / "core-ideas"
CONTENT_ELEMENTS = ROOT / "shared" / "curriculum" / "content-elements"
MIDDLE_SCIENCE = ROOT / "shared" / "curriculum" / "2022" / "middle" / "m001.md"
NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
TIME_LABEL_WIDTH = 4000  # "시간(분)"이 한 줄에 드는 폭: 한글 3자 3000 + 괄호 2개 1000


def example_spec() -> dict:
    match = re.search(r"```json\n(.*?)```", WIDE_FORM, re.DOTALL)
    return json.loads(match.group(1))


def example_tables(spec: dict) -> list[dict]:
    return [block for block in spec["blocks"] if block["type"] == "table"]


def body_cells(table: dict):
    for row in table["rows"][table.get("header_rows", 0):]:
        yield from row


class KeptPromisesTest(unittest.TestCase):
    def test_opening_notice_and_page_range_question_stay(self):
        self.assertIn("양식은 그 파일에 내용을 채우고", SKILL)
        self.assertIn("교과서 몇 쪽부터 몇 쪽까지 지도안에 담을까요?", SKILL)

    def test_school_form_comes_first(self):
        self.assertIn("초등교육과 게시물", SKILL)
        self.assertIn("학교 양식이 우선", SKILL)

    def test_table_text_is_centered_by_default(self):
        self.assertTrue(has_rule(SKILL, "표 안 글자", "가운데 정렬", "기본"))


class DesignRulesTest(unittest.TestCase):
    def test_design_order_comes_before_the_tables(self):
        order = SKILL.index("## 3. 설계 순서")
        self.assertLess(order, SKILL.index("### 5-2. 교수·학습 활동표"))
        for step in ("평가 요소", "탐구 질문", "도달의 증거", "정리에서 탐구 질문"):
            self.assertIn(step, SKILL[order:order + 900])

    def test_fake_inquiry_question_forms_are_banned(self):
        self.assertIn("~을 이해하는가?", SKILL)
        self.assertIn("~할 수 있는가?", SKILL)
        self.assertTrue(has_rule(SKILL, "탐구 질문일 필요는 없다"))

    def test_form_fields_of_2022(self):
        for field in ("교수·학습 모형", "내용 영역", "핵심 아이디어", "학습 주제", "학습 형태",
                      "보편적 학습 설계", "채점 기준표"):
            self.assertIn(field, SKILL)

    def test_content_area_and_assessment_area_are_told_apart(self):
        self.assertIn("평가 영역", SKILL)
        self.assertIn("references/performance-levels.md", SKILL)

    def test_adverb_only_levels_are_gone(self):
        self.assertNotIn("정확하고 명확하게", SKILL)
        self.assertNotIn("부분적으로 ~함", SKILL)
        self.assertIn("단계 수", SKILL)

    def test_page_split_guidance_reports_what_hangul_does(self):
        self.assertIn("쪽 경계에서 갈라", WIDE_FORM)
        self.assertIn("page_break", WIDE_FORM)

    def test_header_rows_explanation_matches_generator(self):
        line = next(text for text in WIDE_FORM.splitlines() if text.startswith("- `header_rows`"))
        self.assertIn("`rows`", line)
        self.assertIn("`header`", line)

    def test_rare_wide_form_path_lives_in_its_reference(self):
        part = SKILL[SKILL.index("## 9. 파일 만들기"):SKILL.index("## 10.")]
        self.assertIn(WIDE_FORM_REF, part)
        self.assertNotIn("```json", SKILL)                 # 긴 JSON 예시는 본문에 두지 않는다
        self.assertIn("scripts/make_hwpx.py", WIDE_FORM)
        files, errors = build.collect_dependencies(ROOT, SKILL_DIR)
        self.assertEqual(errors, [])
        self.assertIn("scripts/make_hwpx.py", files)


class ExampleJsonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = example_spec()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "lesson.hwpx"
        build_hwpx(cls.spec, cls.path)
        with zipfile.ZipFile(cls.path) as archive:
            cls.section = ElementTree.fromstring(archive.read("Contents/section0.xml"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_example_builds_a_valid_file(self):
        self.assertEqual(validate_package(self.path), [])

    def test_activity_table_has_seven_columns(self):
        activity = next(t for t in example_tables(self.spec) if t.get("header_rows") == 2)
        self.assertEqual(len(activity["widths"]), 7)

    def test_time_column_fits_its_label_on_one_line(self):
        for cell in self.section.iter(f"{{{NS['hp']}}}tc"):
            if "".join(cell.itertext()) == "시간(분)":
                width = int(cell.find("hp:cellSz", NS).get("width"))
                self.assertGreaterEqual(width, TIME_LABEL_WIDTH + CELL_PADDING_X)
                return
        self.fail("시간(분) 칸이 없음")

    def test_body_cells_are_centered(self):
        for table in example_tables(self.spec):
            for cell in body_cells(table):
                self.assertIsInstance(cell, dict, cell)
                self.assertEqual(cell.get("align"), "center", cell)

    def test_blackboard_example_is_filled_in(self):
        blocks = self.spec["blocks"]
        heading = next(i for i, block in enumerate(blocks) if block.get("text") == "판서 계획")
        self.assertEqual(blocks[heading + 1]["type"], "table")

    def test_example_matches_the_2022_standard(self):
        data = MIDDLE_SCIENCE.read_text(encoding="utf-8")
        text = json.dumps(self.spec, ensure_ascii=False)
        sentence = re.search(r"\| \[9과04-01\] \| (.+?) \|", data).group(1)
        self.assertIn(f"[9과04-01] {sentence}", text)
        self.assertNotIn("물질의 구성", text)


class ExampleLayoutTest(unittest.TestCase):
    """실사용 시험: 예시에 쪽 설정과 내용 요소 행이 빠져 지도안이 3쪽이 되고 내용 요소가 비었다."""

    def test_example_uses_compact_page_so_plan_fits_two_pages(self):
        self.assertEqual(example_spec().get("page"), "compact")

    def test_skill_explains_page_values(self):
        self.assertIn('"page": "compact"', SKILL)
        self.assertIn("normal", SKILL[SKILL.index("## 9. 파일 만들기"):])

    def test_header_table_lists_content_elements_row(self):
        table = SKILL[SKILL.index("### 5-1."):SKILL.index("### 5-2.")]
        self.assertRegex(table, r"\| 내용 요소 \|")
        self.assertLess(table.index("| 핵심 아이디어 |"), table.index("| 내용 요소 |"))
        self.assertLess(table.index("| 내용 요소 |"), table.index("| 성취기준 |"))

    def test_json_example_has_content_elements_row(self):
        head = example_tables(example_spec())[0]
        labels = [row[0]["text"] for row in head["rows"]]
        self.assertEqual(labels.index("내용 요소"), labels.index("핵심 아이디어") + 1)
        text = "".join(cell["text"] for cell in head["rows"][labels.index("내용 요소")] if isinstance(cell, dict))
        self.assertIn("입자 운동", text)        # 중학교 1~3학년 '물질' 영역의 내용 요소 (content-elements/science.md)

    def test_skill_points_to_equation_guide(self):
        self.assertIn("references/equations.md", SKILL)


class CompetencyFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = COMPETENCIES.read_text(encoding="utf-8")

    def test_official_names(self):
        for name in ("비판적⋅창의적 사고 역량", "디지털⋅미디어 역량", "자기 성찰⋅계발 역량",
                     "문제해결, 추론, 의사소통, 연결, 정보처리", "영어 의사소통 역량",
                     "문제 해결력 및 의사 결정력", "정보 활용 능력"):
            self.assertIn(name, self.text)

    def test_unconfirmed_subjects_stay_marked(self):
        for subject in ("과학", "역사"):
            line = next(row for row in self.text.splitlines() if row.startswith(f"| {subject} |"))
            self.assertIn("[확인 필요]", line)

    def test_research_proposal_names_are_not_listed_as_official(self):
        self.assertNotIn("과학 가치 인식", self.text)

    def test_skill_points_to_the_file(self):
        self.assertIn("references/subject-competencies.md", SKILL)


class CoreIdeaDataTest(unittest.TestCase):
    FILES = {"korean.md": "국어", "math.md": "수학", "english.md": "영어",
             "social.md": "사회", "science.md": "과학"}

    def test_each_file_names_its_source_and_has_sentences(self):
        for name, subject in self.FILES.items():
            text = (CORE_IDEAS / name).read_text(encoding="utf-8")
            self.assertIn("교육부 고시 제2022-33호", text)
            self.assertIn(f"## {subject} (공통 교육과정)", text)
            self.assertGreater(len(re.findall(r"^- .+$", text, re.MULTILINE)), 50)

    def test_known_sentence_for_the_example_area(self):
        text = (CORE_IDEAS / "science.md").read_text(encoding="utf-8")
        self.assertIn("### 물질", text)
        self.assertIn("물질은 여러 가지 상태로 존재하며, 구성 입자의 운동에 따라 물질의 상태와 물리적 성질이 변한다.", text)

    def test_wrapped_lines_keep_word_spacing(self):
        text = (CORE_IDEAS / "math.md").read_text(encoding="utf-8")
        self.assertIn("이때 연산의 성질이 일관되게 성립한다.", text)

    def test_names_are_ascii_for_upload(self):
        for path in CORE_IDEAS.iterdir():
            self.assertTrue(path.name.isascii(), path.name)


SCIENCE_ELECTIVES = ("전문 수학", "이산 수학", "고급 대수", "고급 미적분", "고급 기하", "고급 물리학", "고급 화학",
                     "고급 생명과학", "고급 지구과학", "과학과제 연구", "정보과학", "물리학 실험", "화학 실험",
                     "생명과학 실험", "지구과학 실험")


def parse_content_elements(path: Path) -> list[tuple[str, str, str, str, str]]:
    """내용 요소 파일을 (과목, 영역, 구분, 학년군 칸, 항목) 목록으로 읽는다.

    들여쓴 줄이 아래에 이어지는 `- 칸 이름` 줄은 칸 이름이고, 이어지지 않는 줄은 칸 이름 없는 항목이다.
    """
    records: list[tuple[str, str, str, str, str]] = []
    subject = area = group = label = ""
    pending: tuple[str, str, str, str] | None = None   # 아직 칸 이름인지 항목인지 모르는 줄
    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        nested = line.startswith("  - ")
        if pending and not nested:
            records.append((*pending[:3], "", pending[3]))
            pending = None
        if nested and group:
            pending = None   # 바로 위 줄은 칸 이름이었다
            records.append((subject, area, group, label, line[4:].strip()))
            continue
        if line.startswith("## "):
            subject, area, group, label = line[3:].strip(), "", "", ""
        elif line.startswith("### "):
            area = re.sub(r"\s*\(원문 [^)]*\)$", "", line[4:].strip())
            area = "" if area == "영역 구분 없음" else area
            group = label = ""
        elif line.startswith("#### "):
            group, label = line[5:].strip(), ""
        elif line.startswith("- ") and group:
            label = line[2:].strip()
            pending = (subject, area, group, label)
    return records


class ContentElementDataTest(unittest.TestCase):
    FILES = {"korean.md": ("국어", 5), "math.md": ("수학", 8), "english.md": ("영어", 14),
             "social.md": ("사회", 7), "science.md": ("과학", 9)}
    # 원문 추출본(한글 문서를 PDF로 낸 글, 배포 PDF)과 맞춰 본 표본 25곳
    SAMPLES = (
        ("korean.md", "국어 (공통 교육과정)", "문법", "지식·이해", "초등학교 5∼6학년", "글과 담화의 시간 표현"),
        ("korean.md", "국어 (공통 교육과정)", "듣기⋅말하기", "과정·기능", "초등학교 1∼2학년", "일이 일어난 순서에 따라 조직하기"),
        ("korean.md", "국어 (공통 교육과정)", "읽기", "가치·태도", "초등학교 1∼2학년", "읽기에 대한 흥미"),
        ("korean.md", "국어 (공통 교육과정)", "읽기", "지식·이해", "초등학교 5∼6학년", "다양한 설명 방법을 활용하여 주제를 제시한 글"),
        ("social.md", "사회 (공통 교육과정)", "지속가능한 세계", "지식·이해", "초등학교 3~4학년", "살기 좋은 환경과 삶의 질"),
        ("social.md", "사회 (공통 교육과정)", "지리 인식", "과정·기능", "중학교 1~3학년", "지리적 질문이나 주제에 적합한 데이터, 지리 정보를 수집하고 비교분석하기"),
        ("social.md", "사회 (공통 교육과정)", "역사 일반", "가치·태도", "중학교 1~3학년", "타인의 역사적 해석을 존중하는 태도"),
        ("social.md", "사회 (공통 교육과정)", "정치", "지식·이해", "초등학교 5~6학년", "지구촌의 평화"),
        ("math.md", "수학 (공통 교육과정)", "도형과 측정", "지식·이해", "초등학교 1~2학년", "입체도형의 모양"),
        ("math.md", "수학 (공통 교육과정)", "변화와 관계", "과정·기능", "중학교 1~3학년", "방정식과 부등식 풀기"),
        ("math.md", "수학 (공통 교육과정)", "자료와 가능성", "가치·태도", "중학교 1~3학년", "확률 및 통계적 근거를 바탕으로 비판적으로 사고하는 태도"),
        ("math.md", "수학 (공통 교육과정)", "수와 연산", "지식·이해", "초등학교 1~2학년", "네 자리 이하의 수"),
        ("science.md", "과학 (공통 교육과정)", "운동과 에너지", "지식·이해", "중학교 1~3학년", "중력에 의한 위치 에너지"),
        ("science.md", "과학 (공통 교육과정)", "물질", "과정·기능", "중학교 1~3학년", "관찰, 측정, 분류, 예상, 추리 등을 통해 자료를 수집하고 비교⋅분석하기"),
        ("science.md", "과학 (공통 교육과정)", "물질", "과정·기능", "중학교 1~3학년", "탐구 결과를 해석하여 결론을 도출하기"),
        ("science.md", "과학 (공통 교육과정)", "생명", "지식·이해", "초등학교 3~4학년군", "특징에 따른 식물 분류"),
        ("english.md", "영어 (공통 교육과정)", "이해(reception)", "지식·이해", "초등학교 5~6학년", "정보 전달⋅교환 목적의 담화와 글(공지, 안내, 묘사, 설명, 광고 등)"),
        ("english.md", "영어 (공통 교육과정)", "이해(reception)", "과정·기능", "중학교 1~3학년", "주제 파악하기"),
        ("english.md", "영어 (공통 교육과정)", "표현(production)", "가치·태도", "중학교 1~3학년", "상대방을 배려하며 말하거나 쓰는 태도"),
        ("english.md", "영어 (공통 교육과정)", "이해(reception)", "지식·이해", "초등학교 5~6학년", "의견 전달⋅교환이나 주장 목적의 담화와 글(포스터, 감상문 등)"),
        ("science.md", "고급 지구과학", "", "지식·이해", "", "대기 안정도"),
        ("science.md", "생명과학 실험", "", "과정·기능", "", "생명과학 실험 설계 및 수행하기"),
        ("science.md", "지구과학 실험", "", "가치·태도", "", "과학의 심미적 가치"),
        ("science.md", "전문 수학", "", "지식·이해", "", "삼각함수의 활용"),
        ("science.md", "고급 대수", "", "과정·기능", "", "선형변환을 행렬로 표현하기"),
    )

    def text(self, name: str) -> str:
        return (CONTENT_ELEMENTS / name).read_text(encoding="utf-8")

    def test_five_subject_files_exist_with_ascii_names_and_sane_size(self):
        self.assertEqual(sorted(path.name for path in CONTENT_ELEMENTS.iterdir()), sorted(self.FILES))
        for path in CONTENT_ELEMENTS.iterdir():
            self.assertTrue(path.name.isascii(), path.name)
            self.assertLess(path.stat().st_size, 200_000, path.name)

    def test_each_file_names_its_source_and_pages(self):
        for name, (subject, booklet) in self.FILES.items():
            text = self.text(name)
            self.assertIn("교육부 고시 제2022-33호", text)
            self.assertIn(f"[별책 {booklet}]", text)
            self.assertIn(f"## {subject} (공통 교육과정)", text)
            self.assertRegex(text, r"### .+ \(원문 \d+(~\d+)?쪽\)")
            self.assertIn("boardSeq=93458", text)

    def test_every_area_block_has_the_three_groups(self):
        for name in self.FILES:
            blocks = re.split(r"^### ", self.text(name), flags=re.MULTILINE)[1:]
            self.assertGreater(len(blocks), 10, name)
            for block in blocks:
                title = block.splitlines()[0]
                for group in ("#### 지식·이해", "#### 과정·기능", "#### 가치·태도"):
                    self.assertIn(group, block, f"{name}: {title}")

    def test_no_conversion_leftovers(self):
        for name in self.FILES:
            text = self.text(name)
            for marker in ("{?", "{중첩표}", "[수식:"):
                self.assertNotIn(marker, text, name)

    def test_subject_names_match_the_core_ideas_files(self):
        for name in self.FILES:
            ours = {line[3:].strip() for line in self.text(name).splitlines()
                    if line.startswith("## ") and "([별책 20])" not in line}
            core = {line[3:].strip() for line in (CORE_IDEAS / name).read_text(encoding="utf-8").splitlines()
                    if line.startswith("## ")}
            self.assertEqual(ours, core, name)

    def test_science_electives_are_in_both_core_ideas_and_content_elements(self):
        core = (CORE_IDEAS / "science.md").read_text(encoding="utf-8")
        elements = self.text("science.md")
        self.assertIn("[별책 20]", core)
        self.assertIn("[별책 20]", elements)
        for subject in SCIENCE_ELECTIVES:
            self.assertIn(f"## {subject}\n", core, subject)
            self.assertIn(f"## {subject}\n", elements, subject)
        self.assertIn("삼각함수와 미적분", elements)      # 전문 수학 범주
        self.assertIn("n차원 벡터공간은 n개의 기저벡터를 통하여 설명되며", core)  # 수식을 글자로 바꾼 곳

    def test_samples_sit_under_the_right_subject_area_group_and_column(self):
        self.assertGreaterEqual(len(self.SAMPLES), 20)
        parsed = {name: parse_content_elements(CONTENT_ELEMENTS / name) for name in self.FILES}
        for name, subject, area, group, label, item in self.SAMPLES:
            self.assertIn((subject, area, group, label, item), parsed[name], (name, subject, area, item))

    def test_merged_and_empty_cells_are_called_out(self):
        social = self.text("social.md")
        self.assertIn("원문 칸에 ‘-’만 적혀 있음", social)
        self.assertIn("범주에 걸친 칸", social)
        self.assertIn("(칸 합침)", self.text("science.md"))
        self.assertIn("원문 칸이 비어 있음", self.text("science.md"))

    def test_readme_states_the_real_numbers(self):
        readme = (ROOT / "shared" / "curriculum" / "README.md").read_text(encoding="utf-8")
        core_total = sum(len(re.findall(r"^- .+$", (CORE_IDEAS / name).read_text(encoding="utf-8")[
            (CORE_IDEAS / name).read_text(encoding="utf-8").index("\n## "):], re.MULTILINE)) for name in self.FILES)
        self.assertIn(f"{core_total}개", readme)       # 핵심 아이디어 문장 수
        notes = re.compile(r"원문 칸에|원문 칸이|합쳐진 칸|걸친 칸\)?$")
        item_total = sum(1 for name in self.FILES for record in parse_content_elements(CONTENT_ELEMENTS / name)
                         if not notes.search(record[4]))
        self.assertIn(f"{item_total:,}개", readme)      # 내용 요소 항목 수
        self.assertEqual(item_total, 4062)

    def test_skill_points_to_the_data(self):
        self.assertIn("references/curriculum/content-elements/", SKILL)
        self.assertNotIn("내용 요소 데이터는 없으므로", SKILL)
        self.assertIn("[확인 필요]", SKILL)


class PackagingTest(unittest.TestCase):
    def test_lesson_plan_zip_gets_the_new_files(self):
        files, errors = build.collect_dependencies(ROOT, SKILL_DIR)
        self.assertEqual(errors, [])
        for wanted in ("references/subject-competencies.md", "references/performance-levels.md",
                       "references/curriculum/core-ideas/science.md",
                       *(f"references/curriculum/content-elements/{name}"
                         for name in ("korean.md", "math.md", "english.md", "social.md", "science.md"))):
            self.assertIn(wanted, files)

    def test_lesson_plan_stays_under_the_upload_file_limit(self):
        manifests, _ = build.check(ROOT)
        self.assertLessEqual(len(manifests["lesson-plan"]), build.MAX_SKILL_FILES)


if __name__ == "__main__":
    unittest.main()
