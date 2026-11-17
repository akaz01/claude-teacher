"""수업 PPT 폼 시험."""
import json

import pytest
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

import make_deck

DOC = {"subject": "과학", "unit": "단원", "meta": "중2", "slides": [
    {"type": "cover", "title": "제목"},
    {"type": "goals", "items": ["목표"]},
    {"type": "flow", "title": "흐름", "steps": [{"head": "가", "text": "나"}], "key": "핵심"},
    {"type": "cards", "title": "카드", "cards": [{"head": "가", "text": "나"}]},
    {"type": "compare", "title": "비교", "left": {"head": "가", "items": ["나"]}, "right": {"head": "다", "items": ["라"]}},
    {"type": "table", "title": "표", "header": ["가"], "rows": [["나"]]},
    {"type": "quiz", "question": "문제", "choices": ["가", "나"], "answer": 1},
    {"type": "summary", "items": ["정리"]},
]}

CYCLE_SLIDES = [
    {"type": "cover", "title": "제목"},
    {"type": "goals", "items": [{"text": "목표"}]},
    {"type": "keywords", "words": [{"word": "확산", "meaning": "입자가 퍼져 나가는 현상"}]},
    {"type": "outline", "items": ["첫째 주기", "둘째 주기"], "current": 0},
    {"type": "section", "title": "1. 확산", "subtitle": "입자가 퍼진다"},
    {"type": "content", "title": "설명", "items": ["가", {"text": "나", "sub": ["다"]}], "key": "핵심"},
    {"type": "figure", "title": "그림", "caption": "교과서 32쪽", "callouts": ["설명"], "key": "핵심"},
    {"type": "check", "question": "맞는 것은?", "choices": ["가", "나", "다", "라", "마"], "answer": 4,
     "explain": "마가 맞는 까닭"},
    {"type": "check", "question": "참일까요?", "truth": False, "reasons": ["까닭 하나", "까닭 둘"], "answer": 1},
    {"type": "task", "title": "연습", "steps": ["첫째 일", "둘째 일"], "minutes": 3, "output": "공책에 두 문장",
     "answer": ["첫째 답", "둘째 답"]},
    {"type": "example", "title": "예제", "worked": {"lines": ["풀이 한 줄"]}, "problem": {"lines": ["문제 한 줄"]},
     "answer": ["문제의 답"]},
    {"type": "activity", "title": "활동", "time": "20분", "group": "4명 모둠", "materials": "비커",
     "roles": "기록, 발표", "output": "결과표", "steps": ["준비한다", "관찰한다"]},
    {"type": "summary", "items": ["정리"]},
]
CYCLE = {"subject": "과학", "unit": "단원", "meta": "중2", "slides": CYCLE_SLIDES}


def build(tmp_path, slides):
    """장 목록을 파일로 만들어 슬라이드 목록과 경고를 돌려준다."""
    out = tmp_path / "out.pptx"
    warnings = make_deck.build_deck({**CYCLE, "slides": slides}, out, tmp_path)
    return list(Presentation(out).slides), warnings


def frames(slide):
    return [shape.text_frame for shape in slide.shapes if shape.has_text_frame and shape.text_frame.text]


def slide_text(slide):
    return "\n".join(frame.text for frame in frames(slide))


def notes_text(slide):
    return slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""


def runs(slide):
    return [run for frame in frames(slide) for paragraph in frame.paragraphs for run in paragraph.runs]


def png(path, width, height):
    Image.new("RGB", (width, height), "white").save(path)
    return path


def test_quiz_adds_reveal_slide(tmp_path):
    out = tmp_path / "a.pptx"
    make_deck.build_deck(DOC, out)
    assert len(Presentation(out).slides) == len(DOC["slides"]) + 1


def test_all_text_is_centered_both_ways(tmp_path):
    out = tmp_path / "a.pptx"
    make_deck.build_deck(DOC, out)
    all_frames = [frame for slide in Presentation(out).slides for frame in frames(slide)]
    assert all_frames
    assert all(frame.vertical_anchor == MSO_ANCHOR.MIDDLE for frame in all_frames)
    assert all(paragraph.alignment == PP_ALIGN.CENTER for frame in all_frames for paragraph in frame.paragraphs)


def test_long_text_shrinks_but_not_below_minimum():
    assert make_deck.fit_size("가" * 200, 3, 1, 30) == make_deck.MIN_FONT


def test_short_text_keeps_size():
    assert make_deck.fit_size("가", 3, 1, 30) == 30


def test_unknown_slide_type_is_refused(tmp_path):
    with pytest.raises(ValueError, match="wave"):
        make_deck.build_deck({**DOC, "slides": [{"type": "wave"}]}, tmp_path / "a.pptx")


def test_missing_subject_is_refused(tmp_path):
    with pytest.raises(ValueError, match="subject"):
        make_deck.build_deck({**DOC, "subject": ""}, tmp_path / "a.pptx")


@pytest.mark.parametrize("spec", [spec for spec in CYCLE_SLIDES if spec["type"] != "cover"],
                         ids=lambda spec: spec["type"])
def test_every_kind_builds_centered_inside_the_slide(tmp_path, spec):
    slides, _ = build(tmp_path, [spec])
    assert all(paragraph.alignment == PP_ALIGN.CENTER for slide in slides for frame in frames(slide)
               for paragraph in frame.paragraphs)
    assert all(frame.vertical_anchor == MSO_ANCHOR.MIDDLE for slide in slides for frame in frames(slide))
    width, height = Inches(make_deck.SLIDE_W), Inches(make_deck.SLIDE_H)
    for slide in slides:
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= width + 1000 and shape.top + shape.height <= height + 1000


def test_full_cycle_deck_has_one_extra_slide_per_reveal(tmp_path):
    slides, _ = build(tmp_path, CYCLE_SLIDES)
    assert len(slides) == len(CYCLE_SLIDES) + 4


def test_bold_marks_become_bold_runs_without_asterisks(tmp_path):
    slides, _ = build(tmp_path, [{"type": "content", "title": "입자는 **스스로** 움직인다",
                                  "items": ["잉크가 **퍼진다**", "짝 없는 ** 별표"]}])
    assert "**" not in slide_text(slides[0])
    bold_by_text = {run.text: run.font.bold for run in runs(slides[0])}
    assert bold_by_text["퍼진다"] is True and bold_by_text["잉크가 "] is False


def test_bold_mark_in_title_uses_the_subject_color(tmp_path):
    slides, _ = build(tmp_path, [{"type": "content", "title": "입자는 **스스로** 움직인다", "items": ["가"]}])
    marked = next(run for run in runs(slides[0]) if run.text == "스스로")
    assert str(marked.font.color.rgb) == make_deck.PALETTES["과학"][0]


def test_marks_do_not_count_toward_text_width():
    assert make_deck.fit_size("**" + "가" * 10 + "**", 3, 0.6, 30) == make_deck.fit_size("가" * 10, 3, 0.6, 30)


def test_short_tag_title_and_key_keep_their_sizes(tmp_path):
    slides, _ = build(tmp_path, [{"type": "content", "title": "짧은 제목", "tag": "꼬리표", "items": ["가"],
                                  "key": "핵심 문장"}])
    sizes = {run.text: run.font.size.pt for run in runs(slides[0])}
    assert (sizes["꼬리표"], sizes["짧은 제목"], sizes["핵심 문장"]) == (18, 38, 26)


def test_fit_size_counts_only_the_real_vertical_margin():
    one_line = 30 * make_deck.LINE_RATIO / 72
    assert make_deck.fit_size("가", 3, one_line + 2 * make_deck.VPAD, 30) == 30


def test_six_choices_are_refused_with_a_readable_message(tmp_path):
    with pytest.raises(ValueError, match="1번째 장.*5개"):
        build(tmp_path, [{"type": "quiz", "question": "문제", "choices": list("가나다라마바"), "answer": 0}])


@pytest.mark.parametrize("answer", [5, -1, "1", True, None])
def test_answer_outside_the_choices_is_refused(tmp_path, answer):
    with pytest.raises(ValueError, match="answer"):
        build(tmp_path, [{"type": "check", "question": "문제", "choices": list("가나다라마"), "answer": answer}])


def test_five_choices_stay_above_the_body_bottom(tmp_path):
    slides, _ = build(tmp_path, [{"type": "quiz", "question": "문제", "choices": list("가나다라마"), "answer": 0}])
    assert all(shape.top + shape.height <= Inches(make_deck.BODY_BOTTOM) + 1000 for shape in slides[0].shapes)


def test_check_reveal_marks_the_answer_with_more_than_color(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "choices": ["가", "나"], "answer": 1,
                                  "explain": "나가 맞는 까닭"}])
    assert make_deck.ANSWER_MARK not in slide_text(slides[0]) and "까닭" not in slide_text(slides[0])
    marked = next(run for run in runs(slides[1]) if make_deck.ANSWER_MARK in run.text)
    assert "나" in marked.text and marked.font.bold is True
    assert "까닭" in slide_text(slides[1])


def test_reveal_false_leaves_only_the_question_slide(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "choices": ["가", "나"], "answer": 1,
                                  "reveal": False},
                                 {"type": "quiz", "question": "문제", "choices": ["가", "나"], "answer": 0,
                                  "reveal": False}])
    assert len(slides) == 2


def test_check_notes_always_carry_the_answer(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "choices": ["가", "나"], "answer": 1,
                                  "notes": "발문", "reveal_notes": "절반 넘게 틀리면 앞 설명으로 돌아간다"}])
    assert "발문" in notes_text(slides[0]) and "정답: ② 나" in notes_text(slides[0])
    assert "돌아간다" in notes_text(slides[1]) and "정답: ② 나" in notes_text(slides[1])


def test_true_false_with_reasons_reveals_both(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "truth": False,
                                  "reasons": ["까닭 하나", "까닭 둘"], "answer": 0}])
    marked = [run.text for run in runs(slides[1]) if make_deck.ANSWER_MARK in run.text]
    assert len(marked) == 2 and "거짓" in marked[0] and "까닭 하나" in marked[1]
    assert not any(make_deck.ANSWER_MARK in run.text for run in runs(slides[0]))
    assert "정답: 거짓, ① 까닭 하나" in notes_text(slides[0])


def test_plain_true_false_needs_no_answer_index(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "truth": True}])
    assert len(slides) == 2 and "정답: 참" in notes_text(slides[0])


def test_task_answer_slide_keeps_the_same_frame(tmp_path):
    slides, _ = build(tmp_path, [{"type": "task", "title": "연습", "steps": ["첫째 일", "둘째 일"], "minutes": 3,
                                  "output": "공책", "answer": ["첫째 답"]}])
    assert len(slides) == 2
    first = {shape.text_frame.text: (shape.left, shape.top) for shape in slides[0].shapes if shape.has_text_frame}
    second = {shape.text_frame.text: (shape.left, shape.top) for shape in slides[1].shapes if shape.has_text_frame}
    assert first["첫째 일"] == second["첫째 일"] and first["둘째 일"] == second["둘째 일"]
    assert "첫째 답" not in slide_text(slides[0]) and "첫째 답" in slide_text(slides[1])
    assert "3분" in slide_text(slides[0]) and "공책" in slide_text(slides[0])
    assert "첫째 답" in notes_text(slides[0]) and "3분" in notes_text(slides[0])


def test_task_with_several_right_answers_says_it_is_an_example(tmp_path):
    slides, _ = build(tmp_path, [{"type": "task", "title": "연습", "steps": ["일"], "answer": ["답"], "sample": True}])
    assert "이렇게 쓸 수 있어요" in slide_text(slides[1])


def test_task_without_answer_has_no_answer_slide(tmp_path):
    slides, _ = build(tmp_path, [{"type": "task", "title": "연습", "steps": ["일"]}])
    assert len(slides) == 1


def test_outline_marks_the_current_cycle_with_more_than_color(tmp_path):
    slides, _ = build(tmp_path, [{"type": "outline", "items": ["첫째", "둘째"], "current": 1}])
    marked = next(run for run in runs(slides[0]) if "둘째" in run.text)
    assert "지금" in marked.text and marked.font.bold is True
    assert not any("지금" in run.text for run in runs(slides[0]) if "첫째" in run.text)


def test_outline_current_out_of_range_is_refused(tmp_path):
    with pytest.raises(ValueError, match="current"):
        build(tmp_path, [{"type": "outline", "items": ["첫째"], "current": 1}])


def test_keywords_show_word_and_meaning(tmp_path):
    slides, _ = build(tmp_path, [{"type": "keywords", "words": [{"word": "확산", "meaning": "퍼지는 현상"}]}])
    assert "확산" in slide_text(slides[0]) and "퍼지는 현상" in slide_text(slides[0])
    assert "핵심어" in slide_text(slides[0])


def test_example_reveals_answer_beside_the_worked_solution(tmp_path):
    slides, _ = build(tmp_path, [{"type": "example", "title": "예제", "worked": {"head": "풀이", "lines": ["한 줄"]},
                                  "problem": {"head": "문제", "lines": ["물음"]}, "answer": ["답 한 줄"]}])
    assert len(slides) == 2 and "답 한 줄" not in slide_text(slides[0])
    assert "답 한 줄" in slide_text(slides[1]) and "한 줄" in slide_text(slides[1])
    assert "답 한 줄" in notes_text(slides[0])


def test_long_content_continues_on_the_next_slide(tmp_path):
    slides, _ = build(tmp_path, [{"type": "content", "title": "설명", "items": list("가나다라마바사")}])
    assert len(slides) == 2 and "설명 (계속)" in slide_text(slides[1])


def test_content_sub_items_are_shown(tmp_path):
    slides, _ = build(tmp_path, [{"type": "content", "title": "설명", "items": [{"text": "위", "sub": ["아래"]}]}])
    assert "아래" in slide_text(slides[0])


def test_key_band_is_for_explanation_slides_only(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "choices": ["가", "나"], "answer": 0,
                                  "key": "띠 문장"},
                                 {"type": "task", "title": "연습", "steps": ["일"], "key": "띠 문장"},
                                 {"type": "content", "title": "설명", "items": ["가"], "key": "띠 문장"}])
    assert ["띠 문장" in slide_text(slide) for slide in slides] == [False, False, False, True]


def test_figure_keeps_image_ratio_and_finds_it_next_to_the_input(tmp_path):
    png(tmp_path / "그림.png", 400, 200)
    slides, _ = build(tmp_path, [{"type": "figure", "title": "그림", "image": "그림.png", "caption": "32쪽"}])
    picture = next(shape for shape in slides[0].shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE)
    assert picture.width / picture.height == pytest.approx(2, rel=0.01)
    assert "32쪽" in slide_text(slides[0])


def test_figure_callout_draws_a_line_to_the_named_point(tmp_path):
    png(tmp_path / "그림.png", 400, 400)
    slides, _ = build(tmp_path, [{"type": "figure", "title": "그림", "image": "그림.png",
                                  "callouts": [{"text": "여기", "x": 0.5, "y": 0.5}, "점 없는 설명"]}])
    lines = [shape for shape in slides[0].shapes if shape.shape_type == MSO_SHAPE_TYPE.LINE]
    assert len(lines) == 1 and "여기" in slide_text(slides[0]) and "점 없는 설명" in slide_text(slides[0])


def test_figure_callout_point_outside_the_image_is_refused(tmp_path):
    png(tmp_path / "그림.png", 400, 400)
    with pytest.raises(ValueError, match="callouts"):
        build(tmp_path, [{"type": "figure", "title": "그림", "image": "그림.png",
                          "callouts": [{"text": "여기", "x": 1.5, "y": 0.5}]}])


def test_figure_without_image_leaves_a_marked_place(tmp_path):
    slides, _ = build(tmp_path, [{"type": "figure", "title": "그림", "caption": "교과서 32쪽 입자 모형"}])
    assert "[그림: 교과서 32쪽 입자 모형]" in slide_text(slides[0])


def test_missing_image_file_is_refused(tmp_path):
    with pytest.raises(ValueError, match="없는그림.png"):
        build(tmp_path, [{"type": "figure", "title": "그림", "image": "없는그림.png"}])


def test_activity_shows_time_role_and_output(tmp_path):
    slides, _ = build(tmp_path, [{"type": "activity", "title": "활동", "time": "20분", "roles": "기록", "output": "표",
                                  "steps": ["한다"]}])
    assert all(word in slide_text(slides[0]) for word in ("20분", "기록", "표", "한다"))


def test_activity_with_more_than_five_steps_warns(tmp_path):
    _, warnings = build(tmp_path, [{"type": "activity", "title": "활동", "steps": list("가나다라마바"), "notes": "말"}])
    assert any("학습지" in warning for warning in warnings)


def test_section_shows_subtitle(tmp_path):
    slides, _ = build(tmp_path, [{"type": "section", "title": "차시 예고", "subtitle": "다음 시간"}])
    assert "다음 시간" in slide_text(slides[0])


def test_compare_accepts_the_other_generator_heading_name(tmp_path):
    slides, _ = build(tmp_path, [{"type": "compare", "title": "비교", "left": {"heading": "가", "items": ["나"]},
                                  "right": {"heading": "다", "items": ["라"]}}])
    assert "가" in slide_text(slides[0])


def test_missing_field_names_the_slide_and_the_field(tmp_path):
    with pytest.raises(ValueError, match="2번째 장.*title"):
        build(tmp_path, [{"type": "cover", "title": "제목"}, {"type": "content", "items": ["가"]}])


def test_empty_list_is_refused(tmp_path):
    with pytest.raises(ValueError, match="1번째 장"):
        build(tmp_path, [{"type": "content", "title": "설명", "items": []}])


def test_text_too_long_for_its_box_warns(tmp_path):
    _, warnings = build(tmp_path, [{"type": "content", "title": "설명", "items": ["가" * 900], "notes": "말"}])
    assert any("1번째 장" in warning and "넘" in warning for warning in warnings)


def test_slide_without_notes_warns_except_cover(tmp_path):
    _, warnings = build(tmp_path, [{"type": "cover", "title": "제목"}, {"type": "summary", "items": ["가"]}])
    assert len(warnings) == 1 and "2번째 장" in warnings[0] and "노트" in warnings[0]


def boxes(slide, *words):
    return [shape for shape in slide.shapes if shape.has_text_frame and any(word in shape.text_frame.text for word in words)]


def test_number_badge_does_not_cover_the_row_text(tmp_path):
    slides, _ = build(tmp_path, [{"type": "task", "title": "연습", "steps": ["지시문"]}])
    row, badge = boxes(slides[0], "지시문")[0], boxes(slides[0], "1")[0]
    assert row.left >= badge.left + badge.width


def test_same_role_boxes_share_one_font_size(tmp_path):
    slides, _ = build(tmp_path, [{"type": "activity", "title": "활동", "time": "20분", "group": "4명",
                                  "roles": "실험, 기록, 시간, 재료, 정리, 발표", "materials": "비커", "output": "표",
                                  "steps": ["가"]}])
    sizes = {run.font.size.pt for shape in boxes(slides[0], "시간", "모둠", "준비물", "산출물")
             for paragraph in shape.text_frame.paragraphs for run in paragraph.runs}
    assert len(sizes) == 1


def test_choice_size_does_not_change_on_the_answer_slide(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "answer": 0, "reveal": True,
                                  "choices": ["가" * 13, "나" * 13, "다" * 13, "라" * 13]}])
    sizes = [{run.font.size.pt for shape in boxes(slide, "①", "②") for run in shape.text_frame.paragraphs[0].runs}
             for slide in slides]
    assert sizes[0] == sizes[1] and len(sizes[0]) == 1


def test_long_few_choices_take_the_full_width(tmp_path):
    slides, _ = build(tmp_path, [{"type": "check", "question": "문제", "truth": True, "answer": 0,
                                  "reasons": ["입자는 스스로 끊임없이 움직이기 때문이다", "둘째"]}])
    assert boxes(slides[0], "①")[0].width == boxes(slides[0], "②")[0].width
    assert boxes(slides[0], "①")[0].width > Inches(make_deck.BODY_W - 0.1)


def test_callouts_follow_the_points_from_top_to_bottom_so_lines_do_not_cross(tmp_path):
    png(tmp_path / "그림.png", 400, 400)
    slides, _ = build(tmp_path, [{"type": "figure", "title": "그림", "image": "그림.png",
                                  "callouts": [{"text": "아래", "x": 0.5, "y": 0.9}, {"text": "위", "x": 0.5, "y": 0.1}]}])
    assert boxes(slides[0], "위")[0].top < boxes(slides[0], "아래")[0].top


def test_text_at_the_smallest_size_warns_once_per_slide(tmp_path):
    rows = [["가" * 200, "나" * 200], ["다" * 200, "라" * 200]]
    _, warnings = build(tmp_path, [{"type": "table", "title": "표", "header": ["가", "나"], "rows": rows, "notes": "말"}])
    assert len(warnings) == 1 and "1번째 장" in warnings[0]


def test_main_reports_errors_and_warnings_in_korean(tmp_path, capsys):
    bad = tmp_path / "나쁨.json"
    bad.write_text(json.dumps({**CYCLE, "slides": [{"type": "wave"}]}), encoding="utf-8")
    assert make_deck.main([str(bad), str(tmp_path / "a.pptx")]) == 1
    assert "wave" in capsys.readouterr().out

    good = tmp_path / "좋음.json"
    good.write_text(json.dumps({**CYCLE, "slides": [{"type": "summary", "items": ["가"]}]}), encoding="utf-8")
    assert make_deck.main([str(good), str(tmp_path / "b.pptx")]) == 0
    assert "확인 필요" in capsys.readouterr().out


def test_broken_picture_is_reported_in_korean(tmp_path, capsys):
    (tmp_path / "bad.png").write_bytes(b"not an image")
    slide = {"type": "figure", "title": "그림", "image": "bad.png", "notes": "노트"}
    source = tmp_path / "in.json"
    source.write_text(json.dumps({"subject": "과학", "unit": "단원", "slides": [slide]}), encoding="utf-8")
    assert make_deck.main([str(source), str(tmp_path / "a.pptx")]) == 1
    assert "그림 파일을 열 수 없음" in capsys.readouterr().out


def test_missing_output_folder_is_reported_in_korean(tmp_path, capsys):
    source = tmp_path / "in.json"
    deck = {"subject": "과학", "unit": "단원", "slides": [{"type": "cover", "title": "제목"}]}
    source.write_text(json.dumps(deck), encoding="utf-8")
    assert make_deck.main([str(source), str(tmp_path / "없는폴더" / "a.pptx")]) == 1
    assert "입력 오류" in capsys.readouterr().out


# ---- 실제 시험에서 나온 결함: 행 높이 배분, 글자 폭 여유, 주기 안내 점검 ----

def font_sizes(slide):
    return {run.font.size.pt for run in runs(slide) if run.font.size}


def test_one_row_with_sub_items_does_not_shrink_the_other_rows(tmp_path):
    items = ["첫째 항목", "둘째 항목", "셋째 항목", {"text": "넷째 항목", "sub": ["하위 하나", "하위 둘", "하위 셋"]}]
    slides, warnings = build(tmp_path, [{"type": "content", "title": "설명", "items": items, "notes": "말"}])
    assert len(slides) == 1 and not warnings
    assert min(font_sizes(slides[0])) >= make_deck.CLASSROOM_FONT


def test_rows_get_height_in_proportion_to_their_lines(tmp_path):
    items = ["짧다", {"text": "길다", "sub": ["하나", "둘", "셋"]}]
    slides, _ = build(tmp_path, [{"type": "content", "title": "설명", "items": items, "notes": "말"}])
    rows = sorted((s for s in slides[0].shapes if s.has_text_frame and s.text_frame.text in ("짧다", "길다\n하나\n둘\n셋")),
                  key=lambda s: s.top)
    assert len(rows) == 2 and rows[1].height > rows[0].height * 1.8


def test_heavy_rows_split_into_more_slides_instead_of_tiny_text(tmp_path):
    items = [{"text": f"항목 {n}", "sub": ["하위 하나", "하위 둘", "하위 셋"]} for n in range(5)]
    slides, _ = build(tmp_path, [{"type": "content", "title": "설명", "items": items, "notes": "말"}])
    assert len(slides) > 1
    assert "(계속)" in slide_text(slides[1])
    assert all(min(font_sizes(slide)) >= make_deck.CLASSROOM_FONT for slide in slides)


def test_single_row_that_cannot_reach_classroom_size_warns_clearly(tmp_path):
    _, warnings = build(tmp_path, [{"type": "content", "title": "설명", "items": ["가" * 900], "notes": "말"}])
    assert any("교실 기준" in warning for warning in warnings)


def test_line_that_nearly_fills_the_box_is_treated_as_wrapping(tmp_path):
    one_line = 30 * make_deck.LINE_RATIO / 72 + 2 * make_deck.VPAD
    assert make_deck.fit_size("가가가가가ab", 3, one_line, 30) < 30       # 6.1칸 어치: 상자 끝까지 차므로 한 줄로 보지 않는다
    assert make_deck.fit_size("가가가가", 3, one_line, 30) == 30


def test_space_is_narrower_than_a_letter():
    assert make_deck.text_units("가 가") < make_deck.text_units("가가가")


OUTLINE = {"type": "outline", "items": ["첫째 주기", "둘째 주기"], "notes": "말"}


def test_outline_without_a_slide_for_each_cycle_warns(tmp_path):
    _, warnings = build(tmp_path, [{**OUTLINE, "current": 0}])
    assert any("수업 안내" in warning and "둘째 주기" in warning for warning in warnings)


def test_outline_for_every_cycle_gives_no_warning(tmp_path):
    _, warnings = build(tmp_path, [{**OUTLINE, "current": 0}, {**OUTLINE, "current": 1}])
    assert not any("수업 안내" in warning for warning in warnings)


def test_several_sections_without_any_outline_warn(tmp_path):
    sections = [{"type": "section", "title": f"{n}. 소주제", "notes": "말"} for n in (1, 2)]
    _, warnings = build(tmp_path, sections)
    assert any("수업 안내" in warning for warning in warnings)


def test_a_few_stray_letters_on_the_last_line_shrink_the_font_slightly():
    text = "가" * 27                                       # 한 줄이 26칸쯤: 조금만 넘쳐 끝 줄에 몇 글자만 남는다
    width = 10.9
    assert make_deck.has_short_tail(text, width, 27)
    tidy = make_deck.tidy_size(text, width, 1.5, 27)
    assert make_deck.MIN_FONT <= tidy < 27 and not make_deck.has_short_tail(text, width, tidy)
    assert make_deck.fit_size(text, width, 1.5, 27) == 27       # 칸에 들어가기만 하면 fit_size는 그대로 둔다
