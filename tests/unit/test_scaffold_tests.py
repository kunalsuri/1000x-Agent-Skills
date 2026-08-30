"""
Tests for the preflight-test-engineer test scaffolder.

The central guarantee here is that a scaffolded suite is RED until someone
writes it. This repository shipped 93 `assert True` bodies produced by this
generator; the suite reported green over zero verification for as long as
they existed. These tests make that state unreachable.
"""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def scaffolder(load_script):
    return load_script("skills/custom/preflight-test-engineer/scripts/scaffold_tests.py")


@pytest.fixture
def project(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "service.py").write_text(
        "class Widget:\n    def render(self):\n        return 1\n\n"
        "def helper():\n    return 2\n",
        encoding="utf-8")
    return tmp_path


class TestGeneratedPythonTestsAreHonest:
    def test_generated_tests_contain_no_empty_assertions(self, scaffolder):
        content = scaffolder.generate_python_unit_test(
            "service", ["helper"], [{"name": "Widget", "methods": ["render"]}])
        assert "assert True" not in content

    def test_generated_tests_fail_until_written(self, scaffolder, tmp_path):
        """Run the generated file for real: every test must fail, none pass."""
        content = scaffolder.generate_python_unit_test("service", ["helper"], [])
        path = tmp_path / "test_generated.py"
        path.write_text(content, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(path), "-p", "no:cacheprovider", "-q"],
            capture_output=True, text=True, cwd=tmp_path)
        assert result.returncode != 0, "a scaffolded suite must not report green"
        assert "Unimplemented" in result.stdout

    def test_generated_tests_name_what_is_missing(self, scaffolder):
        content = scaffolder.generate_python_unit_test("service", ["helper"], [])
        assert "Unimplemented: helper success case" in content

    def test_a_test_is_generated_per_public_function(self, scaffolder):
        content = scaffolder.generate_python_unit_test("m", ["alpha", "beta"], [])
        assert "def test_alpha_success" in content and "def test_beta_success" in content

    def test_classes_get_a_test_class_with_method_coverage(self, scaffolder):
        content = scaffolder.generate_python_unit_test(
            "m", [], [{"name": "Widget", "methods": ["render", "resize"]}])
        assert "class TestWidget:" in content
        assert "def test_render_happy_path" in content
        assert "def test_resize_edge_cases" in content

    def test_empty_module_still_produces_a_failing_placeholder(self, scaffolder):
        content = scaffolder.generate_python_unit_test("empty", [], [])
        assert "pytest.fail" in content and "assert True" not in content

    def test_generated_python_is_syntactically_valid(self, scaffolder):
        import ast
        ast.parse(scaffolder.generate_python_unit_test(
            "m", ["fn"], [{"name": "C", "methods": ["do"]}]))


class TestGeneratedTypeScriptTests:
    def test_no_tautological_expectations(self, scaffolder):
        content = scaffolder.generate_ts_unit_test("service", ["helper"])
        assert "expect(true).toBe(true)" not in content

    def test_unwritten_tests_throw(self, scaffolder):
        content = scaffolder.generate_ts_unit_test("service", ["helper"])
        assert "throw new Error('Unimplemented" in content

    def test_describe_block_per_function(self, scaffolder):
        content = scaffolder.generate_ts_unit_test("m", ["alpha"])
        assert "describe('alpha()'" in content

    def test_react_component_tests_also_fail_until_written(self, scaffolder):
        content = scaffolder.generate_react_component_test("Sidebar")
        assert "expect(true).toBe(true)" not in content
        assert "Unimplemented" in content


class TestScaffolding:
    def test_dry_run_writes_nothing(self, scaffolder, project):
        result = scaffolder.scaffold(project, dry_run=True)
        assert result["dry_run"] is True
        assert not (project / "tests" / "unit").exists() or \
            not any((project / "tests" / "unit").iterdir())

    def test_scaffold_creates_the_expected_tree(self, scaffolder, project):
        scaffolder.scaffold(project)
        for sub in ("unit", "integration", "fixtures", "smoke"):
            assert (project / "tests" / sub).is_dir()

    def test_scaffold_reports_what_it_created(self, scaffolder, project):
        result = scaffolder.scaffold(project)
        assert result["created_files"]

    def test_rerunning_without_force_skips_existing_files(self, scaffolder, project):
        scaffolder.scaffold(project)
        second = scaffolder.scaffold(project)
        assert second["created_files"] == [] or second["skipped_files"]

    def test_scaffolded_suite_contains_no_empty_assertions(self, scaffolder, project):
        """End to end: nothing this tool writes to disk may be a no-op test."""
        scaffolder.scaffold(project)
        for path in (project / "tests").rglob("test_*.py"):
            assert "assert True" not in path.read_text(encoding="utf-8"), path
