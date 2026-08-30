#requires -Version 5.1
<#
.SYNOPSIS
    One-command local dev environment for 1000x-Agent-Skills (Windows).

.DESCRIPTION
    Creates the virtual environment the test suite needs, or updates it in
    place if one already exists. Safe to re-run any time: re-running never
    recreates an environment that is already correct, it only brings it up
    to date with requirements-dev.txt.

    Uses uv (https://docs.astral.sh/uv/) when it is on PATH, since it
    resolves and installs the same requirements-dev.txt in a fraction of
    the time pip takes. Falls back to the standard library's venv + pip
    automatically when uv is not installed -- nothing here is required to
    have this work, uv is an optimization, not a dependency of the
    repository.

    What this script does NOT do, by design:
      - It never touches anything outside this repository. The only thing
        it creates or modifies is .venv\ at the repository root.
      - It never installs anything system-wide or requires an elevated
        (Administrator) prompt.
      - It never pipes a downloaded script into a shell. If uv is missing
        it is skipped, not silently fetched and executed -- see -WithUv
        below for the one opt-in exception, which uses a normal `pip
        install`.

.PARAMETER Clean
    Wipe the existing .venv and rebuild it from scratch.

.PARAMETER NoUv
    Force the venv + pip path even if uv is available on PATH.

.PARAMETER WithUv
    Install uv via `pip install --user uv` first (a normal package
    install, nothing piped from the network into a shell), then use it.

.PARAMETER PythonPath
    Use a specific Python interpreter instead of auto-detecting one.

.EXAMPLE
    .\scripts\win\dev-setup.ps1
    Create or update .venv using whatever is on PATH.

.EXAMPLE
    .\scripts\win\dev-setup.ps1 -Clean
    Wipe .venv and rebuild it.

.NOTES
    If Windows refuses to run this script ("running scripts is disabled on
    this system"), that is PowerShell's execution policy, not a problem
    with this script. Run it for this one invocation without changing your
    system-wide policy:

        powershell -ExecutionPolicy Bypass -File .\scripts\win\dev-setup.ps1

    Then run tests with scripts\win\dev-test.ps1.
#>
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$NoUv,
    [switch]$WithUv,
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$MinPyMajor = 3
$MinPyMinor = 11

# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

function Write-Info  { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Message) Write-Host "  [OK] $Message" -ForegroundColor Green }
function Write-Warn2 { param([string]$Message) Write-Host "  [!]  $Message" -ForegroundColor Yellow }
function Fail {
    param([string]$Message)
    Write-Host "FAILED: $Message" -ForegroundColor Red
    exit 1
}

if ($NoUv -and $WithUv) {
    Fail "-NoUv and -WithUv are mutually exclusive"
}

# ---------------------------------------------------------------------------
# Locate the repository regardless of where this script is invoked from
# ---------------------------------------------------------------------------

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$VenvDir = Join-Path $RepoRoot ".venv"
$Requirements = Join-Path $RepoRoot "requirements-dev.txt"
$VenvPy = Join-Path $VenvDir "Scripts/python.exe"

Write-Host "1000x-Agent-Skills - dev environment setup (Windows)" -ForegroundColor White
Write-Host "repo: $RepoRoot" -ForegroundColor DarkGray
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Find a Python interpreter that meets the CI minimum (3.11, matching
#    the oldest version in .github/workflows/ci.yml's test matrix). Prefers
#    the exact versions CI tests, then the Windows `py` launcher, then a
#    bare `python` on PATH.
# ---------------------------------------------------------------------------

# Resolves every candidate (a bare command, or the `py` launcher with a
# version flag) down to one concrete interpreter path via sys.executable,
# so everything downstream -- uv, venv, pip -- deals with a single plain
# path and never has to re-guess which interpreter "python" or "py" meant.
function Resolve-Interpreter {
    param([string]$Exe, [string[]]$LauncherArgs = @())
    try {
        $code = "import sys; sys.exit(0 if sys.version_info >= ($MinPyMajor, $MinPyMinor) else 1)"
        & $Exe @LauncherArgs "-c" $code 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $resolved = (& $Exe @LauncherArgs "-c" "import sys; print(sys.executable)").Trim()
        if (-not $resolved) { return $null }
        return $resolved
    } catch {
        return $null
    }
}

function Find-Python {
    if ($PythonPath) {
        if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) {
            Fail "-PythonPath '$PythonPath' not found"
        }
        $resolved = Resolve-Interpreter -Exe $PythonPath
        if (-not $resolved) {
            Fail "-PythonPath '$PythonPath' is older than $MinPyMajor.$MinPyMinor"
        }
        return $resolved
    }

    # The `py` launcher (installed by python.org's Windows installer) can
    # target an exact version without that version being first on PATH.
    # Checked before a bare `python`/`python3` so the CI-tested versions win
    # even when a newer interpreter shadows them on PATH.
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        foreach ($ver in @("-3.12", "-3.11", "-3.13", "-3.14", "-3")) {
            $resolved = Resolve-Interpreter -Exe "py" -LauncherArgs @($ver)
            if ($resolved) { return $resolved }
        }
    }

    foreach ($candidate in @("python3.12", "python3.11", "python3", "python")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            $resolved = Resolve-Interpreter -Exe $cmd.Source
            if ($resolved) { return $resolved }
        }
    }
    return $null
}

Write-Info "Looking for Python $MinPyMajor.$MinPyMinor+"
$PythonExe = Find-Python
if (-not $PythonExe) {
    Fail "No Python $MinPyMajor.$MinPyMinor+ found. Install one from https://www.python.org/downloads/windows/ (check 'Add python.exe to PATH') and re-run, or pass -PythonPath."
}
$PyVersion = (& $PythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
Write-Ok "Using $PythonExe (Python $PyVersion)"

# ---------------------------------------------------------------------------
# 2. Decide whether to use uv or fall back to venv + pip
# ---------------------------------------------------------------------------

$UseUv = $false
if (-not $NoUv) {
    if ($WithUv -and -not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
        Write-Info "Installing uv (https://docs.astral.sh/uv/) via pip -- a normal package install, nothing piped from the network into a shell"
        & $PythonExe -m pip install --user --upgrade uv | Out-Null
        $env:PATH = "$([Environment]::GetEnvironmentVariable('PATH','User'));$env:PATH"
    }
    $uvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
    if ($uvCmd) {
        $UseUv = $true
        $uvVersion = (& uv --version) -replace '^uv\s+', ''
        Write-Ok "Using uv $uvVersion for environment and dependency management"
    }
}
if (-not $UseUv) {
    Write-Warn2 "uv not found - falling back to the standard library's venv + pip"
    Write-Warn2 "Tip: 'pip install --user uv' (or -WithUv on this script) makes this and every future setup several times faster"
}

# ---------------------------------------------------------------------------
# 3. Create the virtual environment (idempotent: reused if already present,
#    unless -Clean asked for a fresh one)
# ---------------------------------------------------------------------------

if ($Clean -and (Test-Path $VenvDir)) {
    $item = Get-Item $VenvDir -Force
    if ($item.LinkType -ne $null) {
        Fail "-Clean: $VenvDir is a symlink or junction — refusing to remove it to avoid deleting outside the repository"
    }
    Write-Info "Removing existing environment (-Clean): $VenvDir"
    Remove-Item -Recurse -Force $VenvDir
}

if (Test-Path $VenvDir) {
    Write-Info "Reusing existing environment: $VenvDir"
} else {
    Write-Info "Creating virtual environment: $VenvDir"
    if ($UseUv) {
        uv venv --python $PythonExe $VenvDir | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail "uv venv failed (exit $LASTEXITCODE)" }
    } else {
        & $PythonExe -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            Fail "Could not create a venv (exit $LASTEXITCODE)."
        }
    }
    Write-Ok "Environment created"
}

if (-not (Test-Path $VenvPy)) {
    Fail "Expected a Python interpreter at $VenvPy but did not find one. Try -Clean."
}

# ---------------------------------------------------------------------------
# 4. Install / update dependencies. Always runs, whether the venv was just
#    created or already existed -- this is what makes re-running the
#    script an update rather than a no-op.
# ---------------------------------------------------------------------------

if (-not (Test-Path $Requirements)) {
    Fail "Missing $Requirements"
}

Write-Info "Installing / updating dependencies from $(Split-Path -Leaf $Requirements)"
if ($UseUv) {
    uv pip install --python $VenvPy --upgrade -r $Requirements
    if ($LASTEXITCODE -ne 0) { Fail "uv pip install failed (exit $LASTEXITCODE)" }
} else {
    & $VenvPy -m pip install --quiet --upgrade pip
    if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed (exit $LASTEXITCODE)" }
    & $VenvPy -m pip install --quiet --upgrade -r $Requirements
    if ($LASTEXITCODE -ne 0) { Fail "pip install -r requirements-dev.txt failed (exit $LASTEXITCODE)" }
}
Write-Ok "Dependencies up to date"

# ---------------------------------------------------------------------------
# 5. Sanity check: prove the environment actually works before declaring
#    success, rather than assuming the install step's exit code was enough.
# ---------------------------------------------------------------------------

Write-Info "Verifying the environment"
$checkScript = @"
from importlib.metadata import version
import jsonschema  # noqa: F401  (import-ability is the check; version comes from metadata)
import pytest  # noqa: F401
print(f"  pytest {version('pytest')}, jsonschema {version('jsonschema')} import cleanly")
"@
& $VenvPy -c $checkScript
if ($LASTEXITCODE -ne 0) { Fail "Environment verification failed" }
Write-Ok "Environment verified"

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "  Environment : $VenvDir"
Write-Host "  Python      : $PyVersion"
Write-Host "  Tool used   : $(if ($UseUv) { 'uv' } else { 'venv + pip' })"
Write-Host ""
Write-Host "Next: scripts\win\dev-test.ps1 to run the full test suite." -ForegroundColor White
