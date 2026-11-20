"""단원 설계서 한글(hwpx) 모양: 앱 디자인 캔버스(samples/app-sample/write_unit_canvas.py)와 같은 짜임.

진한 청록 한 계열 + 황토 포인트(학습지의 파랑과 구별되는 색). 흑백 인쇄에서도 갈리게 진한 바탕엔 흰 글자,
연한 바탕엔 진한 글자를 쓴다. 머리 띠 바탕은 종이 기준 그라데이션 사각형, 칩·번호·글자 상자는 한글 도형(글상자),
나머지는 한글 표다. 그림 파일을 쓰지 않으므로 교사가 한글에서 글·색·칸을 모두 고칠 수 있다.
크기는 앱 화면 px(1px = 0.75pt). 상자(머리띠 상자, GRASPS 칸, 강조 상자, 평가 배치)는 keep_together라
쪽 경계에서 갈라지지 않고 통째로 다음 쪽으로 간다. 머리 행이 있는 표는 짧아도 쪽 끝에서 행 단위로 나뉘고
(split_rows: 통째로 넘어가 앞 쪽 아래가 비지 않게) 머리 행이 쪽마다 되풀이된다.
칩 글은 너비 한도(CHIP_MAX_W 등)를 넘으면 뒤를 줄여 '…'를 붙인다 (경고는 make_unit_design이 낸다).
"""

from __future__ import annotations

import re

# ---- 색 (단원 설계서 판: 진한 청록 + 황토 포인트)
DEEP, TEAL = "#0F4A46", "#1F7A72"                       # 머리 띠·머리띠·진한 칩 / 번호 칸·선·강조 글
MINT, MINT_LINE, PALE, TINT = "#E5F2F0", "#A8D2CB", "#F4FAF9", "#DCEFEC"
BAND_TEXT, INK, MUTED, WHITE = "#D6EEEA", "#1B2A2A", "#4F5F5D", "#FFFFFF"
GOLD, CREAM, GOLD_LINE, FILL = "#A8670F", "#FFF6E3", "#E6C383", "#FFEFC2"

# ---- 쪽 모양 (px). 편집 용지: A4 세로, 좌우 15mm(margins "narrow"), 위 40px·아래 꼬리말 자리(page "app")
PAGE_W = 794
BODY_X, BODY_W = 60, 672          # 표 가장자리 = 여백 15mm + 표 바깥 여백 1mm
BAND_H = 128                      # 1쪽 머리 띠 높이 (쪽 위·양옆 끝까지)
TOP_MARGIN = 54                   # 본문 첫 블록이 시작하는 자리 어림: 위 여백 40px + 머리 띠를 단 빈 문단들
GAP, SMALL_GAP = 14, 8            # 블록 사이, 소제목과 그 아래 블록 사이
THIN, THICK, BOLD = 0.25, 0.4, 0.5    # 선 굵기 mm: 1px, 1.5px, 2px
SERIF = "myeongjo"                # HY견명조: 앱의 명조 제목(Hahmlet)에 가장 가까운 한컴 기본 글꼴
SANS_RATIO, SERIF_RATIO = 92, 85  # 장평 %: 앱 글꼴 너비에 맞춘다
CHECK = "[확인 필요]"
TIMELINE_PER_ROW = 9              # 평가 배치 한 줄의 차시 수 (표 열 수 한도 30 안)
ELEMENT_TYPES = ("지식⋅이해", "과정⋅기능", "가치⋅태도")
QUESTION_TYPES = ("사실", "개념", "논쟁")
GRASPS_PARTS = (("G", "목표", "goal"), ("R", "역할", "role"), ("A", "청중", "audience"),
                ("S", "상황", "situation"), ("P", "결과물", "product"), ("S", "기준", "standards"))
# 평가 칩 (바탕, 글자, 테두리): 흑백에서도 갈리게 테두리만 / 연한 바탕 / 진한 바탕 / 노랑 포인트
KIND_LOOK = {"진단": (WHITE, DEEP, DEEP), "형성": (TINT, DEEP, MINT_LINE), "수행": (DEEP, WHITE, None),
             "지필": (CREAM, GOLD, GOLD_LINE)}
RUN_NOTE = ("수행과제는 수업 시간 안에서 초안 → 피드백 → 수정으로 마칩니다. 모둠으로 하면 개인 산출물을 따로 받습니다. "
            "배점과 단계 점수는 학교 학업성적관리규정에 맞춰 채점기준표에서 정합니다.")
NEXT_NOTE = "아래 요청 문장을 그대로 보내면 이 설계서의 값을 넘겨받아 이어서 만듭니다."
CHIP_MAX_W, BAND_CHIP_MAX_W, LABEL_MAX_W = 220, 150, 260   # 칩·머리 띠 칩(세 개가 한 줄)·차시 밖 평가 글 너비 한도 px
CHIP_PAD, LABEL_PAD = 20, 8                                 # 칩·글상자 좌우 여백 합 px
EM = {"han": 1.0, "digit": 0.55, "latin": 0.52, " ": 0.35, "narrow": 0.22}
PX_PER_PT = 96 / 72


# ---------------------------------------------------------------- 글 도우미

def text_of(value) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if str(item).strip())
    return "" if value is None else str(value).strip()


def lines_of(value) -> list[str]:
    return [line for line in text_of(value).split("\n") if line.strip()]


def codes_of(items) -> list[str]:
    if isinstance(items, str):          # 목록 대신 코드 하나를 글로 준 경우
        items = [items]
    return [text_of(code) for code in (items or []) if text_of(code)]


def kind_of(value) -> str:
    """평가 종류 글: 띄어쓰기와 끝의 '평가'를 뗀다 ("수행평가", "수행 평가" → "수행")."""
    text = re.sub(r"\s+", "", text_of(value))
    return text[:-2] if text.endswith("평가") and len(text) > 2 else text


def text_px(text: str, pt: float) -> float:
    """맑은 고딕(장평 92%) 글 한 줄의 너비 어림 (px)."""
    total = sum(EM["narrow"] if char in "·.,:()'" else EM[" "] if char == " " else EM["digit"] if char.isdigit()
                else EM["latin"] if char.isascii() else EM["han"] for char in text)
    return total * pt * PX_PER_PT * SANS_RATIO / 100


def shape_width(text: str, pad: float = CHIP_PAD) -> int:
    """9pt 굵은 글 한 줄을 담는 칩·글상자 너비 (px)."""
    return round(text_px(text, 9) * 1.06 + pad)


def too_long(text: str, max_w: float, pad: float = CHIP_PAD) -> bool:
    return shape_width(text, pad) > max_w


def fit(text: str, max_w: float, pad: float = CHIP_PAD) -> str:
    """칩 너비 한도를 넘는 글은 뒤를 줄이고 '…'를 붙인다."""
    if not too_long(text, max_w, pad):
        return text
    text = text[:int(max_w)]                  # 글자 하나는 2px보다 넓으므로 미리 잘라 반복을 줄인다
    while text and too_long(text + "…", max_w, pad):
        text = text[:-1]
    return text.rstrip() + "…"


# ---------------------------------------------------------------- 칸·도형 도우미

def line(width: float = THIN, color: str = MINT_LINE, kind: str = "SOLID") -> list:
    return [kind, width, color]


def sides(which: str, edge: list) -> dict:
    """'lrtb' 가운데 고른 변에 같은 선."""
    return {name: edge for name in ("left", "right", "top", "bottom") if name[0] in which}


GRID = sides("lrtb", line())


def cell(content=None, **options) -> dict:
    """표 칸. 기본은 테두리 없음·가운데 정렬·9pt(앱 12px)·줄 간격 150%."""
    pad = options.pop("pad", (6, 6, 4, 4))
    base = {"edges": "none", "valign": "center", "align": "center", "pad_px": list(pad), "color": INK, "size": 9,
            "spacing": 150, "ratio": SERIF_RATIO if options.get("font") == SERIF else SANS_RATIO, "font_space": True}
    if isinstance(content, list):
        base["content"] = content
    elif content is not None:
        base["text"] = content
    return {**base, **options}


def table(widths: list, rows: list, above: float = GAP, keep: bool = True, **options) -> dict:
    return {"type": "table", "widths": widths, "border": "none", "rows": rows, "gap_px": [above, 0],
            "keep_together": keep, **options}


def run(text: str, pt: float = 9, color: str = INK, **extra) -> dict:
    ratio = SERIF_RATIO if extra.get("font") == SERIF else SANS_RATIO
    return {"run": text, "size": pt, "color": color, "ratio": ratio, "font_space": True, **extra}


def chip(text: str, fill: str, color: str, edge: str | None = None, height: float = 20,
         max_w: float = CHIP_MAX_W, **extra) -> dict:
    """둥근 이름표(글상자). 너비는 글 길이에 맞추되 max_w를 넘으면 글을 줄인다."""
    text = fit(text, max_w)
    shape = {"shape": "round", "w": shape_width(text), "h": height, "fill": fill, "text": text,
             "color": color, "bold": True, "size": 9, "pad_px": 2, "ratio": SANS_RATIO, "font_space": True, **extra}
    return {**shape, "line": edge, "line_px": 1.5} if edge else shape


def kind_chip(kind: str) -> dict | None:
    look = KIND_LOOK.get(kind)
    return chip(kind, look[0], look[1], look[2]) if look else None


def kind_cell(value, **options) -> dict:
    """평가 종류 칸: 진단·형성·수행·지필은 칩, 그 밖(관찰 등)은 흐린 글."""
    kind = kind_of(value)
    shape = kind_chip(kind)
    if shape:
        return cell([shape], spacing=100, **options)
    return cell(text_of(value) or CHECK, color=MUTED, **options)


# ---------------------------------------------------------------- 머리 띠·기본 정보·마디 띠·소제목

def band_blocks(info: dict, periods_label: str) -> list:
    """쪽 위·양옆 끝까지 닿는 진한 청록 → 청록 그라데이션 띠: 바탕 사각형과 그 위의 글 표(종이 기준, 글 앞)."""
    chips = [chip(text, WHITE, DEEP, height=22, max_w=BAND_CHIP_MAX_W, mr_px=6) for text in
             (text_of(info.get("grade")) or CHECK, text_of(info.get("subject")) or CHECK, periods_label)]
    rows = [[cell(chips, align="left", valign="bottom", pad=(BODY_X, 0, 0, 0), height_px=48, spacing=100),
             cell("백워드 설계 · 개념기반 탐구 · GRASPS", color=BAND_TEXT, align="right", valign="bottom",
                  pad=(0, BODY_X, 0, 3), height_px=48)],
            [cell("단원 설계서", colspan=2, font=SERIF, size=21, bold=True, color=WHITE, align="left",
                  pad=(BODY_X, 0, 6, 0), height_px=44)],
            [cell(text_of(info.get("unit")) or CHECK, colspan=2, size=10.5, bold=True, color=WHITE, align="left",
                  valign="top", pad=(BODY_X, BODY_X, 0, 0), height_px=BAND_H - 92)]]
    backdrop = {"type": "shape", "shape": "rect", "w": PAGE_W, "h": BAND_H, "corner": 0, "fill": DEEP,
                "fill_to": TEAL, "fill_angle": 80, "paper": {"x": 0, "y": 0}}
    text = {**table([470, PAGE_W - 470], rows), "paper": {"x": 0, "y": 0, "width": PAGE_W, "wrap": "front"}}
    return [backdrop, text]


def info_strip(info: dict, periods_label: str) -> dict:
    """머리 띠 아래 기본 정보 줄: 적용 교육과정 | 단원 차시 | 학기 차시 기준 | 작성일."""
    items = [("적용 교육과정", info.get("curriculum")), ("단원 차시", periods_label),
             ("학기 차시 기준", info.get("semester_periods")), ("작성일", info.get("date"))]
    frame, inner = line(THICK), line()
    cells = []
    for index, (label, value) in enumerate(items):
        edges = {"top": frame, "bottom": frame, "left": inner if index else frame}
        if index == len(items) - 1:
            edges["right"] = frame
        cells.append(cell([run(label, 9, TEAL, bold=True), run("\n" + (text_of(value) or CHECK), 9)],
                          fill=WHITE, align="left", pad=(10, 8, 6, 6), edges=edges))
    return table([1, 0.7, 1.5, 0.8], [cells], above=BAND_H + 12 - TOP_MARGIN)


def section_strip(mark: str, title: str, tag: str) -> dict:
    """마디 띠: 청록 번호 칸(흰 명조 로마 숫자) + 연청록 바탕 진한 청록 명조 제목 + 오른쪽 칩 + 아래 청록 선."""
    bottom = {"bottom": line(BOLD, TEAL)}
    tag_w = round(text_px(tag, 9) * 1.06 + 20) + 20
    cells = [cell(mark, fill=TEAL, color=WHITE, font=SERIF, size=12, bold=True, height_px=40, edges=bottom),
             cell(title, fill=MINT, color=DEEP, font=SERIF, size=15, bold=True, align="left", pad=(12, 0, 0, 0),
                  edges=bottom),
             cell([chip(tag, WHITE, DEEP, MINT_LINE)], fill=MINT, align="right", pad=(0, 10, 0, 0), spacing=100,
                  edges=bottom)]
    return {**table([40, BODY_W - 40 - tag_w, tag_w], [cells], above=GAP + 4), "keep_with_next": True}


def sub_title(title: str) -> dict:
    """소제목: 청록 짧은 세로 막대 + 진한 청록 명조. 다음 블록과 같은 쪽에 둔다."""
    bar = {"shape": "round", "w": 6, "h": 16, "corner": 50, "fill": TEAL}
    cells = [cell([bar], align="left", pad=(0, 0, 0, 0), height_px=24, spacing=100),
             cell(title, font=SERIF, size=12, bold=True, color=DEEP, align="left", pad=(0, 0, 0, 0))]
    return {**table([14, BODY_W - 14], [cells]), "keep_with_next": True}


def note_line(text: str, above: float = SMALL_GAP) -> dict:
    return {**table([1], [[cell(text, color=MUTED, align="left", pad=(0, 0, 0, 0))]], above=above),
            "keep_with_next": True}


def head_cells(names: list[str]) -> list[dict]:
    """표 머리 행: 연청록 바탕 진한 청록 굵은 글. 쪽을 넘으면 되풀이된다."""
    return [cell(name, fill=MINT, color=DEEP, bold=True, pad=(6, 6, 6, 6), edges=GRID) for name in names]


def grid_cell(content, **options) -> dict:
    return cell(content, fill=WHITE, edges=GRID, pad=options.pop("pad", (7, 7, 5, 5)), **options)


def grid_table(names: list[str], rows: list, widths: list, above: float = SMALL_GAP) -> dict:
    """머리 행이 있는 표. 길면 행 단위로 쪽을 넘고(행 가운데는 안 잘림) 머리 행이 되풀이된다."""
    return table(widths, rows, above=above, keep=False, header=head_cells(names), split_rows=True)


def footer_blocks(info: dict) -> list:
    """꼬리말: 연청록 선 위에 청록 짧은 막대 + 문서 이름·작성일, 오른쪽 진한 청록 둥근 칩 '쪽 / 전체'."""
    top = {"top": line(THICK)}
    name = " ".join(filter(None, (text_of(info.get("grade")), text_of(info.get("subject")), "단원 설계서")))
    bar = cell([{"shape": "round", "w": 22, "h": 4, "corner": 50, "fill": TEAL}], align="left", pad=(0, 0, 0, 0),
               height_px=28, spacing=100, edges=top)
    text = cell(f"{name} · {text_of(info.get('date'))}", color=MUTED, align="left", pad=(0, 0, 0, 0), edges=top)
    page = cell([{"shape": "round", "w": 52, "h": 18, "fill": DEEP, "color": WHITE, "bold": True, "size": 9,
                  "page_number": True, "pad_px": 2, "ratio": SANS_RATIO}], align="right", pad=(0, 0, 0, 0),
                spacing=100, edges=top)
    return [{**table([32, BODY_W - 92, 60], [[bar, text, page]], above=0), "gap_px": [0, 0]}]


# ---------------------------------------------------------------- 1단계 바라는 결과

def standards_table(stage1: dict) -> dict:
    rows = [[grid_cell([run(text_of(s.get("code")) or CHECK, 9, DEEP, bold=True), run("\n" + text_of(s.get("text")), 9)],
                       align="left"),
             grid_cell(text_of(s.get("know")) or CHECK), grid_cell(text_of(s.get("do")) or CHECK)]
            for s in stage1["standards"]]
    return grid_table(["성취기준", "알아야 할 것 (지식⋅이해)", "할 수 있어야 할 것 (과정⋅기능)"], rows, [46, 26, 28])


def _groups(value, keys: tuple[str, ...]) -> dict:
    return value if isinstance(value, dict) and value else {key: None for key in keys}


def box_head(title: str, fill: str, edges: dict, **options) -> dict:
    """상자 머리띠: 진한 바탕 흰 명조."""
    return cell(title, fill=fill, color=WHITE, font=SERIF, size=10.5, bold=True, align="left", pad=(12, 12, 6, 6),
                height_px=30, edges=edges, **options)


def idea_boxes(stage1: dict) -> dict:
    """핵심 아이디어 상자 | 내용 요소 상자(이름표 칩 + 글). 두 상자는 한 표라 높이가 같고 함께 옮겨진다."""
    groups = _groups(stage1.get("content_elements"), ELEMENT_TYPES)
    count, frame = len(groups), line(THICK)
    chip_w = max(shape_width(fit(name, CHIP_MAX_W)) for name in groups) + 18
    half = (BODY_W - 12) / 2
    ideas = "\n".join("· " + idea for idea in lines_of(stage1.get("core_ideas"))) or CHECK
    rows = [[box_head("핵심 아이디어 (교육과정)", DEEP, sides("lrt", frame)), cell(None, rowspan=count + 1),
             box_head("내용 요소", DEEP, sides("lrt", frame), colspan=2)],
            [cell(ideas, rowspan=count, fill=PALE, align="left", valign="top", pad=(12, 12, 8, 8),
                  edges=sides("lrb", frame))]]
    for index, (name, value) in enumerate(groups.items()):
        last = index == count - 1
        top, bottom = 8 if index == 0 else 2, 8 if last else 2
        cells = [cell([chip(name, TINT, DEEP)], fill=PALE, align="left", valign="top", pad=(12, 0, top, bottom),
                      spacing=100, edges=sides("lb" if last else "l", frame)),
                 cell(", ".join(lines_of(value)) or CHECK, fill=PALE, align="left", valign="top",
                      pad=(0, 12, top + 1, bottom), edges=sides("rb" if last else "r", frame))]
        if index == 0:
            rows[1] += cells
        else:
            rows.append(cells)
    return table([half, 12, chip_w, half - chip_w], rows)


def concept_row(stage1: dict) -> dict:
    """핵심 개념: 청록 굵은 이름 + 흰 바탕 칩들. 칩은 한 칸에 글자처럼 이어 놓아 많으면 다음 줄로 넘어간다."""
    concepts = codes_of(stage1.get("concepts")) or [CHECK]
    shapes = [chip(name, WHITE, DEEP, MINT_LINE, mr_px=6) for name in concepts]
    cells = [cell("핵심 개념", color=TEAL, bold=True, align="left", pad=(0, 0, 0, 0), height_px=26),
             cell(shapes, align="left", pad=(0, 0, 0, 0), spacing=130)]
    return table([70, BODY_W - 70], [cells], above=10)


def key_boxes(stage1: dict) -> dict:
    """영속적 이해(진한 청록 테두리, 흰 바탕) | 핵심 질문(크림 바탕, 황토 테두리) 나란히."""
    half = (BODY_W - 12) / 2
    under = [chip("영속적 이해 (일반화)", DEEP, WHITE)] + [
        run("\n" + text, 11.25, INK, font=SERIF) for text in lines_of(stage1.get("understandings")) or [CHECK]]
    quest = [chip("핵심 질문", GOLD, WHITE)] + [
        run("\n" + text, 12, INK, bold=True, font=SERIF) for text in lines_of(stage1.get("essential_questions")) or [CHECK]]
    quest.append(run("\n답이 영속적 이해가 되는 질문 · 1차시에 열고 마지막 차시에 답합니다", 9, MUTED))
    look = {"align": "left", "valign": "top", "pad": (14, 14, 10, 12)}
    return table([half, 12, half], [[cell(under, fill=WHITE, edges=sides("lrtb", line(BOLD, DEEP)), **look),
                                     cell(None),
                                     cell(quest, fill=CREAM, edges=sides("lrtb", line(BOLD, GOLD_LINE)), **look)]],
                 above=10)


def question_box(stage1: dict) -> dict:
    """탐구 질문 상자: 청록 머리띠 + (사실·개념·논쟁 칩 | 질문) 줄, 줄 사이 점선."""
    groups = _groups(stage1.get("questions"), QUESTION_TYPES)
    frame, dash = line(THICK), line(THIN, MINT_LINE, "DASH")
    rows = [[box_head("탐구 질문", TEAL, sides("lrt", frame), colspan=2)]]
    label_w = max(66, max(shape_width(fit(str(name), CHIP_MAX_W)) for name in groups) + 18)   # 이름표 + 왼쪽 여백 12
    for index, (name, value) in enumerate(groups.items()):
        edge = ({"top": dash} if index else {}) | (sides("b", frame) if index == len(groups) - 1 else {})
        rows.append([cell([chip(str(name), DEEP if "논쟁" in str(name) else TEAL, WHITE)], fill=PALE, align="left",
                          valign="top", pad=(12, 0, 8, 8), spacing=100, edges={**sides("l", frame), **edge}),
                     cell("\n".join(lines_of(value)) or CHECK, fill=PALE, size=10.5, align="left", valign="top",
                          pad=(0, 12, 8, 8), edges={**sides("r", frame), **edge})])
    return table([label_w, BODY_W - label_w], rows)


# ---------------------------------------------------------------- 2단계 평가 계획

def grasps_cards(grasps: dict) -> dict:
    """GRASPS 여섯 칸(2열): 진한 청록 글자 칸 + 청록 이름 + 내용. 한 줄의 두 칸은 높이가 같다."""
    side, frame = (BODY_W - 8) / 2, line(THICK)
    rows = []
    for start in range(0, len(GRASPS_PARTS), 2):
        if start:
            rows.append([cell(None, colspan=5, size=1, spacing=100, pad=(0, 0, 0, 0), height_px=8)])
        row = []
        for letter, name, key in GRASPS_PARTS[start:start + 2]:
            mark = {"shape": "round", "w": 32, "h": 32, "corner": 22, "fill": DEEP, "text": letter, "color": WHITE,
                    "bold": True, "font": SERIF, "size": 15, "pad_px": 0, "ratio": SERIF_RATIO}
            row += [cell([mark], fill=WHITE, align="left", valign="top", pad=(12, 0, 10, 10), spacing=100,
                         edges=sides("ltb", frame)),
                    cell([run(name, 9, TEAL, bold=True), run("\n" + (text_of(grasps.get(key)) or CHECK), 9)],
                         fill=WHITE, align="left", valign="top", pad=(4, 12, 10, 10), edges=sides("rtb", frame))]
            if len(row) == 2:
                row.append(cell(None))
        rows.append(row)
    return table([52, side - 52, 8, 52, side - 52], rows, above=SMALL_GAP)


def run_note() -> dict:
    """운영 안내: 크림 바탕 황토 테두리 + 황토 칩."""
    frame = line(THICK, GOLD_LINE)
    return table([70, BODY_W - 70], [[
        cell([chip("운영", GOLD, WHITE)], fill=CREAM, valign="top", pad=(12, 0, 9, 8), spacing=100,
             edges=sides("ltb", frame)),
        cell(RUN_NOTE, fill=CREAM, align="left", pad=(0, 12, 8, 8), edges=sides("rtb", frame))]], above=10)


def criteria_table(criteria: list) -> dict:
    rows = [[grid_cell(text_of(c.get("element")) or CHECK, bold=True, color=DEEP),
             grid_cell(text_of(c.get("look")) or CHECK, align="left")] for c in criteria]
    return grid_table(["평가 요소", "보는 것"], rows, [22, 78])


def evidence_table(evidence: list) -> dict:
    rows = [[grid_cell(text_of(e.get("periods")) or CHECK, bold=True), kind_cell(e.get("kind"), fill=WHITE, edges=GRID),
             grid_cell(text_of(e.get("method")) or CHECK), grid_cell(text_of(e.get("focus")) or CHECK),
             grid_cell("\n".join(codes_of(e.get("standards"))) or CHECK)] for e in evidence]
    return grid_table(["차시", "종류", "방법", "확인할 것", "성취기준"],
                      rows or [[grid_cell(CHECK) for _ in range(5)]], [11, 11, 26, 30, 22], above=10)


# ---------------------------------------------------------------- 평가 배치 (차시 줄)

TRACK_PAD, DOT = 14, 26            # 상자 안쪽 좌우 여백, 차시 동그라미 지름


def _edges_of(item: dict) -> dict:
    return item["edges"] if isinstance(item.get("edges"), dict) else {}


def _framed(rows: list, frame: list) -> list:
    """상자 테두리: 모든 줄의 첫 칸 왼쪽·끝 칸 오른쪽, 첫 줄 위에 선 (아래 선은 마지막 줄이 직접 단다)."""
    out = []
    for index, row in enumerate(rows):
        row = [{**item, "edges": {**_edges_of(item), **(sides("t", frame) if index == 0 else {})}} for item in row]
        row[0]["edges"]["left"], row[-1]["edges"]["right"] = frame, frame
        out.append(row)
    return out


def _rail(width: float, shown: bool, top: float) -> dict:
    """차시 동그라미 사이 연청록 선(동그라미 가운데 높이)."""
    rail = [{"shape": "rect", "w": round(width, 1), "h": 2, "corner": 0, "fill": MINT_LINE}] if shown else None
    return cell(rail, fill=PALE, pad=(0, 0, top, 0), spacing=100)


def _circle_row(numbers: list[int], per_row: int, half: float, marks: dict, top: float) -> list:
    """차시 번호 동그라미: 평가가 있는 차시는 진한 청록 바탕 흰 글자, 수업만 하는 차시는 흰 바탕."""
    cells = [cell(None, fill=PALE, pad=(0, 0, top, 0), height_px=DOT + top)]
    for slot in range(per_row):
        if slot >= len(numbers):
            cells += [cell(None, fill=PALE) for _ in range(3)]
            continue
        marked = bool(marks.get(numbers[slot]))
        circle = {"shape": "ellipse", "w": DOT, "h": DOT, "fill": DEEP if marked else WHITE, "line": DEEP, "line_px": 2,
                  "text": str(numbers[slot]), "color": WHITE if marked else DEEP, "bold": True, "size": 9,
                  "pad_px": 0, "ratio": SANS_RATIO}
        cells += [_rail(half, slot > 0, top), cell([circle], fill=PALE, pad=(0, 0, top, 0), spacing=100),
                  _rail(half, slot < len(numbers) - 1, top)]
    return cells + [cell(None, fill=PALE)]


def _stacked(shapes: list) -> list:
    out = []
    for index, shape in enumerate(shapes):
        out += (["\n"] if index else []) + [shape]
    return out


def _mark_row(numbers: list[int], per_row: int, marks: dict) -> list:
    """동그라미 아래 평가 종류 칩(한 차시에 여럿이면 세로로), 평가가 없으면 흐린 '수업'."""
    cells = [cell(None, fill=PALE)]
    for slot in range(per_row):
        look = {"colspan": 3, "fill": PALE, "valign": "top", "pad": (0, 0, 6, 10)}
        if slot >= len(numbers):
            cells.append(cell(None, **look))
            continue
        kinds = marks.get(numbers[slot]) or []
        shapes = [kind_chip(kind) or chip(kind or CHECK, PALE, MUTED, MINT_LINE) for kind in kinds]
        cells.append(cell(_stacked(shapes), spacing=130, **look) if shapes
                     else cell("수업", color=MUTED, **{**look, "pad": (0, 0, 9, 10)}))
    return cells + [cell(None, fill=PALE)]


def _plain_shape(text: str, color: str = INK, bold: bool = False) -> dict:
    """바탕·선 없는 글상자: 칩과 같은 높이라 한 줄에서 글과 칩의 세로 가운데가 맞는다."""
    text = fit(text, LABEL_MAX_W, LABEL_PAD)
    return {"shape": "rect", "w": shape_width(text, LABEL_PAD), "h": 20, "corner": 0, "text": text,
            "color": color, "bold": bold, "size": 9, "pad_px": 0, "ratio": SANS_RATIO, "font_space": True, "mr_px": 4}


def _outside_row(cols: int, outside: list[tuple[str, str]], frame: list) -> list:
    """점선 아래 줄: 왼쪽 '단원 밖'(정기시험 등 차시 밖 평가), 오른쪽 칩 보기."""
    edges = {"top": line(THIN, MINT_LINE, "DASH"), "bottom": frame}
    left = []
    for kind, label in outside:
        left += [kind_chip(kind) or chip(kind or CHECK, PALE, MUTED, MINT_LINE), _plain_shape(label)]
    if left:
        left = [_plain_shape("단원 밖", TEAL, True)] + left
    legend = [{**kind_chip(kind), "ml_px": 4} for kind in KIND_LOOK]
    span = cols // 2
    look = {"fill": PALE, "spacing": 100, "edges": edges}
    return [cell(left or None, colspan=span, align="left", pad=(TRACK_PAD, 0, 8, 10), **look),
            cell(legend, colspan=cols - span, align="right", pad=(0, TRACK_PAD, 8, 10), **look)]


def timeline_box(total: int, marks: dict[int, list[str]], outside: list[tuple[str, str]]) -> dict:
    """평가 배치: 차시 1..N 줄(동그라미 + 선) 아래 평가 종류 칩. 한 줄에 TIMELINE_PER_ROW 차시까지, 줄마다 고르게."""
    lines_needed = -(-total // TIMELINE_PER_ROW)
    per_row = -(-total // lines_needed)            # 줄마다 고르게 (12차시면 9+3이 아니라 6+6)
    half = (BODY_W - 2 * TRACK_PAD - DOT * per_row) / (2 * per_row)
    widths = [TRACK_PAD] + [half, DOT, half] * per_row + [TRACK_PAD]
    rows = []
    for start in range(1, total + 1, per_row):
        numbers = list(range(start, min(start + per_row, total + 1)))
        rows += [_circle_row(numbers, per_row, half, marks, 14 if start == 1 else 4), _mark_row(numbers, per_row, marks)]
    frame = line(THICK)
    rows.append(_outside_row(len(widths), outside, frame))
    return table(widths, _framed(rows, frame), above=SMALL_GAP)


# ---------------------------------------------------------------- 3단계 차시 흐름, 다음 단계

def _activity_runs(value) -> list[dict]:
    """주요 활동: ◉ 줄은 진한 청록 굵게, ○ 줄은 보통."""
    out = []
    for index, text in enumerate(lines_of(value) or [CHECK]):
        main = text.lstrip().startswith("◉")
        out.append(run(("\n" if index else "") + text, 9, DEEP if main else INK, bold=main))
    return out


def flow_table(stage3: list) -> dict:
    """차시 흐름표: 큰 명조 차시 번호 | 학습 목표 + 성취기준 코드 | 주요 활동 | 평가 칩."""
    rows = []
    for row in stage3:
        codes = " ".join(codes_of(row.get("standards")))
        goal = [run(text_of(row.get("goal")) or CHECK, 9)] + ([run("\n" + codes, 9, TEAL)] if codes else [])
        rows.append([grid_cell(text_of(row.get("periods")), font=SERIF, size=15, bold=True, color=DEEP),
                     grid_cell(goal), grid_cell(_activity_runs(row.get("activities")), align="left"),
                     kind_cell(row.get("assessment"), fill=WHITE, edges=GRID)])
    return grid_table(["차시", "학습 목표 · 성취기준", "주요 활동", "평가"], rows, [9, 33, 44, 14], above=SMALL_GAP)


def next_table(steps: list) -> dict:
    """다음 단계 표: 요청 문장은 연노랑 바탕 + 밑줄(그대로 보내면 되는 글)."""
    rows = []
    for step in steps:
        request = text_of(step.get("request"))
        rows.append([grid_cell(text_of(step.get("skill")) or CHECK, bold=True, color=DEEP),
                     grid_cell(f"~~{request}~~" if request else CHECK, bold=True, blank_fill=FILL),
                     grid_cell(text_of(step.get("what")) or CHECK)])
    return grid_table(["다음에 만들 것", "이렇게 요청하세요", "넘길 내용"], rows, [24, 40, 36])
