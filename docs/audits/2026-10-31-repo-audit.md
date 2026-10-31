# Repository audit: 1000x-Agent-Skills against current Agent Skills practice

**Date:** 2026-10-31 · **Scope:** whole repository at `claude/dazzling-rubin-bglozd`, after the author's commit `1d694df` (flattened `skills/`, added `lessons-learnt`) · **Method:** primary-source research (§1), then a review from eight viewpoints (§3), with every gate re-run before and after changes.

> **How to read this.** §2 is the one-page summary. §3 gives findings by viewpoint; each finding is marked **Fixed** (changed in this branch), **Flagged** (needs the author's decision), or **Roadmap**. §4 is a prioritised plan. §5 lists what could not be verified. References use APA style with URLs; only sources actually read are cited as such.

---

## 1. What "current best practice" means here

Read on 2026-10-31 (details and per-fact sources in [`../agent-skills-specs/skill-specs.md`](../agent-skills-specs/skill-specs.md) and [`../lessons-learnt/2026-10-31_2253_recon_agent-skills-spec.md`](../lessons-learnt/2026-10-31_2253_recon_agent-skills-spec.md)):

1. **Portable format.** Six frontmatter keys; custom fields under `metadata`; `compatibility` is a string; body under 500 lines / ~5k tokens; references one level deep (Agent Skills, n.d.-a).
2. **The description is the trigger.** What + when, in the user's language, slightly "pushy", measured with ~20 realistic queries including near-miss negatives and a held-out split (Agent Skills, n.d.-c; Anthropic, n.d.-a).
3. **Skills grounded in real expertise,** with Gotchas sections, defaults instead of menus, and validation loops (Agent Skills, n.d.-b).
4. **Evaluation-first:** with-skill vs. baseline runs, checkable assertions, human review (Agent Skills, n.d.-d; Anthropic, n.d.-a).
5. **Agent-friendly scripts:** non-interactive, `--help`, structured stdout, exit codes, dry-run, bounded output (Agent Skills, n.d.-e).
6. **Distribution through installers:** Claude Code plugin marketplaces (Anthropic, n.d.-c) and the cross-agent `npx skills` CLI (Vercel Labs, n.d.).
7. **Supply-chain caution:** public marketplaces have been found to carry malicious skills (Snyk, 2026, *not read in full*), so provenance and pre-install review matter.

---

## 2. Summary

**Verdict.** The repository's distinctive asset is real: a stdlib-only toolchain that checks what each skill's *code* can do against a declaration, scans the *Markdown* for hidden instructions, and binds attestations to exact bytes. Few public skill collections do any of this. But on the day of the audit the build was red, the catalogue was not installable by any mainstream installer, 7 of 8 skills violated the portable spec, and several "trust" signals (a static *Grade A* badge, six `VERIFIED` attestations with no evidence) were stronger than the evidence. The fixes below make the engineering match the story; the roadmap makes the *skills* as strong as the *tooling*.

| Area | Before | After this branch |
|---|---|---|
| CI gates (validator / audit / digest / pytest) | 17 validator failures, 5 CRITICAL + 4 HIGH audit, ~20 failing tests | All green (see §6) |
| Spec conformance | 7/8 skills non-portable | 8/8 conform; validator enforces it |
| Install routes | Clone + script; README `degit` paths pointed at deleted dirs | Plugin marketplace (validated), `npx skills`, script |
| Trust signals | Static "Grade A" badge; `VERIFIED` without evidence unremarked | Live CI badge; validator warns on evidence-free `VERIFIED` |
| Spec doc freshness | Undated drift risk | `last_verified` stamp, 90-day validator warning |
| Lessons | One free-form note | Indexed, dated, append-only, written with the repo's own skill |

---

## 3. Findings by viewpoint

### 3.1 Build integrity (the restructure)

- **Fixed.** Validator, tests, CI, `CLAUDE.md`/`AGENTS.md` (×2), skill bodies and the allowlist hard-coded `skills/custom/` or `skills/<category>/<skill>`. All moved to `skills/<skill>/`. Keeping the flatten was the right call: it is the layout of `anthropics/skills`, of Claude Code plugins, and the first place `npx skills` looks.
- **Fixed.** Safety-allowlist fingerprints hash the path, so the move un-suppressed 8 reviewed findings. Old-path fingerprints were recomputed and matched before re-pinning; 7 entries for deleted vendored skills were removed.
- **Fixed.** No tool existed for the documented "re-sync the mirror" step. Added `scripts/sync_mirror.py` (dry-run default; declared `workspace-delete`).
- **Fixed.** `.DS_Store` files committed; `test_vendored_skill_parity.py` asserted a deleted directory existed. Rewritten to guard the remaining vendored copy instead.

### 3.2 Specification conformance and portability

- **Fixed.** Top-level `version`/`author`/`tags` in 7 skills (claude.ai uploads and `package_skill.py` reject these), list-valued `compatibility` in 6. Moved to `metadata`, strings throughout.
- **Fixed, and the deeper cause.** The validator *warned when top-level `version:` was missing*, i.e. it rewarded non-portable frontmatter, and `utils/skill-creator/SKILL-TEMPLATE.md` plus the creator prompt taught it. All three corrected; the validator now errors on non-spec keys and warns on Claude Code-only keys.
- **Fixed.** `allowed-tools: [run_command, view_file, …]` lists one client's internal tool names. Elsewhere it pre-approves nothing, or the wrong thing. Removed rather than translated: translating would create pre-approvals nobody reviewed.
- **Fixed.** `preflight-test-engineer` linked references with absolute `file:///skills/custom/...` URLs, which break on install.
- **Flagged.** `utils/Skill-Doctor.html` still generates top-level `version:` (JavaScript, not changed here).

### 3.3 Triggering and descriptions

- **Flagged.** Several descriptions describe implementation instead of user intent. `readme-designer` lists `<br/>`, `---`, ASCII art frames; `saas-app-builder` leads with "Express port 3031". Agents match on what the user *asks for*. Suggested pattern: *"Redesigns a project README so newcomers understand and try the project quickly. Use when the user wants a README written, rewritten, made clearer or more attractive, even if they only say 'the docs are bad'."*
- **Flagged.** Negative trigger prompts are mostly trivially unrelated ("fibonacci", "install nodejs", "TCP vs UDP"). Upstream guidance is explicit that such negatives "test nothing"; near-misses do. `third-party-skill-verifier` and the new `lessons-learnt` are the models to copy.
- **Roadmap.** Nothing runs the trigger sets. A small harness (Claude Code's JSON output; detect a Skill tool call; 3 runs per query; train/validation split) would turn `evals/test-cases.json` from a declaration into a measurement. Anthropic's `skill-creator` already includes a description-optimisation loop; wire it to these files.

### 3.4 Skill bodies and context economy

- **Flagged.** No skill has a `## Gotchas` section, the single highest-value pattern in current guidance. The lessons-learnt notes are a ready source: e.g. "rsync is absent in sandboxes", "fingerprints hash the path".
- **Flagged.** `readme-designer` (270 lines) prescribes a house style (`<br/>` spacing, emoji headings, badges). That is a taste choice, not domain knowledge the agent lacks, and it competes with specialised design skills listed in `other-skills.md`. Consider cutting it to the audit script plus a short rubric, or making the style a selectable `assets/` template.
- **Flagged.** `saas-app-builder` pins framework versions (React 19, Tailwind v4) in the body; guidance says avoid time-sensitive content in skill bodies. Keep versions in `scripts/`/`references/` where `updating-dependencies-and-templates.md` already lives.
- **Roadmap.** References over 100 lines (`python-testing.md`, `typescript-react-testing.md`, `tailwind-v4-shadcn-tokens.md`, `README_TEMPLATE.md`, `THREAT-MODEL.md`) should open with a table of contents.

### 3.5 Evaluation

- **Fixed (one skill).** `lessons-learnt` ships upstream-format `evals/evals.json` with checkable assertions.
- **Flagged.** Six skills are `VERIFIED`; the schema defines that as "multi-platform verified with linked evidence", and no `evidence_url` exists anywhere. Recorded models (`claude-3-7-sonnet`, `gpt-4o`, `gemini-3.7-flash`) are generations old. Recommendation: downgrade to `TESTED` until a with/without-skill run is linked. The validator now warns; the status itself is the author's call.
- **Flagged.** `performance_summary` figures carry their own "illustrative, not measured" caveat. Either measure them (tokens and time are logged by the upstream eval workflow) or drop the fields; a caveated fake number still anchors readers.
- **Roadmap.** Add `evals/evals.json` (2–3 realistic tasks with assertions) to each skill, starting with the three most distinctive.

### 3.6 Security and trust

- **Strength.** AST capability derivation, `CAP-UNPROVEN` for opaque imports, Markdown instruction-surface scanning, fingerprint-pinned allowlist, content digests, a no-dependency CI job, and a verifier with a hard no-network/no-exec/read-only boundary. This is the repository's differentiator; lead with it.
- **Fixed.** Removed the static "Skill Doctor: Grade A" badge (a claim CI never checked) for the live CI badge. Kept the README's "reduce risk, do not make safe" wording.
- **Fixed.** Deleted the nested `docs/AGENTS.md`: agents load nested `AGENTS.md` as instructions, and this one directed them to four skills that do not exist.
- **Roadmap.** The installer copies into `~/.claude/skills`; most users will now install via the marketplace or `npx skills`, which bypass the safety gate. Document the verifier as the pre-install step for *those* routes too (done in README), and consider publishing verifier output per release.
- **Roadmap.** Published scanners have been evaded by truncation, archive indirection and bytecode (per a curated survey list; not independently verified here). Add regression fixtures for each known evasion class to `tests/` so the auditor's coverage claims are tested, as the parity test already does for rule tables.

### 3.7 Distribution and adoption

- **Fixed.** `.claude-plugin/marketplace.json` (passes `claude plugin validate .`), with a test that it lists exactly `skills/`. Users: `/plugin marketplace add kunalsuri/1000x-Agent-Skills`.
- **Fixed.** README documents `npx skills add kunalsuri/1000x-Agent-Skills`; the flat layout is discovered directly.
- **Flagged.** `install_to_agent.py --target cursor` writes `SKILL.md` into `.cursor/rules`; Cursor and Codex skill paths could not be verified (§5). Consider dropping per-client targets in favour of `npx skills`, which maintains those mappings.
- **Roadmap.** Add the repository to skills.sh by installing once via `npx skills`; tag releases (`v1.x`) so plugin users get stable versions; add a 30-second demo GIF of the verifier catching a planted payload.

### 3.8 Documentation, pedagogy and maintenance

- **Fixed.** README rewritten: install first, catalogue with "try saying" prompts drawn from each skill's evals and a plain-language capability column cross-checked against every `attestation.json`, honest enforced-vs-recorded table, student path. The old README (737 lines) linked a non-existent `docs/SPECIFICATIONS.md` and deleted skills.
- **Fixed.** Student Guide's first commands installed skills that do not exist (`resumable-sdd`, `systematic-debugging`). Rewritten with a spec-aligned checklist.
- **Fixed.** Spec summary rewritten against primary sources, with `last_verified` / `next_review_due` and a validator freshness warning; unverified items are listed rather than asserted.
- **Fixed.** Ecosystem tracker: wrong skill-creator link (`anthropic-quickstarts`) and an unsourced "40%+ token efficiency" claim removed; each entry marked read or not re-checked.
- **Fixed.** Lessons-learnt folder indexed; three dated notes written with the repo's own skill.
- **Flagged.** `preflight-test-engineer` metadata has placeholder author `kunal@example.com`; other skills use `kunal.suri@cea.fr`.
- **Consider.** The "1000x" name signals hype to exactly the sceptical, security-minded audience the tooling earns. A subtitle that states the claim plainly (already in the README) mitigates it; renaming is the author's call.

### 3.9 Portfolio: which skills to grow

Distinctive and worth investing in: **`third-party-skill-verifier`** (directly addresses the supply-chain risk in §1.7, with a stronger isolation guarantee than a script you must trust; whether comparable tools exist was not surveyed), **`lessons-learnt`** (turns sessions into durable, agent-readable memory; pairs naturally with Gotchas), **`public-repo-release-review`** (directly useful to researchers releasing code). Commodity, compete with well-known alternatives: `readme-designer`, `saas-app-builder`.

New skills that fit this audience (PhD students, postdocs, mentees) and this repo's trust posture:

| Idea | Why it fits |
|---|---|
| `paper-artifact-release` | Extends release-review for research code: pinned environments, data/licence statements, `CITATION.cff`, reproducibility checklist (e.g. ACM artifact badges). |
| `citation-verifier` | Checks every reference in a draft resolves (DOI/URL) and matches title/authors; flags anything unverifiable rather than "fixing" it. |
| `experiment-logbook` | Records runs, seeds, configs and results as append-only dated files, like `lessons-learnt` for experiments. |
| `skill-trigger-eval` | Runs `evals/test-cases.json` against a real client and writes `evidence_url`-ready results, closing §3.5. |
| `gotchas-harvester` | Mines `docs/lessons-learnt/` for rules and proposes Gotchas additions to the relevant skills. |

---

## 4. Prioritised roadmap

| # | Action | Effort | Impact |
|---|---|---|---|
| 1 | Merge this branch (green build, installable, spec-conformant) | — | High |
| 2 | Downgrade evidence-free `VERIFIED` to `TESTED`, or link evidence | 15 min | High (credibility) |
| 3 | Rewrite descriptions to user intent; replace trivial negatives with near-misses | 1–2 h | High (triggering) |
| 4 | Add `## Gotchas` to every skill, seeded from lessons-learnt | 1–2 h | High |
| 5 | Build `skill-trigger-eval` harness; publish results with `evidence_url` | 1 day | High |
| 6 | `evals/evals.json` for verifier, release-review, preflight | 0.5 day | Medium |
| 7 | Tag `v1.1.0`; demo GIF; list on skills.sh | 2 h | Medium (adoption) |
| 8 | Fix Skill-Doctor.html generator; TOCs on long references | 1 h | Low |
| 9 | Re-verify Codex/Cursor/Antigravity paths from an unrestricted network; update installer | 1 h | Medium |

---

## 5. Not verified

- `agentskills.io`, `developers.openai.com` and `cursor.com` failed DNS resolution from the audit sandbox. The spec was read from its GitHub source instead; Codex, Cursor and Antigravity details remain unverified.
- The Claude Code skills page was partly read through a summariser; limits quoted from it (1,536 characters, 1% budget) are marked † in the spec summary.
- Snyk's ToxicSkills figures, the SkillsBench result, and scanner-evasion claims were seen in search summaries only.
- `tested_platforms` rows in attestations were not re-run.

---

## 6. Gate results after the changes

```text
python scripts/audit_skill_safety.py --strict          -> RESULT: PASS (0 CRITICAL, 0 HIGH; 18 suppressed, all pinned)
python scripts/skill_digest.py --check                 -> 16 skills checked, 0 failed
python scripts/validate_skills.py                      -> 8 scanned, 0 failed (warnings: evidence-free VERIFIED)
python scripts/sync_mirror.py                          -> mirror in sync
python -m pytest                                       -> 457 passed, 2 skipped (pwsh not installed); coverage 71%
python skills/public-repo-release-review/scripts/audit_repo.py --target . --strict -> pass
claude plugin validate .                               -> Validation passed
```

---

## References

Agent Skills. (n.d.-a). *Specification*. Retrieved October 31, 2026, from https://agentskills.io/specification (read from source: https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)

Agent Skills. (n.d.-b). *Best practices for skill creators*. Retrieved October 31, 2026, from https://agentskills.io/skill-creation/best-practices

Agent Skills. (n.d.-c). *Optimizing skill descriptions*. Retrieved October 31, 2026, from https://agentskills.io/skill-creation/optimizing-descriptions

Agent Skills. (n.d.-d). *Evaluating skill output quality*. Retrieved October 31, 2026, from https://agentskills.io/skill-creation/evaluating-skills

Agent Skills. (n.d.-e). *Using scripts*. Retrieved October 31, 2026, from https://agentskills.io/skill-creation/using-scripts

Anthropic. (n.d.-a). *Skill authoring best practices*. Claude Platform Docs. Retrieved October 31, 2026, from https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

Anthropic. (n.d.-b). *Skills* [Documentation page; title not recorded]. Claude Code Docs. Retrieved October 31, 2026, from https://code.claude.com/docs/en/skills

Anthropic. (n.d.-c). *Plugin marketplaces* [Documentation page; title not recorded]. Claude Code Docs. Retrieved October 31, 2026, from https://code.claude.com/docs/en/plugin-marketplaces

Anthropic. (n.d.-d). *anthropics/skills* [Computer software]. GitHub. Retrieved October 31, 2026, from https://github.com/anthropics/skills

Snyk. (2026). *ToxicSkills* [Blog post; full title not recorded]. https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/ — **not read in full; title and summary from search results only.**

Vercel Labs. (n.d.). *skills* [Computer software]. GitHub. Retrieved October 31, 2026, from https://github.com/vercel-labs/skills
