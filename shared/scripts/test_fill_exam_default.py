"""기본 원안지 양식(assessment-items/assets/exam_form.hwpx)과 fill_exam의 배치 고르기·배점 넘김·내어쓰기 시험."""
import re
import zipfile
from pathlib import Path

import pytest

from fill_exam import _last_line_room, _text_width, fill_exam
from fill_exam_parse import choice_order_notes, inspect_exam
from fill_hwpx import FillError

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
    item = {"type": "combo_table", "layout": "4x4", "stem": "가", "points": 3, "choices": CHOICES, "answer": 1}
    result = fill_exam(FORM, {"items": [item]}, tmp_path / "out.hwpx")
    assert any("layout 4x4" in note for note in result.notes)


def test_points_follow_the_last_word_with_a_plain_space(tmp_path):
    """배점 앞은 보통 빈칸이다. 묶음 빈칸이면 "것은? [5점]"이 통째로 내려가 윗줄 끝이 비었다(교사 지적).
    교사가 한글에서 고칠 수 있게 줄을 강제로 바꾸지 않는다."""
    long_stem = "다음 대화의 빈칸에 들어갈 말로 가장 알맞은 것은?"
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "5x1", "stem": long_stem, "points": 9,
                                "choices": CHOICES, "answer": 1}]}, out)
    xml = section(out)
    assert "알맞은 것은? [9점]" in xml and "<hp:nbSpace/>[9점]" not in xml
    assert "<hp:lineBreak/>[9점]" not in xml and " " not in xml


def test_points_written_in_the_stem_get_one_plain_space(tmp_path):
    """points 없이 문제 글에 쓴 배점도 앞 빈칸을 보통 빈칸 하나로 맞춘다 (_keep_points를 직접 거치는 입력)."""
    out = tmp_path / "out.hwpx"
    stem = "다음 중 옳은 것은?   [9점]"
    fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "5x1", "stem": stem,
                                "choices": CHOICES, "answer": 1}]}, out)
    xml = section(out)
    assert "옳은 것은? [9점]" in xml and "<hp:nbSpace/>[9점]" not in xml


def test_points_in_stem_and_points_key_are_not_doubled(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "5x1", "stem": "옳은 것은? [5점]", "points": 5,
                                "choices": CHOICES, "answer": 1}]}, out)
    assert "[5점] [5점]" not in section(out) and "옳은 것은? [5점]" in section(out)
    with pytest.raises(FillError):
        fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "5x1", "stem": "옳은 것은? [4점]", "points": 5,
                                    "choices": CHOICES, "answer": 1}]}, tmp_path / "bad.hwpx")


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
    xml = section(out).replace("<hp:nbSpace/>", " ")            # 표지 뒤 묶음 빈칸은 보통 빈칸으로 읽는다
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


def test_repeated_answer_sequence_is_reported():
    answers = [4, 2, 5, 1, 3, 5, 2, 4, 1, 3, 2, 5, 4, 1, 3, 5, 2, 4, 1, 3]          # 4~10번과 14~20번이 같다
    named = [(f"문항 {n}", item(["가", "나", "다", "라", "마"], a)) for n, a in enumerate(answers, 1)]
    assert any("같은 순서로 되풀이" in note and "문항 4~문항 10" in note and "문항 14~문항 20" in note
               for note in choice_order_notes(named))
    fresh = [3, 5, 2, 4, 1, 4, 2, 5, 1, 3, 5, 3, 5, 4, 2, 1, 3, 1, 2, 4]
    named = [(f"문항 {n}", item(["가", "나", "다", "라", "마"], a)) for n, a in enumerate(fresh, 1)]
    assert not any("되풀이" in note for note in choice_order_notes(named))


def test_repeated_answer_note_uses_real_item_numbers_when_other_types_sit_between():
    """표형 선지·서답형이 중간에 끼어도 알림은 실제 문항 번호를 쓴다 (리뷰 지적)."""
    answers = iter([4, 2, 5, 1, 3, 5, 2, 4, 1, 3, 2, 5, 4, 1, 3, 5, 2, 4, 1, 3])
    named = []
    for number in range(1, 23):
        if number == 3:
            named.append((f"문항 {number}", {"type": "grid_table", "stem": "가", "answer": 1}))
        elif number == 6:
            named.append((f"문항 {number}", {"type": "written", "stem": "가"}))
        else:
            named.append((f"문항 {number}", item(["가", "나", "다", "라", "마"], next(answers))))
    note = next(note for note in choice_order_notes(named) if "되풀이" in note)
    assert "문항 5~문항 12" in note and "문항 16~문항 22" in note


def test_random_like_answers_rarely_trip_the_repeat_note():
    """우연히 생기는 짧은 되풀이(20문항 5지선다의 4개짜리)는 알리지 않는다 (리뷰: 거짓 알림이 잦음)."""
    answers = [1, 2, 3, 4, 5, 2, 1, 3, 4, 5, 1, 2, 3, 4, 2, 5, 3, 1, 4, 5]        # 1,2,3,4가 두 번
    named = [(f"문항 {n}", item(["가", "나", "다", "라", "마"], a)) for n, a in enumerate(answers, 1)]
    assert not any("되풀이" in note for note in choice_order_notes(named))


def test_same_answer_streak_is_not_reported_twice():
    named = [(f"문항 {n}", item(["가", "나", "다", "라", "마"], 3)) for n in range(1, 9)]
    notes = choice_order_notes(named)
    assert any("4문항 이어짐" in note for note in notes)
    assert not any("되풀이" in note for note in notes)


def test_pair_choices_checked_by_head_group_not_length():
    grouped = item(["acting - solution", "action - solving", "actor - solve", "actor - solution", "actor - solving"], 4)
    split = item(["cools - safely", "cools - quickly", "warms - safely", "cleans - quickly", "warms - quickly"], 1)
    assert not choice_order_notes([("문항 1", grouped)])
    split_notes = choice_order_notes([("문항 1", split)])
    assert any("앞 칸이 같은 것끼리" in note for note in split_notes)
    assert not any("계단식" in note for note in split_notes)


def test_labels_combos_and_numbers_follow_their_own_order():
    labelled = item(["㉠ 아주 긴 첫 선지 문장", "㉡ 짧다", "㉢ 중간 길이", "㉣ 가", "㉤ 나"], 1)
    combos = item(["ㄱ", "ㄴ", "ㄱ, ㄴ", "ㄱ, ㄷ", "ㄱ, ㄴ, ㄷ"], 2)
    numbers = item(["2", "4", "10", "12", "100"], 3)
    shuffled = item(["10", "2", "4", "12", "100"], 3)
    assert not choice_order_notes([("문항 1", labelled), ("문항 2", combos), ("문항 3", numbers)])
    assert any("작은 수부터" in note for note in choice_order_notes([("문항 1", shuffled)]))


def test_answer_spread_is_checked():
    numbers = ["1", "2", "3", "4", "5"]
    even = [(f"문항 {n}", item(numbers, answer)) for n, answer in enumerate([1, 2, 3, 4, 5, 2, 4, 1, 5, 3], 1)]
    lopsided = [(f"문항 {n}", item(numbers, answer)) for n, answer in enumerate([3, 3, 1, 3, 2, 3, 4, 3, 5, 3], 1)]
    assert not choice_order_notes(even)
    assert any("정답 번호 분포" in note for note in choice_order_notes(lopsided))
    streak = [(f"문항 {n}", item(numbers, 2)) for n in range(1, 5)]
    assert any("4문항 이어짐" in note for note in choice_order_notes(streak))


def test_every_choice_cell_of_a_frame_shares_one_paragraph_shape():
    """한 선지 틀의 칸마다 문단 모양이 다르면 그 번호만 두 줄째 내어쓰기가 빠진다 (③만 들여쓰기 안 되던 결함)."""
    from fill_exam_parse import choice_cells, read_exam
    from fill_hwpx import read_form
    form = read_form(FORM)
    exam = read_exam(form)
    xml = form.section_xml[exam.section]
    for frame in exam.frames:
        if frame.choice_table is None:
            continue
        shapes = {re.search(r'paraPrIDRef="(\d+)"', xml[cell.paragraphs[0].start:cell.paragraphs[0].start + 200]).group(1)
                  for cell in choice_cells(frame.choice_table.table)}
        assert len(shapes) == 1, (frame.kind, shapes)


def test_item_paragraphs_keep_lines_together(tmp_path):
    """문두 문단 하나가 단 끝에서 두 단으로 쪼개지지 않게 문단 보호(keepLines)도 켠다."""
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "5x1", "stem": "가", "points": 3, "box": "자료",
                                "choices": CHOICES, "answer": 1}]}, out)
    with zipfile.ZipFile(out) as package:
        header = package.read("Contents/header.xml").decode("utf-8")
    stem_ref = re.search(r'<hp:p [^>]*paraPrIDRef="(\d+)"[^>]*>(?:(?!</hp:p>).)*?1\.', section(out), re.S).group(1)
    shape = re.search(rf'<hh:paraPr id="{stem_ref}".*?</hh:paraPr>', header, re.S).group(0)
    assert 'keepWithNext="1"' in shape and 'keepLines="1"' in shape



# ---------------------------------------------------------------- 양식 값 (exam-layout.md 5절)
BASE_LINE = 1000            # 기준선: 번호 자리에서 글자 하나 들어간 선
BOGI_LABEL = "&lt;보 기&gt;"


def form_parts() -> tuple[str, str]:
    with zipfile.ZipFile(FORM) as package:
        return package.read("Contents/section0.xml").decode("utf-8"), package.read("Contents/header.xml").decode("utf-8")


def tables_with(xml: str, marker: str) -> list[str]:
    found = []
    for start in re.finditer(r"<hp:tbl\b", xml):
        table = xml[start.start():xml.index("</hp:tbl>", start.start())]
        if marker in table:
            found.append(table)
    return found


def number_attr(tag: str, name: str, text: str) -> int:
    return int(re.search(rf'<hp:{tag}\b[^>]*\b{name}="(\d+)"', text).group(1))


def shape(header: str, tag: str, ident: str) -> str:
    return re.search(rf'<hh:{tag} id="{ident}".*?</hh:{tag}>', header, re.S).group(0)


def test_boxes_and_bogi_start_on_the_reference_line_and_end_at_the_column_edge():
    xml, _ = form_parts()
    frames = tables_with(xml, 'id="1103651517"') + tables_with(xml, BOGI_LABEL)
    assert len(frames) == 3                                # 자료 상자 둘(글이 든 것, 서답형 답 상자), <보기> 하나
    edges = set()
    for table in frames:
        margin = re.search(r"<hp:outMargin\b[^>]*>", table).group(0)
        left, right = number_attr("outMargin", "left", margin), number_attr("outMargin", "right", margin)
        edges.add((left, left + number_attr("sz", "width", table) + right))
    assert edges == {(BASE_LINE, 26500)}                 # 상자들이 같은 자리, 오른쪽은 단 끝(26504)에 맞춤


def test_box_cell_widths_add_up_to_the_table_width():
    xml, _ = form_parts()
    for table in tables_with(xml, "자료 상자 글"):
        widths = [int(w) for w in re.findall(r'<hp:cellSz width="(\d+)"', table)]
        assert widths[0] == widths[-1] == number_attr("sz", "width", table) == sum(widths[1:4])


def test_bogi_label_stays_centred_after_narrowing():
    xml, _ = form_parts()
    table = tables_with(xml, BOGI_LABEL)[0]
    cells = {(number_attr("cellAddr", "colAddr", c), number_attr("cellAddr", "rowAddr", c)): number_attr("cellSz", "width", c)
             for c in re.findall(r"<hp:tc\b.*?</hp:tc>", table, re.S)}
    assert abs(cells[(0, 0)] - cells[(3, 0)]) <= 60      # 이름표 좌우 윗선 길이가 거의 같다
    assert cells[(0, 3)] == number_attr("sz", "width", table)


def plain_choice_tables(xml: str) -> list[str]:
    """①이 든 표 가운데 테두리 없는 선지 표."""
    return [table for table in tables_with(xml, "①") if 'borderFillIDRef="18"' not in table]


def test_choice_cells_start_on_the_reference_line():
    xml, _ = form_parts()
    tables = plain_choice_tables(xml)
    assert len(tables) == 5                              # 5x1 둘, 1x5, 2x3, 3x2
    for table in tables:
        margin = re.search(r"<hp:outMargin\b[^>]*>", table).group(0)
        inner = re.search(r"<hp:cellMargin\b[^>]*>", table).group(0)
        assert number_attr("outMargin", "left", margin) + number_attr("cellMargin", "left", inner) == BASE_LINE


def test_choice_cells_have_no_vertical_padding_and_a_narrow_right_margin():
    """선지 줄 사이 = 본문 줄 간격(1600)이 되도록 칸 위아래 여백 0. 오른쪽 여백은 141로 줄여 글이 더 들어간다."""
    xml, _ = form_parts()
    for table in plain_choice_tables(xml):
        margins = re.findall(r"<hp:(?:cellMargin|inMargin)\b[^>]*>", table)
        assert margins
        for margin in margins:
            assert 'top="0"' in margin and 'bottom="0"' in margin and 'right="141"' in margin and 'left="510"' in margin


def test_space_below_boxes_is_wider_than_before():
    xml, _ = form_parts()
    for table in tables_with(xml, "자료 상자 글") + tables_with(xml, BOGI_LABEL):
        assert number_attr("outMargin", "bottom", re.search(r"<hp:outMargin\b[^>]*>", table).group(0)) >= 600


def test_item_numbers_are_bold_and_one_point_one_five_times_the_body():
    xml, header = form_parts()
    refs = set(re.findall(r'<hp:run charPrIDRef="(\d+)"><hp:t>(?:\d+\.|서답형 1\.)</hp:t>', xml))
    assert len(refs) == 1
    number = shape(header, "charPr", refs.pop())
    assert 'height="1150"' in number and "<hh:bold/>" in number
    assert 'height="1000"' in shape(header, "charPr", "0")          # 본문 10pt


def test_stem_paragraphs_hang_from_the_reference_line_and_share_one_shape():
    xml, header = form_parts()
    refs = set(re.findall(r'paraPrIDRef="(\d+)"[^>]*><hp:run charPrIDRef="\d+"><hp:t>(?:\d+\.|서답형 1\.)</hp:t>', xml))
    assert len(refs) == 1
    stem = shape(header, "paraPr", refs.pop())
    assert f'<hc:intent value="-{BASE_LINE}"' in stem and 'keepWithNext="1"' in stem and 'value="160"' in stem


def test_default_form_has_the_two_column_and_grid_choice_frames():
    report = inspect_exam(FORM)
    assert "combo_table 표 3×2" in report and "grid_table 표 6×4" in report


def test_two_column_choices_pick_the_3x2_frame(tmp_path):
    out = tmp_path / "out.hwpx"
    result = fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "3x2", "stem": "가", "points": 3,
                                         "choices": CHOICES, "answer": 1}]}, out)
    assert layouts(section(out)) == ["3x2"]
    assert not any("layout" in note for note in result.notes)


def test_two_column_frame_reduces_to_four_choices(tmp_path):
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [{"type": "combo_table", "layout": "3x2", "stem": "가", "points": 3,
                                "choices": CHOICES[:4], "answer": 2}]}, out)
    assert layouts(section(out)) == ["2x2"]


def test_grid_table_frame_is_filled(tmp_path):
    out = tmp_path / "out.hwpx"
    item = {"type": "grid_table", "stem": "표의 빈칸에 알맞은 것은?", "points": 3, "head": ["ⓐ", "ⓑ", "ⓒ"],
            "rows": [["가", "나", "다"], ["라", "마", "바"], ["사", "아", "자"], ["차", "카", "타"], ["파", "하", "거"]],
            "answer": 2}
    fill_exam(FORM, {"items": [item]}, out)
    xml = section(out)
    assert "<hp:t>파</hp:t>" in xml and "<hp:t>ⓒ</hp:t>" in xml


def test_grid_cells_are_centred_and_bordered():
    xml, header = form_parts()
    table = tables_with(xml, 'borderFillIDRef="18"')[0]
    refs = set(re.findall(r'paraPrIDRef="(\d+)"', table))
    assert len(refs) == 1
    assert 'horizontal="CENTER"' in shape(header, "paraPr", refs.pop())
