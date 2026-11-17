import contextlib
import io
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from import_curriculum import file_name, fix_spacing, group_rows, main, render_subject, write_dataset

ROWS = [
    {"code": "[9과01-01]", "subject_group": "과학", "subject": "과학", "grade_group": "중1-3",
     "school_level": "중학교", "curriculum_category": "공통", "area": "과학과 사회",
     "content": "과학 지식의 특징을 설명할 수 있다.", "explanation": "해설 문장"},
    {"code": "[9과02-01]", "subject_group": "과학", "subject": "과학", "grade_group": "중1-3",
     "school_level": "중학교", "curriculum_category": "공통", "area": "물질의 구성",
     "content": "원소의 뜻을 안다.", "explanation": ""},
    {"code": "[10공국1-01-01]", "subject_group": "국어", "subject": "공통국어1, 공통국어2", "grade_group": "고공통",
     "school_level": "고등학교", "curriculum_category": "공통", "area": "듣기⋅말하기",
     "content": "대화의 원리를 고려하여 대화한다.", "explanation": None},
    {"code": "[직업01-01]", "subject_group": "직업", "subject": "직업", "grade_group": "",
     "school_level": "", "curriculum_category": "전공실무", "area": "", "content": "제외 대상", "explanation": ""},
]


class ImportTest(unittest.TestCase):
    def test_file_name_is_ascii_number(self):
        # claude.ai 스킬 업로드가 한글·괄호·+ 가 든 경로를 "invalid characters"로 거부했다
        self.assertEqual(file_name("elementary", 1), "e001.md")
        self.assertEqual(file_name("high", 226), "h226.md")

    def test_vocational_rows_are_skipped(self):
        groups = group_rows(ROWS)
        self.assertEqual(set(groups), {("middle", "과학", "과학"), ("high", "국어", "공통국어1, 공통국어2")})

    def test_subject_page_groups_by_area_and_keeps_text_verbatim(self):
        page = render_subject("middle", "과학", "과학", group_rows(ROWS)[("middle", "과학", "과학")])
        self.assertIn("## 과학과 사회", page)
        self.assertIn("| [9과01-01] | 과학 지식의 특징을 설명할 수 있다. |", page)
        self.assertIn("- **[9과01-01]** 해설 문장", page)
        self.assertLess(page.index("## 과학과 사회"), page.index("## 물질의 구성"))

    def test_split_words_from_pdf_extraction_are_joined(self):
        rows = [{**ROWS[0], "content": "소리의 파 형을 비교한다.", "explanation": "세포의 특징으 로는 개괄 적으로 다룬다."}]
        page = render_subject("middle", "과학", "과학", rows)
        self.assertIn("| [9과01-01] | 소리의 파형을 비교한다. |", page)
        self.assertIn("세포의 특징으로는 개괄적으로 다룬다.", page)

    def test_spacing_fix_leaves_normal_spacing_alone(self):
        text = "실험할 수 있다. 이 때 그 중 빅 데이터와 신재생 에너지를 다룬다."
        self.assertEqual(fix_spacing(text), text)

    def test_write_dataset_creates_files_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_dataset(ROWS, root)
            self.assertTrue((root / "2022/middle/m001.md").exists())
            self.assertTrue((root / "2022/high/h001.md").exists())
            index = (root / "2022/INDEX.md").read_text(encoding="utf-8")
            self.assertIn("| 과학 | 과학 | middle/m001.md | 2 |", index)
            self.assertIn("| 국어 | 공통국어1, 공통국어2 | high/h001.md | 1 |", index)

    def _write_four_subjects(self, tmp: str) -> tuple[str, list[str], str]:
        rows = [{**ROWS[2], "subject": name, "code": f"[10x{i}]"} for i, name in enumerate(("가", "나", "다"))]
        rows.append({**ROWS[2], "subject_group": "수학", "subject": "라", "code": "[10y]"})
        write_dataset(rows, Path(tmp))
        index = (Path(tmp) / "2022/INDEX.md").read_text(encoding="utf-8")
        first = (Path(tmp) / "2022/high/h001.md").read_text(encoding="utf-8")
        names = sorted(path.name for path in (Path(tmp) / "2022/high").glob("*.md"))
        return index, names, first

    def test_same_group_subjects_share_a_file_up_to_the_size_limit(self):
        # claude.ai 스킬은 파일 200개까지만 받는다. 교과군 안의 과목을 크기 상한까지 한 파일에 담는다
        with tempfile.TemporaryDirectory() as tmp:
            index, names, first = self._write_four_subjects(tmp)
        self.assertEqual(names, ["h001.md", "h002.md"])
        for subject in ("가", "나", "다"):
            self.assertIn(f"| 국어 | {subject} | high/h001.md | 1 |", index)
            self.assertIn(f"# 2022 개정 / 고등학교 / 국어 / {subject}", first)
        self.assertIn("| 수학 | 라 | high/h002.md | 1 |", index)     # 교과군이 다르면 새 파일

    def test_a_full_file_starts_a_new_one(self):
        with mock.patch("import_curriculum.MAX_FILE_BYTES", 10), tempfile.TemporaryDirectory() as tmp:
            index, names, _ = self._write_four_subjects(tmp)
        self.assertEqual(names, ["h001.md", "h002.md", "h003.md", "h004.md"])   # 한 과목은 상한보다 커도 쪼개지 않는다
        self.assertIn("| 국어 | 다 | high/h003.md | 1 |", index)

    def test_stale_generated_files_are_removed_but_others_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2022/middle").mkdir(parents=True)
            (root / "2022/middle/m012.md").write_text("지난번 결과", encoding="utf-8")
            (root / "2022/middle/notes.txt").write_text("손으로 쓴 메모", encoding="utf-8")
            write_dataset(ROWS, root)
            self.assertFalse((root / "2022/middle/m012.md").exists())
            self.assertTrue((root / "2022/middle/notes.txt").exists())
            self.assertTrue((root / "2022/middle/m001.md").exists())

    def test_pipes_and_newlines_in_cells_do_not_break_tables(self):
        rows = [{**ROWS[0], "content": "가 | 나\n다음 줄", "subject": "과|학"}]
        page = render_subject("middle", "과학", "과|학", rows)
        self.assertIn("| [9과01-01] | 가 \\| 나 다음 줄 |", page)
        with tempfile.TemporaryDirectory() as tmp:
            write_dataset(rows, Path(tmp))
            index = (Path(tmp) / "2022/INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| 과학 | 과\\|학 | middle/m001.md | 1 |", index)

    def test_all_written_paths_are_ascii(self):
        rows = [{**ROWS[0], "subject_group": "..", "subject": "기술·가정(중학교_공통)"}]
        with tempfile.TemporaryDirectory() as tmp:
            write_dataset(rows, Path(tmp))
            names = [path.relative_to(tmp).as_posix() for path in Path(tmp).rglob("*.md")]
        self.assertTrue(names)
        self.assertTrue(all(name.isascii() for name in names), names)


class MainErrorTest(unittest.TestCase):
    def call_main(self, args, root=None):
        out = io.StringIO()
        out.reconfigure = lambda **kwargs: None
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(out):
            code = main(args, root=root or Path(tmp) / "curriculum")
        return code, out.getvalue()

    def run_with_content(self, content, root=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "standards.json"
            path.write_text(content, encoding="utf-8")
            return self.call_main([str(path)], root)

    def test_success_writes_into_given_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "curriculum"
            code, out = self.run_with_content(json.dumps(ROWS), root)
            self.assertEqual(code, 0)
            self.assertIn("완료: 성취기준 3개", out)
            self.assertTrue((root / "2022/INDEX.md").exists())

    def test_wrong_argument_count_prints_usage(self):
        for args in ([], ["a.json", "b.json"]):
            code, out = self.call_main(args)
            self.assertEqual(code, 2)
            self.assertIn("사용법", out)

    def test_no_matching_rows_is_an_error_and_keeps_old_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "curriculum"
            self.run_with_content(json.dumps(ROWS), root)
            code, out = self.run_with_content(json.dumps([ROWS[3]]), root)
            self.assertEqual(code, 1)
            self.assertIn("입력 오류", out)
            self.assertTrue((root / "2022/middle/m001.md").exists())

    def test_null_or_non_string_fields_report_korean_error(self):
        for key, value in (("content", None), ("subject", None), ("grade_group", 3),
                           ("explanation", 5), ("school_level", ["중학교"])):
            code, out = self.run_with_content(json.dumps([{**ROWS[0], key: value}, ROWS[1]]))
            self.assertEqual(code, 1, key)
            self.assertIn("입력 오류", out)
            self.assertIn(key, out)

    def test_invalid_json_reports_korean_error(self):
        code, out = self.run_with_content("{깨진")
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", out)

    def test_missing_key_reports_korean_error(self):
        code, out = self.run_with_content(json.dumps([{"school_level": "중학교"}]))
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", out)

    def test_non_list_json_reports_korean_error(self):
        code, out = self.run_with_content('{"a": 1}')
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", out)

    def test_missing_file_reports_korean_error(self):
        code, out = self.call_main(["C:/no/such/standards.json"])
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", out)


if __name__ == "__main__":
    unittest.main()
