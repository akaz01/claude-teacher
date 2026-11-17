"""수행평가 세부 계획(기본 양식) 생성기 시험."""
import re
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "scripts"))
from make_hwpx import validate_package  # noqa: E402

from make_rubric_form import DEFAULT_NOTES, FormError, build, main  # noqa: E402

TASK = {
    "title": "1. 생활 속 명제 발표하기",
    "standards": ["[10공수2-02-04] 명제와 조건의 뜻을 안다.", "~", "[10공수2-02-06] 역과 대우를 이해한다."],
    "methods": ["구술·발표", "기타(관찰)"],
    "areas": [{"name": "명제 발표", "elements": [
        {"name": "명제 판별", "levels": [["세 개를 구별함.", 10], ["두 개를 구별함.", 8], ["한 개를 구별함.", 6], ["구별하지 못함.", 4]]},
        {"name": "역과 대우", "levels": [["역과 대우를 씀.", 10], ["하나만 씀.", 7], ["쓰지 못함.", 4]]},
        {"name": "발표", "levels": [["근거를 들어 답함.", 10], ["근거 없이 답함.", 7]]}]}],
    "base": [["미참여(기본점수)", "○ [확인 필요]"], ["장기 미인정 결시(기본점수의 -1)", "○ [확인 필요]"]],
}


def section(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        return package.read("Contents/section0.xml").decode("utf-8")


def texts(xml: str) -> str:
    return "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", xml.replace("<hp:fwSpace/>", " ")))


def make(tmp_path: Path, spec: dict) -> str:
    out = tmp_path / "out.hwpx"
    build(spec, out)
    assert not validate_package(out)
    return section(out)


def test_rows_follow_elements_and_levels(tmp_path):
    xml = make(tmp_path, TASK)
    table = re.search(r"<hp:tbl .*?</hp:tbl>", xml, re.S).group(0)
    # 성취기준 + 평가 방법 + 머리행 + 수준 9행 + 기본점수 2행 + 유의사항 2행
    assert re.search(r'rowCnt="(\d+)"', table).group(1) == str(3 + 9 + 2 + 2)
    assert table.count("<hp:tr>") == 16
    rows = [int(r) for r in re.findall(r'rowAddr="(\d+)"', table)]
    assert sorted(set(rows)) == list(range(16))
    spans = dict(re.findall(r'<hp:t>([^<]*)</hp:t>.*?<hp:cellSpan colSpan="\d+" rowSpan="(\d+)"', table, re.S))
    assert spans.get("명제 판별") == "4" and spans.get("역과 대우") == "3" and spans.get("발표") == "2"


def test_texts_points_and_scale(tmp_path):
    words = texts(make(tmp_path, TASK))
    assert "1. 생활 속 명제 발표하기" in words
    assert "(30점)" in words and "(10점)" in words
    assert "■구술·발표" in words and "■기타(관찰)" in words and "□서술·논술" in words
    assert "".join(str(n) for n in range(30, 14, -1)) in words           # 평가 척도 30 → 15
    assert DEFAULT_NOTES[0] in words
    assert "근현대" not in words and "전시실" not in words                # 양식의 옛 글이 남지 않는다


def test_area_and_scale_span_all_level_rows(tmp_path):
    table = re.search(r"<hp:tbl .*?</hp:tbl>", make(tmp_path, TASK), re.S).group(0)
    area = re.search(r"<hp:t>명제 발표</hp:t>.*?rowSpan=\"(\d+)\"", table, re.S).group(1)
    assert area == "9"


def test_feedback_rows_come_only_when_given(tmp_path):
    # 3차 평가: 중·고 채점기준표에도 가장 낮은 단계 학생의 피드백 줄을 둔다 (지도안 평가 계획표의 "피드백(하)")
    plain = make(tmp_path, TASK)
    assert "피드백 계획" not in texts(plain)                     # 주지 않으면 이전과 같은 표
    element = {**TASK["areas"][0]["elements"][0], "feedback": "명제와 조건의 예를 한 쌍씩 견주어 다시 고르게 함"}
    task = {**TASK, "areas": [{"name": "명제 발표", "elements": [element, *TASK["areas"][0]["elements"][1:]]}]}
    out = tmp_path / "feedback.hwpx"
    build(task, out)
    assert not validate_package(out)
    xml = section(out)
    table = re.search(r"<hp:tbl .*?</hp:tbl>", xml, re.S).group(0)
    assert re.search(r'rowCnt="(\d+)"', table).group(1) == str(3 + 9 + 2 + 2 + 2)
    assert sorted({int(r) for r in re.findall(r'rowAddr="(\d+)"', table)}) == list(range(18))
    words = texts(xml)
    assert "피드백 계획" in words and "명제 판별: 명제와 조건의 예를 한 쌍씩 견주어 다시 고르게 함" in words
    assert words.index("피드백 계획") < words.index("학생 유의사항")
    assert "역과 대우:" not in words                              # 피드백이 없는 요소는 줄을 만들지 않는다


@pytest.mark.parametrize("value", ["", "  ", 3])
def test_empty_feedback_is_refused(tmp_path, value):
    element = {**TASK["areas"][0]["elements"][0], "feedback": value}
    with pytest.raises(FormError, match="피드백"):
        build({**TASK, "areas": [{"name": "명제 발표", "elements": [element]}]}, tmp_path / "out.hwpx")


def test_several_tasks_and_no_base_rows(tmp_path):
    second = {**TASK, "title": "2. 둘째 과제", "base": [], "notes": []}
    xml = make(tmp_path, {"tasks": [TASK, second]})
    assert xml.count("<hp:tbl ") == 2 and xml.count("<hp:secPr") == 1
    assert "2. 둘째 과제" in texts(xml)


@pytest.mark.parametrize("bad, message", [
    ({"methods": ["관찰"]}, "평가 방법"),
    ({"areas": []}, "areas"),
    ({"areas": [{"name": "가", "elements": [{"name": "나", "levels": [["글", -1]]}]}]}, "점수"),
    ({"title": ""}, "제목"),
])
def test_bad_input_is_refused_in_korean(tmp_path, bad, message):
    with pytest.raises(FormError, match=message):
        build({**TASK, **bad}, tmp_path / "out.hwpx")


def test_does_not_overwrite(tmp_path, capsys):
    spec = tmp_path / "in.json"
    spec.write_text(__import__("json").dumps(TASK, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out.hwpx"
    assert main([str(spec), str(out)]) == 0
    assert main([str(spec), str(out)]) == 1
    assert "덮어쓰지 않음" in capsys.readouterr().out


def test_control_characters_are_removed_not_written(tmp_path):
    task = {**TASK, "title": "1. 제\u0001목", "standards": ["[10공수2-02-04] 명제\u000b와 조건"],
            "areas": [{"name": "명제\u0002 발표", "elements": [{"name": "판\u000c별", "levels": [["구\u0001별함.", 10]]}]}],
            "notes": ["유의\u0001사항"]}
    xml = make(tmp_path, task)                     # make는 validate_package 통과까지 본다
    assert not re.search("[\x00-\x08\x0b\x0c\x0e-\x1f]", xml)
    words = texts(xml)
    for word in ("1. 제목", "명제와 조건", "명제 발표", "판별", "구별함.", "유의사항"):
        assert word in words


def test_bom_json_is_read(tmp_path):
    spec = tmp_path / "in.json"
    spec.write_text(__import__("json").dumps(TASK, ensure_ascii=False), encoding="utf-8-sig")
    out = tmp_path / "out.hwpx"
    assert main([str(spec), str(out)]) == 0
    assert not validate_package(out)


def test_failed_check_leaves_no_file(tmp_path, monkeypatch):
    import make_rubric_form
    monkeypatch.setattr(make_rubric_form, "validate_package", lambda path: ["가짜 문제"])
    with pytest.raises(FormError, match="가짜 문제"):
        build(TASK, tmp_path / "out.hwpx")
    assert list(tmp_path.iterdir()) == []
