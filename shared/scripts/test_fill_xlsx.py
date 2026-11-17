"""fill_xlsx.py 시험: 교사 엑셀 양식의 모양을 지키고 지정한 칸의 값만 바꾸는지 본다."""

import io
import json
import re
import tempfile
import tracemalloc
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.protection import SheetProtection

import fill_xlsx
from fill_xlsx import FillError, fill_form, inspect_form, main
from test_make_hwpx_zip import BOMB_BYTES, PEAK_LIMIT, lie_about_size

SHEET1 = "xl/worksheets/sheet1.xml"
WORKBOOK = "xl/workbook.xml"


INLINE_CELL = re.compile(r'<c r="([A-Z]+\d+)"((?: s="\d+")?) t="inlineStr"><is><t>(.*?)</t></is></c>', re.S)
SST_REL = ('<Relationship Id="rIdSst" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
           'sharedStrings" Target="sharedStrings.xml"/>')
SST_TYPE = ('<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sharedStrings+xml"/>')


def to_shared_strings(path: Path) -> None:
    """이 openpyxl은 글을 인라인 문자열로 쓴다. 실제 엑셀처럼 공유 문자열 표를 쓰는 파일로 바꾼다."""
    entries = read_entries(path)
    texts: list[str] = []

    def share(found):
        texts.append(found.group(3))
        return f'<c r="{found.group(1)}"{found.group(2)} t="s"><v>{len(texts) - 1}</v></c>'

    for name in [n for n in entries if n.startswith("xl/worksheets/sheet")]:
        entries[name] = INLINE_CELL.sub(share, entries[name].decode("utf-8")).encode("utf-8")
    body = "".join(f'<si><t xml:space="preserve">{text}</t></si>' for text in texts)
    entries["xl/sharedStrings.xml"] = ('<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.'
                                       f'org/spreadsheetml/2006/main" count="{len(texts)}" uniqueCount="{len(texts)}">'
                                       f'{body}</sst>').encode("utf-8")
    rels = entries["xl/_rels/workbook.xml.rels"].decode("utf-8")
    entries["xl/_rels/workbook.xml.rels"] = rels.replace("</Relationships>", SST_REL + "</Relationships>").encode("utf-8")
    types = entries["[Content_Types].xml"].decode("utf-8")
    entries["[Content_Types].xml"] = types.replace("</Types>", SST_TYPE + "</Types>").encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        for name, data in entries.items():
            out.writestr(name, data)


def make_form(path: Path, shared: bool = True) -> Path:
    """시험용 양식: 병합 칸, 수식, 조건부 서식, 데이터 유효성, 여러 시트, 한글 시트 이름."""
    book = openpyxl.Workbook()
    first = book.active
    first.title = "1반"
    first["A1"] = "○○ 수행평가 기록표"
    first.merge_cells("A1:F1")
    first["A1"].font = Font(bold=True, size=14)
    first["A1"].alignment = Alignment(horizontal="center")
    for column, head in zip("ABCD", ("번호", "이름", "점수", "비고")):
        first[f"{column}4"] = head
    for row in range(5, 10):
        first[f"A{row}"] = row - 4
        first[f"C{row}"].fill = PatternFill("solid", start_color="FFFFCC00")
        first[f"C{row}"].number_format = "0.0"
    first["B5"].fill = PatternFill("solid", start_color="FF00CC00")
    first["D5"] = "메모 ○○ 와 ○○"
    first["C10"] = "=SUM(C5:C9)"
    first["A10"] = "합계 & <평균>"
    first.merge_cells("A12:B13")
    first["A12"] = "병합 칸"
    first.conditional_formatting.add("C5:C9", CellIsRule(operator="lessThan", formula=["60"], fill=PatternFill(
        "solid", start_color="FFFF0000", end_color="FFFF0000")))
    check = DataValidation(type="list", formula1='"A,B,C"', allow_blank=True)
    first.add_data_validation(check)
    check.add("D6:D9")
    second = book.create_sheet("2반")
    second["A1"] = "○○ 2반"
    second["B2"] = 7
    second["C2"] = "=B2*2"
    third = book.create_sheet("숨김 시트")
    third["A1"] = "비밀"
    third.sheet_state = "hidden"
    fourth = book.create_sheet("보호")
    fourth["A1"] = "잠김"
    fourth.protection = SheetProtection(sheet=True)
    book.save(path)
    if shared:
        to_shared_strings(path)
    return path


def read_entries(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def rewrite(source: Path, target: Path, changes: dict[str, bytes | None]) -> Path:
    """양식 압축 파일의 항목을 바꾸거나(bytes) 지워(None) 새 파일로 쓴다. 망가진 양식 시험용."""
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out:
        for info in archive.infolist():
            if info.filename not in changes:
                out.writestr(info.filename, archive.read(info.filename))
            elif changes[info.filename] is not None:
                out.writestr(info.filename, changes[info.filename])
        for name, data in changes.items():
            if data is not None and name not in archive.namelist():
                out.writestr(name, data)
    return target


class XlsxCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = Path(holder.name)
        self.form = make_form(self.folder / "양식.xlsx")
        self.result = self.folder / "결과.xlsx"

    def fill(self, *fills: dict) -> int:
        return fill_form(self.form, {"fills": list(fills)}, self.result)

    def refused(self, *fills: dict) -> str:
        """이름을 fail로 하면 unittest의 TestCase.fail을 덮어써 모든 assert 실패가 조용히 통과한다."""
        with self.assertRaises(FillError) as caught:
            self.fill(*fills)
        self.assertFalse(self.result.exists(), "실패하면 결과 파일을 만들지 않아야 함")
        return str(caught.exception)

    def reread(self, data_only: bool = False):
        return openpyxl.load_workbook(self.result, data_only=data_only)


class InspectTest(XlsxCase):
    def test_lists_sheets_cells_formulas_and_merges(self):
        text = inspect_form(self.form)
        self.assertIn('시트 1 "1반"', text)
        self.assertIn('시트 2 "2반"', text)
        self.assertIn("C5: (빈 칸)", text)
        self.assertIn("D5: 메모 ○○ 와 ○○", text)
        self.assertIn("C10: [수식] =SUM(C5:C9)", text)
        self.assertRegex(text, r"합침: (A1:F1, A12:B13|A12:B13, A1:F1)\n")    # 파일에 적힌 순서대로
        self.assertIn("A10: 합계 & <평균>", text)

    def test_shows_hidden_and_protected_sheets(self):
        text = inspect_form(self.form)
        self.assertRegex(text, r'시트 3 "숨김 시트".*\[숨김\]')
        self.assertRegex(text, r'시트 4 "보호".*\[시트 보호\]')
        self.assertNotRegex(text, r'시트 1 "1반".*\[(숨김|시트 보호)\]')

    def test_rejects_non_xlsx(self):
        junk = self.folder / "가짜.xlsx"
        junk.write_bytes(b"not a zip")
        with self.assertRaises(FillError):
            inspect_form(junk)

    def test_old_binary_or_password_file_gets_guidance(self):
        old = self.folder / "옛것.xlsx"
        old.write_bytes(b"\xd0\xcf\x11\xe0" + b"\0" * 64)
        with self.assertRaisesRegex(FillError, "xlsx로 저장"):
            inspect_form(old)


class ValueFillTest(XlsxCase):
    def test_text_and_number_land_with_the_cell_style(self):
        count = self.fill({"sheet": "1반", "cell": "B5", "value": "홍길동"},
                          {"sheet": 1, "cell": "C5", "value": 85.5},
                          {"sheet": "2반", "cell": "A2", "value": "수학"})
        self.assertEqual(count, 3)
        book = self.reread()
        first = book["1반"]
        self.assertEqual(first["B5"].value, "홍길동")
        self.assertEqual(first["C5"].value, 85.5)
        self.assertEqual(book["2반"]["A2"].value, "수학")
        self.assertEqual(first["B5"].fill.start_color.rgb, "FF00CC00")
        self.assertEqual(first["C5"].fill.start_color.rgb, "FFFFCC00")
        self.assertEqual(first["C5"].number_format, "0.0")

    def test_integer_stays_integer_and_numeric_text_stays_text(self):
        self.fill({"sheet": "1반", "cell": "C6", "value": 85}, {"sheet": "1반", "cell": "D6", "value": "85"})
        first = self.reread()["1반"]
        self.assertEqual(first["C6"].value, 85)
        self.assertIsInstance(first["C6"].value, int)
        self.assertEqual(first["D6"].value, "85")

    def test_xml_special_characters_and_newlines_survive(self):
        text = "A & B <c> \"q\" 'a'\n둘째 줄  끝 "
        self.fill({"sheet": "1반", "cell": "D7", "value": text})
        self.assertEqual(self.reread()["1반"]["D7"].value, text)

    def test_formula_like_values_stay_text_not_formulas(self):
        """=, +, -, @로 시작하는 값은 수식이 아니라 글자로 남는다(수식 주입 방지)."""
        values = {"B5": '=HYPERLINK("x")', "B6": "+1", "B7": "-1", "B8": "@SUM(1)", "B9": '=cmd|" /C calc"!A0'}
        self.fill(*({"sheet": "1반", "cell": cell, "value": value} for cell, value in values.items()))
        first = self.reread()["1반"]
        for cell, value in values.items():
            with self.subTest(cell=cell):
                self.assertEqual(first[cell].value, value)
                self.assertEqual(first[cell].data_type, "s")
        xml = read_entries(self.result)[SHEET1].decode("utf-8")
        for cell in values:
            found = re.search(rf'<c r="{cell}"[^>]*>.*?</c>', xml, re.S)
            self.assertIn('t="inlineStr"', found.group(0))
            self.assertNotIn("<f>", found.group(0))
        self.assertEqual(xml.count("<f>"), 1)      # 양식의 합계 수식(C10)만 남음

    def test_formula_like_replacement_in_find_stays_text(self):
        self.fill({"find": "메모", "replace": "=1+1", "sheet": "1반"})
        cell = self.reread()["1반"]["D5"]
        self.assertEqual(cell.data_type, "s")
        self.assertTrue(str(cell.value).startswith("=1+1"))

    def test_replaces_an_existing_text_cell(self):
        self.fill({"sheet": "1반", "cell": "B4", "value": "성명"})
        self.assertEqual(self.reread()["1반"]["B4"].value, "성명")

    def test_empty_value_clears_but_keeps_style(self):
        self.fill({"sheet": "1반", "cell": "D5", "value": None}, {"sheet": "1반", "cell": "B4", "value": ""})
        first = self.reread()["1반"]
        self.assertIsNone(first["D5"].value)
        self.assertIsNone(first["B4"].value)

    def test_style_index_is_kept_byte_for_byte(self):
        before = read_entries(self.form)[SHEET1].decode("utf-8")
        self.fill({"sheet": "1반", "cell": "C5", "value": 90})
        after = read_entries(self.result)[SHEET1].decode("utf-8")
        old_style = re.search(r'<c r="C5" s="(\d+)"', before).group(1)
        self.assertRegex(after, rf'<c r="C5" s="{old_style}"')

    def test_missing_cells_and_rows_inside_the_form_are_created_in_order(self):
        self.fill({"sheet": "1반", "cell": "E5", "value": "새 칸"},
                  {"sheet": "1반", "cell": "B11", "value": "새 행"},
                  {"sheet": "1반", "cell": "A11", "value": "새 행 앞"},
                  {"sheet": "1반", "cell": "B10", "value": "중간"})
        first = self.reread()["1반"]
        self.assertEqual([first["E5"].value, first["A11"].value, first["B11"].value, first["B10"].value],
                         ["새 칸", "새 행 앞", "새 행", "중간"])
        xml = read_entries(self.result)[SHEET1].decode("utf-8")
        rows = [int(number) for number in re.findall(r'<row r="(\d+)"', xml)]
        self.assertEqual(rows, sorted(rows))
        row_five = re.search(r'<row r="5".*?</row>', xml, re.S).group(0)
        columns = re.findall(r'<c r="([A-Z]+)5"', row_five)
        self.assertEqual(columns, sorted(columns, key=lambda c: (len(c), c)))


class ShapeKeptTest(XlsxCase):
    def test_merges_formulas_conditional_formats_and_validations_survive(self):
        self.fill({"sheet": "1반", "cell": "C5", "value": 90}, {"sheet": "1반", "cell": "C6", "value": 40})
        first = self.reread()["1반"]
        self.assertEqual({str(r) for r in first.merged_cells.ranges}, {"A1:F1", "A12:B13"})
        self.assertEqual(first["C10"].value, "=SUM(C5:C9)")
        self.assertEqual(len(first.conditional_formatting), 1)
        self.assertEqual(len(first.data_validations.dataValidation), 1)
        self.assertTrue(first["A1"].font.bold)
        self.assertEqual(self.reread()["2반"]["C2"].value, "=B2*2")

    def test_untouched_entries_are_identical_and_others_barely_change(self):
        before = read_entries(self.form)
        self.fill({"sheet": "1반", "cell": "B5", "value": "홍길동"})
        after = read_entries(self.result)
        self.assertEqual(list(before), list(after))
        changed = {name for name in before if before[name] != after[name]}
        self.assertLessEqual(changed, {SHEET1, WORKBOOK})
        self.assertIn(SHEET1, changed)

    def test_untouched_part_of_the_edited_sheet_is_identical(self):
        before = read_entries(self.form)[SHEET1].decode("utf-8")
        self.fill({"sheet": "1반", "cell": "B5", "value": "홍길동"})
        after = read_entries(self.result)[SHEET1].decode("utf-8")
        strip = lambda xml: re.sub(r'<c r="B5".*?(?:/>|</c>)', "", xml)  # noqa: E731
        self.assertEqual(strip(before), strip(after))

    def test_workbook_recalculates_on_open(self):
        self.fill({"sheet": "1반", "cell": "C5", "value": 90})
        workbook = read_entries(self.result)[WORKBOOK].decode("utf-8")
        self.assertRegex(workbook, r'<calcPr[^>]*fullCalcOnLoad="1"')
        self.assertEqual(workbook.count("<calcPr"), 1)

    def test_calc_setting_is_added_when_missing_and_kept_in_order(self):
        entries = read_entries(self.form)
        stripped = re.sub(r"<calcPr[^>]*/>", "", entries[WORKBOOK].decode("utf-8"))
        form = rewrite(self.form, self.folder / "계산없음.xlsx", {WORKBOOK: stripped.encode("utf-8")})
        fill_form(form, {"fills": [{"sheet": 1, "cell": "B5", "value": "가"}]}, self.result)
        workbook = read_entries(self.result)[WORKBOOK].decode("utf-8")
        self.assertIn('fullCalcOnLoad="1"', workbook)
        self.assertLess(workbook.index("<sheets"), workbook.index("<calcPr"))
        openpyxl.load_workbook(self.result)

    def test_original_is_untouched(self):
        before = self.form.read_bytes()
        self.fill({"sheet": "1반", "cell": "B5", "value": "홍길동"})
        self.assertEqual(self.form.read_bytes(), before)


class RefusalTest(XlsxCase):
    def test_formula_cell_is_never_overwritten(self):
        message = self.refused({"sheet": "1반", "cell": "C10", "value": 100})
        self.assertIn("수식", message)
        self.assertIn("C10", message)

    def test_cell_inside_a_merge_that_is_not_top_left(self):
        message = self.refused({"sheet": "1반", "cell": "B1", "value": "x"})
        self.assertIn("A1", message)
        self.assertIn("합쳐", message)
        message = self.refused({"sheet": "1반", "cell": "B13", "value": "x"})
        self.assertIn("A12", message)

    def test_top_left_of_a_merge_is_allowed(self):
        self.fill({"sheet": "1반", "cell": "A1", "value": "국어 수행평가 기록표"})
        self.assertEqual(self.reread()["1반"]["A1"].value, "국어 수행평가 기록표")

    def test_all_problems_are_reported_together(self):
        message = self.refused({"sheet": "없는반", "cell": "A1", "value": 1},
                            {"sheet": 9, "cell": "A1", "value": 1},
                            {"sheet": "1반", "cell": "Z99", "value": 1},
                            {"sheet": "1반", "cell": "C10", "value": 1},
                            {"find": "없는글", "replace": "x"})
        for part in ("1번 지시", "2번 지시", "3번 지시", "4번 지시", "5번 지시"):
            self.assertIn(part, message)

    def test_bad_instructions(self):
        cases = [
            ({"sheet": "1반", "cell": "B5"}, "value"),
            ({"sheet": "1반", "cell": "B5:C6", "value": 1}, "칸 주소"),
            ({"sheet": "1반", "cell": "5B", "value": 1}, "칸 주소"),
            ({"sheet": "1반", "cell": "B5", "value": True}, "value"),
            ({"sheet": "1반", "cell": "B5", "value": [1]}, "value"),
            ({"sheet": "1반", "cell": "B5", "value": float("nan")}, "value"),
            ({"sheet": "1반", "cell": "B5", "value": "a\x00b"}, "제어 문자"),
            ({"sheet": 0, "cell": "B5", "value": 1}, "sheet"),
            ({"sheet": True, "cell": "B5", "value": 1}, "sheet"),
            ({"cell": "B5", "value": 1}, "sheet"),
            ({"sheet": "1반", "cell": "XFE5", "value": 1}, "칸 주소"),
            ({"sheet": "1반", "cell": "A1048577", "value": 1}, "칸 주소"),
            ({"sheet": "1반", "cell": "B5", "value": 1, "extra": 1}, "모르는 항목"),
            ({"find": "", "replace": "x"}, "find"),
            ({"find": "○○", "replace": "x", "all": True, "nth": 1}, "함께"),
            ({"find": "○○", "replace": "x", "nth": 0}, "nth"),
            ({"find": "○○"}, "replace"),
            ({"hello": 1}, "find 또는 sheet"),
        ]
        for fill, expected in cases:
            with self.subTest(fill=fill):
                self.assertIn(expected, self.refused(fill))

    def test_empty_or_missing_fills(self):
        for spec in ({}, {"fills": []}, {"fills": "x"}, []):
            with self.subTest(spec=spec):
                with self.assertRaises(FillError):
                    fill_form(self.form, spec, self.result)

    def test_same_cell_twice_is_an_error(self):
        message = self.refused({"sheet": "1반", "cell": "B5", "value": 1}, {"sheet": "1반", "cell": "b5", "value": 2})
        self.assertIn("겹침", message)

    def test_cell_outside_the_form_area(self):
        message = self.refused({"sheet": "1반", "cell": "Z99", "value": 1})
        self.assertIn("범위", message)

    def test_result_path_rules(self):
        with self.assertRaisesRegex(FillError, "덮어쓸 수 없음"):
            fill_form(self.form, {"fills": [{"sheet": 1, "cell": "B5", "value": 1}]}, self.form)
        self.result.write_bytes(b"x")
        with self.assertRaisesRegex(FillError, "덮어쓰지 않음"):
            self.fill({"sheet": 1, "cell": "B5", "value": 1})
        self.assertEqual(self.result.read_bytes(), b"x")
        with self.assertRaisesRegex(FillError, "폴더가 없음"):
            fill_form(self.form, {"fills": [{"sheet": 1, "cell": "B5", "value": 1}]}, self.folder / "없음" / "a.xlsx")
        with self.assertRaisesRegex(FillError, "확장자"):
            fill_form(self.form, {"fills": [{"sheet": 1, "cell": "B5", "value": 1}]}, self.folder / "결과.xlsm")

    def test_no_temp_file_is_left_behind_on_failure(self):
        self.refused({"sheet": "없는반", "cell": "A1", "value": 1})
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["양식.xlsx"])


class FindReplaceTest(XlsxCase):
    def test_all_replaces_every_match_in_every_sheet(self):
        count = self.fill({"find": "○○", "replace": "국어", "all": True})
        book = self.reread()
        self.assertEqual(book["1반"]["A1"].value, "국어 수행평가 기록표")
        self.assertEqual(book["1반"]["D5"].value, "메모 국어 와 국어")
        self.assertEqual(book["2반"]["A1"].value, "국어 2반")
        self.assertEqual(count, 3)

    def test_sheet_limits_the_search_and_style_stays(self):
        self.fill({"find": "○○", "replace": "국어", "all": True, "sheet": "2반"})
        book = self.reread()
        self.assertEqual(book["2반"]["A1"].value, "국어 2반")
        self.assertEqual(book["1반"]["A1"].value, "○○ 수행평가 기록표")

    def test_merged_title_keeps_its_look(self):
        self.fill({"find": "○○", "replace": "국어", "all": True, "sheet": 1})
        first = self.reread()["1반"]
        self.assertTrue(first["A1"].font.bold)
        self.assertEqual(first["A1"].alignment.horizontal, "center")

    def test_nth_picks_one_occurrence(self):
        self.fill({"find": "○○", "replace": "수학", "nth": 2, "sheet": "1반"})
        first = self.reread()["1반"]
        self.assertEqual(first["A1"].value, "○○ 수행평가 기록표")
        self.assertEqual(first["D5"].value, "메모 수학 와 ○○")

    def test_ambiguous_find_names_the_places(self):
        message = self.refused({"find": "○○", "replace": "x"})
        self.assertIn("A1", message)
        self.assertIn("all", message)

    def test_unique_find_works_without_all(self):
        self.fill({"find": "2반", "replace": "3반", "sheet": 2})
        self.assertEqual(self.reread()["2반"]["A1"].value, "○○ 3반")

    def test_nth_too_big_and_not_found(self):
        self.assertIn("3곳뿐", self.refused({"find": "○○", "replace": "x", "nth": 9, "sheet": "1반"}))
        self.assertIn("찾지 못함", self.refused({"find": "없는글", "replace": "x"}))

    def test_formula_text_is_not_searched(self):
        self.assertIn("찾지 못함", self.refused({"find": "SUM", "replace": "x"}))

    def test_two_fills_on_one_cell_overlap(self):
        message = self.refused({"find": "○○", "replace": "가", "nth": 2, "sheet": 1},
                            {"find": "○○", "replace": "나", "nth": 3, "sheet": 1})
        self.assertIn("겹침", message)

    def test_value_fill_and_find_on_same_cell_overlap(self):
        message = self.refused({"sheet": "1반", "cell": "A1", "value": "x"},
                            {"find": "○○ 수행", "replace": "y", "sheet": 1})
        self.assertIn("겹침", message)

    def test_replacement_with_special_characters(self):
        self.fill({"find": "2반", "replace": "<3반> & \"q\"", "sheet": "2반"})
        self.assertEqual(self.reread()["2반"]["A1"].value, "○○ <3반> & \"q\"")

    def test_numeric_replacement_becomes_text_in_text_cell(self):
        self.fill({"find": "2반", "replace": 3, "sheet": 2})
        self.assertEqual(self.reread()["2반"]["A1"].value, "○○ 3")

    def test_nonbreaking_space_matches_plain_space(self):
        second = self.folder / "둘째.xlsx"
        fill_form(self.form, {"fills": [{"sheet": "2반", "cell": "A2", "value": "가 나"}]}, second)
        fill_form(second, {"fills": [{"find": "가 나", "replace": "다"}]}, self.result)
        self.assertEqual(self.reread()["2반"]["A2"].value, "다")


class PackageSafetyTest(XlsxCase):
    def test_entry_with_parent_path_is_refused(self):
        evil = rewrite(self.form, self.folder / "악성.xlsx", {"../evil.txt": b"x"})
        with self.assertRaisesRegex(FillError, "경로"):
            inspect_form(evil)

    def test_absolute_and_backslash_entry_names_are_refused(self):
        for name in ("/abs.txt", "a/../b.txt", "C:/x.txt"):
            with self.subTest(name=name):
                evil = rewrite(self.form, self.folder / "악성2.xlsx", {name: b"x"})
                with self.assertRaisesRegex(FillError, "경로"):
                    inspect_form(evil)

    def test_lying_entry_size_does_not_blow_up_memory(self):
        bomb = rewrite(self.form, self.folder / "폭탄.xlsx", {"xl/media/x.bin": bytes(BOMB_BYTES)})
        lie_about_size(bomb, "xl/media/x.bin", 10)
        tracemalloc.start()
        try:
            with self.assertRaises(FillError):
                inspect_form(bomb)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, PEAK_LIMIT)

    def test_total_size_limit(self):
        with mock.patch.object(fill_xlsx, "MAX_TOTAL_BYTES", 100):
            with self.assertRaisesRegex(FillError, "너무 큼"):
                inspect_form(self.form)

    def test_oversized_entry_is_refused(self):
        with mock.patch.object(fill_xlsx, "MAX_ENTRY_BYTES", 100):
            with self.assertRaisesRegex(FillError, "너무 큼"):
                inspect_form(self.form)

    def test_missing_workbook_part(self):
        broken = rewrite(self.form, self.folder / "깨짐.xlsx", {WORKBOOK: None})
        with self.assertRaisesRegex(FillError, "xlsx 파일이 아님|읽을 수 없음"):
            inspect_form(broken)

    def test_broken_sheet_xml(self):
        broken = rewrite(self.form, self.folder / "깨짐2.xlsx", {SHEET1: b"<worksheet><sheetData>"})
        with self.assertRaisesRegex(FillError, "읽을 수 없음"):
            inspect_form(broken)

    def test_sheet_path_that_escapes_the_package_is_refused(self):
        rels = read_entries(self.form)["xl/_rels/workbook.xml.rels"].decode("utf-8")
        evil = rels.replace("/xl/worksheets/sheet1.xml", "../../evil.xml").replace("worksheets/sheet1.xml",
                                                                                     "../../evil.xml")
        broken = rewrite(self.form, self.folder / "경로.xlsx", {"xl/_rels/workbook.xml.rels": evil.encode("utf-8")})
        with self.assertRaises(FillError):
            inspect_form(broken)

    def test_macro_workbook_keeps_its_macro_part(self):
        macro = rewrite(self.form, self.folder / "매크로.xlsm", {"xl/vbaProject.bin": b"VBA"})
        out = self.folder / "결과.xlsm"
        fill_form(macro, {"fills": [{"sheet": 1, "cell": "B5", "value": "가"}]}, out)
        self.assertEqual(read_entries(out)["xl/vbaProject.bin"], b"VBA")


class InlineAndSharedTest(XlsxCase):
    def test_works_when_the_form_already_uses_inline_strings(self):
        form = make_form(self.folder / "인라인.xlsx", shared=False)
        self.assertNotIn("xl/sharedStrings.xml", read_entries(form))
        fill_form(form, {"fills": [{"find": "메모", "replace": "채움", "sheet": 1},
                                   {"sheet": 1, "cell": "B5", "value": "가"}]}, self.result)
        first = openpyxl.load_workbook(self.result)["1반"]
        self.assertEqual((first["D5"].value, first["B5"].value), ("채움 ○○ 와 ○○", "가"))

    def test_rich_text_cell_replacement_is_reported(self):
        shared = read_entries(self.form)["xl/sharedStrings.xml"].decode("utf-8")
        rich = re.sub(r'<si><t[^>]*>(?:&#9675;){2} 2&#48152;</t></si>',
                      '<si><r><rPr><b/></rPr><t>○○ </t></r><r><t>2반</t></r></si>', shared)
        self.assertNotEqual(shared, rich)
        form = rewrite(self.form, self.folder / "서식글.xlsx", {"xl/sharedStrings.xml": rich.encode("utf-8")})
        message = fill_xlsx._run_fill(str(form), self._spec([{"find": "○○", "replace": "국어", "sheet": "2반"}]),
                                      str(self.result))
        self.assertIn("글자별 서식", message)

    def _spec(self, fills: list[dict]) -> str:
        path = self.folder / "지시.json"
        path.write_text(json.dumps({"fills": fills}, ensure_ascii=False), encoding="utf-8")
        return str(path)


class CommandLineTest(XlsxCase):
    def run_main(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch("sys.stdout", buffer):
            code = main(list(args))
        return code, buffer.getvalue()

    def spec(self, fills: list[dict]) -> str:
        path = self.folder / "지시.json"
        path.write_text(json.dumps({"fills": fills}, ensure_ascii=False), encoding="utf-8-sig")
        return str(path)

    def test_inspect_and_fill(self):
        code, out = self.run_main("--inspect", str(self.form))
        self.assertEqual(code, 0)
        self.assertIn("1반", out)
        code, out = self.run_main(str(self.form), self.spec([{"sheet": "1반", "cell": "B5", "value": "홍길동"}]),
                                  str(self.result))
        self.assertEqual(code, 0)
        self.assertIn("완료", out)
        self.assertIn("1곳", out)
        self.assertTrue(self.result.exists())

    def test_notes_hidden_and_protected_sheets_on_fill(self):
        code, out = self.run_main(str(self.form), self.spec([{"sheet": "보호", "cell": "A1", "value": "x"},
                                                             {"sheet": "숨김 시트", "cell": "A1", "value": "y"}]),
                                  str(self.result))
        self.assertEqual(code, 0)
        self.assertIn("보호", out)
        self.assertIn("숨김", out)

    def test_failure_returns_one_and_usage_returns_two(self):
        code, out = self.run_main(str(self.form), self.spec([{"sheet": "없음", "cell": "A1", "value": 1}]),
                                  str(self.result))
        self.assertEqual(code, 1)
        self.assertIn("없음", out)
        code, _ = self.run_main()
        self.assertEqual(code, 2)
        code, _ = self.run_main("--inspect")
        self.assertEqual(code, 2)

    def test_bad_spec_file(self):
        bad = self.folder / "나쁨.json"
        bad.write_text("{", encoding="utf-8")
        code, out = self.run_main(str(self.form), str(bad), str(self.result))
        self.assertEqual(code, 1)
        self.assertIn("지시 파일", out)
        code, out = self.run_main(str(self.form), str(self.folder / "없음.json"), str(self.result))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
