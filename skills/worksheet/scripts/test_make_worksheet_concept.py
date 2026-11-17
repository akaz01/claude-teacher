"""개념 정리 학습지 시험: 학생용 답 누출, 빈칸 너비, 쪽 넘침 경고, 입력 검사, 앱 색 비교.
(test_make_worksheet.py가 800줄 가까워 나눔. 시험 파일은 스킬 zip에 들어가지 않는다.
 본보기는 저장소에 없는 실제 양식 대신 코드로 만든 가짜 학습지를 쓴다.)"""
import ast
import json
import os
import re
import zipfile
from pathlib import Path

import pytest

import make_worksheet  # noqa: I001  (먼저 불러야 공용 폴더 경로가 잡힌다)
import make_hwpx
import make_worksheet_concept as concept_module

ROOT = Path(os.environ.get("TEACHER_KIT_ROOT") or Path(__file__).resolve().parents[3])
APP_COLORS = ROOT / "samples" / "app-sample" / "write_sheet.py"
def _fake_doc() -> dict:
    """본보기와 같은 짜임(주제 5개, 용어 7쌍, 연표 7줄, 문항 7개)의 가짜 학습지. 글은 모두 지어낸 것이다."""
    def topic(title, tag, rows):
        return {"title": title, "tag": tag, "rows": [{"label": label, "lines": lines} for label, lines in rows]}

    return {
        "subject": "과학", "unit": "물의 순환", "lesson": "1차시", "meta": "중학교 1학년 과학 · 물의 순환",
        "title": "물은 어떻게 돌고 도는가", "sub": "개념 정리와 형성평가",
        "goal": ["① 물의 순환 과정을 단계별로 설명할 수 있다.", "② 증발과 응결이 일어나는 까닭을 말할 수 있다."],
        "question": "물은 땅과 하늘 사이를 어떻게 오갈까?", "curriculum": "2022",
        "standards": ["[9과01-01] 물의 순환 과정에서 일어나는 상태 변화를 설명할 수 있다.",
                      "[9과01-02] 물의 순환이 생활에 주는 영향을 예를 들어 말할 수 있다."],
        "topics": [
            topic("물의 순환이란", "개념", [("뜻", ["물이 (바다·육지·대기)를 (돌며) 모습을 바꾸는 현상"]),
                                       ("원인", ["태양 에너지가 [[물을 데워]] 증발시키고", "중력이 물을 아래로 끌어당김"]),
                                       ("중요성", ["지구의 물이 한곳에 쌓이지 않고 고루 퍼짐"])]),
            topic("증발", "상태 변화", [("뜻", ["액체인 물이 [[기체]]인 수증기로 변함"]),
                                      ("조건", ["햇빛이 강하고 바람이 잘 불며", "공기가 건조할수록 잘 일어남"]),
                                      ("예", ["젖은 빨래가 마르는 일, 바다에서 올라가는 수증기"])]),
            topic("응결", "상태 변화", [("뜻", ["수증기가 [[액체]]인 물방울로 변함"]),
                                      ("과정", ["수증기가 높이 올라가 차가워지면", "작은 물방울이 되어 구름을 이룸"]),
                                      ("예", ["차가운 컵 겉면에 맺힌 물방울"])]),
            topic("강수와 흐름", "순환의 마무리", [("강수", ["구름 속 물방울이 커져 비나 눈으로 내림", "내린 물은 땅 위와 땅속으로 나뉨"]),
                                                 ("흐름", ["지표수는 강을 따라 바다로 흐르고", "지하수는 천천히 땅속을 흐름"]),
                                                 ("다시 증발", ["바다에 모인 물이 다시 증발하며 순환이 이어짐", "이 과정은 끊이지 않고 되풀이됨"])]),
            topic("순환과 생활", "활용", [("농사", ["비가 내려 [[논밭에 물]]을 댈 수 있음"]),
                                       ("날씨", ["구름과 비는 물의 순환으로 생김", "가뭄과 홍수도 순환과 관련 있음"])]),
        ],
        "terms": [["증발", ["액체가 기체로 변하는 일"]], ["응결", ["기체가 액체로 변하는 일"]],
                  ["수증기", ["기체 상태의 물"]], ["강수", ["비·눈처럼 내리는 물"]],
                  ["지표수", ["땅 위를 흐르는 물"]], ["지하수", ["땅속을 흐르는 물"]], ["구름", ["물방울이 모인 덩어리"]]],
        "side": {"title": "한눈에 보는 순환", "items": [["1단계", "바다·육지에서 증발"], ["2단계", "하늘에서 응결"],
                                                    ["3단계", "구름이 모여 형성"], ["4단계", "비나 눈으로 강수"],
                                                    ["5단계", "지표·지하로 흐름"], ["6단계", "바다로 모임"], ["7단계", "다시 증발"]]},
        "questions": [
            {"kind": "선택형", "text": "물이 수증기로 변하는 현상으로 옳은 것은?", "options": ["증발", "응결", "강수", "융해", "승화"],
             "answer": 1, "cols": 3, "explain": "액체인 물이 기체인 수증기로 변하는 현상은 증발이다."},
            {"kind": "선택형", "text": "수증기가 물방울로 변하는 현상은?", "options": ["증발하는 것", "응결하는 것", "얼어붙는 것", "녹아내리는 것", "흩어지는 것"],
             "answer": 2, "cols": 3, "explain": "기체가 액체로 변하는 현상은 응결이며 구름이 만들어지는 까닭이다."},
            {"kind": "단답형", "text": "구름 속 물방울이 커져 땅으로 내리는 것을 무엇이라 하는가?", "answer": "강수"},
            {"kind": "O·X", "text": "물의 순환은 태양 에너지와 관계가 없다.", "answer": "X"},
            {"kind": "선택형", "text": "지표수에 해당하는 것은?", "options": ["강물", "우물물", "지하수 샘", "깊은 땅속 물", "암석 속 물"],
             "answer": 1, "cols": 2},
            {"kind": "단답형", "text": "땅속을 천천히 흐르는 물을 무엇이라 하는가?", "answer": "지하수"},
            {"kind": "서술형", "text": "물의 순환이 끊이지 않고 이어지는 까닭을 쓰시오.", "lines": 2,
             "answer": "태양 에너지로 증발하고 응결과 강수가 되풀이되기 때문이다."},
        ],
        "check": ["나는 물의 순환 과정을 순서대로 말할 수 있다.", "나는 증발과 응결의 차이를 설명할 수 있다."],
        "foot": "정리한 내용을 가족에게 설명해 보세요.",
    }


DOC = _fake_doc()
SECRET = "[[비밀]]"
PLAIN_KEYS = {"kind", "cols", "lines", "answer", "explain", "point", "curriculum", "standards", "closing"}


def with_secret(value, key=None):
    """본보기의 모든 글에 [[비밀]]을 덧붙인 새 값. 종류·번호·답 같은 값 칸은 그대로 둔다."""
    if isinstance(value, dict):
        return {name: with_secret(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [with_secret(item, key) for item in value]
    if isinstance(value, str) and key not in PLAIN_KEYS:
        return value + SECRET
    return value


def build(tmp_path, doc, teacher=False):
    out = tmp_path / f"{int(teacher)}.hwpx"
    warnings = make_hwpx.build_hwpx(make_worksheet.build_spec(doc, teacher=teacher), out)
    assert not make_hwpx.validate_package(out)
    with zipfile.ZipFile(out) as package:
        return warnings, {name: package.read(name).decode("utf-8", "ignore") for name in package.namelist()}


def spec_cells(spec):
    return [cell for block in spec["blocks"] if block["type"] == "table" for row in block["rows"] for cell in row]


# ---------------------------------------------------------------- 1. 학생용 정답 누출

def test_student_package_has_no_answer_when_every_text_holds_a_blank(tmp_path):
    _, contents = build(tmp_path, with_secret(DOC))
    assert "Preview/PrvText.txt" in contents
    assert [name for name, text in contents.items() if "비밀" in text or "[[" in text] == []


def test_teacher_package_shows_the_answers_and_no_brackets(tmp_path):
    _, contents = build(tmp_path, with_secret(DOC), teacher=True)
    assert "비밀" in contents["Contents/section0.xml"] and "비밀" in contents["Preview/PrvText.txt"]
    assert [name for name, text in contents.items() if "[[" in text] == []


def test_unmatched_bracket_is_refused_so_no_answer_can_stay(tmp_path):
    doc = {**DOC, "topics": [{"title": "가", "rows": [{"label": "나", "lines": ["[[답이 안 닫힘"]}]}]}
    with pytest.raises(ValueError, match=r"\[\["):
        make_worksheet.build_spec(doc)


def test_blank_in_title_and_shape_text_never_shows_the_answer():
    spec = make_worksheet.build_spec({**DOC, "title": "제목 [[비밀]]", "meta": "머리 [[비밀]]"})
    assert "비밀" not in json.dumps(spec, ensure_ascii=False)


# ---------------------------------------------------------------- 2. 빈칸 너비는 답 길이와 상관없이 같다

def blank_runs(spec):
    return [text for cell in spec_cells(spec) for text in [str(cell.get("text", ""))] if "~~" in text
            for text in re.findall(r"~~[^~]*~~", text)]


def test_every_student_blank_has_the_same_width_whatever_the_answer():
    doc = {**DOC, "topics": [{"title": "가", "rows": [
        {"label": "나", "lines": ["[[짧]]을", "[[아주아주 긴 답입니다]]를", "[[중간 답]]"]}]}]}
    runs = blank_runs(make_worksheet.build_spec(doc))
    assert len(runs) == 3 and len(set(runs)) == 1 and runs[0].strip("~").strip() == ""


def test_teacher_topic_rows_have_the_same_row_heights_as_student():
    def layout(teacher):
        spec = make_worksheet.build_spec(DOC, teacher=teacher)
        return [[cell.get("height_px") for row in block["rows"] for cell in row]
                for block in spec["blocks"] if block.get("width_px") == 488]       # 주제 머리·줄 표
    assert layout(True) == layout(False)


def test_short_answer_boxes_share_one_width_in_both_versions():
    questions = [{"kind": "단답형", "text": "가", "answer": "짧"}, {"kind": "단답형", "text": "나", "answer": "아주아주 긴 답입니다"}]

    def widths(teacher):
        spec = make_worksheet.build_spec({**DOC, "questions": questions}, teacher=teacher)
        return [block["widths"] for block in spec["blocks"] if block.get("type") == "table" and block["widths"][:2] == [34, 38]]
    assert len(widths(False)) == 2 and widths(False)[0] == widths(False)[1] == widths(True)[0] == widths(True)[1]


def test_blank_that_makes_a_line_overflow_is_reported():
    doc = {**DOC, "topics": [{"title": "가", "rows": [
        {"label": "나", "lines": ["가나다라마바사아자차카타파하가나다라마바사 [[짧]] 끝", "[[아주아주아주아주 긴 답 하나입니다]]"]}]}]}
    assert any("빈칸이 넓어" in note for note in make_worksheet.build_spec(doc)["notes"])


# ---------------------------------------------------------------- 3. 쪽 넘침 경고

def test_sample_fits_without_any_overflow_warning():
    assert make_worksheet.build_spec(DOC)["notes"] == []


def test_too_many_topics_warns_about_the_first_page():
    notes = make_worksheet.build_spec({**DOC, "topics": DOC["topics"] * 2})["notes"]
    assert any(note.startswith("확인: 1쪽 개념 정리가 약 ") and "px(약 " in note and "줄" in note for note in notes)
    assert any("옆 칸" in note for note in notes)


def test_too_many_questions_warns_about_the_second_page():
    notes = make_worksheet.build_spec({**DOC, "questions": DOC["questions"] * 2})["notes"]
    assert any("2쪽 형성평가가" in note and "넘침" in note for note in notes)


def test_quiz_gap_leaves_a_safety_margin_at_the_bottom():
    # 한글은 표마다 조금씩 높이가 늘어 어림이 꽉 차면 마지막 표가 다음 쪽으로 밀린다
    gap, overflow = concept_module.quiz_gap(166, 8.5, teacher=False)
    assert overflow <= 0
    assert gap * 8.5 <= 166 - concept_module.SAFETY_PX + 0.01


def test_quiz_gap_warns_the_student_copy_when_only_the_margin_is_left():
    gap, overflow = concept_module.quiz_gap(118, 8.5, teacher=False)    # 최소 간격 14px이면 119px 필요
    assert gap == concept_module.MIN_QUESTION_GAP
    assert overflow > 1


def test_quiz_gap_lets_the_teacher_copy_tighten_to_stay_on_two_pages():
    # 교사용은 해설 줄만큼 길다. 학생에게 나눠 주지 않으므로 간격을 더 좁혀 2쪽을 지킨다
    gap, overflow = concept_module.quiz_gap(118, 8.5, teacher=True)
    assert concept_module.TEACHER_MIN_QUESTION_GAP <= gap < concept_module.MIN_QUESTION_GAP
    assert overflow <= 0


def test_teacher_copy_with_challenge_fits_without_warning():
    challenge = {"text": "물의 순환이 멈춘다면 어떤 일이 생길지 새 상황을 정해 써 보세요.", "lines": 2,
                 "answer": "비가 내리지 않아 강이 마르는 식으로 순환 단계와 연결해 쓴다."}
    assert make_worksheet.build_spec({**DOC, "challenge": challenge}, teacher=True)["notes"] == []


def test_too_many_terms_warns_about_the_side_column():
    notes = make_worksheet.build_spec({**DOC, "terms": DOC["terms"] * 3})["notes"]
    assert any("옆 칸" in note for note in notes)


def test_overflow_warning_reaches_the_cli(tmp_path, capsys):
    source = tmp_path / "in.json"
    source.write_text(json.dumps({**DOC, "topics": DOC["topics"] * 2}, ensure_ascii=False), encoding="utf-8")
    assert make_worksheet.main([str(source), str(tmp_path / "a.hwpx")]) == 0
    assert "확인: 1쪽 개념 정리가" in capsys.readouterr().err


def test_check_without_questions_is_reported_not_dropped_silently():
    notes = make_worksheet.build_spec({**DOC, "questions": []})["notes"]
    assert any("도달 점검" in note for note in notes)
    assert make_worksheet.build_spec({**DOC, "questions": [], "closing": "none"})["notes"] == []


# ---------------------------------------------------------------- 4. 입력 검사와 한국어 오류

@pytest.mark.parametrize("changes, pattern", [
    ({"topics": [{"title": "가", "rows": "글"}]}, "주제 1"),
    ({"topics": [DOC["topics"][0], "글"]}, "주제 2"),
    ({"topics": [{"title": "가", "rows": ["글"]}]}, "주제 1의 1번째 줄"),
    ({"topics": [{"title": "가", "rows": [{"label": "나", "lines": [1, {"x": 1}]}]}]}, "주제 1의 1번째 줄 lines"),
    ({"questions": [DOC["questions"][0], "글"]}, "문항 2"),
    ({"questions": [{"kind": "선택형", "text": "가", "options": "글", "answer": 1}]}, "문항 1"),
    ({"questions": [{"kind": "선택형", "text": "가", "options": ["가", "나"], "cols": 9}]}, "문항 1 cols"),
    ({"questions": [{"kind": "서술형", "text": "가", "lines": 0}]}, "문항 1 lines"),
    ({"questions": [{"kind": "서술형", "text": "가", "lines": 99}]}, "문항 1 lines"),
    ({"questions": [{"kind": "서술형", "text": "가", "lines": "셋"}]}, "문항 1 lines"),
    ({"questions": [{"kind": "단답형", "text": ["가"]}]}, "문항 1"),
    ({"questions": [{"kind": "단답형", "text": "가", "answer": ["가"]}]}, "문항 1 answer"),
    ({"terms": [["용어", {"x": 1}]]}, "terms"),
    ({"terms": "글"}, "terms"),
    ({"side": {"title": "가", "items": [["1961"]]}}, "side.items"),
    ({"side": "연표"}, "side"),
    ({"goal": [["중첩"]]}, "goal"),
    ({"check": [{"x": 1}]}, "check"),
    ({"standards": {"x": 1}}, "standards"),
    ({"subject": ["한국사"]}, "subject"),
])
def test_wrong_shapes_are_refused_with_a_korean_place(changes, pattern):
    with pytest.raises(ValueError, match=pattern):
        make_worksheet.build_spec({**DOC, **changes})


def test_single_text_in_a_list_place_is_wrapped():
    spec = make_worksheet.build_spec({**DOC, "goal": "목표 하나", "check": "나는 할 수 있다.", "standards": "[기준] 하나"}, teacher=True)
    texts = [str(cell.get("text")) for cell in spec_cells(spec)]
    assert "목표 하나" in texts and any("나는 할 수 있다." in text for text in texts) and any("[기준] 하나" in text for text in texts)


def test_too_long_topic_title_is_refused_with_a_length_hint():
    topic = {**DOC["topics"][1], "title": "아주 긴 제목 " * 8, "tag": "1961~1963 군사 정부 시기"}
    with pytest.raises(ValueError, match=r"주제 2 제목이 너무 김\(약 \d+자 이하\)"):
        make_worksheet.build_spec({**DOC, "topics": [DOC["topics"][0], topic]})


def test_activity_goal_list_is_joined_by_line_breaks_not_printed_as_a_list():
    doc = {"subject": "수학", "unit": "방정식", "title": "제목", "goal": ["① 하나", "② 둘"], "check": "나는 한다.",
           "standards": ["[기준1]", "[기준2]"], "curriculum": "2022", "activities": [{"title": "활동", "parts": []}]}
    for teacher in (False, True):
        text = json.dumps(make_worksheet.build_spec(doc, teacher=teacher), ensure_ascii=False)
        assert "① 하나\\n② 둘" in text and "['" not in text
    assert "나는 한다." in json.dumps(make_worksheet.build_spec(doc), ensure_ascii=False)


def test_python_errors_never_reach_the_teacher_in_english(tmp_path, capsys):
    bad = {"subject": "수학", "unit": "단원", "title": "제목", "goal": "목표",
           "activities": [{"title": "활동", "parts": [{"kind": "grid", "header": "머리", "rows": 5}]}]}
    source = tmp_path / "in.json"
    source.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    assert make_worksheet.main([str(source), str(tmp_path / "a.hwpx")]) == 1
    error = capsys.readouterr().err
    assert "만들지 못함" in error and "활동 1의 1번째 부품" in error
    assert not re.search(r"[A-Za-z]{4,} ", error.replace("JSON", ""))


def test_non_object_input_is_reported_in_korean(tmp_path, capsys):
    source = tmp_path / "in.json"
    source.write_text("[1, 2]", encoding="utf-8")
    assert make_worksheet.main([str(source), str(tmp_path / "a.hwpx")]) == 1
    assert "객체" in capsys.readouterr().err


def test_teacher_notes_longer_than_the_lines_grow_the_row_estimate():
    essay = {"kind": "서술형", "text": "가", "lines": 1, "answer": "예시 답입니다 " * 12, "point": "채점 기준을 길게 " * 8}
    heights = []
    for teacher in (False, True):
        spec = make_worksheet.build_spec({**DOC, "questions": [essay], "check": []}, teacher=teacher)
        table = next(block for block in spec["blocks"] if block.get("widths") == [34, 664]
                     and block["rows"][0][1].get("fill") == concept_module.PALE)
        heights.append(table["rows"][0][1]["height_px"])
    assert heights[1] > heights[0]


# ---------------------------------------------------------------- 7. 앱 색과 같은 값

def app_colors():
    values = {}
    for node in ast.parse(APP_COLORS.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple) and isinstance(node.value, ast.Tuple):
            names = [target.id for target in node.targets[0].elts]
            values.update(zip(names, [item.value for item in node.value.elts if isinstance(item, ast.Constant)]))
    return values


@pytest.mark.skipif(not APP_COLORS.exists(), reason="앱 학습지 파일(samples/app-sample/write_sheet.py)이 없음")
def test_house_colors_match_the_app_sheet_writer():
    app = app_colors()
    names = {"NAVY": "NAVY", "BLUE": "BLUE", "SKY": "SKY", "SKY_LINE": "SKY_LINE", "PALE": "PALE", "TINT_BLUE": "TINT",
             "HAIR": "HAIR", "ROW_LINE": "ROW_LINE", "GOLD": "GOLD", "CREAM": "CREAM", "FILL": "FILL", "ANS": "ANS"}
    assert set(names) <= set(app)
    assert {ours: getattr(concept_module, ours) for ours in names.values()} == {ours: app[theirs] for theirs, ours in names.items()}


def test_activity_sheet_takes_its_colors_from_the_concept_module():
    for name in ("NAVY", "TINT", "SKY_LINE", "PALE", "ROW_LINE", "GOLD", "CREAM"):
        assert getattr(make_worksheet, name) == getattr(concept_module, name)
    assert make_worksheet.ANSWER_COLOR == concept_module.ANS and make_worksheet.BLANK_MARK is concept_module.BLANK_MARK


# ---------------------------------------------------------------- 8. 도전 과제 칸 (challenge)

CHALLENGE = {"text": "물의 순환이 멈춘다면 어떤 일이 생길지 새 상황을 정해 써 보세요.", "lines": 2,
             "answer": "비가 내리지 않아 강이 마른다는 식으로 순환 단계와 연결해 쓴다."}


def challenge_tables(spec):
    """'도전 과제' 이름표 칸으로 시작하는 표."""
    return [block for block in spec["blocks"] if block.get("type") == "table"
            and any(cell.get("text") == "도전 과제" for row in block["rows"] for cell in row)]


def test_challenge_is_a_labeled_box_with_the_task_and_writing_lines():
    (box,) = challenge_tables(make_worksheet.build_spec({**DOC, "challenge": CHALLENGE}))
    assert box["rows"][0][0]["text"] == "도전 과제" and box["rows"][0][1]["text"] == CHALLENGE["text"]
    assert len(box["rows"]) >= 1 + CHALLENGE["lines"]


def test_challenge_comes_after_the_questions_and_before_the_check():
    spec = make_worksheet.build_spec({**DOC, "challenge": CHALLENGE})
    texts = [json.dumps(block, ensure_ascii=False) for block in spec["blocks"]]
    last_question = max(i for i, text in enumerate(texts) if "맞은 문항" not in text and DOC["questions"][-1]["text"] in text)
    challenge = next(i for i, text in enumerate(texts) if "도전 과제" in text)
    check = next(i for i, text in enumerate(texts) if "도달 점검" in text)
    assert last_question < challenge < check


def test_challenge_answer_is_only_in_the_teacher_version(tmp_path):
    doc = {**DOC, "challenge": CHALLENGE}
    assert CHALLENGE["answer"] not in json.dumps(make_worksheet.build_spec(doc), ensure_ascii=False)
    assert CHALLENGE["answer"] in json.dumps(make_worksheet.build_spec(doc, teacher=True), ensure_ascii=False)
    _, student = build(tmp_path, with_secret({**doc, "challenge": {**CHALLENGE, "text": CHALLENGE["text"]}}))
    assert [name for name, text in student.items() if "비밀" in text or "[[" in text] == []


def test_challenge_rows_have_the_same_heights_in_both_versions():
    def heights(teacher):
        (box,) = challenge_tables(make_worksheet.build_spec({**DOC, "challenge": CHALLENGE}, teacher=teacher))
        return [[cell.get("height_px") for cell in row] for row in box["rows"]]
    assert heights(True) == heights(False)


def test_challenge_label_stays_the_old_name_even_if_asked_otherwise():
    spec = make_worksheet.build_spec({**DOC, "challenge": {**CHALLENGE, "label": "심화"}})
    assert "심화" not in json.dumps(spec, ensure_ascii=False) and challenge_tables(spec)


def test_without_challenge_the_result_is_the_same_as_before():
    plain = make_worksheet.build_spec(DOC)
    assert make_worksheet.build_spec({**DOC, "challenge": None}) == plain
    assert make_worksheet.build_spec({**DOC, "challenge": ""}) == plain
    assert "도전 과제" not in json.dumps(plain, ensure_ascii=False)


def test_challenge_text_alone_is_accepted_with_three_lines():
    (box,) = challenge_tables(make_worksheet.build_spec({**DOC, "challenge": "새 상황에 적용해 보세요."}))
    assert box["rows"][0][1]["text"] == "새 상황에 적용해 보세요."


@pytest.mark.parametrize("challenge, pattern", [
    ({"lines": 2}, "challenge"), ({"text": ["가"]}, "challenge text"), ({"text": "가", "lines": 99}, "challenge lines"),
    ({"text": "가", "answer": ["가"]}, "challenge answer"), (["가"], "challenge"), (5, "challenge"),
])
def test_wrong_challenge_is_refused_with_a_korean_place(challenge, pattern):
    with pytest.raises(ValueError, match=pattern):
        make_worksheet.build_spec({**DOC, "challenge": challenge})


def test_big_challenge_that_overflows_the_second_page_is_reported():
    assert make_worksheet.build_spec({**DOC, "challenge": CHALLENGE})["notes"] == []
    big = {"text": "새 상황에 적용해 보세요. " * 12, "lines": 8}
    notes = make_worksheet.build_spec({**DOC, "challenge": big})["notes"]
    assert any("2쪽 형성평가가" in note and "넘침" in note for note in notes)


def test_challenge_without_questions_is_reported_not_dropped_silently():
    notes = make_worksheet.build_spec({**DOC, "questions": [], "challenge": CHALLENGE})["notes"]
    assert any("도전 과제" in note for note in notes)


def test_unanswered_reports_a_challenge_without_answer():
    assert make_worksheet.unanswered({**DOC, "challenge": CHALLENGE}) == []
    assert make_worksheet.unanswered({**DOC, "challenge": {"text": "가"}}) == ["도전 과제: 답이 없음"]


def test_challenge_writes_valid_files_for_both_versions(tmp_path):
    for teacher in (False, True):
        out = tmp_path / f"{int(teacher)}.hwpx"
        make_worksheet.make_hwpx.build_hwpx(make_worksheet.build_spec({**DOC, "challenge": CHALLENGE}, teacher=teacher), out)
        assert not make_worksheet.make_hwpx.validate_package(out)
