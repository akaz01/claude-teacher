"""make_hwpx_zip.py 시험: zip 양식을 머리말 크기를 믿지 않고 안전하게 읽는지 본다."""

import struct
import tempfile
import tracemalloc
import unittest
import zipfile
from pathlib import Path

from make_hwpx_zip import PackageError, read_entry, read_package, unsafe_name

BOMB_BYTES = 40 * 1024 * 1024
PEAK_LIMIT = 16 * 1024 * 1024


def lie_about_size(path: Path, name: str, size: int) -> None:
    """중앙 디렉터리에 적힌 name 항목의 풀린 크기(file_size)를 size로 속인다."""
    data = bytearray(path.read_bytes())
    position = data.find(b"PK\x01\x02")
    while position != -1:
        name_length = struct.unpack_from("<H", data, position + 28)[0]
        if data[position + 46:position + 46 + name_length] == name.encode():
            struct.pack_into("<I", data, position + 24, size)
        position = data.find(b"PK\x01\x02", position + 4)
    path.write_bytes(bytes(data))


class ZipCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = Path(holder.name)

    def package(self, *entries: tuple[str, bytes]) -> Path:
        path = self.folder / "양식.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries:
                archive.writestr(name, data)
        return path

    def read(self, path: Path, max_entry: int = 64 * 1024 * 1024, max_total: int = 512 * 1024 * 1024):
        return read_package(path, max_entry, max_total, "한글")


class ReadPackageTest(ZipCase):
    def test_reads_every_entry(self):
        infos, entries = self.read(self.package(("mimetype", b"a"), ("Contents/x.xml", b"<x/>")))
        self.assertEqual([info.filename for info in infos], ["mimetype", "Contents/x.xml"])
        self.assertEqual(entries, {"mimetype": b"a", "Contents/x.xml": b"<x/>"})

    def test_lying_size_in_header_does_not_blow_up_memory(self):
        path = self.package(("mimetype", b"a"), ("BinData/x.bin", b"\0" * BOMB_BYTES))
        lie_about_size(path, "BinData/x.bin", 10)
        tracemalloc.start()
        try:
            with self.assertRaises(PackageError):
                self.read(path)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, PEAK_LIMIT)

    def test_entry_over_the_limit_is_refused(self):
        path = self.package(("mimetype", b"a"), ("BinData/x.bin", b"\0" * 2000))
        with self.assertRaisesRegex(PackageError, "너무 큼"):
            self.read(path, max_entry=1000)

    def test_total_over_the_limit_is_refused(self):
        path = self.package(("a.xml", b"\0" * 600), ("b.xml", b"\0" * 600))
        with self.assertRaisesRegex(PackageError, "너무 큼"):
            self.read(path, max_entry=1000, max_total=1000)

    def test_entries_with_the_same_name_are_refused(self):
        path = self.folder / "겹침.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Contents/section0.xml", b"<a/>")
            with self.assertWarns(UserWarning):
                archive.writestr("Contents/section0.xml", b"<b/>")
        with self.assertRaisesRegex(PackageError, "이름이 같은"):
            self.read(path)

    def test_unsafe_paths_are_refused(self):
        for name in ("../밖.txt", "/abs.txt", "a/../b.txt", "C:/x.txt"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(PackageError, "안전하지 않은 경로"):
                    self.read(self.package(("mimetype", b"a"), (name, b"x")))

    def test_encrypted_entry_names_the_app(self):
        path = self.package(("mimetype", b"a"))
        data = bytearray(path.read_bytes())
        data[data.index(b"PK\x01\x02") + 8] |= 0x01
        path.write_bytes(bytes(data))
        with self.assertRaisesRegex(PackageError, "한글에서 암호를 풀고"):
            self.read(path)

    def test_corrupted_data_is_reported_in_korean(self):
        path = self.package(("mimetype", b"a"), ("x.xml", b"<x>" + b"abc" * 1000 + b"</x>"))
        data = bytearray(path.read_bytes())
        start = data.index(b"x.xml") + len(b"x.xml")
        data[start + 10:start + 30] = b"\xff" * 20
        path.write_bytes(bytes(data))
        with self.assertRaisesRegex(PackageError, "손상"):
            self.read(path)


class UnsafeNameTest(unittest.TestCase):
    def test_backslash_and_empty_names_are_unsafe(self):
        for name in ("a\\b.txt", "", "D:x", ".."):
            with self.subTest(name=name):
                self.assertTrue(unsafe_name(name))
        for name in ("Contents/section0.xml", "BinData/image1.png", "mimetype"):
            with self.subTest(name=name):
                self.assertFalse(unsafe_name(name))


class ReadEntryTest(ZipCase):
    def test_reads_up_to_the_limit(self):
        path = self.package(("x.bin", b"\1" * 1000))
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(read_entry(archive, archive.getinfo("x.bin"), 1000), b"\1" * 1000)
            with self.assertRaisesRegex(PackageError, "너무 큼"):
                read_entry(archive, archive.getinfo("x.bin"), 999)


if __name__ == "__main__":
    unittest.main()
