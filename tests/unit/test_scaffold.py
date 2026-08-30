"""Tests for the multi-agent-docs scaffolder."""

import json

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def scaffold(load_script):
    return load_script("skills/custom/multi-agent-docs/scripts/scaffold.py")


class TestManifestDetection:
    def test_node_manifest_yields_project_type_and_commands(self, scaffold, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps(
            {"scripts": {"build": "tsc", "test": "vitest", "lint": "eslint ."}}),
            encoding="utf-8")
        facts = scaffold.detect_manifests(tmp_path)
        assert "Node.js" in facts["project_types"]
        assert "npm run build" in facts["commands"]["build"]
        assert "npm test" in facts["commands"]["test"]

    def test_lockfile_selects_the_package_manager(self, scaffold, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"build": "tsc"}}), encoding="utf-8")
        (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 6\n", encoding="utf-8")
        assert "pnpm run build" in scaffold.detect_manifests(tmp_path)["commands"]["build"]

    def test_yarn_lockfile_is_recognised(self, scaffold, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8")
        (tmp_path / "yarn.lock").write_text("# yarn\n", encoding="utf-8")
        assert "yarn test" in scaffold.detect_manifests(tmp_path)["commands"]["test"]

    def test_an_empty_directory_detects_nothing(self, scaffold, tmp_path):
        facts = scaffold.detect_manifests(tmp_path)
        assert facts["project_types"] == []

    def test_malformed_package_json_does_not_raise(self, scaffold, tmp_path):
        (tmp_path / "package.json").write_text("{ broken", encoding="utf-8")
        assert "Node.js" in scaffold.detect_manifests(tmp_path)["project_types"]

    def test_python_project_is_detected_from_requirements(self, scaffold, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        (tmp_path / "tests").mkdir()
        facts = scaffold.detect_manifests(tmp_path)
        assert "Python" in facts["project_types"]
        assert "pytest" in facts["commands"]["test"]

    def test_python_without_a_tests_directory_falls_back_to_unittest(self, scaffold, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        assert "python -m unittest discover" in scaffold.detect_manifests(
            tmp_path)["commands"]["test"]

    def test_multiple_ecosystems_are_all_reported(self, scaffold, tmp_path):
        (tmp_path / "requirements.txt").write_text("x\n", encoding="utf-8")
        (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
        types = scaffold.detect_manifests(tmp_path)["project_types"]
        assert "Python" in types and "Go" in types


class TestDocumentGeneration:
    @pytest.fixture
    def facts(self, scaffold, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "vitest"}}), encoding="utf-8")
        return scaffold.detect_manifests(tmp_path)

    def test_claude_md_has_a_heading_and_commands(self, scaffold, facts):
        content = scaffold.generate_claude_md(facts)
        assert "# Claude Code Project Guidelines" in content
        assert "npm test" in content

    def test_agents_md_has_a_heading_and_commands(self, scaffold, facts):
        content = scaffold.generate_agents_md(facts)
        assert "# Project Directives & Conventions" in content
        assert "npm test" in content

    def test_each_document_points_at_the_other(self, scaffold, facts):
        """The cross-reference is what reminds an editor to update both."""
        assert "AGENTS.md" in scaffold.generate_claude_md(facts)
        assert "CLAUDE.md" in scaffold.generate_agents_md(facts)

    def test_both_documents_describe_the_same_commands(self, scaffold, facts):
        """The drift this skill exists to prevent, checked at the source."""
        claude = scaffold.generate_claude_md(facts)
        agents = scaffold.generate_agents_md(facts)
        for command in facts["commands"]["test"]:
            assert command in claude and command in agents

    def test_generation_works_with_no_detected_facts(self, scaffold, tmp_path):
        facts = scaffold.detect_manifests(tmp_path)
        assert scaffold.generate_claude_md(facts)
        assert scaffold.generate_agents_md(facts)
