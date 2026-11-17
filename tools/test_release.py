"""배포 설정 시험: 마켓플레이스 파일, plugin.json, 릴리스 자동화가 서로 맞는지 본다."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
NAME_RULE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class MarketplaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.market = load(MARKETPLACE)
        self.plugin = load(PLUGIN)

    def test_required_fields_and_name_rules(self) -> None:
        self.assertTrue(NAME_RULE.match(self.market["name"]))
        self.assertTrue(self.market["owner"]["name"])
        self.assertTrue(self.market.get("description"))
        self.assertEqual(len(self.market["plugins"]), 1)

    def test_entry_name_matches_plugin_manifest(self) -> None:
        # 이름이 다르면 설치할 때 "not found in marketplace"가 난다
        self.assertEqual(self.market["plugins"][0]["name"], self.plugin["name"])

    def test_source_points_at_the_built_plugin_branch(self) -> None:
        source = self.market["plugins"][0]["source"]
        self.assertEqual(source["source"], "github")
        self.assertEqual(source["ref"], "plugin")
        self.assertTrue(self.plugin["repository"].endswith("/" + source["repo"]))

    def test_entry_does_not_override_plugin_version(self) -> None:
        # 버전은 plugin.json 한 곳에만 둔다 (둘 다 있으면 plugin.json이 이기고 검사가 경고한다)
        self.assertNotIn("version", self.market["plugins"][0])
        self.assertRegex(self.plugin["version"], r"^\d+\.\d+\.\d+$")


class ReleaseWorkflowTest(unittest.TestCase):
    def test_release_checks_version_and_publishes_both_outputs(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        self.assertIn("plugin.json", text)
        self.assertIn("python -m pytest", text)
        self.assertIn("dist/claude-ai/*.zip", text)
        self.assertIn("push origin plugin", text)
        self.assertNotRegex(text, r"push\s+(-f|--force)")   # plugin 가지 기록을 지우지 않는다


if __name__ == "__main__":
    unittest.main()
