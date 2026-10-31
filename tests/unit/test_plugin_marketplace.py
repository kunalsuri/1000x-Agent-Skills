"""
.claude-plugin/marketplace.json must list exactly the skills in skills/.

The marketplace is how most Claude Code users will install this catalogue
(`/plugin marketplace add kunalsuri/1000x-Agent-Skills`). A skill missing from
it is invisible to them; a path that no longer exists breaks the install for
everyone. Both directions are checked, as for the README catalogue.
"""

import json

import pytest

pytestmark = pytest.mark.unit


def load(repo_root):
    return json.loads((repo_root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


def test_marketplace_has_the_required_fields(repo_root):
    data = load(repo_root)
    assert data["name"] and data["owner"]["name"]
    for plugin in data["plugins"]:
        assert plugin["name"] and plugin["source"]


def test_marketplace_lists_every_skill_and_nothing_else(repo_root):
    listed = set()
    for plugin in load(repo_root)["plugins"]:
        for path in plugin.get("skills", []):
            assert path.startswith("./skills/"), path
            listed.add(path.removeprefix("./skills/").rstrip("/"))
    on_disk = {p.name for p in (repo_root / "skills").iterdir() if (p / "SKILL.md").exists()}
    assert listed - on_disk == set(), f"listed but missing on disk: {sorted(listed - on_disk)}"
    assert on_disk - listed == set(), f"on disk but not in marketplace.json: {sorted(on_disk - listed)}"
