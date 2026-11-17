import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

try:
    from PIL import Image as PILImage
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Emu, Pt
except ImportError:  # pragma: no cover
    Presentation = None

import fill_template
from fill_template import build, inspect_template, main

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
SLIDE_W, SLIDE_H = 18288000, 10287000


def make_image(path: Path, size=(400, 200), color=(200, 30, 30)) -> Path:
    PILImage.new("RGB", size, color).save(path)
    return path


def make_template(folder: Path) -> Path:
    """Canva 양식처럼 디자인이 슬라이드 위에 직접 그려진 3장짜리 양식."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(SLIDE_W), Emu(SLIDE_H)
    blank = prs.slide_layouts[6]

    cover = prs.slides.add_slide(blank)
    background = cover.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Emu(SLIDE_W), Emu(SLIDE_H))
    background.name = "배경"
    title = cover.shapes.add_textbox(Emu(2000000), Emu(3000000), Emu(14000000), Emu(1500000))
    title.name = "제목"
    run = title.text_frame.paragraphs[0].add_run()
    run.text = "양식 제목"
    run.font.size, run.font.bold = Pt(60), True
    run.font.color.rgb = RGBColor(0x29, 0x29, 0x29)

    body = prs.slides.add_slide(blank)
    card = body.shapes.add_textbox(Emu(2000000), Emu(3000000), Emu(6000000), Emu(1200000))
    card.name = "본문"
    for index, text in enumerate(["첫 문단", "둘째 문단"]):
        paragraph = card.text_frame.paragraphs[0] if index == 0 else card.text_frame.add_paragraph()
        r = paragraph.add_run()
        r.text = text
        r.font.size = Pt(18)
    photo = body.shapes.add_picture(str(make_image(folder / "원래사진.png", (300, 300), (0, 0, 255))),
                                    Emu(9000000), Emu(3000000), Emu(4000000), Emu(2000000))
    photo.name = "사진"

    grouped = prs.slides.add_slide(blank)
    group = grouped.shapes.add_group_shape()
    group.name = "묶음"
    inner = group.shapes.add_textbox(Emu(1000000), Emu(1000000), Emu(5000000), Emu(800000))
    inner.name = "묶음 글"
    inner_run = inner.text_frame.paragraphs[0].add_run()
    inner_run.text = "그룹 안 글"
    inner_run.font.size = Pt(20)

    path = folder / "양식.pptx"
    prs.save(str(path))
    return path


def shape_named(slide, name):
    for shape in slide.shapes:
        if shape.name == name:
            return shape
        if shape.shape_type == 6:
            for inner in shape.shapes:
                if inner.name == name:
                    return inner
    raise KeyError(name)


def runs_of(shape):
    return [run for paragraph in shape.text_frame.paragraphs for run in paragraph.runs]


@unittest.skipIf(Presentation is None, "python-pptx 없음")
class FillTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.template = make_template(self.dir)

    def fill(self, slides):
        out = self.dir / "결과.pptx"
        warnings = build({"template": str(self.template), "slides": slides}, out)
        return Presentation(str(out)), warnings


class CloneTest(FillTestCase):
    def test_output_has_only_listed_slides_in_order(self):
        prs, _ = self.fill([{"from": 2}, {"from": 1}, {"from": 2}])
        self.assertEqual(len(prs.slides), 3)
        self.assertEqual(shape_named(prs.slides[0], "본문").text_frame.text.splitlines()[0], "첫 문단")
        self.assertEqual(shape_named(prs.slides[1], "제목").text_frame.text, "양식 제목")

    def test_design_shapes_are_kept(self):
        prs, _ = self.fill([{"from": 1, "text": {"제목": "새 제목"}}])
        background = shape_named(prs.slides[0], "배경")
        self.assertEqual((background.width, background.height), (SLIDE_W, SLIDE_H))

    def test_slide_size_is_kept(self):
        prs, _ = self.fill([{"from": 1}])
        self.assertEqual((prs.slide_width, prs.slide_height), (SLIDE_W, SLIDE_H))

    def test_reused_picture_slide_keeps_its_image(self):
        prs, _ = self.fill([{"from": 2}, {"from": 2}])
        for slide in prs.slides:
            blip = shape_named(slide, "사진")._element.find(f".//{A}blip")
            self.assertIn(blip.get(R_EMBED), slide.part.rels)

    def test_notes_are_written(self):
        prs, _ = self.fill([{"from": 1, "notes": "발문: 왜 그럴까요?"}])
        self.assertEqual(prs.slides[0].notes_slide.notes_text_frame.text, "발문: 왜 그럴까요?")


class TextTest(FillTestCase):
    def test_text_keeps_template_format(self):
        prs, _ = self.fill([{"from": 1, "text": {"제목": "6·25 전쟁"}}])
        run = runs_of(shape_named(prs.slides[0], "제목"))[0]
        self.assertEqual(run.text, "6·25 전쟁")
        self.assertEqual(run.font.size, Pt(60))
        self.assertTrue(run.font.bold)
        self.assertEqual(run.font.color.rgb, RGBColor(0x29, 0x29, 0x29))

    def test_list_becomes_paragraphs(self):
        prs, _ = self.fill([{"from": 2, "text": {"본문": ["가", "나", "다"]}}])
        paragraphs = shape_named(prs.slides[0], "본문").text_frame.paragraphs
        self.assertEqual([p.text for p in paragraphs], ["가", "나", "다"])

    def test_bold_markup(self):
        prs, _ = self.fill([{"from": 2, "text": {"본문": "**정전 협정** 체결"}}])
        runs = runs_of(shape_named(prs.slides[0], "본문"))
        self.assertEqual([(r.text, bool(r.font.bold)) for r in runs], [("정전 협정", True), (" 체결", False)])

    def test_runs_are_korean_for_word_wrap(self):
        prs, _ = self.fill([{"from": 2, "text": {"본문": "한국어 문장"}}])
        for run in runs_of(shape_named(prs.slides[0], "본문")):
            self.assertEqual(run._r.find(f"{A}rPr").get("lang"), "ko-KR")

    def test_size_override(self):
        prs, _ = self.fill([{"from": 2, "text": {"본문": "크게"}, "size": {"본문": 24}}])
        self.assertEqual(runs_of(shape_named(prs.slides[0], "본문"))[0].font.size, Pt(24))

    def test_text_inside_group(self):
        prs, _ = self.fill([{"from": 3, "text": {"묶음 글": "바뀐 글"}}])
        self.assertEqual(shape_named(prs.slides[0], "묶음 글").text_frame.text, "바뀐 글")

    def test_numbers_are_accepted_as_text(self):
        prs, _ = self.fill([{"from": 1, "text": {"제목": 1950}}])
        self.assertEqual(shape_named(prs.slides[0], "제목").text_frame.text, "1950")


class ShapeEditTest(FillTestCase):
    def test_remove_shape(self):
        prs, _ = self.fill([{"from": 2, "remove": ["사진"]}])
        self.assertNotIn("사진", [s.name for s in prs.slides[0].shapes])

    def test_geometry_moves_shape(self):
        prs, _ = self.fill([{"from": 2, "geometry": {"본문": {"top": 5000000, "height": 2000000}}}])
        shape = shape_named(prs.slides[0], "본문")
        self.assertEqual((shape.left, shape.top, shape.height), (2000000, 5000000, 2000000))

    def test_clone_copies_shape_with_new_name(self):
        prs, _ = self.fill([{"from": 2, "clone": [{"from": "본문", "name": "본문 2", "top": 6000000}],
                             "text": {"본문 2": "복제한 글"}}])
        copy = shape_named(prs.slides[0], "본문 2")
        self.assertEqual((copy.left, copy.top), (2000000, 6000000))
        self.assertEqual(copy.text_frame.text, "복제한 글")
        self.assertEqual(runs_of(copy)[0].font.size, Pt(18))


class ImageTest(FillTestCase):
    def new_image(self):
        blip = shape_named(self.prs.slides[0], "사진")._element.find(f".//{A}blip")
        part = self.prs.slides[0].part.related_part(blip.get(R_EMBED))
        return PILImage.open(io.BytesIO(part.blob))

    def test_image_is_replaced_and_cropped_to_shape_ratio(self):
        make_image(self.dir / "새사진.png", (1000, 1000), (0, 200, 0))
        self.prs, _ = self.fill([{"from": 2, "images": {"사진": str(self.dir / "새사진.png")}}])
        image = self.new_image()
        self.assertAlmostEqual(image.width / image.height, 2.0, delta=0.02)
        self.assertEqual(image.getpixel((image.width // 2, image.height // 2))[:3], (0, 200, 0))

    def test_crop_box_is_applied_before_fitting(self):
        picture = PILImage.new("RGB", (1000, 500), (255, 255, 255))
        picture.paste((0, 0, 0), (0, 250, 1000, 500))  # 아래 절반만 검정
        picture.save(self.dir / "아래.png")
        self.prs, _ = self.fill([{"from": 2, "images": {"사진": {"path": str(self.dir / "아래.png"),
                                                                  "crop": [0, 0.5, 1, 1]}}}])
        image = self.new_image()
        self.assertEqual(image.getpixel((image.width // 2, image.height // 2))[:3], (0, 0, 0))

    def test_image_needs_picture_fill(self):
        make_image(self.dir / "새사진.png")
        with self.assertRaisesRegex(ValueError, "그림"):
            self.fill([{"from": 1, "images": {"제목": str(self.dir / "새사진.png")}}])


class AddShapeTest(FillTestCase):
    def test_card_with_text_color_and_korean_wrap(self):
        prs, _ = self.fill([{"from": 2, "add": [
            {"shape": "rounded", "name": "카드", "left": 1000000, "top": 2000000, "width": 3000000, "height": 1000000,
             "fill": "8C2F2F", "text": ["**1950**", "남침"], "size": 28, "color": "FFFFFF"}]}])
        card = shape_named(prs.slides[0], "카드")
        self.assertEqual((card.left, card.top, card.width), (1000000, 2000000, 3000000))
        self.assertEqual(card.fill.fore_color.rgb, RGBColor(0x8C, 0x2F, 0x2F))
        self.assertEqual([p.text for p in card.text_frame.paragraphs], ["1950", "남침"])
        run = runs_of(card)[0]
        self.assertTrue(run.font.bold)
        self.assertEqual((run.font.size, run.font.color.rgb), (Pt(28), RGBColor(0xFF, 0xFF, 0xFF)))
        self.assertEqual(run._r.find(f"{A}rPr").get("lang"), "ko-KR")

    def test_default_font_is_template_title_font(self):
        prs, _ = self.fill([{"from": 1, "add": [
            {"shape": "circle", "name": "원", "left": 0, "top": 0, "width": 900000, "height": 900000, "text": "1"}]}])
        title_font = runs_of(shape_named(prs.slides[0], "제목"))[0].font.name
        self.assertEqual(runs_of(shape_named(prs.slides[0], "원"))[0].font.name, title_font)

    def test_all_shape_kinds_are_drawn(self):
        entries = [{"shape": kind, "name": kind, "left": 0, "top": 0, "width": 800000, "height": 400000}
                   for kind in ("box", "rounded", "circle", "chevron", "arrow", "line")]
        prs, _ = self.fill([{"from": 2, "add": entries}])
        names = [s.name for s in prs.slides[0].shapes]
        for kind in ("box", "rounded", "circle", "chevron", "arrow", "line"):
            self.assertIn(kind, names)

    def test_image_keeps_its_ratio_inside_the_box(self):
        make_image(self.dir / "지도.png", (300, 600))
        prs, _ = self.fill([{"from": 2, "add": [{"shape": "image", "name": "지도", "path": str(self.dir / "지도.png"),
                                                 "left": 1000000, "top": 1000000, "width": 4000000, "height": 4000000}]}])
        picture = shape_named(prs.slides[0], "지도")
        self.assertEqual(picture.height, 4000000)
        self.assertEqual(picture.width, 2000000)
        self.assertEqual(picture.left, 2000000)  # 가로 가운데 맞춤

    def test_image_needs_path(self):
        with self.assertRaisesRegex(ValueError, "path"):
            self.fill([{"from": 2, "add": [{"shape": "image", "left": 0, "top": 0, "width": 1, "height": 1}]}])

    def test_bad_shape_kind_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            self.fill([{"from": 2, "add": [{"shape": "star", "left": 0, "top": 0, "width": 1, "height": 1}]}])

    def test_bad_color_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RRGGBB"):
            self.fill([{"from": 2, "add": [{"shape": "box", "left": 0, "top": 0, "width": 1, "height": 1,
                                            "fill": "red"}]}])

    def test_geometry_is_required(self):
        with self.assertRaisesRegex(ValueError, "width"):
            self.fill([{"from": 2, "add": [{"shape": "box", "left": 0, "top": 0, "height": 1}]}])


class WarningTest(FillTestCase):
    def test_overflowing_text_is_reported(self):
        long_text = ["아주 긴 문장을 여러 번 써서 상자를 넘치게 만든다. " * 4] * 4
        _, warnings = self.fill([{"from": 2, "text": {"본문": long_text}}])
        self.assertTrue(any("1쪽" in w and "본문" in w for w in warnings), warnings)

    def test_short_text_has_no_warning(self):
        _, warnings = self.fill([{"from": 2, "text": {"본문": "짧은 글"}}])
        self.assertEqual(warnings, [])

    def test_few_letters_wrapping_to_next_line_is_reported(self):
        # 상자 폭(본문 18pt 기준 한글 약 28자)을 한두 글자 넘는 한 줄 글
        _, warnings = self.fill([{"from": 2, "text": {"본문": "가" * 14 + " " + "가" * 15}}])
        self.assertTrue(any("다음 줄" in w and "본문" in w for w in warnings), warnings)

    def test_wrapped_text_in_added_card_is_reported(self):
        _, warnings = self.fill([{"from": 2, "add": [
            {"shape": "rounded", "name": "카드", "left": 0, "top": 0, "width": 2000000, "height": 2000000,
             "size": 20, "text": "가나다라마바사 아"}]}])  # 한 줄 한글 약 8자
        self.assertTrue(any("다음 줄" in w and "카드" in w for w in warnings), warnings)

    def test_evenly_wrapped_paragraph_is_not_reported(self):
        _, warnings = self.fill([{"from": 2, "text": {"본문": ("가" * 14 + " ") * 3}}])
        self.assertFalse(any("다음 줄" in w for w in warnings), warnings)

    def test_picture_outside_slide_is_reported(self):
        _, warnings = self.fill([{"from": 2, "geometry": {"사진": {"top": 9000000}}}])
        self.assertTrue(any("밖" in w and "사진" in w for w in warnings), warnings)

    def test_picture_inside_slide_has_no_outside_warning(self):
        _, warnings = self.fill([{"from": 2}])
        self.assertFalse(any("밖" in w for w in warnings), warnings)

    def test_text_box_outside_slide_is_reported(self):
        _, warnings = self.fill([{"from": 2, "geometry": {"본문": {"left": 15000000}}}])
        self.assertTrue(any("밖" in w and "본문" in w for w in warnings), warnings)

    def test_added_shape_outside_slide_is_moved_inside(self):
        prs, warnings = self.fill([{"from": 2, "add": [
            {"shape": "rounded", "name": "카드", "left": 17000000, "top": -500000, "width": 3000000, "height": 1000000,
             "text": "카드"}]}])
        card = shape_named(prs.slides[0], "카드")
        self.assertEqual((card.left, card.top), (SLIDE_W - 3000000, 0))
        self.assertTrue(any("옮김" in w and "카드" in w for w in warnings), warnings)

    def test_added_line_outside_slide_is_moved_inside(self):
        prs, _ = self.fill([{"from": 2, "add": [
            {"shape": "line", "name": "선", "left": -400000, "top": 1000000, "width": 2000000, "height": 0}]}])
        line = shape_named(prs.slides[0], "선")
        self.assertGreaterEqual(line.left, 0)

    def test_added_shape_bigger_than_slide_is_reported(self):
        _, warnings = self.fill([{"from": 2, "add": [
            {"shape": "box", "name": "큰 상자", "left": 0, "top": 0, "width": SLIDE_W + 1000000, "height": 1000}]}])
        self.assertTrue(any("밖" in w and "큰 상자" in w for w in warnings), warnings)

    def test_full_slide_background_is_not_reported(self):
        _, warnings = self.fill([{"from": 1}])
        self.assertFalse(any("밖" in w for w in warnings), warnings)

    def test_rotated_picture_uses_its_visible_box(self):
        # 가로로 긴 사진을 90° 돌리면 화면에서는 세로로 서므로 오른쪽 끝을 넘지 않는다
        geometry = {"사진": {"left": 15000000, "top": 3000000, "width": 4000000, "height": 300000}}
        prs = Presentation(str(self.template))
        photo = prs.slides[1].shapes[1]
        photo.rotation = 90
        prs.save(str(self.template))
        _, warnings = self.fill([{"from": 2, "geometry": geometry}])
        self.assertFalse(any("밖" in w for w in warnings), warnings)

    def test_added_image_outside_slide_is_reported(self):
        make_image(self.dir / "지도.png", (100, 100))
        _, warnings = self.fill([{"from": 2, "add": [{"shape": "image", "name": "지도", "path": str(self.dir / "지도.png"),
                                                      "left": 17000000, "top": 0, "width": 3000000, "height": 3000000}]}])
        self.assertTrue(any("밖" in w and "지도" in w for w in warnings), warnings)

    def test_big_label_that_fits_without_inset_has_no_warning(self):
        prs = Presentation()
        box = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(0, 0, Emu(2800480), Emu(731516))
        frame = box.text_frame
        frame.margin_left = frame.margin_right = 0  # Canva 양식의 번호 칸처럼 여백 없음
        frame.paragraphs[0].add_run().text = "01. 배경"
        frame.paragraphs[0].runs[0].font.size = Pt(45.66)
        self.assertFalse(fill_template._overflows(box))

    def test_label_wider_than_box_warns(self):
        prs = Presentation()
        box = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(0, 0, Emu(1943928), Emu(1261369))
        box.text_frame.paragraphs[0].add_run().text = "10분 활동 안내"
        box.text_frame.paragraphs[0].runs[0].font.size = Pt(80)
        self.assertTrue(fill_template._overflows(box))


class ValidationTest(FillTestCase):
    def test_unknown_shape_lists_available_names(self):
        with self.assertRaisesRegex(ValueError, "없는 도형.*본문"):
            self.fill([{"from": 2, "text": {"없는 도형": "글"}}])

    def test_slide_number_out_of_range(self):
        with self.assertRaisesRegex(ValueError, "1~3"):
            self.fill([{"from": 4}])

    def test_slides_required(self):
        with self.assertRaisesRegex(ValueError, "slides"):
            build({"template": str(self.template), "slides": []}, self.dir / "결과.pptx")

    def test_template_required(self):
        with self.assertRaisesRegex(ValueError, "template"):
            build({"slides": [{"from": 1}]}, self.dir / "결과.pptx")

    def test_crop_must_be_four_fractions(self):
        make_image(self.dir / "새사진.png")
        with self.assertRaisesRegex(ValueError, "crop"):
            self.fill([{"from": 2, "images": {"사진": {"path": str(self.dir / "새사진.png"), "crop": [0, 0, 2]}}}])


class InspectTest(FillTestCase):
    def test_lists_slides_shapes_and_text(self):
        report = inspect_template(self.template)
        for word in ("1쪽", "2쪽", "3쪽", "제목", "양식 제목", "60pt", "본문", "사진", "그림", "묶음 글"):
            self.assertIn(word, report)

    def test_marks_pictures_that_cross_the_slide_edge(self):
        prs = Presentation(str(self.template))
        prs.slides[1].shapes[1].top = Emu(9000000)  # 사진을 아래로 내려 슬라이드 밖으로
        prs.save(str(self.template))
        self.assertIn("슬라이드 밖으로 나감", inspect_template(self.template))

    def test_marks_text_and_decorations_that_cross_the_slide_edge(self):
        prs = Presentation(str(self.template))
        prs.slides[0].shapes[1].left = Emu(15000000)  # 제목 글상자를 오른쪽 밖으로
        prs.slides[0].shapes[0].top = Emu(-500000)  # 배경 도형(장식)을 위쪽 밖으로
        prs.save(str(self.template))
        report = inspect_template(self.template)
        self.assertRegex(report, r"제목 .*슬라이드 밖으로 나감")
        self.assertIn("밖으로 나간 장식: 배경", report)


@unittest.skipIf(Presentation is None, "python-pptx 없음")
class MainTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        make_template(self.dir)
        make_image(self.dir / "새사진.png")

    def run_main(self, args):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(args)
        return code, buffer.getvalue()

    def write_spec(self, spec) -> Path:
        path = self.dir / "입력.json"
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return path

    def test_relative_paths_resolve_against_json_folder(self):
        spec = {"template": "양식.pptx", "slides": [{"from": 2, "images": {"사진": "새사진.png"}}]}
        code, output = self.run_main([str(self.write_spec(spec)), str(self.dir / "결과.pptx")])
        self.assertEqual(code, 0, output)
        self.assertIn("완료", output)

    def test_inspect_command(self):
        code, output = self.run_main(["--inspect", str(self.dir / "양식.pptx")])
        self.assertEqual(code, 0)
        self.assertIn("양식 제목", output)

    def test_output_must_not_overwrite_template(self):
        spec = {"template": "양식.pptx", "slides": [{"from": 1}]}
        code, output = self.run_main([str(self.write_spec(spec)), str(self.dir / "양식.pptx")])
        self.assertEqual(code, 1)
        self.assertIn("템플릿", output)

    def test_output_must_be_pptx(self):
        spec = {"template": "양식.pptx", "slides": [{"from": 1}]}
        code, output = self.run_main([str(self.write_spec(spec)), str(self.dir / "결과.pdf")])
        self.assertEqual(code, 1)
        self.assertIn(".pptx", output)

    def test_bad_input_gives_korean_error_not_traceback(self):
        spec = {"template": "양식.pptx", "slides": [{"from": "첫째"}]}
        code, output = self.run_main([str(self.write_spec(spec)), str(self.dir / "결과.pptx")])
        self.assertEqual(code, 1)
        self.assertIn("입력 오류", output)
        self.assertNotIn("Traceback", output)

    def test_usage_without_arguments(self):
        code, output = self.run_main([])
        self.assertEqual(code, 2)
        self.assertIn("사용법", output)

    def test_docstring_example_is_valid_json(self):
        start = fill_template.__doc__.index("{")
        end = fill_template.__doc__.index("\n설명")
        spec = json.loads(fill_template.__doc__[start:end])
        self.assertIn("slides", spec)


if __name__ == "__main__":
    unittest.main()
