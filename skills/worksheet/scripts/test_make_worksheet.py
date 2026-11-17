"""학습지 폼 생성기 시험."""
import json
import zipfile
from pathlib import Path

import pytest

import make_worksheet

DOC = {"subject": "수학", "unit": "방정식", "title": "제목", "goal": "목표", "activities": [
    {"title": "활동", "parts": [{"kind": "lines", "count": 2}, {"kind": "labels", "rows": [["가설", 2], ["문제", "글"]]}]}]}

# 학생용 파일에 나오면 안 되는 글. 칸 종류마다 하나씩 둔다
SECRETS = ["비밀빈칸", "비밀줄답", "비밀공간", "비밀라벨", "비밀표답", "비밀단계", "비밀틀답", "비밀도전",
           "비밀예시", "비밀인정", "비밀채점", "비밀지도", "비밀시간", "비밀교육과정", "비밀성취기준", "비밀제목빈칸"]
FULL = {
    "subject": "과학", "unit": "식물", "title": "광합성 [[비밀제목빈칸]]", "goal": "목표", "question": "질문",
    "curriculum": "비밀교육과정", "standards": ["비밀성취기준"], "check": ["나는 설명할 수 있다."],
    "activities": [{
        "title": "활동 하나", "time": "비밀시간", "model": "비밀예시", "accept": "비밀인정", "point": "비밀채점",
        "tip": "비밀지도",
        "parts": [
            {"kind": "text", "text": "식물은 [[비밀빈칸]]을/를 한다."},
            {"kind": "hint", "text": "빛을 떠올려 보세요."},
            {"kind": "choices", "items": ["광합성", "호흡"], "answer": "광합성"},
            {"kind": "lines", "count": 2, "answer": "비밀줄답"},
            {"kind": "space", "lines": 4, "label": "풀이", "answer": "비밀공간"},
            {"kind": "labels", "rows": [["가설", {"answer": "비밀라벨", "lines": 2}], ["문제", "글"]]},
            {"kind": "grid", "header": ["구분", "답"], "rows": [["가", {"answer": "비밀표답"}], ["나", "글"]]},
            {"kind": "steps", "items": ["관찰한다", {"text": "기록한다", "lines": 2, "answer": "비밀단계"}]},
            {"kind": "frame", "starter": "내 생각에는", "lines": 2, "answer": "비밀틀답"},
            {"kind": "challenge", "text": "새 상황에 적용해 보세요.", "lines": 2, "answer": "비밀도전"},
        ]}],
}
BLUE = make_worksheet.ANSWER_COLOR
HEAD_BLOCKS = 3         # 머리 띠, 이름 줄, 목표 표
PART_BLOCK = HEAD_BLOCKS + 1


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def write_json(folder, doc):
    path = folder / "in.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


def cells(spec):
    return [cell for block in spec["blocks"] if block["type"] == "table" for row in block["rows"] for cell in row]


def one_part(part, teacher=False):
    doc = {**DOC, "closing": "none", "activities": [{"title": "활동", "parts": [part]}]}
    return make_worksheet.build_spec(doc, teacher=teacher)


def part_cells(part, teacher=False):
    """머리표와 활동 소제목을 뺀, 그 칸의 표에 든 칸들."""
    block = one_part(part, teacher)["blocks"][PART_BLOCK]
    return [cell for row in block["rows"] for cell in row]


def shape(spec):
    """글을 뺀 칸 구성: 블록 종류, 열 비율, 행마다 칸의 줄 수와 합친 칸 수."""
    return [(block["type"], block.get("widths"),
             [[(cell.get("lines", 0), cell.get("colspan", 1)) for cell in row] for row in block.get("rows", [])])
            for block in spec["blocks"] if not block.get("teacher_only")]


@pytest.mark.parametrize("subject", ["국어", "영어", "수학", "사회", "과학", "음악"])
def test_every_subject_uses_the_same_navy_band(subject):
    band = make_worksheet.build_spec({**DOC, "subject": subject})["blocks"][0]["rows"][0][0]
    assert band["fill"] == make_worksheet.NAVY == "#1F3F7A"


def test_no_per_subject_palette_is_left():
    assert not hasattr(make_worksheet, "PALETTES") and not hasattr(make_worksheet, "DEFAULT_PALETTE")


def test_activity_label_cells_use_tint_blue_with_navy_text():
    label = part_cells({"kind": "space", "label": "풀이"})[0]
    assert label["fill"] == make_worksheet.TINT and label["color"] == make_worksheet.NAVY


def test_all_tables_get_compact_gap_unless_set():
    tables = [b for b in make_worksheet.build_spec(DOC)["blocks"] if b["type"] == "table"]
    assert tables[0]["gap"] == "tight" and tables[-1]["gap"] == "small"


def test_missing_required_value_is_refused():
    with pytest.raises(ValueError, match="goal"):
        make_worksheet.build_spec({**DOC, "goal": ""})


def test_unknown_part_is_refused():
    bad = {**DOC, "activities": [{"title": "활동", "parts": [{"kind": "wave"}]}]}
    with pytest.raises(ValueError, match="wave"):
        make_worksheet.build_spec(bad)


def test_writes_valid_hwpx(tmp_path):
    out = tmp_path / "a.hwpx"
    make_worksheet.make_hwpx.build_hwpx(make_worksheet.build_spec(DOC), out)
    assert out.stat().st_size > 0


def test_table_text_and_paragraphs_are_centered_by_default():
    doc = {**DOC, "activities": [{"title": "활동", "parts": [
        {"kind": "text", "text": "지시문"}, {"kind": "grid", "header": ["가"], "rows": [["나"]]}]}]}
    blocks = make_worksheet.build_spec(doc)["blocks"]
    table_cells = [cell for block in blocks if block["type"] == "table" for row in block["rows"] for cell in row]
    paragraphs = [block for block in blocks if block["type"] == "paragraph"]
    assert all(cell["align"] == "center" for cell in table_cells)
    assert paragraphs and all(block["align"] == "center" for block in paragraphs)


@pytest.mark.parametrize("teacher", [False, True])
def test_every_new_cell_kind_is_centered_in_both_versions(teacher):
    spec = make_worksheet.build_spec(FULL, teacher=teacher)
    assert all(cell["align"] == "center" for cell in cells(spec))
    assert all(block["align"] == "center" for block in spec["blocks"] if block["type"] == "paragraph")


def test_grid_number_cell_is_printed_as_text():
    grid = {"kind": "grid", "header": ["가"], "rows": [[3]]}
    assert part_cells(grid)[-1]["text"] == 3


# ---------------------------------------------------------------- 학생용에 답이 새지 않음

def test_student_spec_has_no_answer_or_teacher_text():
    found = [secret for text in strings(make_worksheet.build_spec(FULL)) for secret in SECRETS if secret in text]
    assert found == []


def test_student_file_has_no_answer_anywhere_in_package(tmp_path):
    out = tmp_path / "student.hwpx"
    assert make_worksheet.main([str(write_json(tmp_path, FULL)), str(out)]) == 0
    with zipfile.ZipFile(out) as package:
        contents = {name: package.read(name).decode("utf-8", "ignore") for name in package.namelist()}
    found = [(name, secret) for name, text in contents.items() for secret in SECRETS if secret in text]
    assert found == []


def test_student_file_has_no_answer_color(tmp_path):
    out = tmp_path / "student.hwpx"
    make_worksheet.main([str(write_json(tmp_path, FULL)), str(out)])
    with zipfile.ZipFile(out) as package:
        assert f'textColor="{BLUE}"' not in package.read("Contents/header.xml").decode()


def test_student_choices_do_not_mark_the_answer():
    box = part_cells({"kind": "choices", "items": ["빛", "물"], "answer": "빛"})[-1]
    assert "**" not in box["text"] and "mark_color" not in box


def test_blank_width_does_not_reveal_answer_length():
    short = part_cells({"kind": "frame", "text": "[[빛]]"})[-1]["text"]
    long = part_cells({"kind": "frame", "text": "[[엽록체의 틸라코이드]]"})[-1]["text"]
    assert short == long == make_worksheet.BLANK


# ---------------------------------------------------------------- 교사용은 같은 칸

def test_teacher_has_same_cells_as_student():
    assert shape(make_worksheet.build_spec(FULL, teacher=True)) == shape(make_worksheet.build_spec(FULL))


def test_teacher_only_blocks_appear_only_in_teacher_version():
    assert [b for b in make_worksheet.build_spec(FULL, teacher=True)["blocks"] if b.get("teacher_only")]
    assert not [b for b in make_worksheet.build_spec(FULL)["blocks"] if b.get("teacher_only")]


def test_teacher_shows_every_answer():
    text = "\n".join(strings(make_worksheet.build_spec(FULL, teacher=True)))
    assert [secret for secret in SECRETS if secret not in text] == []


def test_teacher_band_says_teacher_version():
    assert "교사용" in make_worksheet.build_spec(DOC, teacher=True)["blocks"][0]["rows"][0][0]["text"]
    assert "교사용" not in make_worksheet.build_spec(DOC)["blocks"][0]["rows"][0][0]["text"]


@pytest.mark.parametrize("part", [
    {"kind": "space", "answer": "답글"},
    {"kind": "lines", "count": 1, "answer": "답글"},
    {"kind": "labels", "rows": [["가", {"answer": "답글"}]]},
    {"kind": "grid", "header": ["가"], "rows": [[{"answer": "답글"}]]},
    {"kind": "steps", "items": [{"text": "가", "answer": "답글"}]},
    {"kind": "challenge", "text": "가", "answer": "답글"},
])
def test_answer_in_own_cell_is_blue_and_bold(part):
    cell = next(cell for cell in part_cells(part, teacher=True) if cell["text"] == "답글")
    assert cell["color"] == BLUE and cell["bold"] is True


@pytest.mark.parametrize("part", [
    {"kind": "text", "text": "식물은 [[답글]]을/를 한다."},
    {"kind": "frame", "text": "식물은 [[답글]]을/를 한다."},
    {"kind": "frame", "starter": "내 생각에는", "answer": "답글"},
    {"kind": "choices", "items": ["답글", "다른 말"], "answer": "답글"},
    {"kind": "grid", "header": ["가"], "rows": [["식물은 [[답글]]을/를 한다."]]},
])
def test_answer_inside_sentence_is_marked_blue(part):
    cell = next(cell for cell in part_cells(part, teacher=True) if "답글" in str(cell["text"]))
    assert "**답글**" in cell["text"] and cell["mark_color"] == BLUE


def test_sentence_with_blank_has_same_shape_in_both_versions():
    part = {"kind": "text", "text": "식물은 [[답글]]을/를 한다."}
    assert shape(one_part(part)) == shape(one_part(part, teacher=True))


def test_long_answer_goes_to_model_answer_cell_right_after_activity():
    doc = {**DOC, "activities": [{"title": "활동", "model": "길게 쓴 예시", "parts": [{"kind": "space"}]},
                                 {"title": "다음", "parts": [{"kind": "lines", "count": 1}]}]}
    blocks = make_worksheet.build_spec(doc, teacher=True)["blocks"]
    note = next(index for index, block in enumerate(blocks) if block.get("teacher_only"))
    assert blocks[note]["rows"][0][0]["text"] == "예시 답안"
    assert blocks[note]["rows"][0][1]["color"] == BLUE
    assert blocks[note + 1]["rows"][0][1]["text"] == "다음"


@pytest.mark.parametrize("part", [{"kind": "space", "answer": 0}, {"kind": "frame", "starter": "값은", "answer": 0}])
def test_zero_is_a_real_answer(part):
    assert any("0" in str(cell["text"]) for cell in part_cells(part, teacher=True))
    assert make_worksheet.unanswered({**DOC, "activities": [{"title": "가", "parts": [part]}]}) == []


def test_multi_line_answer_stays_in_given_rows():
    part = {"kind": "lines", "count": 2, "answer": "첫 줄\n둘째 줄\n셋째 줄"}
    assert [cell["text"] for cell in part_cells(part, teacher=True)] == ["첫 줄", "둘째 줄\n셋째 줄"]


def test_teacher_head_has_curriculum_and_standards():
    doc = {**DOC, "curriculum": "2022 개정", "standards": ["[9수01-01] 문장", "[9수01-02] 문장"]}
    head = next(block for block in make_worksheet.build_spec(doc, teacher=True)["blocks"] if block.get("teacher_only"))
    assert [row[1]["text"] for row in head["rows"]] == ["2022 개정", "[9수01-01] 문장\n[9수01-02] 문장"]


def test_unanswered_counts_open_cells_per_activity():
    doc = {**DOC, "activities": [
        {"title": "가", "parts": [{"kind": "space"}, {"kind": "text", "text": "식물은 (        )을 한다."}]},
        {"title": "나", "model": "예시", "parts": [{"kind": "space"}]},
        {"title": "다", "parts": [{"kind": "lines", "count": 1, "answer": "답"}]}]}
    assert make_worksheet.unanswered(doc) == ["활동 1: 답이 없는 칸 2곳"]


def test_unanswered_sees_empty_cells_in_tables_and_steps():
    doc = {**DOC, "activities": [{"title": "가", "parts": [
        {"kind": "labels", "rows": [["가", 2], ["나", "인쇄된 글"], ["다", {"answer": "답"}]]},
        {"kind": "grid", "header": ["가"], "rows": [[""], ["글"], [{"lines": 2}]]},
        {"kind": "steps", "items": ["할 일", {"text": "쓰기", "lines": 2}]}]}]}
    assert make_worksheet.unanswered(doc) == ["활동 1: 답이 없는 칸 4곳"]


def test_full_doc_has_no_unanswered_cells():
    assert make_worksheet.unanswered(FULL) == []


# ---------------------------------------------------------------- 명령줄

def test_cli_teacher_flag_writes_blue_answers(tmp_path):
    source, out = write_json(tmp_path, FULL), tmp_path / "t.hwpx"
    assert make_worksheet.main([str(source), str(out), "--teacher"]) == 0
    with zipfile.ZipFile(out) as package:
        assert "비밀표답" in package.read("Contents/section0.xml").decode()
        assert f'textColor="{BLUE}"' in package.read("Contents/header.xml").decode()


def test_cli_warns_about_unanswered_cells_only_for_teacher(tmp_path, capsys):
    doc = {**DOC, "activities": [{"title": "가", "parts": [{"kind": "space"}]}]}
    source, out = write_json(tmp_path, doc), tmp_path / "t.hwpx"
    make_worksheet.main([str(source), str(out)])
    assert capsys.readouterr().err == ""
    make_worksheet.main([str(source), str(out), "--teacher"])
    assert "활동 1" in capsys.readouterr().err


def test_cli_without_paths_shows_usage(capsys):
    assert make_worksheet.main(["--teacher"]) == 2
    assert "--teacher" in capsys.readouterr().err


# ---------------------------------------------------------------- 새 칸 종류

def test_space_is_empty_box_with_given_height():
    cell = part_cells({"kind": "space", "lines": 6})[-1]
    assert cell["text"] == "" and cell["lines"] == 6


def test_space_label_sits_in_left_cell():
    label, box = part_cells({"kind": "space", "label": "풀이", "lines": 6})
    assert label["text"] == "풀이" and box["lines"] == 6


def test_frame_starter_is_gray_first_sentence():
    cell = part_cells({"kind": "frame", "starter": "내 생각에는", "lines": 3})[-1]
    assert cell["text"] == "내 생각에는" and cell["color"] == make_worksheet.GRAY and cell["lines"] == 3


def test_frame_with_writing_room_starts_at_top_and_stays_centered():
    cell = part_cells({"kind": "frame", "starter": "내 생각에는", "lines": 3})[-1]
    assert cell["valign"] == "top" and cell["align"] == "center"


def test_frame_needs_text_or_starter():
    with pytest.raises(ValueError, match="frame"):
        one_part({"kind": "frame", "lines": 2})


def test_steps_number_each_row():
    rows = one_part({"kind": "steps", "items": ["관찰한다", "기록한다"]})["blocks"][PART_BLOCK]["rows"]
    assert [[cell["text"] for cell in row] for row in rows] == [["1단계", "관찰한다"], ["2단계", "기록한다"]]


def test_steps_keep_given_name_and_add_writing_column():
    part = {"kind": "steps", "items": [{"name": "예측", "text": "쓴다", "lines": 2}, "본다"]}
    rows = one_part(part)["blocks"][PART_BLOCK]["rows"]
    assert rows[0][0]["text"] == "예측" and rows[0][2]["lines"] == 2 and len(rows[1]) == 3


def test_hint_stays_with_next_part():
    block = one_part({"kind": "hint", "text": "도움"})["blocks"][PART_BLOCK]
    assert block["keep_with_next"] is True and block["rows"][0][0]["text"] == "도움말"


def test_choices_show_all_items_in_one_box():
    label, box = part_cells({"kind": "choices", "items": ["빛", "물"]})
    assert label["text"] == "보기" and "빛" in box["text"] and "물" in box["text"]


def test_challenge_has_task_row_and_full_width_writing_row():
    rows = one_part({"kind": "challenge", "text": "과제", "lines": 3})["blocks"][PART_BLOCK]["rows"]
    assert rows[0][0]["text"] == "도전 과제" and rows[0][1]["text"] == "과제"
    assert rows[1][0]["colspan"] == 2 and rows[1][0]["lines"] == 3


def test_challenge_does_not_show_level_name():
    text = " ".join(strings(one_part({"kind": "challenge", "text": "과제"})))
    assert not any(name in text for name in ("심화", "기초", "기본"))


def test_all_new_kinds_write_a_valid_file(tmp_path):
    out = tmp_path / "t.hwpx"
    make_worksheet.make_hwpx.build_hwpx(make_worksheet.build_spec(FULL, teacher=True), out)
    assert out.stat().st_size > 0


# ---------------------------------------------------------------- 마무리

def closing_text(**options):
    return [cell["text"] for cell in cells(make_worksheet.build_spec({**DOC, **options}))]


def test_default_closing_keeps_stars_and_reflection():
    text = closing_text(check=["나는 할 수 있다."])
    assert "스스로 평가" in text and make_worksheet.STARS in text and "오늘 새롭게 알게 된 점" in text


def test_default_closing_without_check_keeps_reflection_only():
    text = closing_text()
    assert "스스로 평가" not in text and "오늘 새롭게 알게 된 점" in text


def test_closing_none_removes_all_closing_tables():
    text = closing_text(check=["나는 할 수 있다."], closing="none")
    assert "스스로 평가" not in text and "오늘 새롭게 알게 된 점" not in text


def test_closing_check_keeps_star_table_only():
    text = closing_text(check=["나는 할 수 있다."], closing="check")
    assert make_worksheet.STARS in text and "오늘 새롭게 알게 된 점" not in text


def test_closing_reflect_keeps_reflection_only():
    text = closing_text(check=["나는 할 수 있다."], closing="reflect")
    assert "스스로 평가" not in text and "오늘 새롭게 알게 된 점" in text


def test_closing_reach_is_yes_no_check():
    text = closing_text(check=["나는 할 수 있다."], closing="reach")
    assert "예" in text and "아니요" in text and make_worksheet.STARS not in text


def test_unknown_closing_is_refused():
    with pytest.raises(ValueError, match="closing"):
        make_worksheet.build_spec({**DOC, "closing": "stars"})


@pytest.mark.parametrize("closing", ["check", "reach"])
def test_closing_with_items_needs_check_list(closing):
    with pytest.raises(ValueError, match="check"):
        make_worksheet.build_spec({**DOC, "closing": closing})


def test_bad_input_is_reported_in_korean_without_a_file(tmp_path, capsys):
    out = tmp_path / "a.hwpx"
    bad = {**DOC, "activities": [{"title": "활동", "parts": [{"kind": "card", "label": "개념"}]}]}
    assert make_worksheet.main([str(write_json(tmp_path, bad)), str(out)]) == 1
    assert "만들지 못함" in capsys.readouterr().err
    assert not out.exists()


def test_unreadable_json_is_reported_in_korean(tmp_path, capsys):
    source = tmp_path / "in.json"
    source.write_text("{", encoding="utf-8")
    assert make_worksheet.main([str(source), str(tmp_path / "a.hwpx")]) == 1
    assert "만들지 못함" in capsys.readouterr().err


def test_generator_warnings_reach_the_teacher(tmp_path, capsys):
    doc = {**DOC, "goal": "2026-03-02 수업 목표"}
    assert make_worksheet.main([str(write_json(tmp_path, doc)), str(tmp_path / "a.hwpx")]) == 0
    assert "주의:" in capsys.readouterr().err


# ---------------------------------------------------------------- 답이 수식일 때 색·굵기

EQUATION_DOC = {
    "subject": "수학", "unit": "방정식", "title": "수식 답", "goal": "목표", "closing": "none",
    "activities": [{"title": "활동", "parts": [
        {"kind": "grid", "header": ["식", "답"], "rows": [["가", {"answer": "{{x=2}}"}]]},
        {"kind": "choices", "items": ["{{x=1}}", "{{x=2}}"], "answer": "{{x=2}}"},
        {"kind": "frame", "text": "답은 [[{{x=3}}]] 이다"},
        {"kind": "grid", "header": ["{{y}}", "답"], "rows": [["나", ""]]},
    ]}],
}


def equations_in(tmp_path, teacher):
    from xml.etree import ElementTree
    out = tmp_path / ("t.hwpx" if teacher else "s.hwpx")
    args = [str(write_json(tmp_path, EQUATION_DOC)), str(out)] + (["--teacher"] if teacher else [])
    assert make_worksheet.main(args) == 0
    with zipfile.ZipFile(out) as package:
        section = ElementTree.fromstring(package.read("Contents/section0.xml"))
    hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
    return [(eq.find(f"{hp}script").text, eq.get("textColor")) for eq in section.iter(f"{hp}equation")]


def test_teacher_equation_answers_are_blue_and_bold(tmp_path):
    found = equations_in(tmp_path, teacher=True)
    assert ("bold {x=2}", BLUE) in found                      # 답 칸 (grid)
    assert found.count(("bold {x=2}", BLUE)) == 2             # 답 칸과 보기의 정답
    assert ("bold {x=3}", BLUE) in found                      # 문장 속 [[ ]] 답
    assert ("x=1", "#000000") in found                        # 정답이 아닌 보기는 그대로


def test_dark_header_equation_is_white(tmp_path):
    found = equations_in(tmp_path, teacher=False)
    assert ("bold {y}", "#FFFFFF") in found


def test_student_file_has_no_blue_equation(tmp_path):
    found = equations_in(tmp_path, teacher=False)
    assert all(color != BLUE for _, color in found)
    assert not any(script in ("bold {x=2}", "bold {x=3}") for script, _ in found)
    assert ("x=1", "#000000") in found


# ---------------------------------------------------------------- 개념 정리 학습지 (topics)

CONCEPT = {
    "subject": "한국사", "unit": "발전", "lesson": "주제 1", "title": "제목", "sub": "교과서 1쪽",
    "goal": ["① 목표 하나", "② 목표 둘"], "question": "핵심 질문?",
    "curriculum": "비밀교육과정", "standards": ["비밀성취기준"],
    "topics": [
        {"title": "주제 하나", "tag": "1961", "rows": [
            {"label": "정변", "lines": ["한 줄"]},
            {"label": "군정", "lines": ["[[비밀빈칸]]을 만듦", "둘째 줄"]}]},
        {"title": "주제 둘", "rows": [{"label": "배경", "lines": ["글"]}, {"label": "과정", "lines": ["글", "글"]}]}],
    "terms": [["군정", "군대가 다스리는 정치"], ["차관", "빌려 온 돈"]],
    "side": {"title": "연표", "items": [["1961", "정변"], ["1965", "협정"]]},
    "summary": "**성장**했지만 **후퇴**하였다.",
    "questions": [
        {"kind": "선택형", "text": "선택 문항", "options": ["가", "나", "다", "라", "마"], "answer": 2, "explain": "비밀해설"},
        {"kind": "단답형", "text": "단답 문항", "answer": "비밀단답"},
        {"kind": "O·X", "text": "참거짓 문항", "answer": "X"},
        {"kind": "서술형", "text": "서술 문항", "starter": "성과는 …", "lines": 3, "answer": "비밀서술",
         "point": "비밀채점기준"}],
    "check": ["나는 설명할 수 있다."],
}
CONCEPT_SECRETS = ["비밀교육과정", "비밀성취기준", "비밀빈칸", "비밀해설", "비밀단답", "비밀서술", "비밀채점기준"]
HOUSE_COLORS = ["#1F3F7A", "#2E6DB4", "#EAF0F7", "#E3EDF9", "#F6F9FD", "#B9CDE6", "#97AECB", "#A8670F", "#FFF6E3"]
USED_COLORS = {*HOUSE_COLORS, "#FFFFFF", "#7F7F7F", "#1D4ED8"}


def concept(teacher=False, **changes):
    return make_worksheet.build_spec({**CONCEPT, **changes}, teacher=teacher)


def tables(spec):
    return [block for block in spec["blocks"] if block["type"] == "table"]


def topic_tables(spec):
    """주제 줄 표(첫 열이 13px 세로선 칸)와 주제 머리 표(첫 칸이 24px 동그라미 칸)."""
    return [block for block in tables(spec) if block.get("width_px") == 488 and block["widths"][0] == 13]


def topic_heads(spec):
    return [block for block in tables(spec) if block.get("width_px") == 488 and block["widths"][0] == 24]


def item_texts(spec):
    """칸의 글과 content 속 글 조각·도형 글을 모두 모은다."""
    texts = []
    for cell in cells(spec):
        texts.append(str(cell.get("text", "")))
        texts += [str(item if isinstance(item, str) else item.get("run") or item.get("text") or "")
                  for item in cell.get("content", [])]
    return texts


def test_palette_values_are_the_house_style_colors():
    concept_module = make_worksheet.make_worksheet_concept
    names = ("NAVY", "BLUE", "SKY", "TINT", "PALE", "SKY_LINE", "ROW_LINE", "GOLD", "CREAM")
    assert [getattr(concept_module, name) for name in names] == HOUSE_COLORS
    assert concept_module.ANS == "#1D4ED8"


@pytest.mark.parametrize("teacher", [False, True])
def test_concept_sheet_uses_only_house_style_colors(teacher):
    allowed = {*HOUSE_COLORS, "#FFFFFF", "#767676", "#1D4ED8", "#14213D", "#556070", "#C9D3DF", "#DCE7F6"}
    used = {text.upper() for text in strings(concept(teacher)) if text.startswith("#") and len(text) == 7}
    assert used and used <= allowed


def test_concept_band_is_a_paper_gradient_with_a_paper_table_on_top():
    blocks = concept()["blocks"]
    backdrop, band = blocks[0], blocks[1]
    assert backdrop["type"] == "shape" and backdrop["w"] == 794 and backdrop["fill_to"] == "#2E6DB4"
    assert backdrop["paper"] == {"x": 0, "y": 0}
    assert band["paper"]["width"] == 794 and band["widths"] == [440, 170, 184]
    assert any(isinstance(item, dict) and item.get("shape") == "round" and item["h"] == 24
               for cell in band["rows"][0] for item in cell.get("content", []))


def test_concept_page_modes_and_footer():
    spec = concept()
    assert spec["margins"] == "app" and spec["page"] == "app"
    footer = spec["footer"][0]
    assert any(item.get("page_number") for cell in footer["rows"][0] for item in cell.get("content", [])
               if isinstance(item, dict))


def test_concept_head_has_name_boxes_and_goal_names():
    texts = item_texts(concept())
    for expected in ("학년", "반", "번", "이름", "학습 목표", "핵심 질문"):
        assert expected in texts
    assert not any("교사용" in text for text in texts)


def test_concept_teacher_head_says_teacher_and_adds_curriculum_row():
    texts = item_texts(concept(True))
    assert any("교사용" in text for text in texts) and "교육과정" in texts
    assert "교육과정" not in item_texts(concept())


def test_concept_sheet_order_head_goal_strips_topics_questions_check():
    spec = concept()
    kinds = [block["type"] for block in spec["blocks"]]
    assert kinds.count("page_break") == 1
    texts = item_texts(spec)
    assert "Ⅰ" in texts and "Ⅱ" in texts and any("맞은 문항" in text for text in texts)
    assert texts.index("Ⅰ") < texts.index("Ⅱ") < texts.index("도달 점검")


def test_concept_side_boxes_are_separate_paper_tables_that_do_not_push_the_text():
    side = [block for block in tables(concept()) if block.get("paper") and block["paper"]["x"] == 550]
    assert len(side) == 2 and all(block["paper"]["wrap"] == "front" for block in side)
    assert side[0]["rows"][0][0]["fill"] == make_worksheet.NAVY
    assert side[1]["rows"][0][0]["fill"] == make_worksheet.ACCENT
    assert side[0]["paper"]["y"] < side[1]["paper"]["y"]


def test_concept_without_side_columns_has_no_side_tables():
    spec = concept(terms=None, side=None)
    assert not [block for block in tables(spec) if block.get("paper", {}).get("x") == 550]


def test_concept_topic_has_circle_number_year_chip_and_tint_labels():
    head = topic_heads(concept())[0]["rows"][0]
    circle, year = head[0]["content"][0], head[2]["content"][0]
    assert circle["shape"] == "ellipse" and circle["fill"] == make_worksheet.ACCENT and circle["text"] == "1"
    assert head[1]["font"] == "myeongjo" and year["fill"] == make_worksheet.TINT and year["text"] == "1961"
    assert all(cell["valign"] == "center" for cell in head)
    label = topic_tables(concept())[0]["rows"][0][2]["content"][0]
    assert label["fill"] == make_worksheet.TINT and label["color"] == make_worksheet.NAVY


def test_concept_has_no_one_line_summary_even_if_the_input_has_one():
    spec = concept(summary="**결론**")
    assert "한 줄 정리" not in item_texts(spec) and "결론" not in "".join(strings(spec))


def test_concept_student_has_no_answer_in_spec():
    found = [secret for text in strings(concept()) for secret in CONCEPT_SECRETS if secret in text]
    assert found == []


def test_concept_student_file_has_no_answer_or_answer_color(tmp_path):
    out = tmp_path / "s.hwpx"
    assert make_worksheet.main([str(write_json(tmp_path, CONCEPT)), str(out)]) == 0
    with zipfile.ZipFile(out) as package:
        contents = {name: package.read(name).decode("utf-8", "ignore") for name in package.namelist()}
    assert [name for name, text in contents.items() for secret in CONCEPT_SECRETS if secret in text] == []
    assert f'textColor="{BLUE}"' not in contents["Contents/header.xml"]


def test_concept_student_blank_is_a_shaded_underlined_run_of_spaces():
    texts = [text for text in item_texts(concept()) if "~~" in text]
    assert texts and any("~~    " in text for text in texts)
    assert not [text for text in item_texts(concept()) if "[[" in text]


def test_concept_teacher_shows_answers_explanations_and_standards():
    text = "\n".join(strings(concept(True)))
    assert [secret for secret in CONCEPT_SECRETS if secret not in text] == []
    assert "해설: 비밀해설" in text and "채점: 비밀채점기준" in text and "← 정답" in text


def test_concept_teacher_blank_has_the_answer_inside_blue_mark_color():
    spec = concept(True)
    blank = next(cell for cell in cells(spec) if "비밀빈칸" in str(cell.get("text")))
    assert "~~" in blank["text"] and blank["mark_color"] == BLUE
    answers = [item["run"] for cell in cells(spec) for item in cell.get("content", [])
               if isinstance(item, dict) and item.get("color") == BLUE and item.get("bold")]
    assert "비밀단답" in answers
    assert "비밀서술" in [cell["text"] for cell in cells(spec) if cell.get("color") == BLUE and cell.get("bold")]


def test_concept_teacher_marks_only_the_right_option():
    def marked(teacher):
        runs = [item for cell in cells(concept(teacher)) for item in cell.get("content", [])
                if isinstance(item, dict) and item.get("run", "").startswith(tuple("①②③④⑤"))]
        return [item["run"] for item in runs if item["color"] == BLUE]
    assert marked(True) == ["② 나"] and marked(False) == []


def test_concept_teacher_topics_have_same_rows_as_student():
    def rows(teacher):
        return [[len(row) for row in table["rows"]] for table in topic_tables(concept(teacher))]
    assert rows(True) == rows(False)


def test_concept_essay_keeps_line_count_with_answer_and_scoring_on_the_lines():
    def essay(teacher):
        return next(block for block in tables(concept(teacher)) if block["widths"] == [34, 664]
                    and block["rows"][0][1].get("color") == "#767676")
    student, teacher = essay(False), essay(True)
    assert len(student["rows"]) == len(teacher["rows"]) == 5        # 첫 문장 + 줄 3 + 아래 여백 칸
    assert [row[1]["text"] for row in teacher["rows"]][1:3] == ["비밀서술", "채점: 비밀채점기준"]
    assert [row[1]["text"] for row in student["rows"]][1:] == ["", "", "", ""]
    assert student["rows"][3][1]["edges"]["bottom"][2] == make_worksheet.ROW_LINE    # 마지막 쓰기 줄도 밑줄
    assert student["rows"][4][1]["edges"]["bottom"][2] != make_worksheet.ROW_LINE    # 여백 칸은 상자 테두리


def test_concept_ox_shows_correct_answer_only_for_teacher():
    def ox(teacher):
        return "".join(item["run"] for cell in cells(concept(teacher)) for item in cell.get("content", [])
                       if isinstance(item, dict) and item.get("run", "").startswith(("( ", "O", "X", "　/", " )")))
    assert "← 정답" not in ox(False) and "X  ← 정답" in ox(True)


def test_concept_source_box_has_thin_outline_and_pale_body():
    item = {"kind": "선택형", "text": "문항", "source": "제시문", "source_note": "— 출처", "options": ["가", "나"],
            "answer": 1}
    source = next(block for block in tables(concept(questions=[item])) if block["widths"] == [34, 664]
                  and block["rows"][0][1].get("fill") == make_worksheet.PALE)
    box = source["rows"][0][1]
    assert box["edges"]["left"][2] == make_worksheet.SKY_LINE and "— 출처" in str(box["content"])


def rows_height(block):
    return sum(max(cell.get("height_px", 0) for cell in row) for row in block["rows"])


def side_pair(spec):
    side = [block for block in tables(spec) if block.get("paper") and block["paper"]["x"] == 550]
    return side[0], side[1]


def test_concept_topics_share_the_free_height_evenly_with_a_minimum_gap():
    long_doc = {**CONCEPT, "topics": CONCEPT["topics"] * 3}
    gaps = [block["gap_px"][0] for block in concept(**{"topics": long_doc["topics"]})["blocks"]
            if block["type"] == "table" and block.get("width_px") == 488 and block["widths"][0] == 24][1:]
    assert gaps and min(gaps) >= 12 and len(set(gaps)) == 1


def test_concept_first_side_box_is_the_gloss_and_stretches_to_the_bottom_of_the_outline():
    gloss, timeline = side_pair(concept())
    assert gloss["rows"][0][0]["text"] == "용어 풀이" and timeline["rows"][0][0]["text"] == "연표"
    assert timeline["paper"]["y"] == gloss["paper"]["y"] + rows_height(gloss) + 10
    assert all(row[0]["valign"] == "center" for row in gloss["rows"][1:])


def test_concept_side_without_terms_is_only_the_timeline():
    spec = concept(terms=None)
    assert [block for block in tables(spec) if block.get("paper", {}).get("x") == 550][0]["rows"][0][0]["text"] == "연표"


def test_concept_quiz_gap_is_shared_evenly_and_the_reach_box_is_one_and_a_half_times_apart():
    spec = concept()
    heads = [block for block in tables(spec) if block["widths"] == [34, 594, 70]]
    pads = [head["rows"][0][0]["pad_px"][2] for head in heads]
    assert pads[0] == 0 and len(set(pads[1:])) == 1 and pads[1] >= 7          # 점선 아래 간격 = 문항 사이 간격의 절반
    reach = next(block for block in spec["blocks"] if block.get("widths") == [428, 270])
    assert reach["gap_px"][0] >= 20


HIST19_SAMPLE = Path(__file__).resolve().parents[3] / "samples" / "hwpx" / "hist19.json"


@pytest.mark.skipif(not HIST19_SAMPLE.exists(), reason="samples/는 저장소에 올리지 않는다: 본보기 hist19.json 없음")
def test_concept_essay_in_the_sample_has_two_lines():
    import json
    sample = json.loads(HIST19_SAMPLE.read_text(encoding="utf-8"))
    assert [q["lines"] for q in sample["questions"] if q["kind"] == "서술형"] == [2]
    assert "summary" not in sample


def test_concept_writes_valid_files_for_both_versions(tmp_path):
    for teacher in (False, True):
        out = tmp_path / f"{int(teacher)}.hwpx"
        make_worksheet.make_hwpx.build_hwpx(concept(teacher), out)
        assert out.stat().st_size > 0 and not make_worksheet.make_hwpx.validate_package(out)


@pytest.mark.parametrize("missing", ["title", "goal", "topics"])
def test_concept_required_values_are_refused(missing):
    with pytest.raises(ValueError, match=missing):
        make_worksheet.build_spec({**CONCEPT, missing: ""})


@pytest.mark.parametrize("changes, pattern", [
    ({"topics": [{"title": "가", "rows": []}]}, "rows"),
    ({"topics": [{"title": "가", "rows": [{"label": "가"}]}]}, "lines"),
    ({"questions": [{"kind": "수수께끼", "text": "가"}]}, "kind"),
    ({"questions": [{"kind": "선택형", "text": "가", "options": ["하나"], "answer": 1}]}, "options"),
    ({"terms": ["군정"]}, "terms"),
])
def test_concept_bad_values_are_refused_in_korean(changes, pattern):
    with pytest.raises(ValueError, match=pattern):
        concept(**changes)


def test_concept_unanswered_reports_missing_answers():
    doc = {**CONCEPT, "topics": [{"title": "가", "rows": [{"label": "라", "lines": ["(      )를 쓴다"]}]}],
           "questions": [{"kind": "선택형", "text": "가", "options": ["가", "나"]},
                         {"kind": "선택형", "text": "나", "options": ["가", "나"], "answer": 9},
                         {"kind": "단답형", "text": "다"}, {"kind": "O·X", "text": "라", "answer": "?"},
                         {"kind": "서술형", "text": "마", "answer": "답"}]}
    assert make_worksheet.unanswered(doc) == ["주제 1: 답이 없는 빈칸 1곳", "문항 1: 답이 없거나 맞지 않음",
                                              "문항 2: 답이 없거나 맞지 않음", "문항 3: 답이 없거나 맞지 않음",
                                              "문항 4: 답이 없거나 맞지 않음"]


def test_concept_full_doc_has_no_unanswered_items():
    assert make_worksheet.unanswered(CONCEPT) == []


def test_concept_cli_warns_only_for_teacher(tmp_path, capsys):
    doc = {**CONCEPT, "questions": [{"kind": "단답형", "text": "가"}]}
    source, out = write_json(tmp_path, doc), tmp_path / "a.hwpx"
    make_worksheet.main([str(source), str(out)])
    assert capsys.readouterr().err == ""
    make_worksheet.main([str(source), str(out), "--teacher"])
    assert "문항 1" in capsys.readouterr().err


def test_activity_sheet_still_builds_when_topics_are_absent():
    assert make_worksheet.build_spec(FULL)["blocks"][0]["rows"][0][0]["fill"] == make_worksheet.NAVY
