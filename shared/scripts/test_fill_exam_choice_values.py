"""수 선지 순서 점검: 한글 수식 분수·대분수·음수를 값으로 읽는지 본다."""
import pytest

from fill_exam_parse import choice_order_notes


def notes(choices: list[str]) -> list[str]:
    item = {"type": "combo_table", "stem": "가", "points": 3, "choices": choices, "answer": 1}
    return [n for n in choice_order_notes([("문항 1", item)]) if "수 선지" in n or "계단식" in n]


@pytest.mark.parametrize("choices", [
    ["{{1/4}}", "{{1/3}}", "{{1/2}}", "{{2/3}}", "{{3/4}}"],
    ["{{1 1/4}}", "{{1 7/12}}", "{{2 1/3}}", "{{2 1/2}}", "{{3}}"],
    ["{{-2/3}}", "{{-1/2}}", "{{-1/4}}", "{{1/4}}", "{{1/2}}"],
    ["-1", "{{-1/2}}", "0", "0.75", "{{4/3}}"],
    ["{{1/2}}", "0.6", "{{2/3}}", "0.75", "1"],
])
def test_ordered_fraction_choices_have_no_note(choices):
    assert not notes(choices)


@pytest.mark.parametrize("choices", [
    ["{{3/4}}", "{{1/3}}", "{{1/2}}", "{{2/3}}", "{{1/4}}"],
    ["{{1 7/12}}", "{{1 1/4}}", "{{2}}", "{{3}}", "{{4}}"],
    ["{{-1/4}}", "{{-2/3}}", "{{1/4}}", "{{1/2}}", "{{3/4}}"],
    ["0.8", "{{1/2}}", "{{2/3}}", "{{3/4}}", "1"],
])
def test_unordered_fraction_choices_get_note(choices):
    assert any("작은 수부터" in n for n in notes(choices))


def test_unreadable_math_skips_order_check():
    assert not any("작은 수부터" in n for n in notes(["{{sqrt 2}}", "{{sqrt 3}}", "1", "{{pi}}", "{{1/2}}"]))
    assert not any("작은 수부터" in n for n in notes(["{{sqrt 5}}", "{{sqrt 3}}", "{{sqrt 2}}", "1", "2"]))
