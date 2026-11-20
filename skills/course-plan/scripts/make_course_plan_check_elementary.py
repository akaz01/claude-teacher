"""초등 교수학습 및 평가 계획 점검 (references/elementary-plan.md).

- 평가 단계(scale)와 성취수준(levels)·채점 기준(criteria) 단계가 같은지, 평가 영역이 있는지
- 2026 필수 항목: AI 도구 활용 유의 사항, 결시자·학적변동자 처리
- 초등에 없는 점수식 표현(%, 반영 비율, 정기시험, 성취도, A~E, 점수 배점)이 자유 글에 섞였는지, 단계 이름이 A~E인지
- 1·2학년 3월 평가 (입학 초기 적응·진단활동 기간)
"""

from __future__ import annotations

import re

AI_WORDS = ("AI", "인공지능")
MONTH = re.compile(r"([0-9]{1,2})\s*월")
FREE_TEXT = ("purpose", "direction", "policy", "cautions", "absence", "use")
SCORE_WORDS = (
    re.compile(r"[0-9]+(?:\.[0-9]+)?\s*%"), re.compile(r"반영\s*비율"), re.compile(r"정기\s*시험"),
    re.compile(r"지필\s*평가"), re.compile(r"(?:중간|기말)\s*고사"), re.compile(r"성취도"), re.compile(r"배점"),
    re.compile(r"(?<![A-Za-z])[A-E]\s*[~∼]\s*[A-E](?![A-Za-z])"), re.compile(r"(?<![0-9.])[0-9]+\s*점(?![검])"),
)
GRADE_NAME = re.compile(r"^[A-Ea-e][+-]?$")
EARLY_GRADES = (1, 2)          # 3월은 입학 초기 적응(1학년 34시간)·진단활동 기간
SHOWN_WORDS = 3


def _score_words(text: str) -> list[str]:
    return list(dict.fromkeys(found.group(0) for pattern in SCORE_WORDS for found in pattern.finditer(text)))


def leak_warnings(evaluation: dict) -> list[str]:
    """초등에 없는 점수·비율·성취도 표현이 자유 글에 섞였는지."""
    places = [(f"evaluation.{key}의 {n}번째", line["text"]) for key in FREE_TEXT
              for n, line in enumerate(evaluation[key], 1)]
    places += [(f"evaluation.items의 {n}번째 method", item["method"]) for n, item in enumerate(evaluation["items"], 1)]
    warnings = []
    for where, text in places:
        if words := _score_words(text):
            shown = ", ".join(f"'{word}'" for word in words[:SHOWN_WORDS])
            warnings.append(f"{where}에 점수식 표현({shown})이 있음: 초등은 점수·반영 비율·성취도(A~E)를 쓰지 않음")
    return warnings


def _item_warnings(evaluation: dict, grade: int) -> list[str]:
    scale, warnings = evaluation["scale"], []
    for number, item in enumerate(evaluation["items"], 1):
        name = f"{number}번째 평가 '{item['element'][:15]}'"
        for key in ("levels", "criteria"):
            if set(item[key]) != set(scale):
                field = "성취수준(levels)" if key == "levels" else "채점 기준(criteria)"
                warnings.append(f"{name}: {field}의 단계 {list(item[key]) or '없음'}가 평가 단계 {scale}와 다름")
        if not item["area"]:
            warnings.append(f"{name}: 평가 영역(area)이 비어 있음")
        if grade in EARLY_GRADES and "3" in MONTH.findall(item["timing"]):
            warnings.append(f"{name}: {grade}학년 3월 평가 '{item['timing']}'는 입학 초기 적응·진단활동 기간과 겹침 "
                            "(보통 4월부터 평가)")
    return warnings


def elementary_warnings(plan: dict) -> list[str]:
    evaluation = plan["evaluation"]
    warnings = [] if evaluation["items"] else ["성취기준별 평가(evaluation.items)가 없음"]
    grades = [name for name in evaluation["scale"] if GRADE_NAME.match(name)]
    if grades:
        warnings.append(f"평가 단계 이름 {grades}가 성취도 등급(A~E)처럼 보임: 초등은 잘함·보통·노력요함 같은 단계 이름을 씀")
    warnings += _item_warnings(evaluation, plan["info"]["grade"]) + leak_warnings(evaluation)
    lines = " ".join(line["text"] for line in evaluation["cautions"])
    if not any(word in lines for word in AI_WORDS):
        warnings.append("평가 시 유의 사항(cautions)에 AI 도구 활용 안내가 없음 (2026 필수)")
    absence = " ".join(line["text"] for line in evaluation["absence"])
    if "결시" not in absence or not any(word in absence for word in ("학적", "전입")):
        warnings.append("결시자·학적변동자 처리(absence)에 결시자와 학적변동(전입) 처리가 모두 있어야 함 (2026 필수)")
    return warnings
