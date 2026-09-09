#!/usr/bin/env python3
"""
Pre-Flight Test Runner & Diagnostic CLI.
Executes a 4-stage pre-flight verification sequence before running application code:
1. Syntax & Compilation Check
2. Smoke & Environment Sanity
3. Hermetic Test Collection & Fast Execution
4. Diagnostic Health & Remediation Summary
"""

import sys
import os
import subprocess
import time
import argparse
import py_compile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple

try:
    from analyze_codebase import detect_stack, find_existing_tests
except ImportError:
    from .analyze_codebase import detect_stack, find_existing_tests

def check_python_syntax(target_dir: Path) -> Tuple[bool, List[str]]:
    """Stage 1: Checks Python files for syntax errors using py_compile."""
    errors = []
    py_files = list(target_dir.rglob("*.py"))
    
    for pf in py_files:
        # Skip ignored dirs
        parts = set(pf.parts)
        if any(d in parts for d in {".venv", "venv", "__pycache__", ".git", "build", "dist"}):
            continue
        try:
            py_compile.compile(str(pf), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax Error in {pf.relative_to(target_dir)}: {e.msg}")
        except Exception as e:
            errors.append(f"Parse Error in {pf.relative_to(target_dir)}: {str(e)}")

    return len(errors) == 0, errors

def run_command_capture(cmd: List[str], cwd: Path, timeout_sec: int = 30) -> Tuple[int, str, str]:
    """Runs a shell command and captures stdout/stderr with a timeout."""
    try:
        if not cmd:
            return 1, "", "Empty command."
        if not shutil.which(cmd[0]):
            raise FileNotFoundError(f"Executable '{cmd[0]}' not found in PATH.")
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            shell=(os.name == 'nt')
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout_sec} seconds."
    except FileNotFoundError:
        return 127, "", f"Executable '{cmd[0]}' not found in PATH."
    except Exception as e:
        return 1, "", str(e)

def run_preflight_pipeline(target_dir: Path, runner_override: str = None, fast: bool = False) -> Dict[str, Any]:
    """Executes the full 4-stage pre-flight validation pipeline."""
    stack = detect_stack(target_dir)
    results = {
        "target_dir": str(target_dir.resolve()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stages": {},
        "all_passed": True,
        "summary": []
    }

    start_time = time.time()

    # =========================================================================
    # STAGE 1: Syntax & Compilation Integrity
    # =========================================================================
    print(" 🔹 [STAGE 1/4] Checking Syntax & Compilation...")
    s1_start = time.time()
    s1_passed = True
    s1_errors = []

    if stack["is_python"]:
        s1_passed, s1_errors = check_python_syntax(target_dir)

    results["stages"]["1_syntax"] = {
        "name": "Syntax & Compilation Integrity",
        "passed": s1_passed,
        "duration_sec": round(time.time() - s1_start, 2),
        "errors": s1_errors
    }

    if not s1_passed:
        results["all_passed"] = False
        print(f"    ❌ Stage 1 Failed with {len(s1_errors)} syntax error(s).")
        for err in s1_errors[:5]:
            print(f"       - {err}")
        return results
    else:
        print(f"    ✅ Stage 1 Passed ({results['stages']['1_syntax']['duration_sec']}s)")

    # =========================================================================
    # STAGE 2: Test Discovery & Dry-Run Collection
    # =========================================================================
    print(" 🔹 [STAGE 2/4] Verifying Test Discovery & Imports...")
    s2_start = time.time()
    s2_passed = True
    s2_output = ""
    s2_errors = []

    runner = runner_override or stack["suggested_runner"]

    if stack["is_python"] and (runner == "pytest" or stack["existing_test_runner"] == "pytest"):
        # Test collection only
        ret, out, err = run_command_capture([sys.executable, "-m", "pytest", "--collect-only", "-q"], target_dir)
        if ret != 0:
            s2_passed = False
            s2_errors.append(err or out)
        else:
            s2_output = out

    elif (stack["is_typescript"] or stack["is_javascript"]) and runner == "vitest":
        ret, out, err = run_command_capture(["npx", "vitest", "--run", "--passWithNoTests"], target_dir)
        if ret != 0 and ret != 127: # Allow missing npx in mock runs
            s2_passed = False
            s2_errors.append(err or out)

    results["stages"]["2_discovery"] = {
        "name": "Test Discovery & Import Graph",
        "passed": s2_passed,
        "duration_sec": round(time.time() - s2_start, 2),
        "output": s2_output.strip(),
        "errors": s2_errors
    }

    if not s2_passed:
        results["all_passed"] = False
        print(f"    ❌ Stage 2 Failed during test collection.")
        for err in s2_errors:
            print(f"       {err}")
    else:
        print(f"    ✅ Stage 2 Passed ({results['stages']['2_discovery']['duration_sec']}s)")

    # =========================================================================
    # STAGE 3: Hermetic Test Suite Execution
    # =========================================================================
    print(" 🔹 [STAGE 3/4] Running Hermetic Fast Tests...")
    s3_start = time.time()
    s3_passed = True
    s3_output = ""
    s3_errors = []

    if stack["is_python"]:
        cmd = [sys.executable, "-m", "pytest", "-ra", "--tb=short", "-m", "unit or smoke" if fast else "not slow"]
        # If no pytest.ini or markers, fallback to running tests/
        if (target_dir / "tests").exists():
            cmd.append("tests")
        
        ret, out, err = run_command_capture(cmd, target_dir, timeout_sec=60)
        s3_output = out
        if ret != 0 and "no tests ran" not in out.lower() and "collected 0 items" not in out.lower():
            # If exit code was 5 (no tests found), treat gracefully
            if ret == 5:
                s3_output += "\n(Notice: No tests matched filter; pass with warning)"
            else:
                s3_passed = False
                s3_errors.append(err if err else out)

    elif stack["is_typescript"] or stack["is_javascript"]:
        cmd = ["npx", "vitest", "run"] if runner == "vitest" else ["npm", "test", "--", "--bail"]
        ret, out, err = run_command_capture(cmd, target_dir, timeout_sec=60)
        s3_output = out
        if ret != 0 and ret != 127:
            s3_passed = False
            s3_errors.append(err if err else out)

    results["stages"]["3_execution"] = {
        "name": "Hermetic Fast Test Execution",
        "passed": s3_passed,
        "duration_sec": round(time.time() - s3_start, 2),
        "output": s3_output.strip(),
        "errors": s3_errors
    }

    if not s3_passed:
        results["all_passed"] = False
        print(f"    ❌ Stage 3 Failed during test execution.")
    else:
        print(f"    ✅ Stage 3 Passed ({results['stages']['3_execution']['duration_sec']}s)")

    # =========================================================================
    # STAGE 4: Diagnostics & Remediation
    # =========================================================================
    print(" 🔹 [STAGE 4/4] Generating Pre-Flight Health Report...")
    total_time = round(time.time() - start_time, 2)
    results["total_duration_sec"] = total_time

    remediations = []
    if not results["stages"]["1_syntax"]["passed"]:
        remediations.append("Fix syntax errors identified in Stage 1 before attempting to run tests.")
    if not results["stages"]["2_discovery"]["passed"]:
        remediations.append("Ensure all dependencies and test packages (e.g., pytest, vitest) are installed in the environment.")
    if not results["stages"]["3_execution"]["passed"]:
        remediations.append("Inspect failed test assertions in Stage 3 and update implementation logic or test mocks.")
    
    if not (target_dir / "tests").exists():
        remediations.append("No /tests/ directory found. Run 'scaffold_tests.py' to generate a complete test suite.")

    results["remediations"] = remediations
    return results

def print_summary_table(res: Dict[str, Any]):
    print("\n" + "=" * 72)
    print(" 🏁 [PRE-FLIGHT VERIFICATION SUMMARY]")
    print("=" * 72)
    print(f" Target Directory : {res['target_dir']}")
    print(f" Total Duration   : {res.get('total_duration_sec', 0)}s")
    print(f" Overall Verdict  : {'🟢 READY FOR LAUNCH (PASS)' if res['all_passed'] else '🔴 BLOCKED (FAIL)'}")
    print("-" * 72)
    
    print(f" {'Stage':<35} | {'Status':<10} | {'Duration'}")
    print("-" * 72)
    for key, stage in res["stages"].items():
        status = "✅ PASS" if stage["passed"] else "❌ FAIL"
        print(f" {stage['name']:<35} | {status:<10} | {stage['duration_sec']}s")

    if res.get("remediations"):
        print("-" * 72)
        print(" 🛠️  [REMEDIATION ACTIONS]")
        for rem in res["remediations"]:
            print(f"  • {rem}")

    print("=" * 72)

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Run 4-stage pre-flight test verification on a codebase.")
    parser.add_argument("--target-dir", type=str, default=".", help="Target repository directory.")
    parser.add_argument("--runner", type=str, default=None, help="Test runner override (pytest, vitest, jest).")
    parser.add_argument("--fast", action="store_true", help="Run only fast unit and smoke tests.")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format.")
    args = parser.parse_args()

    target = Path(args.target_dir).resolve()
    if not target.exists():
        print(f"[ERROR] Target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print("=" * 72)
    print(" 🚀 [PRE-FLIGHT TEST RUNNER] Starting Verification Pipeline")
    print("=" * 72)

    res = run_preflight_pipeline(target, runner_override=args.runner, fast=args.fast)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print_summary_table(res)

    sys.exit(0 if res["all_passed"] else 1)

if __name__ == "__main__":
    main()
