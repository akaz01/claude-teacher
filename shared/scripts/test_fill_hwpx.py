"""fill_hwpx.py 시험: 교사 양식의 모양을 지키고 지정한 자리의 글만 바꾸는지 본다."""

import json
import re
import tempfile
import tracemalloc
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

import fill_hwpx
from fill_hwpx import FillError, fill_form, inspect_form, main
from make_hwpx import build_hwpx, validate_package
from make_hwpx_save import BLANK_PNG
from test_make_hwpx_zip import BOMB_BYTES, PEAK_LIMIT, lie_about_size

SECTION = "Contents/section0.xml"
LINESEG = ('<hp:linesegarray><hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" '
           'baseline="850" spacing="600" horzpos="0" horzsize="42520" flags="393216"/></hp:linesegarray>')
OPEN_P = '<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'


def para(*runs: str) -> str:
    return f'{OPEN_P}{"".join(runs)}{LINESEG}</hp:p>'


def run(inner: str = "", char: int = 0) -> str:
    return f'<hp:run charPrIDRef="{char}">{inner}</hp:run>'


def text(value: str, char: int = 0) -> str:
    return run(f"<hp:t>{value}</hp:t>", char)


def cell(row: int, col: int, *paragraphs: str, row_span: int = 1, col_span: int = 1) -> str:
    return ('<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="1">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER">{"".join(paragraphs)}'
            f'</hp:subList><hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
            f'<hp:cellSpan colSpan="{col_span}" rowSpan="{row_span}"/>'
            f'<hp:cellSz width="{1000 * col_span}" height="1000"/>'
            '<hp:cellMargin left="510" right="510" top="141" bottom="141"/></hp:tc>')


def table(rows: list[list[str]], cols: int = 2) -> str:
    body = "".join(f'<hp:tr>{"".join(row)}</hp:tr>' for row in rows)
    return (f'<hp:tbl id="7" zOrder="0" numberingType="TABLE" rowCnt="{len(rows)}" colCnt="{cols}" '
            f'cellSpacing="0" borderFillIDRef="1"><hp:sz width="{1000 * cols}" widthRelTo="ABSOLUTE" '
            f'height="{1000 * len(rows)}" heightRelTo="ABSOLUTE" protect="0"/>{body}</hp:tbl>')


class FormCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = Path(holder.name)
        self.result = self.folder / "결과.hwpx"

    def form(self, *body: str, extra_sections: tuple[str, ...] = ()) -> Path:
        """시험용 양식: make_hwpx 골격의 끝에 손으로 쓴 문단을 붙인다."""
        base = self.folder / "base.hwpx"
        build_hwpx({"blocks": [{"type": "paragraph", "text": "첫 문단"}]}, base)
        source = self.folder / "양식.hwpx"
        with zipfile.ZipFile(base) as archive, zipfile.ZipFile(source, "w") as out:
            original = archive.read(SECTION).decode("utf-8")
            head = re.match(r"(?s).*?<hs:sec[^>]*>", original).group(0)
            for info in archive.infolist():
                data = archive.read(info.filename)
                if info.filename == SECTION:
                    data = original.replace("</hs:sec>", "".join(body) + "</hs:sec>").encode("utf-8")
                out.writestr(info, data, compress_type=info.compress_type)
            for number, section in enumerate(extra_sections, start=1):
                out.writestr(f"Contents/section{number}.xml", f"{head}{section}</hs:sec>", zipfile.ZIP_DEFLATED)
        self.assertEqual(validate_package(source), [])
        return source

    def fill(self, source: Path, *fills: dict) -> str:
        fill_form(source, {"fills": list(fills)}, self.result)
        self.assertEqual(validate_package(self.result), [])
        return self.read(self.result)

    @staticmethod
    def read(path: Path, name: str = SECTION) -> str:
        with zipfile.ZipFile(path) as archive:
            return archive.read(name).decode("utf-8")

    def refused(self, source: Path, spec: dict, *expected: str) -> None:
        with self.assertRaises(FillError) as caught:
            fill_form(source, spec, self.result)
        for phrase in expected:
            self.assertIn(phrase, str(caught.exception))
        self.assertFalse(self.result.exists())


class InspectTest(FormCase):
    def test_lists_numbered_paragraphs_and_cells(self):
        source = self.form(para(text("단원: ○○")), para(run(table([
            [cell(0, 0, para(text("구분"))), cell(0, 1, para(run()))],
            [cell(1, 0, para(text("합침")), col_span=2)],
        ]))))
        listing = inspect_form(source)
        self.assertIn("문단 1: (빈 줄)", listing)      # 골격의 첫 문단은 구역 설정만 가진다
        self.assertIn("문단 2: 첫 문단", listing)
        self.assertIn("문단 3: 단원: ○○", listing)
        self.assertIn("문단 4: [표·그림]", listing)
        self.assertIn("표 1 (2행 × 2칸)", listing)
        self.assertIn("표 1 행 1 칸 1: 구분", listing)
        self.assertIn("표 1 행 1 칸 2: (빈 칸)", listing)
        self.assertIn("표 1 행 2 칸 1 [합침 1행 × 2칸]: 합침", listing)

    def test_numbers_nested_tables_and_all_sections(self):
        inner = table([[cell(0, 0, para(text("안쪽"))), cell(0, 1, para(run()))]])
        source = self.form(
            para(run(table([[cell(0, 0, para(run(inner))), cell(0, 1, para(text("바깥")))]]))),
            extra_sections=(para(text("둘째 구역")) + para(run(table([[cell(0, 0, para(text("셋째 표"))),
                                                                   cell(0, 1, para(run()))]]))),))
        listing = inspect_form(source)
        self.assertIn("표 2 행 1 칸 1: 안쪽", listing)
        self.assertIn("표 3 행 1 칸 1: 셋째 표", listing)
        self.assertIn("구역 2", listing)
        self.assertIn("둘째 구역", listing)

    def test_labels_text_outside_the_body(self):
        memo = ('<hp:ctrl><hp:fieldBegin id="1" type="MEMO" name=""><hp:subList>'
                f'{para(text("메모 글"))}</hp:subList></hp:fieldBegin></hp:ctrl>')
        box = f'<hp:rect id="2"><hp:drawText><hp:subList>{para(text("상자 글"))}</hp:subList></hp:drawText></hp:rect>'
        source = self.form(para(run(memo), text("본문 글"), run(box)))
        listing = inspect_form(source)
        self.assertIn("[글상자]: 상자 글", listing)
        self.assertIn("[메모]: 메모 글", listing)


class FindReplaceTest(FormCase):
    def test_changes_only_the_text_and_leaves_every_other_part_alone(self):
        source = self.form(para(text("단원: ○○", 3)), para(text("그대로")))
        filled = self.fill(source, {"find": "○○", "replace": "일차방정식"})
        self.assertIn('<hp:run charPrIDRef="3"><hp:t>단원: 일차방정식</hp:t></hp:run>', filled)
        before = self.read(source)
        self.assertEqual(filled.replace("단원: 일차방정식", "단원: ○○"), before.replace(
            para(text("단원: ○○", 3)), para(text("단원: ○○", 3)).replace(LINESEG, "")))
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(self.result) as new:
            self.assertEqual([i.filename for i in old.infolist()], [i.filename for i in new.infolist()])
            self.assertEqual(new.infolist()[0].filename, "mimetype")
            self.assertEqual(new.infolist()[0].compress_type, zipfile.ZIP_STORED)
            for name in old.namelist():
                if name not in (SECTION, "Preview/PrvText.txt", "Preview/PrvImage.png"):
                    self.assertEqual(old.read(name), new.read(name), name)

    def test_drops_line_layout_only_of_the_changed_paragraph(self):
        source = self.form(para(text("바꿀 글")), para(text("둘")))
        filled = self.fill(source, {"find": "바꿀", "replace": "새로 넣는 긴 글"})
        self.assertEqual(filled.count("<hp:linesegarray>"), self.read(source).count("<hp:linesegarray>") - 1)
        self.assertIn(para(text("둘")), filled)

    def test_keeps_line_layout_when_one_line_text_does_not_grow(self):
        source = self.form(para(text("선택형(26문항)")))
        filled = self.fill(source, {"find": "26", "replace": "20"})
        self.assertIn("선택형(20문항)", filled)
        self.assertEqual(filled.count("<hp:linesegarray>"), 1)

    def test_match_across_runs_keeps_the_first_run_style(self):
        source = self.form(para(text("앞 ○", 3), text("○ 뒤", 4)))
        filled = self.fill(source, {"find": "○○", "replace": "글"})
        self.assertIn('<hp:run charPrIDRef="3"><hp:t>앞 글</hp:t></hp:run>', filled)
        self.assertIn('<hp:run charPrIDRef="4"><hp:t> 뒤</hp:t></hp:run>', filled)

    def test_special_spaces_match_a_plain_space(self):
        source = self.form(para(run("<hp:t>가<hp:fwSpace/>나<hp:nbSpace/>다</hp:t>")))
        filled = self.fill(source, {"find": "가 나 다", "replace": "라"})
        self.assertIn("<hp:t>라</hp:t>", filled)

    def test_zero_width_marks_survive_a_replacement(self):
        source = self.form(para(run('<hp:t>앞<hp:markpenBegin color="#FFFF00"/>글<hp:markpenEnd/>뒤</hp:t>')))
        filled = self.fill(source, {"find": "앞글뒤", "replace": "새"})
        self.assertIn('<hp:markpenBegin color="#FFFF00"/>', filled)
        self.assertIn("<hp:markpenEnd/>", filled)

    def test_entities_are_read_and_written_safely(self):
        source = self.form(para(text("A &amp; B")))
        filled = self.fill(source, {"find": "A & B", "replace": "<가> & 나"})
        self.assertIn("&lt;가&gt; &amp; 나", filled)
        ElementTree.fromstring(filled)

    def test_new_line_becomes_a_line_break_in_the_same_paragraph(self):
        filled = self.fill(self.form(para(text("자리"))), {"find": "자리", "replace": "하나\n둘"})
        self.assertIn("<hp:t>하나<hp:lineBreak/>둘</hp:t>", filled)

    def test_finds_text_inside_table_cells(self):
        source = self.form(para(run(table([[cell(0, 0, para(text("칸 ○○"))), cell(0, 1, para(run()))]]))))
        self.assertIn("칸 글", self.fill(source, {"find": "○○", "replace": "글"}))

    def test_memo_text_is_not_a_fill_target(self):
        memo = ('<hp:ctrl><hp:fieldBegin id="1" type="MEMO" name=""><hp:subList>'
                f'{para(text("○○ 메모"))}</hp:subList></hp:fieldBegin></hp:ctrl>')
        filled = self.fill(self.form(para(run(memo), text("○○"))), {"find": "○○", "replace": "글"})
        self.assertIn("○○ 메모", filled)

    def test_match_does_not_cross_an_object(self):
        source = self.form(para(text("가"), run('<hp:equation id="1"><hp:script>x</hp:script></hp:equation>'), text("나")))
        self.refused(source, {"fills": [{"find": "가나", "replace": "다"}]}, "찾지 못함")

    def test_all_fill_targets_are_read_from_the_original_form(self):
        source = self.form(para(text("가")), para(text("나")))
        filled = self.fill(source, {"find": "가", "replace": "나 하나"}, {"find": "나", "replace": "다", "nth": 1})
        self.assertIn("<hp:t>나 하나</hp:t>", filled)
        self.assertIn("<hp:t>다</hp:t>", filled)

    def test_two_targets_in_one_paragraph(self):
        filled = self.fill(self.form(para(text("가 나"))), {"find": "가", "replace": "1"}, {"find": "나", "replace": "2"})
        self.assertIn("<hp:t>1 2</hp:t>", filled)

    def test_several_matches_need_a_choice(self):
        source = self.form(para(text("○○")), para(run(table([[cell(0, 0, para(text("○○"))),
                                                           cell(0, 1, para(run()))]]))))
        self.refused(source, {"fills": [{"find": "○○", "replace": "글"}]}, "2곳", "문단 3", "표 1 행 1 칸 1")

    def test_all_replaces_every_match(self):
        source = self.form(para(text("○ ○")), para(text("○")))
        filled = self.fill(source, {"find": "○", "replace": "글", "all": True})
        self.assertNotIn("○", filled)

    def test_nth_replaces_one_match(self):
        filled = self.fill(self.form(para(text("○ ○"))), {"find": "○", "replace": "글", "nth": 2})
        self.assertIn("<hp:t>○ 글</hp:t>", filled)

    def test_nth_out_of_range_is_refused(self):
        self.refused(self.form(para(text("○"))), {"fills": [{"find": "○", "replace": "글", "nth": 2}]}, "1곳")

    def test_every_missing_place_is_reported_and_nothing_is_written(self):
        source = self.form(para(text("있음")))
        self.refused(source, {"fills": [{"find": "없는 글", "replace": "1"}, {"find": "또 없음", "replace": "2"},
                                        {"find": "있음", "replace": "3"}]}, "없는 글", "또 없음")

    def test_overlapping_targets_are_refused(self):
        source = self.form(para(text("가나다")))
        self.refused(source, {"fills": [{"find": "가나", "replace": "1"}, {"find": "나다", "replace": "2"}]}, "겹침")

    def test_numbers_are_written_as_text(self):
        self.assertIn("<hp:t>20</hp:t>", self.fill(self.form(para(text("○"))), {"find": "○", "replace": 20}))


class CellFillTest(FormCase):
    def one_cell(self, *paragraphs: str) -> Path:
        return self.form(para(run(table([[cell(0, 0, *paragraphs), cell(0, 1, para(text("옆칸")))]]))))

    def fill_first(self, source: Path, value: str = "새 글") -> str:
        return self.fill(source, {"table": 1, "row": 1, "col": 1, "text": value})

    def test_self_closing_run_keeps_its_style(self):
        source = self.one_cell(para('<hp:run charPrIDRef="5"/>'))
        self.assertIn('<hp:run charPrIDRef="5"><hp:t>새 글</hp:t></hp:run>', self.fill_first(source))

    def test_empty_run_without_text(self):
        self.assertIn('<hp:run charPrIDRef="5"><hp:t>새 글</hp:t></hp:run>', self.fill_first(self.one_cell(para(run("", 5)))))

    def test_empty_text_element(self):
        source = self.one_cell(para(run("<hp:t/>", 5)))
        self.assertIn('<hp:run charPrIDRef="5"><hp:t>새 글</hp:t></hp:run>', self.fill_first(source))

    def test_existing_text_is_replaced_in_the_first_run(self):
        source = self.one_cell(para(text("옛", 5), text(" 글", 6)))
        filled = self.fill_first(source)
        self.assertIn('<hp:run charPrIDRef="5"><hp:t>새 글</hp:t></hp:run>', filled)
        self.assertNotIn("옛", filled)

    def test_later_paragraphs_of_the_cell_are_removed(self):
        filled = self.fill_first(self.one_cell(para(text("하나")), para(text("둘"))))
        self.assertNotIn("둘", filled)
        self.assertIn("옆칸", filled)

    def test_click_here_field_gets_the_text_inside(self):
        begin = '<hp:ctrl><hp:fieldBegin id="1" type="CLICK_HERE" name=""/></hp:ctrl>'
        end = '<hp:ctrl><hp:fieldEnd beginIDRef="1"/></hp:ctrl>'
        filled = self.fill_first(self.one_cell(para(run(begin + end, 5))))
        self.assertIn(f"{begin}<hp:t>새 글</hp:t>{end}", filled)

    def test_cell_address_counts_merged_cells(self):
        source = self.form(para(run(table([
            [cell(0, 0, para(text("합침")), row_span=2), cell(0, 1, para(text("위")))],
            [cell(1, 1, para(text("아래")))],
        ]))))
        self.assertIn("<hp:t>새</hp:t>", self.fill(source, {"table": 1, "row": 2, "col": 2, "text": "새"}))
        self.result.unlink()
        self.refused(source, {"fills": [{"table": 1, "row": 2, "col": 1, "text": "새"}]}, "합쳐", "행 1 칸 1")

    def test_missing_addresses_are_reported(self):
        source = self.one_cell(para(run()))
        self.refused(source, {"fills": [{"table": 9, "row": 1, "col": 1, "text": "가"}]}, "표 9")
        self.refused(source, {"fills": [{"table": 1, "row": 5, "col": 1, "text": "가"}]}, "행 5")

    def test_cell_with_an_object_is_refused(self):
        source = self.one_cell(para(text("가"), run('<hp:pic id="1"/>')))
        self.refused(source, {"fills": [{"table": 1, "row": 1, "col": 1, "text": "새"}]}, "그림", "find")

    def test_find_and_cell_on_the_same_place_are_refused(self):
        source = self.one_cell(para(text("가나")))
        self.refused(source, {"fills": [{"table": 1, "row": 1, "col": 1, "text": "새"},
                                        {"find": "가", "replace": "다"}]}, "겹침")

    def test_same_cell_twice_is_refused(self):
        source = self.one_cell(para(run()))
        fill = {"table": 1, "row": 1, "col": 1, "text": "새"}
        self.refused(source, {"fills": [fill, fill]}, "겹침")

    def test_empty_text_clears_the_cell(self):
        self.assertNotIn("옛", self.fill_first(self.one_cell(para(text("옛"))), ""))

    def test_second_section_table(self):
        source = self.form(para(run(table([[cell(0, 0, para(run())), cell(0, 1, para(run()))]]))),
                           extra_sections=(para(run(table([[cell(0, 0, para(run())), cell(0, 1, para(run()))]]))),))
        fill_form(source, {"fills": [{"table": 2, "row": 1, "col": 2, "text": "새"}]}, self.result)
        self.assertIn("<hp:t>새</hp:t>", self.read(self.result, "Contents/section1.xml"))
        self.assertNotIn("<hp:t>새</hp:t>", self.read(self.result))


class SafetyTest(FormCase):
    def test_refuses_to_overwrite_the_form(self):
        source = self.form(para(text("○")))
        before = source.read_bytes()
        with self.assertRaises(FillError) as caught:
            fill_form(source, {"fills": [{"find": "○", "replace": "글"}]}, source)
        self.assertIn("원본", str(caught.exception))
        self.assertEqual(source.read_bytes(), before)

    def test_refuses_an_existing_output(self):
        source = self.form(para(text("○")))
        self.result.write_bytes(b"teacher work")
        with self.assertRaises(FillError):
            fill_form(source, {"fills": [{"find": "○", "replace": "글"}]}, self.result)
        self.assertEqual(self.result.read_bytes(), b"teacher work")

    def test_hwp_form_gets_the_save_as_hwpx_guide(self):
        source = self.folder / "양식.hwp"
        source.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64)
        with self.assertRaises(FillError) as caught:
            inspect_form(source)
        self.assertIn("hwpx로 저장", str(caught.exception))

    def test_not_a_hwpx_file(self):
        source = self.folder / "양식.hwpx"
        source.write_bytes(b"plain text")
        with self.assertRaises(FillError):
            inspect_form(source)

    def test_zip_that_is_not_a_hwpx(self):
        source = self.folder / "양식.hwpx"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("mimetype", "text/plain")
        with self.assertRaises(FillError):
            inspect_form(source)

    def test_oversized_entry_is_refused_before_reading(self):
        source = self.form(para(text("○")))
        with mock.patch.object(fill_hwpx, "MAX_ENTRY_BYTES", 10):
            with self.assertRaises(FillError) as caught:
                inspect_form(source)
        self.assertIn("너무", str(caught.exception))

    def test_broken_section_is_reported(self):
        source = self.form(para(text("○")))
        broken = self.folder / "깨짐.hwpx"
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(broken, "w") as new:
            for info in old.infolist():
                data = old.read(info.filename)
                new.writestr(info, data.replace(b"</hs:sec>", b"") if info.filename == SECTION else data)
        with self.assertRaises(FillError):
            inspect_form(broken)

    def test_bad_instructions_are_refused(self):
        source = self.form(para(text("○")))
        for spec, phrase in (
            ({}, "fills"), ({"fills": []}, "fills"), ({"fills": ["글"]}, "1번"),
            ({"fills": [{"find": "", "replace": "글"}]}, "find"),
            ({"fills": [{"find": "○"}]}, "replace"),
            ({"fills": [{"find": "○", "replace": "글", "색": "빨강"}]}, "색"),
            ({"fills": [{"find": "○", "replace": "글", "all": True, "nth": 1}]}, "all"),
            ({"fills": [{"find": "○", "replace": None}]}, "replace"),
            ({"fills": [{"table": 0, "row": 1, "col": 1, "text": "글"}]}, "table"),
            ({"fills": [{"table": 1, "row": "1", "col": 1, "text": "글"}]}, "row"),
            ({"fills": [{"table": 1, "row": 1, "text": "글"}]}, "col"),
        ):
            self.refused(source, spec, phrase)

    def test_a_new_check_problem_stops_the_output(self):
        source = self.form(para(text("○")))
        calls = iter([[], ["새 문제"]])
        with mock.patch.object(fill_hwpx, "validate_package", lambda path: next(calls)):
            self.refused(source, {"fills": [{"find": "○", "replace": "글"}]}, "새 문제")
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_problems_already_in_the_form_do_not_stop_the_output(self):
        source = self.form(para(text("○")))
        with mock.patch.object(fill_hwpx, "validate_package", lambda path: ["원래 있던 문제"]):
            fill_form(source, {"fills": [{"find": "○", "replace": "글"}]}, self.result)
        self.assertTrue(self.result.exists())

    def test_preview_text_follows_the_filled_text(self):
        source = self.form(para(text("학생 이름 ○○")))
        self.fill(source, {"find": "학생 이름 ○○", "replace": "새 글"})
        preview = self.read(self.result, "Preview/PrvText.txt")
        self.assertIn("새 글", preview)
        self.assertNotIn("○○", preview)

    def test_old_preview_image_is_replaced_with_a_blank_one(self):
        source = self.form(para(text("○○")))
        with zipfile.ZipFile(source) as archive:
            self.assertNotEqual(archive.read("Preview/PrvImage.png"), BLANK_PNG)
        self.fill(source, {"find": "○○", "replace": "글"})
        with zipfile.ZipFile(self.result) as archive:
            self.assertEqual(archive.read("Preview/PrvImage.png"), BLANK_PNG)

    def test_blank_preview_image_is_shared_with_fill_exam(self):
        import fill_exam
        self.assertIs(fill_exam.BLANK_PNG, BLANK_PNG)


class MemoNoticeTest(FormCase):
    MEMO = ('<hp:ctrl><hp:fieldBegin id="%d" type="MEMO" name=""><hp:subList>'
            '%s</hp:subList></hp:fieldBegin></hp:ctrl>')

    def memo_form(self, count: int) -> Path:
        memos = "".join(self.MEMO % (number, para(text(f"메모 {number}"))) for number in range(1, count + 1))
        return self.form(para(run(memos), text("본문 ○○")))

    def test_notice_counts_the_memos_after_filling(self):
        source = self.memo_form(2)
        spec = self.folder / "지시.json"
        spec.write_text(json.dumps({"fills": [{"find": "○○", "replace": "글"}]}, ensure_ascii=False), encoding="utf-8")
        with mock.patch("sys.stdout.write") as write:
            self.assertEqual(main([str(source), str(spec), str(self.result)]), 0)
        self.assertIn("메모 2개가 남아 있습니다. 한글에서 확인하세요", write.call_args_list[0].args[0])

    def test_inspect_shows_the_notice(self):
        self.assertIn("메모 1개가 남아 있습니다. 한글에서 확인하세요", inspect_form(self.memo_form(1)))

    def test_no_notice_without_memos(self):
        source = self.form(para(text("본문 ○○")))
        self.assertNotIn("메모", inspect_form(source).replace("[메모]", ""))
        spec = self.folder / "지시.json"
        spec.write_text(json.dumps({"fills": [{"find": "○○", "replace": "글"}]}, ensure_ascii=False), encoding="utf-8")
        with mock.patch("sys.stdout.write") as write:
            main([str(source), str(spec), str(self.result)])
        self.assertNotIn("남아 있습니다", write.call_args_list[0].args[0])


class PackageHardeningTest(FormCase):
    def copy_with(self, source: Path, name: str, *extra: tuple[str, bytes]) -> Path:
        target = self.folder / name
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w") as new:
            for info in old.infolist():
                new.writestr(info, old.read(info.filename))
            for entry, data in extra:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")      # 같은 이름 항목 경고
                    new.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED)
        return target

    def test_entries_with_the_same_name_are_refused(self):
        source = self.form(para(text("○월")))
        hidden = self.read(source).replace("○월", "숨은글").encode("utf-8")
        twin = self.copy_with(source, "겹침.hwpx", (SECTION, hidden))
        with self.assertRaisesRegex(FillError, "이름이 같은"):
            inspect_form(twin)
        self.refused(twin, {"fills": [{"find": "숨은글", "replace": "X"}]}, "이름이 같은")

    def test_unsafe_entry_paths_are_refused(self):
        source = self.form(para(text("○월")))
        for number, name in enumerate(("../밖.txt", "/abs.txt", "C:/x.txt")):
            with self.subTest(name=name):
                evil = self.copy_with(source, f"악성{number}.hwpx", (name, b"x"))
                with self.assertRaisesRegex(FillError, "안전하지 않은 경로"):
                    inspect_form(evil)

    def test_lying_entry_size_does_not_blow_up_memory(self):
        source = self.form(para(text("○월")))
        bomb = self.copy_with(source, "폭탄.hwpx", ("BinData/x.bin", b"\0" * BOMB_BYTES))
        lie_about_size(bomb, "BinData/x.bin", 10)
        tracemalloc.start()
        try:
            with self.assertRaises(FillError):
                inspect_form(bomb)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, PEAK_LIMIT)

    def test_total_size_limit(self):
        source = self.form(para(text("○월")))
        with mock.patch.object(fill_hwpx, "MAX_TOTAL_BYTES", 100):
            with self.assertRaisesRegex(FillError, "너무 큼"):
                inspect_form(source)

    def test_nan_and_infinity_are_not_written_as_text(self):
        source = self.form(para(text("○월")), para(run(table([[cell(0, 0, para(text("칸"))),
                                                               cell(0, 1, para(run()))]]))))
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                self.refused(source, {"fills": [{"find": "○월", "replace": value}]}, "replace")
                self.refused(source, {"fills": [{"table": 1, "row": 1, "col": 2, "text": value}]}, "text")
        parsed = json.loads('{"fills":[{"find":"○월","replace":NaN}]}')
        self.refused(source, parsed, "replace")

    def test_form_with_a_big_picture_is_still_checked(self):
        source = self.form(para(text("○월")))
        big = self.copy_with(source, "큰그림.hwpx", ("BinData/image1.bmp", b"\0" * (21 * 1024 * 1024)))
        self.assertEqual(validate_package(big), [])
        fill_form(big, {"fills": [{"find": "○월", "replace": "3월"}]}, self.result)
        self.assertEqual(validate_package(self.result), [])
        self.assertIn("3월", self.read(self.result))


class CommandLineTest(FormCase):
    def write_spec(self, spec: dict) -> str:
        path = self.folder / "지시.json"
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_fill_and_inspect_commands(self):
        source = self.form(para(text("○")))
        spec = self.write_spec({"fills": [{"find": "○", "replace": "글"}]})
        with mock.patch("sys.stdout.write") as write:
            self.assertEqual(main([str(source), spec, str(self.result)]), 0)
            self.assertIn("1곳", write.call_args_list[0].args[0])
            self.assertEqual(main(["--inspect", str(self.result)]), 0)
            self.assertIn("문단 3: 글", write.call_args_list[-1].args[0])

    def test_failure_is_a_sentence_and_exit_code_one(self):
        source = self.form(para(text("가")))
        spec = self.write_spec({"fills": [{"find": "○", "replace": "글"}]})
        with mock.patch("sys.stdout.write") as write:
            self.assertEqual(main([str(source), spec, str(self.result)]), 1)
        self.assertIn("찾지 못함", write.call_args.args[0])

    def test_bad_json_and_missing_file(self):
        source = self.form(para(text("가")))
        spec = self.folder / "지시.json"
        spec.write_text("{", encoding="utf-8")
        with mock.patch("sys.stdout.write"):
            self.assertEqual(main([str(source), str(spec), str(self.result)]), 1)
            self.assertEqual(main([str(self.folder / "없음.hwpx"), str(spec), str(self.result)]), 1)

    def test_wrong_usage(self):
        with mock.patch("sys.stdout.write") as write:
            self.assertEqual(main([]), 2)
        self.assertIn("사용법", write.call_args.args[0])


def _strip_changes(section: str) -> str:
    """바뀌어도 되는 것(글, 줄 배치 정보)을 지운 나머지."""
    section = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", section)
    return re.sub(r"<hp:t>.*?</hp:t>|<hp:t/>", "", section)


def _plan_table(subject: str) -> str:
    """평가계획표처럼 합친 칸이 많고 칸 안에 표가 든 가짜 표. 글은 모두 지어낸 것이다."""
    inner = table([[cell(0, 0, para(text("영역"))), cell(0, 1, para(text("비율")))],
                   [cell(1, 0, para(text(f"{subject} 쓰기"))), cell(1, 1, para(run()))]])
    rows = [
        [cell(0, 0, para(text("평가 종류")), row_span=2), cell(0, 1, para(text("지필 평가")), col_span=2),
         cell(0, 3, para(text("수행 평가")))],
        [cell(1, 1, para(text("1회"))), cell(1, 2, para(text("2회"))), cell(1, 3, para(run()))],
        [cell(2, 0, para(text("반영 비율"))), cell(2, 1, para(run(inner)), col_span=2), cell(2, 3, para(text("40%")))],
        [cell(3, 0, para(text("평가 시기"))), cell(3, 1, para(run()), col_span=3)],
    ]
    return para(run(table(rows, cols=4)))


def _field_paragraph() -> str:
    """글이 든 필드(누름틀이나 하이퍼링크)와 각주가 있는 문단."""
    field = ('<hp:ctrl><hp:fieldBegin id="9" type="HYPERLINK" name=""><hp:parameters/></hp:fieldBegin></hp:ctrl>')
    note = f'<hp:ctrl><hp:footNote><hp:subList>{para(text("각주 글"))}</hp:subList></hp:footNote></hp:ctrl>'
    return para(run(field), text("연결 글"), run("<hp:ctrl><hp:fieldEnd/></hp:ctrl>"), run(note))


def _box_paragraph() -> str:
    box = f'<hp:rect id="3"><hp:drawText><hp:subList>{para(text("안내 상자 글"))}</hp:subList></hp:drawText></hp:rect>'
    return para(run(box), text("상자 옆 글"))


class FakeSchoolFormTest(FormCase):
    """학교 평가계획 양식을 흉내 낸 가짜 양식(합친 칸, 칸 속 표, 필드, 각주, 글상자, 둘째 구역)으로
    양식의 모양이 글만 빼고 그대로인지 본다. 실제 학교 양식과 학교 이름은 저장소에 두지 않는다."""

    def forms(self) -> list[Path]:
        plain = self.form(para(text("2026학년도 ○○과 평가계획")), _plan_table("국어"), para(text("끝")))
        rich = self.form(para(text("교과 진도 평가계획")), _plan_table("수학"), _field_paragraph(), _box_paragraph(),
                         extra_sections=(para(text("둘째 구역 안내")) + _plan_table("사회"),))
        return [plain, rich]

    def test_fake_forms_keep_everything_but_the_text(self):
        for number, form in enumerate(self.forms()):
            before_bytes = form.read_bytes()
            listing = inspect_form(form)
            place = re.search(r"표 (\d+) 행 (\d+) 칸 (\d+)(?: \[[^\]]*\])?: [^⏎\n(]+\n", listing)
            self.assertIsNotNone(place, listing)
            spec = {"fills": [{"table": int(place[1]), "row": int(place[2]), "col": int(place[3]), "text": "시험 글"}]}
            target = self.folder / f"가짜{number}.hwpx"
            fill_form(form, spec, target)
            self.assertEqual(form.read_bytes(), before_bytes)
            self.assertEqual(validate_package(target), validate_package(form))
            self.assertIn("시험 글", inspect_form(target))
            with zipfile.ZipFile(form) as old, zipfile.ZipFile(target) as new:
                self.assertEqual(old.namelist(), new.namelist())
                for name in old.namelist():
                    if name.startswith("Contents/section"):
                        self.assertEqual(_strip_changes(old.read(name).decode()), _strip_changes(new.read(name).decode()))
                    elif name not in ("Preview/PrvText.txt", "Preview/PrvImage.png"):
                        self.assertEqual(old.read(name), new.read(name), name)

    def test_fake_forms_list_merged_and_nested_cells(self):
        listing = inspect_form(self.forms()[1])
        self.assertIn("[합침 2행 × 1칸]", listing)
        self.assertIn("[합침 1행 × 2칸]", listing)
        self.assertIn("영역", listing)                  # 칸 속 표도 번호가 매겨진다
        self.assertIn("[글상자]", listing)


if __name__ == "__main__":
    unittest.main()
