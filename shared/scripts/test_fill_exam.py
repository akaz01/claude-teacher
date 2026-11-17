"""fill_exam.py 시험: 시험지 양식의 표 틀을 복제해 채우고, 옛 문항과 정답이 새지 않는지 본다.

실제 시험지는 쓰지 않는다. 여기의 양식은 구조만 같은 가짜이고 글은 모두 지어낸 것이다.
"""

import io
import json
import re
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from fill_exam import fill_exam, inspect_exam, main
from fill_hwpx import FillError
from make_hwpx import build_hwpx, validate_package
from test_fill_hwpx import LINESEG, OPEN_P, SECTION, cell, para, run, table, text

PLAIN, BOLD = 7, 8                      # make_hwpx 골격에서 같은 글꼴의 보통, 굵은 글자 모양
PEN = '<hp:markpenBegin color="#FFFF00"/>'
COLUMNS = ('<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="2" sameSz="1" sameGap="850">'
           '</hp:colPr></hp:ctrl>')
PICTURE = ('<hp:pic id="77" zOrder="50"><hc:img binaryItemIDRef="image1" bright="0" contrast="0" effect="REAL_PIC"/>'
           '</hp:pic>')
CHOICE_NAMES = "①②③④⑤"


def word(value: str, char: int = PLAIN) -> str:
    return text(escape(value), char)


def marked(value: str) -> str:
    return run(f"<hp:t>{PEN}{value}<hp:markpenEnd/></hp:t>", PLAIN)


def stem(number: object, value: str, *, column_break: bool = False) -> str:
    body = para(word(f"{number}.", BOLD), word(f" {value}"))
    return body.replace('columnBreak="0"', 'columnBreak="1"', 1) if column_break else body


def blank() -> str:
    return para(run())


def holder(xml: str, table_id: int) -> str:
    """표 하나를 담은 본문 문단. id가 겹치지 않게 한다."""
    return para(run(xml.replace('<hp:tbl id="7"', f'<hp:tbl id="{table_id}"')))


def short_table(table_id: int, answer: int = 0, mark: bool = True) -> str:
    cells = [cell(0, index, para(marked(f"{name} 옛 짧은 선택지") if mark and index == answer
                                 else word(f"{name} 옛 짧은 선택지")))
             for index, name in enumerate(CHOICE_NAMES)]
    return holder(table([cells], cols=5), table_id)


def combo_table(table_id: int, answer: int = 2) -> str:
    def body(index: int) -> str:
        words = f"{CHOICE_NAMES[index]} ㄱ, ㄴ 옛 조합"
        return para(marked(words) if index == answer else word(words))
    rows = [[cell(0, index, body(index)) for index in range(3)],
            [cell(1, index, body(index + 3)) for index in range(2)] + [cell(1, 2, para(run()))]]
    return holder(table(rows, cols=3), table_id)


def bogi_table(table_id: int) -> str:
    rows = [[cell(0, 0, para(word("<보 기>")), col_span=3)],
            [cell(1, 0, para(word("ㄱ. 옛 보기 첫째 문장")), para(word("ㄴ. 옛 보기 둘째 문장")),
                  para(word("ㄷ. 옛 보기 셋째 문장")), col_span=3)]]
    return holder(table(rows, cols=3), table_id)


def box_table(table_id: int) -> str:
    return holder(table([[cell(0, 0, para(word("옛 자료 상자 글입니다")))]], cols=1), table_id)


def grid_table(table_id: int, answer: int = 4) -> str:
    rows = [[cell(0, 0, para(run()))] + [cell(0, index, para(word(f"옛머리{index}"))) for index in (1, 2, 3)]]
    for row, name in enumerate(CHOICE_NAMES, start=1):
        pieces = (marked if row == answer else word)
        rows.append([cell(row, 0, para(pieces(name)))]
                    + [cell(row, index, para(pieces(f"옛값 {row}{index}"))) for index in (1, 2, 3)])
    return holder(table(rows, cols=4), table_id)


def choice_paragraphs(answer: int = 3) -> list[str]:
    return [para(marked(f"{name} 옛 긴 선택지 문장입니다") if index == answer else word(f"{name} 옛 긴 선택지 문장입니다"))
            for index, name in enumerate(CHOICE_NAMES)]


def head() -> list[str]:
    title = table([[cell(0, 0, para(word("2026학년도 ○학기 정기시험"))), cell(0, 1, para(word("과목: 가짜")))],
                   [cell(1, 0, para(word("문항수 26문항(100점) - "), marked("총 7면"))), cell(1, 1, para(run()))]])
    return [holder(title, 1001), para(word("유의: 가짜 유의사항을 지키시오."))]


def passage() -> list[str]:
    return [para(word("[1~2]", BOLD), word(" 옛 지문 안내 문장입니다.")),
            para(word(" (가)", BOLD)), para(word("옛 지문 본문 첫째 문단입니다.")), blank(),
            para(word(" (나)", BOLD)), para(word("옛 지문 본문 둘째 문단입니다.")), blank()]


def tail() -> list[str]:
    return [blank(), blank(), blank(), holder(table([[cell(0, 0, para(word("※ 꼬리 확인사항 글")))]], cols=1), 1090)]


def full_body() -> list[str]:
    return [*passage(),
            stem(1, "옛 문제 하나의 문장 [2점]"), short_table(1010), blank(),
            stem(2, "옛 문제 둘의 문장 <보기> [3점]"), bogi_table(1020), combo_table(1021), blank(),
            stem(3, "옛 문제 셋의 문장 [3점]"), grid_table(1030),
            stem(4, "옛 문제 넷의 문장 [3점]", column_break=True), box_table(1040), *choice_paragraphs(), blank(),
            stem(5, "옛 문제 다섯의 그림 문장 [3점]"), para(run(PICTURE)), short_table(1050, 1)]


def item_short(answer: int = 2, **more: object) -> dict:
    return {"type": "short_table", "stem": "새 짧은 문제", "points": 3, "answer": answer,
            "choices": ["새가", "새나", "새다", "새라", "새마"], **more}


def item_combo(answer: int = 3) -> dict:
    return {"type": "combo_table", "stem": "새 합답 문제", "points": 3.5, "answer": answer,
            "bogi": ["새 보기 하나", "새 보기 둘"], "choices": ["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄱ, ㄷ", "ㄴ, ㄷ"]}


def item_grid(answer: int = 1) -> dict:
    return {"type": "grid_table", "stem": "새 표 문제", "points": 4, "answer": answer, "head": ["ⓐ", "ⓑ", "ⓒ"],
            "rows": [[f"새값{row}{col}" for col in "가나다"] for row in range(5)]}


def item_paragraphs(answer: int = 5, **more: object) -> dict:
    return {"type": "paragraphs", "stem": "새 문단 문제", "points": 3, "answer": answer,
            "choices": [f"새 긴 선택지 {index}" for index in range(5)], **more}


def visible(xml: str) -> str:
    return re.sub(r"<[^>]+>", "", xml)


def package_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return "\n".join(visible(archive.read(info.filename).decode("utf-8", "ignore")) for info in archive.infolist()
                         if info.filename.endswith((".xml", ".txt", ".hpf", ".rdf")))


class ExamCase(unittest.TestCase):
    def setUp(self):
        holder_dir = tempfile.TemporaryDirectory()
        self.addCleanup(holder_dir.cleanup)
        self.folder = Path(holder_dir.name)
        self.result = self.folder / "결과.hwpx"

    def form(self, *body: str, first: str = "") -> Path:
        """가짜 시험지 양식. make_hwpx 골격에 단 설정, 머리, 문항, 꼬리, 그림, 옛 미리 보기를 넣는다."""
        base = self.folder / "base.hwpx"
        build_hwpx({"blocks": [{"type": "paragraph", "text": "**굵게** 보통"}]}, base)
        source = self.folder / "양식.hwpx"
        with zipfile.ZipFile(base) as archive, zipfile.ZipFile(source, "w") as out:
            for info in archive.infolist():
                data = archive.read(info.filename)
                if info.filename == SECTION:
                    xml = data.decode("utf-8")
                    start = xml.index("<hp:p ", xml.index("</hp:p>"))
                    xml = xml[:start] + first + "".join(body) + "</hs:sec>"
                    data = re.sub(r'colCount="\d+"', 'colCount="2"', xml, count=1).encode("utf-8")
                elif info.filename == "Contents/content.hpf":
                    item = '<opf:item id="image1" href="BinData/image1.png" media-type="image/png" isEmbeded="1"/>'
                    data = data.decode("utf-8").replace("</opf:manifest>", f"{item}</opf:manifest>").encode("utf-8")
                elif info.filename == "Preview/PrvText.txt":
                    data = "옛 문제 하나의 문장".encode("utf-8")
                elif info.filename == "Preview/PrvImage.png":
                    data = b"old preview image of the old exam" * 10
                out.writestr(info, data, compress_type=info.compress_type)
            out.writestr("BinData/image1.png", b"old picture", zipfile.ZIP_STORED)
        self.assertEqual(validate_package(source), [])
        return source

    def exam(self) -> Path:
        return self.form(*head(), *full_body(), *tail())

    def fill(self, source: Path, *items: dict, student: bool = False, fills: list | None = None) -> str:
        spec: dict = {"items": list(items)}
        if fills:
            spec["fills"] = fills
        self.outcome = fill_exam(source, spec, self.result, student)
        self.assertEqual(validate_package(self.result), [])
        return self.read(self.result)

    @staticmethod
    def read(path: Path, name: str = SECTION) -> str:
        with zipfile.ZipFile(path) as archive:
            return archive.read(name).decode("utf-8")

    def refused(self, source: Path, spec: dict, *expected: str) -> None:
        with self.assertRaises(FillError) as caught:
            fill_exam(source, spec, self.result)
        for phrase in expected:
            self.assertIn(phrase, str(caught.exception))
        self.assertFalse(self.result.exists())


class InspectTest(ExamCase):
    def test_reports_types_counts_marks_and_columns(self):
        listing = inspect_exam(self.exam())
        for phrase in ("단 수: 2단", "문항: 5개", "공통 지문: 1곳", "short_table (짧은 선택지 표): 2개",
                       "combo_table (합답형 선택지 표): 1개", "grid_table (표형 선지): 1개",
                       "paragraphs (문단 선택지): 1개", "정답 표시: 형광펜 #FFFF00, 문항 5개",
                       "머리·꼬리의 형광펜 1곳은 정답 표시가 아님", "2번: combo_table 표 2×3 + <보기>",
                       "3번: grid_table 표 6×4", "4번: paragraphs + 자료 상자", "5번: short_table 표 1×5 + 그림"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, listing)

    def test_shows_head_and_tail_numbers_but_not_old_items(self):
        listing = inspect_exam(self.exam())
        self.assertIn("표 1 행 1 칸 2: 과목: 가짜", listing)
        self.assertIn("※ 꼬리 확인사항 글", listing)
        self.assertNotIn("옛", listing)

    def test_form_without_answers_says_so(self):
        source = self.form(*head(), stem(1, "옛 문제 [2점]"), short_table(1010, mark=False))
        self.assertIn("정답 표시: 없음", inspect_exam(source))

    def test_numbered_notes_before_the_first_item_stay_in_the_head(self):
        source = self.form(para(word("1. 답안지에 이름을 쓰시오")), para(word("2. 시간을 지키시오")),
                           stem(1, "옛 문제"), short_table(1010))
        listing = inspect_exam(source)
        self.assertIn("문항: 1개", listing)
        self.assertIn("1. 답안지에 이름을 쓰시오", listing)

    def test_number_like_sentence_is_not_an_item(self):
        source = self.form(stem(1, "옛 문제"), para(word("4. 19 혁명을 다룬 자료의 설명글")), short_table(1010))
        self.assertIn("문항: 1개", inspect_exam(source))

    def test_form_without_items_is_refused(self):
        source = self.form(para(word("문항이 없는 문서")))
        with self.assertRaises(FillError) as caught:
            inspect_exam(source)
        self.assertIn("문항을 찾지 못함", str(caught.exception))


class CloneTest(ExamCase):
    def test_grows_past_the_number_of_frames_and_renumbers(self):
        xml = self.fill(self.exam(), *[item_short() for _ in range(7)])
        self.assertEqual(re.findall(r">(\d+)\.</hp:t>", xml), [str(n) for n in range(1, 8)])
        self.assertEqual(visible(xml).count("새라"), 7)

    def test_shrinks_below_the_number_of_frames(self):
        xml = self.fill(self.exam(), item_grid())
        self.assertEqual(re.findall(r">(\d+)\.</hp:t>", xml), ["1"])
        self.assertEqual(xml.count("<hp:tbl "), 3)          # 머리 표, 표형 선지, 꼬리 상자

    def test_choices_stay_in_tables_of_the_same_shape(self):
        xml = self.fill(self.exam(), item_short(), item_combo(), item_grid(), item_paragraphs(box="새 자료"))
        tables = re.findall(r'<hp:tbl [^>]*rowCnt="(\d+)" colCnt="(\d+)"', xml)
        self.assertEqual(tables, [("2", "2"), ("1", "5"), ("2", "3"), ("2", "3"), ("6", "4"), ("1", "1"), ("1", "1")])

    def test_head_and_tail_keep_their_exact_text(self):
        source = self.exam()
        original = self.read(source)
        xml = self.fill(source, item_short())
        start = original.index("[1~2]")
        self.assertEqual(xml[:original.rindex("<hp:p ", 0, start)], original[:original.rindex("<hp:p ", 0, start)])
        ending = original[original.index('<hp:tbl id="1090"'):]
        self.assertTrue(xml.endswith(ending))

    def test_cell_borders_and_table_width_are_copied(self):
        xml = self.fill(self.exam(), item_short())
        new = xml[xml.index("새가") - 2000:]
        self.assertIn('borderFillIDRef="1"', new)
        self.assertIn('<hp:sz width="5000" widthRelTo="ABSOLUTE"', xml)

    def test_clones_get_new_ids(self):
        xml = self.fill(self.exam(), *[item_short() for _ in range(4)], item_combo(), item_combo())
        ids = re.findall(r'<hp:tbl id="(\d+)"', xml)
        self.assertEqual(len(ids), len(set(ids)))
        orders = re.findall(r'<hp:tbl [^>]*zOrder="(\d+)"', xml)[1:-1]
        self.assertEqual(len(orders), len(set(orders)))

    def test_new_paragraphs_have_no_old_line_layout_and_no_forced_break(self):
        source = self.exam()
        xml = self.fill(source, item_paragraphs(), item_short())
        body = xml[xml.index("새 문단 문제") - 400:xml.index('<hp:tbl id="1090"')]
        self.assertNotIn("lineseg", body[400:])
        self.assertNotIn('columnBreak="1"', xml)

    def test_short_new_text_does_not_keep_the_old_box_height(self):
        xml = self.fill(self.exam(), item_paragraphs(box="짧은 글"))
        box = xml[xml.index("짧은 글"):]
        self.assertIn('height="300"', box[:box.index("</hp:tc>")])

    def test_items_stay_together_in_one_column(self):
        source = self.exam()
        xml = self.fill(source, item_paragraphs())
        header = self.read(self.result, "Contents/header.xml")
        shapes = dict(re.findall(r'<hh:paraPr id="(\d+)".*?keepWithNext="(\d)"', header, re.S))
        kept = re.search(r'paraPrIDRef="(\d+)"[^>]*>(?:(?!</hp:p>).)*새 문단 문제', xml, re.S).group(1)
        self.assertEqual(shapes[kept], "1")
        last = xml[:xml.index("⑤ 새 긴 선택지")]
        self.assertEqual(shapes[re.findall(r'paraPrIDRef="(\d+)"', last)[-1]], "0")
        count = re.search(r'<hh:paraProperties itemCnt="(\d+)"', header).group(1)
        self.assertEqual(int(count), len(shapes))

    def test_bogi_and_box_join_any_choice_type(self):
        xml = self.fill(self.exam(), item_short(box=["자료 하나", "자료 둘"], bogi=["보기 글"]))
        words = visible(xml)
        self.assertLess(words.index("자료 둘"), words.index("ㄱ. 보기 글"))
        self.assertLess(words.index("ㄱ. 보기 글"), words.index("① 새가"))
        self.assertIn("<보 기>".replace("<", "&lt;").replace(">", "&gt;"), words)

    def test_given_markers_and_numbers_are_not_doubled(self):
        item = item_short(stem="3. 숫자를 쓴 문제", choices=["① 새가", "② 새나", "③ 새다", "④ 새라", "⑤ 새마"])
        words = visible(self.fill(self.exam(), item))
        self.assertIn("① 새가", words)
        self.assertNotIn("① ① 새가", words)
        self.assertNotIn("3. 숫자", words)

    def test_special_characters_are_escaped(self):
        xml = self.fill(self.exam(), item_short(stem="A < B & C 비교"))
        ElementTree.fromstring(xml)
        self.assertIn("A &lt; B &amp; C", xml)

    def test_first_item_in_the_first_paragraph_keeps_section_settings(self):
        source = self.form(stem(1, "옛 문제 [2점]").replace("<hp:run", f'<hp:run charPrIDRef="{PLAIN}">{COLUMNS}</hp:run><hp:run', 1),
                           short_table(1010))
        xml = self.fill(source, item_short())
        self.assertEqual(xml.count("<hp:colPr"), self.read(source).count("<hp:colPr"))


class PassageTest(ExamCase):
    def spec(self, count: int = 2) -> dict:
        return {"type": "passage", "count": count, "lead": "다음을 읽고 답하시오.",
                "paragraphs": [{"label": "(가)", "text": "새 지문 첫째"}, {"label": "(나)", "text": "새 지문 둘째"},
                               {"label": "(다)", "text": "새 지문 셋째"}]}

    def test_range_follows_the_items_after_the_passage(self):
        words = visible(self.fill(self.exam(), item_short(), self.spec(), item_short(), item_short()))
        self.assertIn("[2~3] 다음을 읽고 답하시오.", words)
        self.assertIn("(다)", words)
        self.assertNotIn("[1~2]", words)

    def test_label_keeps_its_bold_shape(self):
        xml = self.fill(self.exam(), self.spec(), item_short(), item_short())
        self.assertIn(f'<hp:run charPrIDRef="{BOLD}"><hp:t> (가)</hp:t>', xml)

    def test_count_past_the_end_is_refused(self):
        self.refused(self.exam(), {"items": [self.spec(3), item_short()]}, "count가 3인데", "1개뿐")

    def test_no_passage_frame_is_refused(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010))
        self.refused(source, {"items": [self.spec(1), item_short()]}, "공통 지문 틀이 없음")


class NoOldContentTest(ExamCase):
    def test_nothing_of_the_old_items_is_left_anywhere_in_the_file(self):
        self.fill(self.exam(), item_short(), item_combo(), item_grid(), item_paragraphs(box="새 자료"))
        self.assertNotIn("옛", package_text(self.result))

    def test_old_picture_is_gone_from_the_package(self):
        xml = self.fill(self.exam(), item_short())
        self.assertNotIn("<hp:pic", xml)
        with zipfile.ZipFile(self.result) as archive:
            self.assertFalse([name for name in archive.namelist() if name.startswith("BinData/")])
            self.assertNotIn("BinData", archive.read("Contents/content.hpf").decode("utf-8"))

    def test_old_preview_image_is_replaced(self):
        self.fill(self.exam(), item_short())
        with zipfile.ZipFile(self.result) as archive:
            image = archive.read("Preview/PrvImage.png")
        self.assertTrue(image.startswith(b"\x89PNG"))
        self.assertNotIn(b"old exam", image)

    def test_preview_text_shows_the_new_items(self):
        self.fill(self.exam(), item_short())
        preview = self.read(self.result, "Preview/PrvText.txt")
        self.assertIn("새 짧은 문제", preview)
        self.assertNotIn("옛", preview)

    def test_picture_used_by_the_head_stays(self):
        source = self.form(para(run(PICTURE)), stem(1, "옛 문제"), short_table(1010))
        self.fill(source, item_short())
        with zipfile.ZipFile(self.result) as archive:
            self.assertIn("BinData/image1.png", archive.namelist())

    def test_old_cell_text_outside_the_choices_is_cleared(self):
        rows = [[cell(0, 0, para(word("① 가"))), cell(0, 1, para(word("② 나"))), cell(0, 2, para(word("③ 다")))],
                [cell(1, 0, para(word("④ 라"))), cell(1, 1, para(word("⑤ 마"))),
                 cell(1, 2, para(word("옛 메모 칸 긴 글")))]]
        source = self.form(stem(1, "옛 문제"), holder(table(rows, cols=3), 1010))
        item = item_combo()
        del item["bogi"]
        self.assertNotIn("옛", visible(self.fill(source, item)))


class AnswerMarkTest(ExamCase):
    def choice_runs(self, xml: str) -> list[str]:
        """형광펜 안의 글 목록."""
        return [visible(found) for found in re.findall(r"<hp:markpenBegin[^>]*/>(.*?)<hp:markpenEnd", xml, re.S)]

    def test_only_the_answer_is_marked_for_each_type(self):
        cases = ((item_short(4), ["④ 새라"]), (item_combo(5), ["⑤ ㄴ, ㄷ"]), (item_paragraphs(2), ["② 새 긴 선택지 1"]),
                 (item_grid(3), ["③", "새값2가", "새값2나", "새값2다"]))
        for item, expected in cases:
            with self.subTest(kind=item["type"]):
                self.result = self.folder / f"{item['type']}.hwpx"
                marks = self.choice_runs(self.fill(self.exam(), item))
                self.assertEqual(marks[1:], expected)       # 첫째는 머리의 "총 7면"

    def test_uses_the_forms_color(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010).replace("#FFFF00", "#00FF00"))
        self.assertIn('color="#00FF00"', self.fill(source, item_short()))

    def test_student_copy_has_no_mark_at_all(self):
        xml = self.fill(self.exam(), item_short(), item_combo(), item_grid(), item_paragraphs(), student=True)
        self.assertNotIn("markpen", xml)
        for name in ("Contents/header.xml", "Preview/PrvText.txt"):
            self.assertNotIn("markpen", self.read(self.result, name))

    def test_student_copy_differs_from_the_original_only_in_marks(self):
        items = (item_short(), item_combo(), item_grid(), item_paragraphs(box="새 자료"))
        source = self.exam()
        original = self.fill(source, *items)
        self.result = self.folder / "학생.hwpx"
        student = self.fill(source, *items, student=True)
        self.assertEqual(visible(student), visible(original))

    def test_student_copy_keeps_head_text_of_a_highlight(self):
        words = visible(self.fill(self.exam(), item_short(), student=True))
        self.assertIn("총 7면", words)

    def test_answer_in_a_student_copy_cannot_be_told_from_the_runs(self):
        xml = self.fill(self.exam(), item_short(1), student=True)
        chars = re.findall(r'charPrIDRef="(\d+)"><hp:t>[①-⑤] ', xml)
        self.assertEqual(len(set(chars)), 1)

    def test_form_without_marks_stays_unmarked(self):
        source = self.form(stem(1, "옛 문제 [2점]"), short_table(1010, mark=False))
        self.assertNotIn("markpen", self.fill(source, item_short()))

    def test_marked_equation_choice_is_inside_the_highlight(self):
        xml = self.fill(self.exam(), item_short(1, choices=["{{1/2}}", "{{1/3}}", "{{1/4}}", "{{1/5}}", "{{1/6}}"]))
        inside = re.findall(r"<hp:markpenBegin[^>]*/>(.*?)<hp:markpenEnd", xml, re.S)[1]
        self.assertIn("<hp:equation", inside)

    def test_colored_answer_form_keeps_its_method(self):
        source = self.colored_form()
        xml = self.fill(source, item_short(3))
        self.assertIn(f'<hp:run charPrIDRef="{self.red}"><hp:t>③ 새다', xml)
        self.assertEqual(xml.count(f'charPrIDRef="{self.red}"'), 1)

    def test_colored_answer_student_copy_has_no_red(self):
        xml = self.fill(self.colored_form(), item_short(3), student=True)
        self.assertNotIn(f'charPrIDRef="{self.red}"', xml)

    def colored_form(self) -> Path:
        cells = [cell(0, index, para(word(f"{name} 옛 선택지", 99 if index == 1 else PLAIN)))
                 for index, name in enumerate(CHOICE_NAMES)]
        source = self.form(stem(1, "옛 문제"), holder(table([cells], cols=5), 1010).replace('"99"', '"0"'))
        return self.with_red_shape(source, cells)

    def with_red_shape(self, source: Path, cells: list[str]) -> Path:
        """글자색만 다른 글자 모양을 양식에 더하고 둘째 선택지에 건다."""
        target = self.folder / "색.hwpx"
        with zipfile.ZipFile(source) as archive, zipfile.ZipFile(target, "w") as out:
            header = archive.read("Contents/header.xml").decode("utf-8")
            numbers = [int(n) for n in re.findall(r'<hh:charPr id="(\d+)"', header)]
            self.red = max(numbers) + 1
            shape = re.search(rf'<hh:charPr id="{PLAIN}".*?</hh:charPr>', header, re.S).group(0)
            shape = shape.replace(f'id="{PLAIN}"', f'id="{self.red}"', 1).replace('textColor="#000000"', 'textColor="#FF0000"', 1)
            header = header.replace("</hh:charProperties>", f"{shape}</hh:charProperties>")
            header = re.sub(r'(<hh:charProperties itemCnt=")(\d+)', lambda m: f"{m.group(1)}{int(m.group(2)) + 1}", header)
            for info in archive.infolist():
                data = archive.read(info.filename)
                if info.filename == "Contents/header.xml":
                    data = header.encode("utf-8")
                elif info.filename == SECTION:
                    data = data.decode("utf-8").replace(
                        '<hp:run charPrIDRef="0"><hp:t>② 옛 선택지', f'<hp:run charPrIDRef="{self.red}"><hp:t>② 옛 선택지').encode("utf-8")
                out.writestr(info, data, compress_type=info.compress_type)
        self.assertEqual(validate_package(target), [])
        return target


class MarkupTest(ExamCase):
    def test_bold_uses_the_forms_bold_shape(self):
        xml = self.fill(self.exam(), item_short(stem="**옳지 않은** 것은?"))
        self.assertIn(f'<hp:run charPrIDRef="{BOLD}"><hp:t>옳지 않은</hp:t>', xml)

    def test_underline_without_a_shape_is_refused_not_printed_raw(self):
        self.refused(self.exam(), {"items": [item_short(stem="밑줄 친 __부분__")]}, "문항 1", "밑줄 글자 모양이 없어")

    def test_equation_becomes_a_hangul_equation(self):
        xml = self.fill(self.exam(), item_short(stem="{{2/3}}와 같은 값은?"))
        self.assertIn("<hp:script>{2} over {3}</hp:script>", xml)
        self.assertNotIn("{{", visible(xml))

    def test_equations_have_their_own_ids_and_the_forms_size(self):
        xml = self.fill(self.exam(), item_short(stem="{{1/2}}과 {{1/3}}"))
        ids = re.findall(r'<hp:equation id="(\d+)" zOrder="(\d+)"', xml)
        self.assertEqual(len({number for number, _ in ids}), 2)
        self.assertEqual(len({order for _, order in ids}), 2)
        self.assertNotIn('baseUnit="1000"', xml.replace('baseUnit="1100"', ""))

    def test_mistyped_equation_is_noted(self):
        self.fill(self.exam(), item_short(stem="{{가 = 1}} 값"))
        self.assertTrue(any("수식 안에 한글" in note for note in self.outcome.notes))

    def test_line_break_in_stem(self):
        self.assertIn("첫 줄<hp:lineBreak/>둘째 줄", self.fill(self.exam(), item_short(stem="첫 줄\n둘째 줄")))


class FrameChoiceTest(ExamCase):
    def test_missing_type_names_the_item_and_what_the_form_has(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010))
        self.refused(source, {"items": [item_short(), item_grid()]},
                     "문항 2", "grid_table(표형 선지) 틀이 없음", "양식의 유형: short_table")

    def test_paragraph_type_is_not_silently_used_for_a_table_type(self):
        source = self.form(stem(1, "옛 문제"), *choice_paragraphs())
        self.refused(source, {"items": [item_short()]}, "short_table", "틀이 없음")

    def test_table_type_is_not_silently_used_for_paragraph_choices(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010))
        self.refused(source, {"items": [item_paragraphs()]}, "paragraphs(문단 선택지) 틀이 없음")

    def test_nearest_table_is_used_and_reported(self):
        source = self.form(stem(1, "옛 문제"), bogi_table(1020), combo_table(1021))
        xml = self.fill(source, item_short())
        self.assertIn('rowCnt="2" colCnt="3"', xml)
        self.assertTrue(any("가장 가까운 combo_table" in note for note in self.outcome.notes))

    def test_bogi_falls_back_to_box_and_reports(self):
        source = self.form(stem(1, "옛 문제"), box_table(1040), short_table(1010))
        words = visible(self.fill(source, item_short(bogi=["새 보기"])))
        self.assertIn("ㄱ. 새 보기", words)
        self.assertTrue(any("자료 상자 틀을 썼습니다" in note for note in self.outcome.notes))

    def test_box_without_any_box_frame_is_refused(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010))
        self.refused(source, {"items": [item_short(box="자료")]}, "자료 상자 틀이 없음")

    def test_wrong_choice_count_is_refused_for_each_type(self):
        six = ["가", "나", "다", "라", "마", "바"]       # 틀보다 많은 선택지는 줄여 쓸 수 없다 (적은 쪽은 줄여 쓴다)
        cases = ((item_short(1, choices=six), 6), ({**item_combo(1), "choices": six}, 6),
                 (item_paragraphs(1, choices=six), 6), ({**item_grid(), "rows": [["가", "나", "다"]] * 4}, 4))
        for item, count in cases:
            with self.subTest(kind=item["type"]):
                self.refused(self.exam(), {"items": [item]}, "문항 1", f"선택지가 {count}개", "5개")

    def test_grid_with_other_columns_is_refused(self):
        item = {**item_grid(), "head": ["ⓐ", "ⓑ"], "rows": [["가", "나"]] * 5}
        self.refused(self.exam(), {"items": [item]}, "내용 2칸", "내용 3칸")

    def test_every_failure_is_reported_at_once(self):
        items = [item_short(1, choices=["가"]), item_short(), item_paragraphs(1, choices=["나"])]
        self.refused(self.exam(), {"items": items}, "문항 1", "문항 3")

    def test_long_short_choice_is_noted(self):
        self.fill(self.form(stem(1, "옛"), short_table(1010)), item_short(choices=["아주 길고 긴 선택지입니다"] * 5))
        self.assertTrue(any("칸보다 길어" in note for note in self.outcome.notes))

    def test_fitting_equation_choice_is_not_noted(self):
        wide = short_table(1010).replace('cellSz width="1000"', 'cellSz width="5000"').replace(
            '<hp:sz width="5000"', '<hp:sz width="25000"')
        self.fill(self.form(stem(1, "옛"), wide), item_short(choices=["{{1/2}}"] * 5))
        self.assertFalse(any("칸보다 길어" in note for note in self.outcome.notes))


class WrittenTest(ExamCase):
    def form_with_written(self) -> Path:
        return self.form(stem(1, "옛 문제 [2점]"), short_table(1010), blank(),
                         para(word("서답형 1.", BOLD), word(" 옛 서답형 문제 [5점]")),
                         holder(table([[cell(0, 0, para(word("옛 답 칸 안내 글")))]], cols=1), 1060), blank(),
                         para(word("서답형 2.", BOLD), word(" 옛 서답형 둘째 문제 [5점]")))

    def test_written_items_count_apart_and_old_text_goes(self):
        written = {"type": "written", "stem": "새 서술 문제", "points": 5}
        words = visible(self.fill(self.form_with_written(), item_short(), written, written))
        self.assertIn("서답형 1. 새 서술 문제 [5점]", words)
        self.assertIn("서답형 2. 새 서술 문제", words)
        self.assertNotIn("옛", words)

    def test_written_without_frame_is_refused(self):
        self.refused(self.exam(), {"items": [{"type": "written", "stem": "새", "points": 5}]},
                     "written(서답형) 틀이 없음")


class SpecTest(ExamCase):
    def test_bad_specs_are_refused_with_the_item_named(self):
        cases = (({"items": []}, '"items" 문항 목록이 없음'), ({"items": "x"}, '"items"'), ([], "items"),
                 ({"items": [item_short()], "extra": 1}, "모르는 항목"),
                 ({"items": [{"type": "그림"}]}, "type은"),
                 ({"items": [item_short(1, picture="a.png")]}, "그림은 넣을 수 없음"),
                 ({"items": [item_short(1, more=1)]}, "모르는 항목 more"),
                 ({"items": [item_short(6)]}, "1부터 5까지"), ({"items": [item_short(True)]}, "answer"),
                 ({"items": [item_short(stem=" ")]}, "stem"), ({"items": [item_short(points="많이")]}, "points"),
                 ({"items": [item_short(bogi="글")]}, "bogi"), ({"items": [item_short(box={"a": 1})]}, "box"),
                 ({"items": [item_short(choices=[])]}, "choices"), ({"items": [{**item_grid(), "rows": []}]}, "rows"),
                 ({"items": [{**item_grid(), "rows": [["가"]] * 5}]}, "칸 수"),
                 ({"items": [{"type": "passage", "count": 0}, item_short()]}, "count"),
                 ({"items": [{"type": "passage", "count": 1}, item_short()]}, "lead"),
                 ({"items": [{"type": "passage", "count": 1, "lead": "글"}, item_short()]}, "paragraphs"),
                 ({"items": [{"type": "passage", "count": 1, "lead": "글", "paragraphs": [{"x": 1}]}, item_short()]},
                  "paragraphs"))
        source = self.exam()
        for spec, phrase in cases:
            with self.subTest(phrase=phrase):
                self.refused(source, spec, phrase)

    def test_form_that_writes_points_needs_points(self):
        item = item_short()
        del item["points"]
        self.refused(self.exam(), {"items": [item]}, "points를 적어 주세요")

    def test_points_may_be_written_in_the_stem(self):
        item = item_short(stem="문제 [3점]")
        del item["points"]
        self.assertIn("문제 [3점]", visible(self.fill(self.exam(), item)))

    def test_form_without_points_does_not_require_them(self):
        item = item_short()
        del item["points"]
        self.assertIn("새 짧은 문제", visible(self.fill(self.form(stem(1, "옛 문제"), short_table(1010)), item)))

    def test_refuses_to_overwrite(self):
        source = self.exam()
        self.result.write_bytes(b"old")
        with self.assertRaises(FillError) as caught:
            fill_exam(source, {"items": [item_short()]}, self.result)
        self.assertIn("덮어쓰지 않음", str(caught.exception))
        with self.assertRaises(FillError) as caught:
            fill_exam(source, {"items": [item_short()]}, source)
        self.assertIn("원본 양식", str(caught.exception))

    def test_missing_folder_is_refused(self):
        with self.assertRaises(FillError):
            fill_exam(self.exam(), {"items": [item_short()]}, self.folder / "없음" / "결과.hwpx")

    def test_column_change_between_items_is_refused(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010), blank(),
                           para(run(COLUMNS), word("2. 옛 문제")), short_table(1011))
        self.refused(source, {"items": [item_short()]}, "단 설정이 바뀌는")

    def test_unknown_paragraph_inside_an_item_is_not_carried_over(self):
        source = self.form(stem(1, "옛 문제"), short_table(1010), para(word("끝 안내가 빈 줄 없이 붙은 옛 문단")))
        self.assertNotIn("옛", visible(self.fill(source, item_short())))

    def test_old_text_guard_stops_the_file_if_cloning_ever_carries_old_text(self):
        leaked = para(word("1. 옛 문제 하나의 문장 [2점] 뒤에 붙은 글"))
        with mock.patch("fill_exam._build_body", return_value=(leaked, 1)):
            self.refused(self.exam(), {"items": [item_short()]}, "옛 문항 글이 결과에 남음")

    def test_student_guard_stops_the_file_if_a_mark_survives(self):
        with mock.patch("fill_exam._strip_marks", side_effect=lambda entries, _names: entries):
            with self.assertRaises(FillError) as caught:
                fill_exam(self.exam(), {"items": [item_short()]}, self.result, student=True)
        self.assertIn("학생용에 정답 표시가 남음", str(caught.exception))
        self.assertFalse(self.result.exists())

    def test_items_spread_over_two_sections_are_refused(self):
        source = self.exam()
        target = self.folder / "두구역.hwpx"
        second = self.read(source)
        with zipfile.ZipFile(source) as archive, zipfile.ZipFile(target, "w") as out:
            for info in archive.infolist():
                out.writestr(info, archive.read(info.filename), compress_type=info.compress_type)
            out.writestr("Contents/section1.xml", second, zipfile.ZIP_DEFLATED)
        self.refused(target, {"items": [item_short()]}, "여러 구역")


class FillsTest(ExamCase):
    def test_head_cell_and_find_are_filled(self):
        xml = self.fill(self.exam(), item_short(), fills=[{"find": "○학기", "replace": "2학기"},
                                                         {"table": 1, "row": 1, "col": 2, "text": "과목: 시험"}])
        words = visible(xml)
        self.assertIn("2026학년도 2학기 정기시험", words)
        self.assertIn("과목: 시험", words)

    def test_highlighted_head_text_stays_highlighted_when_changed(self):
        xml = self.fill(self.exam(), item_short(), fills=[{"find": "7면", "replace": "4면"}])
        self.assertRegex(xml, r"markpenBegin[^>]*/>총 4면<hp:markpenEnd")

    def test_find_does_not_reach_old_items(self):
        self.refused(self.exam(), {"items": [item_short()], "fills": [{"find": "옛 문제 하나", "replace": "새"}]}, "찾지 못함")

    def test_cell_inside_items_is_refused(self):
        self.refused(self.exam(), {"items": [item_short()], "fills": [{"table": 2, "row": 1, "col": 1, "text": "새"}]},
                     "fills는 머리와 꼬리만")

    def test_tail_cell_can_be_filled(self):
        words = visible(self.fill(self.exam(), item_short(), fills=[{"find": "꼬리 확인사항", "replace": "새 확인사항"}]))
        self.assertIn("새 확인사항", words)

    def test_head_count_and_total_differences_are_noted(self):
        self.fill(self.exam(), item_short())
        notes = "\n".join(self.outcome.notes)
        self.assertIn("26문항", notes)
        self.assertIn("100점", notes)

    def test_matching_head_count_is_not_noted(self):
        items = [item_short() for _ in range(26)]
        self.fill(self.exam(), *items)
        self.assertNotIn("문항이 지시", "\n".join(self.outcome.notes))


class CommandLineTest(ExamCase):
    def run_main(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def spec_file(self, spec: dict) -> str:
        path = self.folder / "지시.json"
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_inspect(self):
        code, output = self.run_main("--inspect", str(self.exam()))
        self.assertEqual(code, 0)
        self.assertIn("문항: 5개", output)

    def test_fill_and_student(self):
        source, spec = str(self.exam()), self.spec_file({"items": [item_short()]})
        code, output = self.run_main(source, spec, str(self.result))
        self.assertEqual(code, 0)
        self.assertIn("원안지", output)
        target = self.folder / "학생.hwpx"
        code, output = self.run_main(source, spec, str(target), "--student")
        self.assertEqual(code, 0)
        self.assertIn("학생용", output)
        self.assertNotIn("markpen", self.read(target))

    def test_failure_makes_no_file(self):
        code, output = self.run_main(str(self.exam()), self.spec_file({"items": [item_grid(9)]}), str(self.result))
        self.assertEqual(code, 1)
        self.assertIn("문항 1", output)
        self.assertFalse(self.result.exists())

    def test_bad_json_and_hwp_file(self):
        bad = self.folder / "나쁨.json"
        bad.write_text("{", encoding="utf-8")
        self.assertEqual(self.run_main(str(self.exam()), str(bad), str(self.result))[0], 1)
        hwp = self.folder / "옛.hwp"
        hwp.write_bytes(b"\xd0\xcf\x11\xe0 old")
        code, output = self.run_main("--inspect", str(hwp))
        self.assertEqual(code, 1)
        self.assertIn("hwpx로 저장", output)

    def rewritten(self, name: str, change) -> Path:
        source, target = self.exam(), self.folder / name
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w") as new:
            for info in old.infolist():
                data = change(info.filename, old.read(info.filename))
                if data is not None:
                    new.writestr(info, data)
        return target

    def test_form_without_manifest_is_refused_in_korean(self):
        source = self.rewritten("목록없음.hwpx", lambda name, data: None if name == "Contents/content.hpf" else data)
        self.refused(source, {"items": [item_short()]}, "content.hpf")

    def test_stem_without_paragraph_shape_is_still_filled(self):
        def drop(name: str, data: bytes) -> bytes:
            return data.replace(b'paraPrIDRef="0" styleIDRef="0"', b'styleIDRef="0"') if name == SECTION else data
        fill_exam(self.rewritten("모양없음.hwpx", drop), {"items": [item_short()]}, self.result)
        self.assertIn("새 짧은 문제", self.read(self.result))

    def test_unexpected_error_is_reported_without_a_traceback(self):
        spec = self.spec_file({"items": [item_short()]})
        with mock.patch("fill_exam.fill_exam", side_effect=AttributeError("x")):
            code, output = self.run_main(str(self.exam()), spec, str(self.result))
        self.assertEqual(code, 1)
        self.assertIn("내부 오류: 예상하지 못한 양식입니다 (AttributeError)", output)

    def test_usage(self):
        self.assertEqual(self.run_main()[0], 2)
        self.assertEqual(self.run_main("--inspect", "a", "--student")[0], 2)


if __name__ == "__main__":
    unittest.main()
