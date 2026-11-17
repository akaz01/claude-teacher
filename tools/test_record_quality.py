"""학생부 예문 품질 시험: 세 스킬과 학생부 자료의 예문에 부정 서술·어색한 말이 없는지 본다.

tools/test_skill_wiring.py의 NEGATIVE에 이번 재평가에서 찾은 유형을 더한 확장 목록으로 검사한다.
정상 내용("잔반 줄이기", "청년 인구가 줄어든 지역")은 걸리지 않게 낱말을 골랐다.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "shared" / "scripts")]

from test_skill_wiring import NEGATIVE, RECORD_SKILLS  # noqa: E402

# 이전의 부족을 짐작하게 하는 변화의 말
CHANGE_WORDS = r"좋아짐|좋아졌|정확해짐|정확해졌|향상됨|향상되었|향상시|신장됨|늘어 ?감|늘려 감|줄어들었|줄어 ?감"
# 실패→수정 서사, 고치기 전의 잘못
FAILURE_WORDS = (r"처음에는|처음엔|처음 설계한|첫 실험에서|예상과 달|실패|서툴|서툰|치우친 것을 발견|"
                 r"달라지는 점을 발견|지 않자|두 번 다시|도움을 받|질문을 받은 뒤|하게 됨|게 되었")
# 부정문으로 쓴 성실함 ("한 번도 ~하지 않음")
NEGATIVE_FORM = r"빠뜨리지 않|한 번도|미루지 않|넘기지 않|늦지 않|거르지 않|어기지 않"
# 사건 짐작, 다른 학생을 알아볼 단서
EVENT_WORDS = r"갈등|전학 온|사과하|화해|막힌 친구|소외된|이 낮은 (?:팀원|친구|모둠원)"
# 교사 기록 928문장에 드문 말과 의도로 맺는 말 (record-korean-style.md 1장·3장)
STYLE_WORDS = (r"해냄|해내[는고며면]|해 냄|따짐|[가-힣] 감[.,]|[가-힣] 가는 학생|씀[.,]|씀$|"
               r"하려 함|하려고 함|려고 함\.|려 함\.")
# 3차 평가에서 찾은 유형: 근거 없는 평가어, 어색한 보조 동사, 성과 단정, 고치기 전 빈틈을 짐작하게 하는 말,
# 계산기가 바이트를 확인하지 못하는 가운뎃점(예문 본문에서는 쉼표나 '와/과'를 쓴다)
THIRD_WORDS = (r"신뢰를 얻|읽어 ?내|풀어 ?내|다듬|해 나가|해 가며|나가며|늘림|높임|떠받치|완성도를 높|"
               r"보완해|빠진 핵심|·")
EXTRA = "|".join((CHANGE_WORDS, FAILURE_WORDS, NEGATIVE_FORM, EVENT_WORDS, STYLE_WORDS, THIRD_WORDS))
RECORD_BANNED = re.compile(f"{NEGATIVE}|{EXTRA}")

# 시점 표현은 새로 맡은 역할이나 넓힌 활동에만 쓴다 (예: "2학기에는 ~ 역할까지 맡음")
TIME_WORD = re.compile(r"(?:[12]학기|학기 (?:말|후반)|활동 후반|\d+월)(?:에는|부터)")
NEW_ROLE = re.compile(r"맡|까지 확장|범위를 확대|새로")  # 시점 뒤에 새 역할이 오거나, 1학기에 한 일을 2학기에 넓힌 활동

# 예문 줄: `> ` 인용, `- 고친 예:/쓸 말:/쌓은 문장:`, 수준별 예문(`- 상:/중:/하:/노력형:`), 권장 동사 목록
EXAMPLE_LINE = re.compile(r"\s*(?:> |- (?:고친 예|쓸 말|쌓은 문장|상|중|하|노력형|동사): |"
                          r"\*\*자주 쓰는 동사·표현\*\*: )(.*)")
SKILL_EXAMPLE = re.compile(r"(?:쓸 말|쌓은 문장): `([^`]+)`")
META_LINE = re.compile(r"^\*\*|근거와 한계|기재요령|이 파일|예시는|예문의 학생|KICE|학교급 구분")


def shared_examples(text: str) -> list[tuple[int, str]]:
    """학생부 자료의 예문 줄: `> ` 인용 예문과 `- 고친 예:/쓸 말:/쌓은 문장:` 줄. 머리 설명 줄은 뺀다."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        match = EXAMPLE_LINE.match(line)
        if match and not META_LINE.search(match[1]):
            found.append((number, match[1]))
    return found


def skill_examples(text: str) -> list[str]:
    return SKILL_EXAMPLE.findall(text)


def problems(sentence: str) -> list[str]:
    """예문 하나에서 찾은 금지 유형."""
    found = [match[0] for match in RECORD_BANNED.finditer(sentence)]
    for part in re.split(r"(?<=[.])\s", sentence):
        time = TIME_WORD.search(part)
        if time and not NEW_ROLE.search(part[time.end():]) and "1학기에" not in part:
            found.append(f"시점: {time[0]}")
    return found


def record_sources() -> dict[str, str]:
    """검사할 글: 세 스킬 SKILL.md와 shared/record-*.md."""
    sources = {f"skills/{name}/SKILL.md": (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
               for name in RECORD_SKILLS}
    for path in sorted((ROOT / "shared").glob("record-*.md")):
        sources[f"shared/{path.name}"] = path.read_text(encoding="utf-8")
    return sources


def scan(sources: dict[str, str]) -> list[str]:
    """금지 유형이 든 예문을 '파일:줄 낱말' 꼴로 모은다. 이전 판 점검에도 쓴다."""
    hits = []
    for name, text in sources.items():
        if name.startswith("skills/"):
            examples = [(0, sentence) for sentence in skill_examples(text)]
        else:
            examples = shared_examples(text)
        for number, sentence in examples:
            for word in problems(sentence):
                hits.append(f"{name}:{number} {word}")
    return hits


class BannedPatternTest(unittest.TestCase):
    """확장 목록이 잡을 것은 잡고, 정상 내용은 놓아준다."""

    def test_catches_the_reported_types(self):
        for sentence in ("어림하는 감각이 좋아짐.", "표기가 정확해짐.", "전학 온 친구에게 학교를 안내함.",
                         "결과를 연결해 해석하려 함.", "맡은 몫을 해냄.", "방법을 익혀 감.", "방법을 다듬어 감.",
                         "결과 해석을 씀.", "첫 실험에서 시행 횟수가 적어 결과가 한쪽으로 치우친 것을 발견함.",
                         "일을 빠뜨리지 않음.", "친구 사이의 갈등을 조정함.", "풀이가 막힌 친구를 도움.", "물이 모이지 않자 두 번 다시 만듦.",
                         "점검표를 만들어 2학기에는 기한에 맞추어 제출함.", "6월부터 과제를 끝까지 마침.",
                         "요약을 맡은 뒤 발표하기 시작하여 2학기에는 의견을 먼저 냄."):
            with self.subTest(sentence=sentence):
                self.assertTrue(problems(sentence))

    def test_leaves_normal_content_alone(self):
        for sentence in ("학급 회의에서 잔반 줄이기 방안을 제안함.", "청년 인구가 줄어든 지역을 고름.",
                         "2학기에는 모둠의 발표 순서를 정하는 역할까지 맡음.", "기록을 빠짐없이 정리함.",
                         "결과를 근거로 보고서를 작성함.", "학습률을 바꾸어 가며 손실 값을 계산함.",
                         "1학기에 소음을 측정하고, 2학기에는 개선 방법을 조사하여 발표함.",
                         "주간 점검표를 만들어 과제 기한을 스스로 관리하는 습관을 들임."):
            with self.subTest(sentence=sentence):
                self.assertEqual(problems(sentence), [])


class RecordExampleQualityTest(unittest.TestCase):
    """세 스킬의 '쓸 말·쌓은 문장'과 학생부 자료의 예문에 금지 유형이 없다."""

    def test_examples_are_found(self):
        sources = record_sources()
        for name in RECORD_SKILLS:
            self.assertTrue(skill_examples(sources[f"skills/{name}/SKILL.md"]), name)
        self.assertGreaterEqual(len(shared_examples(sources["shared/record-examples.md"])), 40)

    def test_no_banned_types_in_examples(self):
        self.assertEqual(scan(record_sources()), [])


class RecordRuleConsistencyTest(unittest.TestCase):
    """규칙끼리 부딪치지 않고, 기재요령 원문과 맞는다."""

    def setUp(self):
        self.sources = record_sources()
        self.skills = {name: self.sources[f"skills/{name}/SKILL.md"] for name in RECORD_SKILLS}

    def test_club_header_is_left_to_the_system(self):
        activity = self.skills["activity-record"]
        self.assertIn("머리말", activity)
        self.assertIn("바이트에 세지 않는다", activity)
        for name in ("shared/record-examples.md", "shared/record-behavior-activity.md"):
            for number, sentence in shared_examples(self.sources[name]):
                with self.subTest(file=name, line=number):
                    self.assertNotRegex(sentence, r"^\([^)]+\)(?:\(\d+시간\))? ")

    def test_student_number_alone_stops_the_work(self):
        privacy = (ROOT / "shared" / "privacy.md").read_text(encoding="utf-8")
        self.assertNotIn("학번+이름", privacy)
        self.assertIn("학번만 있어도", privacy)
        for name, text in self.skills.items():
            self.assertIn("학번만 있어도", text, name)

    def test_no_unsourced_claims_about_universities(self):
        self.assertNotIn("대학은 이런 결과도 과정 중심의 탐구로 읽는다", self.skills["activity-record"])
        self.assertNotIn("부산대 기준", self.sources["shared/record-behavior-activity.md"])

    def test_behavior_skill_has_one_section_for_each_step(self):
        text = self.skills["behavior-record"]
        self.assertEqual(text.count("여러 학생을 한꺼번에"), 1)
        self.assertEqual(text.count("python scripts/neis_bytes.py"), 1)

    def test_rules_are_split_into_short_items(self):
        for name, text in self.skills.items():
            for line in text.splitlines():
                with self.subTest(skill=name, start=line[:20]):
                    self.assertLess(len(line), 700)

    def test_unrelated_privacy_requests_skip_the_record_form(self):
        text = self.skills["subject-record"]
        branch = text.index("references/privacy-tasks.md` 절차")
        self.assertLess(branch, text.index("학생부 문장을 쓰기 위해"))

    def test_rubric_is_not_said_to_make_a_score_sheet(self):
        for text in (self.skills["subject-record"], self.sources["shared/record-guide.md"]):
            self.assertNotIn("스킬의 채점 기록표", text)


if __name__ == "__main__":
    unittest.main()
