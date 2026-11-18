"""fill_exam_text: 표지 내어쓰기, 출처·각주 오른쪽 정렬, 줄글 첫 줄 들여쓰기, 선지 배치 자동 고르기. 기본 원안지 양식을 쓴다."""
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from fill_exam import fill_exam
from fill_exam_text import auto_layout, classify, marker_width

FORM = Path(__file__).resolve().parents[2] / "skills" / "assessment-items" / "assets" / "exam_form.hwpx"
pytestmark = pytest.mark.skipif(not FORM.exists(), reason="기본 원안지 양식이 없음")
PROSE = "조선은 건국 초기에 중앙 집권 체제를 정비하고 유교 이념을 통치 원리로 삼았다."
FIVE = ["가", "나", "다", "라", "마"]


def build(tmp_path, items):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": items}, out)
    with zipfile.ZipFile(out) as package:
        return package.read("Contents/section0.xml").decode(), package.read("Contents/header.xml").decode()


def shape_of(xml, header, text):
    """text가 든 문단의 (정렬, 첫 줄 들여쓰기, 왼쪽 여백). 새 방식 값. 표지 뒤 묶음 빈칸은 보통 빈칸으로 읽는다."""
    xml = xml.replace("<hp:nbSpace/>", " ")
    paragraph = re.search(rf'<hp:p [^>]*paraPrIDRef="(\d+)"[^>]*>(?:(?!</hp:p>).)*?{re.escape(escape(text))}', xml, re.S)
    shape = re.search(rf'<hh:paraPr id="{paragraph.group(1)}".*?</hh:paraPr>', header, re.S).group(0)
    case = shape.split("<hp:default>")[0]
    return (re.search(r'horizontal="(\w+)"', shape).group(1), int(re.search(r'intent value="(-?\d+)"', case).group(1)),
            int(re.search(r'left value="(-?\d+)"', case).group(1)))


def item(box, **extra):
    return {"type": "short_table", "layout": "1x5", "stem": "다음 자료에 대한 설명으로 옳은 것은?", "points": 3,
            "box": box, "choices": FIVE, "answer": 1, **extra}


@pytest.mark.parametrize("text,width", [("○ 항목", 1100), ("ㄱ. 항목", 1600), ("갑: 말", 1900), ("(가) 글", 2100),
                                        ("교사: 말", 2900), ("학생 1: 말", 3750), ("(A) 글", 1750)])
def test_marker_widths_follow_the_measured_values(text, width):
    assert marker_width(text) == width


@pytest.mark.parametrize("text", ["(가)는 옳다고 본다", "시각이 3시였다", "갑은 말했다: 나는 안다", "*낱말"])
def test_texts_without_a_marker_and_space_are_not_markers(text):
    assert marker_width(text) is None


def test_marker_paragraphs_hang_by_their_marker_width(tmp_path):
    texts = ["교사: " + PROSE, "갑: " + PROSE, "을: " + PROSE, "(가) " + PROSE, "○ " + PROSE]
    xml, header = build(tmp_path, [item(texts)])
    got = [shape_of(xml, header, text[:6]) for text in texts]
    # 한글 내어쓰기는 왼쪽 여백 0 + 음수 intent (첫 줄은 제자리, 둘째 줄부터 표지 뒤 글 시작). 한글 화면에서 확인
    assert [(g[1], g[2]) for g in got] == [(-2900, 0), (-1900, 0), (-1900, 0), (-2100, 0), (-1100, 0)]
    assert all(g[0] == "JUSTIFY" for g in got)


def test_source_and_footnote_are_right_aligned_and_plain_text_is_not(tmp_path):
    texts = [PROSE, "*낱말: 뜻풀이", "- 이광수, 「무정」 -"]
    xml, header = build(tmp_path, [item(texts)])
    assert shape_of(xml, header, "*낱말")[0] == "RIGHT"
    assert shape_of(xml, header, "이광수")[0] == "RIGHT"
    assert shape_of(xml, header, PROSE[:10])[0] == "JUSTIFY"


def test_source_dash_is_a_source_on_the_last_paragraph():
    assert classify("- 지은이, 「제목」 -", True)[0] == "right"
    assert classify("-『제목』", True)[0] == "right"
    assert classify("― 지은이, 제목 ―", True)[0] == "right"


def test_part_source_under_each_label_is_right_aligned_anywhere():
    """(가)·(나) 자료마다 바로 아래 출처를 단다(교사 지시). 상자 중간 줄이어도 수능 꼴이면 오른쪽 정렬."""
    assert classify("- 『신한민보』, 1910. 7. 6. -", False)[0] == "right"
    assert classify("- 「봉화가 켜질 때에」, 『개벽』, 1925 -", False)[0] == "right"
    assert classify("- 지은이, 제목 -", False)[0] != "right"        # 책·글 이름 괄호가 없으면 중간 줄은 출처로 보지 않는다
    assert classify("- 가나다라 -", False)[0] != "right"
    assert classify("- 「가」 문서를 읽고 학생들이 토론하였다 -", False)[0] != "right"   # 문장은 출처가 아니다
    assert classify("-｢제목｣", True)[0] == "right"                                  # 반각 낫표도 출처


def test_prose_first_line_is_indented_one_em_and_headings_are_not(tmp_path):
    xml, header = build(tmp_path, [item(["<자료 1>", PROSE, "x = 2y + 1", "시\n행"])])
    assert shape_of(xml, header, PROSE[:10])[1:] == (1000, 0)
    assert shape_of(xml, header, "<자료 1>")[1] == 0
    assert shape_of(xml, header, "x = 2y")[1] == 0
    assert classify("첫 줄\n둘째 줄 글입니다", False)[0] == "plain"


def test_same_width_shares_one_paragraph_shape(tmp_path):
    texts = ["갑: " + PROSE, "을: " + PROSE, "병: " + PROSE]
    xml, _ = build(tmp_path, [item(texts)])
    ids = re.findall(r'<hp:p [^>]*paraPrIDRef="(\d+)"[^>]*><hp:run [^>]*><hp:t>[갑을병]:<hp:nbSpace/>', xml)
    assert len(ids) == 3 and len(set(ids)) == 1


def test_passage_body_is_no_longer_a_hanging_indent(tmp_path):
    passage = {"type": "passage", "count": 1, "lead": "다음 글을 읽고 물음에 답하시오.", "paragraphs": [PROSE]}
    xml, header = build(tmp_path, [passage, item([PROSE])])
    assert shape_of(xml, header, PROSE[:10])[1:] == (1000, 0)


def test_form_with_its_own_indent_is_left_alone(tmp_path):
    xml, header = build(tmp_path, [item(["갑: " + PROSE])])
    assert shape_of(xml, header, "갑: ")[1] == -1900          # 양식 상자 본문은 들여쓰기 0이라 바뀐다
    # 이미 내어쓰기가 있는 문단은 keep_own으로 건드리지 않는다 (공통 지문의 표지 문단은 별도 경로)
    assert classify("갑: x", False) == ("hang", 1900)


@pytest.mark.parametrize("choices,expected", [(["3", "-12", "0.5", "7", "100"], "1x5"), (["증가", "감소", "불변", "일정", "무"], "1x5"),
                                              (["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄴ, ㄷ", "ㄱ, ㄴ, ㄷ"], "2x3"),
                                              (["창가의 화분", "달리는 말", "푸른 하늘", "깊은 바다", "높은 산"], "2x3"),
                                              (["이 글은 사실을 바탕으로 쓴 글이다"] * 5, "5x1")])
def test_auto_layout_by_longest_choice(choices, expected):
    assert auto_layout({"type": "combo_table", "choices": choices}) == expected


def test_auto_layout_never_puts_bogi_items_on_one_row():
    assert auto_layout({"type": "combo_table", "choices": FIVE, "bogi": ["x"]}) == "2x3"
    assert auto_layout({"type": "paragraphs", "choices": FIVE}) is None


def tables(xml):
    found = []
    for table in re.finditer(r'<hp:tbl [^>]*rowCnt="(\d+)" colCnt="(\d+)"', xml):
        if "①" in xml[table.start():xml.index("</hp:tbl>", table.start())]:
            found.append(f"{table.group(1)}x{table.group(2)}")
    return found


def test_items_without_layout_get_the_narrowest_fitting_frame(tmp_path):
    items = [{"type": "combo_table", "stem": "수", "points": 3, "choices": ["1", "2", "3", "4", "5"], "answer": 1},
             {"type": "combo_table", "stem": "합", "points": 3, "choices": ["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄴ, ㄷ", "ㄱ, ㄴ, ㄷ"], "answer": 2},
             {"type": "short_table", "stem": "문장", "points": 3, "choices": ["이 글은 사실을 바탕으로 쓴 글이다"] * 5, "answer": 3},
             {"type": "short_table", "stem": "낱말", "points": 3, "choices": ["가", "나", "다", "라", "마"], "answer": 4}]
    xml, _ = build(tmp_path, items)
    assert tables(xml) == ["1x5", "2x3", "5x1", "1x5"]


def test_explicit_layout_is_still_respected(tmp_path):
    items = [{"type": "combo_table", "layout": "5x1", "stem": "수", "points": 3, "choices": ["1", "2", "3", "4", "5"], "answer": 1}]
    xml, _ = build(tmp_path, items)
    assert tables(xml) == ["5x1"]


def test_space_after_a_marker_does_not_stretch(tmp_path):
    """양쪽 정렬에서 표지 뒤 빈칸이 벌어지면 둘째 줄이 첫 줄 글 시작과 어긋난다 (한글 2024 화면에서 확인).
    표지 뒤 빈칸은 묶음 빈칸(hp:nbSpace)으로 써서 늘어나지 않게 한다. <보기>의 ㄱ.도 같다."""
    texts = ["교사: " + PROSE, "갑: " + PROSE, "(가) " + PROSE, "○ " + PROSE]
    spec = item(texts)
    spec["bogi"] = ["첫째 진술입니다", "둘째 진술입니다", "셋째 진술입니다"]
    spec["choices"] = ["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄴ, ㄷ", "ㄱ, ㄴ, ㄷ"]
    xml, _ = build(tmp_path, [spec])
    for glued in ("교사:<hp:nbSpace/>", "갑:<hp:nbSpace/>", "(가)<hp:nbSpace/>", "○<hp:nbSpace/>", "ㄱ.<hp:nbSpace/>첫째"):
        assert glued in xml, glued
    assert " " not in xml
