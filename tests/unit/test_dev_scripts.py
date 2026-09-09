"""
Tests for scripts/linux/dev-{setup,test}.sh and scripts/win/dev-{setup,test}.ps1.

These wrap the same CI sequence for a developer's own machine, so their
biggest failure mode is invisible drift: someone fixes a step, an argument,
or an ordering in the bash script and forgets the PowerShell mirror (or vice
versa) -- exactly the CLAUDE.md/AGENTS.md drift this repository already
guards against elsewhere with validate_sync.py. These tests hold the same
line for the dev scripts: both variants must run the identical five checks,
in the identical order, against the identical targets.

Executing the scripts themselves (they create a venv, install packages, run
pytest recursively) is deliberately out of scope for the suite that scripts
like these are meant to run -- that would be slow, environment-dependent,
and self-referential. What is tested is what regresses silently: syntax,
required safety properties, and cross-platform parity of the step list.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

LINUX_DIR = Path("scripts/linux")
WIN_DIR = Path("scripts/win")


def read(repo_root: Path, rel: str) -> str:
    return (repo_root / rel).read_text(encoding="utf-8")


class TestFilesExist:
    @pytest.mark.parametrize("name", ["dev-setup.sh", "dev-test.sh"])
    def test_linux_script_exists_and_is_executable(self, repo_root, name):
        path = repo_root / LINUX_DIR / name
        assert path.is_file(), path
        if sys.platform != "win32":
            assert path.stat().st_mode & 0o111, f"{path} is not executable (chmod +x)"

    @pytest.mark.parametrize("name", ["dev-setup.ps1", "dev-test.ps1"])
    def test_windows_script_exists(self, repo_root, name):
        assert (repo_root / WIN_DIR / name).is_file()


class TestBashSyntax:
    @pytest.mark.parametrize("name", ["dev-setup.sh", "dev-test.sh"])
    def test_script_has_a_bash_shebang(self, repo_root, name):
        first_line = read(repo_root, str(LINUX_DIR / name)).splitlines()[0]
        assert first_line == "#!/usr/bin/env bash"

    @pytest.mark.parametrize("name", ["dev-setup.sh", "dev-test.sh"])
    def test_script_passes_bash_syntax_check(self, repo_root, name):
        path = repo_root / LINUX_DIR / name
        rel = (LINUX_DIR / name).as_posix()
        result = subprocess.run(["bash", "-n", rel], cwd=str(repo_root), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("name", ["dev-setup.sh", "dev-test.sh"])
    def test_script_enables_strict_error_handling(self, repo_root, name):
        """set -Eeuo pipefail is what makes a mid-script failure fail loudly
        instead of continuing on with a corrupted state."""
        assert "set -Eeuo pipefail" in read(repo_root, str(LINUX_DIR / name))

    @pytest.mark.parametrize("name", ["dev-setup.sh", "dev-test.sh"])
    def test_no_variable_is_left_unquoted_in_an_rm_command(self, repo_root, name):
        """The one shell mistake that turns a bug into data loss."""
        text = read(repo_root, str(LINUX_DIR / name))
        for match in re.finditer(r"rm\s+-r[^\s]*\s+(?:--\s+)?(\S+)", text):
            arg = match.group(1)
            assert arg.startswith('"'), (
                f"unquoted rm target in {name}: {match.group(0)!r}"
            )


class TestPowerShellSyntax:
    pwsh_available = shutil.which("pwsh") is not None
    skip_reason = "pwsh not installed on this machine"

    @pytest.mark.skipif(not pwsh_available, reason=skip_reason)
    @pytest.mark.parametrize("name", ["dev-setup.ps1", "dev-test.ps1"])
    def test_script_parses_cleanly(self, repo_root, name):
        path = repo_root / WIN_DIR / name
        probe = (
            "$err = $null; "
            f"$null = [System.Management.Automation.Language.Parser]::ParseFile("
            f"'{path}', [ref]$null, [ref]$err); "
            "if ($err) { $err | ForEach-Object { Write-Error $_ }; exit 1 } else { exit 0 }"
        )
        result = subprocess.run(["pwsh", "-NoProfile", "-Command", probe],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("name", ["dev-setup.ps1", "dev-test.ps1"])
    def test_no_functional_join_path_uses_a_backslash(self, repo_root, name):
        """
        Backslash literals inside Join-Path/string interpolation are a
        recurring source of bugs on this codebase's one Linux-testable
        surface for these scripts; forward slashes work identically on
        Windows and let the logic be exercised here. Comments and help text
        may still show `scripts\\win\\...` for a Windows reader -- only
        Join-Path calls are checked.
        """
        text = read(repo_root, str(WIN_DIR / name))
        for match in re.finditer(r"Join-Path\s+\$\w+\s+\"([^\"]*)\"", text):
            assert "\\" not in match.group(1), (
                f"{name}: Join-Path argument {match.group(1)!r} uses a backslash"
            )

    @pytest.mark.parametrize("name", ["dev-setup.ps1", "dev-test.ps1"])
    def test_no_switch_or_string_parameter_aliases_its_own_name(self, repo_root, name):
        """
        The exact bug this test would have caught: [Alias("k")] on a
        parameter literally named $K aliases itself, and PowerShell refuses
        to start at all -- MetadataError, not a runtime failure, so nothing
        short of actually invoking the script surfaces it.
        """
        text = read(repo_root, str(WIN_DIR / name))
        for alias_match, param_match in re.findall(
            r'\[Alias\("(\w+)"\)\]\[\w+\]\$(\w+)', text
        ):
            assert alias_match.lower() != param_match.lower(), (
                f"{name}: parameter ${param_match} aliases its own name"
            )


class TestCrossPlatformParity:
    """
    The property that matters most: both variants run the same checks, in
    the same order, against the same targets. Extracted textually rather
    than by executing either script, so this stays fast and has no
    environment prerequisites (no venv, no network, no pwsh).
    """

    @staticmethod
    def bash_steps(repo_root: Path) -> list[tuple[str, str]]:
        text = read(repo_root, str(LINUX_DIR / "dev-test.sh"))
        # Matches: run_step "Name" "$VENV_PY" target.py [args...]
        pattern = re.compile(
            r'run_step\s+"([^"]+)"\s+\\?\s*\n?\s*"\$VENV_PY"\s+([^\n]+)', re.MULTILINE
        )
        return [(name, args.strip()) for name, args in pattern.findall(text)
                if "$PYTEST_K" not in args]

    @staticmethod
    def powershell_steps(repo_root: Path) -> list[tuple[str, str]]:
        text = read(repo_root, str(WIN_DIR / "dev-test.ps1"))
        pattern = re.compile(
            r'Invoke-Step\s+-Name\s+"([^"]+)"\s+-Exe\s+\$VenvPy\s+`?\s*\n?\s*'
            r'-StepArgs\s+@\(([^)]*)\)',
            re.MULTILINE,
        )
        results = []
        for name, args_block in pattern.findall(text):
            if "$K" in args_block:
                continue
            args = re.findall(r'"([^"]*)"', args_block)
            results.append((name, " ".join(args)))
        return results

    def test_both_variants_define_the_same_number_of_steps(self, repo_root):
        bash = self.bash_steps(repo_root)
        ps = self.powershell_steps(repo_root)
        assert len(bash) == len(ps) == 5, (
            f"expected 5 non-filter steps in each script, "
            f"found {len(bash)} in dev-test.sh and {len(ps)} in dev-test.ps1"
        )

    def test_both_variants_use_the_same_step_names_in_the_same_order(self, repo_root):
        bash_names = [name for name, _ in self.bash_steps(repo_root)]
        ps_names = [name for name, _ in self.powershell_steps(repo_root)]
        assert bash_names == ps_names

    def test_both_variants_target_the_same_scripts_in_the_same_order(self, repo_root):
        """
        Compares the .py file each step invokes (ignoring platform-specific
        flag spelling like -k vs -k, which match anyway, and cosmetic
        spacing) so a step that silently starts auditing the wrong file in
        one variant is caught.
        """
        def target_scripts(steps):
            targets = []
            for _, args in steps:
                match = re.search(r"([\w./-]+\.py)", args)
                targets.append(match.group(1) if match else None)
            return targets

        bash_targets = target_scripts(self.bash_steps(repo_root))
        ps_targets = target_scripts(self.powershell_steps(repo_root))
        assert bash_targets == ps_targets

    def test_both_variants_enforce_the_same_coverage_floor(self, repo_root):
        bash_text = read(repo_root, str(LINUX_DIR / "dev-test.sh"))
        ps_text = read(repo_root, str(WIN_DIR / "dev-test.ps1"))
        bash_floor = re.search(r"--cov-fail-under=(\d+)", bash_text)
        ps_floor = re.search(r"--cov-fail-under=(\d+)", ps_text)
        assert bash_floor and ps_floor
        assert bash_floor.group(1) == ps_floor.group(1)

    def test_dev_test_step_list_matches_ci_workflow(self, repo_root):
        """
        The whole point of these scripts is that a clean local report
        predicts a clean CI run. If ci.yml's validate job gains or loses a
        step, this is what would otherwise let dev-test.sh quietly stop
        matching it.
        """
        ci_text = read(repo_root, ".github/workflows/ci.yml")
        bash_targets = {
            re.search(r"([\w./-]+\.py)", args).group(1)
            for _, args in self.bash_steps(repo_root)
            if re.search(r"([\w./-]+\.py)", args)
        }
        for target in bash_targets:
            assert target in ci_text, f"{target} is checked by dev-test.sh but not by ci.yml"


class TestReadOnlyPrinciple:
    """
    dev-setup.sh explicitly documents that it writes only inside .venv/.
    Since nothing enforces that by construction, keep the documented
    invariant checked against the actual write targets in the script.
    """

    def test_setup_script_never_removes_anything_outside_venv(self, repo_root):
        text = read(repo_root, str(LINUX_DIR / "dev-setup.sh"))
        for match in re.finditer(r'rm -rf -- "([^"]+)"', text):
            assert "VENV_DIR" in match.group(1), (
                f"dev-setup.sh removes a path not derived from VENV_DIR: {match.group(1)}"
            )

    def test_setup_script_never_uses_sudo(self, repo_root):
        """
        The script mentions 'sudo' twice as text a human reads -- a doc
        comment describing this guarantee, and an error hint suggesting the
        user run one themselves (`apt install python3-venv`). Neither is an
        invocation, so this checks for 'sudo' actually starting a command,
        not the substring anywhere in the file.
        """
        text = read(repo_root, str(LINUX_DIR / "dev-setup.sh"))
        assert not re.search(r"^\s*sudo\b", text, re.MULTILINE)

    def test_setup_script_never_pipes_a_download_into_a_shell(self, repo_root):
        text = read(repo_root, str(LINUX_DIR / "dev-setup.sh"))
        assert not re.search(r"curl[^\n|]*\|\s*(ba|z|k|da)?sh\b", text)
        assert not re.search(r"wget[^\n|]*\|\s*(ba|z|k|da)?sh\b", text)
