#requires -Version 5.1
<#
.SYNOPSIS
    Run the full 1000x-Agent-Skills test suite locally (Windows).

.DESCRIPTION
    Runs exactly the checks .github/workflows/ci.yml's "validate" job runs,
    in the same order, against the environment scripts\win\dev-setup.ps1
    created. A clean report locally means CI will be clean too.

    Order matters: cheapest and most security-relevant checks run first, so
    a malicious or broken change fails fast instead of waiting for the full
    pytest run.

      1. Skill safety audit       (undeclared capabilities, hidden instructions)
      2. Content digest check     (skill content still matches its attestation)
      3. Skill Doctor validator   (frontmatter, attestation schema, evals)
      4. Pre-flight release audit (secrets, governance files, broken links)
      5. Pytest suite             (all tests, with a coverage floor)

.PARAMETER Verbose2
    Also show full output for passing steps, not just failing ones.
    (Named Verbose2 because -Verbose is a reserved common parameter.)

.PARAMETER K
    Forward to `pytest -k`: run only matching tests, skipping steps 1-4.

.PARAMETER NoSetup
    Fail instead of auto-running dev-setup.ps1 when no environment exists.

.EXAMPLE
    .\scripts\win\dev-test.ps1
    Run every check and print a report.

.EXAMPLE
    .\scripts\win\dev-test.ps1 -K "TestEstimateTokens"
    Run only tests matching that expression.

.NOTES
    If Windows refuses to run this script, that is PowerShell's execution
    policy, not a problem with this script:

        powershell -ExecutionPolicy Bypass -File .\scripts\win\dev-test.ps1

    Exit code is 0 only if every step passed -- safe to use as a pre-push
    gate ($LASTEXITCODE / $? in a calling script).
#>
[CmdletBinding()]
param(
    [Alias("v")][switch]$Verbose2,
    [string]$K = "",
    [switch]$NoSetup
)

$ErrorActionPreference = "Stop"

function Write-Info { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Fail {
    param([string]$Message)
    Write-Host "FAILED: $Message" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Locate the repository regardless of where this script is invoked from
# ---------------------------------------------------------------------------

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPy = Join-Path $VenvDir "Scripts/python.exe"

Set-Location $RepoRoot

# ---------------------------------------------------------------------------
# Make sure an environment exists. Auto-bootstrap it the first time so
# dev-test.ps1 works standalone; -NoSetup opts out for a strict, CI-style
# failure instead.
# ---------------------------------------------------------------------------

if (-not (Test-Path $VenvPy)) {
    if ($NoSetup) {
        Fail "No environment at $VenvDir. Run scripts\win\dev-setup.ps1 first."
    }
    Write-Info "No environment found - running dev-setup.ps1 once to create it"
    & (Join-Path $PSScriptRoot "dev-setup.ps1")
    if ($LASTEXITCODE -ne 0) { Fail "dev-setup.ps1 failed; see the output above." }
    Write-Host ""
}

Write-Host "1000x-Agent-Skills - local test report" -ForegroundColor White
Write-Host "repo: $RepoRoot" -ForegroundColor DarkGray
Write-Host ""

# ---------------------------------------------------------------------------
# Step runner: records name, status, duration and output for every step so
# the final report can show a clean summary while still surfacing full
# output for whatever failed.
# ---------------------------------------------------------------------------

$Steps = New-Object System.Collections.Generic.List[hashtable]

function Invoke-Step {
    param(
        [string]$Name,
        [string]$Exe,
        [string[]]$StepArgs
    )

    Write-Host -NoNewline "> $Name... " -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    $output = & $Exe @StepArgs 2>&1 | Out-String
    $rc = $LASTEXITCODE
    $sw.Stop()
    $elapsed = "{0:N1}" -f $sw.Elapsed.TotalSeconds

    $status = if ($rc -eq 0) { "PASS" } else { "FAIL" }
    $color = if ($rc -eq 0) { "Green" } else { "Red" }
    $icon = if ($rc -eq 0) { "OK" } else { "FAIL" }
    Write-Host "`r[$icon] $Name (${elapsed}s)                    " -ForegroundColor $color

    if ($rc -eq 0 -and $Verbose2) {
        ($output -split "`n") | ForEach-Object { Write-Host "    $_" }
    }

    $Steps.Add(@{
        Name    = $Name
        Status  = $status
        Seconds = [double]$elapsed
        Output  = $output
    })
}

# ---------------------------------------------------------------------------
# Run the checks
# ---------------------------------------------------------------------------

if ($K) {
    Write-Info "Filter given (-K), running only the matching tests"
    Invoke-Step -Name "Pytest ($K)" -Exe $VenvPy -StepArgs @("-m", "pytest", "-v", "-k", $K)
} else {
    Invoke-Step -Name "Skill safety audit" -Exe $VenvPy `
        -StepArgs @("scripts/audit_skill_safety.py", "--strict")
    Invoke-Step -Name "Content digest check" -Exe $VenvPy `
        -StepArgs @("scripts/skill_digest.py", "--check")
    Invoke-Step -Name "Skill Doctor validator" -Exe $VenvPy `
        -StepArgs @("scripts/validate_skills.py")
    Invoke-Step -Name "Pre-flight release audit" -Exe $VenvPy `
        -StepArgs @("skills/custom/public-repo-release-review/scripts/audit_repo.py", "--target", ".", "--strict")
    Invoke-Step -Name "Pytest suite (coverage >= 60%)" -Exe $VenvPy `
        -StepArgs @("-m", "pytest", "-q", "--cov=scripts", "--cov=skills", "--cov=utils",
                    "--cov-report=term-missing", "--cov-fail-under=60")
}

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

$divider = "-" * 64
Write-Host ""
Write-Host $divider
Write-Host " Summary"
Write-Host $divider

$passCount = 0
$totalTime = 0.0
foreach ($step in $Steps) {
    $label = if ($step.Status -eq "PASS") { "PASS" } else { "FAIL" }
    $color = if ($step.Status -eq "PASS") { "Green" } else { "Red" }
    if ($step.Status -eq "PASS") { $passCount++ }
    $totalTime += $step.Seconds
    Write-Host (" {0,-4}  {1,-42} {2,6:N1}s" -f $label, $step.Name, $step.Seconds) -ForegroundColor $color
}

Write-Host $divider

$overallOk = ($passCount -eq $Steps.Count)
$summaryColor = if ($overallOk) { "Green" } else { "Red" }
Write-Host (" {0}/{1} checks passed in {2:N1}s" -f $passCount, $Steps.Count, $totalTime) -ForegroundColor $summaryColor

if (-not $overallOk) {
    Write-Host ""
    Write-Host "Full output of failing step(s):" -ForegroundColor White
    foreach ($step in $Steps) {
        if ($step.Status -eq "FAIL") {
            Write-Host ""
            Write-Host "-- $($step.Name) --" -ForegroundColor Red
            Write-Host $step.Output
        }
    }
}

Write-Host ""
if ($overallOk) {
    Write-Host "This matches what CI checks - safe to push." -ForegroundColor Green
    exit 0
} else {
    Write-Host "CI would fail on this too - fix the step(s) above before pushing." -ForegroundColor Red
    exit 1
}
