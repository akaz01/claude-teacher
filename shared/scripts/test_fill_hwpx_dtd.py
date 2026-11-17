"""DTD(<!DOCTYPE·<!ENTITY)가 든 hwpx 양식: 다른 자리를 바꾸거나 추적 로그를 내지 않고 한국어 오류로 멈춘다."""

import re
import unittest
import zipfile

import fill_hwpx_parse
from fill_exam_parse import inspect_exam
from fill_hwpx import FillError, fill_form, inspect_form, main
from test_fill_hwpx import SECTION, FormCase, para, text

DTD = '<!DOCTYPE hs:sec [<!ENTITY e "ABC">]>'


class DtdFormTest(FormCase):
    def dtd_form(self, entry=SECTION):
        source = self.form(para(text("가QQZZ나")), para(text("바꿀 글")))
        with zipfile.ZipFile(source) as archive:
            entries = {info.filename: (info, archive.read(info)) for info in archive.infolist()}
        info, data = entries[entry]
        xml = data.decode("utf-8")
        xml = re.sub(r"\?>", "?>" + DTD, xml, count=1).replace("QQZZ", "&e;", 1)
        entries[entry] = (info, xml.encode("utf-8"))
        broken = self.folder / "dtd.hwpx"
        with zipfile.ZipFile(broken, "w") as out:
            for item, content in entries.values():
                out.writestr(item, content, compress_type=item.compress_type)
        return broken

    def test_fill_refuses_in_korean(self):
        with self.assertRaises(FillError) as caught:
            fill_form(self.dtd_form(), {"fills": [{"find": "바꿀 글", "replace": "새 글"}]}, self.result)
        self.assertIn("DTD", str(caught.exception))
        self.assertFalse(self.result.exists())

    def test_dtd_outside_the_body_is_refused_too(self):
        for entry in ("Contents/header.xml", "Contents/content.hpf"):
            with self.subTest(entry=entry):
                with self.assertRaises(FillError) as caught:
                    fill_form(self.dtd_form(entry), {"fills": [{"find": "바꿀 글", "replace": "새 글"}]}, self.result)
                self.assertIn("DTD", str(caught.exception))
                self.assertIn(entry, str(caught.exception))
                self.assertFalse(self.result.exists())

    def test_inspect_and_main_do_not_trace(self):
        source = self.dtd_form()
        with self.assertRaises(FillError):
            inspect_form(source)
        self.assertEqual(main(["--inspect", str(source)]), 1)

    def test_fill_exam_refuses_in_korean(self):
        with self.assertRaises(FillError) as caught:
            inspect_exam(self.dtd_form())
        self.assertIn("DTD", str(caught.exception))


class EntityDecodeTest(unittest.TestCase):
    def test_unknown_entity_is_an_error_not_several_chars(self):
        with self.assertRaises(ValueError):
            fill_hwpx_parse.SectionReader('<hp:p><hp:run><hp:t>&e;</hp:t></hp:run></hp:p>', 0).read()

    def test_doctype_token_is_refused_by_reader(self):
        with self.assertRaises(ValueError):
            fill_hwpx_parse.SectionReader(DTD + '<hp:p><hp:run><hp:t>x</hp:t></hp:run></hp:p>', 0).read()


if __name__ == "__main__":
    unittest.main()
