"""수식 생성기 시험: 지수·아래첨자 묶기, 끝 중괄호, 글자색·굵기, 경고 (실사용 시험의 결함 회귀 방지)."""

import unittest
from xml.etree import ElementTree

from make_hwpx import build_hwpx, plain_text
from make_hwpx_equation import equation_script, equation_text_warnings, equation_xml, split_equations
from test_make_hwpx_realuse import HP, BuildMixin


class ScriptTokenTest(unittest.TestCase):
    def test_exponent_without_space_is_grouped(self):
        cases = {
            "x^3-3x^2+2": "x^{3}-3x^{2}+2",
            "x^2+1": "x^{2}+1",
            "3x^2-6x": "3x^{2}-6x",
            "x^2=4": "x^{2}=4",
            "x^2>4": "x^{2}>4",
            "x^2,y": "x^{2},y",
            "(x-1)^2+3": "(x-1)^{2}+3",
            "a_n+1": "a_{n}+1",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(equation_script(source), expected)

    def test_token_boundaries(self):
        cases = {
            "2^10": "2^{10}",
            "x^2.5y": "x^{2.5}y",
            "e^-x": "e^{-x}",
            "10^-3": "10^{-3}",
            "x^n": "x^{n}",
            "x^alpha+1": "x^{alpha}+1",
            "x_pi": "x_{pi}",
            "x^2y": "x^{2}y",
            "x_1+x_2": "x_{1}+x_{2}",
            "x^2 + 1": "x^{2} + 1",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(equation_script(source), expected)

    def test_existing_braces_are_kept(self):
        for source in ("x^{3}-3x^{2}+2", "lim_{x->1} f(x)", "int_{0}^{2} x dx", "sqrt{2}", "{x^{2}} over {3}"):
            with self.subTest(source=source):
                self.assertEqual(equation_script(source), source)

    def test_conversion_is_idempotent(self):
        once = equation_script("x^3-3x^2+2")
        self.assertEqual(equation_script(once), once)

    def test_decimal_over_integer_is_one_fraction(self):
        self.assertEqual(equation_script("0.5/2"), "{0.5} over {2}")
        self.assertEqual(equation_script("1.5/0.5"), "{1.5} over {0.5}")
        self.assertEqual(equation_script("2/3"), "{2} over {3}")
        self.assertEqual(equation_script("1 7/12"), "1 {7} over {12}")


class SpanTest(unittest.TestCase):
    def contents(self, text):
        return [part for part, is_equation in split_equations(text) if is_equation]

    def test_triple_closing_braces_end_at_the_matching_pair(self):
        cases = {
            "{{x^{2}}}": "x^{2}",
            "{{sqrt{2}}}": "sqrt{2}",
            "{{{x^2} over {3}}}": "{x^2} over {3}",
            "{{2^{10}}}": "2^{10}",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                pieces = split_equations(f"앞 {source} 뒤")
                self.assertEqual(pieces, [("앞 ", False), (expected, True), (" 뒤", False)])

    def test_two_equations_on_one_line(self):
        self.assertEqual(self.contents("{{x^{2}}} 와 {{a}} 와 {{sqrt{3}}}"), ["x^{2}", "a", "sqrt{3}"])

    def test_preview_has_no_leftover_braces(self):
        self.assertEqual(plain_text("답 {{x^{2}}} 이다"), "답 x^{2} 이다")

    def test_unbalanced_falls_back_to_first_closing_pair(self):
        self.assertEqual(self.contents("{{a{b}} 끝"), ["a{b"])

    def test_hangul_and_blank_stay_text(self):
        self.assertEqual(self.contents("{{학생이름}} {{ }} {{x=1일 때}}"), [])


class EquationLookTest(unittest.TestCase):
    def test_color_and_bold(self):
        xml = equation_xml(3, "x=2", color="#0000FF", bold=True)
        self.assertIn('textColor="#0000FF"', xml)
        self.assertIn("<hp:script>bold {x=2}</hp:script>", xml)

    def test_default_look_is_unchanged(self):
        xml = equation_xml(3, "x=2")
        self.assertIn('textColor="#000000"', xml)
        self.assertIn("<hp:script>x=2</hp:script>", xml)

    def test_bold_does_not_widen_the_estimate(self):
        self.assertEqual(equation_xml(1, "x=2", bold=True).split('width="')[1].split('"')[0],
                         equation_xml(1, "x=2").split('width="')[1].split('"')[0])


class WarningTest(unittest.TestCase):
    def test_hangul_inside_equation_warns(self):
        warnings = equation_text_warnings({"a": "{{x=1일 때}}"})
        self.assertEqual(len(warnings), 1)
        self.assertIn("x=1일 때", warnings[0])

    def test_leftover_placeholder_does_not_warn(self):
        self.assertEqual(equation_text_warnings({"a": "{{학생이름}} 보호자님"}), [])

    def test_backslash_warns(self):
        warnings = equation_text_warnings({"a": [r"{{\frac{1}{2}}}"]})
        self.assertEqual(len(warnings), 1)
        self.assertIn(chr(92), warnings[0])

    def test_clean_equation_has_no_warning(self):
        self.assertEqual(equation_text_warnings({"a": "{{x^{2}}} {{1/2}}"}), [])


class BuildTest(BuildMixin, unittest.TestCase):
    def scripts(self, text):
        section = self.section({"blocks": [{"type": "paragraph", "text": text}]})
        return [eq.find(f"{HP}script").text for eq in ElementTree.fromstring(section).iter(f"{HP}equation")]

    def test_reported_formulas_print_correctly(self):
        self.assertEqual(self.scripts("{{x^3-3x^2+2}}"), ["x^{3}-3x^{2}+2"])
        self.assertEqual(self.scripts("{{x^{2}}}"), ["x^{2}"])
        self.assertEqual(self.scripts("{{0.5/2}}"), ["{0.5} over {2}"])

    def test_no_stray_brace_text_remains(self):
        section = self.section({"blocks": [{"type": "paragraph", "text": "{{x^{2}}}"}]})
        self.assertNotIn("<hp:t>}", section)

    def test_equation_takes_cell_color_and_bold(self):
        section = self.section({"blocks": [{"type": "table", "rows": [
            [{"text": "{{x=2}}", "color": "#0000FF", "bold": True}, {"text": "{{y}}"}]]}]})
        equations = list(ElementTree.fromstring(section).iter(f"{HP}equation"))
        self.assertEqual([eq.get("textColor") for eq in equations], ["#0000FF", "#000000"])
        self.assertEqual([eq.find(f"{HP}script").text for eq in equations], ["bold {x=2}", "y"])

    def test_header_cell_equation_follows_cell_color(self):
        section = self.section({"blocks": [{"type": "table", "rows": [
            [{"text": "{{x}}", "fill": "#2B4FA2", "color": "#FFFFFF", "bold": True}]]}]})
        equation = next(ElementTree.fromstring(section).iter(f"{HP}equation"))
        self.assertEqual(equation.get("textColor"), "#FFFFFF")

    def test_marked_text_equation_takes_mark_color(self):
        section = self.section({"blocks": [{"type": "table", "rows": [
            [{"text": "답 **{{x=2}}** 이다", "mark_color": "#0000FF"}]]}]})
        equation = next(ElementTree.fromstring(section).iter(f"{HP}equation"))
        self.assertEqual(equation.get("textColor"), "#0000FF")

    def test_wide_equation_in_narrow_cell_warns(self):
        import tempfile
        from pathlib import Path
        long = "{{" + "+".join(f"x^{n}" for n in range(2, 30)) + "}}"
        spec = {"blocks": [{"type": "table", "widths": [1, 9], "rows": [[long, "가"]]}]}
        with tempfile.TemporaryDirectory() as tmp:
            warnings = build_hwpx(spec, Path(tmp) / "a.hwpx")
        self.assertTrue(any("수식" in w and "넓" in w for w in warnings), warnings)

    def test_short_equation_in_cell_does_not_warn(self):
        import tempfile
        from pathlib import Path
        spec = {"blocks": [{"type": "table", "rows": [["{{x^2}}", "가"]]}]}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(build_hwpx(spec, Path(tmp) / "a.hwpx"), [])


if __name__ == "__main__":
    unittest.main()


# 한글 2024가 EquationCreate로 만든 수식의 실제 너비 (baseUnit 1000, 2026-11-18 실측).
# 한글은 파일을 열 때 너비를 다시 계산하지 않으므로, 어림이 이보다 좁으면 뒤 글자와 겹친다.
HANGUL_MEASURED_WIDTHS = {"4x+3y-12=0": 7205, "y=2x-1": 4525, "y=x+1": 4000, "a=3": 2295, "2x+ay-3=0": 6680,
                          "x+(a-1)y+3=0": 8605, "a={2} over {3}": 2795, "PA^{2}+PB^{2}": 4990, "d^{2}": 975,
                          "12": 1050, "-3": 1490, "A(1,2)": 3135, "x^{2}+y^{2}=25": 5425,
                          "{1} over {2}x-3": 3255, "f(x)=x^{2}-4x+3": 8230, "LEQ": 1050, "a+b": 2080}


def test_equation_width_is_never_narrower_than_hangul():
    from make_hwpx_equation import equation_width
    for script, measured in HANGUL_MEASURED_WIDTHS.items():
        estimated = equation_width(script, 1000)
        assert measured <= estimated <= measured * 1.25, (script, estimated, measured)


def test_equation_width_scales_with_font_size():
    from make_hwpx_equation import equation_width
    assert equation_width("4x+3y-12=0", 1200) == round(equation_width("4x+3y-12=0", 1000) * 1.2)
