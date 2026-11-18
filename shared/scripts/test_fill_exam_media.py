"""fill_exam의 대화 장면(dialogue)과 그림(picture) 시험. 기본 원안지 양식을 쓴다."""
import re
import struct
import zipfile
import zlib
from pathlib import Path

import pytest

from fill_exam import fill_exam
from fill_exam_media import FIGURES, figure_path, image_size, next_item_ids, speakers, wrapped_lines
from fill_hwpx import FillError

FORM = Path(__file__).resolve().parents[2] / "skills" / "assessment-items" / "assets" / "exam_form.hwpx"
pytestmark = pytest.mark.skipif(not FORM.exists(), reason="기본 원안지 양식이 없음")
CHOICES = ["갑", "을", "갑, 병", "을, 병", "갑, 을, 병"]
SHORT = [{"who": "갑", "text": "전국에 시행했어요."}, {"who": "을", "text": "양반만 대상이었어요."},
         {"who": "병", "figure": "student_f2", "text": "16세 이상 남자가 지녔어요."}]
LONG = [{"who": "교사", "figure": "teacher_f",
         "text": "이 왕은 6조의 일을 왕에게 바로 아뢰게 하고, 호패법을 처음 실시했어요. 이 왕이 펼친 다른 정책을 말해 볼까요?"},
        {"who": "갑", "text": "(가)"}]


def item(**extra) -> dict:
    return {"type": "combo_table", "layout": "5x1", "stem": "다음 대화에서 옳게 말한 학생만을 고른 것은?",
            "points": 3, "choices": CHOICES, "answer": 3, **extra}


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    row = b"\x00" + b"\xff\xff\xff" * width
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b"")


def package(path: Path) -> tuple[str, str, str, dict[str, zipfile.ZipInfo]]:
    with zipfile.ZipFile(path) as archive:
        infos = {info.filename: info for info in archive.infolist()}
        return (archive.read("Contents/section0.xml").decode("utf-8"),
                archive.read("Contents/header.xml").decode("utf-8"),
                archive.read("Contents/content.hpf").decode("utf-8"), infos)


def test_every_figure_file_is_shipped_and_readable():
    for name in FIGURES:
        path = figure_path(name, "시험")
        assert path.exists(), name
        assert image_size(path.read_bytes(), "시험") == (300, 330)


def test_short_dialogue_puts_bubbles_above_the_figures(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(dialogue=SHORT)]}, out)
    xml, header, manifest, infos = package(out)
    assert 'rowCnt="2" colCnt="3"' in xml                       # 가로: 말풍선 줄 + 인물 줄
    assert xml.count("<hp:pic ") == 3                                      # 인물 셋
    assert len(re.findall(r'<hp:rect [^>]*ratio="0"', xml)) == 3          # 네모 말풍선 셋 (둥근 모서리 없음)
    for text in ("전국에 시행했어요.", "16세 이상 남자가 지녔어요."):
        assert text in xml
    used = set(re.findall(r'binaryItemIDRef="([^"]+)"', xml))
    listed = dict(re.findall(r'<opf:item id="(image\d+)" href="(BinData/[^"]+)"', manifest))
    assert used == set(listed)                                   # 쓴 그림이 모두 목록에 있고 남는 것이 없다
    for entry in listed.values():
        assert infos[entry].compress_type == zipfile.ZIP_STORED
    bubble_ref = re.search(r'<hp:rect\b.*?<hp:p [^>]*paraPrIDRef="(\d+)"', xml, re.S).group(1)
    shape = re.search(rf'<hh:paraPr id="{bubble_ref}".*?</hh:paraPr>', header, re.S).group(0)
    assert 'horizontal="LEFT"' in shape and 'keepWithNext="0"' in shape


def test_long_dialogue_switches_to_figures_beside_bubbles(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(dialogue=LONG)]}, out)
    assert 'rowCnt="2" colCnt="2"' in package(out)[0]           # 세로: 사람마다 한 줄, 인물 칸 + 말풍선 칸


def test_layout_can_be_forced(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(dialogue=SHORT, dialogue_layout="column")]}, out)
    assert 'rowCnt="3" colCnt="2"' in package(out)[0]


def test_same_figure_is_stored_once(tmp_path):
    people = [{"who": "갑", "figure": "student_m1", "text": "가"}, {"who": "을", "figure": "student_m1", "text": "나"}]
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item(dialogue=people), item(dialogue=people)]}, out)
    xml, _, manifest, _ = package(out)
    assert xml.count("<hp:pic ") == 4
    assert manifest.count("BinData/") == 1


def test_picture_is_scaled_and_captioned(tmp_path):
    picture = tmp_path / "graph.png"
    picture.write_bytes(png(40, 20))
    out = tmp_path / "out.hwpx"
    spec = {"file": str(picture), "width_mm": 50, "caption": "<그림> 인구 변화"}
    fill_exam(FORM, {"items": [item(picture=spec)]}, out)
    xml, _, manifest, _ = package(out)
    size = re.search(r'<hp:pic .*?<hp:sz width="(\d+)"[^>]*height="(\d+)"', xml, re.S)
    assert abs(int(size.group(1)) - 50 * 7200 / 25.4) < 2 and abs(int(size.group(2)) * 2 - int(size.group(1))) < 3
    assert "&lt;그림&gt; 인구 변화" in xml and 'media-type="image/png"' in manifest


def test_student_copy_keeps_pictures(tmp_path):
    out = tmp_path / "student.hwpx"
    fill_exam(FORM, {"items": [item(dialogue=SHORT)]}, out, student=True)
    xml, _, manifest, _ = package(out)
    assert xml.count("<hp:pic ") == 3 and "hp:markpen" not in xml and manifest.count("BinData/") == 3


@pytest.mark.parametrize("extra, message", [
    ({"dialogue": []}, "1~4명"),
    ({"dialogue": [{"who": "갑"}]}, "말풍선 글"),
    ({"dialogue": [{"who": "갑", "text": "가", "mood": "기쁨"}]}, "who"),
    ({"dialogue": SHORT, "dialogue_layout": "grid"}, "dialogue_layout"),
    ({"dialogue_layout": "row"}, "dialogue_layout"),
    ({"picture": {"file": "a.png", "width_mm": 500}}, "width_mm"),
    ({"picture": 3}, "picture"),
])
def test_bad_media_specs_are_refused(tmp_path, extra, message):
    with pytest.raises(FillError, match=message):
        fill_exam(FORM, {"items": [item(**extra)]}, tmp_path / "out.hwpx")
    assert not (tmp_path / "out.hwpx").exists()


def test_missing_or_unknown_pictures_are_refused(tmp_path):
    with pytest.raises(FillError, match="그림 파일을 읽을 수 없음"):
        fill_exam(FORM, {"items": [item(picture=str(tmp_path / "none.png"))]}, tmp_path / "a.hwpx")
    with pytest.raises(FillError, match="figure는"):
        fill_exam(FORM, {"items": [item(dialogue=[{"who": "갑", "figure": "dragon", "text": "가"}])]},
                  tmp_path / "b.hwpx")
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not a picture")
    with pytest.raises(FillError, match="PNG, JPG"):
        fill_exam(FORM, {"items": [item(picture=str(fake))]}, tmp_path / "c.hwpx")


def test_written_items_cannot_take_pictures(tmp_path):
    with pytest.raises(FillError, match="서답형"):
        fill_exam(FORM, {"items": [{"type": "written", "stem": "가", "points": 5, "dialogue": SHORT}]},
                  tmp_path / "out.hwpx")


def test_line_count_follows_word_wrapping():
    em = 1000
    assert wrapped_lines("가나다", 10 * em, em) == 1
    assert wrapped_lines("가나다라마 바사아자차", 6 * em, em) == 2          # 낱말째 다음 줄로 넘어간다
    assert wrapped_lines("가\n나", 10 * em, em) == 2
    assert wrapped_lines("가" * 25, 10 * em, em) == 3                       # 칸보다 긴 낱말은 끊긴다


def test_speakers_get_distinct_default_figures():
    chosen = [p["figure"] for p in speakers([{"who": "갑"}, {"who": "을", "figure": "student_f1"}, {"who": "병"}])]
    assert chosen[1] == "student_f1" and len(set(chosen)) == 3


def test_item_ids_avoid_existing_names():
    manifest = '<opf:item id="image1" href="BinData/image1.png"/><opf:item id="pic" href="BinData/image2.jpg"/>'
    assert next_item_ids(manifest, 2) == ["image3", "image4"]
