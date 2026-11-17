import io
import json
import struct
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches
except ImportError:  # pragma: no cover
    Presentation = None

import make_pptx
from make_pptx import THEMES, build_pptx, main, validate

EA_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}ea"

SPEC = {
    "theme": "basic",
    "slides": [
        {"type": "cover", "unit": "Ⅱ. 물질의 구성", "title": "입자의 운동", "meta": "중학교 2학년 과학", "notes": "인사"},
        {"type": "goals", "items": ["확산을 설명할 수 있다.", "증발을 설명할 수 있다."]},
        {"type": "content", "title": "입자는 움직인다", "items": ["확산", {"text": "증발", "sub": ["표면에서 일어남"]}],
         "notes": "향수 냄새를 맡아 본 적 있나요?"},
        {"type": "compare", "title": "확산과 증발", "left": {"heading": "확산", "items": ["퍼짐"]},
         "right": {"heading": "증발", "items": ["기체로 변함"]}},
        {"type": "activity", "title": "실험", "time": "20분", "group": "4명 모둠", "materials": "비커, 잉크",
         "steps": ["준비", "관찰", "비교"]},
        {"type": "quiz", "question": "확산이 아닌 것은?", "choices": ["향수", "잉크", "빵 냄새", "얼음이 녹음"],
         "answer": 3, "reveal": True},
        {"type": "summary", "items": ["입자는 **스스로** 운동한다"]},
        {"type": "figure", "title": "입자 모형", "caption": "찬물과 더운물 비교"},
        {"type": "table", "title": "비교표", "header": ["구분", "확산", "증발"], "rows": [["장소", "어디서나", "표면"]]},
        {"type": "section", "title": "2. 상태 변화"},
    ],
}


def tiny_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\x00\x00\x00\x00\xff")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def slide_text(slide) -> str:
    parts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            parts.append(shape.text_frame.text)
        if shape.has_table:
            parts.extend(cell.text for row in shape.table.rows for cell in row.cells)
    return "\n".join(parts)


@unittest.skipIf(Presentation is None, "python-pptx 없음")
class PptxTestCase(unittest.TestCase):
    def build(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        path = self.dir / "out.pptx"
        warnings = build_pptx(spec, path)
        return Presentation(str(path)), warnings


class StructureTest(PptxTestCase):
    def setUp(self):
        self.prs, _ = self.build(SPEC)

    def test_slide_size_is_16_by_9(self):
        self.assertEqual((self.prs.slide_width, self.prs.slide_height), (Inches(13.333), Inches(7.5)))

    def test_one_slide_per_entry_plus_quiz_answer(self):
        self.assertEqual(len(self.prs.slides), len(SPEC["slides"]) + 1)

    def test_quiz_answer_slide_reveals_answer(self):
        answer = slide_text(self.prs.slides[6])
        self.assertIn("정답", answer)
        self.assertIn("얼음이 녹음", answer)

    def test_notes_are_written(self):
        self.assertEqual(self.prs.slides[2].notes_slide.notes_text_frame.text, "향수 냄새를 맡아 본 적 있나요?")

    def test_sub_items_rendered(self):
        self.assertIn("표면에서 일어남", slide_text(self.prs.slides[2]))

    def test_activity_cards(self):
        text = slide_text(self.prs.slides[4])
        for word in ("20분", "4명 모둠", "비커, 잉크", "관찰"):
            self.assertIn(word, text)

    def test_table_has_header_and_rows(self):
        tables = [s for s in self.prs.slides[9].shapes if s.has_table]
        self.assertEqual(len(tables), 1)
        self.assertEqual((len(tables[0].table.rows), len(tables[0].table.columns)), (2, 3))

    def test_figure_without_image_shows_placeholder(self):
        self.assertIn("[그림: 찬물과 더운물 비교]", slide_text(self.prs.slides[8]))

    def test_bold_markup_removed_from_text(self):
        text = slide_text(self.prs.slides[7])
        self.assertIn("입자는 스스로 운동한다", text)
        self.assertNotIn("**", text)

    def test_every_run_sets_korean_font(self):
        for slide in self.prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        ea = run._r.find(f"{{*}}rPr/{EA_TAG}")
                        self.assertIsNotNone(ea, run.text)
                        self.assertEqual(ea.get("typeface"), "맑은 고딕")
                        # 한국어로 지정해야 PowerPoint가 단어 중간에서 줄을 바꾸지 않는다
                        self.assertEqual(run._r.find("{*}rPr").get("lang"), "ko-KR", run.text)


class ThemeTest(PptxTestCase):
    def test_background_uses_theme_color(self):
        prs, _ = self.build({"theme": "board", "slides": [{"type": "section", "title": "칠판"}]})
        fill = prs.slides[0].background.fill
        self.assertEqual(fill.fore_color.rgb, RGBColor.from_string(THEMES["board"].bg))

    def test_every_shape_stays_inside_the_slide(self):
        for name in THEMES:
            prs, _ = self.build({**SPEC, "theme": name})
            width, height = prs.slide_width, prs.slide_height
            for number, slide in enumerate(prs.slides, 1):
                for shape in slide.shapes:
                    inside = (shape.left >= 0 and shape.top >= 0
                              and shape.left + shape.width <= width and shape.top + shape.height <= height)
                    self.assertTrue(inside, f"{name} 테마 {number}쪽 {shape.name}")

    def test_all_themes_build(self):
        for name in THEMES:
            prs, _ = self.build({**SPEC, "theme": name})
            self.assertEqual(len(prs.slides), len(SPEC["slides"]) + 1, name)


class SplitTest(PptxTestCase):
    def test_long_list_continues_on_next_slide(self):
        items = [f"{n}번째 설명 문장은 학생들이 읽기 쉽도록 충분히 길게 씁니다" for n in range(1, 16)]
        prs, _ = self.build({"theme": "elem", "slides": [{"type": "content", "title": "긴 설명", "items": items}]})
        self.assertGreater(len(prs.slides), 1)
        self.assertIn("(계속)", slide_text(prs.slides[1]))
        joined = "\n".join(slide_text(s) for s in prs.slides)
        self.assertIn("15번째", joined)

    def test_long_table_repeats_header(self):
        rows = [[str(n), f"내용 {n}"] for n in range(1, 30)]
        prs, _ = self.build({"theme": "basic", "slides": [{"type": "table", "title": "표", "header": ["번호", "내용"],
                                                           "rows": rows}]})
        self.assertGreater(len(prs.slides), 1)
        second = [s for s in prs.slides[1].shapes if s.has_table][0].table
        self.assertEqual(second.cell(0, 0).text, "번호")


class LayoutFitTest(PptxTestCase):
    def card_height(self, materials: str) -> int:
        prs, _ = self.build({"theme": "elem", "slides": [{"type": "activity", "title": "활동", "time": "10분",
                                                          "group": "짝", "materials": materials, "steps": []}]})
        return max(s.height for s in prs.slides[0].shapes if s.shape_type == 1)  # 자동 도형

    def test_activity_cards_grow_when_value_wraps(self):
        self.assertGreater(self.card_height("비커, 잉크, 온도계, 스포이트, 보안경, 실험 기록지"), self.card_height("비커"))

    def test_compare_panels_fit_short_content(self):
        prs, _ = self.build({"theme": "basic", "slides": [SPEC["slides"][3]]})
        panel = max((s for s in prs.slides[0].shapes if s.shape_type == 1), key=lambda s: s.height)
        self.assertLess(panel.height, prs.slide_height * 0.6)


class ReviewEdgeCaseTest(PptxTestCase):
    """코드 리뷰에서 나온 경계 사례."""

    def test_long_quiz_question_never_makes_negative_shapes(self):
        prs, warnings = self.build({"theme": "basic", "slides": [
            {"type": "quiz", "question": "가" * 400, "choices": ["a", "b", "c", "d"], "answer": 1}]})
        line_shape = 9  # 제목 밑줄 같은 직선은 원래 높이가 0
        heights = [s.height for s in prs.slides[0].shapes if s.shape_type != line_shape]
        self.assertTrue(all(h > 0 for h in heights))
        self.assertTrue(warnings)

    def test_missing_required_field_names_slide_number(self):
        with self.assertRaises(ValueError) as caught:
            self.build({"theme": "basic", "slides": [{"type": "section", "title": "a"}, {"type": "content", "items": []}]})
        self.assertIn("2번", str(caught.exception))
        self.assertIn("title", str(caught.exception))

    def test_reveal_requires_integer_answer(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "basic", "slides": [
                {"type": "quiz", "question": "q", "choices": ["a", "b"], "answer": "1", "reveal": True}]})

    def test_empty_table_header_rejected(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "basic", "slides": [{"type": "table", "title": "t", "header": [], "rows": []}]})

    def test_empty_slide_list_rejected(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "basic", "slides": []})

    def test_numbers_and_none_are_accepted_as_text(self):
        prs, _ = self.build({"theme": "basic", "slides": [
            {"type": "content", "title": 2026, "items": [3, {"text": "가", "sub": None}]}]})
        self.assertIn("2026", slide_text(prs.slides[0]))

    def test_missing_template_file_is_reported_clearly(self):
        with self.assertRaises(ValueError) as caught:
            self.build({"theme": "basic", "template": "없는템플릿.pptx", "slides": [{"type": "section", "title": "a"}]})
        self.assertIn("템플릿", str(caught.exception))

    def test_short_label_column_is_wide_enough(self):
        prs, _ = self.build({"theme": "basic", "slides": [{"type": "table", "title": "t", "header": ["구분", "내용"],
                                                           "rows": [["일시", "가" * 60]]}]})
        table = [s for s in prs.slides[0].shapes if s.has_table][0].table
        self.assertGreaterEqual(table.columns[0].width, Inches(0.9))


class InputTest(PptxTestCase):
    def test_figure_with_image_inserts_picture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        image = Path(tmp.name) / "fig.png"
        image.write_bytes(tiny_png())
        prs, _ = self.build({"theme": "sci", "slides": [{"type": "figure", "title": "그림", "image": str(image),
                                                         "caption": "교과서 32쪽"}]})
        pictures = [s for s in prs.slides[0].shapes if s.shape_type == 13]
        self.assertEqual(len(pictures), 1)

    def test_rejects_unknown_theme(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "neon", "slides": []})

    def test_rejects_unknown_slide_type(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "basic", "slides": [{"type": "video"}]})

    def test_rejects_answer_out_of_range(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "basic", "slides": [{"type": "quiz", "question": "q", "choices": ["a", "b"],
                                                      "answer": 5}]})

    def test_teacher_template_keeps_its_size_and_background(self):
        template = Path(tempfile.mkdtemp()) / "template.pptx"
        Presentation().save(str(template))  # 기본 4:3 템플릿
        prs, _ = self.build({"theme": "basic", "template": str(template),
                             "slides": [{"type": "content", "title": "템플릿 제목", "items": ["가"]}]})
        self.assertEqual(prs.slide_width, Inches(10))
        slide = prs.slides[0]
        self.assertEqual(slide.shapes.title.text, "템플릿 제목")
        self.assertFalse(slide.follow_master_background is False)


class ReviewFixTest(PptxTestCase):
    """두 번째 코드 리뷰에서 확인된 문제."""

    def test_goals_and_summary_accept_text_dicts(self):
        prs, _ = self.build({"theme": "basic", "slides": [
            {"type": "goals", "items": [{"text": "목표 가"}, "목표 나"]},
            {"type": "summary", "items": [{"text": "요약 가"}]}]})
        self.assertIn("목표 가", slide_text(prs.slides[0]))
        self.assertIn("요약 가", slide_text(prs.slides[1]))

    def test_goals_dict_without_text_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            self.build({"theme": "basic", "slides": [{"type": "goals", "items": [{"txt": "a"}]}]})
        self.assertIn("text", str(caught.exception))

    def test_table_rows_must_be_lists(self):
        with self.assertRaises(ValueError) as caught:
            self.build({"theme": "basic", "slides": [{"type": "table", "title": "t", "header": ["가", "나"],
                                                      "rows": ["xy"]}]})
        self.assertIn("rows", str(caught.exception))

    def test_compare_items_must_be_lists(self):
        with self.assertRaises(ValueError) as caught:
            self.build({"theme": "basic", "slides": [{"type": "compare", "title": "t",
                                                      "left": {"heading": "a", "items": "abc"},
                                                      "right": {"heading": "b", "items": ["x"]}}]})
        self.assertIn("items", str(caught.exception))

    def test_content_sub_must_be_list(self):
        with self.assertRaises(ValueError):
            self.build({"theme": "basic", "slides": [{"type": "content", "title": "t",
                                                      "items": [{"text": "a", "sub": "xyz"}]}]})

    def test_template_must_be_text(self):
        with self.assertRaises(ValueError):
            validate({"theme": "basic", "template": 5, "slides": [{"type": "section", "title": "a"}]})

    def test_docstring_example_is_valid_json(self):
        doc = make_pptx.__doc__
        start = doc.index("\n{\n") + 1
        end = doc.index("\n}\n", start) + 2
        example = json.loads(doc[start:end])
        validate(example, check_files=False)
        self.assertEqual({slide["type"] for slide in example["slides"]}, set(make_pptx.SLIDE_TYPES))


class MainSafetyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def run_main(self, spec, out_name="out.pptx", in_name="in.json"):
        source = self.dir / in_name
        source.write_text(spec if isinstance(spec, str) else json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main([str(source), str(self.dir / out_name)])
        return code, buffer.getvalue()

    def test_valid_input_succeeds(self):
        code, _ = self.run_main(SPEC)
        self.assertEqual(code, 0)
        self.assertTrue((self.dir / "out.pptx").exists())

    def test_json_with_bom_is_read(self):
        # Windows PowerShell이 쓴 JSON은 BOM이 붙어 "Unexpected UTF-8 BOM"으로 실패했다 (실사용 시험)
        code, output = self.run_main("﻿" + json.dumps(SPEC, ensure_ascii=False))
        self.assertEqual(code, 0, output)

    def test_bad_shapes_give_korean_errors(self):
        bad_specs = [[], {"slides": [{"type": "goals", "items": [{"x": 1}]}]},
                     {"slides": [{"type": "table", "title": "t", "header": ["a", "b"], "rows": ["xy"]}]}]
        for spec in bad_specs:
            code, output = self.run_main(spec)
            self.assertEqual(code, 1, spec)
            self.assertTrue(output.startswith("입력 오류:"), output)

    def test_unexpected_exception_falls_back(self):
        from unittest import mock
        with mock.patch("make_pptx.build_pptx", side_effect=RuntimeError("boom")):
            code, output = self.run_main(SPEC)
        self.assertEqual(code, 1)
        self.assertIn("입력 오류: 예상하지 못한 입력입니다 (RuntimeError)", output)

    def test_output_must_be_pptx(self):
        code, output = self.run_main(SPEC, out_name="out.txt")
        self.assertEqual(code, 1)
        self.assertIn(".pptx", output)
        self.assertFalse((self.dir / "out.txt").exists())

    def test_output_must_not_overwrite_input(self):
        code, output = self.run_main(SPEC, out_name="same.pptx", in_name="same.pptx")
        self.assertEqual(code, 1)
        self.assertTrue(output.startswith("입력 오류:"))
        self.assertIn("{", (self.dir / "same.pptx").read_text(encoding="utf-8"))

    @unittest.skipIf(Presentation is None, "python-pptx 없음")
    def test_output_must_not_overwrite_template(self):
        template = self.dir / "tpl.pptx"
        Presentation().save(str(template))
        before = template.read_bytes()
        code, output = self.run_main({**SPEC, "template": str(template)}, out_name="tpl.pptx")
        self.assertEqual(code, 1)
        self.assertIn("템플릿", output)
        self.assertEqual(template.read_bytes(), before)

    @unittest.skipIf(Presentation is None, "python-pptx 없음")
    def test_relative_template_is_resolved_against_json_folder(self):
        Presentation().save(str(self.dir / "tpl.pptx"))
        code, output = self.run_main({"template": "tpl.pptx", "slides": [{"type": "section", "title": "a"}]})
        self.assertEqual((code, output.startswith("완료")), (0, True), output)
        self.assertEqual(Presentation(str(self.dir / "out.pptx")).slide_width, Inches(10))


if __name__ == "__main__":
    unittest.main()
