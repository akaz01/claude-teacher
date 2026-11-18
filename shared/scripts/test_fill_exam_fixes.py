"""fill_exam 검토 결함 시험: 머리 1단+본문 2단 너비, 그림·대화 keep, 수식 말풍선, 그림 크기·경로 등."""
import json
import re
import struct
import zipfile
from pathlib import Path

import pytest

from fill_exam import _run_fill, fill_exam
from fill_exam_media import borderless_fill, bubble_height, image_size, wrapped_lines
from fill_exam_parse import _column_width, inspect_exam
from make_hwpx_equation import _EQ_TOKEN, _token_width, equation_width
from test_fill_exam_media import FORM, item, png

pytestmark = pytest.mark.skipif(not FORM.exists(), reason="기본 원안지 양식이 없음")
COLUMN_TAG = ('<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="2" sameSz="1" sameGap="850">'
              '<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/></hp:colPr></hp:ctrl>')
ONE_COLUMN = 59528 - 2 * 2834
TWO_COLUMN = (ONE_COLUMN - 850) // 2
SPEAKERS = [{"who": "갑", "text": "가"}, {"who": "을", "text": "나"}]


def head_one_column_form(tmp_path) -> Path:
    """머리는 1단, 문항부터 2단인 양식. 원안지의 첫 단 설정을 1단으로 바꾸고 첫 문항 앞에 2단 설정을 더한다."""
    out = tmp_path / "form.hwpx"
    with zipfile.ZipFile(FORM) as source, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "Contents/section0.xml":
                xml = data.decode("utf-8")
                xml = re.sub(r'colCount="2"( sameSz="1" sameGap=")850', r'colCount="1"\g<1>0', xml, count=1)
                at = xml.rindex("<hp:p ", 0, xml.index("[1~2]"))
                start = ('<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                         f'<hp:run charPrIDRef="0">{COLUMN_TAG}<hp:t/></hp:run></hp:p>')
                data = (xml[:at] + start + xml[at:]).encode("utf-8")
            target.writestr(info, data)
    return out


def package(path):
    with zipfile.ZipFile(path) as z:
        return z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode()


def shape_of(header, number):
    return re.search(rf'<hh:paraPr id="{number}".*?</hh:paraPr>', header, re.S).group(0)


def test_column_width_reads_last_setting_before_body(tmp_path):
    xml = package(head_one_column_form(tmp_path))[0]
    assert _column_width(xml) == TWO_COLUMN
    assert _column_width(xml, xml.index(COLUMN_TAG)) == ONE_COLUMN


def test_dialogue_table_fits_column_in_one_column_head(tmp_path):
    out = tmp_path / "o.hwpx"
    fill_exam(head_one_column_form(tmp_path), {"items": [item(dialogue=SPEAKERS)]}, out)
    xml, _ = package(out)
    at = xml.index('rowCnt="2" colCnt="2"')
    width = int(re.search(r'<hp:sz width="(\d+)"', xml[at:]).group(1))
    assert width <= TWO_COLUMN


def test_picture_dialogue_and_caption_paragraphs_keep_with_next(tmp_path):
    picture = tmp_path / "g.png"
    picture.write_bytes(png(40, 20))
    out = tmp_path / "o.hwpx"
    spec = {"file": str(picture), "caption": "<그림> 설명"}
    fill_exam(FORM, {"items": [item(picture=spec, dialogue=SPEAKERS)]}, out)
    xml, header = package(out)
    table_at = xml.rindex("<hp:p ", 0, xml.index('rowCnt="2" colCnt="2"'))
    paragraphs = [re.search(r'<hp:p [^>]*?paraPrIDRef="(\d+)"[^>]*><hp:run [^>]*><hp:pic ', xml),
                  re.search(r'<hp:p [^>]*?paraPrIDRef="(\d+)"[^>]*><hp:run [^>]*><hp:t>&lt;그림&gt; 설명', xml),
                  re.match(r'<hp:p [^>]*?paraPrIDRef="(\d+)"', xml[table_at:])]
    for found in paragraphs:
        assert found
        shape = shape_of(header, found.group(1))
        assert 'keepWithNext="1"' in shape and 'keepLines="1"' in shape


def test_equation_in_bubble_adds_height_by_width_and_fraction():
    em, spacing = 1000, 160
    long_math = "{{" + "+".join("x^2" for _ in range(14)) + "}}"
    assert wrapped_lines(long_math, 8000, em) > 1
    assert bubble_height(long_math, 8000, em, spacing) > bubble_height("수수", 8000, em, spacing)
    assert bubble_height("값 {{1/2}} 이다", 20000, em, spacing) > bubble_height("값 {{x+1}} 이다", 20000, em, spacing)
    assert wrapped_lines("{{a+b}}", 20000, em) == 1


def test_equation_width_skips_unmatched_outer_brace():
    assert equation_width("{x^{2}}+2x+1}") == equation_width("{x^{2}}+2x+1")
    assert equation_width("{x^{2}}+2x+1}") > 3000


@pytest.mark.parametrize("symbol, expected", [("×", 1120), ("÷", 1120), ("±", 1120), ("≤", 1050), ("≥", 1050),
                                               ("≠", 1050), ("→", 1200), ("∞", 900), ("°", 400)])
def test_special_symbols_are_counted_narrow(symbol, expected):
    assert _EQ_TOKEN.findall(f"a{symbol}b") == ["a", symbol, "b"]
    assert _token_width(symbol) == expected


def test_uppercase_greek_and_inf_widths():
    assert _token_width("PI") == 780 and _token_width("OMEGA") == 780
    assert _token_width("pi") == 620 and _token_width("INF") == 900


def test_tall_picture_is_capped_to_column_height(tmp_path):
    picture = tmp_path / "t.png"
    picture.write_bytes(png(10, 100))
    out = tmp_path / "o.hwpx"
    fill_exam(FORM, {"items": [item(picture={"file": str(picture), "width_mm": 40})]}, out)
    xml, _ = package(out)
    size = re.search(r'<hp:pic .*?<hp:sz width="(\d+)"[^>]*height="(\d+)"', xml, re.S)
    width, height = int(size.group(1)), int(size.group(2))
    assert height <= 0.6 * (84188 - 4251 - 2267) + 2
    assert abs(height - width * 10) <= 12


def test_relative_picture_resolves_beside_spec_file(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    (folder / "g.png").write_bytes(png(40, 20))
    spec = folder / "spec.json"
    spec.write_text(json.dumps({"items": [item(picture="g.png")]}), encoding="utf-8")
    out = tmp_path / "o.hwpx"
    _run_fill(str(FORM), str(spec), str(out), False)
    assert "<hp:pic " in package(out)[0]


def test_inspect_says_pictures_can_be_added():
    text = inspect_exam(FORM)
    assert "새로 넣지 못함" not in text and "dialogue" in text


SIDES = "".join(f'<hh:{s}Border type="NONE" width="0.1 mm" color="#000000"/>'
                for s in ("left", "right", "top", "bottom"))


def header_with(body):
    return f'<hh:borderFills itemCnt="1"><hh:borderFill id="1" threeD="0">{body}</hh:borderFill></hh:borderFills>'


def test_borderless_fill_reuses_plain_fill():
    xml = header_with('<hh:slash type="NONE"/><hh:backSlash type="NONE"/>' + SIDES)
    assert borderless_fill(xml) == ("1", xml)


@pytest.mark.parametrize("extra", [
    '<hh:slash type="CENTER"/><hh:backSlash type="NONE"/>',
    '<hh:slash type="NONE"/><hh:backSlash type="CENTER"/>',
    '<hh:slash type="NONE"/><hh:backSlash type="NONE"/><hc:fillBrush><hc:gradation/></hc:fillBrush>',
    '<hh:slash type="NONE"/><hh:backSlash type="NONE"/><hc:fillBrush><hc:imgBrush/></hc:fillBrush>'])
def test_borderless_fill_skips_decorated_fills(extra):
    number, updated = borderless_fill(header_with(extra + SIDES))
    assert number == "2" and 'itemCnt="2"' in updated


def test_borderless_fill_added_to_header_when_form_has_none(tmp_path):
    out = tmp_path / "o.hwpx"
    fill_exam(FORM, {"items": [item(dialogue=SPEAKERS)]}, out)
    xml, header = package(out)
    at = xml.index('rowCnt="2" colCnt="2"')
    number = re.search(r'borderFillIDRef="(\d+)"', xml[at:]).group(1)
    count = int(re.search(r'<hh:borderFills itemCnt="(\d+)"', header).group(1))
    assert count == len(re.findall(r"<hh:borderFill id=", header))
    assert f'<hh:borderFill id="{number}"' in header


def test_image_size_reads_jpg_gif_bmp():
    gif = b"GIF89a" + struct.pack("<HH", 30, 20) + b"\0" * 10
    bmp = b"BM" + b"\0" * 16 + struct.pack("<ii", 40, -25) + b"\0" * 8
    jpg = (b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"\0\0" + b"\xff\xc0"
           + struct.pack(">HBHH", 11, 8, 50, 70) + b"\0" * 8)
    assert image_size(gif, "x") == (30, 20)
    assert image_size(bmp, "x") == (40, 25)
    assert image_size(jpg, "x") == (70, 50)


def test_new_picture_does_not_clash_with_old_pictures(tmp_path):
    form = tmp_path / "old.hwpx"
    old = '<opf:item id="image1" href="BinData/image1.png" media-type="image/png" isEmbeded="1"/>'
    with zipfile.ZipFile(FORM) as source, zipfile.ZipFile(form, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "Contents/content.hpf":
                data = data.decode("utf-8").replace("</opf:manifest>", old + "</opf:manifest>").encode("utf-8")
            target.writestr(info, data)
        target.writestr("BinData/image1.png", png(5, 5))
    picture = tmp_path / "g.png"
    picture.write_bytes(png(40, 20))
    out = tmp_path / "o.hwpx"
    fill_exam(form, {"items": [item(picture=str(picture))]}, out)
    with zipfile.ZipFile(out) as z:
        names = [i.filename for i in z.infolist()]
        manifest = z.read("Contents/content.hpf").decode("utf-8")
        xml = z.read("Contents/section0.xml").decode("utf-8")
    ids = re.findall(r'<opf:item id="(image\d+)"', manifest)
    assert len(names) == len(set(names)) and len(ids) == len(set(ids))
    assert set(re.findall(r'binaryItemIDRef="([^"]+)"', xml)) <= set(ids)
