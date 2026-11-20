"""스킬 문서 시험이 함께 쓰는 도우미.

문서 시험은 두 가지로 나눈다.
- 승인 문구: 사용자가 승인한 교사 안내 문구(APPROVED). 한 글자도 바뀌면 안 되므로 문장 그대로 찾는다.
- 내부 규칙: Claude가 따르는 규칙 문장. 다듬어도 되므로 같은 줄(문단)에 핵심 낱말이 모두 있는지로 본다.
  규칙 문장을 지우면 그 낱말들이 한 줄에 모이지 않으므로 시험이 깨진다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import build  # noqa: E402

TEACHING_SKILLS = ("lesson-plan", "worksheet", "class-slides", "rubric", "assessment-items", "unit-design")
RECORD_SKILLS = ("subject-record", "activity-record", "behavior-record")
ALL_SKILLS = (*TEACHING_SKILLS, *RECORD_SKILLS)
LESSON_SKILLS = ("lesson-plan", "worksheet", "class-slides")
YEAR_QUESTION_SKILLS = (*LESSON_SKILLS, "assessment-items", "rubric", "unit-design")  # 첫 질문에 학년도 질문을 넣는 스킬
ASSESSMENT_SKILLS = ("rubric", "assessment-items")
RESPONSIBILITY_SKILLS = (*ASSESSMENT_SKILLS, *RECORD_SKILLS)               # 첫 응답에 책임 안내를 쓰는 스킬
# 출력 절 제목: 번호 목록의 마지막 항목이 "확인 필요"여야 한다
OUTPUT_HEADINGS = {"lesson-plan": "## 10. 출력 순서", "worksheet": "## 7. 출력", "class-slides": "## 5. 출력",
                   "rubric": "## 7. 출력 순서", "assessment-items": "## 7. 출력 순서", "unit-design": "## 9. 출력 순서"}

# 사용자가 승인한 교사 안내 문구. 문장 그대로 시험한다 (바꾸려면 사용자 승인이 먼저다)
APPROVED = {
    "책임 안내": "AI가 만드는 것은 초안입니다. 검토와 최종 제출은 선생님의 몫입니다.",
    "평가 확인 항목": "문항, 정답, 배점, 채점 기준을 직접 확인",
    "수행평가 확인 항목": "평가 과제, 배점, 채점 기준을 직접 확인",
    "계정 안전": "학교가 허용한 계정을 쓰시고, 계정 설정에서 대화 내용이 학습에 쓰이지 않도록 되어 있는지 확인해 주세요.",
    "초안 안내": "이 문장은 초안입니다.",
    "장기결석": ("장기 결석 등으로 참여하지 못한 학생은 기재요령에 따라 해당 칸에 사유를 입력해야 합니다. "
               "사유 문구는 학교에서 정한 문구로 직접 입력해 주세요."),
    "기본점수 질문": "채점할 내용이 없는 학생에게 줄 점수는 몇 점인가요?",
    "질문 없이": "질문 없이 바로 만들어 달라고 하시면 기본값으로 만들어 드립니다.",
    "학년도 질문": "이번 학년도(○○○○학년도) 자료인가요, 다음 학년도(○○○○학년도) 자료인가요?",
    "세특 첫 요청": "세특을 쓰려면 수업 활동 내용이 필요합니다.",
    "개인정보 지우기": "올리기 전에 개인정보를 지워 주세요",
    "개인정보 까닭": "학교 밖 서비스로 나갑니다",
    "기호 요청": "출석번호 대신 학생A·B처럼 임의 기호를 써 주세요",
    "PPT 정답 안내": ("이 파일에는 정답 장과 발표자 노트의 정답이 들어 있습니다. "
                   "학생에게 나눠 줄 때는 정답을 뺀 학생용 사본을 쓰세요."),
    "멈춤 안내 첫 줄": "학생 개인정보가 들어 있어 작업을 멈췄습니다. 아직 아무것도 쓰지 않았습니다.",
    "멈춤 안내 새 대화": "이 대화를 삭제하고, 개인정보를 지운 자료를 새 대화에서 다시 올려 주세요.",
    "멈춤 안내 까닭": ("번거로우시겠지만 이유가 있습니다. 자료는 올리는 순간 학교 밖 서비스로 나갑니다. 올라온 뒤에 지워도 이미 "
                   "나간 정보는 되돌릴 수 없습니다. 그래서 반드시 올리기 전에 지워 주셔야 합니다. 제가 대신 지워 드리지 않는 것도 이 때문입니다."),
    "세특 반 전체 안내": "**반 전체에 한 번만 알려 주세요**",
    "세특 메모 안내": "**학생마다 1~3줄 메모면 됩니다**",
    "규정 문장 요청": "학교 학업성적관리규정의 해당 문장을 붙여 주시면 그대로 맞춥니다",
    "나머지 제안": "나머지는 제가 제안한 뒤 확인받겠습니다.",
    "수업 디자인 저장": "선생님 계정에 수업 디자인을 저장해도 될까요?",
    "PPT 첫 질문": ("1. 학년, 교과, 차시 (지도안, 교과서 쪽 PDF, PPT 템플릿이 있으면 함께 올려 주세요)",
                 "2. 슬라이드 수 (기본: 12장 안팎)",
                 "3. 인터넷 자료(영상·사진) 제안이 필요한가요?",
                 "4. 학생에게 나눠 줄 파일인가요? (그렇다면 정답과 노트를 뺀 학생용 사본을 함께 만듭니다)"),
    "수행평가 끝 줄": "배점과 기본점수는 학교 학업성적관리규정과 교과협의회 결정에 맞는지 확인해 주세요.",
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def skill(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def description(name: str) -> str:
    return build.parse_frontmatter(skill(name))["description"]


def section(text: str, start: str, end: str) -> str:
    """start부터 그 뒤 첫 end 앞까지."""
    begin = text.index(start)
    return text[begin:text.index(end, begin + len(start))]


def rule_line(text: str, *words: str) -> str | None:
    """핵심 낱말이 모두 든 첫 줄(문단). 없으면 None."""
    return next((line for line in text.splitlines() if all(word in line for word in words)), None)


def has_rule(text: str, *words: str) -> bool:
    return rule_line(text, *words) is not None


def missing_rules(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    """규칙 이름 → 핵심 낱말 표에서, 한 줄에 낱말이 다 모이지 않는 규칙의 이름들."""
    return [name for name, words in rules.items() if not has_rule(text, *words)]


def numbered_items(part: str) -> list[str]:
    """맨 왼쪽 번호 목록("1. …")의 항목 글."""
    items = []
    for line in part.splitlines():
        head, _, rest = line.partition(". ")
        if head.isdigit() and rest:
            items.append(rest)
    return items
