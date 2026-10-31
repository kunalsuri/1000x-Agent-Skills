---
name: cross-platform-dev-scripts
version: 1.0.0
description: Generates and validates turnkey, cross-platform dev setup and test scripts (scripts/win and scripts/linux) with dual-engine uv/venv support. Use when setting up a repository for local onboarding, adding Windows and Linux dev scripts, or verifying script parity.
license: Apache-2.0
compatibility: Requires bash or PowerShell, and Python 3.10+
allowed-tools: [run_command, view_file, write_to_file, replace_file_content]
metadata:
  author: Kunal Suri <kunal.suri@cea.fr>
  tags: dev-scripts, powershell, bash, onboarding, testing, uv
---

# Cross-Platform Dev Scripts & Local Onboarding

## Purpose
Provides a standardized, atomic workflow to equip any repository with hardened, turnkey developer setup and test scripts:
- `scripts/linux/dev-setup.sh` (Linux / macOS / WSL)
- `scripts/linux/dev-test.sh`
- `scripts/win/dev-setup.ps1` (Windows PowerShell 5.1 / 7+)
- `scripts/win/dev-test.ps1`

Empowers any contributor or autonomous agent to clone a repository and immediately run setup and test commands with zero configuration friction.

---

## Architectural Principles

1. **Dual-Engine Acceleration (`uv` + `venv`)**:
   - Uses `uv` when installed on the user's PATH for 10x–100x faster package resolution.
   - Automatically and gracefully falls back to the Python standard library's `venv` + `pip` when `uv` is absent.
   - Never mandates external downloads or pipes unverified scripts into a shell.

2. **Strict Hermetic Isolation (Least Privilege)**:
   - Everything is confined strictly to `.venv/` at the repository root.
   - Never requires `sudo` or Administrator escalation.
   - All paths and cleanup routines (`rm -rf -- "$VENV_DIR"`) are strictly quoted.

3. **Parity & Developer Experience (DX)**:
   - Identical test targets and step sequences between Windows PowerShell and Linux Bash.
   - Auto-bootstrap: `dev-test` runs `dev-setup` automatically if the virtual environment does not exist yet.
   - Test filtering: supports `-k <expr>` (Bash) and `-K <expr>` (PowerShell) for fast local iteration.

---

## Procedural Workflow

### Phase 1: Heavy-Lifting Scaffolding
Inspect the target project root and execute the built-in generator script:

```bash
python <skill_path>/scripts/scaffold_dev_scripts.py --target . [--requirements requirements-dev.txt] [--test-cmd "-m pytest"]
```

The script automatically:
1. Detects project manifests (`requirements-dev.txt`, `requirements.txt`, `pyproject.toml`, etc.).
2. Creates `scripts/linux/` and `scripts/win/` directories idempotently.
3. Generates the 4 hardened scripts with proper permissions (`0o755` for `.sh` scripts).
4. Outputs a JSON summary of generated files.

---

### Phase 2: Semantic Tailoring (Agent Review)
Inspect the generated scripts and tailor them to any project-specific constraints:
1. **Requirements & Build Tools**:
   - If the project requires multiple requirements files (e.g. `requirements.txt` + `requirements-dev.txt`), update the setup scripts to install both.
2. **Environment Variables & Secrets**:
   - If tests require specific local environment flags (e.g. `TESTING=1` or `PYTHONPATH=.`), configure them in `dev-test.sh` and `dev-test.ps1`.
3. **Multi-Step Test Pipelines**:
   - If the project has linting or type-checking steps (e.g. `ruff check`, `mypy`), add corresponding `run_step` (Bash) and `Invoke-Step` (PowerShell) invocations in both test scripts in identical order.

---

### Phase 3: Parity & Safety Verification
Run the verification tool to audit the created scripts for safety invariants and cross-platform parity:

```bash
python <skill_path>/scripts/validate_dev_scripts.py --target .
```

The validator verifies:
- Script presence and shebang formatting.
- Strict error handling (`set -Eeuo pipefail` in Bash, `$ErrorActionPreference = "Stop"` in PowerShell).
- Safe quoting and isolation (no `sudo` invocations, no piping remote scripts to a shell, no writes outside `.venv/`).
- Cross-platform step parity and filter support.
- Static syntax checking (`bash -n` and PowerShell AST parsing when tooling is present).
