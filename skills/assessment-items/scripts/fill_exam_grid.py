"""fill_exam.py의 자료 표(table)와 그림 두 장 나란히(picture 목록). 표준 라이브러리만 쓴다.

    "table": {"head": ["구분", "1950년", "1960년"], "rows": [["농업", "46.4", "37.1"]],
              "caption": "<표> 산업별 취업자 비율(%)", "widths": [2, 1, 1], "align": ["center", "center", "right"]}
    "picture": [{"file": "가.png", "caption": "(가)"}, {"file": "나.png", "caption": "(나)"}]

- 표: 머리 칸은 가운데 정렬·굵게·연한 회색 바탕, 나머지 칸은 가운데 정렬(align으로 칸마다 left, center, right).
  표의 왼쪽은 기준선(번호 자리에서 글자 하나 들어간 선), 오른쪽은 단 끝이다. widths는 칸 너비의 비율이고
  안 적으면 칸의 가장 긴 글에 맞춘다. caption은 표 위에 가운데로 놓는다. 칸 모양(실선 테두리)은 양식에 더한다.
- 그림 두 장: 테두리 없는 한 줄 표에 사이를 글자 두 개 폭으로 띄워 놓는다. 폭(width_mm)을 안 적으면 높이를 맞춘다.
  설명(caption)은 그림 아래 가운데에 놓는다.
- 순서는 문제 → picture → box → table → bogi → 선택지다.
"""

from __future__ import annotations

import re
from pathlib import Path

from fill_exam_media import CELL_MARGIN, FALLBACK_WIDTH, MEDIA_TYPES, MM, TABLE_SIDE, wrap_layout
from fill_exam_parse import _text_width
from fill_exam_spec import _plain
from fill_hwpx import FillError
from make_hwpx_lint import wide_words

RULE_WIDTH = "0.12 mm"                  # 표 테두리 (자료 상자 0.36pt와 같은 가는 실선)
HEAD_SHADE = "#E6E6E6"                  # 머리 칸 바탕. 흑백으로 인쇄해도 글이 또렷한 연한 회색
GAP_EM = 2                              # 그림 두 장 사이 (글자 개수)
WIDTH_FLOOR = 2.0                       # 칸 너비 비율의 최소·최대 (글자 개수)
WIDTH_CEIL = 12.0
MAX_WIDE_NOTES = 3
TIGHT_WORDS = 3                         # 이 낱말 수 이하의 칸 글은 한 줄로 두어야 읽기 좋다 (이름·값)
TIGHT_RATIO = 0.9                       # 칸 안쪽의 이 비율을 넘으면 한글에서 두 줄이 될 수 있다 (실측)
HANGUL_SPACE_EM = 0.5                   # 한글이 그리는 빈칸 폭 (글자 크기 대비)
ALIGNS = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}
FILL_COUNT = re.compile(r'(<hh:borderFills\b[^>]*?\bitemCnt=")(\d+)')


def ruled_fill(header_xml: str, shaded: bool) -> tuple[str, str]:
    """네 변이 실선인 칸 모양(shaded면 연한 회색 바탕)을 header에 더한다. (번호, 고친 header)"""
    if "</hh:borderFills>" not in header_xml:
        raise FillError("양식 header.xml에 칸 모양 목록이 없어 표를 만들지 못함")
    number = str(max((int(n) for n in re.findall(r'<hh:borderFill id="(\d+)"', header_xml)), default=0) + 1)
    sides = "".join(f'<hh:{side}Border type="SOLID" width="{RULE_WIDTH}" color="#000000"/>'
                    for side in ("left", "right", "top", "bottom"))
    brush = (f'<hc:fillBrush><hc:winBrush faceColor="{HEAD_SHADE}" hatchColor="#999999" alpha="0"/></hc:fillBrush>'
             if shaded else "")
    fill = (f'<hh:borderFill id="{number}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            f'{sides}<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>{brush}</hh:borderFill>')
    header_xml = header_xml.replace("</hh:borderFills>", f"{fill}</hh:borderFills>", 1)
    header_xml = FILL_COUNT.sub(lambda m: f"{m.group(1)}{int(m.group(2)) + 1}", header_xml, count=1)
    return number, header_xml


def _plain_fill(header_xml: str) -> tuple[str, str]:
    return ruled_fill(header_xml, False)


def _shaded_fill(header_xml: str) -> tuple[str, str]:
    return ruled_fill(header_xml, True)


def _ruled(media) -> tuple[str, str]:
    """(글 칸 모양, 머리 칸 모양) 번호. 처음 쓸 때 한 번만 더한다."""
    if media.ruled is None:
        media.ruled = (media.add_fill(_plain_fill), media.add_fill(_shaded_fill))
    return media.ruled


def _shown(text: str) -> str:
    return text.replace("**", "").replace("__", "")


def column_widths(spec: dict, cells: list[list[str]], total: int) -> list[int]:
    """칸 너비(HWPUNIT). widths 비율이 있으면 그대로, 없으면 칸의 가장 긴 글(2~12글자)에 맞춘다. 합은 total."""
    count = len(cells[0])
    if "widths" in spec:
        weights = [float(value) for value in spec["widths"]]
    else:
        weights = [min(WIDTH_CEIL, max(WIDTH_FLOOR, max(_text_width(_shown(row[col]), 1) for row in cells)))
                   for col in range(count)]
    widths = [int(total * weight / sum(weights)) for weight in weights]
    widths[-1] = total - sum(widths[:-1])
    return widths


def _notes_for_wide(cells: list[list[str]], widths: list[int], em: int, where: str, notes: list[str]) -> None:
    found: list[str] = []
    for row in cells:
        for text, width in zip(row, widths):
            found += [word for word in wide_words(text, width - 2 * CELL_MARGIN, em) if word not in found]
    if found:
        shown = ", ".join(found[:MAX_WIDE_NOTES]) + (" 등" if len(found) > MAX_WIDE_NOTES else "")
        notes.append(f"{where}: 표 칸보다 넓어 낱말 중간에서 줄이 바뀝니다: {shown}. table의 widths를 고쳐 주세요")
    tight = list(dict.fromkeys(text for row in cells for text, width in zip(row, widths)
                               if _fills_cell(text, width, em) and not any(word in found for word in text.split())))
    if tight:
        shown = ", ".join(tight[:MAX_WIDE_NOTES]) + (" 등" if len(tight) > MAX_WIDE_NOTES else "")
        notes.append(f"{where}: 표 칸에 꽉 차 한글에서 두 줄이 될 수 있습니다: {shown}. "
                     "table의 widths를 고치거나 단위를 머리 칸·표 제목으로 옮겨 주세요")


def _fills_cell(text: str, width: int, em: int) -> bool:
    """세 낱말 이하의 짧은 칸 글(이름·값)이 칸 안쪽의 TIGHT_RATIO를 넘는가.
    한글은 빈칸을 반 글자로 그려 어림보다 넓다 (실측: "Reading Stand" 어림 6600, 실제 약 7100)."""
    words = _shown(text).split()
    if not words or len(words) > TIGHT_WORDS:
        return False
    drawn = _text_width("".join(words), em) + (len(words) - 1) * em * HANGUL_SPACE_EM
    return drawn > (width - 2 * CELL_MARGIN) * TIGHT_RATIO


def _row_height(texts: list[str], widths: list[int], em: int, spacing: int) -> int:
    line = em * spacing // 100
    lines = max(wrap_layout(text, width - 2 * CELL_MARGIN, em)[0] for text, width in zip(texts, widths))
    return lines * line + 2 * CELL_MARGIN


def table_parts(media, spec: dict, stem, where: str, notes: list[str]) -> list[str]:
    """자료 표 문단(과 표 위 설명 문단). 문단마다 따로 돌려줘 모두 다음 문단과 함께 놓이게 한다."""
    writer = media.writer
    template, char = media._base(stem)
    em, spacing = media._em(char), media._spacing(template)
    cells = [[_plain(text) for text in row] for row in [spec["head"], *spec["rows"]]]
    total = (writer.column_width or FALLBACK_WIDTH + TABLE_SIDE) - em
    widths = column_widths(spec, cells, total)
    _notes_for_wide(cells, widths, em, where, notes)
    plain, shaded = _ruled(media)
    head_char = writer.shapes.variant(char, True, False) or char
    aligns = [ALIGNS[name] for name in spec.get("align", ["center"] * len(widths))]
    rows = []
    for index, texts in enumerate(cells):
        is_head = index == 0
        rows.append([(media._paragraph(template, "CENTER" if is_head else align,
                                       writer.runs(text, head_char if is_head else char)),
                      "CENTER", shaded if is_head else plain)
                     for text, align in zip(texts, aligns)])
    heights = [_row_height(texts, widths, em, spacing) for texts in cells]
    table = media._table(rows, widths, heights, template, char, align="RIGHT", fill=plain)
    parts = [media._paragraph(template, "CENTER", writer.runs(_plain(spec["caption"]), char))] \
        if spec.get("caption") else []
    return [*parts, table]


def _picture_widths(media, specs: list[dict], sizes: list[tuple[int, int]], room: int) -> list[int]:
    """그림 너비들. width_mm가 하나라도 있으면 각자, 없으면 높이를 맞춘다. 칸 너비와 단 높이 상한을 넘지 않는다."""
    if any("width_mm" in spec for spec in specs):
        widths = [min(room, round(float(spec["width_mm"]) * MM)) if "width_mm" in spec else room // 2
                  for spec in specs]
    else:
        height = min(room * h / w for w, h in sizes)
        widths = [round(height * w / h) for w, h in sizes]
    return [min(width, max(1, round(media.max_height * w / h))) for width, (w, h) in zip(widths, sizes)]


def picture_parts(media, value: object, stem, where: str) -> list[str]:
    """picture가 목록이면 한 줄에 나란히(둘), 하나면 Media.picture 그대로."""
    if not isinstance(value, list):
        return media.picture(value, stem, where)
    if len(value) == 1:
        return media.picture(value[0], stem, where)
    return [_picture_pair(media, value, stem, where)]


def _picture_pair(media, value: list, stem, where: str) -> str:
    writer = media.writer
    specs = [{"file": item} if isinstance(item, str) else dict(item) for item in value]
    template, char = media._base(stem)
    em, spacing = media._em(char), media._spacing(template)
    paths = [media.resolve(_path(spec, where)) for spec in specs]
    sizes = [media._picture(path, where)[1] for path in paths]
    gap = GAP_EM * em
    cell = (media._width() - gap) // 2
    widths = _picture_widths(media, specs, sizes, cell - 2 * CELL_MARGIN)
    cells = [_picture_cell(media, path, width, spec, template, char, where)
             for path, width, spec in zip(paths, widths, specs)]
    blank = media._paragraph(template, "LEFT", writer.runs("", char))
    row = [(cells[0], "TOP"), (blank, "TOP"), (cells[1], "TOP")]
    line = em * spacing // 100
    tallest = max(round(w * h / max(pw, 1)) for w, (pw, h) in zip(widths, sizes))
    caption = line if any(spec.get("caption") for spec in specs) else 0
    return media._table([row], [cell, gap, media._width() - gap - cell], [tallest + caption + 2 * CELL_MARGIN],
                        template, char)


def _path(spec: dict, where: str) -> Path:
    path = Path(spec["file"])
    if path.suffix.lower() not in MEDIA_TYPES:
        raise FillError(f"{where}: picture는 PNG, JPG, GIF, BMP 파일이어야 함: {path.name}")
    return path


def _picture_cell(media, path, width: int, spec: dict, template, char: str, where: str) -> str:
    cell = media._paragraph(template, "CENTER", media._picture_run(path, width, char, where))
    if spec.get("caption"):
        cell += media._paragraph(template, "CENTER", media.writer.runs(str(spec["caption"]), char))
    return cell
