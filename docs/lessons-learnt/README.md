# Lessons learnt

What this project has learned, written so that the next session (agent or human) starts from what is already known.

- **How to add:** ask your agent to "write the lessons learnt" — the [`lessons-learnt`](../../skills/lessons-learnt/SKILL.md) skill does the rest.
- **File names:** `YYYY-MM-DD_HHMM_<kind>_<topic>.md` (time from `date`, never guessed).
- **Rules:** important things only (would it change what someone does next time?); no secrets; **append-only** — never edit a dated file, write a new one that says "supersedes …". Only this index is edited in place.

| Kind | Contains |
|---|---|
| `session` | Decisions and the reasons behind them. |
| `failures` | What broke, the root cause, and the rules we now follow. |
| `recon` | Facts from outside the repo, each with source, check date and re-check date. |

## Index (newest first)

| Date | File | Summary |
|---|---|---|
| 2026-10-31 | [failures: triple-dash-frontmatter](./2026-10-31_2316_failures_triple-dash-frontmatter.md) | A `---` inside a description truncates frontmatter for `skills-ref`; validator now catches it; external validators pinned in CI. |
| 2026-10-31 | [failures: flatten-layout](./2026-10-31_2253_failures_flatten-layout.md) | Moving skills to `skills/<name>/` broke every gate; the template taught non-spec frontmatter; 7 rules distilled. |
| 2026-10-31 | [recon: agent-skills-spec](./2026-10-31_2253_recon_agent-skills-spec.md) | Verified spec keys, eval formats, Claude Code extensions, marketplace and `npx skills` facts, with sources; what could not be verified. |
| 2026-10-31 | [session: repo-audit](./2026-10-31_2253_session_repo-audit.md) | Decisions from the full repository audit and why. |
| 2026-09-14 | [notes-lessons-learnt](./notes-lessons-learnt.md) | Legacy free-form notes (pre-dates the dated-file format): building `cross-platform-dev-scripts`. |

## Checklist for the next session
- Run `python scripts/validate_skills.py` first; a `[SPEC FRESHNESS]` warning means `docs/agent-skills-specs/` needs re-verifying.
- After moving or adding any skill: `python scripts/sync_mirror.py --write`, `python scripts/skill_digest.py --update`, and add it to `README.md` and `.claude-plugin/marketplace.json`.
