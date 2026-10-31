# `skills/` — the catalogue

One directory per skill, at `skills/<skill-name>/`. This flat layout matches
[`anthropics/skills`](https://github.com/anthropics/skills), the Claude Code
plugin format (`<plugin>/skills/<name>/SKILL.md`) and the first place
`npx skills add` looks, so the repository installs cleanly with all three.

Every directory here is **original work**. Vendored upstream skills do not
belong in `skills/`; the one we use, `skill-creator`, lives in
[`.claude/skills/`](../.claude/skills/).

## What every skill must ship

| File | Why | Checked by |
|---|---|---|
| `SKILL.md` | Spec-conformant frontmatter (`name`, `description`, optional `license`, `compatibility`, `metadata`, `allowed-tools`); custom keys such as `version` go under `metadata`. Body under 500 lines. | `scripts/validate_skills.py` |
| `attestation.json` | Declared `capabilities`, provenance, honest status, `content_digest`. | `scripts/audit_skill_safety.py`, `scripts/skill_digest.py` |
| `evals/test-cases.json` | Trigger prompts: realistic positives and near-miss negatives. | `scripts/validate_skills.py` |
| `evals/evals.json` (recommended) | Output-quality evals in the [agentskills.io format](https://agentskills.io/skill-creation/evaluating-skills): `prompt`, `expected_output`, `assertions`. | reviewed by hand; run with `skill-creator` |

After any edit: `python scripts/skill_digest.py --update`, review the diff,
then `python scripts/sync_mirror.py --write` to refresh `.agents/skills/`.

## Catalogue

The authoritative list, with what each skill's code is allowed to do, is in
the [root README](../README.md#-the-skills). The Claude Code marketplace
manifest is [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json);
CI fails if either drifts from this directory.

## Proposing a skill

Start from the templates in [`utils/skill-creator/`](../utils/skill-creator/)
and the [Student & Contributor Guide](../docs/STUDENT-GUIDE.md), then open a
pull request adding `skills/<skill-name>/`.
