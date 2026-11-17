import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from neis_bytes import (BYTES_PER_HANGUL, check, count_bytes, count_chars, main, read_text, split_entries,
                        unverified_chars)


class CountBytesTest(unittest.TestCase):
    def test_hangul_counts_three_bytes_each(self):
        self.assertEqual(count_bytes("가나다"), 9)

    def test_ascii_letters_digits_spaces_count_one_byte_each(self):
        self.assertEqual(count_bytes("ab 12"), 5)

    def test_newline_counts_one_byte(self):
        # 2026학년도 기재요령(초 p.150, 중 p.162, 고 p.208): 한글 3Byte, 영문·숫자 1Byte, 엔터 1Byte
        self.assertEqual(count_bytes("가\n나"), 3 + 1 + 3)

    def test_crlf_is_treated_as_single_newline(self):
        self.assertEqual(count_bytes("가\r\n나"), count_bytes("가\n나"))

    def test_mixed_text(self):
        # 탐구함(9) + 공백(1) + "A"(1) + 마침표(1)
        self.assertEqual(count_bytes("탐구함 A."), 12)


class CountCharsTest(unittest.TestCase):
    def test_counts_characters_not_bytes(self):
        self.assertEqual(count_chars("탐구함 A."), 6)

    def test_crlf_counts_as_one_character(self):
        self.assertEqual(count_chars("가\r\n나"), 3)


class CheckTest(unittest.TestCase):
    def test_within_limit(self):
        result = check("가" * 500, limit_chars=500)
        self.assertTrue(result["ok"])
        self.assertEqual(result["limit_bytes"], 500 * BYTES_PER_HANGUL)
        self.assertEqual(result["remaining_bytes"], 0)

    def test_over_limit(self):
        result = check("가" * 501, limit_chars=500)
        self.assertFalse(result["ok"])
        self.assertEqual(result["remaining_bytes"], -3)

    def test_no_limit_reports_counts_only(self):
        result = check("가나", limit_chars=None)
        self.assertIsNone(result["ok"])
        self.assertEqual(result["bytes"], 6)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(check("  가나 \n", limit_chars=None)["bytes"], 6)


class SplitEntriesTest(unittest.TestCase):
    def test_splits_on_dash_lines_and_drops_empty_entries(self):
        text = "학생A 기록\n---\n학생B 기록\n---\n\n"
        self.assertEqual(split_entries(text), ["학생A 기록", "학생B 기록"])

    def test_single_entry_without_separator(self):
        self.assertEqual(split_entries("기록 하나"), ["기록 하나"])


class ReadFileTest(unittest.TestCase):
    """메모장 'UTF-8 (BOM)'과 한글 윈도우 기본 인코딩(CP949) 파일도 읽는다."""

    def write(self, data: bytes) -> str:
        import os
        import tempfile
        handle, path = tempfile.mkstemp(suffix=".txt")
        os.close(handle)
        self.addCleanup(os.remove, path)
        with open(path, "wb") as file:
            file.write(data)
        return path

    def test_utf8_bom_is_not_counted(self):
        self.assertEqual(read_text(self.write("가".encode("utf-8-sig"))), "가")

    def test_cp949_file_is_read(self):
        self.assertEqual(read_text(self.write("탐구함".encode("cp949"))), "탐구함")

    def test_utf16_le_and_be_with_bom_are_read(self):
        import codecs
        for data in ("탐구함".encode("utf-16"), codecs.BOM_UTF16_LE + "탐구함".encode("utf-16-le"),
                     codecs.BOM_UTF16_BE + "탐구함".encode("utf-16-be")):
            with self.subTest(data=data[:2]):
                self.assertEqual(read_text(self.write(data)), "탐구함")


class UnverifiedCharsTest(unittest.TestCase):
    def test_byte_count_is_unchanged(self):
        self.assertEqual(count_bytes("가·"), 3 + 2)

    def test_lists_non_hangul_non_ascii_characters_once_in_order(self):
        self.assertEqual(unverified_chars("가·나…·😀 a1\n"),["·", "…", "😀"])

    def test_hangul_and_ascii_are_verified(self):
        self.assertEqual(unverified_chars("탐구함 A. (1) ~!@"), [])

    def test_check_result_includes_unverified_list(self):
        self.assertEqual(check("가“나”", 10)["unverified"], ["“", "”"])
        self.assertEqual(check("가나", None)["unverified"], [])


class NormalizeTest(unittest.TestCase):
    def test_decomposed_hangul_counts_like_composed(self):
        decomposed = "가"  # 가 (초성+중성)
        self.assertEqual(count_chars(decomposed), 1)
        self.assertEqual(count_bytes(decomposed), count_bytes("가"))

    def test_surrounding_whitespace_is_not_counted(self):
        self.assertEqual(count_bytes(" \n 가 \n"), 3)


class CliTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(arg) for arg in args])
        return code, out.getvalue()

    def write(self, data: bytes, name="기록.txt"):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_cp949_file(self):
        code, out = self.run_main(self.write("탐구함".encode("cp949")))
        self.assertEqual(code, 0)
        self.assertIn("3자 / 9바이트", out)

    def test_empty_file_has_nothing_to_check(self):
        for data in (b"", b"  \r\n \n"):
            with self.subTest(data=data):
                code, out = self.run_main(self.write(data))
                self.assertEqual(code, 2)
                self.assertIn("확인할 기록이 없음", out)
                self.assertNotIn("통과", out)

    def test_empty_file_with_split_has_nothing_to_check(self):
        code, out = self.run_main("--split", self.write(b""))
        self.assertEqual(code, 2)
        self.assertIn("확인할 기록이 없음", out)

    def test_split_reports_each_entry(self):
        code, out = self.run_main("--limit", "2", "--split", self.write("가나\n---\n가나다\n".encode("utf-8")))
        self.assertEqual(code, 1)
        self.assertIn("[1]", out)
        self.assertIn("[2]", out)
        self.assertIn("통과", out)
        self.assertIn("초과", out)

    def test_exit_code_1_when_over_limit(self):
        code, out = self.run_main("--limit", "1", self.write("가나".encode("utf-8")))
        self.assertEqual(code, 1)
        self.assertIn("3바이트 줄여야 함", out)

    def test_exit_code_0_when_within_limit(self):
        self.assertEqual(self.run_main("--limit", "2", self.write("가나".encode("utf-8")))[0], 0)

    def test_limit_must_be_positive(self):
        for value in ("0", "-5"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as caught:
                    main(["--limit", value, str(self.write(b"a"))])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn("0보다 커야", err.getvalue())

    def test_missing_file(self):
        code, out = self.run_main(self.dir / "없음.txt")
        self.assertEqual(code, 2)
        self.assertIn("파일을 읽을 수 없음", out)

    def test_undecodable_file(self):
        code, out = self.run_main(self.write(b"\xff\xfe\xfa\xfb\x80"))
        self.assertEqual(code, 2)

    def test_byte_limit_is_used_as_given(self):
        result = check("가" * 301, None, 900)
        self.assertEqual((result["limit_bytes"], result["ok"]), (900, False))
        self.assertTrue(check("가" * 300, None, 900)["ok"])

    def test_non_integer_limit(self):
        with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as caught:
            main(["--limit", "abc", str(self.write(b"a"))])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("정수여야", err.getvalue())

    def test_unverified_characters_are_warned_in_output(self):
        code, out = self.run_main("--limit", "10", self.write("가·나… “인용”".encode("utf-8")))
        self.assertEqual(code, 0)
        self.assertIn("확인되지 않은 글자", out)
        for ch in ("·", "…", "“", "”"):
            self.assertIn(ch, out)

    def test_no_warning_for_hangul_ascii_only(self):
        _, out = self.run_main(self.write("탐구함 A.\n2학년".encode("utf-8")))
        self.assertNotIn("확인되지 않은", out)

    def test_utf16_file_from_notepad_unicode(self):
        code, out = self.run_main(self.write("탐구함".encode("utf-16")))
        self.assertEqual(code, 0)
        self.assertIn("3자 / 9바이트", out)

    def test_stdout_is_reconfigured_to_utf8(self):
        buffer = io.BytesIO()
        stdout = io.TextIOWrapper(buffer, encoding="cp949")
        with mock.patch("sys.stdout", stdout):
            code = main([str(self.write("가·".encode("utf-8")))])
            stdout.flush()
        self.assertEqual(code, 0)
        self.assertIn("·", buffer.getvalue().decode("utf-8"))

    def test_public_functions_are_documented(self):
        for function in (count_chars, count_bytes, check, split_entries, read_text, main):
            self.assertTrue(function.__doc__, function.__name__)


if __name__ == "__main__":
    unittest.main()
