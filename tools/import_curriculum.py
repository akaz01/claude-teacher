"""2022 개정 교육과정 성취기준 데이터를 교과별 마크다운으로 바꾼다.

입력: greatsong/k-curriculum-2022 의 standards.json (CC BY 4.0, 고시 원문은 교육부 고시 제2022-33호 등)
출력: shared/curriculum/2022/{elementary,middle,high}/<e|m|h><번호 3자리>.md 와 2022/INDEX.md
      (파일 이름은 ASCII만 쓴다. claude.ai 스킬 업로드가 한글·괄호·+ 가 든 경로를 거부한다.
       교과군·과목 이름은 INDEX.md 표에 있다.)

사용법:
    python tools/import_curriculum.py standards.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

SOURCE = ("데이터: greatsong/k-curriculum-2022 v3.0.1 (CC BY 4.0, https://github.com/greatsong/k-curriculum-2022) / "
          "원문: 교육부 고시 제2022-33호 및 국가교육위원회 고시 제2024-3호 (국가교육과정정보센터)")
LEVELS = {"초등학교": "elementary", "중학교": "middle", "고등학교": "high"}
LEVEL_NAMES = {"elementary": "초등학교", "middle": "중학교", "high": "고등학교"}
DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "shared" / "curriculum"
REQUIRED_FIELDS = ("code", "subject_group", "subject", "content")
OPTIONAL_FIELDS = ("grade_group", "curriculum_category", "area", "explanation")  # 없거나 null 이면 빈 값
# 같은 학교급·교과군의 과목을 한 파일에 이 크기(UTF-8 바이트)까지 담는다. 과목마다 한 파일이면 268개라
# claude.ai 스킬 제한(200개)을 넘고, 두 과목씩이면 148개라 스킬에 다른 파일을 더할 여유가 없다. 한 과목은 쪼개지 않는다
MAX_FILE_BYTES = 40 * 1024
AMENDMENT_NOTE = ("초1~2 '즐거운 생활'은 국가교육위원회 고시 제2026-1호로 같은 코드에 새 문장이 정해졌지만 "
                  "2028. 3. 1.부터 적용된다. 이 데이터는 현재 적용되는 문장이다.")
# 원본 PDF 추출 때 한 낱말 안에 들어간 띄어쓰기. 앞뒤 글자까지 넣어 다른 곳이 바뀌지 않게 한다.
SPACING_FIXES = (
    ("특징으 로는", "특징으로는"), ("이해함으 로써", "이해함으로써"), ("조사함 으로써", "조사함으로써"),
    ("개괄 적으로", "개괄적으로"), ("동역학 적 상황", "동역학적 상황"), ("후천적 면역 으로", "후천적 면역으로"),
    ("계산 하거나", "계산하거나"), ("어떻게 활용 하는지", "어떻게 활용하는지"), ("공 통점", "공통점"),
    ("결상 공 식이나", "결상 공식이나"), ("수권, 기 권이", "수권, 기권이"), ("기 조력이", "기조력이"),
    ("정 도로만", "정도로만"), ("따로 정 해져", "따로 정해져"), ("생 존하는", "생존하는"), ("확 산할", "확산할"),
    ("탄 성력", "탄성력"), ("전환되면 서 ", "전환되면서 "), ("방 법이나", "방법이나"), ("토 의하도록", "토의하도록"),
    ("태 양전지", "태양전지"), ("중규모 저 기압", "중규모 저기압"), ("설명 체 계의", "설명 체계의"),
    ("행 성계", "행성계"), ("초⋅중⋅고 등학교", "초⋅중⋅고등학교"), ("전기 신 호로", "전기 신호로"),
    ("기본 단 위체", "기본 단위체"), ("예 방을", "예방을"), ("장 점과", "장점과"), ("쌍 성계", "쌍성계"),
    ("추 정한", "추정한"), ("반 복적", "반복적"), ("과학적 용 어로", "과학적 용어로"), ("파 형을", "파형을"),
    ("일기도 작 성은", "일기도 작성은"), ("대한 의 식을", "대한 의식을"), ("법칙을 이 용해", "법칙을 이용해"),
)


def fix_spacing(text: str) -> str:
    for wrong, right in SPACING_FIXES:
        text = text.replace(wrong, right)
    return text


def table_cell(text: str) -> str:
    """표 칸 안의 | 와 줄바꿈이 마크다운 표를 깨지 않게 한다."""
    return " ".join(text.splitlines()).replace("|", "\\|")


def _row_level(row: dict) -> str | None:
    """행의 학교급(elementary 등)을 돌려준다. 쓰는 값이 문자열이 아니면 ValueError."""
    where = row.get("code") if isinstance(row.get("code"), str) else "코드 없음"
    if not isinstance(row.get("school_level") or "", str):
        raise ValueError(f"{where}: 'school_level' 값이 문자열이 아님")
    level = LEVELS.get(row.get("school_level") or "")
    if level:  # 제외할 행(직업계)은 나머지 값을 쓰지 않으므로 검사하지 않는다
        for key in REQUIRED_FIELDS:
            if not isinstance(row.get(key), str):
                raise ValueError(f"{where}: '{key}' 값이 없거나 문자열이 아님")
        for key in OPTIONAL_FIELDS:
            if not isinstance(row.get(key) or "", str):
                raise ValueError(f"{where}: '{key}' 값이 문자열이 아님")
    return level


def file_name(level: str, number: int) -> str:
    """학교급 첫 글자와 학교급 안 순번으로 만든 ASCII 파일 이름 (예: middle 5번째 → m005.md)."""
    return f"{level[0]}{number:03d}.md"


def group_rows(rows: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        level = _row_level(row)
        if level:  # 직업계 전문교과(학교급 없음)는 제외
            groups[(level, row["subject_group"], row["subject"])].append(row)
    return dict(groups)


def render_subject(level: str, subject_group: str, subject: str, rows: list[dict]) -> str:
    grades = ", ".join(sorted({r.get("grade_group") or "" for r in rows} - {""}))
    categories = ", ".join(sorted({r.get("curriculum_category") or "" for r in rows} - {""}))
    lines = [f"# 2022 개정 / {LEVEL_NAMES[level]} / {subject_group} / {subject}", "",
             f"- 학년(군): {grades}", f"- 구분: {categories}", f"- 성취기준 수: {len(rows)}", f"- {SOURCE}", ""]
    areas: dict[str, list[dict]] = defaultdict(list)
    for row in rows:  # 원래 순서를 지키며 영역별로 묶는다
        areas[row.get("area") or "영역 없음"].append(row)
    for area, items in areas.items():
        lines += [f"## {area}", "", "| 코드 | 성취기준 |", "|---|---|"]
        lines += [f"| {table_cell(r['code'])} | {table_cell(fix_spacing(r['content']))} |" for r in items]
        notes = [r for r in items if r.get("explanation")]
        if notes:
            lines += ["", "### 성취기준 해설", ""]
            lines += [f"- **{r['code']}** {fix_spacing(r['explanation'])}" for r in notes]
        lines.append("")
    return "\n".join(lines)


def render_index(entries: list[tuple[str, str, str, str, int]]) -> str:
    lines = ["# 2022 개정 교육과정 성취기준 색인", "", f"- {SOURCE}", f"- 참고: {AMENDMENT_NOTE}", "",
             "학교급과 교과로 파일을 찾은 뒤 그 파일만 연다.", ""]
    for level in ("elementary", "middle", "high"):
        lines += [f"## {LEVEL_NAMES[level]}", "", "| 교과군 | 과목 | 파일 | 성취기준 수 |", "|---|---|---|---|"]
        lines += [f"| {table_cell(group)} | {table_cell(subject)} | {level}/{name} | {count} |"
                  for lv, group, subject, name, count in entries if lv == level]
        lines.append("")
    return "\n".join(lines)


def write_dataset(rows: list[dict], root: Path) -> int:
    base = root / "2022"
    entries = []
    pages: dict[tuple[str, str], list[str]] = {}  # (학교급, 파일 이름) → 과목 페이지들
    numbers: dict[str, int] = defaultdict(int)
    previous: tuple[str, str] | None = None
    for (level, group, subject), items in sorted(group_rows(rows).items()):
        page = render_subject(level, group, subject, items)
        current = pages.get((level, file_name(level, numbers[level]))) if numbers[level] else None
        used = len("\n".join(current).encode("utf-8")) if current else 0
        if previous != (level, group) or current is None or used + len(page.encode("utf-8")) + 1 > MAX_FILE_BYTES:
            numbers[level] += 1
        name = file_name(level, numbers[level])
        pages.setdefault((level, name), []).append(page)
        entries.append((level, group, subject, name, len(items)))
        previous = (level, group)
    if not entries:
        raise ValueError("학교급(초·중·고)이 있는 성취기준이 하나도 없음")
    for level in LEVEL_NAMES:  # 지난번에 만든 파일(예: 이번엔 없는 m012.md)이 남지 않게 지운다
        for stale in (base / level).glob(f"{level[0]}[0-9][0-9][0-9].md"):
            stale.unlink()
    for (level, name), subject_pages in pages.items():
        target = base / level / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(subject_pages), encoding="utf-8")
    (base / "INDEX.md").write_text(render_index(entries), encoding="utf-8")
    return sum(count for *_, count in entries)


def main(argv: list[str] | None = None, root: Path = DEFAULT_ROOT) -> int:
    args = sys.argv[1:] if argv is None else argv
    sys.stdout.reconfigure(encoding="utf-8")
    if len(args) != 1:
        sys.stdout.write("사용법: python tools/import_curriculum.py standards.json\n")
        return 2
    try:
        rows = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("최상위가 객체 목록이어야 함")
        total = write_dataset(rows, root)
    except (OSError, ValueError, KeyError) as error:  # JSONDecodeError, UnicodeDecodeError는 ValueError
        sys.stdout.write(f"입력 오류: {args[0]} 를 처리할 수 없음 ({type(error).__name__}: {error})\n")
        return 1
    sys.stdout.write(f"완료: 성취기준 {total}개\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
