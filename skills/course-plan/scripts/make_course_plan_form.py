"""중·고 교과진도평가계획을 기본 양식(학교 교과진도평가계획 hwpx)에 채운다.

기본 양식(assets/course_plan_form_2.hwpx)은 학교가 실제로 낸 교과진도평가계획에서 과목 하나를 떼어 낸 것이다
(교사 이름·메모를 지움). 1·2학기 모두 이 양식을 쓴다: 진도표 5열(시기, 시수/누계, 단원명, 성취기준, 비고),
채점 기준은 수준마다 한 열.
교사가 같은 짜임(절 제목 상자 Ⅰ~Ⅺ)의 학교 양식을 주면 그 양식에 채운다. 진도표에 수업 방법 칸이 있는 양식
(예: 시험용 scripts/testdata/course_plan_form_1.hwpx, 진도표 7열)이면 수업 방법·주안점, 예정시간/누계 칸까지 채우고,
채점 기준이 수준마다 한 행인 양식도 채운다.
용지, 글꼴, 문단 모양, 표 테두리, 절 제목 상자는 양식 그대로이고 글과 행·열 수만 바뀐다.

절 제목 상자(Ⅰ~Ⅺ)로 양식을 나눠 절마다 채운다:
머리(제목, ◆ 대상 학년·학점·지도 교사) · Ⅰ 진도표 · Ⅱ 목적 · Ⅲ 방향과 방침 · Ⅳ 종류와 방법 · Ⅴ 성취율과 성취도
· Ⅵ 수행평가 세부기준 · Ⅶ 유의 사항 · Ⅷ 결시생 · Ⅸ 결과 활용 · Ⅹ 원격수업 · Ⅺ 성취기준 및 성취수준
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from make_hwpx_check import validate_package
from make_hwpx_save import hwpx_check, save_atomically, write_zip

from course_form_eval import achievement_part, direction_part, info_paragraph, kinds_part, list_part, title_paragraph
from course_form_levels import levels_part
from course_form_marks import MARK_RE, apply_marks, count_marks
from course_form_progress import has_teaching_column, progress_table
from course_form_tasks import tasks_part
from course_form_xml import LINESEG_RE, body_height, cell_map, plain, table_shape, tables_in, top_paragraphs

ASSETS = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_FORM = ASSETS / "course_plan_form_2.hwpx"
SECTION = "Contents/section0.xml"
ROMAN = "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪ"
LIST_PARTS = {"Ⅱ": ("purpose", "평가의 목적"), "Ⅶ": ("cautions", "수행평가 시 유의 사항"),
              "Ⅷ": ("absence", "결시생의 성적 처리"), "Ⅸ": ("use", "평가 결과의 활용 방안"),
              "Ⅹ": ("remote", "원격수업 운영 시 평가 계획")}
TABLE_ID_RE = re.compile(r'<hp:tbl id="(\d+)"')


class FormError(ValueError):
    """기본 양식을 읽지 못하거나 짜임이 예상과 다를 때 (한국어 알림)."""


# ---------------------------------------------------------------- 양식 나누기

def headings(paragraphs: list[str]) -> dict[str, int]:
    """절 번호(Ⅰ~Ⅺ) → 그 절 제목 상자(1행 2열 표)가 든 문단 번호."""
    found = {}
    for index, paragraph in enumerate(paragraphs):
        for start, end in tables_in(paragraph):
            table = paragraph[start:end]
            if table_shape(table) == (1, 2):
                mark = plain(cell_map(table)[(0, 0)]).strip()
                if mark in ROMAN and mark not in found:
                    found[mark] = index
    return found


def _parts(paragraphs: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """(머리 문단들, [(절 번호, 그 절 문단들)])."""
    marks = headings(paragraphs)
    if "Ⅰ" not in marks or "Ⅵ" not in marks:
        raise FormError("양식에서 절 제목 상자(Ⅰ, Ⅵ)를 찾지 못함: 기본 양식과 짜임이 달라 이 프로그램으로는 채울 수 없음")
    order = sorted(marks.items(), key=lambda item: item[1])
    parts = [(mark, paragraphs[start:(order[n + 1][1] if n + 1 < len(order) else len(paragraphs))])
             for n, (mark, start) in enumerate(order)]
    return paragraphs[:order[0][1]], parts


# ---------------------------------------------------------------- 절 채우기

def _header(paragraphs: list[str], info: dict) -> list[str]:
    out = []
    for paragraph in paragraphs:
        text = plain(paragraph)
        if tables_in(paragraph) and "학년도" in text:
            paragraph = title_paragraph(paragraph, info)
        elif tables_in(paragraph) and "◆" in text:
            paragraph = info_paragraph(paragraph, info)
        out.append(paragraph)
    return out


def _progress(paragraphs: list[str], plan: dict, warnings: list[str]) -> list[str]:
    first = paragraphs[0]
    tables = [first[a:b] for a, b in tables_in(first) if table_shape(first[a:b])[0] >= 3]
    if not tables:
        raise FormError("양식에서 진도표를 찾지 못함")
    if not has_teaching_column(tables[0]) and any(row["methods"] or row["focus"] for row in plan["progress"]):
        warnings.append("양식 진도표에 수업 방법·주안점 칸이 없어 progress의 methods, focus는 넣지 않음")
    return [first.replace(tables[0], progress_table(tables[0], plan), 1)] + paragraphs[1:]


def _note_template(first_part: list[str]) -> str:
    """'※ …' 안내 문단 모양 (Ⅰ 진도표 아래 문단)."""
    for paragraph in first_part:
        if not tables_in(paragraph) and plain(paragraph).strip().startswith("※"):
            return paragraph
    return first_part[-1]


def fill_parts(paragraphs: list[str], plan: dict, warnings: list[str], page: int = 0) -> list[str]:
    """절마다 채운다. page는 쪽 본문 높이(Ⅵ 과제 표를 쪽에 맞춰 배치할 때 씀, 0이면 맞추지 않음)."""
    head, parts = _parts(paragraphs)
    info, evaluation = plan["info"], plan["evaluation"]
    note = _note_template(dict(parts)["Ⅰ"])
    out = _header(head, info)
    for mark, part in parts:
        if mark == "Ⅰ":
            part = _progress(part, plan, warnings)
        elif mark in LIST_PARTS:
            key, title = LIST_PARTS[mark]
            part = list_part(part, evaluation[key], f"{title}(evaluation.{key})", warnings, rule_tables=key == "absence")
        elif mark == "Ⅲ":
            part = direction_part(part, evaluation, warnings)
        elif mark == "Ⅳ":
            part = kinds_part(part, evaluation, info["semester"], note, warnings)
        elif mark == "Ⅴ":
            part = achievement_part(part, info["course_type"])
        elif mark == "Ⅵ":
            part = tasks_part(part, evaluation, warnings, page)
        elif mark == "Ⅺ":
            part = levels_part(part, evaluation.get("achievement_levels"), warnings, page)
        out += part
    return out


def _unique_table_ids(xml: str) -> str:
    """복제한 표의 id가 겹치지 않게 새 번호를 준다."""
    seen: set[str] = set()
    next_id = max((int(found) for found in TABLE_ID_RE.findall(xml)), default=1000000000)

    def renumber(match: re.Match) -> str:
        nonlocal next_id
        if match.group(1) not in seen:
            seen.add(match.group(1))
            return match.group(0)
        next_id += 1
        return f'<hp:tbl id="{next_id}"'
    return TABLE_ID_RE.sub(renumber, xml)


OBJECT_TAGS = ("<hp:tbl", "<hp:pic", "<hp:ole", "<hp:container", "<hp:rect", "<hp:ellipse", "<hp:line",
               "<hp:polygon", "<hp:curve", "<hp:equation", "<hp:textart", "<hp:ctrl", "<hp:secPr")


def _empty(paragraph: str) -> bool:
    """글도 표·그림 같은 개체도 없는 문단."""
    return not plain(paragraph).strip() and not any(tag in paragraph for tag in OBJECT_TAGS)


def _trim_tail(paragraphs: list[str]) -> list[str]:
    """맨 끝의 빈 문단은 하나만 남긴다 (양식 끝 빈 줄이 마지막 쪽 뒤에 빈 쪽을 만들지 않게)."""
    end = len(paragraphs)
    while end > 2 and all(_empty(p) for p in paragraphs[end - 2:end]):
        end -= 1
    return paragraphs[:end]


def fill_section(section: str, plan: dict, warnings: list[str],
                 header: str = "") -> tuple[str, tuple[int, int]]:
    """양식 구역 XML 전체를 채운 새 XML과 (형광펜 수, 메모 수). 줄 배치는 한글이 다시 잡게 뺀다.
    학교 환경에 따라 바꿀 곳의 표식은 마지막에 형광펜과 메모로 바꾼다(course_form_marks.py)."""
    section = MARK_RE.sub("", section)                  # 양식 글에 섞인 표식 글자(사용자 영역 문자)는 뺀다
    spans = top_paragraphs(section)
    paragraphs = [section[start:end] for start, end in spans]
    filled = _trim_tail(fill_parts(paragraphs, plan, warnings, body_height(section)))
    body = LINESEG_RE.sub("", "".join(filled))
    counts = count_marks(body)
    filled_section = section[:spans[0][0]] + apply_marks(body, header) + section[spans[-1][1]:]
    return _unique_table_ids(filled_section), counts


# ---------------------------------------------------------------- 저장

def doc_title(info: dict) -> str:
    return f"{info['year']}학년도 {info['semester']}학기 <{info['subject']}> 교수학습 및 평가 운영계획"


def _hpf_title(content: bytes, title: str) -> bytes:
    safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(rb"<opf:title>[^<]*</opf:title>", f"<opf:title>{safe}</opf:title>".encode("utf-8"), content,
                  count=1)


def build_form(plan: dict, out_path: Path, form: Path | None = None) -> tuple[tuple[int, int], list[str]]:
    """양식(form, 없으면 기본 양식)에 채워 저장한다. ((형광펜 수, 메모 수), 경고)를 돌려준다."""
    form = Path(form) if form else DEFAULT_FORM
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(form) as source:
            infos = source.infolist()
            entries = {info.filename: source.read(info.filename) for info in infos}
    except zipfile.BadZipFile as error:
        raise FormError("양식이 hwpx 파일이 아님 (hwp는 한글에서 hwpx로 저장해 주세요)") from error
    if SECTION not in entries or "Contents/content.hpf" not in entries:
        raise FormError("양식이 hwpx 파일이 아님 (본문 구역을 찾지 못함)")
    others = sorted(name for name in entries if re.fullmatch(r"Contents/section\d+\.xml", name) and name != SECTION)
    if others:
        warnings.append(f"양식에 구역이 {len(others) + 1}개 있어 첫 구역만 채움 (다른 과목 구역은 지우고 주세요)")
    header = entries.get("Contents/header.xml", b"").decode("utf-8")
    source_section = entries[SECTION].decode("utf-8")
    try:
        section, counts = fill_section(source_section, plan, warnings, header)
    except (StopIteration, KeyError, IndexError) as error:
        raise FormError(f"양식 짜임이 기본 양식과 달라 채우지 못함 ({type(error).__name__}): "
                        "references/form-fill.md 순서로 채워 주세요") from None
    old_ids = re.findall(r'<hp:fieldBegin id="(\d+)" type="MEMO"', source_section)
    new_ids = set(re.findall(r'<hp:fieldBegin id="(\d+)" type="MEMO"', section))
    kept_memos = sum(1 for memo_id in old_ids if memo_id in new_ids) if old_ids else source_section.count('type="MEMO"')
    if kept_memos:
        warnings.append(f"양식에 원래 있던 메모 {kept_memos}개가 남아 있음: 한글에서 확인하세요")
    entries[SECTION] = section.encode("utf-8")
    title = doc_title(plan["info"])
    if "Preview/PrvText.txt" in entries:
        entries["Preview/PrvText.txt"] = title.encode("utf-8")
    entries["Contents/content.hpf"] = _hpf_title(entries["Contents/content.hpf"], title)
    known = validate_package(form)          # 교사가 다른 양식을 넘겼을 때 그 양식에 원래 있던 문제는 빼고 검사
    save_atomically(Path(out_path), lambda path: write_zip(path, infos, entries),
                    hwpx_check(FormError, "만든 hwpx 검사 실패:", known, validate_package))
    return counts, warnings
