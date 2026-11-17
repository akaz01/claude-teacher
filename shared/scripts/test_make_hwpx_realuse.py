"""실사용 시험에서 나온 문제의 회귀 방지: 번호 이어 쓰기, 2단 첫 줄, 문서 정보, 분수 수식."""

import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from make_hwpx import build_hwpx, validate_package

HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
SKELETON_DATE = "2025년 9월 17일 수요일 오후 1:32:50"
KOREAN_DATE = re.compile(r"\d{4}년 \d{1,2}월 \d{1,2}일 [월화수목금토일]요일 (오전|오후) \d{1,2}:\d{2}:\d{2}")


class BuildMixin:
    def build(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "out.hwpx"
        build_hwpx(spec, path)
        self.assertEqual(validate_package(path), [])
        with zipfile.ZipFile(path) as archive:
            return {name: archive.read(name).decode("utf-8")
                    for name in ("Contents/section0.xml", "Contents/content.hpf", "Preview/PrvText.txt")}

    def section(self, spec):
        return self.build(spec)["Contents/section0.xml"]

    def rejected(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with self.assertRaises(ValueError):
            build_hwpx(spec, Path(tmp.name) / "out.hwpx")


class NumberedStartTest(BuildMixin, unittest.TestCase):
    def test_start_continues_numbering_after_a_table(self):
        section = self.section({"blocks": [
            {"type": "numbered", "items": ["가", "나"]},
            {"type": "table", "header": ["a"], "rows": [["1"]]},
            {"type": "numbered", "start": 3, "items": ["다", "라"]},
        ]})
        self.assertIn("3. 다", section)
        self.assertIn("4. 라", section)
        self.assertEqual(section.count("1. 가"), 1)

    def test_default_start_is_one(self):
        self.assertIn("1. 가", self.section({"blocks": [{"type": "numbered", "items": ["가"]}]}))

    def test_start_must_be_positive_integer(self):
        for bad in (0, -1, True, "2", 1.5):
            with self.subTest(start=bad):
                self.rejected({"blocks": [{"type": "numbered", "start": bad, "items": ["가"]}]})


class ColumnSwitchTest(BuildMixin, unittest.TestCase):
    """2단 설정이 빈 문단에 따로 있으면 왼쪽 단만 한 줄 내려가 오른쪽 단과 높이가 어긋났다 (한글에서 확인)."""

    def paragraphs(self, section):
        return list(ElementTree.fromstring(section).iter(f"{HP}p"))

    def test_column_setting_shares_paragraph_with_first_block(self):
        section = self.section({"columns": 2, "blocks": [{"type": "paragraph", "text": "첫 문제"}]})
        holder = [p for p in self.paragraphs(section) if p.find(f".//{HP}colPr[@colCount='2']") is not None]
        self.assertEqual(len(holder), 1)
        self.assertIn("첫 문제", "".join(holder[0].itertext()))

    def test_no_extra_empty_paragraph_in_two_columns(self):
        blocks = [{"type": "paragraph", "text": "가"}, {"type": "paragraph", "text": "나"}]
        one = self.paragraphs(self.section({"blocks": blocks}))
        two = self.paragraphs(self.section({"columns": 2, "blocks": blocks}))
        self.assertEqual(len(one), len(two))

    def test_column_setting_with_table_first_and_header_blocks(self):
        table = {"type": "table", "header": ["a"], "rows": [["1"]]}
        section = self.section({"columns": 2, "header_blocks": 1, "column_line": True, "blocks": [table, table]})
        self.assertEqual(section.count('colCount="2"'), 1)
        self.assertEqual(section.count("<hp:colLine"), 1)

    def test_column_setting_kept_when_nothing_follows(self):
        table = {"type": "table", "header": ["a"], "rows": [["1"]]}
        self.assertIn('colCount="2"', self.section({"columns": 2, "header_blocks": 1, "blocks": [table]}))
        self.assertIn('colCount="2"', self.section({"columns": 2, "blocks": []}))

    def test_page_break_right_after_column_switch(self):
        section = self.section({"columns": 2, "blocks": [{"type": "page_break"}, {"type": "paragraph", "text": "가"}]})
        holder = [p for p in self.paragraphs(section) if p.find(f".//{HP}colPr[@colCount='2']") is not None][0]
        self.assertEqual(holder.get("pageBreak"), "1")
        self.assertIn("가", "".join(holder.itertext()))


class MetadataTest(BuildMixin, unittest.TestCase):
    def meta(self, spec):
        return self.build(spec)["Contents/content.hpf"]

    def test_skeleton_date_replaced_with_build_date(self):
        hpf = self.meta({"blocks": []})
        self.assertNotIn(SKELETON_DATE, hpf)
        date = re.search(r'<opf:meta name="date" content="text">([^<]*)<', hpf).group(1)
        self.assertRegex(date, KOREAN_DATE)

    def test_doc_title_goes_to_metadata_only(self):
        files = self.build({"doc_title": "3학년 분수 학습지", "blocks": [{"type": "paragraph", "text": "가"}]})
        self.assertIn("<opf:title>3학년 분수 학습지</opf:title>", files["Contents/content.hpf"])
        self.assertNotIn("3학년 분수 학습지", files["Contents/section0.xml"])
        self.assertNotIn("3학년 분수 학습지", files["Preview/PrvText.txt"])

    def test_first_heading_used_when_no_title(self):
        hpf = self.meta({"blocks": [{"type": "paragraph", "text": "안내"},
                                    {"type": "heading", "text": "**분수의 덧셈**", "level": 1},
                                    {"type": "heading", "text": "두 번째"}]})
        self.assertIn("<opf:title>분수의 덧셈</opf:title>", hpf)

    def test_title_used_when_present(self):
        hpf = self.meta({"title": "가정통신문", "blocks": [{"type": "heading", "text": "1. 개요"}]})
        self.assertIn("<opf:title>가정통신문</opf:title>", hpf)

    def test_doc_title_must_be_text(self):
        self.rejected({"doc_title": ["목록"], "blocks": []})


class EquationTest(BuildMixin, unittest.TestCase):
    """{{2/3}}은 한글 수식(hp:equation)으로 들어가 분수로 보인다 (한글에서 PDF로 바꿔 확인)."""

    def equations(self, section):
        return list(ElementTree.fromstring(section).iter(f"{HP}equation"))

    def test_inline_fraction_becomes_equation(self):
        files = self.build({"blocks": [{"type": "paragraph", "text": "{{1 7/12}} + {{2/3}}을 계산하시오."}]})
        scripts = [eq.find(f"{HP}script").text for eq in self.equations(files["Contents/section0.xml"])]
        self.assertEqual(scripts, ["1 {7} over {12}", "{2} over {3}"])
        self.assertIn("1 7/12 + 2/3을 계산하시오.", files["Preview/PrvText.txt"])
        self.assertIn("을 계산하시오.", files["Contents/section0.xml"])

    def test_equation_is_inline_with_unique_ids(self):
        section = self.section({"blocks": [
            {"type": "paragraph", "text": "{{1/2}}"},
            {"type": "table", "header": ["답"], "rows": [["{{3/4}}"]]},
        ]})
        equations = self.equations(section)
        self.assertEqual(len(equations), 2)
        self.assertTrue(all(eq.find(f"{HP}pos").get("treatAsChar") == "1" for eq in equations))
        ids = [el.get("id") for el in ElementTree.fromstring(section).iter()
               if el.tag in (f"{HP}equation", f"{HP}tbl")]
        self.assertEqual(len(ids), len(set(ids)))

    def test_raw_equation_script_is_escaped(self):
        section = self.section({"blocks": [{"type": "paragraph", "text": "{{a < b & c}}"}]})
        self.assertEqual(self.equations(section)[0].find(f"{HP}script").text, "a < b & c")

    def test_placeholder_with_hangul_stays_text(self):
        # 남은 자리표시자 {{학생이름}}이 수식으로 바뀌면 빈칸인 줄 모르고 지나친다 (코드 리뷰)
        section = self.section({"blocks": [{"type": "paragraph", "text": "{{학생이름}} 보호자님께"}]})
        self.assertEqual(self.equations(section), [])
        self.assertIn("{{학생이름}} 보호자님께", section)

    def test_braces_do_not_pair_across_lines_and_empty_is_text(self):
        section = self.section({"blocks": [{"type": "paragraph", "text": "a {{ b\nc }} d {{ }}"}]})
        self.assertEqual(self.equations(section), [])

    def test_only_plain_number_fractions_are_converted(self):
        # {{2024/12/25}}가 {2024} over {12}/25로 망가졌다 (코드 리뷰)
        section = self.section({"blocks": [{"type": "paragraph", "text": "{{2024/12/25}} {{3/4 + 1/4}}"}]})
        scripts = [eq.find(f"{HP}script").text for eq in self.equations(section)]
        self.assertEqual(scripts, ["2024/12/25", "{3} over {4} + {1} over {4}"])

    def test_text_without_braces_is_unchanged(self):
        section = self.section({"blocks": [{"type": "paragraph", "text": "2/3 { } {한 쌍}"}]})
        self.assertEqual(self.equations(section), [])
        self.assertIn("2/3 { } {한 쌍}", section)


if __name__ == "__main__":
    unittest.main()
