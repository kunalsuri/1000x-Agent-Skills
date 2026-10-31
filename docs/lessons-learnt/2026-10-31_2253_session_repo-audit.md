# Session 2026-10-31: full repository audit against current agent-skills practice

**Written:** 2026-10-31 22:53 UTC. **Read when:** you want to know why the repo looks the way it does after October 2026, or you plan the next round of improvements.

## TL;DR
- Kept the flat `skills/<name>/` layout the author introduced and made every tool, test and doc agree with it.
- Made the repo installable in one line two ways (plugin marketplace, `npx skills`).
- Spec doc now carries a `last_verified` stamp that the validator enforces (warns after 90 days).
- Full findings and the prioritised roadmap: [`../audits/2026-10-31-repo-audit.md`](../audits/2026-10-31-repo-audit.md).

## What happened / decisions
- Kept the flatten — because it matches anthropics/skills, Claude Code plugins and `npx skills`. Rejected: restoring `skills/custom/` (would fight every installer).
- Validator: non-spec top-level keys are **errors**; Claude Code-only keys are **warnings** — because the first break claude.ai uploads, the second only reduce portability.
- Removed `allowed-tools` from all skills — because the values (`run_command`, `view_file`, …) are one client's internal tool names; in other clients they pre-approve nothing or the wrong thing. Rejected: translating them to Claude Code names (would grant pre-approval nobody reviewed).
- Did **not** change any attestation status — because that is the author's sign-off; added a warning instead.
- Deleted `docs/AGENTS.md` — nested AGENTS.md files are loaded as instructions; this one named four non-existent skills.
- Added `scripts/sync_mirror.py` (declared `workspace-delete` in `docs/capability-declarations.json`) — the mirror rule had no tool.
- Adopted the upstream `evals/evals.json` format for the new `lessons-learnt` skill alongside the repo's `test-cases.json`.

## Open items
- [ ] See the roadmap in the audit report.
