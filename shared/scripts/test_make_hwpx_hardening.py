"""make_hwpx 입력 검증·경계·CLI 테스트 (코드 리뷰에서 확인된 문제의 회귀 방지)."""

import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import make_hwpx
import make_hwpx_check
from make_hwpx import SKELETON, build_hwpx, main, validate_package


def make_spec(*blocks, **options):
    return {"blocks": list(blocks), **options}


class BuildMixin:
    def build(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "out.hwpx"
        build_hwpx(spec, path)
        with zipfile.ZipFile(path) as archive:
            return path, archive.read("Contents/section0.xml").decode("utf-8")

    def preview(self, spec):
        path, _ = self.build(spec)
        with zipfile.ZipFile(path) as archive:
            return archive.read("Preview/PrvText.txt").decode("utf-8")

    def assertRejects(self, spec, *words):
        with self.assertRaises(ValueError) as caught:
            self.build(spec)
        for word in words:
            self.assertIn(word, str(caught.exception))


def table_block(**extra):
    return {"type": "table", "header": ["a", "b"], "rows": [["1", "2"]], **extra}


class SpecShapeTest(BuildMixin, unittest.TestCase):
    def test_top_level_must_be_object(self):
        for spec in ([], "문자열", 3, None):
            with self.subTest(spec=spec):
                self.assertRejects(spec, "객체")

    def test_blocks_must_be_list(self):
        for blocks in ("abc", {"type": "blank"}, 5):
            with self.subTest(blocks=blocks):
                self.assertRejects({"blocks": blocks}, "blocks", "목록")

    def test_each_block_must_be_object(self):
        self.assertRejects(make_spec({"type": "blank"}, "문자열"), "2번째 블록은 객체")

    def test_title_must_be_text_number_or_null(self):
        for title in (["가"], True, {"a": 1}):
            with self.subTest(title=title):
                self.assertRejects(make_spec(title=title), "title")

    def test_option_types_raise_value_error_not_type_error(self):
        for key, value in (("margins", ["normal"]), ("columns", "2"), ("orientation", ["portrait"]),
                           ("page_numbers", ["center"]), ("margins", 3)):
            with self.subTest(key=key):
                self.assertRejects(make_spec(**{key: value}), key)

    def test_block_limit(self):
        self.assertRejects({"blocks": [{"type": "blank"}] * 2001}, "2000")
        self.build({"blocks": [{"type": "blank"}] * 2000})

    def test_input_spec_is_not_mutated(self):
        import copy
        spec = make_spec({"type": "table", "header": ["a"], "rows": [[{"text": "x", "colspan": 1}]],
                          "widths": [1]}, {"type": "paragraph", "text": "**a**"}, title="t")
        before = copy.deepcopy(spec)
        self.build(spec)
        self.assertEqual(spec, before)


class AllowListTest(BuildMixin, unittest.TestCase):
    def cell_table(self, **cell):
        return {"type": "table", "header": ["a"], "rows": [[{"text": "x", **cell}]]}

    def test_unknown_cell_valign(self):
        self.assertRejects(make_spec(self.cell_table(valign="middle")), "valign", "top")

    def test_unknown_cell_align(self):
        self.assertRejects(make_spec(self.cell_table(align="justify")), "align", "left")

    def test_unknown_paragraph_align(self):
        self.assertRejects(make_spec({"type": "paragraph", "text": "a", "align": "justified"}), "align", "justify")

    def test_unknown_size(self):
        self.assertRejects(make_spec({"type": "paragraph", "text": "a", "size": "huge"}), "size", "small")

    def test_unknown_border(self):
        self.assertRejects(make_spec(table_block(border="dotted")), "border", "solid")

    def test_known_values_and_null_are_accepted(self):
        self.build(make_spec(self.cell_table(valign="bottom", align="right"),
                             {"type": "paragraph", "text": "a", "align": None, "size": None}))

    def test_attribute_values_are_escaped_as_backstop(self):
        with zipfile.ZipFile(SKELETON) as archive:
            header = archive.read("Contents/header.xml").decode("utf-8")
        _, styles = make_hwpx.prepare_header(header)
        writer = make_hwpx.SectionWriter(styles, 40000)
        cell = make_hwpx.TableCell("x", 0, 0, 1, 1, False, False, False, "left", '"><evil/>', 0)
        xml = writer._cell(cell, 1000, 1000, "center")
        self.assertNotIn('"><evil', xml)


class IntOptionTest(BuildMixin, unittest.TestCase):
    def test_helper_bounds(self):
        self.assertEqual(make_hwpx._int_option(3, "x", 1, 5), 3)
        for bad in (True, 2.0, "3", None, 0, 6):
            with self.subTest(bad=bad), self.assertRaises(ValueError) as caught:
                make_hwpx._int_option(bad, "x", 1, 5)
            self.assertIn("x", str(caught.exception))

    def test_answer_box_lines(self):
        for lines in (0, 51, True, "3", 2.5, -1):
            with self.subTest(lines=lines):
                self.assertRejects(make_spec({"type": "answer_box", "lines": lines}), "lines")
        self.build(make_spec({"type": "answer_box", "lines": 50}, {"type": "answer_box"}))

    def test_cell_lines(self):
        for lines in (51, True, -1, 1.5):
            with self.subTest(lines=lines):
                self.assertRejects(make_spec({"type": "table", "header": ["a"], "rows": [[{"lines": lines}]]}),
                                   "lines")

    def test_header_rows(self):
        for value in (2, -1, True, 1.5, "1"):
            with self.subTest(value=value):
                self.assertRejects(make_spec(table_block(header_rows=value)), "header_rows")
        self.build(make_spec(table_block(header_rows=1)))

    def test_columns_must_be_exact_int(self):
        for value in (2.0, True, 3, 0):
            with self.subTest(value=value):
                self.assertRejects(make_spec(columns=value), "columns")

    def test_header_blocks(self):
        for value in (True, 3, -1, 1.0, "1"):
            with self.subTest(value=value):
                self.assertRejects(make_spec({"type": "blank"}, columns=2, header_blocks=value), "header_blocks")

    def test_heading_level(self):
        for level in (0, 7, True, "1", 1.5):
            with self.subTest(level=level):
                self.assertRejects(make_spec({"type": "heading", "text": "a", "level": level}), "level")
        _, section = self.build(make_spec({"type": "heading", "text": "a", "level": 3}))
        self.assertIn("a", section)

    def test_widths_reject_bad_numbers(self):
        for widths in ([True, 1], [float("inf"), 1], [float("nan"), 1], [0, 1], [-1, 2], ["1", 1],
                       [1e-9, 1], [1e308, 1e308]):
            with self.subTest(widths=widths):
                self.assertRejects(make_spec(table_block(widths=widths)), "widths")

    def test_widths_must_be_list(self):
        self.assertRejects(make_spec(table_block(widths="12")), "widths")


class TableCapTest(BuildMixin, unittest.TestCase):
    def test_span_caps(self):
        for key in ("colspan", "rowspan"):
            with self.subTest(key=key):
                self.assertRejects(make_spec({"type": "table", "rows": [[{"text": "a", key: 51}]]}), key, "50")

    def test_row_cap(self):
        rows = [["x"]] * 501
        self.assertRejects(make_spec({"type": "table", "rows": rows}), "500")

    def test_column_cap(self):
        self.assertRejects(make_spec({"type": "table", "rows": [["x"] * 31]}), "30")

    def test_cell_count_per_row_is_checked_before_layout(self):
        self.assertRejects(make_spec({"type": "table", "rows": [["x"] * 100000]}), "30")

    def test_rows_must_be_lists(self):
        self.assertRejects(make_spec({"type": "table", "rows": ["abc"]}), "행")

    def test_maximum_table_is_accepted(self):
        self.build(make_spec({"type": "table", "rows": [["x"] * 30] * 500}))


class InlineThresholdTest(BuildMixin, unittest.TestCase):
    def rows(self, count):
        return make_spec({"type": "table", "rows": [["x"] for _ in range(count)]})

    def test_height_equal_to_threshold_stays_inline(self):
        with mock.patch("make_hwpx.INLINE_TABLE_MAX_HEIGHT", make_hwpx.ROW_HEIGHT * 3):
            self.assertIn('treatAsChar="1"', self.build(self.rows(3))[1])
            self.assertIn('treatAsChar="0"', self.build(self.rows(4))[1])

    def test_real_threshold_between_eight_and_nine_default_rows(self):
        self.assertIn('treatAsChar="1"', self.build(self.rows(8))[1])
        self.assertIn('treatAsChar="0"', self.build(self.rows(9))[1])


class MarkupBoundaryTest(BuildMixin, unittest.TestCase):
    def preview_of(self, text):
        return self.preview(make_spec({"type": "paragraph", "text": text}))

    def test_double_underscore_inside_word_is_literal(self):
        self.assertIn("snake__case__name", self.preview_of("snake__case__name"))
        _, section = self.build(make_spec({"type": "paragraph", "text": "snake__case__name"}))
        self.assertIn("snake__case__name</hp:t>", section)

    def test_double_star_inside_expression_is_literal(self):
        self.assertIn("2**3**4", self.preview_of("2**3**4"))

    def test_normal_markup_still_works(self):
        self.assertIn("굵게 그리고 밑줄", self.preview_of("**굵게** 그리고 __밑줄__"))

    def test_markup_followed_by_korean_particle_still_works(self):
        self.assertEqual(self.preview_of("**도시락**과 __회신__까지").strip(), "도시락과 회신까지")


class PreviewCleanTest(BuildMixin, unittest.TestCase):
    def test_control_characters_are_removed_everywhere(self):
        preview = self.preview(make_spec(
            {"type": "paragraph", "text": "문\x0b단"}, {"type": "heading", "text": "제\x01목"},
            {"type": "table", "header": ["머\x0c리"], "rows": [["칸\x02"]]},
            {"type": "bullets", "items": ["항\x0b목"]}, title="큰\x0b제목"))
        for ch in ("\x0b", "\x01", "\x0c", "\x02"):
            self.assertNotIn(ch, preview)
        self.assertIn("큰제목", preview)


class SafeWriteTest(BuildMixin, unittest.TestCase):
    def test_existing_tmp_named_file_is_not_clobbered(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stale = Path(tmp.name) / "out.hwpx.tmp"
        stale.write_text("keep", encoding="utf-8")
        build_hwpx(make_spec(), Path(tmp.name) / "out.hwpx")
        self.assertEqual(stale.read_text(encoding="utf-8"), "keep")

    def test_failed_replace_leaves_no_temp_file(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch("make_hwpx_save.os.replace", side_effect=PermissionError("열려 있음")):
            with self.assertRaises(PermissionError):
                build_hwpx(make_spec(), Path(tmp.name) / "out.hwpx")
        self.assertEqual(list(Path(tmp.name).iterdir()), [])


class SkeletonShapeTest(unittest.TestCase):
    def setUp(self):
        with zipfile.ZipFile(SKELETON) as archive:
            _, self.styles = make_hwpx.prepare_header(archive.read("Contents/header.xml").decode("utf-8"))

    def test_section_run_without_secpr(self):
        with self.assertRaises(ValueError) as caught:
            make_hwpx._section_run("<hs:sec></hs:sec>", 8504)
        self.assertIn("골격 section0.xml 형식이 예상과 다름", str(caught.exception))

    def test_build_section_without_sec_element(self):
        with self.assertRaises(ValueError) as caught:
            make_hwpx.build_section(make_spec(), self.styles, "<nothing/>")
        self.assertIn("골격 section0.xml 형식이 예상과 다름", str(caught.exception))


class CheckModuleTest(unittest.TestCase):
    def write_zip(self, path, section: bytes):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), make_hwpx.MIMETYPE, compress_type=zipfile.ZIP_STORED)
            archive.writestr("Contents/header.xml", b"<a/>", compress_type=zipfile.ZIP_DEFLATED)
            archive.writestr("Contents/section0.xml", section, compress_type=zipfile.ZIP_DEFLATED)
            archive.writestr("Contents/content.hpf", b"<a/>", compress_type=zipfile.ZIP_DEFLATED)

    def test_validate_package_is_reexported_from_check_module(self):
        self.assertIs(make_hwpx.validate_package, make_hwpx_check.validate_package)

    def test_oversized_entry_is_refused_before_reading(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "big.hwpx"
        self.write_zip(path, b"<a>" + b" " * make_hwpx_check.MAX_ENTRY_BYTES + b"</a>")
        with mock.patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("읽으면 안 됨")):
            problems = validate_package(path)
        self.assertTrue(any("너무 큼" in problem for problem in problems))

    def test_entry_at_limit_is_still_read(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "small.hwpx"
        self.write_zip(path, b"<a/>")
        self.assertFalse(any("너무 큼" in problem for problem in validate_package(path)))


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

    def write_json(self, text, name="in.json"):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_spec_builds_and_checks(self):
        source = self.write_json('{"title": "t", "blocks": [{"type": "paragraph", "text": "a"}]}')
        output = self.dir / "o.hwpx"
        code, text = self.run_main(source, output)
        self.assertEqual((code, output.exists()), (0, True))
        self.assertIn("완료", text)
        code, text = self.run_main("--check", output)
        self.assertEqual(code, 0)
        self.assertIn("통과", text)

    def test_rebuilding_its_own_file_is_allowed(self):
        source = self.write_json('{"blocks": [{"type": "paragraph", "text": "첫 판"}]}')
        output = self.dir / "o.hwpx"
        self.assertEqual(self.run_main(source, output)[0], 0)
        source.write_text('{"blocks": [{"type": "paragraph", "text": "둘째 판"}]}', encoding="utf-8")
        self.assertEqual(self.run_main(source, output)[0], 0)
        with zipfile.ZipFile(output) as archive:
            self.assertIn("둘째 판", archive.read("Contents/section0.xml").decode("utf-8"))

    def test_other_files_are_never_overwritten(self):
        source = self.write_json('{"blocks": [{"type": "paragraph", "text": "a"}]}')
        own = self.dir / "own.hwpx"
        self.assertEqual(self.run_main(source, own)[0], 0)
        with zipfile.ZipFile(own) as archive:          # 한글에서 다시 저장하면 마지막 저장자가 바뀐다
            entries = {name: archive.read(name) for name in archive.namelist()}
        entries["Contents/content.hpf"] = entries["Contents/content.hpf"].replace(
            b'"lastsaveby" content="text">teacher-kit', b'"lastsaveby" content="text">someone')
        resaved = self.dir / "resaved.hwpx"
        with zipfile.ZipFile(resaved, "w") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        plain = self.dir / "plain.hwpx"
        plain.write_bytes(b"not a zip")
        for target in (resaved, plain):
            with self.subTest(target=target.name):
                before = target.read_bytes()
                code, out = self.run_main(source, target)
                self.assertEqual(code, 1)
                self.assertIn("덮어쓰지 않음", out)
                self.assertEqual(target.read_bytes(), before)

    def test_top_level_list_and_string_json(self):
        for text in ("[]", '"abc"', "3"):
            with self.subTest(text=text):
                code, out = self.run_main(self.write_json(text), self.dir / "o.hwpx")
                self.assertEqual(code, 1)
                self.assertIn("입력 오류", out)
                self.assertIn("객체", out)

    def test_check_of_bad_file(self):
        bad = self.dir / "bad.hwpx"
        bad.write_bytes(b"not a zip")
        code, out = self.run_main("--check", bad)
        self.assertEqual(code, 1)
        self.assertIn("파일 구조 오류", out)

    def test_missing_input_file(self):
        code, out = self.run_main(self.dir / "없음.json", self.dir / "o.hwpx")
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", out)

    def test_malformed_json(self):
        code, out = self.run_main(self.write_json("{"), self.dir / "o.hwpx")
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", out)

    def test_wrong_argument_count(self):
        for args in ([], ["a.json"], ["a", "b", "c"], ["--check"]):
            with self.subTest(args=args):
                code, out = self.run_main(*args)
                self.assertEqual(code, 2)
                self.assertIn("사용법", out)

    def test_unexpected_exception_becomes_internal_error(self):
        source = self.write_json("{}")
        with mock.patch("make_hwpx.build_hwpx", side_effect=ZeroDivisionError("x")):
            code, out = self.run_main(source, self.dir / "o.hwpx")
        self.assertEqual(code, 1)
        self.assertIn("내부 오류: 예상하지 못한 입력입니다 (ZeroDivisionError)", out)

    def test_permission_error_hints_to_close_hancom(self):
        source = self.write_json("{}")
        with mock.patch("make_hwpx.build_hwpx", side_effect=PermissionError("denied")):
            code, out = self.run_main(source, self.dir / "o.hwpx")
        self.assertEqual(code, 1)
        self.assertIn("출력 오류: 한글에서 파일이 열려 있으면 닫고 다시 실행해 주세요", out)

    def test_other_write_failure_is_output_error(self):
        source = self.write_json("{}")
        with mock.patch("make_hwpx.build_hwpx", side_effect=OSError("디스크 가득")):
            code, out = self.run_main(source, self.dir / "o.hwpx")
        self.assertEqual(code, 1)
        self.assertIn("출력 오류", out)

    def test_deeply_nested_json_is_reported_not_crashed(self):
        source = self.write_json("[" * 200000 + "]" * 200000)
        code, out = self.run_main(source, self.dir / "o.hwpx")
        self.assertEqual(code, 1)
        self.assertTrue(out.strip())

    def test_works_when_stdout_cannot_be_reconfigured(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = main(["--check", str(self.dir / "없음.hwpx")])
        self.assertEqual(code, 1)


# ---------------------------------------------------------------- 2차 코드 리뷰 회귀 방지

class XmlForbiddenCharTest(BuildMixin, unittest.TestCase):
    def test_noncharacters_fffe_ffff_are_removed(self):
        preview = self.preview(make_spec({"type": "paragraph", "text": "a￾b￿c"}, title="제￾목"))
        self.assertIn("abc", preview)
        self.assertIn("제목", preview)


class ListItemTextTest(BuildMixin, unittest.TestCase):
    def test_bullets_and_numbered_accept_text_objects(self):
        preview = self.preview(make_spec({"type": "bullets", "items": [{"text": "모자"}, 3]},
                                         {"type": "numbered", "items": [{"text": "출발"}]}))
        self.assertIn("• 모자", preview)
        self.assertIn("• 3", preview)
        self.assertIn("1. 출발", preview)
        self.assertNotIn("{", preview)

    def test_null_items_are_rejected_in_every_list_block(self):
        for kind in ("bullets", "numbered", "outline"):
            for items in (["가", None], ["가", {"level": 2}]):
                with self.subTest(kind=kind, items=items):
                    self.assertRejects(make_spec({"type": kind, "items": items}), "2번째 항목")


class OutlineLevelTest(BuildMixin, unittest.TestCase):
    def test_non_integer_and_out_of_range_levels_are_rejected(self):
        for level in (float("inf"), 2.7, "2", 0, 7, True):
            with self.subTest(level=level):
                self.assertRejects(make_spec({"type": "outline", "items": [{"text": "가", "level": level}]}),
                                   "level")

    def test_missing_or_null_level_is_first_level(self):
        preview = self.preview(make_spec({"type": "outline", "items": [{"text": "가", "level": None}, "나"]}))
        self.assertIn("1. 가", preview)
        self.assertIn("2. 나", preview)


class HangulOrderTest(unittest.TestCase):
    def test_markers_continue_with_geo_neo_after_ha(self):
        marker = make_hwpx._outline_marker
        self.assertEqual([marker(2, n) for n in (14, 15, 16, 28)], ["하.", "거.", "너.", "허."])
        self.assertEqual(marker(4, 15), "거)")
        self.assertEqual(marker(6, 15), "(거)")
        self.assertEqual(marker(2, 29), "29.")


class CellBooleanTest(BuildMixin, unittest.TestCase):
    def cell_table(self, **cell):
        return make_spec({"type": "table", "rows": [[{"text": "x", **cell}]]})

    def test_string_booleans_are_rejected(self):
        for key in ("header", "shade", "bold"):
            for value in ("false", "true", 0, 1):
                with self.subTest(key=key, value=value):
                    self.assertRejects(self.cell_table(**{key: value}), key)

    def test_real_booleans_and_null_are_accepted(self):
        _, section = self.build(self.cell_table(header=False, shade=None, bold=True))
        self.assertIn('header="0"', section)

    def test_keep_with_next_rejects_string_booleans(self):
        for block in ({"type": "paragraph", "text": "x"}, {"type": "table", "rows": [["x"]]}):
            for value in ("false", "true", 0, 1):
                with self.subTest(type=block["type"], value=value):
                    self.assertRejects(make_spec({**block, "keep_with_next": value}), "keep_with_next")

    def test_keep_with_next_accepts_booleans_and_null(self):
        for block in ({"type": "paragraph", "text": "x"}, {"type": "table", "rows": [["x"]]}):
            for value in (True, False, None):
                with self.subTest(type=block["type"], value=value):
                    self.build(make_spec({**block, "keep_with_next": value}))


class LayoutChoiceTest(BuildMixin, unittest.TestCase):
    def test_layout_options_are_case_insensitive(self):
        _, section = self.build(make_spec(margins="Narrow", orientation="LANDSCAPE", page_numbers="Center"))
        self.assertIn('left="4252" right="4252"', section)
        self.assertIn('landscape="NARROWLY"', section)
        self.assertIn("<hp:footer", section)

    def test_empty_and_null_mean_default_for_every_layout_option(self):
        for value in ("", None):
            with self.subTest(value=value):
                _, section = self.build(make_spec(margins=value, orientation=value, page_numbers=value))
                self.assertIn('left="8504" right="8504"', section)
                self.assertIn('landscape="WIDELY"', section)
                self.assertNotIn("<hp:footer", section)

    def test_unknown_values_still_rejected(self):
        for key in ("margins", "orientation", "page_numbers"):
            with self.subTest(key=key):
                self.assertRejects(make_spec(**{key: "wide"}), key)


class DocTitleTest(BuildMixin, unittest.TestCase):
    def metadata(self, spec):
        path, _ = self.build(spec)
        with zipfile.ZipFile(path) as archive:
            return archive.read("Contents/content.hpf").decode("utf-8")

    def test_markup_is_removed_from_title_and_doc_title(self):
        for key in ("title", "doc_title"):
            with self.subTest(key=key):
                metadata = self.metadata(make_spec(**{key: "**공지** __회신__ {{1/2}}"}))
                self.assertIn("공지 회신 1/2", metadata)
                self.assertNotIn("**", metadata)


class OutputModeTest(BuildMixin, unittest.TestCase):
    def test_output_permissions_follow_umask_not_temp_file_0600(self):
        import os
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        umask = os.umask(0)
        os.umask(umask)
        with mock.patch("make_hwpx_save.os.chmod", wraps=os.chmod) as chmod:
            build_hwpx(make_spec(), Path(tmp.name) / "out.hwpx")
        self.assertEqual(chmod.call_args.args[1], 0o666 & ~umask)

    @unittest.skipUnless(hasattr(__import__("os"), "getuid"), "POSIX 권한 비트는 POSIX에서만 확인")
    def test_output_is_readable_by_group_and_others_on_posix(self):
        import os
        import stat
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        old = os.umask(0o022)
        try:
            build_hwpx(make_spec(), Path(tmp.name) / "out.hwpx")
        finally:
            os.umask(old)
        self.assertEqual(stat.S_IMODE((Path(tmp.name) / "out.hwpx").stat().st_mode), 0o644)


class TableLayoutErrorTest(BuildMixin, unittest.TestCase):
    def test_colspan_past_column_cap(self):
        row = ["x"] * (make_hwpx.MAX_TABLE_COLS - 1) + [{"text": "넘침", "colspan": 2}]
        self.assertRejects(make_spec({"type": "table", "rows": [row]}), "표 너비를 넘음")

    def test_colspan_overlapping_rowspan_from_above(self):
        rows = [["a", {"text": "b", "rowspan": 2}], [{"text": "c", "colspan": 2}]]
        self.assertRejects(make_spec({"type": "table", "rows": rows}), "겹침")

    def test_empty_table(self):
        for block in ({"type": "table"}, {"type": "table", "rows": [[]]}, {"type": "table", "header": []}):
            with self.subTest(block=block):
                self.assertRejects(make_spec(block), "표에 행이나 칸이 없음")


class SkeletonHeaderShapeTest(unittest.TestCase):
    def test_missing_container(self):
        with self.assertRaises(ValueError) as caught:
            make_hwpx._append_items("<hh:head/>", "borderFills", [])
        self.assertIn("borderFills", str(caught.exception))

    def test_font_groups_not_as_expected(self):
        with self.assertRaises(ValueError) as caught:
            make_hwpx._add_font('<hh:fontface lang="HANGUL" fontCnt="1"></hh:fontface>')
        self.assertIn("글꼴 그룹", str(caught.exception))


class CorruptedPackageTest(unittest.TestCase):
    """일부러 망가뜨린 hwpx로 --check 검사 항목을 하나씩 확인한다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.good = Path(cls.tmp.name) / "good.hwpx"
        build_hwpx(make_spec(table_block()), cls.good)
        with zipfile.ZipFile(cls.good) as archive:
            cls.entries = {info.filename: archive.read(info.filename) for info in archive.infolist()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rewrite(self, edit=lambda section: section, mimetype=make_hwpx.MIMETYPE, mimetype_first=True):
        path = Path(self.tmp.name) / f"{self._testMethodName}.hwpx"
        section = edit(self.entries["Contents/section0.xml"].decode("utf-8")).encode("utf-8")
        others = [(name, section if name == "Contents/section0.xml" else data)
                  for name, data in self.entries.items() if name != "mimetype"]
        with zipfile.ZipFile(path, "w") as archive:
            if not mimetype_first:
                archive.writestr(*others.pop(0), compress_type=zipfile.ZIP_DEFLATED)
            archive.writestr(zipfile.ZipInfo("mimetype"), mimetype, compress_type=zipfile.ZIP_STORED)
            for name, data in others:
                archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
        return validate_package(path)

    def assertProblem(self, problems, word):
        self.assertTrue(any(word in problem for problem in problems), problems)

    def test_untouched_copy_passes(self):
        self.assertEqual(self.rewrite(), [])

    def test_row_count_mismatch(self):
        self.assertProblem(self.rewrite(lambda s: s.replace('rowCnt="2"', 'rowCnt="3"')), "rowCnt 불일치")

    def test_cell_width_sum_mismatch(self):
        import re
        edit = lambda s: re.sub(r'<hp:cellSz width="(\d+)"',  # noqa: E731
                                lambda m: f'<hp:cellSz width="{int(m.group(1)) + 1}"', s, count=1)
        self.assertProblem(self.rewrite(edit), "칸 너비 합")

    def test_mimetype_not_first(self):
        self.assertProblem(self.rewrite(mimetype_first=False), "mimetype이 첫 항목")

    def test_mimetype_content(self):
        self.assertProblem(self.rewrite(mimetype=b"application/zip"), "mimetype 내용이 다름")

    def test_unexpected_value_during_structure_check(self):
        self.assertProblem(self.rewrite(lambda s: s.replace('rowCnt="2"', 'rowCnt="둘"')),
                           "구조 검사 중 예상하지 못한 형식")

    def test_encrypted_entry_is_reported_not_raised(self):
        data = bytearray(self.good.read_bytes())
        central = data.index(b"PK\x01\x02")          # 첫 중앙 디렉터리 항목(mimetype)
        data[central + 8] |= 0x01                    # 일반 목적 플래그의 암호화 비트
        path = Path(self.tmp.name) / "locked.hwpx"
        path.write_bytes(bytes(data))
        problems = validate_package(path)
        self.assertProblem(problems, "암호")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--check", str(path)]), 1)
        self.assertIn("암호", out.getvalue())

    def write_parts(self, name: str, changes: dict) -> Path:
        """좋은 파일의 항목을 바꾸거나 더해 새 파일로 쓴다."""
        path = Path(self.tmp.name) / name
        entries = {**self.entries, **changes}
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), entries.pop("mimetype"), compress_type=zipfile.ZIP_STORED)
            for entry, data in entries.items():
                archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED)
        return path

    def broken_section(self) -> bytes:
        return self.entries["Contents/section0.xml"].replace(b'charPrIDRef="', b'charPrIDRef="9', 1)

    def test_big_picture_does_not_hide_other_problems(self):
        big = b"\0" * (make_hwpx_check.MAX_ENTRY_BYTES + 1)
        self.assertEqual(validate_package(self.write_parts("그림.hwpx", {"BinData/image1.bmp": big})), [])
        problems = validate_package(self.write_parts("그림깨짐.hwpx", {
            "BinData/image1.bmp": big, "Contents/section0.xml": self.broken_section()}))
        self.assertProblem(problems, "정의 없음")

    def test_every_section_is_checked(self):
        problems = validate_package(self.write_parts("둘.hwpx", {"Contents/section1.xml": self.broken_section()}))
        self.assertProblem(problems, "section1: charPrIDRef")
        self.assertFalse(any(problem.startswith("section0") for problem in problems), problems)

    def test_oversized_section_is_named_and_the_rest_still_checked(self):
        huge = b"<a>" + b" " * make_hwpx_check.MAX_ENTRY_BYTES + b"</a>"
        problems = validate_package(self.write_parts("큰구역.hwpx", {
            "Contents/section0.xml": self.broken_section(), "Contents/section1.xml": huge}))
        self.assertProblem(problems, "너무 큼")
        self.assertProblem(problems, "Contents/section1.xml")
        self.assertProblem(problems, "정의 없음")

    def test_lying_size_in_header_is_reported(self):
        from test_make_hwpx_zip import lie_about_size
        path = self.write_parts("속임.hwpx", {})
        lie_about_size(path, "Contents/header.xml", 10)
        problems = validate_package(path)
        self.assertTrue(problems)
        self.assertProblem(problems, "손상")

if __name__ == "__main__":
    unittest.main()
