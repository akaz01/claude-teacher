import copy
import io
import json
import re
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

from make_hwpx import build_hwpx, main
from make_hwpx_lint import date_warnings, with_auto_keep

TABLE = {"type": "table", "header": ["시기", "내용"], "rows": [["가", "나"]]}


class AutoKeepTest(unittest.TestCase):
    def test_paragraph_before_table_keeps_with_it(self):
        # "3. 추진 일정" 문단만 쪽 끝에 남고 표는 다음 쪽으로 넘어갔다 (웹 실사용 시험)
        blocks = with_auto_keep([{"type": "paragraph", "text": "3. 추진 일정"}, TABLE])
        self.assertTrue(blocks[0]["keep_with_next"])

    def test_paragraph_before_answer_box_keeps_with_it(self):
        blocks = with_auto_keep([{"type": "paragraph", "text": "1. 서술하시오."}, {"type": "answer_box"}])
        self.assertTrue(blocks[0]["keep_with_next"])

    def test_other_paragraphs_are_unchanged(self):
        source = [{"type": "paragraph", "text": "가"}, {"type": "paragraph", "text": "나"}, TABLE,
                  {"type": "paragraph", "text": "다"}]
        blocks = with_auto_keep(source)
        self.assertEqual([b.get("keep_with_next") for b in blocks], [None, True, None, None])

    def test_explicit_false_is_respected(self):
        blocks = with_auto_keep([{"type": "paragraph", "text": "가", "keep_with_next": False}, TABLE])
        self.assertFalse(blocks[0]["keep_with_next"])

    def test_input_is_not_mutated(self):
        source = [{"type": "paragraph", "text": "가"}, TABLE]
        before = copy.deepcopy(source)
        with_auto_keep(source)
        self.assertEqual(source, before)

    def test_non_dict_blocks_pass_through_for_later_validation(self):
        self.assertEqual(with_auto_keep(["x", TABLE]), ["x", TABLE])


class DateWarningTest(unittest.TestCase):
    def test_iso_dates_are_reported_with_examples(self):
        # 공문서 날짜는 2026. 11. 14.(토) 형식인데 2026-11-14(토)로 나왔다 (웹 실사용 시험)
        spec = {"title": "계획", "blocks": [
            {"type": "paragraph", "text": "가. 일시: 2026-11-14(토)"},
            {"type": "table", "rows": [["2026-10", "계획 수립"], [{"text": "2026-11-14"}, "실시"]]}]}
        warnings = date_warnings(spec)
        self.assertEqual(len(warnings), 1)
        self.assertIn("2026-11-14", warnings[0])
        self.assertIn("2026-10", warnings[0])
        self.assertIn("2026. 11. 14.", warnings[0])

    def test_official_dates_phones_and_year_ranges_are_fine(self):
        spec = {"blocks": [{"type": "paragraph",
                            "text": "2026. 11. 13.(금), 2025-2026학년도, 010-1234-5678, 2026. 3."}]}
        self.assertEqual(date_warnings(spec), [])

    def test_wrong_weekday_is_reported(self):
        # "2026. 11. 14.(금)"처럼 요일이 틀려도 통과했다 (실사용 시험)
        spec = {"blocks": [{"type": "paragraph", "text": "일시: 2026. 11. 14.(금) 10:00"}]}
        warnings = date_warnings(spec)
        self.assertEqual(len(warnings), 1)
        self.assertIn("2026. 11. 14.(금)", warnings[0])
        self.assertIn("토", warnings[0])

    def test_weekend_date_is_flagged_for_confirmation(self):
        # 토요일 공개수업처럼 주말 행사는 교사가 의도한 것인지 확인해야 한다
        spec = {"blocks": [{"type": "paragraph", "text": "2026. 11. 14.(토), 2026. 11. 15."}]}
        warnings = date_warnings(spec)
        self.assertEqual(len(warnings), 1)
        self.assertIn("주말", warnings[0])
        self.assertIn("2026. 11. 15.", warnings[0])

    def test_version_like_prefix_is_not_a_date(self):
        # "v2026. 3. 1."처럼 글자에 붙은 숫자를 날짜로 읽었다 (코드 리뷰)
        self.assertEqual(date_warnings({"blocks": [{"type": "paragraph", "text": "v2026. 3. 15. 배포"}]}), [])

    def test_impossible_date_is_reported(self):
        spec = {"blocks": [{"type": "paragraph", "text": "2026. 2. 30.(월)"}]}
        warnings = date_warnings(spec)
        self.assertEqual(len(warnings), 1)
        self.assertIn("없는 날짜", warnings[0])

    def test_many_dates_are_summarised(self):
        spec = {"blocks": [{"type": "paragraph", "text": f"2026-03-{day:02d}"} for day in range(1, 11)]}
        warning = date_warnings(spec)[0]
        self.assertIn("10곳", warning)
        self.assertLess(len(warning), 200)


class IntegrationTest(unittest.TestCase):
    def build(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "out.hwpx"
        warnings = build_hwpx(spec, path)
        return path, warnings

    def test_build_applies_auto_keep(self):
        path, _ = self.build({"blocks": [{"type": "paragraph", "text": "3. 추진 일정"}, TABLE]})
        with zipfile.ZipFile(path) as archive:
            header = archive.read("Contents/header.xml").decode("utf-8")
            section = archive.read("Contents/section0.xml").decode("utf-8")
        pid = re.findall(r'<hp:p id="\d+" paraPrIDRef="(\d+)"', section)[1]
        self.assertRegex(header, rf'<hh:paraPr id="{pid}" (?:(?!</hh:paraPr>).)*?keepWithNext="1"')

    def test_build_returns_date_warnings(self):
        _, warnings = self.build({"blocks": [{"type": "paragraph", "text": "2026-11-14"}]})
        self.assertEqual(len(warnings), 1)
        _, warnings = self.build({"blocks": [{"type": "paragraph", "text": "2026. 11. 13."}]})
        self.assertEqual(warnings, [])

    def test_cli_reads_json_with_bom(self):
        # Windows PowerShell이 쓴 JSON은 BOM이 붙어 "Unexpected UTF-8 BOM"으로 실패했다 (실사용 시험)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bom.json"
            src.write_bytes(json.dumps({"blocks": [{"type": "paragraph", "text": "본문"}]}).encode("utf-8-sig"))
            with redirect_stdout(io.StringIO()):
                code = main([str(src), str(Path(tmp) / "bom.hwpx")])
        self.assertEqual(code, 0)

    def test_cli_prints_warning_but_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "a.json"
            src.write_text(json.dumps({"blocks": [{"type": "paragraph", "text": "2026-11-14"}]}), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([str(src), str(Path(tmp) / "a.hwpx")])
        self.assertEqual(code, 0)
        self.assertIn("완료", out.getvalue())
        self.assertIn("주의", out.getvalue())


if __name__ == "__main__":
    unittest.main()
