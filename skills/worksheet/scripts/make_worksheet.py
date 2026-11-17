"""학습지 폼 생성기. 간단한 JSON을 파랑 한 계열 머리 띠와 활동 블록이 있는 한글(hwpx) 학습지로 만든다.

같은 JSON에서 학생용과 교사용을 낸다. 교사용은 칸 구성이 학생용과 같고 답이 그 칸에 파랑·굵게로 들어간다.
색은 모든 교과가 같다(앱 디자인 학습지 판 3: 남색·파랑·하늘색). 모든 칸·문단은 한글에서 고칠 수 있다.

입력 JSON (활동지):
{
  "subject": "수학",
  "unit": "일차방정식", "title": "이항을 이용해 방정식 풀기", "lesson": "3/8차시",
  "goal": "학습 목표", "question": "핵심 질문 (선택)",
  "curriculum": "2022 개정", "standards": ["[9수01-01] ..."],   # 교사용 머리에만 (선택)
  "activities": [{"title": "활동 제목", "parts": [
    {"kind": "text", "text": "지시문"},
    {"kind": "card", "label": "개념", "text": "강조 상자"},
    {"kind": "source", "label": "자료", "text": "제시문", "note": "출처 (선택)"},
    {"kind": "lines", "count": 3, "answer": "답"},         # 점선 쓰기 줄
    {"kind": "labels", "rows": [["주장", ""], ["근거", 2], ["결론", {"answer": "답", "lines": 2}]]},
                                                           # 왼쪽 라벨 칸. 숫자는 빈 칸 줄 수, 글은 인쇄
    {"kind": "grid", "header": ["구분", "답"], "rows": [["가", {"answer": "답"}], ["나", ""]],
     "widths": [30, 70], "lines": 2},                      # 칸 값: 글은 인쇄, ""는 빈 칸, {"answer", "lines"}는 답 칸
    {"kind": "frame", "starter": "회색 첫 문장", "lines": 3, "label": "내 설명", "answer": "이어 쓸 답"},
    {"kind": "frame", "text": "앞 문장 [[답]] 뒤 문장"},   # 문장 틀. starter와 text 가운데 하나
    {"kind": "steps", "items": ["할 일", {"name": "예측", "text": "할 일", "lines": 2, "answer": "답"}]},
                                                           # 단계 표. 이름이 없으면 1단계, 2단계...
    {"kind": "space", "lines": 6, "label": "풀이", "answer": "답"},   # 줄 없는 빈 공간
    {"kind": "hint", "label": "도움말", "text": "다음 문항 바로 앞에 놓을 도움"},
    {"kind": "choices", "label": "보기", "items": ["낱말", "낱말"], "answer": "낱말"},   # 보기 상자
    {"kind": "challenge", "label": "도전 과제", "text": "과제", "lines": 3, "answer": "답"}
  ],
   "time": "10분", "model": "칸보다 긴 예시 답안", "accept": "인정 답안", "point": "채점 포인트", "tip": "지도 메모"
                                                           # 활동 뒤 교사용 칸에만 나옴 (모두 선택)
  }],
  "check": ["나는 ~할 수 있다."],          # 스스로 평가 문장 (선택)
  "closing": "auto"                       # auto(별점 평가 + 배움 성찰) / check(별점) / reach(예·아니요) / reflect / none
}

입력 JSON (개념 정리 학습지): "topics"가 있으면 이 형식으로 만든다. 1쪽 개념 정리, 2쪽 형성평가.
{
  "subject": "한국사", "unit": "대한민국의 발전", "lesson": "주제 19",
  "meta": "고1 한국사2 · 대한민국의 발전 · 주제 19",        # 머리 띠 윗줄 (없으면 subject·unit·lesson으로)
  "title": "5·16 군사 정변으로 민주주의가 후퇴하다", "sub": "교과서 92~95쪽",
  "goal": ["① …", "② …"], "question": "핵심 질문 (선택)",
  "curriculum": "2022 개정", "standards": ["[10한사2-02-03] …"],     # 교사용 머리에만 (선택)
  "topics": [{"title": "주제 이름", "tag": "1961~1963 (선택)", "rows": [
    {"label": "이름표", "lines": ["한 줄에 하나씩", "[[빈칸]]이 있는 줄"]}]}],
  "terms": [["용어", "풀이"]],                                      # 오른쪽 '용어 풀이' 칸 (선택)
  "side": {"title": "한눈에 보는 연표", "items": [["1961", "5·16 군사 정변"]]},   # 오른쪽 둘째 칸 (선택)
  "questions": [                                                   # 형성평가 (선택). 정답은 학생용에 안 들어감
    {"kind": "선택형", "text": "문항", "source": "제시문(선택)", "source_note": "— 출처(선택)",
     "options": ["…", "…", "…", "…", "…"], "answer": 1, "cols": 3, "explain": "해설"},
    {"kind": "단답형", "text": "문항", "answer": "답"},
    {"kind": "O·X", "text": "문항", "answer": "X", "explain": "해설"},
    {"kind": "서술형", "text": "문항", "starter": "성과는 …, 한계는 …", "lines": 3, "answer": "예시 답", "point": "채점 기준"}],
  "challenge": {"text": "새 상황에 적용하는 과제", "lines": 3, "answer": "예시 답", "point": "채점 기준"},
                                                                   # 도전 과제 (선택). 형성평가 뒤, 학생에게는 '도전 과제' 칸으로 나옴
  "check": ["나는 … 설명할 수 있다."]                               # 도달 점검 (선택)
}
오른쪽 칸은 줄 높이에 맞춰 칸을 합쳐 나눈다(한글 표의 칸 합치기). 모두 한글 표와 문단이라 한글에서 글자·칸을 고칠 수 있다.

빈칸: 어느 글이든 [[답]]이라고 쓴다. 학생용은 답 길이와 상관없이 같은 너비의 괄호, 교사용은 괄호 안에 답이 들어간다.
answer, time, model, accept, point, tip, curriculum, standards는 학생용 파일에 들어가지 않는다.

사용법:
    python make_worksheet.py 입력.json 학습지_학생용.hwpx
    python make_worksheet.py 입력.json 학습지_교사용.hwpx --teacher
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if not (SCRIPT_DIR / "make_hwpx.py").exists():      # 저장소에서 직접 실행할 때
    sys.path.insert(0, str(SCRIPT_DIR.parents[2] / "shared" / "scripts"))

import make_hwpx  # noqa: E402
import make_worksheet_concept  # noqa: E402
# 색과 [[답]] 표기는 개념 정리 모듈 한 곳에 둔다 (앱 디자인 학습지 판 3: 모든 교과가 같은 파랑 한 계열)
from make_worksheet_concept import (  # noqa: E402
    BLANK_MARK, GRAY, NAVY, SKY_LINE, TINT, TYPED_BLANK, WHITE, has_answer, text_list)
from make_worksheet_concept import ANS as ANSWER_COLOR, BLUE as ACCENT  # noqa: E402,F401
from make_worksheet_concept import CREAM, GOLD, PALE, ROW_LINE, SKY  # noqa: E402,F401  (시험이 확인하는 하우스 스타일 값)

LINE = SKY_LINE
STARS = "☆  ☆  ☆  ☆  ☆"
BLANK = "(            )"
TEACHER_FLAG = "--teacher"
CLOSINGS = ("auto", "check", "reach", "reflect", "none")
LABEL_WIDTHS = [18, 82]
CARD_WIDTHS = [13, 87]
# 활동 뒤 교사용 칸: (입력 이름, 칸 이름, 답처럼 파랑·굵게로 쓰는가)
NOTE_FIELDS = (("time", "예상 시간", False), ("model", "예시 답안", True), ("accept", "인정 답안", True),
               ("point", "채점 포인트", False), ("tip", "지도 메모", False))


@dataclass(frozen=True)
class Look:
    dark: str = NAVY
    tint: str = TINT
    teacher: bool = False

    @property
    def mark(self) -> dict:
        """칸 글 속 **답**을 파랑으로 칠하는 값. 학생용에는 넣지 않는다."""
        return {"mark_color": ANSWER_COLOR} if self.teacher else {}


def _head_row(label: str, text: str, look: Look, bold: bool = False) -> list[dict]:
    return [{"text": label, "fill": look.tint, "color": look.dark, "bold": True, "align": "center",
             "valign": "center", "edges": "none"},
            {"text": text, "bold": bold, "edges": "bottom_dot", "edge_color": LINE, "valign": "center"}]


def _teacher_head(doc: dict, look: Look) -> list[dict]:
    if not look.teacher:
        return []
    rows = []
    if doc.get("curriculum"):
        rows.append(_head_row("교육과정", doc["curriculum"], look))
    if doc.get("standards"):
        rows.append(_head_row("성취기준", "\n".join(text_list(doc["standards"], "standards")), look))
    return [{"type": "table", "widths": [14, 86], "teacher_only": True, "rows": rows}] if rows else []


def _head(doc: dict, look: Look) -> list[dict]:
    band = {"fill": look.dark, "edges": "none"}
    rows = [_head_row("학습 목표", "\n".join(text_list(doc["goal"], "goal")), look)]
    if doc.get("question"):
        rows.append(_head_row("핵심 질문", doc["question"], look, bold=True))
    band_text = (doc["subject"], doc["unit"], doc.get("lesson"), "교사용" if look.teacher else None)
    return [
        {"type": "table", "widths": [100], "gap": "tight", "border": "none", "rows": [
            [{**band, "text": "  |  ".join(filter(None, band_text)), "color": look.tint, "bold": True}],
            [{**band, "text": doc["title"], "color": WHITE, "bold": True, "size": "title"}],
        ]},
        {"type": "table", "widths": [100], "gap": "tight", "rows": [
            [{"text": "(     )학년  (     )반  (     )번    이름:                         ",
              "edges": "bottom", "edge_color": look.dark}]]},
        {"type": "table", "widths": [14, 86], "rows": rows},
        *_teacher_head(doc, look),
    ]


def _section(number: int, title: str, dark: str) -> dict:
    return {"type": "table", "widths": [6, 94], "keep_with_next": True, "rows": [[
        {"text": str(number), "fill": dark, "color": WHITE, "bold": True, "size": "large", "align": "center",
         "valign": "center", "edges": "none"},
        {"text": title, "color": dark, "bold": True, "size": "large", "valign": "center",
         "edges": "bottom_thick", "edge_color": dark}]]}


def _box(text, lines: int = 0, **options) -> dict:
    return {"text": text, "edges": "all", "edge_color": LINE, "lines": lines, **options}


def _slot(answer, lines: int, look: Look, **options) -> dict:
    """학생이 쓰는 칸. 학생용은 비워 두고 교사용은 같은 칸에 답을 파랑·굵게 넣는다."""
    if look.teacher and has_answer(answer):
        return _box(answer, lines, **{**options, "color": ANSWER_COLOR, "bold": True})
    return _box("", lines, **options)


def _label_cell(label: str, look: Look) -> dict:
    return _box(label, fill=look.tint, color=look.dark, bold=True, align="center", valign="center")


def _labeled(label: str | None, cell: dict, look: Look) -> dict:
    """글이 든 칸 하나를 표로. 이름이 있으면 왼쪽에 이름 칸을 둔다."""
    if label:
        return {"type": "table", "widths": LABEL_WIDTHS, "rows": [[_label_cell(label, look), cell]]}
    return {"type": "table", "widths": [100], "rows": [[cell]]}


def _label_row(label: str, value, look: Look) -> list[dict]:
    if isinstance(value, dict):
        answer = _slot(value.get("answer"), value.get("lines", 1), look)
    else:
        answer = _box("", value) if isinstance(value, int) else _box(value or "", 0 if value else 1)
    return [_label_cell(label, look), answer]


def _source(part: dict, look: Look) -> dict:
    note = f"\n출처: {part['note']}" if part.get("note") else ""
    return {"type": "table", "widths": [100], "rows": [
        [{"text": part.get("label", "자료"), "fill": look.tint, "color": look.dark, "bold": True, "edges": "none"}],
        [{"text": part["text"] + note, "edges": "all_dot", "edge_color": look.dark}]]}


def _grid_cell(value, lines: int, look: Look) -> dict:
    if isinstance(value, dict):
        return _slot(value.get("answer"), value.get("lines", lines), look, valign="center")
    return _box(value, 0 if value else lines, valign="center")


def _grid(part: dict, look: Look) -> dict:
    lines = part.get("lines", 1)
    return {"type": "table", "widths": part.get("widths"), "rows": [
        [_box(text, fill=look.dark, color=WHITE, bold=True, align="center", valign="center")
         for text in part["header"]],
        *[[_grid_cell(value, lines, look) for value in row] for row in part["rows"]]]}


def _lines(part: dict, look: Look) -> dict:
    count = part["count"]
    answers = make_hwpx.as_text(part.get("answer")).split("\n")
    answers = answers[:count - 1] + ["\n".join(answers[count - 1:])]    # 줄 수는 학생용과 같게 둔다
    answers += [""] * (count - len(answers))
    return {"type": "table", "widths": [100], "rows": [
        [_slot(answer, 1, look, edges="bottom_dot")] for answer in answers]}


def _frame(part: dict, look: Look) -> dict:
    """문장 틀. starter는 회색 첫 문장, text는 앞뒤가 인쇄된 문장이다."""
    body = part.get("starter") or part.get("text")
    if not body:
        raise ValueError("frame에는 starter나 text가 필요함")
    answer = part.get("answer")
    shown = f"{body} **{answer}**" if look.teacher and has_answer(answer) else body
    gray = {"color": GRAY} if part.get("starter") else {}
    lines = part.get("lines", 0)
    top = {"valign": "top"} if lines else {}     # 이어 쓸 자리가 첫 문장 아래에 남게 둔다
    return _labeled(part.get("label"), _box(shown, lines, **gray, **top, **look.mark), look)


def _steps(part: dict, look: Look) -> dict:
    items = [{"text": item} if isinstance(item, str) else item for item in part["items"]]
    writing = any("lines" in item or "answer" in item for item in items)
    rows = []
    for number, item in enumerate(items, 1):
        row = [_label_cell(item.get("name", f"{number}단계"), look), _box(item["text"])]
        rows.append(row + [_slot(item.get("answer"), item.get("lines", 1), look)] if writing else row)
    return {"type": "table", "widths": [14, 43, 43] if writing else [14, 86], "rows": rows}


def _hint(part: dict, look: Look) -> dict:
    dotted = {"edges": "all_dot", "edge_color": look.dark}
    return {"type": "table", "widths": CARD_WIDTHS, "keep_with_next": True, "rows": [[
        {**dotted, "text": part.get("label", "도움말"), "color": look.dark, "bold": True},
        {**dotted, "text": part["text"]}]]}


def _choices(part: dict, look: Look) -> dict:
    answer = part.get("answer")
    answers = answer if isinstance(answer, list) else [answer]
    shown = [f"**{item}**" if look.teacher and item in answers else str(item) for item in part["items"]]
    block = _labeled(part.get("label", "보기"), _box("        ".join(shown), **look.mark), look)
    return {**block, "keep_with_next": True}


def _challenge(part: dict, look: Look) -> dict:
    return {"type": "table", "widths": CARD_WIDTHS, "rows": [
        [{"text": part.get("label", "도전 과제"), "fill": look.dark, "color": WHITE, "bold": True, "edges": "none"},
         {"text": part["text"], "fill": look.tint, "edges": "none"}],
        [_slot(part.get("answer"), part.get("lines", 3), look, colspan=2)]]}


def _space(part: dict, look: Look) -> dict:
    return _labeled(part.get("label"), _slot(part.get("answer"), part.get("lines", 5), look), look)


def _card(part: dict, look: Look) -> dict:
    return {"type": "table", "widths": CARD_WIDTHS, "rows": [[
        {"text": part["label"], "fill": look.dark, "color": WHITE, "bold": True, "align": "center",
         "valign": "center", "edges": "none"},
        {"text": part["text"], "fill": look.tint, "edges": "none", "valign": "center"}]]}


def _text(part: dict, look: Look) -> dict:
    return {"type": "paragraph", "text": part["text"], "keep_with_next": True}


def _labels(part: dict, look: Look) -> dict:
    return {"type": "table", "widths": part.get("widths", LABEL_WIDTHS),
            "rows": [_label_row(label, value, look) for label, value in part["rows"]]}


PART_MAKERS = {"text": _text, "card": _card, "source": _source, "lines": _lines, "labels": _labels, "grid": _grid,
               "frame": _frame, "steps": _steps, "space": _space, "hint": _hint, "choices": _choices,
               "challenge": _challenge}


def _part(part: dict, look: Look) -> dict:
    kind = part.get("kind")
    if kind not in PART_MAKERS:
        raise ValueError(f"kind '{kind}'은 쓸 수 없음 ({'/'.join(PART_MAKERS)})")
    return PART_MAKERS[kind](part, look)


def _teacher_notes(activity: dict, look: Look) -> list[dict]:
    """활동 바로 뒤에 놓는 교사용 칸. 칸보다 긴 답, 채점 포인트, 지도 메모가 여기에 든다."""
    if not look.teacher:
        return []
    answer_look = {"color": ANSWER_COLOR, "bold": True}
    rows = [[_label_cell(label, look), _box(activity[key], **(answer_look if is_answer else {}))]
            for key, label, is_answer in NOTE_FIELDS if activity.get(key)]
    return [{"type": "table", "widths": LABEL_WIDTHS, "teacher_only": True, "rows": rows}] if rows else []


def _closing(doc: dict, look: Look) -> list[dict]:
    choice = doc.get("closing", "auto")
    if choice not in CLOSINGS:
        raise ValueError(f"closing '{choice}'은 쓸 수 없음 ({'/'.join(CLOSINGS)})")
    items = text_list(doc.get("check"), "check")
    if choice in ("check", "reach") and not items:
        raise ValueError(f"closing '{choice}'에는 'check' 문장이 필요함")
    title = {"fill": look.tint, "color": look.dark, "bold": True, "align": "center"}
    blocks: list[dict] = []
    if choice == "reach":
        blocks.append({"type": "table", "widths": [70, 15, 15], "rows": [
            [_box("도달 점검", **title), _box("예", **title), _box("아니요", **title)],
            *[[_box(item), _box(""), _box("")] for item in items]]})
    if choice in ("auto", "check") and items:
        blocks.append({"type": "table", "widths": [66, 34], "rows": [
            [_box("스스로 평가", **title), _box("별에 색칠해 보세요", **title)],
            *[[_box(item, valign="center"), _box(STARS, align="center", valign="center")] for item in items]]})
    if choice in ("auto", "reflect"):
        blocks.append({"type": "table", "widths": [50, 50], "rows": [
            [_box("오늘 새롭게 알게 된 점", **title), _box("더 알고 싶은 점", **title)],
            [_box("", 2), _box("", 2)]]})
    return blocks


def _student_text(text) -> str:
    return BLANK_MARK.sub(BLANK, text) if isinstance(text, str) else text


def _fill_cell(cell: dict, look: Look) -> dict:
    """칸 글의 [[답]]을 푼다. 모든 표를 이 한 곳에서 지나가게 해서 답이 그대로 남는 길을 막는다."""
    text = cell.get("text")
    if not isinstance(text, str) or not BLANK_MARK.search(text):
        return cell
    if look.teacher:
        return {**cell, "text": BLANK_MARK.sub(r"( **\1** )", text), **look.mark}
    return {**cell, "text": _student_text(text)}


def _fill_blanks(block: dict, look: Look) -> dict:
    if block["type"] == "paragraph" and BLANK_MARK.search(block["text"]):
        # 문장 속 답에 색을 넣으려면 칸이어야 한다. 학생용도 같은 칸으로 둔다
        block = {"type": "table", "widths": [100], "keep_with_next": True,
                 "rows": [[{"text": block["text"], "edges": "none"}]]}
    if block["type"] != "table":
        return block
    return {**block, "rows": [[_fill_cell(cell, look) for cell in row] for row in block["rows"]]}


def _centered(table: dict) -> dict:
    """표 안 글자의 기본 정렬은 가운데다."""
    rows = [[{"align": "center", "valign": "center", **cell} for cell in row] for row in table["rows"]]
    return {**table, "rows": rows}


# ---------------------------------------------------------------- 개념 정리 입력 검사

CIRCLED_MAX = len(make_worksheet_concept.CIRCLED)


def _text(value, name: str) -> str:
    """글 하나(숫자는 글로, 없으면 빈 글). 모양이 틀리면 위치를 붙인 한국어 오류."""
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{name}은 글이어야 함 (받은 값: {value!r})")
    return str(value)


def _object(value, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name}은 {{ }} 모양의 객체여야 함 (받은 값: {value!r})")
    return value


def _pairs(value, name: str) -> list:
    """[[이름, 글]] 쌍의 목록. 글 자리는 글 목록도 된다(줄바꿈으로 이음)."""
    if not isinstance(value, list):
        raise ValueError(f"'{name}'은 [이름, 글] 쌍의 목록이어야 함 (받은 값: {value!r})")
    pairs = []
    for number, pair in enumerate(value, 1):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"'{name}' {number}번째 항목은 [이름, 글] 쌍이어야 함 (받은 값: {pair!r})")
        pairs.append([_text(pair[0], f"'{name}' {number}번째 이름"),
                      "\n".join(text_list(pair[1], f"{name} {number}번째 글"))])
    return pairs


def _topic(number: int, raw) -> dict:
    topic = _object(raw, f"주제 {number}")
    rows = topic.get("rows")
    if not topic.get("title") or not rows:
        raise ValueError(f"주제 {number}에는 title과 rows가 필요함")
    if not isinstance(rows, list):
        raise ValueError(f"주제 {number}의 rows는 줄의 목록이어야 함")
    lines = []
    for index, item in enumerate(rows, 1):
        row = _object(item, f"주제 {number}의 {index}번째 줄")
        if not row.get("label") or not row.get("lines"):
            raise ValueError(f"주제 {number}의 줄에는 label과 lines가 필요함")
        lines.append({**row, "label": _text(row["label"], f"주제 {number}의 {index}번째 줄 label"),
                      "lines": text_list(row["lines"], f"주제 {number}의 {index}번째 줄 lines")})
    return {**topic, "title": _text(topic["title"], f"주제 {number} title"),
            "tag": _text(topic.get("tag"), f"주제 {number} tag"), "rows": lines}


def _int_in(value, name: str, low: int, high: int, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name}은 {low}~{high} 사이의 정수여야 함 (받은 값: {value!r})")
    return value


def _question(number: int, raw) -> dict:
    where = f"문항 {number}"
    item = _object(raw, where)
    kinds = make_worksheet_concept.QUESTION_KINDS
    kind = item.get("kind")
    if kind not in kinds or not item.get("text"):
        raise ValueError(f"{where}: kind({'/'.join(kinds)})와 text가 필요함")
    fields = {key: _text(item.get(key), f"{where} {key}") for key in
              ("source", "source_note", "starter", "explain", "point")}
    fields["text"] = _text(item["text"], f"{where} text")
    answer = item.get("answer")
    if answer is not None and (isinstance(answer, bool) or not isinstance(answer, (str, int, float))):
        raise ValueError(f"{where} answer는 글 또는 숫자여야 함 (받은 값: {answer!r})")
    if kind == "선택형":
        options = text_list(item.get("options"), f"{where} options")
        if not 2 <= len(options) <= CIRCLED_MAX:
            raise ValueError(f"{where}: 선택형 문항에는 보기 2~{CIRCLED_MAX}개(options)가 필요함")
        fields["options"] = options
        fields["cols"] = _int_in(item.get("cols"), f"{where} cols", 1, CIRCLED_MAX, 3)
    if kind == "서술형":
        low, high = make_worksheet_concept.ESSAY_LINES
        fields["lines"] = _int_in(item.get("lines"), f"{where} lines", low, high, 3)
    return {**item, **fields}


def _challenge_item(raw) -> dict | None:
    """개념 정리의 선택 항목 challenge(도전 과제). 글 하나나 {text, lines, answer, point}. 없으면 None."""
    if raw is None or raw == "":
        return None
    item = {"text": raw} if isinstance(raw, str) else _object(raw, "'challenge'")
    text = _text(item.get("text"), "challenge text")
    if not text.strip():
        raise ValueError("'challenge'에는 text(과제 글)가 필요함")
    answer = item.get("answer")
    if answer is not None and (isinstance(answer, bool) or not isinstance(answer, (str, int, float))):
        raise ValueError(f"challenge answer는 글 또는 숫자여야 함 (받은 값: {answer!r})")
    low, high = make_worksheet_concept.ESSAY_LINES
    return {"text": text, "lines": _int_in(item.get("lines"), "challenge lines", low, high, 3), "answer": answer,
            "point": _text(item.get("point"), "challenge point")}


def normalize_concept(doc: dict) -> dict:
    """개념 정리 입력의 모양을 검사하고 정리한 새 값을 돌려준다. 목록 자리의 글 하나는 [글]로 감싸고, 틀린 모양은
    '주제 2', '문항 3'처럼 위치를 붙인 한국어 오류로 알린다."""
    for key in ("title", "goal", "topics"):
        if not doc.get(key):
            raise ValueError(f"'{key}' 값이 필요함")
    texts = {key: _text(doc.get(key), f"'{key}'") for key in
             ("subject", "unit", "lesson", "meta", "title", "sub", "question", "curriculum", "foot")}
    if not isinstance(doc["topics"], list):
        raise ValueError("'topics'는 주제의 목록이어야 함")
    questions = doc.get("questions") or []
    if not isinstance(questions, list):
        raise ValueError("'questions'는 문항의 목록이어야 함")
    side = _object(doc["side"], "'side'") if doc.get("side") else None
    return {**doc, **texts, "goal": text_list(doc["goal"], "goal"),
            "standards": text_list(doc.get("standards"), "standards"), "check": text_list(doc.get("check"), "check"),
            "topics": [_topic(number, raw) for number, raw in enumerate(doc["topics"], 1)],
            "terms": _pairs(doc["terms"], "terms") if doc.get("terms") else [],
            "side": ({**side, "title": _text(side.get("title") or "한눈에 보는 연표", "'side' title"),
                      "items": _pairs(side.get("items"), "side.items")} if side else None),
            "questions": [_question(number, raw) for number, raw in enumerate(questions, 1)],
            "challenge": _challenge_item(doc.get("challenge"))}


def _checked_part(part, look: Look, number: int, index: int) -> dict:
    """활동 부품 하나. 값 모양이 틀려 생기는 파이썬 오류는 위치를 붙인 한국어 오류로 바꾼다."""
    try:
        return _part(part, look)
    except (TypeError, AttributeError, IndexError) as error:
        kind = part.get("kind") if isinstance(part, dict) else part
        raise ValueError(f"활동 {number}의 {index}번째 부품({kind}): "
                         "값의 모양이 맞지 않음 (목록·글·숫자 자리를 확인하세요)") from error


def build_spec(doc: dict, teacher: bool = False) -> dict:
    if not isinstance(doc, dict):
        raise ValueError("입력은 { } 모양의 객체여야 함")
    if "topics" in doc:
        return make_worksheet_concept.build_concept_spec(normalize_concept(doc), teacher=teacher)
    for key in ("subject", "unit", "title", "goal", "activities"):
        if not doc.get(key):
            raise ValueError(f"'{key}' 값이 필요함")
    if not isinstance(doc["activities"], list):
        raise ValueError("'activities'는 활동의 목록이어야 함")
    look = Look(teacher=teacher)
    blocks = _head(doc, look)
    for number, activity in enumerate(doc["activities"], 1):
        blocks.append(_section(number, activity["title"], look.dark))
        blocks.extend(_checked_part(part, look, number, index)
                      for index, part in enumerate(activity.get("parts", []), 1))
        blocks.extend(_teacher_notes(activity, look))
    blocks.extend(_closing(doc, look))
    return _finish(doc, blocks, look)


def _finish(doc: dict, blocks: list[dict], look: Look) -> dict:
    """빈칸을 풀고 표 글을 가운데로 맞춘 뒤 문서 명세로 묶는다."""
    blocks = [_fill_blanks(block, look) for block in blocks]
    blocks = [_centered({"gap": "small", **block}) if block["type"] == "table"
              else block if block["type"] == "page_break" else {"align": "center", **block}
              for block in blocks]
    return {"doc_title": _student_text(doc["title"]), "margins": "narrow", "page": "compact",
            "page_numbers": "center", "blocks": blocks}


def _open_cells(part: dict) -> int:
    """답이 적히지 않은 칸 수. 인쇄된 글이나 [[답]]이 있는 칸은 세지 않는다."""
    kind = part.get("kind")
    if kind in ("lines", "space", "challenge"):
        return 0 if has_answer(part.get("answer")) else 1
    if kind == "frame":
        return 0 if has_answer(part.get("answer")) or BLANK_MARK.search(part.get("text", "")) else 1
    if kind == "text":
        return len(TYPED_BLANK.findall(part["text"]))
    if kind == "labels":
        return sum(_is_open(value) or isinstance(value, int) for _, value in part["rows"])
    if kind == "grid":
        return sum(_is_open(value) for row in part["rows"] for value in row)
    if kind == "steps":
        return sum(isinstance(item, dict) and "lines" in item and not has_answer(item.get("answer"))
                   for item in part["items"])
    return 0


def _is_open(value) -> bool:
    return value == "" or (isinstance(value, dict) and not has_answer(value.get("answer")))


def unanswered(doc: dict) -> list[str]:
    """교사용에 답이 비는 칸을 활동별로 알린다. 예시 답안·인정 답안·채점 포인트가 있는 활동은 넘어간다."""
    if "topics" in doc:
        return make_worksheet_concept.unanswered_concept(normalize_concept(doc))
    messages = []
    for number, activity in enumerate(doc["activities"], 1):
        if any(activity.get(key) for key in ("model", "accept", "point")):
            continue
        count = sum(_open_cells(part) for part in activity.get("parts", []))
        if count:
            messages.append(f"활동 {number}: 답이 없는 칸 {count}곳")
    return messages


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    teacher = TEACHER_FLAG in args
    paths = [arg for arg in args if arg != TEACHER_FLAG]
    if len(paths) != 2:
        sys.stderr.write(f"사용법: python make_worksheet.py 입력.json 출력.hwpx [{TEACHER_FLAG}]\n")
        return 2
    try:
        doc = json.loads(Path(paths[0]).read_text(encoding="utf-8-sig"))
        warnings = make_hwpx.build_hwpx(build_spec(doc, teacher=teacher), Path(paths[1]))
        messages = warnings + [f"주의: {item}" for item in (unanswered(doc) if teacher else [])]
    except KeyError as error:
        sys.stderr.write(f"만들지 못함: '{error.args[0]}' 값이 필요함\n")
        return 1
    except json.JSONDecodeError as error:
        sys.stderr.write(f"만들지 못함: JSON 모양이 맞지 않음 ({error.lineno}째 줄 {error.colno}째 글자 근처)\n")
        return 1
    except (TypeError, AttributeError, IndexError):
        sys.stderr.write("만들지 못함: 입력 값의 모양이 맞지 않음 (목록·글·숫자 자리를 확인하세요)\n")
        return 1
    except (ValueError, OSError) as error:
        sys.stderr.write(f"만들지 못함: {error}\n")
        return 1
    for message in messages:        # 생성기 경고는 "주의:", "확인:"이 이미 붙어 있다
        sys.stderr.write(f"{message}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
