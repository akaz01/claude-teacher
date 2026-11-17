"""fill_exam.py 시험: 양식 XML의 속성 순서가 달라도 같은 결과가 나오는지, 읽지 못하면 알리는지 본다.

한글은 속성을 정해진 순서로 저장하지만, 다른 프로그램이 저장한 양식은 순서가 다를 수 있다.
"""

import re
import zipfile
from pathlib import Path

from fill_exam import fill_exam
from test_fill_exam import (SECTION, ExamCase, item_combo, item_paragraphs, item_short, short_table, stem)

HEADER = "Contents/header.xml"
TAG = re.compile(r"<(hp:cellSz|hp:sz|hh:paraPr|hp:tbl)\b([^>]*?)(/?)>")
ATTR = re.compile(r'\S+="[^"]*"')


def reversed_attributes(xml: str) -> str:
    """cellSz, sz, paraPr, tbl 태그의 속성 순서를 거꾸로 뒤집는다."""
    def flip(found: re.Match) -> str:
        attrs = " ".join(reversed(ATTR.findall(found.group(2))))
        return f"<{found.group(1)} {attrs}{found.group(3)}>"
    return TAG.sub(flip, xml)


def sorted_attributes(xml: str) -> str:
    """같은 태그를 속성 이름 순으로 정리해 순서만 다른 두 XML을 견줄 수 있게 한다."""
    def order(found: re.Match) -> str:
        return f"<{found.group(1)} {' '.join(sorted(ATTR.findall(found.group(2))))}{found.group(3)}>"
    return TAG.sub(order, xml)


def rewrite(source: Path, name_to_change: dict) -> None:
    """양식 파일의 항목을 바꿔 다시 쓴다. name_to_change는 항목 이름 -> 글을 바꾸는 함수."""
    copy = source.with_suffix(".tmp")
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(copy, "w") as out:
        for info in archive.infolist():
            data = archive.read(info.filename)
            if info.filename in name_to_change:
                data = name_to_change[info.filename](data.decode("utf-8")).encode("utf-8")
            out.writestr(info, data, compress_type=info.compress_type)
    copy.replace(source)


class AttributeOrderTest(ExamCase):
    def test_reversed_attribute_order_gives_the_same_body(self):
        normal = self.exam()
        flipped = self.folder / "뒤집음.hwpx"
        flipped.write_bytes(normal.read_bytes())
        rewrite(flipped, {SECTION: reversed_attributes, HEADER: reversed_attributes})
        expected = self.fill(normal, item_paragraphs(box="짧은 글"), item_short())
        self.result.unlink()
        actual = self.fill(flipped, item_paragraphs(box="짧은 글"), item_short())
        self.assertEqual(sorted_attributes(expected), sorted_attributes(actual))
        self.assertIn('height="300"', actual[actual.index("짧은 글"):])
        header = self.read(self.result, HEADER)
        self.assertIn('keepWithNext="1"', header)

    def test_cloned_tables_get_unique_ids_when_id_follows_zorder(self):
        source = self.exam()
        rewrite(source, {SECTION: reversed_attributes})
        xml = self.fill(source, *[item_short() for _ in range(4)], item_combo(), item_combo())
        tags = re.findall(r"<hp:tbl\b[^>]*>", xml)
        ids = [re.search(r'\bid="(\d+)"', tag).group(1) for tag in tags]
        orders = [re.search(r'\bzOrder="(\d+)"', tag).group(1) for tag in tags]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(orders[1:-1]), len(set(orders[1:-1])))

    def test_paragraph_shape_count_grows_when_item_count_follows_other_attributes(self):
        source = self.exam()
        rewrite(source, {HEADER: lambda xml: xml.replace(
            '<hh:paraProperties itemCnt=', '<hh:paraProperties extra="1" itemCnt=', 1)})
        self.fill(source, item_paragraphs(), item_short())
        header = self.read(self.result, HEADER)
        count = int(re.search(r'<hh:paraProperties[^>]*\bitemCnt="(\d+)"', header).group(1))
        self.assertEqual(count, len(re.findall(r"<hh:paraPr ", header)))

    def test_long_choice_note_survives_reversed_cell_size(self):
        source = self.form(stem(1, "옛"), short_table(1010))
        rewrite(source, {SECTION: reversed_attributes})
        self.fill(source, item_short(choices=["아주 길고 긴 선택지입니다"] * 5))
        self.assertTrue(any("칸보다 길어" in note for note in self.outcome.notes))

    def test_fitting_choice_is_not_noted_with_reversed_cell_size(self):
        wide = short_table(1010).replace('cellSz width="1000"', 'cellSz width="5000"').replace(
            '<hp:sz width="5000"', '<hp:sz width="25000"')
        source = self.form(stem(1, "옛"), wide)
        rewrite(source, {SECTION: reversed_attributes})
        self.fill(source, item_short(choices=["짧음"] * 5))
        self.assertEqual([note for note in self.outcome.notes if "칸" in note], [])

    def test_unreadable_cell_width_skips_the_check_and_says_so(self):
        source = self.form(stem(1, "옛"), short_table(1010))
        rewrite(source, {SECTION: lambda xml: xml.replace('cellSz width="1000"', 'cellSz wide="1000"')})
        spec = {"items": [item_short(choices=["아주 길고 긴 선택지입니다"] * 5)]}
        result = fill_exam(source, spec, self.result)
        notes = " ".join(result.notes)
        self.assertNotIn("칸보다 길어", notes)
        self.assertIn("칸 너비를 읽지 못해", notes)

    def test_missing_keep_with_next_is_reported(self):
        source = self.exam()
        rewrite(source, {HEADER: lambda xml: re.sub(r'\s*keepWithNext="\d"', "", xml)})
        result = fill_exam(source, {"items": [item_paragraphs()]}, self.result)
        self.assertIn("다음 문단과 함께", " ".join(result.notes))
