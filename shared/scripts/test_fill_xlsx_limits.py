"""fill_xlsx.py 한계 값 시험: 엑셀 칸 글자 수 상한(32,767자), 15자리를 넘는 정수, DTD가 든 양식."""

import re

from fill_xlsx import FillError, fill_form_notes
from test_fill_xlsx import SHEET1, XlsxCase, read_entries, rewrite

LIMIT = 32767          # 엑셀 한 칸에 들어가는 글자 수 상한


class TextLimitTest(XlsxCase):
    def test_value_over_limit_is_refused_in_korean(self):
        message = self.refused({"sheet": 1, "cell": "B5", "value": "가" * (LIMIT + 1)})
        self.assertIn("32,767자", message)

    def test_value_at_limit_is_written(self):
        self.fill({"sheet": 1, "cell": "B5", "value": "가" * LIMIT})
        self.assertEqual(len(self.reread()["1반"]["B5"].value), LIMIT)

    def test_emoji_counts_twice_like_excel(self):
        message = self.refused({"sheet": 1, "cell": "B5", "value": "가" * (LIMIT - 1) + chr(0x1F600)})
        self.assertIn("32,767자", message)                  # 파이썬 길이는 상한 안이지만 엑셀로는 32,768

    def test_replace_over_limit_is_refused(self):
        message = self.refused({"find": "○○ 2반", "replace": "가" * (LIMIT + 1)})
        self.assertIn("32,767자", message)

    def test_find_result_over_limit_is_refused(self):
        message = self.refused({"find": "○○", "sheet": "2반", "replace": "가" * (LIMIT - 1)})   # 칸 글 "○○ 2반"이 상한을 넘게 됨
        self.assertIn("32,767자", message)


class LongIntegerTest(XlsxCase):
    def cell_xml(self, address: str) -> str:
        sheet = read_entries(self.result)[SHEET1].decode("utf-8")
        return re.search(rf'<c r="{address}"[^>]*?(?:/>|>.*?</c>)', sheet, re.S).group(0)

    def test_sixteen_digit_integer_goes_in_as_text_without_rounding(self):
        count, notes = fill_form_notes(self.form, {"fills": [{"sheet": 1, "cell": "B5", "value": 1234567890123456789}]},
                                       self.result)
        self.assertEqual(count, 1)
        self.assertIn('t="inlineStr"', self.cell_xml("B5"))
        self.assertEqual(self.reread()["1반"]["B5"].value, "1234567890123456789")
        self.assertTrue(any("15자리" in note for note in notes), notes)

    def test_negative_long_integer_keeps_its_sign(self):
        self.fill({"sheet": 1, "cell": "B5", "value": -1234567890123456})
        self.assertEqual(self.reread()["1반"]["B5"].value, "-1234567890123456")

    def test_fifteen_digit_integer_stays_a_number(self):
        self.fill({"sheet": 1, "cell": "B5", "value": 999999999999999})
        self.assertNotIn("inlineStr", self.cell_xml("B5"))
        self.assertEqual(self.reread()["1반"]["B5"].value, 999999999999999)


class DtdTest(XlsxCase):
    def test_form_with_doctype_is_refused_in_korean(self):
        sheet = read_entries(self.form)[SHEET1].decode("utf-8")
        sheet = '<!DOCTYPE worksheet [<!ENTITY e "ABC">]>' + sheet
        broken = rewrite(self.form, self.folder / "dtd.xlsx", {SHEET1: sheet.encode("utf-8")})
        with self.assertRaises(FillError) as caught:
            fill_form_notes(broken, {"fills": [{"sheet": 1, "cell": "B5", "value": 1}]}, self.result)
        self.assertIn("DTD", str(caught.exception))
        self.assertFalse(self.result.exists())
