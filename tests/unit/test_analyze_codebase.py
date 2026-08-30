"""Tests for the preflight-test-engineer codebase analyser."""

import json

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def analyze(load_script):
    return load_script("skills/custom/preflight-test-engineer/scripts/analyze_codebase.py")


@pytest.fixture
def python_project(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (tmp_path / "app.py").write_text(
        "class Service:\n"
        "    def handle(self):\n        return 1\n"
        "    def _private(self):\n        return 2\n\n"
        "def top_level():\n    return 3\n\n"
        "async def fetch_all():\n    return 4\n\n"
        "def _hidden():\n    return 5\n\n"
        "if __name__ == '__main__':\n    top_level()\n",
        encoding="utf-8")
    return tmp_path


class TestStackDetection:
    def test_python_project_is_detected(self, analyze, python_project):
        stack = analyze.detect_stack(python_project)
        assert stack["is_python"] is True
        assert stack["suggested_runner"] == "pytest"

    def test_node_project_is_detected(self, analyze, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "x", "scripts": {"test": "vitest"}}), encoding="utf-8")
        assert analyze.detect_stack(tmp_path)["is_javascript"] is True

    def test_typescript_is_detected_from_tsconfig(self, analyze, tmp_path):
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
        assert analyze.detect_stack(tmp_path)["is_typescript"] is True

    def test_existing_tests_directory_is_noticed(self, analyze, python_project):
        (python_project / "tests").mkdir()
        assert analyze.detect_stack(python_project)["has_tests_dir"] is True

    def test_empty_directory_detects_no_stack(self, analyze, tmp_path):
        stack = analyze.detect_stack(tmp_path)
        assert stack["is_python"] is False and stack["is_javascript"] is False


class TestPythonFileAnalysis:
    def test_public_functions_are_collected(self, analyze, python_project):
        result = analyze.analyze_python_file(python_project / "app.py")
        assert "top_level" in [f["name"] for f in result["functions"]]

    def test_private_functions_are_skipped(self, analyze, python_project):
        result = analyze.analyze_python_file(python_project / "app.py")
        assert "_hidden" not in [f["name"] for f in result["functions"]]

    def test_classes_and_their_public_methods_are_collected(self, analyze, python_project):
        result = analyze.analyze_python_file(python_project / "app.py")
        service = next(c for c in result["classes"] if c["name"] == "Service")
        assert service["methods"] == ["handle"]

    def test_async_functions_are_tracked_separately(self, analyze, python_project):
        result = analyze.analyze_python_file(python_project / "app.py")
        assert "fetch_all" in [f["name"] for f in result["async_functions"]]

    def test_main_guard_is_detected(self, analyze, python_project):
        assert analyze.analyze_python_file(python_project / "app.py")["has_main"] is True

    def test_line_numbers_are_recorded(self, analyze, python_project):
        result = analyze.analyze_python_file(python_project / "app.py")
        assert all(f["line"] > 0 for f in result["functions"])

    def test_flask_style_endpoints_are_classified_as_endpoints(self, analyze, tmp_path):
        path = tmp_path / "api.py"
        path.write_text(
            "app = object()\n\n"
            "@app.route('/x')\ndef handler():\n    return 'x'\n", encoding="utf-8")
        result = analyze.analyze_python_file(path)
        assert [e["name"] for e in result["endpoints"]] == ["handler"]

    def test_unparseable_file_returns_an_empty_result_rather_than_raising(self, analyze, tmp_path):
        path = tmp_path / "broken.py"
        path.write_text("def oops(:\n", encoding="utf-8")
        result = analyze.analyze_python_file(path)
        assert result["functions"] == [] and result["classes"] == []


class TestExistingTestDiscovery:
    def test_test_files_are_found(self, analyze, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
        assert [p.name for p in analyze.find_existing_tests(tmp_path)] == ["test_a.py"]

    def test_no_tests_yields_an_empty_list(self, analyze, tmp_path):
        (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
        assert analyze.find_existing_tests(tmp_path) == []


class TestFullAnalysis:
    def test_analysis_reports_stack_sources_and_metrics(self, analyze, python_project):
        result = analyze.run_analysis(python_project)
        assert result["stack"]["is_python"] is True
        assert {"source_analysis", "metrics", "existing_tests",
                "recommendations"} <= set(result)

    def test_analysis_counts_untested_modules(self, analyze, python_project):
        """The gap the skill exists to close."""
        metrics = analyze.run_analysis(python_project)["metrics"]
        assert metrics["total_python_modules"] >= 1
        assert metrics["tested_python_modules"] == 0
        assert metrics["python_test_coverage_ratio"] == "0/1"

    def test_adding_a_test_improves_the_coverage_ratio(self, analyze, python_project):
        before = analyze.run_analysis(python_project)["metrics"]["python_test_coverage_ratio"]
        (python_project / "tests").mkdir()
        (python_project / "tests" / "test_app.py").write_text(
            "def test_top_level(): pass\n", encoding="utf-8")
        after = analyze.run_analysis(python_project)["metrics"]["python_test_coverage_ratio"]
        assert before != after
