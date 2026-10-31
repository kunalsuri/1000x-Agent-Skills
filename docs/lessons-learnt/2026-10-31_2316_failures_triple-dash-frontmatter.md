# Failures 2026-10-31: a `---` inside a description breaks naive SKILL.md parsers

**Written:** 2026-10-31 23:16 UTC. **Read when:** you write or edit a skill `description`, or a client or validator says a skill's frontmatter is truncated or invalid.

## TL;DR
- `readme-designer`'s description contained the text `thematic dividers ---`. Full YAML parsers read it fine. The spec's reference validator, `skills-ref`, splits `SKILL.md` on the first `---` in the file, so it would have cut the frontmatter mid-sentence.
- Found by reading `skills-ref`'s source before adding it to CI (running it locally was blocked by the sandbox).

## Rules we now follow
1. **Never put `---` inside any frontmatter value.** Some parsers split on the first `---`, not on a line that is only `---`. *(check: `python scripts/validate_skills.py` now errors on it)*
2. **Pin every external validator to an exact version in CI.** `skills-ref` is pinned to a commit SHA and Claude Code to a version, so an upstream change cannot alter what CI accepts. *(evidence: `spec-conformance` job in `.github/workflows/ci.yml`)*
3. **Read an external tool's source when you cannot run it.** It found this bug before CI did.

## What broke (one line each)
- (M) `readme-designer` description held `---` → parsers that split on the first `---` truncate it → description rewritten around user intent; validator check added with tests.

## How to re-check
- `python scripts/validate_skills.py` : 0 Failed.
- CI job "Upstream validators (skills-ref, claude plugin validate)" : green.

## Open items
- [ ] Not verified locally: `skills-ref` and `claude plugin validate` in CI on a clean runner (no login). The first CI run is the test.
