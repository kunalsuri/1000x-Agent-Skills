#!/usr/bin/env bash
# dev-test.sh — run the full 1000x-Agent-Skills test suite locally (Linux/macOS)
#
# Runs exactly the checks .github/workflows/ci.yml's "validate" job runs, in
# the same order, against the environment scripts/linux/dev-setup.sh created.
# A clean report locally means CI will be clean too.
#
# Order matters: cheapest and most security-relevant checks run first, so a
# malicious or broken change fails fast instead of waiting for the full
# pytest run.
#
#   1. Skill safety audit       (undeclared capabilities, hidden instructions)
#   2. Content digest check     (skill content still matches its attestation)
#   3. Skill Doctor validator   (frontmatter, attestation schema, evals)
#   4. Pre-flight release audit (secrets, governance files, broken links)
#   5. Pytest suite             (all tests, with a coverage floor)
#
# Usage:
#   scripts/linux/dev-test.sh              # run everything, print a report
#   scripts/linux/dev-test.sh -v           # also show full output for passing steps
#   scripts/linux/dev-test.sh -k EXPR      # skip 1-4, run only `pytest -k EXPR`
#   scripts/linux/dev-test.sh --no-setup   # fail instead of auto-running dev-setup.sh
#
# Exit code is 0 only if every step passed — safe to use as a pre-push gate.

set -Eeuo pipefail

# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[91m'; GREEN=$'\033[92m'
  YELLOW=$'\033[93m'; CYAN=$'\033[96m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; CYAN=""; RESET=""
fi

info() { printf '%s\n' "${CYAN}==>${RESET} $*"; }
die()  { printf '%s\n' "${RED}✗ $*${RESET}" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Locate the repository regardless of where this script is invoked from
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." >/dev/null 2>&1 && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
VENV_PY="${VENV_DIR}/bin/python"

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

VERBOSE=0
NO_SETUP=0
PYTEST_K=""

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -v|--verbose) VERBOSE=1; shift ;;
    --no-setup) NO_SETUP=1; shift ;;
    -k) PYTEST_K="${2:-}"; [[ -n "$PYTEST_K" ]] || die "-k requires an expression"; shift 2 ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
done

cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Make sure an environment exists. Auto-bootstrap it the first time so
# `dev-test.sh` works standalone; --no-setup opts out for a strict CI-style
# failure instead.
# ---------------------------------------------------------------------------

if [[ ! -x "$VENV_PY" ]]; then
  if [[ "$NO_SETUP" == "1" ]]; then
    die "No environment at ${VENV_DIR}. Run scripts/linux/dev-setup.sh first."
  fi
  info "No environment found — running dev-setup.sh once to create it"
  "${SCRIPT_DIR}/dev-setup.sh"
  echo
fi

printf '%s\n' "${BOLD}1000x-Agent-Skills — local test report${RESET}"
printf '%s\n' "${DIM}repo: ${REPO_ROOT}${RESET}"
echo

# ---------------------------------------------------------------------------
# Step runner: records name, status, duration and output for every step so
# the final report can show a clean summary while still surfacing full
# output for whatever failed.
# ---------------------------------------------------------------------------

declare -a STEP_NAMES=()
declare -a STEP_STATUS=()
declare -a STEP_SECONDS=()
declare -a STEP_LOGS=()
OVERALL_RC=0

run_step() {
  local name="$1"; shift
  local log_file
  log_file="$(mktemp)"
  local start end elapsed rc

  printf '%s ' "${CYAN}▶${RESET} ${name}..."
  start=$(date +%s.%N)
  if "$@" >"$log_file" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  end=$(date +%s.%N)
  elapsed=$(awk -v s="$start" -v e="$end" 'BEGIN { printf "%.1f", e - s }')

  STEP_NAMES+=("$name")
  STEP_SECONDS+=("$elapsed")
  STEP_LOGS+=("$log_file")

  if [[ "$rc" == "0" ]]; then
    STEP_STATUS+=("PASS")
    printf '\r%s %s %s(%ss)%s%*s\n' "${GREEN}✓${RESET}" "${name}" "$DIM" "$elapsed" "$RESET" 20 ""
    if [[ "$VERBOSE" == "1" ]]; then
      sed 's/^/    /' "$log_file"
    fi
  else
    STEP_STATUS+=("FAIL")
    OVERALL_RC=1
    printf '\r%s %s %s(%ss)%s%*s\n' "${RED}✗${RESET}" "${name}" "$DIM" "$elapsed" "$RESET" 20 ""
  fi
}

# ---------------------------------------------------------------------------
# Run the checks
# ---------------------------------------------------------------------------

if [[ -n "$PYTEST_K" ]]; then
  info "Filter given (-k), running only the matching tests"
  run_step "Pytest ($PYTEST_K)" "$VENV_PY" -m pytest -v -k "$PYTEST_K"
else
  run_step "Skill safety audit"       "$VENV_PY" scripts/audit_skill_safety.py --strict
  run_step "Content digest check"     "$VENV_PY" scripts/skill_digest.py --check
  run_step "Skill Doctor validator"   "$VENV_PY" scripts/validate_skills.py
  run_step "Pre-flight release audit" "$VENV_PY" skills/custom/public-repo-release-review/scripts/audit_repo.py --target . --strict
  run_step "Pytest suite (coverage >= 60%)" \
    "$VENV_PY" -m pytest -q --cov=scripts --cov=skills --cov=utils \
      --cov-report=term-missing --cov-fail-under=60
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

echo
printf '%s\n' "${BOLD}────────────────────────────────────────────────────────────${RESET}"
printf '%s\n' "${BOLD} Summary${RESET}"
printf '%s\n' "${BOLD}────────────────────────────────────────────────────────────${RESET}"

TOTAL_TIME=0
PASS_COUNT=0
for i in "${!STEP_NAMES[@]}"; do
  if [[ "${STEP_STATUS[$i]}" == "PASS" ]]; then
    icon="${GREEN}PASS${RESET}"; ((PASS_COUNT++)) || true
  else
    icon="${RED}FAIL${RESET}"
  fi
  printf ' %-4b  %-42s %6ss\n' "$icon" "${STEP_NAMES[$i]}" "${STEP_SECONDS[$i]}"
  TOTAL_TIME=$(awk -v t="$TOTAL_TIME" -v s="${STEP_SECONDS[$i]}" 'BEGIN { printf "%.1f", t + s }')
done

printf '%s\n' "${BOLD}────────────────────────────────────────────────────────────${RESET}"

if [[ "$OVERALL_RC" == "0" ]]; then
  printf '%s\n' "${BOLD}${GREEN} ${#STEP_NAMES[@]}/${#STEP_NAMES[@]} checks passed${RESET} in ${TOTAL_TIME}s"
else
  printf '%s\n' "${BOLD}${RED} ${PASS_COUNT}/${#STEP_NAMES[@]} checks passed${RESET} in ${TOTAL_TIME}s"
  echo
  printf '%s\n' "${BOLD}Full output of failing step(s):${RESET}"
  for i in "${!STEP_NAMES[@]}"; do
    if [[ "${STEP_STATUS[$i]}" == "FAIL" ]]; then
      echo
      printf '%s\n' "${RED}── ${STEP_NAMES[$i]} ──${RESET}"
      cat "${STEP_LOGS[$i]}"
    fi
  done
fi

for log in "${STEP_LOGS[@]}"; do rm -f -- "$log"; done

echo
if [[ "$OVERALL_RC" == "0" ]]; then
  printf '%s\n' "${GREEN}${BOLD}This matches what CI checks — safe to push.${RESET}"
else
  printf '%s\n' "${RED}${BOLD}CI would fail on this too — fix the step(s) above before pushing.${RESET}"
fi

exit "$OVERALL_RC"
