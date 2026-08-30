#!/usr/bin/env bash
# dev-setup.sh — one-command local dev environment for 1000x-Agent-Skills (Linux/macOS)
#
# Creates the virtual environment the test suite needs, or updates it in
# place if one already exists. Safe to re-run any time: re-running never
# recreates an environment that is already correct, it only brings it
# up to date with requirements-dev.txt.
#
# Uses uv (https://docs.astral.sh/uv/) when it is on PATH, since it resolves
# and installs the same requirements-dev.txt in a fraction of the time pip
# takes. Falls back to the standard library's venv + pip automatically when
# uv is not installed -- nothing here is required to have this work, uv is
# an optimization, not a dependency of the repository.
#
# What this script does NOT do, by design:
#   - It never touches anything outside this repository. The only thing it
#     creates or modifies is .venv/ at the repository root.
#   - It never uses sudo and never installs anything system-wide.
#   - It never pipes a downloaded script into a shell. If uv is missing it
#     is skipped, not silently fetched and executed -- see --with-uv below
#     for the one opt-in exception, which uses a normal `pip install`.
#
# Usage:
#   scripts/linux/dev-setup.sh                 # create or update .venv
#   scripts/linux/dev-setup.sh --clean         # wipe .venv and rebuild it
#   scripts/linux/dev-setup.sh --no-uv         # force the venv+pip path
#   scripts/linux/dev-setup.sh --with-uv       # `pip install uv` first, then use it
#   scripts/linux/dev-setup.sh --python PATH   # use a specific interpreter
#
# Then run tests with scripts/linux/dev-test.sh.

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

info()  { printf '%s\n' "${CYAN}==>${RESET} $*"; }
ok()    { printf '%s\n' "${GREEN}  ✓${RESET} $*"; }
warn()  { printf '%s\n' "${YELLOW}  !${RESET} $*"; }
die()   { printf '%s\n' "${RED}✗ $*${RESET}" >&2; exit 1; }

trap 'die "dev-setup.sh failed at line $LINENO. See the message above for what to fix."' ERR

# ---------------------------------------------------------------------------
# Locate the repository regardless of where this script is invoked from
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." >/dev/null 2>&1 && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
REQUIREMENTS="${REPO_ROOT}/requirements-dev.txt"
MIN_PY_MAJOR=3
MIN_PY_MINOR=11

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

CLEAN=0
FORCE_NO_UV=0
WITH_UV=0
PYTHON_OVERRIDE=""

usage() {
  sed -n '2,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --clean) CLEAN=1; shift ;;
    --no-uv) FORCE_NO_UV=1; shift ;;
    --with-uv) WITH_UV=1; shift ;;
    --python) PYTHON_OVERRIDE="${2:-}"; [[ -n "$PYTHON_OVERRIDE" ]] || die "--python requires a path"; shift 2 ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
done

if [[ "$FORCE_NO_UV" == "1" && "$WITH_UV" == "1" ]]; then
  die "--no-uv and --with-uv are mutually exclusive"
fi

printf '%s\n' "${BOLD}1000x-Agent-Skills — dev environment setup (Linux/macOS)${RESET}"
printf '%s\n' "${DIM}repo: ${REPO_ROOT}${RESET}"
echo

# ---------------------------------------------------------------------------
# 1. Find a Python interpreter that meets the CI minimum (3.11, matching
#    the oldest version in .github/workflows/ci.yml's test matrix)
# ---------------------------------------------------------------------------

version_ok() {
  # $1 = path to a python executable
  "$1" - <<PY 2>/dev/null
import sys
sys.exit(0 if sys.version_info >= (${MIN_PY_MAJOR}, ${MIN_PY_MINOR}) else 1)
PY
}

find_python() {
  if [[ -n "$PYTHON_OVERRIDE" ]]; then
    command -v "$PYTHON_OVERRIDE" >/dev/null 2>&1 || die "--python '$PYTHON_OVERRIDE' not found"
    version_ok "$PYTHON_OVERRIDE" || die "--python '$PYTHON_OVERRIDE' is older than ${MIN_PY_MAJOR}.${MIN_PY_MINOR}"
    echo "$PYTHON_OVERRIDE"
    return
  fi
  # Prefer the exact versions .github/workflows/ci.yml tests against, so a
  # local pass predicts a CI pass. Only fall through to something newer (or
  # to the bare `python3`/`python`) if neither is available.
  local candidate
  for candidate in python3.12 python3.11 python3.13 python3.14 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && version_ok "$candidate"; then
      command -v "$candidate"
      return
    fi
  done
  return 1
}

info "Looking for Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+"
PYTHON_BIN="$(find_python)" || die "No Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ found on PATH. Install one (e.g. https://www.python.org/downloads/) and re-run, or pass --python /path/to/python3.11."
PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
ok "Using ${PYTHON_BIN} (Python ${PY_VERSION})"

# ---------------------------------------------------------------------------
# 2. Decide whether to use uv or fall back to venv + pip
# ---------------------------------------------------------------------------

USE_UV=0
if [[ "$FORCE_NO_UV" == "0" ]]; then
  if [[ "$WITH_UV" == "1" ]] && ! command -v uv >/dev/null 2>&1; then
    info "Installing uv (https://docs.astral.sh/uv/) via pip — a normal package install, nothing piped from the network into a shell"
    "$PYTHON_BIN" -m pip install --user --upgrade uv >/dev/null
    hash -r
  fi
  if command -v uv >/dev/null 2>&1; then
    USE_UV=1
    ok "Using uv $(uv --version | awk '{print $2}') for environment and dependency management"
  fi
fi
if [[ "$USE_UV" == "0" ]]; then
  warn "uv not found — falling back to the standard library's venv + pip"
  warn "Tip: 'pip install --user uv' (or --with-uv on this script) makes this and every future setup several times faster"
fi

# ---------------------------------------------------------------------------
# 3. Create the virtual environment (idempotent: reused if already present,
#    unless --clean asked for a fresh one)
# ---------------------------------------------------------------------------

if [[ "$CLEAN" == "1" && -d "$VENV_DIR" ]]; then
  info "Removing existing environment (--clean): ${VENV_DIR}"
  rm -rf -- "$VENV_DIR"
fi

if [[ -d "$VENV_DIR" ]]; then
  info "Reusing existing environment: ${VENV_DIR}"
else
  info "Creating virtual environment: ${VENV_DIR}"
  if [[ "$USE_UV" == "1" ]]; then
    uv venv --python "$PYTHON_BIN" "$VENV_DIR" >/dev/null
  else
    "$PYTHON_BIN" -m venv "$VENV_DIR" || die "Could not create a venv. On Debian/Ubuntu you may need: sudo apt install python3-venv"
  fi
  ok "Environment created"
fi

VENV_PY="${VENV_DIR}/bin/python"
[[ -x "$VENV_PY" ]] || die "Expected a Python interpreter at ${VENV_PY} but did not find one. Try --clean."

# ---------------------------------------------------------------------------
# 4. Install / update dependencies. Always runs, whether the venv was just
#    created or already existed — this is what makes re-running the script
#    an update rather than a no-op.
# ---------------------------------------------------------------------------

[[ -f "$REQUIREMENTS" ]] || die "Missing ${REQUIREMENTS}"

info "Installing / updating dependencies from $(basename "$REQUIREMENTS")"
if [[ "$USE_UV" == "1" ]]; then
  uv pip install --python "$VENV_PY" --upgrade -r "$REQUIREMENTS"
else
  "$VENV_PY" -m pip install --quiet --upgrade pip
  "$VENV_PY" -m pip install --quiet --upgrade -r "$REQUIREMENTS"
fi
ok "Dependencies up to date"

# ---------------------------------------------------------------------------
# 5. Sanity check: prove the environment actually works before declaring
#    success, rather than assuming the install step's exit code was enough.
# ---------------------------------------------------------------------------

info "Verifying the environment"
"$VENV_PY" - <<'PY'
from importlib.metadata import version
import jsonschema  # noqa: F401  (import-ability is the check; version comes from metadata)
import pytest  # noqa: F401
print(f"  pytest {version('pytest')}, jsonschema {version('jsonschema')} import cleanly")
PY
ok "Environment verified"

echo
printf '%s\n' "${BOLD}${GREEN}Setup complete.${RESET}"
printf '%s\n' "  Environment : ${VENV_DIR}"
printf '%s\n' "  Python      : ${PY_VERSION}"
printf '%s\n' "  Tool used   : $([[ "$USE_UV" == "1" ]] && echo uv || echo "venv + pip")"
echo
printf '%s\n' "Next: ${BOLD}scripts/linux/dev-test.sh${RESET} to run the full test suite."
