"""pptx_safety.py 시험: 올린 pptx와 그림 경로를 열기 전에 거르고, 만든 pptx의 작성자를 teacher-kit으로 맞추는지 본다."""
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image as PILImage
from pptx import Presentation

import fill_template
import make_deck
import make_pptx
import pptx_safety
from pptx_safety import check_image_size, check_inside_folder, check_pptx, stamp_properties
from test_fill_template import make_template

DTD = '<!DOCTYPE a [<!ENTITY e "ABC">]>'


def rewrite(source: Path, target: Path, changes: dict[str, bytes], extra: tuple[tuple[str, bytes], ...] = ()) -> Path:
    """pptx의 항목을 바꾸고(extra는 덧붙여) 새 zip으로 쓴다."""
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as new:
        for info in old.infolist():
            new.writestr(info.filename, changes.get(info.filename, old.read(info.filename)))
        for name, data in extra:
            new.writestr(name, data)
    return target


@pytest.fixture
def template(tmp_path):
    return make_template(tmp_path)


def test_clean_pptx_and_missing_file_pass(template, tmp_path):
    check_pptx(template)
    check_pptx(tmp_path / "없음.pptx")      # 없는 파일은 여는 쪽 오류에 맡긴다


def test_not_a_zip_is_a_korean_error(tmp_path):
    path = tmp_path / "가짜.pptx"
    path.write_bytes(b"\xd0\xcf\x11\xe0" + b"\0" * 100)        # 암호가 걸린 옛 형식 같은 파일
    with pytest.raises(ValueError, match="양식을 열 수 없음.*pptx 파일이 아니거나 손상됨"):
        check_pptx(path)
    with pytest.raises(ValueError, match="템플릿을 열 수 없음"):
        check_pptx(path, "템플릿")


def test_truncated_pptx_is_a_korean_error(template, tmp_path):
    path = tmp_path / "잘림.pptx"
    path.write_bytes(template.read_bytes()[:-200])
    with pytest.raises(ValueError, match="양식을 열 수 없음"):
        check_pptx(path)


def test_unsafe_names_are_refused(template, tmp_path):
    for name in ("../밖.xml", "/절대.xml", "ppt/../밖.xml"):
        bad = rewrite(template, tmp_path / "위험.pptx", {}, ((name, b"x"),))
        with pytest.raises(ValueError, match="안전하지 않은 경로"):
            check_pptx(bad)


def test_duplicate_entries_are_refused(template, tmp_path):
    with pytest.warns(UserWarning):
        bad = rewrite(template, tmp_path / "겹침.pptx", {}, (("[Content_Types].xml", b"<Types/>"),))
    with pytest.raises(ValueError, match="이름이 같은 항목"):
        check_pptx(bad)


def test_encrypted_flag_is_refused(template, tmp_path):
    data = bytearray(template.read_bytes())
    position = data.find(b"PK\x01\x02")
    data[position + 8] |= 1                                     # 중앙 디렉터리 첫 항목에 암호 표시
    path = tmp_path / "암호.pptx"
    path.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="암호"):
        check_pptx(path)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-le", "utf-16-be"])
def test_dtd_in_any_xml_entry_is_refused(template, tmp_path, encoding):
    xml = f'<?xml version="1.0"?>{DTD}<a>&e;</a>'.encode(encoding)
    bad = rewrite(template, tmp_path / "dtd.pptx", {"docProps/app.xml": xml})
    with pytest.raises(ValueError, match="DTD"):
        check_pptx(bad)


def test_real_unpacked_size_is_limited(template, monkeypatch):
    monkeypatch.setattr(pptx_safety, "MAX_ENTRY_BYTES", 1000)
    with pytest.raises(ValueError, match="너무 큼"):
        check_pptx(template)
    monkeypatch.setattr(pptx_safety, "MAX_ENTRY_BYTES", 64 * 1024 * 1024)
    monkeypatch.setattr(pptx_safety, "MAX_TOTAL_BYTES", 1000)
    with pytest.raises(ValueError, match="너무 큼"):
        check_pptx(template)


def test_fill_template_refuses_a_bad_template_before_opening(template, tmp_path, capsys):
    bad = rewrite(template, tmp_path / "bad.pptx", {"docProps/app.xml": f"{DTD}<a/>".encode()})
    spec = tmp_path / "입력.json"
    spec.write_text(json.dumps({"template": "bad.pptx", "slides": [{"from": 1}]}), encoding="utf-8")
    assert fill_template.main([str(spec), str(tmp_path / "결과.pptx")]) == 1
    assert "DTD" in capsys.readouterr().out
    assert fill_template.main(["--inspect", str(bad)]) == 1
    assert "양식을 열 수 없음" in capsys.readouterr().out


def test_make_pptx_refuses_a_bad_template(template, tmp_path, capsys):
    bad = rewrite(template, tmp_path / "bad.pptx", {}, (("../밖.xml", b"x"),))
    spec = tmp_path / "입력.json"
    spec.write_text(json.dumps({"theme": "basic", "template": str(bad),
                                "slides": [{"type": "section", "title": "가"}]}), encoding="utf-8")
    assert make_pptx.main([str(spec), str(tmp_path / "결과.pptx")]) == 1
    assert "안전하지 않은 경로" in capsys.readouterr().out


def test_relative_path_cannot_leave_the_base_folder(tmp_path):
    base = tmp_path / "작업"
    base.mkdir()
    for raw in ("../x.png", "사진/../../x.png"):
        with pytest.raises(ValueError, match="폴더 밖"):
            check_inside_folder(raw, base)
    check_inside_folder("사진/x.png", base)
    check_inside_folder("사진/../x.png", base)
    check_inside_folder(str(tmp_path / "x.png"), base)          # 절대 경로(업로드 폴더)는 막지 않는다
    check_inside_folder("/mnt/user-data/uploads/x.png", base)
    check_inside_folder("/mnt/../x.png", base)                  # 절대 경로는 ..가 있어도 그대로


def test_image_size_is_limited(tmp_path, monkeypatch):
    image = tmp_path / "x.png"
    PILImage.new("RGB", (50, 50)).save(image)
    check_image_size(image)
    check_image_size(tmp_path / "없음.png")
    monkeypatch.setattr(pptx_safety, "MAX_IMAGE_BYTES", 10)
    with pytest.raises(ValueError, match="그림 파일이 너무 큼"):
        check_image_size(image)


def folder_with_image(tmp_path):
    work = tmp_path / "작업"
    work.mkdir()
    PILImage.new("RGB", (40, 40)).save(tmp_path / "밖.png")
    PILImage.new("RGB", (40, 40)).save(work / "안.png")
    return work


def test_fill_template_refuses_images_outside_the_folder(tmp_path, capsys):
    work = folder_with_image(tmp_path)
    make_template(work)
    spec = work / "입력.json"
    spec.write_text(json.dumps({"template": "양식.pptx", "slides": [
        {"from": 2, "images": {"사진": "../밖.png"}}]}), encoding="utf-8")
    assert fill_template.main([str(spec), str(work / "결과.pptx")]) == 1
    assert "폴더 밖" in capsys.readouterr().out
    spec.write_text(json.dumps({"template": "양식.pptx", "slides": [
        {"from": 2, "add": [{"shape": "image", "path": "../밖.png", "left": 1000, "top": 1000, "width": 100000, "height": 100000}]}]}),
        encoding="utf-8")
    assert fill_template.main([str(spec), str(work / "결과.pptx")]) == 1
    assert "폴더 밖" in capsys.readouterr().out


def test_fill_template_accepts_an_inner_image(tmp_path):
    work = folder_with_image(tmp_path)
    make_template(work)
    spec = work / "입력.json"
    spec.write_text(json.dumps({"template": "양식.pptx", "slides": [{"from": 2, "images": {"사진": "안.png"}}]}),
                    encoding="utf-8")
    assert fill_template.main([str(spec), str(work / "결과.pptx")]) == 0


def test_make_pptx_and_make_deck_refuse_images_outside_the_folder(tmp_path, capsys):
    work = folder_with_image(tmp_path)
    spec = work / "입력.json"
    spec.write_text(json.dumps({"theme": "basic", "slides": [
        {"type": "figure", "title": "그림", "image": "../밖.png", "caption": "c"}]}), encoding="utf-8")
    assert make_pptx.main([str(spec), str(work / "a.pptx")]) == 1
    assert "폴더 밖" in capsys.readouterr().out
    deck = {"subject": "과학", "unit": "단원", "meta": "중2",
            "slides": [{"type": "figure", "title": "그림", "image": "../밖.png", "caption": "c"}]}
    spec.write_text(json.dumps(deck), encoding="utf-8")
    assert make_deck.main([str(spec), str(work / "b.pptx")]) == 1
    assert "폴더 밖" in capsys.readouterr().out


def test_oversized_image_is_refused_by_the_builders(tmp_path, monkeypatch, capsys):
    work = folder_with_image(tmp_path)
    monkeypatch.setattr(pptx_safety, "MAX_IMAGE_BYTES", 10)
    spec = work / "입력.json"
    spec.write_text(json.dumps({"theme": "basic", "slides": [
        {"type": "figure", "title": "그림", "image": "안.png", "caption": "c"}]}), encoding="utf-8")
    assert make_pptx.main([str(spec), str(work / "a.pptx")]) == 1
    assert "너무 큼" in capsys.readouterr().out
    make_template(work)
    spec.write_text(json.dumps({"template": "양식.pptx", "slides": [{"from": 2, "images": {"사진": "안.png"}}]}),
                    encoding="utf-8")
    assert fill_template.main([str(spec), str(work / "b.pptx")]) == 1
    assert "너무 큼" in capsys.readouterr().out


def author_of(path: Path) -> tuple[str, str]:
    props = Presentation(str(path)).core_properties
    return props.author, props.last_modified_by


def test_stamp_properties_sets_both_names():
    prs = Presentation()
    prs.core_properties.author = "김교사"
    stamp_properties(prs)
    assert (prs.core_properties.author, prs.core_properties.last_modified_by) == ("teacher-kit", "teacher-kit")


def test_every_builder_writes_teacher_kit_as_author(tmp_path):
    template = make_template(tmp_path)
    marked = Presentation(str(template))
    marked.core_properties.author = marked.core_properties.last_modified_by = "김교사"
    marked.save(str(template))
    filled = tmp_path / "채움.pptx"
    fill_template.build({"template": str(template), "slides": [{"from": 1}]}, filled)
    assert author_of(filled) == ("teacher-kit", "teacher-kit")
    made = tmp_path / "만듦.pptx"
    make_pptx.build_pptx({"theme": "basic", "template": str(template),
                          "slides": [{"type": "section", "title": "가"}]}, made)
    assert author_of(made) == ("teacher-kit", "teacher-kit")
    plain = tmp_path / "기본.pptx"
    make_pptx.build_pptx({"theme": "basic", "slides": [{"type": "section", "title": "가"}]}, plain)
    assert author_of(plain) == ("teacher-kit", "teacher-kit")
    deck = tmp_path / "덱.pptx"
    make_deck.build_deck({"subject": "과학", "unit": "단원", "meta": "중2",
                          "slides": [{"type": "cover", "title": "제목"}]}, deck)
    assert author_of(deck) == ("teacher-kit", "teacher-kit")
