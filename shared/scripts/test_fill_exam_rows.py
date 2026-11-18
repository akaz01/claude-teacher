"""선지 행 높이 맞춤과 원안지 줄나눔 설정 시험."""
import re
import zipfile
from pathlib import Path

from fill_exam import fill_exam
from fill_exam_rows import LINE_RATIO, choice_lines, fit_choice_rows

FORM = Path(__file__).resolve().parents[2] / "skills" / "assessment-items" / "assets" / "exam_form.hwpx"
EM = 1000
INNER = 25535 - 651                     # 원안지 5x1 선지 칸 너비 - 왼쪽·오른쪽 여백


def row_xml(text: str, height: int = 1565) -> str:
    return (f'<hp:tr><hp:tc name=""><hp:subList><hp:p><hp:run charPrIDRef="1"><hp:t>{text}</hp:t></hp:run></hp:p>'
            f'</hp:subList><hp:cellSz width="25535" height="{height}"/>'
            f'<hp:cellMargin left="510" right="141" top="0" bottom="0"/></hp:tc></hp:tr>')


def table_xml(texts: list[str]) -> str:
    rows = "".join(row_xml(text) for text in texts)
    return f'<hp:tbl id="1"><hp:sz width="25535" height="{1565 * len(texts)}"/>{rows}</hp:tbl>'


def heights(xml: str) -> list[int]:
    return [int(value) for value in re.findall(r'<hp:cellSz width="\d+" height="(\d+)"', xml)]


def test_short_korean_choice_is_one_line():
    assert choice_lines("① 신한 청년당이 파리 강화 회의에 대표를 보냈다.", INNER, 1300, EM) == 1


def test_long_korean_choice_wraps_to_two_lines():
    assert choice_lines("② 김약연 등이 북간도에서 명동 학교를 세워 교육하였다.", INNER, 1300, EM) == 2


def test_english_words_are_not_split():
    text = "③ The Green Art Box cleans paint water with filters."
    assert choice_lines(text, INNER, 1300, EM) == 2


def test_highlight_tags_are_not_counted_as_text():
    answer = '<hp:markpenBegin color="#FFFF00"/>① 짧은 선지<hp:markpenEnd/>'
    fitted = fit_choice_rows(table_xml([answer, "② 짧은 선지"]), EM)
    assert heights(fitted) == [1565, 1565]


def test_wrapped_choice_row_grows_by_one_line_and_table_follows():
    fitted = fit_choice_rows(table_xml(["① 짧은 선지", "② 김약연 등이 북간도에서 명동 학교를 세워 교육하였다."]), EM)
    pitch = round(EM * LINE_RATIO)
    assert heights(fitted) == [1565, 1565 + pitch]
    assert f'<hp:sz width="25535" height="{1565 * 2 + pitch}"/>' in fitted


def test_line_break_inside_a_choice_is_counted():
    """선지 글의 
은 같은 문단의 줄바꿈 태그가 된다. 그 줄도 세어 행을 늘린다 (리뷰 지적)."""
    fitted = fit_choice_rows(table_xml(["① 가", "② 둘째<hp:lineBreak/>줄"]), EM)
    assert heights(fitted) == [1565, 1565 + round(EM * LINE_RATIO)]


def test_curly_quote_english_word_is_not_split_like_korean():
    text = "③ school morning book teacher friends read wasn’t every student with went a quietly library"
    same_width_ascii = text.replace("’", ";")            # 폭 어림이 같은 ASCII 문자로 바꿔도 줄 수가 같아야 한다
    assert choice_lines(text, INNER, 1300, EM) == choice_lines(same_width_ascii, INNER, 1300, EM)


def test_english_word_longer_than_a_line_is_split():
    assert choice_lines("① internationalization", 5000, 1300, EM) >= 3


def test_line_spacing_and_hang_are_read_from_the_paragraph_shape():
    shape = ('<hh:paraPr id="7"><hc:intent value="-1500" unit="HWPUNIT"/>'
             '<hh:lineSpacing type="PERCENT" value="180" unit="HWPUNIT"/></hh:paraPr>')
    xml = table_xml(["① 가", "② 김약연 등이 북간도에서 명동 학교를 세워 교육하였다."]).replace("<hp:p>", '<hp:p paraPrIDRef="7">')
    assert heights(fit_choice_rows(xml, EM, {"7": shape})) == [1565, 1565 + 1800]


def test_table_inner_margin_is_used_when_cell_has_no_own_margin():
    xml = table_xml(["① 김약연 등이 북간도에서 명동 학교를 세워 교육하였다."]).replace("<hp:tc ", '<hp:tc hasMargin="0" ')
    wide = xml.replace('<hp:sz width', '<hp:inMargin left="0" right="0" top="0" bottom="0"/><hp:sz width')
    narrow = xml.replace('<hp:sz width', '<hp:inMargin left="3000" right="3000" top="0" bottom="0"/><hp:sz width')
    assert heights(fit_choice_rows(wide, EM)) == [1565 + round(EM * LINE_RATIO)]
    assert heights(fit_choice_rows(narrow, EM))[0] > heights(fit_choice_rows(wide, EM))[0] - 1


def test_table_with_a_table_inside_is_left_alone():
    inner = '<hp:tbl id="2"><hp:sz width="1" height="1"/></hp:tbl>'
    xml = table_xml(["② 김약연 등이 북간도에서 명동 학교를 세워 교육하였다."]).replace("</hp:subList>", inner + "</hp:subList>")
    assert fit_choice_rows(xml, EM) == xml


def test_form_breaks_stems_choices_and_boxes_by_character():
    """발문·선지·상자·<보기>는 글자 단위(빈칸이 벌어지지 않음). 교사 지시 2026-11-18.
    한글 2024 화면 확인: breakNonLatinWord="KEEP_WORD"가 글자 단위, "BREAK_WORD"가 어절 단위다."""
    with zipfile.ZipFile(FORM) as package:
        header = package.read("Contents/header.xml").decode("utf-8")

    def breaking(shape: str) -> str:
        block = re.search(rf'<hh:paraPr id="{shape}".*?</hh:paraPr>', header, re.S).group(0)
        return re.search(r'breakNonLatinWord="(\w+)"', block).group(1)

    assert breaking("114") == "KEEP_WORD"           # 5x1 선지
    assert breaking("115") == "KEEP_WORD"           # <보기>
    assert breaking("117") == "KEEP_WORD"           # 발문도 글자 단위 (교사 지시 2026-11-18)
    with zipfile.ZipFile(FORM) as package:
        section = package.read("Contents/section0.xml").decode("utf-8")
    box = next(cell for cell in re.findall(r"<hp:tc\b.*?</hp:tc>", section, re.S) if "자료 상자 글" in cell)
    assert breaking(re.search(r'paraPrIDRef="(\d+)"', box).group(1)) == "KEEP_WORD"   # 자료 상자 본문


def test_filled_exam_grows_wrapped_choice_rows(tmp_path):
    item = {"type": "combo_table", "stem": "가장 적절한 것은?", "points": 5, "answer": 1, "layout": "5x1",
            "choices": ["짧은 선지", "김약연 등이 북간도에서 명동 학교를 세워 교육하였다.", "가", "나", "다"]}
    out = tmp_path / "out.hwpx"
    fill_exam(FORM, {"items": [item]}, out)
    with zipfile.ZipFile(out) as package:
        xml = package.read("Contents/section0.xml").decode("utf-8")
    start = xml.rfind("<hp:tbl", 0, xml.index("김약연"))
    table = xml[start:xml.index("</hp:tbl>", start)]
    row_heights = sorted(set(heights(table)))
    assert len(row_heights) >= 2 and row_heights[-1] - row_heights[-2] >= 1500


def test_narrow_cell_does_not_loop_forever():
    assert choice_lines("① 아주 좁은 칸에 든 긴 선지 글", 800, 1300, EM) >= 2
    assert choice_lines("① 가나다", 0, 1300, EM) >= 1


def test_form_aligns_stems_and_choices_left():
    """선지는 왼쪽 정렬(낱말 사이가 벌어지지 않음), 발문과 자료 상자·<보기>는 양쪽 정렬 (교사 확인 2026-11-18)."""
    with zipfile.ZipFile(FORM) as package:
        header = package.read("Contents/header.xml").decode("utf-8")

    def align(shape: str) -> str:
        block = re.search(rf'<hh:paraPr id="{shape}".*?</hh:paraPr>', header, re.S).group(0)
        return re.search(r'<hh:align horizontal="(\w+)"', block).group(1)

    assert align("117") == "JUSTIFY"                            # 발문(문두)은 양쪽 정렬 (교사 지시 2026-11-18)
    assert align("114") == "LEFT"                               # 한 줄에 하나인 선지
    assert align("115") == "JUSTIFY"
