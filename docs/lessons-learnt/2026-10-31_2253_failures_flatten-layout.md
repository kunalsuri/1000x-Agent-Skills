# Failures 2026-10-31: flattening skills/ broke every gate, and the template taught non-spec frontmatter

**Written:** 2026-10-31 22:53 UTC. **Read when:** you move, rename or add a skill directory, change frontmatter rules, or CI goes red right after a restructure.

## TL;DR
- Moving `skills/custom/*` to `skills/*` broke 17 validator checks, ~20 tests, CI paths and 18 pinned safety exemptions at once. The move itself was right; the tooling hard-coded the old depth in many places.
- 7 of 8 skills had non-spec frontmatter (top-level `version`/`author`/`tags`, list `compatibility`, Antigravity-only `allowed-tools`). Root cause: `utils/skill-creator/SKILL-TEMPLATE.md` and the creator prompt taught it, and the validator *rewarded* it.
- Six attestations say `VERIFIED` with zero `evidence_url`, contradicting the schema's own definition.

## Rules we now follow
1. **After any move under `skills/`, grep for the old path before running anything.** Paths were hard-coded in tests, CI, CLAUDE.md, AGENTS.md (x2), skill bodies and the allowlist. *(check: `grep -rn "skills/custom" --exclude-dir=.git .` must print nothing)*
2. **Re-pin a moved allowlist entry only after proving the flagged text is unchanged.** The auditor's fingerprint hashes `check|path|snippet`, so a pure move invalidates it by design. We recomputed the old-path fingerprints in a scratch copy and matched all 8 before re-pinning. *(evidence: `docs/safety-allowlist.json` reasons now say "Re-pinned 2026-10-31")*
3. **Fix the template, not just the instances.** A validator that only checks output lets a bad template keep producing bad skills. *(evidence: `utils/skill-creator/SKILL-TEMPLATE.md`)*
4. **Never claim compatibility you have not tested.** A first-draft `compatibility` string said skills were "exercised with Claude Code, Antigravity, Cursor and Codex"; nothing backed it, so it was removed before commit. *(check: `grep -h "^compatibility" skills/*/SKILL.md`)*
5. **Use `scripts/sync_mirror.py --write`, not `rsync`/`cp`.** `rsync` is absent from the sandbox; the mirror rule had no tool behind it. *(check: `python scripts/sync_mirror.py` exits 0 when in sync)*
6. **Dogfood the release skill on this repo.** `public-repo-release-review` caught broken links in `skills/README.md` and a nested `docs/AGENTS.md` that pointed at skills which do not exist. *(check: `python skills/public-repo-release-review/scripts/audit_repo.py --target . --strict`)*
7. **A nested `AGENTS.md` is instructions, not documentation.** Some agents load it when working in that folder. Delete stale ones rather than leaving them as "reference".

## What broke (one line each)
- (H) Validator layout check → hard-coded `skills/<category>/<skill>` → now `skills/<skill>`; tests updated.
- (H) Validator warned when top-level `version:` was *missing* → rewarded non-spec frontmatter → now errors on non-spec keys, reads `metadata.version`.
- (H) 18 allowlist entries → path in fingerprint → 7 dead `skills/anthropic/*` entries removed, 8 re-pinned after content proof.
- (M) README, `skills/README.md`, Student Guide linked to deleted or never-existing skills (`resumable-sdd`, `systematic-debugging`) → rewritten.
- (M) `preflight-test-engineer` used `file:///skills/custom/...` links → break on install → relative `references/...`.
- (M) Six skills `VERIFIED` without evidence → validator now warns; status left for the author to decide.
- (L) `.DS_Store` files committed → removed (already gitignored).

## How to re-check
- `python scripts/validate_skills.py` : must end with 0 Failed; warnings list the VERIFIED-without-evidence skills.
- `python scripts/audit_skill_safety.py --strict` : RESULT PASS.
- `python scripts/skill_digest.py --check && python scripts/sync_mirror.py` : both exit 0.
- `python -m pytest -q` : all green.

## Open items
- [ ] Author: downgrade the six `VERIFIED` attestations to `TESTED`, or attach `evidence_url`s.
- [ ] Author: replace placeholder `kunal@example.com` in `preflight-test-engineer` metadata.
- [ ] `utils/Skill-Doctor.html` still generates top-level `version:` frontmatter. Not verified in a browser.
