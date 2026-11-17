"""수식 안내 문서가 스킬에 이어지고, 실사용 시험에서 나온 안내가 들어 있는지 확인한다."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build  # noqa: E402

GUIDE = ROOT / "shared" / "equations.md"
EQUATION_SKILLS = ("worksheet", "assessment-items", "lesson-plan")
SHORT_TABLE_WORDS = ("over", "sqrt", "lim", "int", "inf", "LEQ")


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


class EquationGuideTest(unittest.TestCase):
    def test_guide_has_the_short_table(self):
        text = GUIDE.read_text(encoding="utf-8")
        for word in SHORT_TABLE_WORDS:
            self.assertIn(word, text, word)

    def test_guide_states_the_rules(self):
        text = GUIDE.read_text(encoding="utf-8")
        for rule in ("한글이 섞이면", "LaTeX", "x^{n+1}", "넓게"):
            self.assertIn(rule, text, rule)

    def test_every_equation_skill_points_to_the_guide(self):
        for name in EQUATION_SKILLS:
            self.assertIn("references/equations.md", skill_text(name), name)

    def test_guide_reaches_each_skill_zip_without_passing_the_file_limit(self):
        manifests, errors = build.check(ROOT)
        for name in EQUATION_SKILLS:
            self.assertIn("references/equations.md", manifests[name], name)
        self.assertEqual([e for e in errors if "파일" in e and "개" in e], [])

    def test_worksheet_skill_says_wide_cells_and_no_latex(self):
        text = skill_text("worksheet")
        self.assertIn("수식이 든 칸은 넓게", text)
        self.assertIn("LaTeX", text)


class WorksheetCheckTest(unittest.TestCase):
    def test_check_list_asks_to_recompute_the_answers(self):
        text = skill_text("worksheet")
        section = text[text.index("## 5. 점검"):text.index("## 6. 파일 만들기")]
        self.assertRegex(section, r"정답을 다시 풀어 검산")


if __name__ == "__main__":
    unittest.main()
