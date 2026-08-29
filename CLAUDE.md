<!-- Companion to AGENTS.md — update both together to prevent instruction drift. -->

# Claude Code Project Guidelines (CLAUDE.md)

## Repository Overview
- **Project Type**: Agent Skills Library & Specification Suite
- **Architecture**: Modular multi-agent repository configured for Antigravity, Claude Code, Cursor, and Codex.

## Essential Commands
- **Test**: `python scripts/validate_skills.py`
- **Run**: `python scripts/install_to_agent.py`

## Directory Architecture
- `docs/`: Specification schemas (attestation, test-cases), authoring standards, and benchmark documentation.
- `scripts/`: Repository maintenance and validation CLI tools (`validate_skills.py`, `install_to_agent.py`).
- `skills/`: Production-ready agent skills catalog partitioned into `anthropic/`, `custom/`, and `google/`.
- `utils/`: Shared utilities, JSON schema definitions, and helper scripts for skill execution.

## Development Guidelines & Agent Best Practices
- **Atomic Modifications**: Make small, verifiable edits using precision diff tools.
- **Specification Compliance**: Enforce strict YAML frontmatter, 500-line body limits, attestation (`attestation.json`), and evaluation coverage (`evals/test-cases.json`).
- **Verification**: Run `python scripts/validate_skills.py` before committing to ensure all skills pass validation with zero errors.
- **Formatting & Fidelity**: Preserve existing docstrings, typing, license headers, and naming conventions.
- **Cross-Agent Sync**: Keep `CLAUDE.md` and `AGENTS.md` strictly synchronized whenever commands or conventions change.

## Tool-Specific Directives (Claude Code)
- Subagent memory and rules are organized under `.claude/`.
- Refer to `AGENTS.md` for tool-agnostic agent directives.
