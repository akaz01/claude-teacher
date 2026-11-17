"""make_hwpx_save.py 시험: 임시 파일 → 검사 → 원자적 교체, 기존 파일 보호, DTD 거부."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from make_hwpx import build_hwpx
from make_hwpx_check import validate_package
from make_hwpx_save import file_error_message, hwpx_check, save_atomically
from make_hwpx_zip import PackageError, refuse_dtd


class SaveCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = Path(holder.name)
        self.target = self.folder / "결과.hwpx"

    def test_writes_through_temp_file_and_replaces(self):
        seen = []

        def write(path: Path) -> None:
            seen.append(path)
            path.write_bytes(b"ok")

        save_atomically(self.target, write)
        self.assertEqual(self.target.read_bytes(), b"ok")
        self.assertNotEqual(seen[0], self.target)
        self.assertEqual(seen[0].parent, self.target.parent)
        self.assertEqual(list(self.folder.iterdir()), [self.target])

    def test_failed_check_leaves_nothing(self):
        def check(path: Path) -> None:
            raise ValueError("검사 실패")

        with self.assertRaises(ValueError):
            save_atomically(self.target, lambda path: path.write_bytes(b"broken"), check)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_refuses_existing_file_by_default(self):
        self.target.write_bytes(b"teacher")
        with self.assertRaises(FileExistsError) as caught:
            save_atomically(self.target, lambda path: path.write_bytes(b"new"))
        self.assertIn("덮어쓰지 않음", str(caught.exception))
        self.assertEqual(self.target.read_bytes(), b"teacher")
        self.assertEqual(list(self.folder.iterdir()), [self.target])

    def test_file_made_during_check_is_not_overwritten(self):
        def check(path: Path) -> None:
            self.target.write_bytes(b"other")      # 검사하는 사이에 같은 이름의 파일이 생김

        with self.assertRaises(FileExistsError):
            save_atomically(self.target, lambda path: path.write_bytes(b"mine"), check)
        self.assertEqual(self.target.read_bytes(), b"other")
        self.assertEqual(list(self.folder.iterdir()), [self.target])

    def test_file_made_just_before_the_move_is_not_overwritten(self):
        import make_hwpx_save
        original = make_hwpx_save._guard

        def late_guard(target, existing):          # 마지막 확인은 통과시키고 그 직후에 파일이 생김
            original(target, existing)
            if any(self.folder.glob("*.tmp")):
                target.write_bytes(b"other")

        make_hwpx_save._guard = late_guard
        self.addCleanup(setattr, make_hwpx_save, "_guard", original)
        with self.assertRaises(FileExistsError):
            save_atomically(self.target, lambda path: path.write_bytes(b"mine"))
        self.assertEqual(self.target.read_bytes(), b"other")
        self.assertEqual(list(self.folder.iterdir()), [self.target])

    def test_own_mode_overwrites_only_files_made_by_this_tool(self):
        build_hwpx({"blocks": [{"type": "paragraph", "text": "처음"}]}, self.target)
        save_atomically(self.target, lambda path: path.write_bytes(b"again"), existing="own")
        self.assertEqual(self.target.read_bytes(), b"again")
        with self.assertRaises(FileExistsError):       # 이제 이 도구가 만든 hwpx가 아니다
            save_atomically(self.target, lambda path: path.write_bytes(b"x"), existing="own")

    def test_hwpx_check_raises_given_error_with_problems(self):
        check = hwpx_check(RuntimeError, "검사 실패:")
        with self.assertRaises(RuntimeError) as caught:
            save_atomically(self.target, lambda path: path.write_bytes(b"not a zip"), check)
        self.assertTrue(str(caught.exception).startswith("검사 실패:\n"))
        self.assertFalse(self.target.exists())

    def test_hwpx_check_ignores_known_problems(self):
        problem = validate_package(Path(self.folder / "없는 파일.hwpx"))
        check = hwpx_check(RuntimeError, "검사 실패:", known=problem)
        missing = self.folder / "없는 파일.hwpx"
        check(missing)      # 원본에 있던 문제만 있으면 통과


class DtdTest(unittest.TestCase):
    def test_doctype_and_entity_are_refused_in_korean(self):
        for xml in (b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY e "ABC">]><a>&e;</a>',
                    '<!ENTITY e "x">'.encode("utf-8")):
            with self.assertRaises(PackageError) as caught:
                refuse_dtd(xml, "Contents/section0.xml")
            self.assertIn("DTD", str(caught.exception))
            self.assertIn("section0", str(caught.exception))

    def test_utf16_and_utf32_dtd_are_refused_with_or_without_bom(self):
        xml = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE a [<!ENTITY e "ABC">]><a>&e;</a>'
        for encoding in ("utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be"):
            with self.subTest(encoding=encoding):
                with self.assertRaises(PackageError) as caught:
                    refuse_dtd(xml.encode(encoding), "Contents/section0.xml")
                self.assertIn("DTD", str(caught.exception))

    def test_plain_utf16_xml_passes(self):
        for encoding in ("utf-16", "utf-16-le", "utf-32"):
            refuse_dtd('<a><b>글 &amp; text</b></a>'.encode(encoding), "x.xml")

    def test_plain_xml_passes(self):
        refuse_dtd('<a><b>&amp; 글</b></a>', "x.xml")
        refuse_dtd(b"<a/>", "x.xml")

    def test_validate_package_reports_dtd(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "a.hwpx"
            build_hwpx({"blocks": [{"type": "paragraph", "text": "글"}]}, path)
            with zipfile.ZipFile(path) as archive:
                entries = {info.filename: archive.read(info) for info in archive.infolist()}
            section = entries["Contents/section0.xml"].decode("utf-8")
            entries["Contents/section0.xml"] = section.replace(
                "?>", '?><!DOCTYPE hs:sec [<!ENTITY e "ABC">]>', 1).replace("글", "&e;", 1).encode("utf-8")
            broken = Path(folder) / "b.hwpx"
            with zipfile.ZipFile(broken, "w") as out:
                for name, data in entries.items():
                    out.writestr(name, data, zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)
            problems = validate_package(broken)
            self.assertTrue(any("DTD" in problem for problem in problems), problems)


class FileErrorMessageTest(unittest.TestCase):
    def test_refused_overwrite_only_asks_for_another_name(self):
        message = file_error_message(FileExistsError("이미 있는 파일이라 덮어쓰지 않음: 결과.hwpx. 다른 이름을 적어 주세요"))
        self.assertIn("다른 이름", message)
        self.assertNotIn("닫거나", message)

    def test_locked_file_names_the_file_and_asks_to_close(self):
        message = file_error_message(PermissionError(13, "denied", "결과.hwpx.abcd.tmp"))
        self.assertIn("결과.hwpx.abcd.tmp", message)
        self.assertIn("닫거나 잠시 뒤 다시 실행", message)

    def test_other_errors_keep_the_reason(self):
        self.assertIn("없는 폴더", file_error_message(FileNotFoundError("없는 폴더")))


if __name__ == "__main__":
    unittest.main()
