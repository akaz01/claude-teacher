"""표의 쪽 나눔 시험: 행은 쪽 끝에서 쪼개지지 않고, 작은 표는 통째로 넘어가며, 쪽보다 큰 행은 내용이 사라지지 않는다.

한글에서 PDF로 바꿔 확인한 사실: pageBreak="TABLE"에서 한 행이 쪽보다 크면 넘치는 줄이 사라진다.
"""

import re
import tempfile
import unittest
from pathlib import Path
import zipfile

from make_hwpx import build_hwpx


def table_attrs(spec):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.hwpx"
        build_hwpx(spec, path)
        with zipfile.ZipFile(path) as archive:
            section = archive.read("Contents/section0.xml").decode("utf-8")
    return [(m.group(1), m.group(2)) for m in re.finditer(
        r'<hp:tbl [^>]*pageBreak="(\w+)"[^>]*>.*?<hp:pos treatAsChar="(\d)"', section, re.S)]


def table(rows, header=None, **extra):
    return {"type": "table", "rows": rows, **({"header": header} if header else {}), **extra}


class PageBreakTest(unittest.TestCase):
    def test_long_table_keeps_rows_whole(self):
        rows = [[str(i), "내용"] for i in range(40)]
        self.assertEqual(table_attrs({"blocks": [table(rows, ["주", "내용"])]}), [("TABLE", "0")])

    def test_row_taller_than_a_page_splits_inside_the_cell(self):
        tall = "\n".join(f"{i}번째 줄" for i in range(1, 91))
        rows = [["작은 행", "짧음"], ["큰 행", tall], ["끝 행", "마지막"]]
        self.assertEqual(table_attrs({"blocks": [table(rows, ["구분", "내용"])]}), [("CELL", "0")])

    def test_single_row_blank_space_moves_as_one_piece(self):
        # 8줄 풀이 칸이 쪽 끝에서 두 쪽으로 쪼개졌다
        blank = table([[{"text": "", "lines": 8}]])
        self.assertEqual(table_attrs({"blocks": [blank]}), [("NONE", "1")])

    def test_single_row_far_taller_than_half_a_page_may_split(self):
        blank = table([[{"text": "", "lines": 25}]])
        self.assertEqual(table_attrs({"blocks": [blank]}), [("CELL", "0")])      # 내용이 사라지지 않게

    def test_small_headed_table_moves_whole_so_header_never_sits_alone(self):
        # 평가 계획 표의 머리행만 쪽 끝에 남았다
        rows = [["광합성 과정 설명", "활동지", "재료, 에너지, 산물을 이어 광합성 과정을 한 문장으로 설명한다"],
                ["환경 요인", "활동지", "조작 변인, 종속 변인, 통제 변인 세 가지를 모두 설계표에 쓴다"]]
        spec = {"blocks": [table(rows, ["평가 요소", "방법", "상"], widths=[2, 1, 4])]}
        self.assertEqual(table_attrs(spec), [("NONE", "1")])

    def test_big_headed_table_still_splits_between_rows(self):
        rows = [[str(i), "내용 " * 20] for i in range(12)]
        self.assertEqual(table_attrs({"blocks": [table(rows, ["주", "내용"])]}), [("TABLE", "0")])


def section_xml(spec):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.hwpx"
        build_hwpx(spec, path)
        with zipfile.ZipFile(path) as archive:
            return archive.read("Contents/section0.xml").decode("utf-8"), archive.read("Contents/header.xml").decode("utf-8")


class SpacerTest(unittest.TestCase):
    """쪽을 넘어 나뉘는 표 바로 뒤에 소제목이 오면 한글이 '다음 문단과 함께'를 무시해 소제목만 쪽 끝에 남았다.
    사이에 1pt 빈 문단을 두면 소제목이 다음 표와 함께 넘어간다 (한글에서 PDF로 바꿔 확인)."""

    def paragraphs_after_tables(self, spec):
        section, header = section_xml(spec)
        return re.findall(r"</hp:tbl><hp:t/></hp:run></hp:p>(<hp:p [^>]*>.*?</hp:p>)?", section, re.S), header

    def test_split_table_is_followed_by_one_point_spacer(self):
        rows = [[str(i), "내용"] for i in range(40)]
        spec = {"blocks": [table(rows, ["주", "내용"]), {"type": "heading", "text": "평가 계획"}]}
        after, header = self.paragraphs_after_tables(spec)
        spacer_height = re.search(r'<hh:charPr id="(\d+)" height="100"', header)
        self.assertIsNotNone(spacer_height)
        self.assertIn(f'charPrIDRef="{spacer_height.group(1)}"', after[0])

    def test_inline_table_gets_no_spacer(self):
        spec = {"blocks": [table([["1", "가"]], ["a", "b"]), {"type": "heading", "text": "다음"}]}
        after, _ = self.paragraphs_after_tables(spec)
        self.assertIn("다음", after[0])


if __name__ == "__main__":
    unittest.main()
