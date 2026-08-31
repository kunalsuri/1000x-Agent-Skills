# `.claude/skills/` — project-local skills

Skills placed here are loaded by Claude Code for sessions rooted in this
repository. They are **not** part of the published catalogue: `skills/` is the
catalogue, and nothing here is scanned by `scripts/validate_skills.py`,
`scripts/audit_skill_safety.py`, or `scripts/skill_digest.py`. Those three walk
`skills/` and `.agents/skills/` only, so a vendored upstream skill cannot move a
digest, a grade, or a capability declaration.

## Vendored skills

| Skill | Upstream | Licence |
|---|---|---|
| `skill-creator/` | [`anthropics/skills`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | Apache-2.0 |

### `skill-creator`

Anthropic's authoring skill: it interviews you about the skill you want, drafts
the `SKILL.md`, generates test prompts, runs them with-skill and baseline in
parallel, grades the pairs with a judge subagent, renders a side-by-side review,
and tunes the frontmatter `description` until the skill triggers on the prompts
it should and stays quiet on the ones it should not.

Invoke it by asking for a new skill, or with `/skill-creator`.

**Provenance.** Vendored from the copy shipped with Claude Code, which is ahead
of the public repository by one commit's worth of `scripts/quick_validate.py`
(it rejects a bundle carrying more than one `SKILL.md`). `LICENSE.txt` is taken
from upstream at commit `3b3fad96af16a10759d930941b4520ba0c40edae`
(2026-08-21), because the shipped copy leaves the Apache-2.0 copyright line as
the unfilled `[yyyy] [name of copyright owner]` placeholder. Every other file is
byte-identical to the shipped copy. Re-vendor by copying the directory again,
not by editing in place.

**It does not know this repository's rules.** `skill-creator` emits an
Anthropic-format skill — `name` and `description` frontmatter, and nothing else.
A skill destined for `skills/` additionally needs `version`, an
`attestation.json` carrying a truthful `capabilities` block, `evals/test-cases.json`,
a refreshed `content_digest`, and — under `skills/custom/` — its `.agents/skills/`
mirror. Draft and evaluate with `skill-creator`, then apply this repository's
layer with the templates in `utils/skill-creator/` and re-run
`python scripts/validate_skills.py` and `python scripts/skill_digest.py --update`.
