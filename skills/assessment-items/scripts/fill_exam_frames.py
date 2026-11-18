"""양식의 문항 틀 가운데 지시에 맞는 것을 고른다 (fill_exam.py에서 나눔). 표준 라이브러리만 쓴다."""

from __future__ import annotations

import re

from fill_exam_parse import (COMBO_TABLE, GRID_TABLE, KIND_NAMES, PARAGRAPHS, SHORT_TABLE, WRITTEN, ExamForm, Frame)
from fill_exam_text import AUTO_ORDER, auto_fits, auto_layout
from fill_exam_reshape import MIN_CHOICES, reshaped_layout
from fill_hwpx import FillError

NEAREST = {SHORT_TABLE: COMBO_TABLE, COMBO_TABLE: SHORT_TABLE}

def _shape_of(frame: Frame) -> tuple[int, int]:
    """(선택지 수, 표형 선지의 내용 칸 수)."""
    columns = frame.choice_table.table.cols - 1 if frame.kind == GRID_TABLE else 0
    return len(frame.slots), columns


def _wanted_shape(item: dict) -> tuple[int, int]:
    if item["type"] == GRID_TABLE:
        return len(item["rows"]), len(item["head"])
    return len(item.get("choices", ())), 0


def _reduced(frame: Frame, count: int) -> tuple[int, int] | None:
    """선택지 count개로 줄인 선지 표의 (행, 칸). 표가 아니거나 줄일 수 없으면 None."""
    if frame.kind not in (SHORT_TABLE, COMBO_TABLE):
        return None
    return reshaped_layout(frame.choice_table.table, len(frame.slots), count)


def _can_reduce(frame: Frame, count: int) -> bool:
    """틀의 선택지 자리보다 적은 선택지(2개 이상)를 담도록 줄일 수 있는가."""
    if frame.kind == PARAGRAPHS:
        return MIN_CHOICES <= count < len(frame.slots)
    return _reduced(frame, count) is not None


def _layout_of(frame: Frame, count: int) -> str | None:
    """선택지 count개를 넣은 뒤 선지 표의 "행x칸". 표가 아니면 None."""
    if frame.choice_table is None:
        return None
    rows, cols = _reduced(frame, count) or (frame.choice_table.table.rows, frame.choice_table.table.cols)
    return f"{rows}x{cols}"


def _original_layout(frame: Frame) -> str | None:
    """줄이기 전 틀의 선지 표 "행x칸". 표가 아니면 None."""
    if frame.choice_table is None:
        return None
    table = frame.choice_table.table
    return f"{table.rows}x{table.cols}"


def _layout_matches(frame: Frame, count: int, wanted: str) -> bool:
    """줄인 뒤의 행x칸이거나, 줄이기 전 틀의 이름(5지 이름 2x3·5x1·1x5)이면 맞는 것으로 본다."""
    return wanted in (_layout_of(frame, count), _original_layout(frame))


def _prefer(fits: list[Frame], item: dict, where: str, notes: list[str], auto: str | None = None) -> Frame:
    """같은 유형·선택지 수의 틀이 여럿이면 layout(선지 표 행x칸)이 맞는 틀, 그다음 <보기> 유무가 맞는 틀을 고른다."""
    wanted = re.sub(r"\s", "", str(item.get("layout", ""))).lower().replace("×", "x")
    count = len(item.get("choices", ()))
    if wanted:
        matched = [frame for frame in fits if _layout_matches(frame, count, wanted)]
        if matched:
            fits = matched
        else:
            have = ", ".join(sorted({_layout_of(frame, count) or "문단" for frame in fits}))
            notes.append(f"{where}: layout {wanted} 틀이 없어 양식의 다른 배치({have})를 썼습니다")
    elif auto:
        fits = auto_fits(fits, auto, count, _layout_matches)
    with_bogi = "bogi" in item
    return next((frame for frame in fits if (frame.bogi is not None) == with_bogi), fits[0])


def _pick_frame(exam: ExamForm, item: dict, where: str, notes: list[str]) -> Frame:
    kind = item["type"]
    kinds = [kind, NEAREST[kind]] if kind in NEAREST else [kind]
    auto = None if item.get("layout") else auto_layout(item)      # layout이 없으면 가장 긴 선지로 고른다
    if auto:
        kinds = [SHORT_TABLE, COMBO_TABLE] if auto == AUTO_ORDER[0] else [COMBO_TABLE, SHORT_TABLE]
    if not any(exam.frame_of(name) for name in kinds):
        have = ", ".join(sorted({frame.kind for frame in exam.frames}))
        raise FillError(f"{where}: 양식에 {kind}({KIND_NAMES[kind]}) 틀이 없음. 양식의 유형: {have}. "
                        "유형을 양식에 있는 것으로 바꾸거나, 그 유형이 든 양식을 교사에게 받아 주세요")
    wanted = _wanted_shape(item)
    for name in kinds:
        fits = [frame for frame in exam.frames if frame.kind == name and (kind == WRITTEN or _shape_of(frame) == wanted)]
        if fits:
            frame = _prefer(fits, item, where, notes, auto)
            if name != kind and not (auto and exam.frame_of(kind)):
                notes.append(f"{where}: {kind} 틀이 없어 가장 가까운 {name} 틀을 썼습니다")
            return frame
    for name in kinds:                          # 맞는 수의 틀이 없으면 더 많은 선택지의 틀을 줄여 쓴다 (4지·3지선다)
        fits = [frame for frame in exam.frames if frame.kind == name and kind != GRID_TABLE
                and _can_reduce(frame, wanted[0])]
        if fits:
            nearest = min(len(frame.slots) for frame in fits)
            frame = _prefer([frame for frame in fits if len(frame.slots) == nearest], item, where, notes, auto)
            if name != kind and not (auto and exam.frame_of(kind)):
                notes.append(f"{where}: {kind} 틀이 없어 가장 가까운 {name} 틀을 썼습니다")
            return frame
    shapes = sorted({_shape_of(frame) for name in kinds for frame in exam.frames if frame.kind == name})
    counts = ", ".join(f"{count}개" + (f"(내용 {cols}칸)" if cols else "") for count, cols in shapes)
    asked = f"{wanted[0]}개" + (f"(내용 {wanted[1]}칸)" if wanted[1] else "")
    raise FillError(f"{where}: 선택지가 {asked}인데 양식의 {kind} 틀은 {counts}임. 표 구조는 바꾸지 않습니다")
