"""수행평가 세부 계획(채점 기준표) 한글(hwpx) 만들기. 표준 라이브러리만 쓴다.

기본 양식 assets/rubric_form.hwpx(학교 수행평가 세부 계획 양식)의 칸을 그대로 복제해 평가 영역·요소·수준 수에 맞게
행을 늘리고 줄인다. 칸의 테두리·글자 모양·문단 모양·열 너비는 양식 그대로이고 글만 바뀐다.

입력 JSON:
{
  "title": "1. 생활 속 명제 발표하기",                       # 표 위 제목 (번호까지 그대로 씀)
  "standards": ["[10공수2-02-04] 명제와 조건의 뜻을 …", "~", "[10공수2-02-05] …"],
                                                            # 한 줄씩. "~"만 쓴 줄은 가운데 정렬
  "methods": ["구술·발표"],                                  # ■로 칠할 평가 방법. 양식의 7가지
                                                            #  (서술·논술, 구술·발표, 토의·토론, 프로젝트, 실험·실습,
                                                            #  포트폴리오, 기타) 가운데에서. "기타(관찰)"처럼 쓰면 기타 칸에 괄호가 붙음
  "areas": [                                                # 평가 영역(만점은 요소 만점의 합)
    {"name": "생활 속 명제 발표",
     "elements": [                                          # 평가 요소(만점은 수준 점수의 가장 큰 값)
       {"name": "명제 판별", "levels": [["기준 문장", 8], ["기준 문장", 6], ["기준 문장", 4]],
        "feedback": "가장 낮은 단계 학생에게 줄 다음 행동"}  # 선택. 있으면 표 아래 "피드백 계획" 칸에 요소마다 한 줄
     ]}
  ],
  "base": [["수행과정 미참여 또는 미제출 …(기본점수)", "9(30%)"],   # 기본점수·예외 행 [글, 점수]. 없으면 행을 뺌
           ["장기 미인정 결시로 수행과정에 참여하지 않음(기본점수의 -1)", "8"]],
  "notes": ["수행평가 과정에서 …"],                          # 학생 유의사항 줄. 없으면 양식의 AI 활용 유의사항 4줄
  "scale": [30, 29, 28]                                     # 평가 척도(선택). 없으면 만점부터 최저점까지 1점 간격
}
"tasks": [위 객체, …] 로 주면 과제마다 제목과 표를 이어 붙인다.

사용법:
    python make_rubric_form.py 입력.json 출력.hwpx
"""

from __future__ import annotations

import json
import math
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SCRIPTS = Path(__file__).resolve().parent
for folder in (SCRIPTS, SCRIPTS.parents[2] / "shared" / "scripts"):      # 스킬 묶음 안, 저장소 안
    if (folder / "make_hwpx_save.py").exists():
        sys.path.insert(0, str(folder))
        break
from make_hwpx_check import validate_package  # noqa: E402
from make_hwpx_save import file_error_message, hwpx_check, save_atomically, write_zip  # noqa: E402
from make_hwpx_text import _clean  # noqa: E402

FORM = SCRIPTS.parent / "assets" / "rubric_form.hwpx"
SECTION = "Contents/section0.xml"
METHODS = ("서술·논술", "구술·발표", "토의·토론", "프로젝트", "실험·실습", "포트폴리오", "기타")
DEFAULT_NOTES = (
    "수행평가 과정에서 AI, 전자기기, 인터넷 사용은 교사가 허용한 범위 내에서만 활용해야 하며, 그 외의 경우 적발 시 부정행위로 간주함",
    "AI 입력창에 본인이나 타인의 학번, 이름, 학교명 등 개인정보를 입력해서는 안됨",
    "AI 활용 시에는 수행평가 과제 활동지의 서식에 맞게 활용 과정을 표기해야 함",
    "AI 생성물을 출처 표기없이 그대로 제출하거나, 결과물의 내용을 묻는 교사의 질의에 적절한 답변을 하지 못하는 경우, "
    "해당 내용은 채점에서 제외될 수 있음",
)
LINE_PITCH = 1600                  # 10pt 글자 한 줄 높이 어림 (HWPUNIT, 줄 간격 160%)
CELL_PAD = 1020                    # 칸 왼쪽·오른쪽 안쪽 여백 합
MIN_ROW = 1848                     # 양식의 한 줄 행 높이
TABLE_RE = re.compile(r"<hp:tbl .*?</hp:tbl>", re.S)
CELL_RE = re.compile(r"<hp:tc .*?</hp:tc>", re.S)
PARA_RE = re.compile(r"<hp:p .*?</hp:p>", re.S)
ADDR_RE = re.compile(r'(<hp:cellAddr colAddr="\d+" rowAddr=")\d+')


class FormError(ValueError):
    """입력이나 양식이 맞지 않음 (한국어 알림)."""


def _xml(text: str) -> str:
    """XML에 넣을 수 없는 제어 문자를 지우고(한글이 파일을 열지 못함) 특수 문자를 바꾼다."""
    return escape(_clean(text))


# ---------------------------------------------------------------- 칸

def _cells(table: str) -> dict[tuple[int, int], str]:
    found = {}
    for tc in CELL_RE.findall(table):
        col, row = re.search(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', tc).groups()
        found[(int(col), int(row))] = tc
    return found


def _para(template: str, inner_xml: str) -> str:
    """template 문단의 문단 모양과 첫 글자 모양으로 새 문단. 줄 배치(linesegarray)는 한글이 다시 잡게 뺀다."""
    opening = re.match(r"<hp:p [^>]*>", template).group(0)
    char = re.search(r'<hp:run charPrIDRef="(\d+)"', template).group(1)
    return f'{opening}<hp:run charPrIDRef="{char}"><hp:t>{inner_xml}</hp:t></hp:run></hp:p>'


def _texts(tc: str, lines: list[str], styles: list[str] | None = None) -> list[str]:
    """줄마다 문단. styles가 있으면 그 문단 모양, 없으면 양식 칸의 같은 순서 문단(모자라면 마지막) 모양."""
    templates = PARA_RE.findall(tc)
    return [_para(styles[i] if styles else templates[min(i, len(templates) - 1)], _xml(line))
            for i, line in enumerate(lines)]


def _cell(tc: str, row: int, height: int, paragraphs: list[str], rowspan: int = 1) -> str:
    body = re.search(r"(<hp:subList [^>]*>).*(</hp:subList>)", tc, re.S)
    tc = tc[:body.start()] + body.group(1) + "".join(paragraphs) + body.group(2) + tc[body.end():]
    tc = ADDR_RE.sub(rf"\g<1>{row}", tc, count=1)
    tc = re.sub(r'(<hp:cellSpan colSpan="\d+" rowSpan=")\d+', rf"\g<1>{rowspan}", tc, count=1)
    return re.sub(r'(<hp:cellSz width="\d+" height=")\d+', rf"\g<1>{height}", tc, count=1)


def _width(tc: str) -> int:
    return int(re.search(r'<hp:cellSz width="(\d+)"', tc).group(1))


def _lines(text: str, width: int) -> int:
    """칸 너비에 글이 몇 줄로 들어갈지 어림 (10pt: 한글 1자 1000, 그 밖 520)."""
    units = sum(1000 if ord(char) > 0x2E7F else 520 for char in text)
    return max(1, math.ceil(units / max(1000, width - CELL_PAD)))


def _row_height(text: str, width: int) -> int:
    return max(MIN_ROW, _lines(text, width) * LINE_PITCH + 400)


# ---------------------------------------------------------------- 입력 검사

def _need_text(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FormError(f"{where}: 글이 필요함 (받은 값: {value!r})")
    return value.strip()


def _score(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise FormError(f"{where}: 점수는 0 이상의 수여야 함 (받은 값: {value!r})")
    return value


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _check_levels(levels, place: str) -> list[tuple[str, float]]:
    if not isinstance(levels, list) or not levels:
        raise FormError(f"{place}: 'levels'([기준 문장, 점수] 목록)가 필요함")
    clean = []
    for index, level in enumerate(levels, 1):
        if not isinstance(level, (list, tuple)) or len(level) != 2:
            raise FormError(f"{place} 수준 {index}: [기준 문장, 점수] 꼴이어야 함")
        clean.append((_need_text(level[0], f"{place} 수준 {index}"), _score(level[1], f"{place} 수준 {index}")))
    return clean


def _check_areas(areas, where: str) -> list[dict]:
    if not isinstance(areas, list) or not areas:
        raise FormError(f"{where}: 'areas'(평가 영역 목록)가 필요함")
    clean = []
    for a_index, area in enumerate(areas, 1):
        spot = f"{where} 영역 {a_index}"
        elements = area.get("elements") if isinstance(area, dict) else None
        if not isinstance(elements, list) or not elements:
            raise FormError(f"{spot}: 'elements'(평가 요소 목록)가 필요함")
        clean.append({"name": _need_text(area.get("name"), f"{spot} 이름"), "elements": [
            {"name": _need_text(element.get("name") if isinstance(element, dict) else None, f"{spot} 요소 {e} 이름"),
             "levels": _check_levels(element.get("levels"), f"{spot} 요소 {e}"),
             "feedback": _check_feedback(element.get("feedback"), f"{spot} 요소 {e} 피드백")}
            for e, element in enumerate(elements, 1)]})
    return clean


def _check_feedback(value, where: str) -> str | None:
    """요소의 피드백(가장 낮은 단계 학생에게 줄 다음 행동). 선택 항목이라 없으면 None."""
    return None if value is None else _need_text(value, where)


def _check_task(task, where: str) -> dict:
    if not isinstance(task, dict):
        raise FormError(f"{where}: 과제는 객체여야 함")
    methods = task.get("methods") or []
    if not isinstance(methods, list):
        raise FormError(f"{where}: 'methods'는 목록이어야 함")
    for method in methods:
        if re.sub(r"\(.*\)$", "", str(method)).strip() not in METHODS:
            raise FormError(f"{where}: 평가 방법 '{method}'는 양식에 없음. 쓸 수 있는 것: {', '.join(METHODS)}")
    standards = task.get("standards") or []
    if not isinstance(standards, list) or not all(isinstance(line, str) for line in standards):
        raise FormError(f"{where}: 'standards'는 글 목록이어야 함")
    base = task.get("base") or []
    if not isinstance(base, list) or any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in base):
        raise FormError(f"{where}: 'base'는 [글, 점수] 목록이어야 함")
    notes = task.get("notes")
    if notes is not None and (not isinstance(notes, list) or not all(isinstance(n, str) for n in notes)):
        raise FormError(f"{where}: 'notes'는 글 목록이어야 함")
    return {"title": _need_text(task.get("title"), f"{where} 제목"), "standards": standards, "methods": methods,
            "areas": _check_areas(task.get("areas"), where), "base": [(str(t), str(s)) for t, s in base],
            "notes": list(DEFAULT_NOTES) if notes is None else notes, "scale": task.get("scale")}


def _scale(task: dict) -> list[str]:
    if task["scale"] is not None:
        if not isinstance(task["scale"], list) or not task["scale"]:
            raise FormError("'scale'은 점수 목록이어야 함")
        return [value if isinstance(value, str) else _fmt(_score(value, "scale")) for value in task["scale"]]
    elements = [element for area in task["areas"] for element in area["elements"]]
    top = sum(max(score for _, score in element["levels"]) for element in elements)
    low = sum(min(score for _, score in element["levels"]) for element in elements)
    if not (float(top).is_integer() and float(low).is_integer()):
        raise FormError("점수에 소수가 있어 평가 척도를 셀 수 없음. 'scale'로 직접 적어 주세요")
    return [str(value) for value in range(int(top), int(low) - 1, -1)]


# ---------------------------------------------------------------- 표

def _methods_line(methods: list[str]) -> str:
    chosen = {re.sub(r"\(.*\)$", "", m).strip(): m for m in methods}
    return "  ".join(("■" if name in chosen else "□") + chosen.get(name, name) for name in METHODS)


def _head_rows(get, task: dict) -> tuple[list[str], list[int]]:
    """성취기준, 평가 방법, 머리행."""
    std_tc = get((2, 0))
    templates = PARA_RE.findall(std_tc)
    lines = task["standards"] or ["[확인 필요]"]
    styles = [templates[1] if line.strip() in ("~", "∼") and len(templates) > 1 else templates[0] for line in lines]
    std_h = max(MIN_ROW, sum(_lines(line, _width(std_tc)) for line in lines) * LINE_PITCH + 400)
    rows = [_cell(get((0, 0)), 0, std_h, _texts(get((0, 0)), ["성취기준"])) + _cell(std_tc, 0, std_h, _texts(std_tc, lines, styles)),
            _cell(get((0, 1)), 1, MIN_ROW, _texts(get((0, 1)), ["평가 방법"]))
            + _cell(get((2, 1)), 1, MIN_ROW, _texts(get((2, 1)), [_methods_line(task["methods"])]))]
    header_h = int(re.search(r'height="(\d+)"', re.search(r"<hp:cellSz [^>]*>", get((2, 2))).group(0)).group(1))
    return rows, [std_h, MIN_ROW, header_h]


def _body_rows(get, task: dict, start: int) -> tuple[list[str], list[int]]:
    """평가 영역·요소·수준 행. 첫 행은 양식 3행(위 굵은 선), 요소 첫 행은 7행, 나머지는 4행 칸을 본뜬다."""
    plan = []
    for a_index, area in enumerate(task["areas"]):
        for e_index, element in enumerate(area["elements"]):
            for l_index, (text, score) in enumerate(element["levels"]):
                kind = 3 if not plan else (7 if l_index == 0 else 4)
                plan.append((area, a_index, element, e_index, l_index, text, score, kind))
    heights = [_row_height(text, _width(get((2, kind)))) for *_, text, _, kind in plan]
    scale = _scale(task)
    rows = []
    for position, (area, a_index, element, e_index, l_index, text, score, kind) in enumerate(plan):
        row_no = start + position
        cells = ""
        if e_index == 0 and l_index == 0:
            span = sum(len(e["levels"]) for e in area["elements"])
            total = sum(max(s for _, s in e["levels"]) for e in area["elements"])
            cells += _cell(get((0, 3)), row_no, sum(heights[position:position + span]),
                           _texts(get((0, 3)), [area["name"], f"({_fmt(total)}점)"]), span)
        if l_index == 0:
            span = len(element["levels"])
            points = max(s for _, s in element["levels"])
            source = get((1, 3)) if kind == 3 else get((1, 7))
            cells += _cell(source, row_no, sum(heights[position:position + span]),
                           _texts(source, [element["name"], f"({_fmt(points)}점)"]), span)
        cells += _cell(get((2, kind)), row_no, heights[position], _texts(get((2, kind)), [text]))
        cells += _cell(get((3, kind)), row_no, heights[position], _texts(get((3, kind)), [_fmt(score)]))
        if position == 0:
            cells += _cell(get((4, 3)), row_no, sum(heights), _texts(get((4, 3)), scale), len(plan))
        rows.append(cells)
    return rows, heights


def _list_block(get, heading: str, lines: list[str], row_no: int) -> tuple[list[str], list[int]]:
    """양식의 "학생 유의사항" 머리 칸(21행)과 목록 칸(22행)을 본뜬 두 행: 머리 글, ‣ 줄 목록."""
    list_tc = get((0, 22))
    template = PARA_RE.findall(list_tc)[0]
    height = sum(_lines("‣ " + line, _width(list_tc)) for line in lines) * LINE_PITCH + 600
    return ([_cell(get((0, 21)), row_no, 1282, _texts(get((0, 21)), [heading])),
             _cell(list_tc, row_no + 1, height, [_para(template, "‣<hp:fwSpace/>" + _xml(line)) for line in lines])],
            [1282, height])


def _tail_rows(get, task: dict, start: int) -> tuple[list[str], list[int]]:
    """기본점수·예외 행, 피드백 계획(요소에 feedback이 있을 때만), 학생 유의사항."""
    rows, heights, row_no = [], [], start
    for index, (text, score) in enumerate(task["base"]):
        source = 19 if index == 0 else 20
        height = _row_height(text, _width(get((0, source))))
        rows.append(_cell(get((0, source)), row_no, height, _texts(get((0, source)), [text]))
                    + _cell(get((4, source)), row_no, height, _texts(get((4, source)), [score])))
        heights.append(height)
        row_no += 1
    feedback = [f"{element['name']}: {element['feedback']}"
                for area in task["areas"] for element in area["elements"] if element["feedback"]]
    for heading, lines in (("피드백 계획", feedback), ("학생 유의사항", task["notes"])):
        if lines:
            block, block_h = _list_block(get, heading, lines, row_no)
            rows += block
            heights += block_h
            row_no += 2
    return rows, heights


def _table(base_table: str, task: dict, table_id: int) -> str:
    get = _cells(base_table).__getitem__
    head, head_h = _head_rows(get, task)
    header = re.findall(r"<hp:tr>(.*?)</hp:tr>", base_table, re.S)[2]
    body, body_h = _body_rows(get, task, 3)
    tail, tail_h = _tail_rows(get, task, 3 + len(body))
    rows = [head[0], head[1], ADDR_RE.sub(r"\g<1>2", header), *body, *tail]
    heights = head_h + body_h + tail_h
    opening = re.match(r"<hp:tbl [^>]*>", base_table).group(0)
    opening = re.sub(r'rowCnt="\d+"', f'rowCnt="{len(rows)}"', opening)
    opening = re.sub(r'<hp:tbl id="\d+"', f'<hp:tbl id="{table_id}"', opening)
    sizes = re.search(r"<hp:sz [^>]*/>.*?<hp:inMargin [^>]*/>", base_table, re.S).group(0)
    sizes = re.sub(r'(<hp:sz width="\d+" widthRelTo="\w+" height=")\d+', rf"\g<1>{sum(heights)}", sizes, count=1)
    return opening + sizes + "".join(f"<hp:tr>{row}</hp:tr>" for row in rows) + "</hp:tbl>"


# ---------------------------------------------------------------- 문서

def _section(section: str, tasks: list[dict]) -> str:
    base_table = TABLE_RE.search(section).group(0)
    table_at = section.index("<hp:tbl ")
    title_match = None
    for found in re.finditer(r"<hp:t>([^<]+)</hp:t>", section[:table_at]):
        title_match = found
    if title_match is None:
        raise FormError("양식의 제목 문단을 찾지 못함")
    title_start = section.rfind("<hp:p ", 0, title_match.start())
    holder_start = section.rfind("<hp:p ", 0, table_at)
    holder_end = section.index("</hp:p>", section.index("</hp:tbl>")) + len("</hp:p>")
    title_para, holder = section[title_start:holder_start], section[holder_start:holder_end]
    strip = lambda xml: re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", xml, flags=re.S)   # noqa: E731
    pieces = []
    for index, task in enumerate(tasks):
        title = title_para.replace(title_match.group(0), f"<hp:t>{_xml(task['title'])}</hp:t>", 1)
        if index:          # 둘째 과제부터: 구역 정의를 빼고, 앞 표와 한 줄 띄운다
            title = re.sub(r'<hp:run charPrIDRef="\d+"><hp:secPr.*?</hp:ctrl></hp:run>', "", title, flags=re.S)
            pieces.append(re.sub(r"<hp:t>[^<]*</hp:t>", "<hp:t/>", strip(title), count=1))
        pieces.append(strip(title) + strip(holder.replace(base_table, _table(base_table, task, 1238186782 + index))))
    return section[:title_start] + "".join(pieces) + section[holder_end:]


def build(spec: dict, out_path: Path, form: Path = FORM) -> None:
    raw = spec.get("tasks") if isinstance(spec, dict) and "tasks" in spec else [spec]
    if not isinstance(raw, list) or not raw:
        raise FormError("'tasks'는 과제 목록이어야 함")
    tasks = [_check_task(task, f"과제 {index}") for index, task in enumerate(raw, 1)]
    out_path = Path(out_path)
    if out_path.exists():
        raise FormError(f"이미 있는 파일이라 덮어쓰지 않음: {out_path.name}. 다른 이름을 적어 주세요")
    if not out_path.parent.is_dir():
        raise FormError(f"결과를 저장할 폴더가 없음: {out_path.parent}")
    with zipfile.ZipFile(form) as source:
        infos = source.infolist()
        entries = {info.filename: source.read(info.filename) for info in infos}
    entries[SECTION] = _section(entries[SECTION].decode("utf-8"), tasks).encode("utf-8")
    if "Preview/PrvText.txt" in entries:
        entries["Preview/PrvText.txt"] = "\r\n".join(_clean(task["title"]) for task in tasks).encode("utf-8")
    # 같은 폴더의 임시 파일에 쓰고 hwpx 검사를 통과해야 결과 파일로 옮긴다 (깨진 파일이 남지 않게)
    save_atomically(out_path, lambda path: write_zip(path, infos, entries),
                    hwpx_check(FormError, "만든 hwpx 검사 실패:", (), validate_package))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(args) != 2:
        print("사용법: python make_rubric_form.py 입력.json 출력.hwpx")
        return 2
    try:
        build(json.loads(Path(args[0]).read_text(encoding="utf-8-sig")), Path(args[1]))
    except (FormError, ValueError) as error:      # JSON·글자 인코딩 오류도 ValueError
        print(f"만들지 못함: {error}")
        return 1
    except OSError as error:
        print(f"만들지 못함: {file_error_message(error)}")
        return 1
    print(f"완료: {args[1]}. 한글에서 열어 쪽이 넘어가는 자리를 확인해 주세요")
    return 0


if __name__ == "__main__":
    sys.exit(main())
