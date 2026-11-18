"""문제지 블록(stem, choices, box) 시험: 문두 내어쓰기, 배점 묶음, 선지 열 맞춤, 상자 위치."""

import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from make_hwpx import build_hwpx, validate_package
from make_hwpx_exam import CHOICE_HANG, STEM_HANG

PARA_ID = r'<hp:p id="[1-9]\d*" paraPrIDRef="(\d+)"'


def build(blocks, **extra):
    spec = {"page": "sheet", "columns": 2, **extra, "blocks": blocks}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.hwpx"
        warnings = build_hwpx(spec, path)
        problems = validate_package(path)
        with zipfile.ZipFile(path) as archive:
            return (archive.read("Contents/section0.xml").decode(), archive.read("Contents/header.xml").decode(),
                    warnings, problems)


def para_pr(header, para_id):
    return re.search(rf'<hh:paraPr id="{para_id}".*?</hh:paraPr>', header, re.S).group(0)


def table_info(section):
    return [(int(m.group(1)), int(m.group(2)), [int(w) for w in re.findall(r'<hp:cellSz width="(\d+)"', m.group(0))])
            for m in re.finditer(r'<hp:tbl [^>]*rowCnt="(\d+)" colCnt="(\d+)".*?</hp:tbl>', section, re.S)]


def choices(items, layout="auto"):
    return build([{"type": "choices", "items": items, "layout": layout}])


class StemTest(unittest.TestCase):
    def test_second_line_hangs_one_em_and_justifies_and_keeps_with_next(self):
        section, header, _, problems = build([{"type": "stem", "number": 1, "text": "문두", "points": 3}])
        self.assertEqual(problems, [])
        pr = para_pr(header, re.findall(PARA_ID, section)[0])
        self.assertIn('horizontal="JUSTIFY"', pr)
        self.assertIn(f'<hc:intent value="-{STEM_HANG}"', pr)
        self.assertIn('<hc:left value="0"', pr)  # 한글 내어쓰기: 첫 줄 제자리
        self.assertIn('keepWithNext="1"', pr)
        self.assertIn('keepLines="1"', pr)

    def test_points_follow_last_word_with_plain_space(self):
        section = build([{"type": "stem", "number": 2, "text": "옳은 것은?", "points": 3.2}])[0]
        self.assertIn("옳은 것은? [3.2점]", section)
        self.assertNotIn("<hp:nbSpace/>[3.2점]", section)
        self.assertIn("[3점]", build([{"type": "stem", "text": "가", "points": 3}])[0])

    def test_points_already_in_text_keep_plain_space(self):
        self.assertIn("것은? [4점]", build([{"type": "stem", "text": "것은?  [4점]"}])[0])

    def test_points_in_text_must_match_points_key(self):
        self.assertIn("것은? [4점]", build([{"type": "stem", "text": "것은? [4점]", "points": 4}])[0])
        with self.assertRaises(ValueError):
            build([{"type": "stem", "text": "것은? [3점]", "points": 5}])

    def test_bad_points_rejected(self):
        with self.assertRaises(ValueError):
            build([{"type": "stem", "text": "가", "points": "삼"}])

    def test_keep_with_next_can_be_turned_off(self):
        section, header, _, _ = build([{"type": "stem", "text": "가", "keep_with_next": False}])
        self.assertIn('keepWithNext="0"', para_pr(header, re.findall(PARA_ID, section)[0]))


class ChoicesTest(unittest.TestCase):
    def test_one_row_of_five_equal_columns_starting_at_baseline(self):
        section, header, _, problems = choices(["1", "2", "3", "4", "5"], "1x5")
        self.assertEqual(problems, [])
        rows, cols, widths = table_info(section)[0]
        self.assertEqual((rows, cols), (1, 5))
        self.assertLessEqual(max(widths) - min(widths), 4)
        self.assertIn(f'<hc:left value="{STEM_HANG}"', para_pr(header, re.findall(PARA_ID, section)[0]))
        self.assertIn('<hp:outMargin left="0"', section)

    def test_three_plus_two_uses_thirds_and_pads_last_row(self):
        section = choices(["ㄱ", "ㄴ", "ㄷ", "ㄱ, ㄴ", "ㄴ, ㄷ"], "2x3")[0]
        rows, cols, widths = table_info(section)[0]
        self.assertEqual((rows, cols), (2, 3))
        self.assertEqual(len(widths), 6)
        self.assertLessEqual(max(widths) - min(widths), 4)

    def test_one_per_line(self):
        rows, cols, _ = table_info(choices(["가", "나", "다", "라", "마"], "5x1")[0])[0]
        self.assertEqual((rows, cols), (5, 1))

    def test_wrapped_choice_aligns_after_marker(self):
        section, header, _, _ = choices(["가", "나"], "5x1")
        ids = set(re.findall(PARA_ID, section))
        self.assertTrue(any(f'<hc:intent value="-{CHOICE_HANG}"' in para_pr(header, i)
                            and '<hc:left value="0"' in para_pr(header, i) for i in ids))

    def test_marker_added_and_glued_but_existing_marker_kept(self):
        section = choices(["가", "② 나"], "5x1")[0]
        self.assertIn("①<hp:nbSpace/>가", section)
        self.assertIn("②<hp:nbSpace/>나", section)
        self.assertNotIn("②<hp:nbSpace/>②", section)

    def test_auto_picks_narrowest_layout_that_fits(self):
        self.assertEqual(table_info(choices(["1", "2", "3", "4", "5"])[0])[0][:2], (1, 5))
        self.assertEqual(table_info(choices(["ㄱ, ㄴ", "ㄱ, ㄷ", "ㄴ, ㄷ", "ㄱ, ㄴ, ㄷ", "ㄴ"])[0])[0][:2], (2, 3))
        self.assertEqual(table_info(choices(["이 문장은 훨씬 더 길어서 한 줄에 하나씩 놓여야 한다"] * 5)[0])[0][:2], (5, 1))

    def test_four_choices_spread_over_four_columns(self):
        self.assertEqual(table_info(choices(["1", "2", "3", "4"])[0])[0][:2], (1, 4))

    def test_explicit_layout_too_narrow_warns(self):
        warnings = choices(["이 문장은 훨씬 더 길어서 칸을 넘는다"] * 5, "1x5")[2]
        self.assertTrue(any("칸보다 길어" in w for w in warnings))

    def test_borderless(self):
        section, header, _, _ = choices(["1", "2"], "1x5")
        border = re.search(r'<hp:tbl [^>]*borderFillIDRef="(\d+)"', section).group(1)
        fill = re.search(rf'<hh:borderFill id="{border}".*?</hh:borderFill>', header, re.S).group(0)
        self.assertIn('type="NONE"', fill)

    def test_count_validated(self):
        with self.assertRaises(ValueError):
            choices(["하나"])


class BoxTest(unittest.TestCase):
    def test_box_runs_from_baseline_to_column_end(self):
        section, header, _, problems = build([{"type": "box", "label": "<보 기>", "paragraphs": ["ㄱ. 가", "ㄴ. 나"]}])
        self.assertEqual(problems, [])
        rows, cols, widths = table_info(section)[0]
        self.assertEqual((rows, cols), (1, 1))
        column = (59528 - 2 * 2834 - 2268) // 2
        self.assertEqual(widths[0], column - STEM_HANG)
        pr = para_pr(header, re.findall(PARA_ID, section)[0])
        self.assertIn(f'<hc:left value="{STEM_HANG}"', pr)
        self.assertIn('keepWithNext="1"', pr)

    def test_marker_paragraph_hangs(self):
        section, header, _, _ = build([{"type": "box", "paragraphs": ["ㄱ. 가", "줄글"]}])
        ids = set(re.findall(PARA_ID, section))
        self.assertTrue(any('<hc:intent value="-1760"' in para_pr(header, i) for i in ids))

    def test_empty_box_rejected(self):
        with self.assertRaises(ValueError):
            build([{"type": "box", "paragraphs": []}])


class WholeItemTest(unittest.TestCase):
    def test_full_item_builds_with_no_problems_and_old_blocks_still_work(self):
        blocks = [{"type": "stem", "number": 1, "text": "다음 중 옳은 것은?", "points": 3},
                  {"type": "box", "paragraphs": ["자료"]},
                  {"type": "choices", "items": ["가", "나", "다", "라", "마"]},
                  {"type": "paragraph", "text": "그냥 문단", "align": "left"}]
        self.assertEqual(build(blocks)[3], [])


if __name__ == "__main__":
    unittest.main()
