"""학생용 사본(--student), 입력 형식 오류, 그림 경로, 양식 모양 지키기 시험."""
import io
import json
from contextlib import redirect_stdout

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Pt

import fill_template
import make_deck
import make_pptx
from make_deck_check import read_input_json
from test_fill_template import make_template as make_fill_template
from test_make_pptx_template import make_template as make_theme_template

ANSWER_TEXTS = ("첫째 답", "문제의 답", "정답을 확인해", "왜 맞고 왜 틀린가", "✔")

DECK_DOC = {"subject": "과학", "unit": "단원", "slides": [
    {"type": "cover", "title": "제목"},
    {"type": "check", "question": "맞는 것은?", "choices": ["가", "나", "다"], "answer": 1,
     "explain": "왜 맞고 왜 틀린가", "notes": "정답은 나. 절반 넘게 틀리면 앞으로 돌아간다."},
    {"type": "check", "question": "참일까요?", "truth": False, "reasons": ["까닭 하나", "까닭 둘"], "answer": 1,
     "notes": "거짓, 근거 둘"},
    {"type": "task", "title": "연습", "steps": ["첫째 일"], "minutes": 3, "output": "공책",
     "answer": ["첫째 답"], "notes": "예상 답 첫째 답"},
    {"type": "example", "title": "예제", "worked": {"lines": ["풀이"]}, "problem": {"lines": ["문제"]},
     "answer": ["문제의 답"], "notes": "답은 문제의 답"},
    {"type": "summary", "items": ["정리"], "notes": "정리 노트"},
]}
PPTX_DOC = {"theme": "basic", "slides": [
    {"type": "quiz", "question": "문제", "choices": ["가", "나"], "answer": 1, "reveal": True,
     "notes": "말할 내용", "reveal_notes": "정답 뒤 행동"},
    {"type": "summary", "items": ["정리"], "notes": "정리 노트"},
]}


def all_text(prs):
    return "\n".join(shape.text_frame.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame)


def all_notes(prs):
    return "".join(slide.notes_slide.notes_text_frame.text for slide in prs.slides if slide.has_notes_slide)


def run_main(module, args):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = module.main(args)
    return code, buffer.getvalue()


def write_json(path, doc):
    path.write_text(doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------- 학생용 사본

def test_deck_student_copy_has_no_answer_slides_or_notes(tmp_path):
    normal, student = tmp_path / "n.pptx", tmp_path / "s.pptx"
    make_deck.build_deck(DECK_DOC, normal, tmp_path)
    make_deck.build_deck(DECK_DOC, student, tmp_path, student=True)
    assert any(word in all_text(Presentation(normal)) + all_notes(Presentation(normal)) for word in ANSWER_TEXTS)
    copy = Presentation(student)
    assert len(copy.slides) < len(Presentation(normal).slides)
    assert not any(word in all_text(copy) for word in ANSWER_TEXTS)
    assert all_notes(copy) == ""
    assert "발표자 노트가 없음" not in " ".join(make_deck.build_deck(DECK_DOC, student, tmp_path, student=True))


def test_pptx_student_copy_has_no_answer_slide_or_notes(tmp_path):
    normal, student = tmp_path / "n.pptx", tmp_path / "s.pptx"
    make_pptx.build_pptx(PPTX_DOC, normal)
    make_pptx.build_pptx(PPTX_DOC, student, student=True)
    assert len(Presentation(normal).slides) == len(Presentation(student).slides) + 1
    copy = Presentation(student)
    assert "정답" not in all_text(copy)
    assert all_notes(copy) == ""
    assert "정답" in all_notes(Presentation(normal))


def test_same_input_gives_same_student_behavior_in_both_generators(tmp_path):
    deck_in = write_json(tmp_path / "d.json", {**DECK_DOC, "slides": DECK_DOC["slides"][:2]})
    pptx_in = write_json(tmp_path / "p.json", {"theme": "basic", "slides": [
        {"type": "quiz", "question": "맞는 것은?", "choices": ["가", "나", "다"], "answer": 1, "reveal": True,
         "notes": "정답은 나"}]})
    assert run_main(make_deck, [str(deck_in), str(tmp_path / "d.pptx"), "--student"])[0] == 0
    assert run_main(make_pptx, [str(pptx_in), str(tmp_path / "p.pptx"), "--student"])[0] == 0
    for name in ("d.pptx", "p.pptx"):
        copy = Presentation(tmp_path / name)
        assert all_notes(copy) == "" and "정답" not in all_text(copy), name


@pytest.mark.parametrize("module", [make_deck, make_pptx])
def test_unknown_option_prints_usage(module, tmp_path):
    code, output = run_main(module, ["a.json", "b.pptx", "--other"])
    assert code == 2 and "사용법" in output and "--student" in output


# ---------------------------------------------------------------- make_deck 입력 형식

def bad_deck(slides):
    return {"subject": "과학", "unit": "단원", "slides": slides}


@pytest.mark.parametrize("doc, expected", [
    ([1, 2], "최상위는 {...} 객체"),
    (bad_deck(["글자"]), "1번째 장"),
    (bad_deck([{"type": "cover", "title": "제목"}, {"type": "goals", "items": "목표 하나"}]), "2번째 장(goals): items는 목록"),
    (bad_deck([{"type": "table", "title": "표", "header": ["가"], "rows": [["나", "다"]]}]), "칸이 2개로 header(1개)보다 많음"),
    (bad_deck([{"type": "content", "title": 5, "items": ["가"]}]), "title는 글자여야 함"),
    (bad_deck([{"type": "flow", "title": "흐름", "steps": ["문자열"]}]), "steps의 1번째 항목"),
])
def test_deck_format_errors_are_korean_and_name_the_slide(tmp_path, doc, expected):
    with pytest.raises(ValueError) as caught:
        make_deck.build_deck(doc, tmp_path / "a.pptx", tmp_path)
    message = str(caught.value)
    assert expected in message
    assert not any(word in message for word in ("TypeError", "object", "has no attribute", "NoneType"))


def test_type_error_text_is_not_leaked_in_english(tmp_path):
    doc = bad_deck([{"type": "cover", "title": "제목"}, {"type": "quiz", "question": "문제", "choices": ["가", "나"], "answer": "0"}])
    with pytest.raises(ValueError) as caught:
        make_deck.build_deck(doc, tmp_path / "a.pptx", tmp_path)
    assert "2번째 장" in str(caught.value) and "int" not in str(caught.value)


def test_json_syntax_error_reports_line_and_column(tmp_path):
    source = write_json(tmp_path / "깨짐.json", '{\n  "subject": "과학",\n  "slides": [\n')
    with pytest.raises(ValueError, match=r"JSON 문법 오류: \d+번째 줄 \d+번째 글자 근처"):
        read_input_json(source)
    for module in (make_deck, make_pptx):
        code, output = run_main(module, [str(source), str(tmp_path / "a.pptx")])
        assert code == 1 and "JSON 문법 오류" in output and "Expecting" not in output
    code, output = run_main(fill_template, [str(source), str(tmp_path / "a.pptx")])
    assert code == 1 and "JSON 문법 오류" in output


def test_main_prints_everything_to_standard_output(tmp_path, capsys):
    source = write_json(tmp_path / "in.json", bad_deck([{"type": "summary", "items": ["가"]}]))
    assert make_deck.main([str(source), str(tmp_path / "a.pptx")]) == 0
    captured = capsys.readouterr()
    assert "완료" in captured.out and "확인 필요" in captured.out and captured.err == ""


def test_deck_output_must_be_pptx_and_not_the_input(tmp_path):
    source = write_json(tmp_path / "in.json", bad_deck([{"type": "summary", "items": ["가"]}]))
    assert run_main(make_deck, [str(source), str(tmp_path / "a.txt")])[0] == 1
    assert run_main(make_deck, [str(source), str(source)])[0] == 1


# ---------------------------------------------------------------- make_pptx 입력 맞추기

def png(path, size=(60, 40)):
    Image.new("RGB", size, (10, 90, 160)).save(path)
    return path


def test_pptx_figure_path_is_relative_to_the_json_folder(tmp_path, monkeypatch):
    folder = tmp_path / "자료"
    folder.mkdir()
    png(folder / "그림.png")
    source = write_json(folder / "in.json", {"theme": "basic", "slides": [
        {"type": "figure", "title": "그림", "image": "그림.png", "caption": "교과서 32쪽"}]})
    elsewhere = tmp_path / "다른곳"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    code, output = run_main(make_pptx, [str(source), str(folder / "out.pptx")])
    assert code == 0, output
    pictures = [s for s in Presentation(folder / "out.pptx").slides[0].shapes if s.shape_type == 13]
    assert len(pictures) == 1


def test_pptx_missing_figure_is_reported_in_korean(tmp_path):
    source = write_json(tmp_path / "in.json", {"theme": "basic", "slides": [
        {"type": "summary", "items": ["가"]}, {"type": "figure", "title": "그림", "image": "없는그림.png"}]})
    code, output = run_main(make_pptx, [str(source), str(tmp_path / "out.pptx")])
    assert code == 1 and "2번 슬라이드(figure)" in output and "그림 파일을 찾을 수 없음" in output


def test_pptx_compare_accepts_head_like_make_deck(tmp_path):
    out = tmp_path / "a.pptx"
    make_pptx.build_pptx({"theme": "basic", "slides": [
        {"type": "compare", "title": "비교", "left": {"head": "왼쪽머리", "items": ["가"]},
         "right": {"heading": "오른쪽머리", "items": ["나"]}}]}, out)
    text = all_text(Presentation(out))
    assert "왼쪽머리" in text and "오른쪽머리" in text


def test_pptx_activity_draws_roles_and_output(tmp_path):
    out = tmp_path / "a.pptx"
    make_pptx.build_pptx({"theme": "basic", "slides": [
        {"type": "activity", "title": "활동", "time": "20분", "group": "4명 모둠", "roles": "기록, 발표",
         "materials": "비커", "output": "결과표", "steps": ["준비한다"]}]}, out)
    text = all_text(Presentation(out))
    for word in ("역할", "기록, 발표", "산출물", "결과표", "시간", "20분"):
        assert word in text


def test_pptx_overflow_warning_is_not_repeated_by_the_polish_step(tmp_path):
    long = "가나다라 " * 120
    warnings = make_pptx.build_pptx({"theme": "basic", "slides": [
        {"type": "cards", "title": "카드", "cards": [{"head": "가", "text": long}, {"head": "나", "text": long}]}]},
        tmp_path / "a.pptx")
    assert len([w for w in warnings if "넘칠" in w]) == 1


# ---------------------------------------------------------------- 양식 모양 지키기 (make_pptx 템플릿)

def test_template_title_keeps_the_template_look(tmp_path):
    template = make_theme_template(tmp_path / "t.pptx")
    out = tmp_path / "a.pptx"
    make_pptx.build_pptx({"theme": "basic", "template": template, "slides": [
        {"type": "content", "title": "양식 제목", "items": ["가"]}]}, out)
    title = Presentation(out).slides[0].shapes.title
    for run in title.text_frame.paragraphs[0].runs:
        assert run.font.size is None and run.font.bold is None and run.font.name is None
        assert run.font.color.type is None
    assert title.text_frame.text == "양식 제목"


def test_template_cover_and_section_use_the_template_layouts(tmp_path):
    template = make_theme_template(tmp_path / "t.pptx")
    out = tmp_path / "a.pptx"
    make_pptx.build_pptx({"theme": "basic", "template": template, "slides": [
        {"type": "cover", "title": "표지 제목", "unit": "단원", "meta": "중2 · 1차시"},
        {"type": "section", "title": "소주제", "subtitle": "짧은 구"}]}, out)
    cover, section = Presentation(out).slides
    assert cover.slide_layout.name == "Title Slide" and section.slide_layout.name == "Section Header"
    assert cover.shapes.title.text_frame.text == "표지 제목"
    assert "중2 · 1차시" in all_text(Presentation(out)) and "짧은 구" in all_text(Presentation(out))
    assert not [ph for ph in cover.placeholders if not ph.has_text_frame or not ph.text_frame.text.strip()]


def test_without_template_the_generator_still_sets_its_own_font(tmp_path):
    out = tmp_path / "a.pptx"
    make_pptx.build_pptx({"theme": "basic", "slides": [{"type": "content", "title": "제목", "items": ["가"]}]}, out)
    run = Presentation(out).slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    assert run.font.name == "맑은 고딕" and run.font.size is not None


# ---------------------------------------------------------------- fill_template

def paragraphs_template(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = 18288000, 10287000
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(1000000, 1000000, 12000000, 4000000)
    box.name = "본문"
    for index, (text, size, bold) in enumerate([("큰 머리", 40, True), ("작은 글", 20, False)]):
        paragraph = box.text_frame.paragraphs[0] if index == 0 else box.text_frame.add_paragraph()
        run = paragraph.add_run()
        run.text, run.font.size, run.font.bold = text, Pt(size), bold
    other = slide.shapes.add_textbox(1000000, 6000000, 6000000, 800000)
    other.name = "남는 글"
    other.text_frame.text = "양식에 있던 글"
    prs.save(str(path))
    return str(path)


def fill(tmp_path, slide_spec):
    template = paragraphs_template(tmp_path / "양식.pptx")
    out = tmp_path / "out.pptx"
    warnings = fill_template.build({"template": template, "slides": [slide_spec]}, out)
    return Presentation(out), warnings


def test_each_new_paragraph_follows_the_matching_template_paragraph(tmp_path):
    prs, _ = fill(tmp_path, {"from": 1, "text": {"본문": ["제목글", "둘째", "셋째"]}, "remove": ["남는 글"]})
    box = next(s for s in prs.slides[0].shapes if s.name == "본문")
    sizes = [p.runs[0].font.size.pt for p in box.text_frame.paragraphs]
    assert sizes == [40, 20, 20]       # 셋째는 모자라서 마지막 양식 문단의 모양
    assert box.text_frame.paragraphs[0].runs[0].font.bold is True
    assert box.text_frame.paragraphs[1].runs[0].font.bold is not True


def test_leftover_template_text_is_warned(tmp_path):
    _, warnings = fill(tmp_path, {"from": 1, "text": {"본문": ["가", "나"]}})
    assert any("양식 원래 글이 남음" in w and "양식에 있던 글" in w and "남는 글" in w for w in warnings)
    assert not any("'본문'" in w and "양식 원래 글" in w for w in warnings)


def test_leftover_warning_goes_away_when_text_or_remove_handles_it(tmp_path):
    for fix in ({"text": {"본문": ["가"], "남는 글": "새 글"}}, {"text": {"본문": ["가"]}, "remove": ["남는 글"]}):
        _, warnings = fill(tmp_path, {"from": 1, **fix})
        assert not any("양식 원래 글" in w for w in warnings)


def test_empty_text_list_is_rejected_with_remove_hint(tmp_path):
    template = paragraphs_template(tmp_path / "양식.pptx")
    spec = write_json(tmp_path / "in.json", {"template": template, "slides": [{"from": 1, "text": {"본문": []}}]})
    code, output = run_main(fill_template, [str(spec), str(tmp_path / "out.pptx")])
    assert code == 1 and "remove" in output and "빈 목록" in output


def test_template_font_prefers_the_east_asian_typeface(tmp_path):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(0, 0, 1000000, 500000)
    run = box.text_frame.paragraphs[0].add_run()
    run.text, run.font.size, run.font.name = "글", Pt(60), "Arial"
    props = run._r.get_or_add_rPr()
    ea = props.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}ea", {"typeface": "나눔고딕"})
    props.find("{http://schemas.openxmlformats.org/drawingml/2006/main}latin").addnext(ea)
    assert fill_template._template_font(prs) == "나눔고딕"


def test_fill_template_fixture_still_builds(tmp_path):
    template = make_fill_template(tmp_path)
    warnings = fill_template.build({"template": str(template), "slides": [{"from": 1, "text": {"제목": "새 제목"},
                                                                          "remove": ["배경"]}]}, tmp_path / "o.pptx")
    assert isinstance(warnings, list)
