"""교수·학습 및 평가 운영 계획(교과진도평가계획) 한 과목 한 학기분 한글(hwpx) 만들기.

- 중·고: 학교 교과진도평가계획 기본 양식(assets/course_plan_form_2.hwpx, 1·2학기 모두)에 채운다
  (make_course_plan_form.py). 교사가 같은 짜임의 학교 양식(hwpx)을 주면 --form으로 그 양식에 채운다.
  Ⅰ 교수학습 운영계획(진도표) · Ⅱ 평가의 목적 · Ⅲ 평가의 방향과 방침 · Ⅳ 평가의 종류와 방법
  · Ⅴ 기준 성취율과 성취도 · Ⅵ 수행평가 세부기준 · Ⅶ 수행평가 시 유의 사항 · Ⅷ 결시생의 성적 처리
  · Ⅸ 평가 결과의 활용 방안 · Ⅹ 원격수업 운영 시 평가 계획 · Ⅺ 성취기준 및 성취수준
- 초등: 표 중심 보통 양식(흑백, A4 세로)으로, 점수·반영 비율·성취도·정기시험 없이 성취기준별 단계 평가
  (make_course_plan_elementary.py)

진도표의 기간·공제일수·예정 시간·누계·행사는 학사일정에서 센다(school_calendar.py).
학교 학업성적관리규정에 따라 정할 문장("rule": true)과 어림한 학사일정 값에는 노란 형광펜과 한글 메모를 달고
(course_form_marks.py, 초·중·고 모두), 경고 맨 앞에 형광펜 수와 메모 수를 알린다.
만들 때마다 진도-평가 성취기준 연결, 반영 비율, 수행평가 배점, 평가 시기, 학사일정을 점검해 경고로 돌려준다.

입력 JSON (칸 설명과 예시 셋: references/course-plan-input.md):
{
  "info": {"year": 2026, "semester": 1, "level": "고", "school": "OO고등학교", "grade": 1, "subject": "통합사회1",
           "classes": "1반 ~ 10반", "credits": 4, "weekly_hours": 4, "teachers": ["OOO", "OOO"],
           "curriculum": "2022 개정", "course_type": "공통"},
  "calendar": {"start": "2026-03-02", "end": "2026-07-21", "no_class": [...], "events": [...], "group": 2},
  "progress": [{"weeks": "1~2", "unit": "...", "standards": ["[10통사1-01-01]"], "methods": "...", "focus": "..."}],
  "evaluation": {"purpose": [...], "direction": [...], "policy": [{"text": "...", "rule": true}],
                 "kinds": [...], "rules": {"performance_min": 40, "essay_min": 30}, "tasks": [...],
                 "cautions": [...], "absence": [...], "use": [...], "remote": [...]}
}

사용법:
    python make_course_plan.py 계획.json 계획.hwpx [--form 학교양식.hwpx]
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
for folder in (SCRIPTS, SCRIPTS.parents[2] / "shared" / "scripts"):      # 스킬 묶음 안, 저장소 안
    if (folder / "make_hwpx.py").exists():
        sys.path.insert(0, str(folder))
        break
sys.path.insert(0, str(SCRIPTS))
from make_hwpx import build_hwpx  # noqa: E402
from make_hwpx_save import file_error_message  # noqa: E402
from make_course_plan_check import plan_warnings  # noqa: E402
from make_course_plan_elementary import elementary_blocks  # noqa: E402
from make_course_plan_input import CoursePlanError, read_plan  # noqa: E402,F401  (CoursePlanError는 여기서도 쓰게)
from make_course_plan_layout import title_of  # noqa: E402
from make_hwpx_check import validate_package  # noqa: E402
from make_hwpx_save import OWN_FILES_ONLY, hwpx_check, save_atomically, write_zip  # noqa: E402
from course_form_marks import MARK_RE, apply_marks, count_marks  # noqa: E402
from make_course_plan_form import FormError, build_form  # noqa: E402

def to_spec(plan: dict, warnings: list[str]) -> dict:
    """초등 계획(정리한 입력) → make_hwpx 입력. 빈칸 경고는 warnings에 더한다. 중·고는 build_form이 맡는다."""
    info = plan["info"]
    if not info["teachers"]:
        warnings.append("지도 교사(info.teachers)가 비어 있음")
    blocks = elementary_blocks(plan, warnings)
    title = title_of(info)
    return {"title": title, "doc_title": title.replace("\n", " ").replace("<", "").replace(">", ""),
            "page": "normal", "margins": "narrow", "page_numbers": "center", "blocks": blocks}


def mark_counts(spec: dict) -> tuple[int, int]:
    """초등 보통 양식 입력의 (형광펜 수, 메모 수)."""
    return count_marks(json.dumps(spec["blocks"], ensure_ascii=False))


def apply_marks_file(path: Path, target: Path) -> None:
    """make_hwpx로 만든 파일(path)의 표식 글자를 형광펜과 메모로 바꿔 target에 한 번에 저장한다
    (미리 보기 글에서는 뺀다). 실패하면 target은 그대로다."""
    with zipfile.ZipFile(path) as source:
        infos = source.infolist()
        entries = {info.filename: source.read(info.filename) for info in infos}
    header = entries["Contents/header.xml"].decode("utf-8")
    section = apply_marks(entries["Contents/section0.xml"].decode("utf-8"), header)
    entries["Contents/section0.xml"] = section.encode("utf-8")
    if "Preview/PrvText.txt" in entries:
        entries["Preview/PrvText.txt"] = MARK_RE.sub("", entries["Preview/PrvText.txt"].decode("utf-8")).encode("utf-8")
    known = validate_package(path)
    save_atomically(target, lambda temp: write_zip(temp, infos, entries),
                    hwpx_check(RuntimeError, "형광펜·메모를 넣은 hwpx 검사 실패:", known, validate_package),
                    existing=OWN_FILES_ONLY)                     # 이 도구가 만든 파일만 바꿔 쓴다


def _pen_line(pens: int, memos: int) -> str:
    return (f"형광펜 표시 {pens}곳(메모 {memos}개): 학교 학업성적관리규정·학사일정에 맞게 고친 뒤 "
            "형광펜과 메모를 지우세요 (지우는 법은 메모에 있음)")


def build(spec: dict, out_path: Path, form: Path | None = None) -> list[str]:
    """hwpx를 만들고 경고를 돌려준다: 형광펜·메모 수, 점검 경고, 빈칸, 생성기 경고 순.

    중·고는 form(없으면 기본 양식, make_course_plan_form.py)에 채우고, 초등은 표 중심 보통 양식으로 만든다."""
    plan = read_plan(spec)
    warnings = plan_warnings(plan)
    if plan["info"]["level"] != "초":
        if not plan["info"]["teachers"]:
            warnings.append("지도 교사(info.teachers)가 비어 있음")
        (pens, memos), form_warnings = build_form(plan, Path(out_path), form)
        return [_pen_line(pens, memos), *warnings, *form_warnings]
    if form:
        raise ValueError("초등은 학교 양식 자동 채우기를 하지 않음 (references/form-fill.md 순서로 채우기)")
    layout_warnings: list[str] = []
    document = to_spec(plan, layout_warnings)
    out_path = Path(out_path)
    draft = out_path.with_name(f"~{out_path.stem}.{os.getpid()}.marks.hwpx")   # 같은 폴더의 중간 파일
    try:
        made = build_hwpx(document, draft)
        apply_marks_file(draft, out_path)
    finally:
        draft.unlink(missing_ok=True)
    return [_pen_line(*mark_counts(document)), *warnings, *layout_warnings, *made]


def _run(source: Path, target: Path, form: Path | None = None) -> tuple[str | None, list[str]]:
    """JSON을 읽어 만든다. (실패 문장 또는 None, 경고 목록). 읽기와 쓰기 오류를 나누어 알린다."""
    try:
        spec = json.loads(source.read_text(encoding="utf-8-sig"))
    except OSError as error:
        return f"입력 파일을 읽지 못함 - {file_error_message(error)}", []
    except ValueError as error:          # JSON 문법, 글자 인코딩
        return f"입력 오류: JSON을 읽지 못함 ({error})", []
    except RecursionError:
        return "입력 오류: JSON이 너무 깊게 겹쳐 있음", []
    try:
        return None, build(spec, target, form)
    except RecursionError:
        return "입력 오류: 입력이 너무 깊게 겹쳐 있음 (글 칸에는 글이나 글의 목록만 넣어 주세요)", []
    except OSError as error:
        return file_error_message(error), []
    except FormError as error:
        return f"양식 오류: {error}", []
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as error:   # RuntimeError: 만든 뒤 검사 실패
        return f"입력 오류: {error}", []
    except Exception as error:  # noqa: BLE001  예상 밖 입력도 추적 로그 대신 안내 문장으로
        return f"내부 오류: 예상하지 못한 입력입니다 ({type(error).__name__})", []


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    form = None
    if len(args) == 4 and args[2] == "--form":
        form, args = Path(args[3]), args[:2]
    if len(args) != 2:
        sys.stdout.write("사용법: python make_course_plan.py 계획.json 계획.hwpx [--form 학교양식.hwpx]\n")
        return 2
    failure, warnings = _run(Path(args[0]), Path(args[1]), form)
    if failure:
        sys.stdout.write(f"만들지 못함: {failure}\n")
        return 1
    sys.stdout.write(f"만들었습니다: {args[1]}\n")
    sys.stdout.write("".join(f"점검: {warning}\n" for warning in warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
