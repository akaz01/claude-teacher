"""fill_exam: 밑줄 문자 3개 이상(___)은 실선 빈칸(밑줄 친 전각 빈칸)이 된다."""
import re
import zipfile
from pathlib import Path

import pytest

from fill_exam import fill_exam
from fill_exam_media import split_blanks

FORM = Path(__file__).resolve().parents[2] / "skills" / "assessment-items" / "assets" / "exam_form.hwpx"
pytestmark = pytest.mark.skipif(not FORM.exists(), reason="기본 원안지 양식이 없음")


def section_of(tmp_path, stem, student=False):
    out = tmp_path / "o.hwpx"
    item = {"type": "short_table", "stem": stem, "points": 3, "choices": ["가", "나", "다", "라", "마"], "answer": 1}
    fill_exam(FORM, {"items": [item]}, out, student)
    with zipfile.ZipFile(out) as z:
        return z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode()


def test_split_blanks():
    assert split_blanks("(A) ______") == [("(A) ", False), ("\u3000" * 3, True)]
    assert split_blanks("가 __밑줄__ 나") == [("가 __밑줄__ 나", False)]
    assert split_blanks("a ___ b") == [("a ", False), ("\u3000" * 3, True), (" b", False)]
    assert split_blanks("_" * 10)[0] == ("\u3000" * 5, True)


@pytest.mark.parametrize("student", [False, True])
def test_underscores_become_underlined_blank(tmp_path, student):
    xml, header = section_of(tmp_path, "다음 빈칸 (A) ______ 에 알맞은 것은?", student)
    stem_part = xml[xml.index("다음 빈칸"):]
    stem_part = stem_part[:stem_part.index("</hp:p>")]
    assert "_" not in stem_part
    run = re.search(r'<hp:run charPrIDRef="(\d+)"><hp:t>(\u3000+)</hp:t></hp:run>', stem_part)
    assert run and len(run.group(2)) == 3
    char = re.search(rf'<hh:charPr id="{run.group(1)}".*?</hh:charPr>', header, re.S).group(0)
    assert "<hh:underline type=\"BOTTOM\"" in char or 'underline type="BOTTOM"' in char


def test_existing_markup_still_works(tmp_path):
    xml, _ = section_of(tmp_path, "**굵게** __밑줄__ 문제")
    assert "<hp:t>굵게</hp:t>" in xml and "<hp:t>밑줄</hp:t>" in xml and "__" not in xml
