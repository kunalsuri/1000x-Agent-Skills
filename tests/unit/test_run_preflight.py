"""Tests for the preflight-test-engineer pipeline runner."""

import sys

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def preflight(load_script):
    return load_script("skills/custom/preflight-test-engineer/scripts/run_preflight.py")


class TestSyntaxStage:
    def test_clean_sources_pass(self, preflight, tmp_path):
        (tmp_path / "ok.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        ok, errors = preflight.check_python_syntax(tmp_path)
        assert ok is True and errors == []

    def test_a_syntax_error_is_reported_with_its_file(self, preflight, tmp_path):
        (tmp_path / "broken.py").write_text("def f(:\n", encoding="utf-8")
        ok, errors = preflight.check_python_syntax(tmp_path)
        assert ok is False and "broken.py" in errors[0]

    def test_one_bad_file_among_good_ones_still_fails(self, preflight, tmp_path):
        (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "bad.py").write_text("x = (\n", encoding="utf-8")
        ok, errors = preflight.check_python_syntax(tmp_path)
        assert ok is False and len(errors) == 1

    def test_virtualenvs_and_caches_are_skipped(self, preflight, tmp_path):
        vendored = tmp_path / ".venv" / "lib"
        vendored.mkdir(parents=True)
        (vendored / "bad.py").write_text("def f(:\n", encoding="utf-8")
        ok, _ = preflight.check_python_syntax(tmp_path)
        assert ok is True

    def test_a_directory_with_no_python_passes(self, preflight, tmp_path):
        (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
        assert preflight.check_python_syntax(tmp_path) == (True, [])


class TestCommandCapture:
    def test_stdout_and_exit_code_are_captured(self, preflight, tmp_path):
        code, out, _ = preflight.run_command_capture(
            [sys.executable, "-c", "print('hello')"], tmp_path)
        assert code == 0 and "hello" in out

    def test_a_failing_command_reports_its_exit_code(self, preflight, tmp_path):
        code, _, _ = preflight.run_command_capture(
            [sys.executable, "-c", "raise SystemExit(3)"], tmp_path)
        assert code == 3

    def test_stderr_is_captured_separately(self, preflight, tmp_path):
        _, _, err = preflight.run_command_capture(
            [sys.executable, "-c", "import sys; sys.stderr.write('boom')"], tmp_path)
        assert "boom" in err

    def test_a_missing_executable_returns_127_rather_than_raising(self, preflight, tmp_path):
        code, _, err = preflight.run_command_capture(["definitely-not-a-real-binary"], tmp_path)
        assert code == 127 and "not found" in err

    def test_a_hanging_command_is_killed_by_the_timeout(self, preflight, tmp_path):
        """Without this, a wedged test runner hangs the whole pipeline."""
        code, _, err = preflight.run_command_capture(
            [sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, timeout_sec=1)
        assert code == 124 and "timed out" in err
