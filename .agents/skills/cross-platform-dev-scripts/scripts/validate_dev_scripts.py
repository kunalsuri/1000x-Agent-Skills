#!/usr/bin/env python3
"""
Validator CLI for cross-platform dev scripts.
Verifies script presence, syntax, safety invariants, and parity between win and linux scripts.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any


def check_scripts(target_dir: Path) -> Dict[str, Any]:
    """Inspects and validates dev scripts in target_dir."""
    target_dir = target_dir.resolve()
    errors: List[str] = []
    warnings: List[str] = []
    checks_passed: List[str] = []

    linux_dir = target_dir / "scripts" / "linux"
    win_dir = target_dir / "scripts" / "win"

    expected_files = {
        "linux_setup": linux_dir / "dev-setup.sh",
        "linux_test": linux_dir / "dev-test.sh",
        "win_setup": win_dir / "dev-setup.ps1",
        "win_test": win_dir / "dev-test.ps1"
    }

    # 1. Existence check
    for label, path in expected_files.items():
        if not path.is_file():
            errors.append(f"Missing expected script: {path.relative_to(target_dir)}")
        else:
            checks_passed.append(f"Found {label}: {path.relative_to(target_dir)}")

    if errors:
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
            "passed": checks_passed
        }

    # Helper reader
    def read_text(p: Path) -> str:
        return p.read_text(encoding="utf-8", errors="replace")

    sh_setup_text = read_text(expected_files["linux_setup"])
    sh_test_text = read_text(expected_files["linux_test"])
    ps1_setup_text = read_text(expected_files["win_setup"])
    ps1_test_text = read_text(expected_files["win_test"])

    # 2. Bash shebang and error handling
    for name, text in [("dev-setup.sh", sh_setup_text), ("dev-test.sh", sh_test_text)]:
        first_line = text.splitlines()[0] if text.splitlines() else ""
        if first_line != "#!/usr/bin/env bash":
            errors.append(f"{name} does not start with '#!/usr/bin/env bash'")
        else:
            checks_passed.append(f"{name} has valid bash shebang")

        if "set -Eeuo pipefail" not in text:
            errors.append(f"{name} missing strict mode 'set -Eeuo pipefail'")
        else:
            checks_passed.append(f"{name} enables strict error handling")

    # 3. Quoting safety for rm commands
    for name, text in [("dev-setup.sh", sh_setup_text), ("dev-test.sh", sh_test_text)]:
        for match in re.finditer(r"rm\s+-r[^\s]*\s+(?:--\s+)?(\S+)", text):
            arg = match.group(1)
            if not (arg.startswith('"') or arg.startswith("'") or arg.startswith('"$')):
                errors.append(f"{name} unquoted rm target: {match.group(0)!r}")
            else:
                checks_passed.append(f"{name} rm command properly quoted")

    # 4. Safety Invariants: No sudo, no curl|sh, writes confined to venv
    for name, text in [("dev-setup.sh", sh_setup_text), ("dev-test.sh", sh_test_text)]:
        if re.search(r"^\s*sudo\b", text, re.MULTILINE):
            errors.append(f"{name} contains 'sudo' invocation (violates least privilege)")
        else:
            checks_passed.append(f"{name} free from sudo invocations")

        if re.search(r"curl[^\n|]*\|\s*(ba|z|k|da)?sh\b", text) or re.search(r"wget[^\n|]*\|\s*(ba|z|k|da)?sh\b", text):
            errors.append(f"{name} pipes remote downloads into a shell (security violation)")
        else:
            checks_passed.append(f"{name} free from pipe-to-shell patterns")

    for match in re.finditer(r'rm -rf -- "([^"]+)"', sh_setup_text):
        target = match.group(1)
        if "VENV_DIR" not in target and "venv" not in target.lower():
            errors.append(f"dev-setup.sh removes path outside virtualenv: {target}")
        else:
            checks_passed.append(f"dev-setup.sh cleanup confined to venv: {target}")

    # 5. PowerShell hygiene
    for name, text in [("dev-setup.ps1", ps1_setup_text), ("dev-test.ps1", ps1_test_text)]:
        if "$ErrorActionPreference = \"Stop\"" not in text and "$ErrorActionPreference=\"Stop\"" not in text:
            errors.append(f"{name} missing '$ErrorActionPreference = \"Stop\"'")
        else:
            checks_passed.append(f"{name} sets ErrorActionPreference = Stop")

        # Functional Join-Path arguments should not use backslashes
        for match in re.finditer(r"Join-Path\s+\$\w+\s+\"([^\"]*)\"", text):
            if "\\" in match.group(1):
                errors.append(f"{name} Join-Path argument {match.group(1)!r} uses backslash")
            else:
                checks_passed.append(f"{name} Join-Path uses forward slashes")

        # Check self-aliasing parameters
        for alias_match, param_match in re.findall(r'\[Alias\("(\w+)"\)\]\[\w+\]\$(\w+)', text):
            if alias_match.lower() == param_match.lower():
                errors.append(f"{name} parameter ${param_match} aliases its own name")
            else:
                checks_passed.append(f"{name} parameter alias is valid")

    # 6. Syntax validation via tools if present
    if shutil.which("bash"):
        for path in [expected_files["linux_setup"], expected_files["linux_test"]]:
            rel_posix = path.relative_to(target_dir).as_posix()
            res = subprocess.run(["bash", "-n", rel_posix], cwd=str(target_dir), capture_output=True, text=True)
            if res.returncode != 0:
                errors.append(f"bash -n failed for {path.name}: {res.stderr.strip()}")
            else:
                checks_passed.append(f"bash -n syntax check clean for {path.name}")
    else:
        warnings.append("'bash' not on PATH; skipped static bash -n syntax checks")

    if shutil.which("pwsh"):
        for path in [expected_files["win_setup"], expected_files["win_test"]]:
            rel_posix = path.relative_to(target_dir).as_posix()
            probe = (
                "$err = $null; "
                f"$null = [System.Management.Automation.Language.Parser]::ParseFile("
                f"'{rel_posix}', [ref]$null, [ref]$err); "
                "if ($err) { $err | ForEach-Object { Write-Error $_ }; exit 1 } else { exit 0 }"
            )
            res = subprocess.run(["pwsh", "-NoProfile", "-Command", probe], cwd=str(target_dir), capture_output=True, text=True)
            if res.returncode != 0:
                errors.append(f"PowerShell parse error in {path.name}: {res.stderr.strip()}")
            else:
                checks_passed.append(f"PowerShell parse check clean for {path.name}")
    else:
        warnings.append("'pwsh' not on PATH; skipped PowerShell AST parse check")

    # 7. Step parity check between dev-test.sh and dev-test.ps1
    # Check that both have auto-bootstrap check and test execution
    if "dev-setup.sh" not in sh_test_text or "dev-setup.ps1" not in ps1_test_text:
        errors.append("Both dev-test scripts must support auto-bootstrapping dev-setup")
    else:
        checks_passed.append("Both dev-test scripts support auto-bootstrapping")

    if "-k" not in sh_test_text or "-k" not in ps1_test_text.lower():
        warnings.append("One or both test runners may lack -k/-K filter flag support")
    else:
        checks_passed.append("Both test runners support test filtering")

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "passed": checks_passed
    }


def main():
    parser = argparse.ArgumentParser(description="Validate cross-platform dev scripts.")
    parser.add_argument("--target", "-t", default=".", help="Target repository directory (default: current dir)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    report = check_scripts(Path(args.target))

    if args.json:
        import json
        print(json.dumps(report, indent=2))
    else:
        print(f"Validation Status: [{report['status']}]")
        if report["errors"]:
            print("\nErrors:")
            for err in report["errors"]:
                print(f"  ✗ {err}")
        if report["warnings"]:
            print("\nWarnings:")
            for warn in report["warnings"]:
                print(f"  ! {warn}")
        if report["passed"]:
            print("\nPassed Checks:")
            for p in report["passed"][:10]:
                print(f"  ✓ {p}")
            if len(report["passed"]) > 10:
                print(f"  ... and {len(report['passed']) - 10} more checks passed.")

    sys.exit(1 if report["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
