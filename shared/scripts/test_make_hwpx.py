import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from make_hwpx import PARA_STYLES, build_hwpx, validate_package

NS = {
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
}

SPEC = {
    "title": "2학년 현장체험학습 안내",
    "blocks": [
        {"type": "heading", "text": "1. 개요", "level": 1},
        {"type": "paragraph", "text": "준비물은 **도시락**과 물입니다. A&B <확인>"},
        {"type": "bullets", "items": ["모자", "운동화"]},
        {"type": "numbered", "items": ["출발", "도착"]},
        {"type": "table", "header": ["구분", "내용"], "rows": [["일시", "11. 10.(화)"], ["장소", "과학관\n2층"]],
         "widths": [1, 3]},
        {"type": "page_break"},
        {"type": "paragraph", "text": "회신란"},
        {"type": "answer_box", "lines": 3},
        {"type": "blank"},
    ],
}


class HwpxTestCase(unittest.TestCase):
    spec = SPEC

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "out.hwpx"
        build_hwpx(cls.spec, cls.path)
        with zipfile.ZipFile(cls.path) as archive:
            cls.infos = archive.infolist()
            cls.header_xml = archive.read("Contents/header.xml").decode("utf-8")
            cls.section_xml = archive.read("Contents/section0.xml").decode("utf-8")
            cls.content_hpf = archive.read("Contents/content.hpf").decode("utf-8")
            cls.preview = archive.read("Preview/PrvText.txt").decode("utf-8")
        cls.header = ElementTree.fromstring(cls.header_xml)
        cls.section = ElementTree.fromstring(cls.section_xml)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class PackageTest(HwpxTestCase):
    def test_mimetype_is_first_and_stored(self):
        first = self.infos[0]
        self.assertEqual(first.filename, "mimetype")
        self.assertEqual(first.compress_type, zipfile.ZIP_STORED)
        with zipfile.ZipFile(self.path) as archive:
            self.assertEqual(archive.read("mimetype"), b"application/hwp+zip")

    def test_validate_package_reports_no_problems(self):
        self.assertEqual(validate_package(self.path), [])

    def test_title_written_to_metadata_and_preview(self):
        self.assertIn("<opf:title>2학년 현장체험학습 안내</opf:title>", self.content_hpf)
        self.assertIn("2학년 현장체험학습 안내", self.preview)


class HeaderTest(HwpxTestCase):
    def test_item_counts_match_children(self):
        for container in ("borderFills", "charProperties", "paraProperties"):
            element = self.header.find(f".//hh:{container}", NS)
            self.assertEqual(int(element.get("itemCnt")), len(list(element)), container)

    def test_malgun_gothic_added_to_every_font_group(self):
        groups = self.header.findall(".//hh:fontface", NS)
        self.assertEqual(len(groups), 7)
        for group in groups:
            faces = [font.get("face") for font in group.findall("hh:font", NS)]
            self.assertIn("맑은 고딕", faces)
            self.assertEqual(int(group.get("fontCnt")), len(faces))


class SectionTest(HwpxTestCase):
    def paragraphs(self):
        return self.section.findall(".//hp:p", NS)

    def char_pr(self, char_id):
        return self.header.find(f".//hh:charPr[@id='{char_id}']", NS)

    def test_first_paragraph_carries_section_properties(self):
        first = self.section.find("hp:p", NS)
        self.assertIsNotNone(first.find(".//hp:secPr", NS))
        self.assertIn("2학년 현장체험학습 안내", "".join(first.itertext()))

    def test_generated_paragraphs_have_no_layout_cache(self):
        self.assertIsNone(self.section.find(".//hp:linesegarray", NS))

    def test_paragraph_ids_are_unique(self):
        ids = [p.get("id") for p in self.paragraphs()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_bold_markup_uses_bold_char_property(self):
        bold_runs = [
            run for run in self.section.findall(".//hp:run", NS)
            if "".join(run.itertext()) == "도시락"
        ]
        self.assertEqual(len(bold_runs), 1)
        self.assertIsNotNone(self.char_pr(bold_runs[0].get("charPrIDRef")).find("hh:bold", NS))

    def test_special_characters_round_trip(self):
        self.assertIn("A&B <확인>", "".join(self.section.itertext()))

    def test_bullets_and_numbers_prefixed(self):
        text = [("".join(p.itertext())) for p in self.paragraphs()]
        self.assertIn("• 모자", text)
        self.assertIn("2. 도착", text)

    def test_table_dimensions_and_widths(self):
        table = self.section.findall(".//hp:tbl", NS)[0]
        rows = table.findall("hp:tr", NS)
        self.assertEqual(int(table.get("rowCnt")), 3)
        self.assertEqual(int(table.get("colCnt")), 2)
        table_width = int(table.find("hp:sz", NS).get("width"))
        for row in rows:
            widths = [int(cell.find("hp:cellSz", NS).get("width")) for cell in row.findall("hp:tc", NS)]
            self.assertEqual(sum(widths), table_width)
        first_row_widths = [int(c.find("hp:cellSz", NS).get("width")) for c in rows[0].findall("hp:tc", NS)]
        self.assertAlmostEqual(first_row_widths[1] / first_row_widths[0], 3, delta=0.01)

    def test_header_row_is_shaded(self):
        table = self.section.findall(".//hp:tbl", NS)[0]
        header_cell = table.find("hp:tr/hp:tc", NS)
        fill = self.header.find(f".//hh:borderFill[@id='{header_cell.get('borderFillIDRef')}']", NS)
        self.assertIsNotNone(fill.find(".//hc:winBrush", NS))
        self.assertNotEqual(fill.find(".//hc:winBrush", NS).get("faceColor"), "none")

    def test_newline_in_cell_becomes_line_break(self):
        self.assertIn("과학관<hp:lineBreak/>2층", self.section_xml)

    def test_page_break_applies_to_next_paragraph(self):
        flagged = [p for p in self.paragraphs() if p.get("pageBreak") == "1"]
        self.assertEqual(["회신란"], ["".join(p.itertext()) for p in flagged])

    def test_answer_box_is_single_bordered_cell(self):
        box = self.section.findall(".//hp:tbl", NS)[1]
        self.assertEqual((box.get("rowCnt"), box.get("colCnt")), ("1", "1"))

    def test_answer_box_moves_to_next_page_instead_of_splitting(self):
        tables = self.section.findall(".//hp:tbl", NS)
        self.assertEqual(tables[1].get("pageBreak"), "NONE")
        # 작은 표도 글자처럼 취급해 통째로 옮긴다. 긴 표만 나뉜다 (test_long_table_floats_...)
        self.assertEqual(tables[0].get("pageBreak"), "NONE")


LESSON_TABLE = {
    "type": "table", "header_rows": 2, "widths": [9, 35, 35, 6, 15],
    "rows": [
        [{"text": "단계", "rowspan": 2}, {"text": "교수·학습 활동", "colspan": 2},
         {"text": "시간", "rowspan": 2}, {"text": "자료 및 유의점", "rowspan": 2}],
        ["교사", "학생"],
        [{"text": "도입", "rowspan": 2}, "동기 유발", "경험 발표", "3'", "▣ 사진"],
        ["학습 문제 확인", "읽기", "2'", ""],
        [{"text": "판서 계획", "shade": True, "align": "center"}, {"text": "", "colspan": 4, "lines": 4}],
    ],
}


class MergedTableTest(unittest.TestCase):
    """지도안처럼 칸을 합친 표 (HTML 표와 같은 방식: 합쳐져 가려진 칸은 생략)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "lesson.hwpx"
        build_hwpx({"blocks": [LESSON_TABLE]}, cls.path)
        with zipfile.ZipFile(cls.path) as archive:
            cls.section = ElementTree.fromstring(archive.read("Contents/section0.xml"))
            cls.header = ElementTree.fromstring(archive.read("Contents/header.xml"))
        cls.table = cls.section.find(".//hp:tbl", NS)
        cls.rows = cls.table.findall("hp:tr", NS)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cell(self, row: int, index: int):
        return self.rows[row].findall("hp:tc", NS)[index]

    def test_package_is_valid(self):
        self.assertEqual(validate_package(self.path), [])

    def test_covered_cells_are_omitted(self):
        self.assertEqual([len(r.findall("hp:tc", NS)) for r in self.rows], [4, 2, 5, 4, 2])
        self.assertEqual((self.table.get("rowCnt"), self.table.get("colCnt")), ("5", "5"))

    def test_spans_and_addresses(self):
        first = self.cell(0, 0)
        self.assertEqual(first.find("hp:cellSpan", NS).get("rowSpan"), "2")
        activity = self.cell(0, 1)
        self.assertEqual(activity.find("hp:cellSpan", NS).get("colSpan"), "2")
        student = self.cell(1, 1)
        self.assertEqual(student.find("hp:cellAddr", NS).attrib, {"colAddr": "2", "rowAddr": "1"})
        time_in_row3 = self.cell(3, 2)
        self.assertEqual(time_in_row3.find("hp:cellAddr", NS).get("colAddr"), "3")

    def test_merged_width_is_sum_of_columns(self):
        widths = [int(c.find("hp:cellSz", NS).get("width")) for c in self.rows[2].findall("hp:tc", NS)]
        merged = int(self.cell(0, 1).find("hp:cellSz", NS).get("width"))
        self.assertEqual(merged, widths[1] + widths[2])

    def test_header_rows_are_shaded_and_marked(self):
        for row in self.rows[:2]:
            for cell in row.findall("hp:tc", NS):
                self.assertEqual(cell.get("header"), "1")
        self.assertEqual(self.cell(2, 1).get("header"), "0")
        self.assertNotEqual(self.cell(0, 0).get("borderFillIDRef"), self.cell(2, 1).get("borderFillIDRef"))

    def test_per_cell_shade_option(self):
        self.assertEqual(self.cell(4, 0).get("borderFillIDRef"), self.cell(0, 0).get("borderFillIDRef"))

    def test_lines_option_makes_tall_writing_row(self):
        heights = [int(r.findall("hp:tc", NS)[-1].find("hp:cellSz", NS).get("height")) for r in self.rows]
        self.assertGreater(heights[4], heights[3] * 3)


class MergedTableErrorTest(unittest.TestCase):
    def build(self, rows):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        build_hwpx({"blocks": [{"type": "table", "rows": rows}]}, Path(tmp.name) / "x.hwpx")

    def test_rowspan_past_bottom_rejected(self):
        with self.assertRaises(ValueError):
            self.build([[{"text": "a", "rowspan": 3}, "b"], ["c"]])

    def test_row_with_wrong_cell_count_after_spans_rejected(self):
        with self.assertRaises(ValueError) as caught:
            self.build([[{"text": "a", "rowspan": 2}, "b"], ["c", "d"]])
        self.assertIn("2행", str(caught.exception))

    def test_bad_span_value_rejected(self):
        with self.assertRaises(ValueError):
            self.build([[{"text": "a", "colspan": 0}]])


class OfficialFormatTest(unittest.TestCase):
    """가정통신문·공문 조사에서 나온 기능: 한국식 항목 번호, 테두리 없는 표, 글자 크기, 밑줄."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "letter.hwpx"
        build_hwpx({"blocks": [
            {"type": "outline", "items": [
                {"text": "목적", "level": 1}, {"text": "세부 목적", "level": 2}, {"text": "더 세부", "level": 3},
                {"text": "두 번째 세부", "level": 2}, {"text": "방침", "level": 1}, {"text": "방침 세부", "level": 2}]},
            {"type": "table", "border": "none", "rows": [["교훈", "가정통신문", "담당"]]},
            {"type": "paragraph", "text": "○○초등학교장", "size": "large", "align": "center"},
            {"type": "paragraph", "text": "회신은 __10. 20.(화)까지__ 해 주세요."},
        ]}, cls.path)
        with zipfile.ZipFile(cls.path) as archive:
            cls.section = ElementTree.fromstring(archive.read("Contents/section0.xml"))
            cls.header = ElementTree.fromstring(archive.read("Contents/header.xml"))
        cls.texts = ["".join(p.itertext()) for p in cls.section.findall(".//hp:p", NS)]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def char_pr_of_run(self, text):
        run = next(r for r in self.section.findall(".//hp:run", NS) if "".join(r.itertext()) == text)
        return self.header.find(f".//hh:charPr[@id='{run.get('charPrIDRef')}']", NS)

    def test_package_is_valid(self):
        self.assertEqual(validate_package(self.path), [])

    def test_outline_uses_korean_markers_and_restarts_sub_levels(self):
        for expected in ("1. 목적", "가. 세부 목적", "1) 더 세부", "나. 두 번째 세부", "2. 방침", "가. 방침 세부"):
            self.assertIn(expected, self.texts)

    def test_outline_levels_are_indented_more(self):
        paragraphs = {"".join(p.itertext()): p for p in self.section.findall(".//hp:p", NS)}
        level1 = paragraphs["1. 목적"].get("paraPrIDRef")
        level2 = paragraphs["가. 세부 목적"].get("paraPrIDRef")
        self.assertNotEqual(level1, level2)

    def test_borderless_table_uses_fill_without_borders(self):
        table = self.section.find(".//hp:tbl", NS)
        fill = self.header.find(f".//hh:borderFill[@id='{table.find('.//hp:tc', NS).get('borderFillIDRef')}']", NS)
        self.assertEqual(fill.find("hh:leftBorder", NS).get("type"), "NONE")

    def test_large_paragraph_uses_bigger_font(self):
        self.assertGreater(int(self.char_pr_of_run("○○초등학교장").get("height")), 1100)

    def test_double_underscore_marks_bold_underline(self):
        char = self.char_pr_of_run("10. 20.(화)까지")
        self.assertIsNotNone(char.find("hh:bold", NS))
        self.assertEqual(char.find("hh:underline", NS).get("type"), "BOTTOM")
        self.assertIn("회신은 10. 20.(화)까지 해 주세요.", self.texts)


class OptionsTest(unittest.TestCase):
    def build(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "out.hwpx"
        build_hwpx(spec, path)
        with zipfile.ZipFile(path) as archive:
            return path, archive.read("Contents/section0.xml").decode("utf-8")

    def build_header(self, spec):
        path, _ = self.build(spec)
        with zipfile.ZipFile(path) as archive:
            return path, archive.read("Contents/header.xml").decode("utf-8")

    def test_tables_flow_inline_so_they_stay_with_the_question(self):
        # 떠 있는 표(treatAsChar=0)는 앞 문단의 keepWithNext가 적용되지 않아 문제와 답 칸이 다른 쪽에 놓였다
        _, section = self.build({"blocks": [
            {"type": "heading", "text": "5. 서술하시오.", "level": 2}, {"type": "answer_box", "lines": 3},
            {"type": "table", "header": ["a"], "rows": [["1"]]}]})
        self.assertNotIn('treatAsChar="0"', section)
        self.assertEqual(section.count('treatAsChar="1"'), 2)

    def test_long_table_floats_so_it_can_split_across_pages(self):
        # 글자처럼 취급한 표는 쪽을 넘어 나뉘지 않아 긴 진도표가 통째로 다음 쪽으로 밀렸다
        rows = [[str(i), "내용"] for i in range(30)]
        _, section = self.build({"blocks": [{"type": "table", "header": ["주", "내용"], "rows": rows}]})
        self.assertIn('treatAsChar="0"', section)
        self.assertIn('pageBreak="TABLE"', section)     # 행은 쪽 경계에서 쪼개지지 않고 통째로 넘어간다

    def test_keep_with_next_paragraph_stays_with_following_choices(self):
        # 2단 시험지에서 문제 문장은 왼쪽 단 끝, 선지는 오른쪽 단 위로 갈라졌다
        path, section = self.build({"blocks": [
            {"type": "paragraph", "text": "1. 문제", "align": "left", "keep_with_next": True},
            {"type": "paragraph", "text": "① 가", "align": "left"}]})
        with zipfile.ZipFile(path) as archive:
            header = archive.read("Contents/header.xml").decode("utf-8")
        ids = re.findall(r'<hp:p id="\d+" paraPrIDRef="(\d+)"', section)
        keep = lambda pid: re.search(  # noqa: E731
            rf'<hh:paraPr id="{pid}" (?:(?!</hh:paraPr>).)*?keepWithNext="(\d)"', header, re.S).group(1)
        self.assertEqual([keep(pid) for pid in ids[-2:]], ["1", "0"])

    def test_single_cell_table_with_long_text_floats(self):
        # 행 수만 보면 짧은 표지만 긴 지문이 들어 있으면 쪽을 넘어 나뉠 수 있어야 한다 (안 그러면 잘림)
        passage = "가나다라마바사아자차 " * 300
        _, section = self.build({"blocks": [{"type": "table", "rows": [[passage]]}]})
        self.assertIn('treatAsChar="0"', section)

    def test_table_keep_with_next_keeps_wrapper_paragraph(self):
        path, section = self.build({"blocks": [
            {"type": "table", "rows": [["<보 기>"]], "keep_with_next": True},
            {"type": "paragraph", "text": "① 가", "align": "left"}]})
        with zipfile.ZipFile(path) as archive:
            header = archive.read("Contents/header.xml").decode("utf-8")
        wrapper = re.search(r'<hp:p id="\d+" paraPrIDRef="(\d+)"[^>]*><hp:run[^>]*><hp:tbl', section).group(1)
        self.assertRegex(header, rf'<hh:paraPr id="{wrapper}" (?:(?!</hh:paraPr>).)*keepWithNext="1"')

    def test_backslash_becomes_fullwidth_so_korean_fonts_do_not_show_won_sign(self):
        # 맑은 고딕 등 한글 글꼴은 역슬래시(U+005C)를 ₩로 그린다 ("주기 \ 족" → "주기 ₩ 족")
        _, section = self.build({"blocks": [{"type": "table", "rows": [["주기 \\ 족"]]},
                                            {"type": "paragraph", "text": "a\\b"}]})
        self.assertNotIn("\\", section)
        self.assertIn("주기 ＼ 족", section)
        self.assertIn("a＼b", section)

    def test_paragraphs_do_not_split_across_pages(self):
        _, header = self.build_header({"blocks": [{"type": "paragraph", "text": "가"}]})
        # 골격 파일의 기존 문단 모양은 그대로 두고, 생성기가 더한 문단 모양만 문단 보호를 켠다
        self.assertGreaterEqual(header.count('keepLines="1"'), len(PARA_STYLES))

    def test_outline_start_continues_numbering_after_a_table(self):
        _, section = self.build({"blocks": [
            {"type": "outline", "items": ["운영 개요"]},
            {"type": "table", "header": ["a"], "rows": [["1"]]},
            {"type": "outline", "start": 2, "items": ["추진 일정", {"text": "세부", "level": 2}]},
        ]})
        self.assertIn("2. 추진 일정", section)
        self.assertIn("가. 세부", section)

    def test_outline_start_must_be_positive_integer(self):
        with self.assertRaises(ValueError):
            self.build({"blocks": [{"type": "outline", "start": 0, "items": ["가"]}]})

    def test_narrow_margins(self):
        _, section = self.build({"margins": "narrow", "blocks": [{"type": "paragraph", "text": "가"}]})
        margin = re.search(r"<hp:pagePr[^>]*><hp:margin ([^/]*)/>", section).group(1)
        self.assertIn('left="4252"', margin)
        self.assertIn('right="4252"', margin)

    def test_two_columns_sets_column_count_and_halves_table_width(self):
        table = {"type": "table", "header": ["a"], "rows": [["1"]]}
        _, one = self.build({"blocks": [table]})
        path, two = self.build({"columns": 2, "blocks": [table]})
        self.assertIn('colCount="2"', two)
        width = lambda xml: int(re.search(r'<hp:sz width="(\d+)"', xml).group(1))  # noqa: E731
        self.assertLess(width(two), width(one) / 2)
        self.assertEqual(validate_package(path), [])

    def test_header_blocks_stay_full_width_before_two_columns(self):
        table = {"type": "table", "header": ["a"], "rows": [["1"]]}
        path, xml = self.build({"columns": 2, "header_blocks": 1, "blocks": [table, table]})
        widths = [int(w) for w in re.findall(r'<hp:sz width="(\d+)"', xml)]
        self.assertGreater(widths[0], widths[1] * 2)
        first_paragraph = xml.split("</hp:p>")[0]
        self.assertIn('colCount="1"', first_paragraph)
        self.assertEqual(xml.count('colCount="2"'), 1)
        self.assertEqual(validate_package(path), [])

    def test_generated_paragraph_styles_wrap_korean_by_word(self):
        # 한글에서 BREAK_WORD가 어절 단위, KEEP_WORD는 글자 단위 줄바꿈이다 (한글 기본 문단도 BREAK_WORD)
        _, header_xml = self.build_header({"blocks": [{"type": "paragraph", "text": "가"}]})
        header = ElementTree.fromstring(header_xml)
        skeleton_count = 20
        generated = [p for p in header.findall(".//hh:paraPr", NS) if int(p.get("id")) >= skeleton_count]
        self.assertTrue(generated)
        for para in generated:
            self.assertEqual(para.find("hh:breakSetting", NS).get("breakNonLatinWord"), "BREAK_WORD")

    def test_rejects_unsupported_column_count(self):
        with self.assertRaises(ValueError):
            self.build({"columns": 3, "blocks": []})

    def test_document_without_title_is_valid(self):
        path, _ = self.build({"blocks": [{"type": "paragraph", "text": "본문만"}]})
        self.assertEqual(validate_package(path), [])

    def test_rejects_row_with_wrong_cell_count(self):
        with self.assertRaises(ValueError):
            self.build({"blocks": [{"type": "table", "header": ["a", "b"], "rows": [["1"]]}]})

    def test_rejects_unknown_block_type(self):
        with self.assertRaises(ValueError):
            self.build({"blocks": [{"type": "image"}]})

    # --- 코드 리뷰에서 나온 입력 경계 사례 ---

    def test_widths_count_must_match_columns(self):
        for widths in ([1, 2], [1, 2, 3, 4]):
            with self.assertRaises(ValueError):
                self.build({"blocks": [{"type": "table", "header": ["a", "b", "c"], "rows": [], "widths": widths}]})

    def test_none_and_numbers_are_accepted_as_text(self):
        path, xml = self.build({"title": 2026, "blocks": [
            {"type": "paragraph", "text": None}, {"type": "heading", "text": 3},
            {"type": "table", "header": ["a", "b"], "rows": [[None, 7]]}]})
        self.assertEqual(validate_package(path), [])
        self.assertNotIn("<hp:t>None", xml)  # dropcapstyle="None"은 한글 속성이므로 글자 칸만 본다
        self.assertIn("<hp:t>7</hp:t>", xml)

    def test_title_with_control_character_is_valid(self):
        path, _ = self.build({"title": "가\x0b나", "blocks": []})
        self.assertEqual(validate_package(path), [])

    def test_null_blocks_and_rows_are_treated_as_empty(self):
        path, _ = self.build({"blocks": None})
        self.assertEqual(validate_package(path), [])
        path, _ = self.build({"blocks": [{"type": "table", "header": ["a"], "rows": None}]})
        self.assertEqual(validate_package(path), [])

    def test_error_names_the_block_number(self):
        with self.assertRaises(ValueError) as caught:
            self.build({"blocks": [{"type": "blank"}, {"type": "table", "header": ["a", "b"], "rows": [["1"]]}]})
        self.assertIn("2번째", str(caught.exception))

    def test_failed_validation_leaves_no_output_file(self):
        from unittest import mock
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "out.hwpx"
        with mock.patch("make_hwpx.validate_package", return_value=["가짜 문제"]):
            with self.assertRaises(RuntimeError):
                build_hwpx({"blocks": []}, path)
        self.assertEqual(list(Path(tmp.name).iterdir()), [])

    def test_check_of_missing_file_reports_problem(self):
        self.assertTrue(validate_package(Path("없는파일.hwpx")))

    def test_bold_can_span_line_break(self):
        _, xml = self.build({"blocks": [{"type": "paragraph", "text": "**가\n나**"}]})
        self.assertNotIn("**", xml)


class PageLayoutOptionsTest(unittest.TestCase):
    """쪽 번호(꼬리말 "1 / 4"), 2단 구분선, 가로 용지. 한글에서 PDF로 바꿔 확인한 형태."""

    TABLE = {"type": "table", "header": ["a", "b"], "rows": [["1", "2"]]}

    def build(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "out.hwpx"
        build_hwpx(spec, path)
        with zipfile.ZipFile(path) as archive:
            section = archive.read("Contents/section0.xml").decode("utf-8")
            header = ElementTree.fromstring(archive.read("Contents/header.xml"))
        self.assertEqual(validate_package(path), [])
        return section, header

    def assert_rejected(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with self.assertRaises(ValueError):
            build_hwpx(spec, Path(tmp.name) / "out.hwpx")

    def footer(self, section_xml):
        first = ElementTree.fromstring(section_xml).find("hp:p", NS)
        return first.find(".//hp:footer", NS)

    def footer_align(self, spec):
        section, header = self.build(spec)
        para_id = self.footer(section).find(".//hp:p", NS).get("paraPrIDRef")
        return header.find(f".//hh:paraPr[@id='{para_id}']/hh:align", NS).get("horizontal")

    def test_page_numbers_add_footer_with_page_and_total(self):
        section, _ = self.build({"page_numbers": "center", "blocks": [{"type": "paragraph", "text": "가"}]})
        footer = self.footer(section)
        self.assertIsNotNone(footer)
        kinds = [num.get("numType") for num in footer.iter(f"{{{NS['hp']}}}autoNum")]
        self.assertEqual(kinds, ["PAGE", "TOTAL_PAGE"])
        self.assertIn(" / ", "".join(footer.itertext()))

    def test_page_number_alignment(self):
        self.assertEqual(self.footer_align({"page_numbers": "center", "blocks": []}), "CENTER")
        self.assertEqual(self.footer_align({"page_numbers": "right", "blocks": []}), "RIGHT")

    def test_no_footer_by_default(self):
        section, _ = self.build({"blocks": []})
        self.assertNotIn("hp:footer", section)
        section, _ = self.build({"page_numbers": None, "blocks": []})
        self.assertNotIn("hp:footer", section)

    def test_page_number_paragraph_ids_stay_unique(self):
        section, _ = self.build({"page_numbers": "right", "title": "제목", "blocks": [self.TABLE]})
        ids = [p.get("id") for p in ElementTree.fromstring(section).iter(f"{{{NS['hp']}}}p")]
        self.assertEqual(len(ids), len(set(ids)))

    def test_rejects_unknown_page_number_position(self):
        self.assert_rejected({"page_numbers": "left", "blocks": []})

    def test_column_line_goes_on_two_column_part_only(self):
        section, _ = self.build({"columns": 2, "column_line": True, "blocks": [self.TABLE]})
        two = re.search(r'<hp:colPr [^>]*colCount="2"[^>]*>(.*?)</hp:colPr>', section)
        self.assertIsNotNone(two)
        self.assertIn('<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/>', two.group(1))
        self.assertEqual(section.count("<hp:colLine"), 1)

    def test_no_column_line_by_default(self):
        section, _ = self.build({"columns": 2, "blocks": [self.TABLE]})
        self.assertNotIn("colLine", section)

    def test_column_line_needs_two_columns(self):
        self.assert_rejected({"column_line": True, "blocks": []})

    def test_landscape_rotates_paper_like_hancom(self):
        # 한글이 가로 용지를 저장하는 방식: 용지 크기는 세로 그대로 두고 landscape="NARROWLY"
        section, _ = self.build({"orientation": "landscape", "blocks": [self.TABLE]})
        self.assertIn('<hp:pagePr landscape="NARROWLY" width="59528" height="84186"', section)

    def test_landscape_table_fills_wider_body(self):
        width = lambda xml: int(re.search(r'<hp:sz width="(\d+)"', xml).group(1))  # noqa: E731
        portrait, _ = self.build({"blocks": [self.TABLE]})
        landscape, _ = self.build({"orientation": "landscape", "blocks": [self.TABLE]})
        self.assertEqual(width(portrait), 59528 - 2 * 8504 - 2 * 283)
        self.assertEqual(width(landscape), 84186 - 2 * 8504 - 2 * 283)

    def test_portrait_is_default(self):
        section, _ = self.build({"orientation": "portrait", "blocks": []})
        self.assertIn('<hp:pagePr landscape="WIDELY" width="59528" height="84186"', section)

    def test_rejects_unknown_orientation(self):
        self.assert_rejected({"orientation": "sideways", "blocks": []})

    def test_explicit_defaults_match_absent_keys(self):
        spec = {"title": "제목", "columns": 2, "blocks": [self.TABLE]}
        plain, _ = self.build(spec)
        explicit, _ = self.build({**spec, "page_numbers": None, "column_line": False, "orientation": "portrait"})
        self.assertEqual(plain, explicit)


class CheckScriptCliTest(unittest.TestCase):
    """make_hwpx_check.py를 직접 실행하면 아무것도 출력하지 않고 0으로 끝나 통과처럼 보였다 (실사용 시험)."""

    def run_check(self, *args):
        import io
        from contextlib import redirect_stdout
        import make_hwpx_check
        out = io.StringIO()
        with redirect_stdout(out):
            code = make_hwpx_check.main(list(args))
        return code, out.getvalue()

    def test_valid_file_prints_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.hwpx"
            build_hwpx({"blocks": [{"type": "paragraph", "text": "본문"}]}, path)
            self.assertEqual(self.run_check(str(path)), (0, "통과\n"))

    def test_broken_file_fails_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.hwpx"
            path.write_bytes(b"not a zip")
            code, out = self.run_check(str(path))
        self.assertEqual(code, 1)
        self.assertIn("오류", out)

    def test_missing_argument_prints_usage(self):
        code, out = self.run_check()
        self.assertEqual(code, 2)
        self.assertIn("사용법", out)


if __name__ == "__main__":
    unittest.main()


def test_bullet_and_numbered_items_hang_their_second_line(tmp_path):
    """두 줄로 넘어간 글머리표·번호 항목의 둘째 줄이 "• ", "1. " 뒤 글 시작에 맞도록 내어쓰기(음수 intent)를 둔다."""
    import re as _re
    import zipfile as _zipfile
    from make_hwpx import ITEM_HANG, build_hwpx
    out = tmp_path / "items.hwpx"
    build_hwpx({"blocks": [{"type": "bullets", "items": ["가"]}, {"type": "numbered", "items": ["나"]},
                           {"type": "numbered", "start": 9, "items": ["다", "라"]}]}, out)
    with _zipfile.ZipFile(out) as package:
        header = package.read("Contents/header.xml").decode("utf-8")
    intents = {int(value) for value in _re.findall(r'<hc:intent value="(-?\d+)"', header)}
    for hang in ITEM_HANG.values():
        assert -hang in intents


def test_table_warns_when_a_word_is_wider_than_its_cell(tmp_path):
    """좁은 칸의 '문항', '선택형(5지)'처럼 칸보다 넓은 낱말은 한글이 낱말 중간에서 끊으므로 경고한다."""
    from make_hwpx import build_hwpx
    narrow = {"type": "table", "header": ["문항", "유형", "내용 영역"], "rows": [["1", "선택형(5지)", "가"]],
              "widths": [1, 1, 30]}
    wide = {**narrow, "widths": [3, 5, 24]}
    warned = build_hwpx({"page": "sheet", "blocks": [narrow]}, tmp_path / "a.hwpx")
    assert any("'문항'" in w for w in warned) and any("'선택형(5지)'" in w for w in warned)
    assert not any("칸보다 넓어" in w for w in build_hwpx({"page": "sheet", "blocks": [wide]}, tmp_path / "b.hwpx"))
