"""teacher-kit 빌드 도구.

skills/<name>/SKILL.md 가 언급하는 `references/...`, `scripts/...` 경로를 shared/ 에서 찾아
스킬마다 복사한 뒤 다음 두 가지를 만든다.

    dist/claude-ai/<name>.zip      claude.ai 스킬 업로드용 (zip 안에 <name>/ 폴더)
    dist/plugin/<plugin-name>/     Claude Code 플러그인 폴더

shared/ 의 마크다운이 `다른파일.md` 처럼 backtick 으로 언급한 파일도 함께 따라간다.
스크립트가 import 하는 같은 폴더 모듈은 ast 로 읽어 따라가고, 빠진 모듈이 있으면 오류로 막는다.
스킬이 쓰지 않는 파일은 SKILL_EXCLUDES 에 적어 따라가지 않게 한다.

사용법:
    python tools/build.py           # 검사 후 빌드
    python tools/build.py --check   # 검사만
"""

from __future__ import annotations

import argparse
import ast
import json
import posixpath
import re
import shutil
import sys
import zipfile
from pathlib import Path, PureWindowsPath

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_FILES = 200  # claude.ai 스킬 zip 하나에 담을 수 있는 파일 수
WARN_SKILL_FILES = 180  # 이만큼 넘으면 빌드는 되지만 상한이 가깝다고 알린다
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 경로 문자는 ASCII로 제한해서 "x.md를" 같은 조사가 경로에 붙지 않게 한다
EXPLICIT_REF = re.compile(r"\b(references|scripts)/([A-Za-z0-9_\-./]*)")
BARE_MD_REF = re.compile(r"`([A-Za-z0-9_\-/]+\.md)`")
EXCLUDED_NAMES = re.compile(
    r"^(test_.*\.py|__pycache__|.*\.pyc|\..*|.*\.(bak|tmp)|Thumbs\.db|desktop\.ini|~\$.*)$",
    re.IGNORECASE)
ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)
ZIP_COMPRESS_LEVEL = 6      # zlib 기본값을 적어 둔다. 파이썬·zlib 버전이 달라져도 같은 입력이면 같은 zip이 나오게 고정
MARKETPLACE_FILE = "marketplace.json"   # 저장소용 마켓플레이스 파일. 플러그인 복사에서 뺀다
ZIP_FILE_ATTR = 0o644 << 16
ZIP_CREATE_SYSTEM_UNIX = 3
REPARSE_POINT = 0x400  # Windows 정션·심볼릭 링크 표시
BLOCK_SCALAR_MARKS = (">", "|")  # YAML 여러 줄 형식. 한 줄짜리만 읽으므로 거부한다
SHARED_SUBDIR = {"references": "", "scripts": "scripts"}

# 문서가 언급만 해도 따라 들어가는 파일 가운데, 그 스킬이 실제로 쓰지 않는 것을 적는다 (스킬 이름 -> 스킬 안 경로).
# 끝이 "/" 이면 폴더 전체다. 제외한 파일을 스킬 자기 문서(SKILL.md, 스킬 폴더의 문서)가 언급하면 빌드 오류,
# 여러 스킬이 함께 쓰는 shared 문서가 언급하면 경고다 (shared 문서는 스킬마다 고칠 수 없으므로).
_RECORD_ONLY = ("references/record-guide.md", "scripts/neis_bytes.py")  # 학생부 세 스킬만 쓴다
_EXAM_FORM_ONLY = ("scripts/fill_exam.py", "scripts/fill_exam_parse.py", "scripts/fill_exam_spec.py")  # 시험지 양식 채우기: 문항 스킬만
# 엑셀 양식 채우기(fill_xlsx)는 양식을 받는 네 스킬 모두에 넣는다 (test_skill_wiring 이 요구하는 정책)
_NO_CURRICULUM = ("references/curriculum/",)  # 성취기준 데이터를 쓰지 않는 스킬
_NO_SUBJECT_COMPETENCIES = ("references/subject-competencies.md",)  # 교과 역량 이름표: 세특·지도안만 쓴다
_LESSON_ONLY_CURRICULUM = ("references/curriculum/core-ideas/", "references/curriculum/content-elements/")
SKILL_EXCLUDES: dict[str, tuple[str, ...]] = {
    "activity-record": _NO_CURRICULUM,
    # 행특·창체만 쓰므로 교과 역량 이름표는 필요 없다. curriculum-transition.md는 교사 프로필의 학년도·교육과정 판별(2절)에 쓰므로 둔다
    "behavior-record": _NO_CURRICULUM + _NO_SUBJECT_COMPETENCIES,
    "subject-record": _LESSON_ONLY_CURRICULUM,
    "assessment-items": _RECORD_ONLY + _LESSON_ONLY_CURRICULUM,
    "class-slides": _RECORD_ONLY + _LESSON_ONLY_CURRICULUM,
    "rubric": _RECORD_ONLY + _EXAM_FORM_ONLY + _LESSON_ONLY_CURRICULUM,
    "worksheet": _RECORD_ONLY + _EXAM_FORM_ONLY + _LESSON_ONLY_CURRICULUM,
    "lesson-plan": _RECORD_ONLY + _EXAM_FORM_ONLY,
}


def _unquote(value: str) -> str:
    """'값' 이나 "값" 처럼 통째로 감싼 따옴표만 벗긴다 ("가" 할 때 "나" 는 그대로)."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"" and value[0] not in value[1:-1]:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    lines = text.lstrip("﻿").splitlines()  # 메모장이 붙이는 BOM 제거
    if not lines or lines[0].strip() != "---":
        return {}
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = _unquote(value.strip())
    return {}


def plain_value_errors(text: str) -> list[str]:
    """따옴표 없는 값에 ': '나 ' #'이 있으면 YAML이 값을 끊어 스킬을 불러오지 못한다. 값 전체를 작은따옴표로 감싸야 한다."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    errors = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        value = value.strip()
        if sep and value and not value.startswith(("'", '"', ">", "|")) and (": " in value or " #" in value):
            errors.append(f"{key.strip()} 값에 따옴표 없이 ': ' 또는 ' #'이 있어 YAML로 읽히지 않음. 값 전체를 작은따옴표로 감싸야 함")
    return errors


def validate_frontmatter(meta: dict, folder_name: str) -> list[str]:
    errors = []
    name = meta.get("name", "")
    description = meta.get("description", "")
    if not NAME_PATTERN.match(name) or len(name) > MAX_NAME_LENGTH:
        errors.append(f"name '{name}'은 영문 소문자·숫자·하이픈 {MAX_NAME_LENGTH}자 이내여야 함")
    if name != folder_name:
        errors.append(f"name '{name}'이 폴더 이름 '{folder_name}'과 다름")
    if description.startswith(BLOCK_SCALAR_MARKS):
        return errors + ["description은 한 줄로 써야 함 (>, | 여러 줄 형식은 읽지 못함)"]
    if not description:
        errors.append("description이 비어 있음")
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"description이 {len(description)}자로 {MAX_DESCRIPTION_LENGTH}자를 넘음")
    if "<" in description or ">" in description:
        errors.append("description에 꺾쇠(< >)를 쓸 수 없음")
    return errors


def _excluded(parts) -> bool:
    return any(EXCLUDED_NAMES.match(part) for part in parts)


def _is_link(path: Path) -> bool:
    """심볼릭 링크 또는 Windows 정션이면 True."""
    try:
        info = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & REPARSE_POINT)


def _is_inside(path: Path, base: Path) -> bool:
    return path.resolve().is_relative_to(base.resolve())


def _packable(path: Path, base: Path) -> bool:
    """base 기준 상대 경로가 제외 대상이 아닌 실제(링크 아닌) 파일인가."""
    return path.is_file() and not _is_link(path) and not _excluded(path.relative_to(base).parts)


def _script_assets(source: Path, target: str) -> dict[str, Path]:
    """scripts/make_x.py 를 복사할 때 make_x_* 자료 파일(템플릿, 라이선스)도 함께 가져간다.

    같은 앞머리의 .py 모듈은 가져가지 않는다. import 하는 모듈만 따라간다 (_import_targets).
    """
    folder = target.rsplit("/", 1)[0]
    return {
        f"{folder}/{path.name}": path
        for path in sorted(source.parent.glob(f"{source.stem}_*"))
        if path.suffix != ".py" and _packable(path, source.parent)
    }


def _expand(source: Path, target: str) -> dict[str, Path]:
    if source.is_file() and source.suffix == ".py":
        return {target: source, **_script_assets(source, target)}
    if source.is_file():
        return {target: source}
    return {
        f"{target.rstrip('/')}/{path.relative_to(source).as_posix()}": path
        for path in sorted(source.rglob("*"))
        if _packable(path, source) and _is_inside(path, source)  # 정션 하위 폴더로 밖을 끌어오지 않게
    }


def _normalise_ref(rel: str) -> str | None:
    """참조 경로를 정리해 돌려준다. 위험한 경로(상위 이동, 절대 경로, 드라이브)면 None."""
    if rel.startswith("/") or ":" in rel or PureWindowsPath(rel).drive:
        return None
    if ".." in rel.split("/"):
        return None
    trimmed = rel.rstrip(".")  # 문장 끝 마침표
    if not trimmed:
        return ""
    cleaned = posixpath.normpath(trimmed)
    return "" if cleaned == "." else cleaned


def _wanted_refs(text: str) -> list[tuple[str, str, bool]]:
    """(종류, 상대 경로, 반드시 있어야 하는지) 목록."""
    explicit = [(kind, rel, True) for kind, rel in EXPLICIT_REF.findall(text)]
    bare = [("references", rel, False) for rel in BARE_MD_REF.findall(text)]
    return explicit + bare


def _resolve_reference(root: Path, skill_dir: Path, kind: str, raw: str, required: bool):
    """(정리된 경로, 원본 경로, 오류 문장)을 돌려준다."""
    rel = _normalise_ref(raw)
    if rel is None:
        return None, None, f"{skill_dir.name}: '{kind}/{raw}' 경로가 안전하지 않음 (상위 폴더·절대 경로 금지)"
    if not rel or (skill_dir / kind / rel).exists():
        return None, None, None
    base = root / "shared" / SHARED_SUBDIR[kind]
    source = base / rel
    if not source.exists():
        return None, None, (f"{skill_dir.name}: '{kind}/{rel}' 파일이 없음" if required else None)
    if not _is_inside(source, base):
        return None, None, f"{skill_dir.name}: '{kind}/{rel}' 가 shared 폴더 밖을 가리킴"
    if _is_link(source):
        return None, None, (f"{skill_dir.name}: '{kind}/{rel}' 가 링크(심볼릭 링크/정션)라 가져올 수 없음"
                            if required else None)
    return rel, source, None


def _is_excluded(skill_name: str, target: str) -> bool:
    return any(target.startswith(rule) if rule.endswith("/") else target == rule
               for rule in SKILL_EXCLUDES.get(skill_name, ()))


def _imported_modules(path: Path) -> set[str]:
    """스크립트가 import 하는 최상위 모듈 이름 (상대 import와 표준 라이브러리 제외)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names - set(sys.stdlib_module_names)


def _known_local_modules(root: Path) -> set[str]:
    """저장소 안 스크립트 모듈 이름 (shared/scripts 와 skills/*/scripts). 이 밖의 이름은 외부 패키지로 본다."""
    folders = [root / "shared" / "scripts", *(root / "skills").glob("*/scripts")]
    return {path.stem for folder in folders for path in folder.glob("*.py") if _packable(path, folder)}


def _import_targets(root: Path, skill_dir: Path, script: Path) -> dict[str, Path]:
    """스크립트가 import 하는 shared 모듈 중 스킬 폴더에 없는 것: {스킬 안 경로: 원본}."""
    wanted: dict[str, Path] = {}
    shared = root / "shared" / "scripts"
    for module in sorted(_imported_modules(script)):
        source = shared / f"{module}.py"
        if (skill_dir / "scripts" / f"{module}.py").exists() or not _packable(source, shared):
            continue
        wanted[f"scripts/{module}.py"] = source
    return wanted


def collect_dependencies(root: Path, skill_dir: Path) -> tuple[dict[str, Path], list[str]]:
    """스킬이 필요로 하는 shared 파일을 {스킬 안 경로: 원본 경로}로 돌려준다."""
    deps: dict[str, Path] = {}
    errors: list[str] = []
    # SKILL.md 뿐 아니라 스킬 폴더의 references/*.md 등이 언급한 shared 파일도 따라간다
    pending = [skill_dir / "SKILL.md", *_skill_files(skill_dir).values()]
    scanned: set[Path] = set()

    def add(targets: dict[str, Path]) -> None:
        for target, path in targets.items():
            if target not in deps and not _is_excluded(skill_dir.name, target):
                deps[target] = path
                pending.append(path)

    while pending:
        document = pending.pop()
        if document in scanned or document.suffix not in (".md", ".py"):
            continue
        scanned.add(document)

        if document.suffix == ".py":
            try:
                imported = _import_targets(root, skill_dir, document)
            except (SyntaxError, ValueError) as error:  # UnicodeDecodeError는 ValueError
                errors.append(f"{skill_dir.name}: '{document.name}'을(를) 읽을 수 없음 ({type(error).__name__}: {error})")
                continue
            for target, source in imported.items():
                add(_expand(source, target))
            continue

        for kind, raw, required in _wanted_refs(document.read_text(encoding="utf-8")):
            rel, source, error = _resolve_reference(root, skill_dir, kind, raw, required)
            if error:
                errors.append(error)
            if source is not None:
                add(_expand(source, f"{kind}/{rel}"))

    return deps, sorted(set(errors))


def _mentions(text: str, target: str) -> bool:
    """문서 글이 target(스킬 안 경로)을 언급하는가: 전체 경로, 또는 backtick 으로 감싼 짧은 이름."""
    if target.endswith("/"):
        return target in text
    if re.search(re.escape(target) + r"(?![A-Za-z0-9_])", text):
        return True
    short = target.split("/", 1)[1] if target.startswith("references/") else target.rsplit("/", 1)[-1]
    return f"`{short}`" in text


def exclusion_findings(root: Path, name: str, files: dict[str, Path]) -> tuple[list[str], list[str]]:
    """제외한 파일을 남은 문서가 언급하는지 본다. (오류, 경고).

    스킬 자기 문서(SKILL.md, 스킬 폴더의 문서)의 언급은 오류, shared 문서의 언급은 경고다.
    성취기준 데이터 폴더 안의 문서는 보지 않는다.
    """
    skill_dir = root / "skills" / name
    errors: list[str] = []
    warnings: list[str] = []
    for path_in_skill, source in sorted(files.items()):
        if not path_in_skill.endswith(".md") or path_in_skill.startswith("references/curriculum/"):
            continue
        text = source.read_text(encoding="utf-8")
        own = _is_inside(source, skill_dir)
        for target in SKILL_EXCLUDES.get(name, ()):
            if _mentions(text, target):
                message = f"{name}: '{path_in_skill}'이(가) 이 스킬에 넣지 않는 '{target}'을(를) 언급함"
                (errors if own else warnings).append(message)
    return errors, warnings


def _check_imports(root: Path, name: str, files: dict[str, Path]) -> list[str]:
    """스킬 안 스크립트가 import 하는 저장소 모듈이 zip에 다 들어 있는가."""
    local = _known_local_modules(root)
    errors: list[str] = []
    for path_in_skill, source in sorted(files.items()):
        if not (path_in_skill.startswith("scripts/") and path_in_skill.endswith(".py")):
            continue
        try:
            missing = sorted(m for m in _imported_modules(source) & local if f"scripts/{m}.py" not in files)
        except (SyntaxError, ValueError):
            continue  # 읽지 못하는 스크립트는 collect_dependencies 가 이미 알렸다
        errors += [f"{name}: '{path_in_skill}'이(가) import 하는 모듈 '{m}'이(가) 스킬에 없음" for m in missing]
    return errors


def _skill_files(skill_dir: Path) -> dict[str, Path]:
    return {
        path.relative_to(skill_dir).as_posix(): path
        for path in sorted(skill_dir.rglob("*"))
        if _packable(path, skill_dir) and _is_inside(path, skill_dir)  # 정션 하위 폴더로 밖을 끌어오지 않게
    }


def _license_file(root: Path) -> dict[str, Path]:
    """저장소 LICENSE 를 스킬마다 함께 넣는다 (zip 하나만 받아 가도 라이선스가 따라가게)."""
    license_path = root / "LICENSE"
    return {"LICENSE": license_path} if _packable(license_path, root) else {}


def check(root: Path) -> tuple[dict[str, dict[str, Path]], list[str]]:
    """모든 스킬을 검사하고 {스킬 이름: {스킬 안 경로: 원본}}을 돌려준다."""
    manifests: dict[str, dict[str, Path]] = {}
    errors: list[str] = []
    for skill_md in sorted((root / "skills").glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        skill_text = skill_md.read_text(encoding="utf-8")
        meta = parse_frontmatter(skill_text)
        errors += [f"{skill_dir.name}: {e}" for e in validate_frontmatter(meta, skill_dir.name)]
        errors += [f"{skill_dir.name}: {e}" for e in plain_value_errors(skill_text)]
        deps, dep_errors = collect_dependencies(root, skill_dir)
        errors += dep_errors
        manifests[skill_dir.name] = {**deps, **_skill_files(skill_dir), **_license_file(root)}
        errors += exclusion_findings(root, skill_dir.name, manifests[skill_dir.name])[0]
        errors += _check_imports(root, skill_dir.name, manifests[skill_dir.name])
        # claude.ai 업로드는 한글·괄호·+ 가 든 경로를 "invalid characters"로 거부한다
        errors += [f"{skill_dir.name}: '{target}' 경로는 ASCII 글자만 써야 함 (claude.ai 업로드 거부)"
                   for target in manifests[skill_dir.name] if not target.isascii()]
        if len(manifests[skill_dir.name]) > MAX_SKILL_FILES:
            errors.append(f"{skill_dir.name}: 파일 {len(manifests[skill_dir.name])}개 "
                          f"(claude.ai 업로드는 {MAX_SKILL_FILES}개까지)")
    return manifests, errors + _check_plugin_meta(root)


def _check_plugin_meta(root: Path) -> list[str]:
    try:
        meta = json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:  # JSONDecodeError, UnicodeDecodeError는 ValueError
        return [f"plugin.json을 읽을 수 없음: {error}"]
    if not isinstance(meta, dict) or not NAME_PATTERN.match(str(meta.get("name", ""))):
        return ["plugin.json의 name이 없거나 형식이 잘못됨"]
    return []


def _checked_target(base: Path, relative: str) -> Path:
    """base 밖으로 나가는 경로면 오류."""
    destination = base / relative
    if posixpath.normpath(relative) != relative or not _is_inside(destination, base):
        raise ValueError(f"출력 경로가 허용 범위를 벗어남: {relative}")
    return destination


def _write_zip(zip_path: Path, name: str, files: dict[str, Path]) -> None:
    """같은 입력이면 같은 바이트가 나오도록 시간·권한·순서를 고정해서 쓴다."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_COMPRESS_LEVEL) as archive:
        for path_in_skill in sorted(files):
            entry = f"{name}/{path_in_skill}"
            _checked_target(zip_path.parent, entry)
            info = zipfile.ZipInfo(entry, ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = ZIP_FILE_ATTR
            info.create_system = ZIP_CREATE_SYSTEM_UNIX
            archive.writestr(info, files[path_in_skill].read_bytes(), compresslevel=ZIP_COMPRESS_LEVEL)


def _write_outputs(root: Path, manifests: dict[str, dict[str, Path]], target: Path) -> None:
    plugin_meta = json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8-sig"))
    plugin_dir = target / "plugin" / plugin_meta["name"]
    zip_dir = target / "claude-ai"
    zip_dir.mkdir(parents=True)
    # marketplace.json은 저장소(main)에서 마켓플레이스로 쓰는 파일이라 플러그인 안에는 넣지 않는다
    shutil.copytree(root / ".claude-plugin", plugin_dir / ".claude-plugin",
                    ignore=shutil.ignore_patterns(MARKETPLACE_FILE))
    for path_in_plugin, source in _license_file(root).items():
        shutil.copy2(source, plugin_dir / path_in_plugin)
    for name, files in manifests.items():
        _write_zip(zip_dir / f"{name}.zip", name, files)
        skill_base = plugin_dir / "skills" / name
        for path_in_skill, source in files.items():
            destination = _checked_target(skill_base, path_in_skill)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _refuse_links(*paths: Path) -> None:
    for path in paths:
        if _is_link(path):
            raise RuntimeError(f"'{path.name}' 이(가) 링크(심볼릭 링크/정션)라 빌드를 중단함: {path}")


def _swap_dist(dist: Path, staging: Path) -> None:
    """dist 를 staging 으로 교체한다. 실패하면 이전 dist 를 되돌린다."""
    old = dist.with_name(dist.name + ".old")
    _refuse_links(dist, staging, old)
    if old.exists():
        shutil.rmtree(old)
    had_previous = dist.exists()
    if had_previous:
        dist.rename(old)
    try:
        staging.rename(dist)
    except OSError:
        if had_previous:
            old.rename(dist)
        raise
    shutil.rmtree(old, ignore_errors=True)


def build(root: Path) -> list[str]:
    manifests, errors = check(root)
    if errors:
        return errors
    # 임시 폴더에 다 만든 뒤에만 기존 dist와 바꾼다 (중간에 실패해도 이전 결과가 남게)
    dist, staging = root / "dist", root / "dist.tmp"
    _refuse_links(dist, staging)
    if staging.exists():
        shutil.rmtree(staging)
    _write_outputs(root, manifests, staging)
    _swap_dist(dist, staging)
    return []


def file_count_line(count: int) -> str:
    """빌드 결과의 파일 수 줄. 상한에 가까우면 미리 알린다."""
    if count > WARN_SKILL_FILES:
        return f"파일 {count}개 (경고: claude.ai 상한 {MAX_SKILL_FILES}개에 가까움)"
    return f"파일 {count}개"


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="teacher-kit 빌드")
    parser.add_argument("--check", action="store_true", help="검사만 하고 빌드하지 않음")
    args = parser.parse_args(argv)
    root = root or Path(__file__).resolve().parent.parent
    for stream in (sys.stdout, sys.stderr):  # 한국어가 아닌 콘솔에서도 깨지지 않게
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")

    try:
        manifests, errors = check(root)
        if not errors and not args.check:
            errors = build(root)
    except (OSError, ValueError, RuntimeError) as error:  # UnicodeDecodeError는 ValueError
        sys.stderr.write(f"빌드 실패: {type(error).__name__}: {error}\n")
        return 1

    if errors:
        sys.stdout.write("오류:\n" + "\n".join(f"  - {e}" for e in errors) + "\n")
        return 1
    warnings = sorted({w for name, files in manifests.items() for w in exclusion_findings(root, name, files)[1]})
    if warnings:
        lines = [f"  - {w}" for w in warnings]
        sys.stdout.write("\n".join(["경고 (shared 문서가 이 스킬에 없는 파일을 언급함):", *lines]) + "\n")
    for name, files in manifests.items():
        sys.stdout.write(f"  {name}: {file_count_line(len(files))}\n")
    sys.stdout.write(f"완료: 스킬 {len(manifests)}개\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
