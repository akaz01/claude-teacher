"""작은 양식에서 선택지 틀을 줄여 쓰는 길의 시험: 다른 유형 틀로 바뀔 때의 참고, 문단 선택지 줄이기."""
import re
import unittest

from test_fill_exam import (CHOICE_NAMES, ExamCase, PEN, blank, choice_paragraphs, combo_table, item_paragraphs,
                            stem)


class ReduceCase(ExamCase):
    def small_form(self, *body: str):
        return self.form(*body, blank())

    def test_reduced_frame_of_another_kind_gets_the_nearest_note(self):
        source = self.small_form(stem(1, "옛 문제 하나의 문장 [3점]"), combo_table(1021), blank())
        item = {"type": "short_table", "stem": "새 문제", "points": 3, "choices": ["가", "나", "다", "라"], "answer": 2}
        xml = self.fill(source, item)
        self.assertIn("④", xml)
        self.assertNotIn("⑤", xml)
        self.assertTrue(any("short_table 틀이 없어 가장 가까운 combo_table 틀을 썼습니다" in note
                            for note in self.outcome.notes), self.outcome.notes)

    def test_reduced_frame_of_the_same_kind_has_no_nearest_note(self):
        source = self.small_form(stem(1, "옛 문제 하나의 문장 [3점]"), combo_table(1021), blank())
        item = {"type": "combo_table", "stem": "새 문제", "points": 3, "choices": ["가", "나", "다", "라"], "answer": 2}
        self.fill(source, item)
        self.assertFalse(any("가장 가까운" in note for note in self.outcome.notes))

    def paragraph_form(self):
        return self.small_form(stem(1, "옛 문제 하나의 문장 [3점]"), *choice_paragraphs(), blank())

    def test_paragraph_choices_shrink_to_four_and_three(self):
        for count in (4, 3):
            with self.subTest(count=count):
                item = item_paragraphs(answer=2)
                item["choices"] = item["choices"][:count]
                self.result.unlink(missing_ok=True)
                xml = self.fill(self.paragraph_form(), item)
                text = re.sub(r"<[^>]+>", "", xml)
                for index, name in enumerate(CHOICE_NAMES):
                    self.assertEqual(name in text, index < count, name)
                self.assertEqual(xml.count(PEN), 1)

    def test_paragraph_choices_refuse_one_choice(self):
        item = item_paragraphs(answer=1)
        item["choices"] = item["choices"][:1]
        self.refused(self.paragraph_form(), {"items": [item]}, "선택지")


if __name__ == "__main__":
    unittest.main()
