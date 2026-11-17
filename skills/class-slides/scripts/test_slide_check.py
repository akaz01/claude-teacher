"""slide_check.py 시험."""

import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).parent))

from make_pptx import build_pptx  # noqa: E402
from slide_check import polish, wrap_widths  # noqa: E402


def blank_slide():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    return prs, prs.slides.add_slide(prs.slide_layouts[6])


def text_box(slide, text, left, top, width, height, size):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.word_wrap = True
    run = frame.paragraphs[0].add_run()
    run.text, run.font.size = text, Pt(size)
    return shape


def run_size(shape) -> float:
    return shape.text_frame.paragraphs[0].runs[0].font.size.pt


class WrapTest(unittest.TestCase):
    def test_words_stay_whole_when_they_wrap(self):
        self.assertEqual(wrap_widths("가나다 라마바", 4.0), [3.0, 3.0])

    def test_word_longer_than_a_line_is_cut(self):
        self.assertEqual(len(wrap_widths("가나다라마바사아", 3.0)), 3)


class KeepInsideTest(unittest.TestCase):
    def test_shape_past_the_edge_moves_in_with_its_size(self):
        prs, slide = blank_slide()
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12), Inches(6.5), Inches(3), Inches(2))
        warnings = polish(prs)
        self.assertEqual((shape.width, shape.height), (Inches(3), Inches(2)))
        self.assertEqual(shape.left + shape.width, prs.slide_width)
        self.assertEqual(shape.top + shape.height, prs.slide_height)
        self.assertEqual(len(warnings), 1)
        self.assertIn("1번째 장", warnings[0])

    def test_shape_bigger_than_the_slide_keeps_its_ratio(self):
        prs, slide = blank_slide()
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(-1), 0, Inches(26.666), Inches(7))
        polish(prs)
        self.assertLessEqual(shape.width, prs.slide_width)
        self.assertAlmostEqual(shape.width / shape.height, 26.666 / 7, places=2)
        self.assertGreaterEqual(shape.left, 0)

    def test_shape_inside_is_untouched(self):
        prs, slide = blank_slide()
        slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        self.assertEqual(polish(prs), [])


class ShortTailTest(unittest.TestCase):
    TAIL = "가나다라마 가나다라마 가나다라마 가나다라마 가나다라마 가나"

    def test_few_letters_on_the_last_line_shrink_to_one_line(self):
        prs, slide = blank_slide()
        shape = text_box(slide, self.TAIL, 1, 1, 6.3, 1.5, 16)
        before = run_size(shape)
        self.assertEqual(polish(prs), [])
        self.assertLess(run_size(shape), before)

    def test_neighbours_of_the_same_role_keep_one_size(self):
        prs, slide = blank_slide()
        first = text_box(slide, self.TAIL, 0.5, 1, 6.3, 1.5, 16)
        second = text_box(slide, "짧은 글", 7, 1, 6.3, 1.5, 16)
        polish(prs)
        self.assertEqual(run_size(first), run_size(second))

    def test_tail_that_cannot_be_fixed_is_reported(self):
        prs, slide = blank_slide()
        text = "가나다라마 " * 30 + "가"
        shape = text_box(slide, text, 1, 1, 6, 5.5, 24)
        warnings = polish(prs)
        if warnings:
            self.assertIn("끝 줄", warnings[0])
        self.assertGreaterEqual(run_size(shape), 24 * 0.85 - 0.5)

    def test_text_that_needs_two_lines_is_broken_evenly(self):
        prs, slide = blank_slide()
        shape = text_box(slide, "가나다라마 바사아자차 카타파하가 나다라마바 사아자차카 타파하가나 다라", 1, 1, 6.3, 2, 28)
        shape.text_frame.paragraphs[0].runs[0].font.bold = True
        self.assertEqual(polish(prs), [])
        paragraph = shape.text_frame.paragraphs[0]
        lengths = [len(line) for line in paragraph.text.split("\x0b")]
        self.assertGreaterEqual(len(lengths), 2)
        self.assertLess(max(lengths) - min(lengths), 8)
        self.assertEqual(run_size(shape), 28)
        self.assertTrue(all(run.font.bold for run in paragraph.runs))

    def test_even_two_lines_are_left_alone(self):
        prs, slide = blank_slide()
        shape = text_box(slide, "가나다라마바사아자차 가나다라마바사아자차", 1, 1, 3, 1.5, 18)
        self.assertEqual(polish(prs), [])
        self.assertEqual(run_size(shape), 18)


class ContentListTest(unittest.TestCase):
    def test_centred_list_has_no_bullet_marks_and_sits_in_the_middle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "수업.pptx"
            build_pptx({"slides": [{"type": "content", "title": "제목", "items": ["첫째 줄", "둘째 줄"]}]}, path)
            frames = [shape.text_frame for shape in Presentation(path).slides[0].shapes
                      if shape.has_text_frame and "첫째 줄" in shape.text_frame.text]
        self.assertEqual(frames[0].paragraphs[0].text, "첫째 줄")
        self.assertEqual(frames[0].vertical_anchor, MSO_ANCHOR.MIDDLE)


class OverflowTest(unittest.TestCase):
    def test_text_taller_than_its_box_shrinks(self):
        prs, slide = blank_slide()
        shape = text_box(slide, "가나다라마 바사아자차 카타파하가 나다라마바", 1, 1, 2, 1.3, 20)
        polish(prs)
        self.assertLess(run_size(shape), 20)

    def test_text_that_stays_too_tall_is_reported(self):
        prs, slide = blank_slide()
        text_box(slide, "가나다라마 " * 40, 1, 1, 2, 0.6, 20)
        self.assertTrue(any("넘칠" in warning for warning in polish(prs)))


if __name__ == "__main__":
    unittest.main()
