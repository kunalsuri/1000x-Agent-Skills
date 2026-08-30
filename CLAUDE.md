<!-- Companion to AGENTS.md — update both together to prevent instruction drift. -->

# Claude Code Project Guidelines (CLAUDE.md)

## Repository Overview
- **Project Type**: Agent Skills Library & Specification Suite
- **Architecture**: Modular multi-agent repository configured for Antigravity, Claude Code, Cursor, and Codex.

## Essential Commands
- **Test**: `python -m pytest`
- **Validate**: `python scripts/validate_skills.py`
- **Audit**: `python scripts/audit_skill_safety.py --strict`
- **Digest**: `python scripts/skill_digest.py --check`
- **Release**: `python skills/custom/public-repo-release-review/scripts/audit_repo.py --target . --strict`
- **Run**: `python scripts/install_to_agent.py --target claude --all`

## Directory Architecture
- `docs/`: Specification schemas (`schemas/attestation.schema.json`), the reviewed safety-exemption list (`safety-allowlist.json`), tooling capability declarations, authoring standards, and benchmark documentation.
- `scripts/`: Repository maintenance and validation CLI tools (`validate_skills.py`, `audit_skill_safety.py`, `skill_digest.py`, `install_to_agent.py`).
- `skills/`: Production-ready agent skills catalog partitioned into `anthropic/`, `custom/`, and `google/`.
- `tests/`: Pytest suite covering the validators, the safety auditor and every skill script.
- `utils/`: Shared utilities, JSON schema definitions, and helper scripts for skill execution.

## Development Guidelines & Agent Best Practices
- **Atomic Modifications**: Make small, verifiable edits using precision diff tools.
- **Specification Compliance**: Enforce strict YAML frontmatter, 500-line body limits, attestation (`attestation.json`), declared capabilities, and evaluation coverage (`evals/test-cases.json`).
- **Verification**: Run `python -m pytest` and `python scripts/validate_skills.py` before committing; both must pass with zero errors.
- **Capability Honesty**: Every skill declares `capabilities` in `attestation.json`. `scripts/audit_skill_safety.py` derives the same values from the source and fails the build when code exceeds its declaration. Never widen a declaration to silence the auditor without saying why in `capabilities_rationale`.
- **Re-attest After Editing**: Editing any file in a skill invalidates its `content_digest`. Re-run `python scripts/skill_digest.py --update` and review the diff -- that step is the deliberate act the digest exists to force.
- **Never Weaken a Check**: Do not add a `docs/safety-allowlist.json` entry without a pinned fingerprint and a written reason, and never lower the coverage floor to turn a red build green.
- **No Empty Tests**: A test that cannot fail is worse than no test. Scaffolded tests use `pytest.fail(...)` and stay red until written.
- **Mirror Parity**: `.agents/skills/` is a byte-identical mirror of `skills/custom/`. Change the canonical copy, then re-sync; CI enforces it.
- **Formatting & Fidelity**: Preserve existing docstrings, typing, license headers, and naming conventions.
- **Cross-Agent Sync**: Keep `CLAUDE.md` and `AGENTS.md` strictly synchronized whenever commands or conventions change.

## Tool-Specific Directives (Claude Code)
- Subagent memory and rules are organized under `.claude/`.
- Refer to `AGENTS.md` for tool-agnostic agent directives.
