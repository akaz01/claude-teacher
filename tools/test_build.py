import contextlib
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from build import (
    MAX_SKILL_FILES,
    SKILL_EXCLUDES,
    _checked_target,
    _normalise_ref,
    _swap_dist,
    build,
    check,
    collect_dependencies,
    exclusion_findings,
    main,
    parse_frontmatter,
    plain_value_errors,
    validate_frontmatter,
)

VALID_SKILL = """---
name: sample-skill
description: 예시 스킬. "예시"라고 할 때 사용.
---

# 예시

- `references/a.md`를 참고한다.
- `scripts/tool.py`를 실행한다.
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def link_or_skip(test: unittest.TestCase, link: Path, target: Path) -> None:
    """심볼릭 링크를 만든다. 권한이 없으면 테스트를 건너뛴다."""
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        test.skipTest("symlink 생성 권한 없음")


def junction_or_skip(test: unittest.TestCase, link: Path, target: Path) -> None:
    """Windows 정션을 만든다 (rglob 이 따라 들어간다). 다른 OS면 디렉터리 심볼릭 링크."""
    try:
        import _winapi
    except ImportError:
        link_or_skip(test, link, target)
        return
    _winapi.CreateJunction(str(target), str(link))


class FrontmatterTest(unittest.TestCase):
    def test_parses_name_and_description(self):
        meta = parse_frontmatter(VALID_SKILL)
        self.assertEqual(meta["name"], "sample-skill")
        self.assertTrue(meta["description"].startswith("예시 스킬"))

    def test_missing_frontmatter_returns_empty(self):
        self.assertEqual(parse_frontmatter("# 제목만"), {})

    def test_valid_frontmatter_has_no_errors(self):
        meta = parse_frontmatter(VALID_SKILL)
        self.assertEqual(validate_frontmatter(meta, "sample-skill"), [])

    def test_rejects_name_not_matching_folder(self):
        errors = validate_frontmatter({"name": "other", "description": "x"}, "sample-skill")
        self.assertTrue(any("폴더" in e for e in errors))

    def test_rejects_uppercase_or_korean_name(self):
        for bad in ("Sample", "지도안", "a_b"):
            errors = validate_frontmatter({"name": bad, "description": "x"}, bad)
            self.assertTrue(errors, bad)

    def test_rejects_missing_or_long_description(self):
        self.assertTrue(validate_frontmatter({"name": "a"}, "a"))
        self.assertTrue(validate_frontmatter({"name": "a", "description": "가" * 1025}, "a"))

    def test_rejects_angle_brackets_in_description(self):
        errors = validate_frontmatter({"name": "a", "description": "<b>굵게</b>"}, "a")
        self.assertTrue(errors)

    def test_missing_closing_marker_returns_empty(self):
        self.assertEqual(parse_frontmatter("---\nname: a\ndescription: b\n"), {})

    def test_rejects_multiline_block_description(self):
        for marker in ("|", ">", "|-", ">-"):
            meta = parse_frontmatter(f"---\nname: a\ndescription: {marker}\n  여러 줄 설명\n---\n")
            errors = validate_frontmatter(meta, "a")
            self.assertTrue(any("한 줄" in e for e in errors), (marker, errors))

    def test_strips_matching_surrounding_quotes(self):
        meta = parse_frontmatter("---\nname: 'sample-skill'\ndescription: \"따옴표 설명\"\n---\n")
        self.assertEqual(meta, {"name": "sample-skill", "description": "따옴표 설명"})
        self.assertEqual(validate_frontmatter(meta, "sample-skill"), [])

    def test_keeps_inner_quotes_that_are_not_wrapping(self):
        meta = parse_frontmatter('---\ndescription: "수업" 할 때 "지도안"\n---\n')
        self.assertEqual(meta["description"], '"수업" 할 때 "지도안"')


class DependencyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root / "shared/a.md", "본문은 `b.md`와 `checklists/c.md`를 따른다.")
        write(self.root / "shared/b.md", "B")
        write(self.root / "shared/checklists/c.md", "C")
        write(self.root / "shared/unused.md", "안 쓰임")
        write(self.root / "shared/scripts/tool.py", "print('tool')")
        write(self.root / "skills/sample-skill/SKILL.md", VALID_SKILL)

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolves_direct_and_transitive_references(self):
        deps, errors = collect_dependencies(self.root, self.root / "skills/sample-skill")
        self.assertEqual(errors, [])
        self.assertEqual(
            set(deps),
            {"references/a.md", "references/b.md", "references/checklists/c.md", "scripts/tool.py"},
        )

    def test_reports_missing_reference(self):
        write(self.root / "skills/sample-skill/SKILL.md", VALID_SKILL + "\n`references/none.md`\n")
        _, errors = collect_dependencies(self.root, self.root / "skills/sample-skill")
        self.assertTrue(any("none.md" in e for e in errors))

    def test_skill_local_files_are_not_copied_from_shared(self):
        write(self.root / "skills/sample-skill/scripts/tool.py", "print('local')")
        deps, errors = collect_dependencies(self.root, self.root / "skills/sample-skill")
        self.assertEqual(errors, [])
        self.assertNotIn("scripts/tool.py", deps)

    def test_script_brings_same_stem_assets_but_not_tests(self):
        write(self.root / "shared/scripts/tool_template.bin", "asset")
        write(self.root / "shared/scripts/test_tool.py", "test")
        write(self.root / "shared/scripts/toolbox.py", "unrelated")
        deps, errors = collect_dependencies(self.root, self.root / "skills/sample-skill")
        self.assertEqual(errors, [])
        self.assertIn("scripts/tool_template.bin", deps)
        self.assertNotIn("scripts/test_tool.py", deps)
        self.assertNotIn("scripts/toolbox.py", deps)

    def test_skill_local_markdown_references_are_followed(self):
        write(self.root / "skills/sample-skill/SKILL.md", VALID_SKILL.split("# 예시")[0] + "`references/local.md`")
        write(self.root / "skills/sample-skill/references/local.md", "`checklists/c.md`를 따른다.")
        deps, errors = collect_dependencies(self.root, self.root / "skills/sample-skill")
        self.assertEqual(errors, [])
        self.assertIn("references/checklists/c.md", deps)

    def test_directory_reference_copies_whole_directory(self):
        write(self.root / "shared/curriculum/README.md", "R")
        write(self.root / "shared/curriculum/2022/math.md", "M")
        write(self.root / "skills/sample-skill/SKILL.md", VALID_SKILL + "\n`references/curriculum/`\n")
        deps, errors = collect_dependencies(self.root, self.root / "skills/sample-skill")
        self.assertEqual(errors, [])
        self.assertIn("references/curriculum/2022/math.md", deps)


class ImportFollowTest(unittest.TestCase):
    """스크립트가 import 하는 같은 폴더 모듈을 이름 앞머리와 상관없이 따라간다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill = self.root / "skills/sample-skill"
        write(self.skill / "SKILL.md", VALID_SKILL)
        write(self.root / "shared/a.md", "A")
        write(self.root / "shared/scripts/tool.py", "import json\nimport helper\nimport pptx\nfrom tool_sub import x\n")
        write(self.root / "shared/scripts/helper.py", "from deep import y\n")
        write(self.root / "shared/scripts/deep.py", "y = 1")
        write(self.root / "shared/scripts/tool_sub.py", "x = 1")
        write(self.root / "shared/scripts/tool_data.bin", "asset")
        write(self.root / "shared/scripts/unrelated.py", "z = 1")

    def tearDown(self):
        self.tmp.cleanup()

    def test_imported_modules_are_followed_whatever_their_name(self):
        deps, errors = collect_dependencies(self.root, self.skill)
        self.assertEqual(errors, [])
        self.assertTrue({"scripts/helper.py", "scripts/deep.py", "scripts/tool_sub.py"} <= set(deps))

    def test_same_stem_py_files_are_no_longer_pulled_without_import(self):
        write(self.root / "shared/scripts/tool_unused.py", "u = 1")
        deps, _ = collect_dependencies(self.root, self.skill)
        self.assertNotIn("scripts/tool_unused.py", deps)
        self.assertNotIn("scripts/unrelated.py", deps)
        self.assertIn("scripts/tool_data.bin", deps)

    def test_stdlib_and_external_packages_are_ignored(self):
        deps, errors = collect_dependencies(self.root, self.skill)
        self.assertEqual(errors, [])
        self.assertNotIn("scripts/json.py", deps)
        self.assertNotIn("scripts/pptx.py", deps)

    def test_skill_own_script_imports_are_followed_too(self):
        write(self.skill / "scripts/own.py", "import deep\n")
        deps, _ = collect_dependencies(self.root, self.skill)
        self.assertIn("scripts/deep.py", deps)

    def test_excluded_module_imported_by_kept_script_stops_check(self):
        with mock.patch.dict(SKILL_EXCLUDES, {"sample-skill": ("scripts/deep.py",)}):
            manifests, errors = check(self.root)
        self.assertTrue(any("'deep'" in e for e in errors), errors)

    def test_complete_package_has_no_import_errors(self):
        write(self.root / ".claude-plugin/plugin.json", '{"name": "kit"}')
        _, errors = check(self.root)
        self.assertEqual(errors, [])


class SkillExcludeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill = self.root / "skills/sample-skill"
        write(self.skill / "SKILL.md", VALID_SKILL)
        write(self.root / ".claude-plugin/plugin.json", '{"name": "kit"}')
        write(self.root / "shared/a.md", "`record-guide.md`와 `references/curriculum/core-ideas/` 참고")
        write(self.root / "shared/record-guide.md", "G")
        write(self.root / "shared/curriculum/README.md", "R")
        write(self.root / "shared/curriculum/core-ideas/math.md", "M")
        write(self.root / "shared/curriculum/2022/x.md", "X")
        write(self.root / "shared/scripts/tool.py", "print('tool')")
        write(self.root / "shared/scripts/neis_bytes.py", "n = 1")
        write(self.skill / "SKILL.md", VALID_SKILL + "\n`references/curriculum/2022/x.md`\n")

    def tearDown(self):
        self.tmp.cleanup()

    def rules(self, *targets):
        return mock.patch.dict(SKILL_EXCLUDES, {"sample-skill": targets})

    def test_excluded_files_and_folders_are_not_copied(self):
        with self.rules("references/record-guide.md", "references/curriculum/core-ideas/"):
            deps, errors = collect_dependencies(self.root, self.skill)
        self.assertEqual(errors, [])
        self.assertNotIn("references/record-guide.md", deps)
        self.assertNotIn("references/curriculum/core-ideas/math.md", deps)
        self.assertIn("references/curriculum/2022/x.md", deps)

    def test_nothing_is_excluded_without_a_rule(self):
        deps, _ = collect_dependencies(self.root, self.skill)
        self.assertIn("references/record-guide.md", deps)

    def test_skill_own_document_mentioning_excluded_file_is_an_error(self):
        write(self.skill / "SKILL.md", VALID_SKILL + "\n`references/record-guide.md`\n")
        with self.rules("references/record-guide.md"):
            _, errors = check(self.root)
        self.assertTrue(any("record-guide.md" in e for e in errors), errors)

    def test_bare_name_in_skill_own_document_is_an_error(self):
        write(self.skill / "references/local.md", "`record-guide.md`를 따른다.")
        with self.rules("references/record-guide.md"):
            _, errors = check(self.root)
        self.assertTrue(any("record-guide.md" in e for e in errors), errors)

    def test_shared_document_mention_is_only_a_warning(self):
        with self.rules("references/record-guide.md"):
            manifests, errors = check(self.root)
            found_errors, warnings = exclusion_findings(self.root, "sample-skill", manifests["sample-skill"])
        self.assertEqual(errors, [])
        self.assertEqual(found_errors, [])
        self.assertTrue(any("references/a.md" in w for w in warnings), warnings)

    def test_main_prints_warnings_but_succeeds(self):
        with self.rules("references/record-guide.md"):
            code, out, _ = MainTest().call_main(["--check"], self.root)
        self.assertEqual(code, 0)
        self.assertIn("경고", out)
        self.assertIn("record-guide.md", out)

    def test_directory_rule_does_not_match_other_references(self):
        write(self.skill / "SKILL.md", VALID_SKILL)
        write(self.skill / "references/local.md", "`references/curriculum-transition.md`")
        write(self.root / "shared/curriculum-transition.md", "T")
        with self.rules("references/curriculum/"):
            _, errors = check(self.root)
        self.assertEqual(errors, [])

    def test_every_rule_names_a_real_skill_and_a_real_shared_file(self):
        repo = Path(__file__).resolve().parent.parent
        for name, targets in SKILL_EXCLUDES.items():
            self.assertTrue((repo / "skills" / name / "SKILL.md").exists(), name)
            for target in targets:
                kind, rel = target.split("/", 1)
                base = repo / "shared" / ("scripts" if kind == "scripts" else "")
                self.assertTrue((base / rel).exists(), f"{name}: {target}")


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root / ".claude-plugin/plugin.json", '{"name": "kit"}')
        write(self.root / "shared/a.md", "본문은 `b.md`를 따른다.")
        write(self.root / "shared/b.md", "B")
        write(self.root / "shared/scripts/tool.py", "print('tool')")
        write(self.root / "skills/sample-skill/SKILL.md", VALID_SKILL)
        write(self.root / "skills/sample-skill/scripts/test_tool.py", "테스트는 배포 제외")

    def tearDown(self):
        self.tmp.cleanup()

    def test_non_ascii_path_stops_build(self):
        # claude.ai 스킬 업로드가 "Zip file contains path with invalid characters"로 거부했다 (과학_과학.md)
        write(self.root / "skills/sample-skill/references/과학_과학.md", "데이터")
        errors = build(self.root)
        self.assertTrue(any("과학_과학.md" in e and "ASCII" in e for e in errors), errors)
        self.assertFalse((self.root / "dist").exists())

    def test_root_license_ships_in_every_zip_and_plugin(self):
        write(self.root / "LICENSE", "라이선스 전문")
        self.assertEqual(build(self.root), [])
        with zipfile.ZipFile(self.root / "dist/claude-ai/sample-skill.zip") as archive:
            self.assertEqual(archive.read("sample-skill/LICENSE").decode("utf-8"), "라이선스 전문")
        self.assertTrue((self.root / "dist/plugin/kit/LICENSE").is_file())
        self.assertTrue((self.root / "dist/plugin/kit/skills/sample-skill/LICENSE").is_file())

    def test_license_counts_toward_file_limit(self):
        manifests, _ = check(self.root)
        for number in range(MAX_SKILL_FILES - len(manifests["sample-skill"])):
            write(self.root / f"skills/sample-skill/references/d{number:03d}.md", "x")
        self.assertEqual(build(self.root), [])  # 라이선스 없이 딱 200개면 통과
        write(self.root / "LICENSE", "라이선스 전문")
        self.assertTrue(any("200" in e for e in build(self.root)))  # 라이선스까지 201개

    def test_too_many_files_stops_build(self):
        # claude.ai 스킬 업로드가 "Zip contains too many files (maximum 200)"로 거부했다
        for number in range(200):
            write(self.root / f"skills/sample-skill/references/d{number:03d}.md", "x")
        errors = build(self.root)
        self.assertTrue(any("200" in e for e in errors), errors)

    def test_builds_zip_with_skill_folder_and_dependencies(self):
        errors = build(self.root)
        self.assertEqual(errors, [])
        with zipfile.ZipFile(self.root / "dist/claude-ai/sample-skill.zip") as archive:
            names = set(archive.namelist())
        self.assertIn("sample-skill/SKILL.md", names)
        self.assertIn("sample-skill/references/a.md", names)
        self.assertIn("sample-skill/references/b.md", names)
        self.assertIn("sample-skill/scripts/tool.py", names)
        self.assertNotIn("sample-skill/scripts/test_tool.py", names)

    def test_testdata_folder_is_not_shipped(self):
        # course-plan의 시험용 학교 양식(scripts/testdata)은 배포하지 않는다
        write(self.root / "skills/sample-skill/scripts/testdata/form.hwpx", "시험용 양식")
        self.assertEqual(build(self.root), [])
        with zipfile.ZipFile(self.root / "dist/claude-ai/sample-skill.zip") as archive:
            self.assertFalse(any("testdata" in name for name in archive.namelist()))

    def test_builds_plugin_folder(self):
        build(self.root)
        plugin = self.root / "dist/plugin/kit"
        self.assertTrue((plugin / ".claude-plugin/plugin.json").exists())
        self.assertTrue((plugin / "skills/sample-skill/references/a.md").exists())

    def test_system_files_are_not_packaged(self):
        for junk in (".DS_Store", "Thumbs.db", "desktop.ini", "~$양식.xlsx"):
            write(self.root / "skills/sample-skill" / junk, "x")
        build(self.root)
        with zipfile.ZipFile(self.root / "dist/claude-ai/sample-skill.zip") as archive:
            names = " ".join(archive.namelist())
        for junk in (".DS_Store", "Thumbs.db", "desktop.ini", "~$"):
            self.assertNotIn(junk, names)

    def test_skill_file_with_bom_is_read(self):
        (self.root / "skills/sample-skill/SKILL.md").write_text("﻿" + VALID_SKILL, encoding="utf-8")
        self.assertEqual(build(self.root), [])

    def test_broken_plugin_json_keeps_previous_dist(self):
        self.assertEqual(build(self.root), [])
        (self.root / ".claude-plugin/plugin.json").write_text("{}", encoding="utf-8")
        errors = build(self.root)
        self.assertTrue(errors)
        self.assertTrue((self.root / "dist/claude-ai/sample-skill.zip").exists())

    def test_invalid_skill_stops_build(self):
        write(self.root / "skills/Bad/SKILL.md", "---\nname: Bad\n---\n")
        errors = build(self.root)
        self.assertTrue(errors)
        self.assertFalse((self.root / "dist/claude-ai/sample-skill.zip").exists())


class TraversalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root / "shared/a.md", "A")
        write(self.root / "shared/refer/secret.txt", "비밀")
        write(self.root / "shared/checklists/c.md", "C")
        write(self.root / "secret.txt", "루트 비밀")
        write(self.root / ".claude-plugin/plugin.json", '{"name": "kit"}')
        self.skill = self.root / "skills/sample-skill"

    def tearDown(self):
        self.tmp.cleanup()

    def collect(self, line):
        write(self.skill / "SKILL.md", VALID_SKILL.split("# 예시")[0] + f"\n{line}\n")
        return collect_dependencies(self.root, self.skill)

    def test_dotdot_reference_is_rejected(self):
        deps, errors = self.collect("`references/../refer/secret.txt`")
        self.assertTrue(any("sample-skill" in e and "../refer/secret.txt" in e for e in errors))
        self.assertFalse([t for t in deps if ".." in t or "secret" in t])

    def test_escape_above_shared_is_rejected(self):
        deps, errors = self.collect("`references/../../secret.txt`")
        self.assertTrue(errors)
        self.assertEqual(deps, {})

    def test_trailing_dotdot_does_not_pull_directories(self):
        for line in ("`scripts/..`", "`references/checklists/..`", "`references/..`"):
            deps, errors = self.collect(line)
            self.assertEqual(deps, {}, line)
            self.assertTrue(errors, line)

    def test_normal_nested_reference_still_works(self):
        deps, errors = self.collect("`references/checklists/c.md`")
        self.assertEqual(errors, [])
        self.assertEqual(set(deps), {"references/checklists/c.md"})

    def test_symlinked_files_are_skipped(self):
        link = self.root / "shared/checklists/link.md"
        try:
            os.symlink(self.root / "secret.txt", link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink 생성 권한 없음")
        deps, _ = self.collect("`references/checklists/`")
        self.assertIn("references/checklists/c.md", deps)
        self.assertNotIn("references/checklists/link.md", deps)

    def test_required_reference_to_link_is_an_error(self):
        # shared 안을 가리키는 링크라도 빠진 채 빌드가 성공하면 안 된다
        link_or_skip(self, self.root / "shared/x.md", self.root / "shared/a.md")
        deps, errors = self.collect("`references/x.md`")
        self.assertEqual(deps, {})
        self.assertTrue(any("x.md" in e and "링크" in e for e in errors), errors)

    def test_reference_linking_outside_shared_is_rejected(self):
        link_or_skip(self, self.root / "shared/out.md", self.root / "secret.txt")
        deps, errors = self.collect("`references/out.md`")
        self.assertEqual(deps, {})
        self.assertTrue(any("out.md" in e and "밖" in e for e in errors), errors)

    def test_linked_subdirectory_inside_reference_dir_is_skipped(self):
        outside = self.root / "outside"
        write(outside / "leak.md", "밖 파일")
        junction_or_skip(self, self.root / "shared/checklists/sub", outside)
        deps, errors = self.collect("`references/checklists/`")
        self.assertEqual(errors, [])
        self.assertIn("references/checklists/c.md", deps)
        self.assertFalse([t for t in deps if "leak" in t], deps)

    def test_absolute_reference_is_rejected(self):
        deps, errors = self.collect("`references//etc/passwd`")
        self.assertEqual(deps, {})
        self.assertTrue(any("안전하지 않음" in e for e in errors), errors)

    def test_dots_only_reference_is_ignored(self):
        self.assertEqual(_normalise_ref("..."), "")
        self.assertEqual(_normalise_ref("."), "")


class HardeningBuildTest(unittest.TestCase):
    def make_root(self, base: Path) -> Path:
        root = base / "proj"
        write(root / ".claude-plugin/plugin.json", '{"name": "kit"}')
        write(root / "shared/a.md", "A")
        write(root / "skills/sample-skill/SKILL.md", VALID_SKILL.replace("scripts/tool.py", "references/a.md"))
        return root

    def zip_names(self, root):
        with zipfile.ZipFile(root / "dist/claude-ai/sample-skill.zip") as archive:
            return set(archive.namelist())

    def test_project_under_excluded_named_parent_still_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(Path(tmp) / "__pycache__")
            self.assertEqual(build(root), [])
            self.assertIn("sample-skill/SKILL.md", self.zip_names(root))

    def test_dotfiles_backups_and_temp_files_are_not_zipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(Path(tmp))
            skill = root / "skills/sample-skill"
            for junk in (".env", "x.bak", "y.tmp", ".git/config", "~$lock.docx"):
                write(skill / junk, "x")
            write(root / "shared/.env", "x")
            write(root / "shared/dir/z.bak", "x")
            self.assertEqual(build(root), [])
            self.assertEqual(self.zip_names(root), {"sample-skill/SKILL.md", "sample-skill/references/a.md"})

    def test_linked_subdirectory_inside_skill_dir_is_not_zipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(Path(tmp))
            write(Path(tmp) / "outside/leak.md", "밖 파일")
            junction_or_skip(self, root / "skills/sample-skill/sub", Path(tmp) / "outside")
            self.assertEqual(build(root), [])
            self.assertEqual(self.zip_names(root), {"sample-skill/SKILL.md", "sample-skill/references/a.md"})

    def test_zip_is_byte_identical_across_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(Path(tmp))
            build(root)
            first = (root / "dist/claude-ai/sample-skill.zip").read_bytes()
            os.utime(root / "shared/a.md", (1_000_000_000, 1_000_000_000))
            os.utime(root / "skills/sample-skill/SKILL.md", (1_100_000_000, 1_100_000_000))
            build(root)
            self.assertEqual(first, (root / "dist/claude-ai/sample-skill.zip").read_bytes())

    def test_zip_entries_have_fixed_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(Path(tmp))
            build(root)
            with zipfile.ZipFile(root / "dist/claude-ai/sample-skill.zip") as archive:
                infos = archive.infolist()
            self.assertEqual([i.filename for i in infos], sorted(i.filename for i in infos))
            for info in infos:
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.external_attr, 0o644 << 16)
                self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)


class SwapDistTest(unittest.TestCase):
    def test_swaps_and_removes_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "dist/old.txt", "old")
            write(root / "dist.tmp/new.txt", "new")
            _swap_dist(root / "dist", root / "dist.tmp")
            self.assertTrue((root / "dist/new.txt").exists())
            self.assertFalse((root / "dist/old.txt").exists())
            self.assertFalse((root / "dist.old").exists())
            self.assertFalse((root / "dist.tmp").exists())

    def test_works_without_previous_dist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "dist.tmp/new.txt", "new")
            _swap_dist(root / "dist", root / "dist.tmp")
            self.assertTrue((root / "dist/new.txt").exists())

    def test_failure_restores_previous_dist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "dist/old.txt", "old")
            with self.assertRaises(OSError):
                _swap_dist(root / "dist", root / "dist.tmp")  # staging 없음
            self.assertTrue((root / "dist/old.txt").exists())
            self.assertFalse((root / "dist.old").exists())

    def test_refuses_symlinked_dist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "elsewhere").mkdir()
            write(root / "dist.tmp/new.txt", "new")
            try:
                os.symlink(root / "elsewhere", root / "dist", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink 생성 권한 없음")
            with self.assertRaises(RuntimeError):
                _swap_dist(root / "dist", root / "dist.tmp")
            self.assertTrue((root / "elsewhere").exists())

    def test_refuses_symlinked_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "elsewhere").mkdir()
            try:
                os.symlink(root / "elsewhere", root / "dist.tmp", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink 생성 권한 없음")
            with self.assertRaises(RuntimeError):
                _swap_dist(root / "dist", root / "dist.tmp")


class OutputSafetyTest(unittest.TestCase):
    def test_checked_target_rejects_escaping_or_unnormalised_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ("../x.md", "a/../../x.md", "a/./b.md"):
                with self.assertRaises(ValueError, msg=bad):
                    _checked_target(Path(tmp), bad)
            self.assertEqual(_checked_target(Path(tmp), "a/b.md"), Path(tmp) / "a/b.md")

    def test_leftover_old_dist_is_removed_before_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "dist.old/stale.txt", "지난번 잔여물")
            write(root / "dist/old.txt", "old")
            write(root / "dist.tmp/new.txt", "new")
            _swap_dist(root / "dist", root / "dist.tmp")
            self.assertTrue((root / "dist/new.txt").exists())
            self.assertFalse((root / "dist.old").exists())

    def test_leftover_staging_is_cleared_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            write(root / "dist.tmp/claude-ai/stale.zip", "잔여물")
            self.assertEqual(build(root), [])
            self.assertFalse((root / "dist/claude-ai/stale.zip").exists())
            self.assertTrue((root / "dist/claude-ai/sample-skill.zip").exists())

    def test_missing_or_undecodable_plugin_json_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            (root / ".claude-plugin/plugin.json").unlink()
            _, errors = check(root)
            self.assertTrue(any("plugin.json" in e for e in errors), errors)
            (root / ".claude-plugin/plugin.json").write_bytes(b"\xff\xfe{")
            _, errors = check(root)
            self.assertTrue(any("plugin.json" in e for e in errors), errors)


class MainTest(unittest.TestCase):
    def call_main(self, args, root):
        out, err = io.StringIO(), io.StringIO()
        out.reconfigure = lambda **kwargs: None
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args, root=root)
        return code, out.getvalue(), err.getvalue()

    def test_check_only_reports_skills_without_building(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            code, out, _ = self.call_main(["--check"], root)
            self.assertEqual(code, 0)
            self.assertIn("완료: 스킬 1개", out)
            self.assertFalse((root / "dist").exists())

    def test_build_writes_dist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            code, _, _ = self.call_main([], root)
            self.assertEqual(code, 0)
            self.assertTrue((root / "dist/claude-ai/sample-skill.zip").exists())

    def test_validation_errors_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            write(root / "skills/Bad/SKILL.md", "---\nname: Bad\n---\n")
            code, out, _ = self.call_main([], root)
            self.assertEqual(code, 1)
            self.assertIn("오류:", out)

    def test_undecodable_skill_file_reports_korean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            (root / "skills/sample-skill/SKILL.md").write_bytes(b"---\nname: \xff\xfe\n---\n")
            code, _, err = self.call_main([], root)
            self.assertEqual(code, 1)
            self.assertIn("빌드 실패", err)

    def test_linked_dist_reports_korean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = HardeningBuildTest().make_root(Path(tmp))
            (root / "elsewhere").mkdir()
            link_or_skip(self, root / "dist", root / "elsewhere")
            code, _, err = self.call_main([], root)
            self.assertEqual(code, 1)
            self.assertIn("빌드 실패", err)
            self.assertTrue((root / "elsewhere").exists())


class PlainValueTest(unittest.TestCase):
    @staticmethod
    def front(description: str) -> str:
        return "\n".join(["---", "name: x", f"description: {description}", "---", ""])

    def test_unquoted_colon_space_is_an_error(self):
        errors = plain_value_errors(self.front("기본 양식(세부 계획: 성취기준)"))
        self.assertEqual(len(errors), 1)
        self.assertIn("작은따옴표", errors[0])

    def test_quoted_value_and_plain_value_pass(self):
        self.assertEqual(plain_value_errors(self.front("'세부 계획: 성취기준'")), [])
        self.assertEqual(plain_value_errors(self.front("콜론 없는 설명. 시각 9:30")), [])

    def test_every_skill_frontmatter_is_plain_safe(self):
        root = Path(__file__).resolve().parent.parent / "skills"
        for skill_md in sorted(root.glob("*/SKILL.md")):
            with self.subTest(skill=skill_md.parent.name):
                self.assertEqual(plain_value_errors(skill_md.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()


def test_file_count_warns_near_the_limit():
    import build
    assert build.file_count_line(120) == "파일 120개"
    assert "경고" in build.file_count_line(build.WARN_SKILL_FILES + 1)


def test_zip_compression_level_is_fixed(tmp_path):
    import build
    source = tmp_path / "a.txt"
    source.write_text("가나다 " * 5000, encoding="utf-8")
    zip_path = tmp_path / "x.zip"
    with mock.patch("zipfile.ZipFile", wraps=zipfile.ZipFile) as opened:
        build._write_zip(zip_path, "skill", {"a.txt": source})
    assert opened.call_args.kwargs["compresslevel"] == build.ZIP_COMPRESS_LEVEL == 6
    first = zip_path.read_bytes()
    build._write_zip(zip_path, "skill", {"a.txt": source})
    assert zip_path.read_bytes() == first
