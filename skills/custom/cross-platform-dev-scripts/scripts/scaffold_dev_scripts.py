#!/usr/bin/env python3
"""
Scaffolds cross-platform developer environment setup and test scripts.
Creates scripts/win/ and scripts/linux/ with hardened dev-setup and dev-test scripts.
"""

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Dict, Any, Optional


BASH_SETUP_TEMPLATE = '''#!/usr/bin/env bash
# dev-setup.sh — one-command local dev environment for {project_name} (Linux/macOS)
#
# Creates the virtual environment the test suite needs, or updates it in
# place if one already exists. Safe to re-run any time: re-running never
# recreates an environment that is already correct, it only brings it
# up to date with {requirements_rel}.
#
# Uses uv (https://docs.astral.sh/uv/) when it is on PATH, since it resolves
# and installs the same dependencies in a fraction of the time pip takes.
# Falls back to the standard library's venv + pip automatically when uv is
# not installed -- uv is an optimization, not a required dependency.
#
# What this script does NOT do, by design:
#   - It never touches anything outside this repository. The only thing it
#     creates or modifies is .venv/ at the repository root.
#   - It never uses sudo and never installs anything system-wide.
#   - It never pipes a downloaded script into a shell.
#
# Usage:
#   scripts/linux/dev-setup.sh                 # create or update .venv
#   scripts/linux/dev-setup.sh --clean         # wipe .venv and rebuild it
#   scripts/linux/dev-setup.sh --no-uv         # force the venv+pip path
#   scripts/linux/dev-setup.sh --with-uv       # install uv via pip first, then use it
#   scripts/linux/dev-setup.sh --python PATH   # use a specific interpreter

set -Eeuo pipefail

# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

if [[ -t 1 ]] && [[ -z "${{NO_COLOR:-}}" ]]; then
  BOLD='\\033[1m'; DIM='\\033[2m'; RED='\\033[91m'; GREEN='\\033[92m'
  YELLOW='\\033[93m'; CYAN='\\033[96m'; RESET='\\033[0m'
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; CYAN=""; RESET=""
fi

info()  {{ printf '%b\\n' "${{CYAN}}==>${{RESET}} $*"; }}
ok()    {{ printf '%b\\n' "${{GREEN}}  [OK]${{RESET}} $*"; }}
warn()  {{ printf '%b\\n' "${{YELLOW}}  [!]${{RESET}} $*"; }}
die()   {{ printf '%b\\n' "${{RED}}FAILED: $*${{RESET}}" >&2; exit 1; }}

trap 'die "dev-setup.sh failed at line $LINENO. See the message above for what to fix."' ERR

# ---------------------------------------------------------------------------
# Locate repository root
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${{BASH_SOURCE[0]}}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${{SCRIPT_DIR}}/../.." >/dev/null 2>&1 && pwd)"
VENV_DIR="${{REPO_ROOT}}/.venv"
REQUIREMENTS="${{REPO_ROOT}}/{requirements_rel}"
MIN_PY_MAJOR={min_py_major}
MIN_PY_MINOR={min_py_minor}

CLEAN=0
FORCE_NO_UV=0
WITH_UV=0
PYTHON_OVERRIDE=""

usage() {{
  sed -n '2,22p' "${{BASH_SOURCE[0]}}" | sed 's/^# \\{{0,1\\}}//'
}}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --clean) CLEAN=1; shift ;;
    --no-uv) FORCE_NO_UV=1; shift ;;
    --with-uv) WITH_UV=1; shift ;;
    --python)
      [[ $# -ge 2 ]] || die "--python requires a path argument"
      PYTHON_OVERRIDE="$2"
      shift 2
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

if [[ $FORCE_NO_UV -eq 1 ]] && [[ $WITH_UV -eq 1 ]]; then
  die "--no-uv and --with-uv are mutually exclusive"
fi

printf '%b\\n' "${{BOLD}}{project_name} - dev environment setup (Linux/macOS)${{RESET}}"
printf '%b\\n\\n' "${{DIM}}repo: ${{REPO_ROOT}}${{RESET}}"

if [[ $CLEAN -eq 1 ]] && [[ -d "$VENV_DIR" ]]; then
  info "Wiping existing virtual environment (--clean)"
  rm -rf -- "$VENV_DIR"
  ok "Removed $VENV_DIR"
fi

# Detect Python interpreter
find_python() {{
  if [[ -n "$PYTHON_OVERRIDE" ]]; then
    command -v "$PYTHON_OVERRIDE" 2>/dev/null || die "Specified Python not found: $PYTHON_OVERRIDE"
    return
  fi
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      local ver
      ver="$("$candidate" -c 'import sys; print(f"{{sys.version_info[0]}}.{{sys.version_info[1]}}")' 2>/dev/null || true)"
      local maj="${{ver%%.*}}"
      local min="${{ver##*.}}"
      if [[ "$maj" -eq "$MIN_PY_MAJOR" ]] && [[ "$min" -ge "$MIN_PY_MINOR" ]]; then
        command -v "$candidate"
        return
      fi
    fi
  done
  die "Python >= ${{MIN_PY_MAJOR}}.${{MIN_PY_MINOR}} is required. Please install it first."
}}

BASE_PYTHON="$(find_python)"
PY_VER="$("$BASE_PYTHON" -c 'import sys; print(f"{{sys.version_info[0]}}.{{sys.version_info[1]}}.{{sys.version_info[2]}}")')"
ok "Using host Python: $BASE_PYTHON ($PY_VER)"

# uv optimization path
USE_UV=0
if [[ $FORCE_NO_UV -eq 0 ]]; then
  if command -v uv >/dev/null 2>&1; then
    USE_UV=1
  elif [[ $WITH_UV -eq 1 ]]; then
    info "Installing uv via pip (--with-uv)"
    "$BASE_PYTHON" -m pip install --user uv
    if command -v uv >/dev/null 2>&1; then
      USE_UV=1
    fi
  fi
fi

if [[ $USE_UV -eq 1 ]]; then
  ok "uv detected: $(uv --version)"
  if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment via uv"
    uv venv --python "$BASE_PYTHON" "$VENV_DIR"
  fi
  if [[ -f "$REQUIREMENTS" ]]; then
    info "Syncing dependencies via uv pip"
    uv pip install --python "$VENV_DIR/bin/python" -r "$REQUIREMENTS"
  fi
else
  info "Using standard library venv + pip"
  if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment via venv"
    "$BASE_PYTHON" -m venv "$VENV_DIR"
  fi
  if [[ -f "$REQUIREMENTS" ]]; then
    info "Installing dependencies via pip"
    "$VENV_DIR/bin/python" -m pip install --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS"
  fi
fi

ok "Environment ready at $VENV_DIR"
info "Run tests with: scripts/linux/dev-test.sh"
'''


BASH_TEST_TEMPLATE = '''#!/usr/bin/env bash
# dev-test.sh — run tests locally for {project_name} (Linux/macOS)
#
# Usage:
#   scripts/linux/dev-test.sh              # run all checks
#   scripts/linux/dev-test.sh -v           # show verbose output
#   scripts/linux/dev-test.sh -k EXPR      # run only matching tests
#   scripts/linux/dev-test.sh --no-setup   # fail instead of auto-running dev-setup.sh
#
# Exit code is 0 only if every step passed.

set -Eeuo pipefail

if [[ -t 1 ]] && [[ -z "${{NO_COLOR:-}}" ]]; then
  BOLD='\\033[1m'; DIM='\\033[2m'; RED='\\033[91m'; GREEN='\\033[92m'
  YELLOW='\\033[93m'; CYAN='\\033[96m'; RESET='\\033[0m'
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; CYAN=""; RESET=""
fi

info() {{ printf '%b\\n' "${{CYAN}}==>${{RESET}} $*"; }}
die()  {{ printf '%b\\n' "${{RED}}FAILED: $*${{RESET}}" >&2; exit 1; }}

SCRIPT_DIR="$(cd -- "$(dirname -- "${{BASH_SOURCE[0]}}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${{SCRIPT_DIR}}/../.." >/dev/null 2>&1 && pwd)"
VENV_DIR="${{REPO_ROOT}}/.venv"
VENV_PY="${{VENV_DIR}}/bin/python"

VERBOSE=0
NO_SETUP=0
FILTER_EXPR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--verbose) VERBOSE=1; shift ;;
    --no-setup) NO_SETUP=1; shift ;;
    -k)
      [[ $# -ge 2 ]] || die "-k requires an expression"
      FILTER_EXPR="$2"
      shift 2
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

if [[ ! -x "$VENV_PY" ]]; then
  if [[ $NO_SETUP -eq 1 ]]; then
    die "Virtualenv not found at $VENV_DIR. Run scripts/linux/dev-setup.sh first."
  fi
  info "Environment not found — running dev-setup.sh once"
  "${{SCRIPT_DIR}}/dev-setup.sh"
fi

cd "$REPO_ROOT"

printf '%b\\n' "${{BOLD}}{project_name} - local test runner (Linux/macOS)${{RESET}}"
printf '%b\\n\\n' "${{DIM}}repo: ${{REPO_ROOT}}${{RESET}}"

run_step() {{
  local name="$1"
  shift
  local start_time
  start_time="$(date +%s)"
  info "Running: $name"
  local output_file
  output_file="$(mktemp)"

  if "$@" > "$output_file" 2>&1; then
    local end_time
    end_time="$(date +%s)"
    local duration=$((end_time - start_time))
    printf '%b\\n' "${{GREEN}}  [OK]${{RESET}} $name (${{duration}}s)"
    if [[ $VERBOSE -eq 1 ]]; then
      cat "$output_file"
    fi
    rm -f "$output_file"
  else
    local end_time
    end_time="$(date +%s)"
    local duration=$((end_time - start_time))
    printf '%b\\n' "${{RED}}  [FAIL]${{RESET}} $name (${{duration}}s)"
    cat "$output_file"
    rm -f "$output_file"
    die "Step '$name' failed"
  fi
}}

if [[ -n "$FILTER_EXPR" ]]; then
  info "Running filtered test suite (-k $FILTER_EXPR)"
  "$VENV_PY" {test_cmd_args} -k "$FILTER_EXPR"
else
  run_step "Unit and Integration Tests" "$VENV_PY" {test_cmd_args}
fi

printf '\\n%b\\n' "${{GREEN}}All tests passed successfully!${{RESET}}"
'''


PWSH_SETUP_TEMPLATE = '''#requires -Version 5.1
<#
.SYNOPSIS
    One-command local dev environment for {project_name} (Windows).

.DESCRIPTION
    Creates or updates the virtual environment at .venv\\ using uv when
    available, falling back to Python standard library venv + pip.

.PARAMETER Clean
    Wipe .venv and rebuild from scratch.

.PARAMETER NoUv
    Force the venv + pip path even if uv is available on PATH.

.PARAMETER WithUv
    Install uv via `pip install --user uv` first, then use it.

.PARAMETER PythonPath
    Use a specific Python interpreter instead of auto-detecting one.

.NOTES
    If Windows refuses to run this script due to PowerShell ExecutionPolicy,
    execute this invocation via:
        powershell -ExecutionPolicy Bypass -File .\\scripts\\win\\dev-setup.ps1
#>
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$NoUv,
    [switch]$WithUv,
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$MinPyMajor = {min_py_major}
$MinPyMinor = {min_py_minor}

function Write-Info  {{ param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }}
function Write-Ok    {{ param([string]$Message) Write-Host "  [OK] $Message" -ForegroundColor Green }}
function Write-Warn2 {{ param([string]$Message) Write-Host "  [!]  $Message" -ForegroundColor Yellow }}
function Fail        {{ param([string]$Message) Write-Host "FAILED: $Message" -ForegroundColor Red; exit 1 }}

if ($NoUv -and $WithUv) {{
    Fail "-NoUv and -WithUv are mutually exclusive"
}}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$VenvDir = Join-Path $RepoRoot ".venv"
$Requirements = Join-Path $RepoRoot "{requirements_rel}"
$VenvPy = Join-Path $VenvDir "Scripts/python.exe"

Write-Host "{project_name} - dev environment setup (Windows)" -ForegroundColor White
Write-Host "repo: $RepoRoot" -ForegroundColor DarkGray
Write-Host ""

if ($Clean -and (Test-Path $VenvDir)) {{
    Write-Info "Wiping existing virtual environment (-Clean)"
    Remove-Item -Recurse -Force $VenvDir
    Write-Ok "Removed $VenvDir"
}}

function Find-Python {{
    if ($PythonPath) {{
        if (Get-Command $PythonPath -ErrorAction SilentlyContinue) {{ return $PythonPath }}
        Fail "Specified Python interpreter not found: $PythonPath"
    }}
    foreach ($cand in @("python", "py", "python3")) {{
        if (Get-Command $cand -ErrorAction SilentlyContinue) {{
            $ver = & $cand -c "import sys; print(f'{{sys.version_info[0]}}.{{sys.version_info[1]}}')" 2>$null
            if ($ver) {{
                $parts = $ver.Split(".")
                if ([int]$parts[0] -eq $MinPyMajor -and [int]$parts[1] -ge $MinPyMinor) {{
                    return $cand
                }}
            }}
        }}
    }}
    Fail "Python >= $MinPyMajor.$MinPyMinor is required. Please install it first."
}}

$BasePy = Find-Python
$HostVer = & $BasePy -c "import sys; print(f'{{sys.version_info[0]}}.{{sys.version_info[1]}}.{{sys.version_info[2]}}')"
Write-Ok "Using host Python: $BasePy ($HostVer)"

$UseUv = $false
if (-not $NoUv) {{
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {{
        $UseUv = $true
    }} elseif ($WithUv) {{
        Write-Info "Installing uv via pip (-WithUv)"
        & $BasePy -m pip install --user uv
        if (Get-Command "uv" -ErrorAction SilentlyContinue) {{
            $UseUv = $true
        }}
    }}
}}

if ($UseUv) {{
    $uvVer = & uv --version
    Write-Ok "uv detected: $uvVer"
    if (-not (Test-Path $VenvDir)) {{
        Write-Info "Creating virtual environment via uv"
        & uv venv --python $BasePy $VenvDir
    }}
    if (Test-Path $Requirements) {{
        Write-Info "Syncing dependencies via uv pip"
        & uv pip install --python $VenvPy -r $Requirements
    }}
}} else {{
    Write-Info "Using standard library venv + pip"
    if (-not (Test-Path $VenvDir)) {{
        Write-Info "Creating virtual environment via venv"
        & $BasePy -m venv $VenvDir
    }}
    if (Test-Path $Requirements) {{
        Write-Info "Installing dependencies via pip"
        & $VenvPy -m pip install --upgrade pip
        & $VenvPy -m pip install -r $Requirements
    }}
}}

Write-Ok "Environment ready at $VenvDir"
Write-Info "Run tests with: scripts\\win\\dev-test.ps1"
'''


PWSH_TEST_TEMPLATE = '''#requires -Version 5.1
<#
.SYNOPSIS
    Run tests locally for {project_name} (Windows).

.DESCRIPTION
    Runs the local test suite using the virtual environment at .venv\\.
    Auto-bootstraps the environment using dev-setup.ps1 if not found.

.PARAMETER Verbose2
    Also show full output for passing steps.

.PARAMETER K
    Forward filter expression to test runner.

.PARAMETER NoSetup
    Fail instead of auto-running dev-setup.ps1 when .venv does not exist.

.NOTES
    If Windows refuses to run this script due to PowerShell ExecutionPolicy,
    execute this invocation via:
        powershell -ExecutionPolicy Bypass -File .\\scripts\\win\\dev-test.ps1
#>
[CmdletBinding()]
param(
    [Alias("v")][switch]$Verbose2,
    [string]$K = "",
    [switch]$NoSetup
)

$ErrorActionPreference = "Stop"

function Write-Info {{ param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }}
function Fail       {{ param([string]$Message) Write-Host "FAILED: $Message" -ForegroundColor Red; exit 1 }}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPy = Join-Path $VenvDir "Scripts/python.exe"

Set-Location $RepoRoot

if (-not (Test-Path $VenvPy)) {{
    if ($NoSetup) {{
        Fail "No environment at $VenvDir. Run scripts\\win\\dev-setup.ps1 first."
    }}
    Write-Info "No environment found — running dev-setup.ps1 once"
    & (Join-Path $PSScriptRoot "dev-setup.ps1")
    if ($LASTEXITCODE -ne 0) {{ Fail "dev-setup.ps1 failed" }}
    Write-Host ""
}}

Write-Host "{project_name} - local test report (Windows)" -ForegroundColor White
Write-Host "repo: $RepoRoot" -ForegroundColor DarkGray
Write-Host ""

function Invoke-Step {{
    param(
        [string]$Name,
        [string]$Exe,
        [string[]]$StepArgs
    )
    Write-Info "Running: $Name"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $pinfo = New-Object System.Diagnostics.ProcessStartInfo
    $pinfo.FileName = $Exe
    $pinfo.Arguments = ($StepArgs -join " ")
    $pinfo.RedirectStandardOutput = $true
    $pinfo.RedirectStandardError = $true
    $pinfo.UseShellExecute = $false
    $pinfo.WorkingDirectory = $RepoRoot

    $proc = [System.Diagnostics.Process]::Start($pinfo)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    $sw.Stop()
    $dur = [math]::Round($sw.Elapsed.TotalSeconds, 1)

    if ($proc.ExitCode -eq 0) {{
        Write-Host "  [OK] $Name (${{dur}}s)" -ForegroundColor Green
        if ($Verbose2 -and ($stdout -or $stderr)) {{
            Write-Host ($stdout + $stderr) -ForegroundColor DarkGray
        }}
    }} else {{
        Write-Host "  [FAIL] $Name (${{dur}}s)" -ForegroundColor Red
        Write-Host ($stdout + $stderr) -ForegroundColor Yellow
        Fail "Step '$Name' failed with exit code $($proc.ExitCode)"
    }}
}}

if ($K) {{
    Write-Info "Running filtered test suite (-K $K)"
    & $VenvPy {pwsh_test_cmd_args} -k $K
    if ($LASTEXITCODE -ne 0) {{ Fail "Filtered tests failed" }}
}} else {{
    Invoke-Step -Name "Unit and Integration Tests" -Exe $VenvPy -StepArgs @({pwsh_step_args})
}}

Write-Host ""
Write-Host "All tests passed successfully!" -ForegroundColor Green
'''


def detect_requirements(repo_root: Path) -> str:
    """Finds the most suitable requirements or config file."""
    candidates = [
        "requirements-dev.txt",
        "requirements_dev.txt",
        "requirements-test.txt",
        "requirements.txt",
        "setup.cfg",
        "pyproject.toml"
    ]
    for c in candidates:
        if (repo_root / c).is_file():
            return c
    return "requirements.txt"


def scaffold_dev_scripts(
    target_dir: Path,
    project_name: Optional[str] = None,
    requirements: Optional[str] = None,
    min_py: str = "3.11",
    test_cmd: str = "-m pytest",
    force: bool = False
) -> Dict[str, Any]:
    """Scaffold scripts/win and scripts/linux with dev-setup and dev-test scripts."""
    target_dir = target_dir.resolve()
    if not target_dir.is_dir():
        raise ValueError(f"Target directory does not exist: {target_dir}")

    pname = project_name or target_dir.name
    req_rel = requirements or detect_requirements(target_dir)

    try:
        min_major, min_minor = [int(x) for x in min_py.split(".")[:2]]
    except Exception:
        min_major, min_minor = 3, 11

    test_args = test_cmd.strip()
    if test_args.startswith("python "):
        test_args = test_args[len("python "):].strip()

    args_list = [f'"{part}"' for part in test_args.split()]
    pwsh_step_args = ", ".join(args_list) if args_list else '"-m", "pytest"'
    pwsh_test_cmd_args = " ".join(test_args.split())

    linux_dir = target_dir / "scripts" / "linux"
    win_dir = target_dir / "scripts" / "win"

    linux_dir.mkdir(parents=True, exist_ok=True)
    win_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    # 1. Linux dev-setup.sh
    sh_setup_path = linux_dir / "dev-setup.sh"
    if force or not sh_setup_path.exists():
        content = BASH_SETUP_TEMPLATE.format(
            project_name=pname,
            requirements_rel=req_rel,
            min_py_major=min_major,
            min_py_minor=min_minor
        )
        sh_setup_path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))
        try:
            sh_setup_path.chmod(sh_setup_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass
        files_created.append(str(sh_setup_path.relative_to(target_dir)))

    # 2. Linux dev-test.sh
    sh_test_path = linux_dir / "dev-test.sh"
    if force or not sh_test_path.exists():
        content = BASH_TEST_TEMPLATE.format(
            project_name=pname,
            test_cmd_args=test_args
        )
        sh_test_path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))
        try:
            sh_test_path.chmod(sh_test_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass
        files_created.append(str(sh_test_path.relative_to(target_dir)))

    # 3. Windows dev-setup.ps1
    ps1_setup_path = win_dir / "dev-setup.ps1"
    if force or not ps1_setup_path.exists():
        content = PWSH_SETUP_TEMPLATE.format(
            project_name=pname,
            requirements_rel=req_rel,
            min_py_major=min_major,
            min_py_minor=min_minor
        )
        ps1_setup_path.write_text(content, encoding="utf-8")
        files_created.append(str(ps1_setup_path.relative_to(target_dir)))

    # 4. Windows dev-test.ps1
    ps1_test_path = win_dir / "dev-test.ps1"
    if force or not ps1_test_path.exists():
        content = PWSH_TEST_TEMPLATE.format(
            project_name=pname,
            pwsh_test_cmd_args=pwsh_test_cmd_args,
            pwsh_step_args=pwsh_step_args
        )
        ps1_test_path.write_text(content, encoding="utf-8")
        files_created.append(str(ps1_test_path.relative_to(target_dir)))

    return {
        "target": str(target_dir),
        "project_name": pname,
        "requirements": req_rel,
        "min_python": f"{min_major}.{min_minor}",
        "test_cmd": test_args,
        "files_created": files_created
    }


def main():
    parser = argparse.ArgumentParser(description="Scaffold cross-platform dev scripts.")
    parser.add_argument("--target", "-t", default=".", help="Target repository directory (default: current dir)")
    parser.add_argument("--name", "-n", default=None, help="Project name (default: directory name)")
    parser.add_argument("--requirements", "-r", default=None, help="Requirements file path (relative to repo root)")
    parser.add_argument("--min-python", default="3.11", help="Minimum required Python version (default: 3.11)")
    parser.add_argument("--test-cmd", default="-m pytest", help="Test command to run (default: -m pytest)")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing scripts")
    parser.add_argument("--json", action="store_true", help="Output JSON result summary")

    args = parser.parse_args()
    target_path = Path(args.target).resolve()

    try:
        result = scaffold_dev_scripts(
            target_dir=target_path,
            project_name=args.name,
            requirements=args.requirements,
            min_py=args.min_python,
            test_cmd=args.test_cmd,
            force=args.force
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Scaffolded cross-platform scripts for '{result['project_name']}':")
            for f in result["files_created"]:
                print(f"  + {f}")
            if not result["files_created"]:
                print("  No new files created (already exist). Use --force to overwrite.")
    except Exception as e:
        print(f"Error scaffolding scripts: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
