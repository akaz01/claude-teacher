"""기본 원안지 양식(assessment-items/assets/exam_form.hwpx)과 fill_exam의 배치 고르기·배점 넘김·내어쓰기 시험."""
import re
import zipfile
from pathlib import Path

import pytest

from fill_exam import _last_line_room, _text_width, fill_exam
from fill_exam_parse import choice_order_notes, inspect_exam

FORM = Path(__file__).resolve().parents[2] / "skills" / "assessment-items" / "assets" / "exam_form.hwpx"
pytestmark = pytest.mark.skipif(not FORM.exists(), reason="기본 원안지 양식이 없음")
CHOICES = ["문장형 선지 하나", "문장형 선지 둘", "문장형 선지 셋", "문장형 선지 넷", "문장형 선지 다섯"]


def section(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        return package.read("Contents/section0.xml").decode("utf-8")


def layouts(xml: str) -> list[str]:
    """선지 표(①이 든 표)의 행x칸 목록, 나오는 차례대로."""
    found = []
    for table in re.finditer(r'<hp:tbl [^>]*rowCnt="(\d+)" colCnt="(\d+)"', xml):
        end = xml.index("</hp:tbl>", table.start())
        if "①" in xml[table.start():end]:
            found.append(f"{table.group(1)}x{table.group(2)}")
    return found


def test_default_form_has_every_frame():
    report = inspect_exam(FORM)
    for line in ("2단", "공통 지문: 1곳", "short_table", "combo_table", "written", "<보기>: 1개", "자료 상자: 2개"):
        assert line in report
    with zipfile.ZipFile(FORM) as package:
        for name in package.namelist():
            data = package.read(name)
            assert "고운".encode() not in data and "교과부장".encode() not in data


def test_layout_picks_the_choice_table(tmp_path):
    items = [{"type": "combo_table", "layout": "2x3", "stem": "가", "points": 3, "choices": CHOICES, "answer": 1},
             {"type": "combo_table", "layout": "5x1", "stem": "나", "points": 3, "choices": CHOICES, "answer": 2},
             {"type": "combo_table", "stem": "다", "points": 3, "bogi": ["하나", "둘", "셋"],
              "choices": ["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄴ, ㄷ", "ㄱ, ㄴ, ㄷ"], "answer": 3}]
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": items}, out)
    assert layouts(section(out)) == ["2x3", "5x1", "2x3"]          # <보기>가 있으면 <보기> 틀(2x3)


def test_unknown_layout_falls_back_with_a_note(tmp_path):
    item = {"type": "combo_table", "layout": "3x2", "stem": "가", "points": 3, "choices": CHOICES, "answer": 1}
    result = fill_exam(FORM, {"items": [item]}, tmp_path / "out.hwpx")
    assert any("layout 3x2" in note for note in result.notes)


def test_points_move_to_the_next_line_instead_of_splitting(tmp_path):
    long_stem = "다음 대화의 빈칸에 들어갈 말로 가장 알맞은 것은?"          # 실제 한글에서 "[9 / 점]"으로 쪼개지던 문장
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "5x1", "stem": long_stem, "points": 9,
                                "choices": CHOICES, "answer": 1}]}, out)
    xml = section(out)
    assert re.search(r"알맞은 것은\?(?:</hp:t>)?.{0,80}<hp:lineBreak/>.{0,80}\[9점\]", xml, re.S)


def test_short_stem_keeps_points_on_the_same_line(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "short_table", "stem": "옳은 것은?", "points": 3,
                                "choices": ["1", "2", "3", "4", "5"], "answer": 1}]}, out)
    assert "옳은 것은? [3점]" in section(out)


@pytest.mark.parametrize("student", [False, True])
def test_footer_gets_automatic_page_numbers(tmp_path, student):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "short_table", "stem": "옳은 것은?", "points": 3,
                                "choices": ["1", "2", "3", "4", "5"], "answer": 1}]}, out, student=student)
    footer = re.search(r"<hp:footer\b.*?</hp:footer>", section(out), re.S).group(0)
    words = re.sub(r"<hp:ctrl><hp:autoNum [^>]*numType=\"(\w+)\".*?</hp:ctrl>", r"[\1]", footer)
    words = re.sub(r"<[^>]+>", "", words)
    assert "전체 ([TOTAL_PAGE])쪽 가운데 ([PAGE])쪽" in words                  # 양식의 괄호와 글은 그대로
    assert "(0)" not in words

def test_line_room_estimate():
    em = 1000
    assert _text_width("가나", em) == 2000 and _text_width(" ", em) == 300
    assert _last_line_room("가" * 10, 20000, 872, em) == pytest.approx(10000)
    assert _last_line_room(("가" * 9 + " ") * 3, 20000, 872, em) < 20000


def test_choices_and_bogi_lines_hang(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "combo_table", "stem": "다", "points": 3, "bogi": ["하나", "둘", "셋"],
                                "choices": ["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄴ, ㄷ", "ㄱ, ㄴ, ㄷ"], "answer": 3}]}, out)
    with zipfile.ZipFile(out) as package:
        header = package.read("Contents/header.xml").decode("utf-8")
    xml = section(out)
    for start in ("ㄱ. 하나", "ㄷ. 셋"):
        shape = re.findall(r'paraPrIDRef="(\d+)"[^>]*><hp:run charPrIDRef="\d+"><hp:t>' + start, xml)[0]
        block = re.search(rf'<hh:paraPr id="{shape}".*?</hh:paraPr>', header, re.S).group(0)
        assert '<hc:intent value="-1600"' in block


def item(choices: list[str], answer: int) -> dict:
    return {"type": "combo_table", "stem": "가", "points": 3, "choices": choices, "answer": answer}


def test_staircase_order_is_checked():
    rising = item(["I'm worried.", "I'm sorry to hear that.", "It's too late to join it.", "I don't like poems at all.",
                   "I'm looking forward to it."], 5)
    falling = item(list(reversed(rising["choices"])), 1)
    assert not choice_order_notes([("문항 1", rising)])
    assert any("계단식" in note for note in choice_order_notes([("문항 1", falling)]))


def test_labels_combos_and_numbers_follow_their_own_order():
    labelled = item(["㉠ 아주 긴 첫 선지 문장", "㉡ 짧다", "㉢ 중간 길이", "㉣ 가", "㉤ 나"], 1)
    combos = item(["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄱ, ㄷ", "ㄱ, ㄴ, ㄷ"], 2)
    numbers = item(["2", "4", "10", "12", "100"], 3)
    shuffled = item(["10", "2", "4", "12", "100"], 3)
    assert not choice_order_notes([("문항 1", labelled), ("문항 2", combos), ("문항 3", numbers)])
    assert any("작은 수부터" in note for note in choice_order_notes([("문항 1", shuffled)]))


def test_answer_spread_is_checked():
    numbers = ["1", "2", "3", "4", "5"]
    even = [(f"문항 {n}", item(numbers, answer)) for n, answer in enumerate([1, 2, 3, 4, 5, 1, 2, 3, 4, 5], 1)]
    lopsided = [(f"문항 {n}", item(numbers, answer)) for n, answer in enumerate([3, 3, 1, 3, 2, 3, 4, 3, 5, 3], 1)]
    assert not choice_order_notes(even)
    assert any("정답 번호 분포" in note for note in choice_order_notes(lopsided))
    streak = [(f"문항 {n}", item(numbers, 2)) for n in range(1, 5)]
    assert any("4문항 이어짐" in note for note in choice_order_notes(streak))
