# Anthropic Skills

Upstream skills published by Anthropic in
[`anthropics/skills`](https://github.com/anthropics/skills), vendored here unmodified
for reference. They are kept in the catalogue so the shape of a first-party skill can
be read next to this repository's own, not because they have been evaluated here.

| Skill | Upstream commit | Licence | Attestation |
|---|:---:|:---:|:---:|
| [`skill-creator`](./skill-creator/SKILL.md) | `3b3fad9` | Apache-2.0 | `DRAFT` |
| [`mcp-builder`](./mcp-builder/SKILL.md) | `3b3fad9` | Apache-2.0 | `DRAFT` |

## What "vendored" means here

- **Unmodified.** Every file is upstream's, byte for byte. The only additions are
  `attestation.json` and `evals/test-cases.json`, which this repository's tooling
  requires and which upstream does not ship. Re-vendor by replacing the directory,
  never by editing in place, then re-run `python scripts/skill_digest.py --update`.
- **`DRAFT`, deliberately.** The schema reserves `TESTED` for a skill evaluated on at
  least one model with a passing trigger suite. Neither of these has been. Their
  `tested_platforms` rows say `NOT_RUN` and their eval prompts describe an intended
  trigger surface that has never been measured.
- **Capabilities are derived, not claimed.** Each `attestation.json` records what
  `scripts/audit_skill_safety.py` derives from the source. Where the declaration is
  *stronger* than the auditor can prove — as with `mcp-builder`, whose network and
  subprocess access live behind the `anthropic` and `mcp` SDKs — the stronger value is
  declared and the resulting `CAP-OVERDECLARED` warning is pinned in
  `docs/safety-allowlist.json` with its reasoning.
- **Scanned before landing.** Both bundles were run through
  `skills/custom/third-party-skill-verifier`, and the verdict is quoted in each
  `attestation.json`: `mcp-builder` came back `no_known_findings`, `skill-creator` came
  back `needs_review` with six HIGH findings that are resolved in writing there.

## The licence gate

Only Apache-2.0 upstream skills are eligible. As of commit `3b3fad9`, 14 of the 19
upstream skills carry an Apache-2.0 `LICENSE.txt`. The four document skills — `docx`,
`pdf`, `pptx`, `xlsx` — are source-available under Anthropic's own terms
(`© Anthropic, PBC. All rights reserved`) and **must not** be redistributed here.
`doc-coauthoring` ships no licence file, and the upstream repository has no root
`LICENSE` to fall back on, so its status is unresolved. Check `LICENSE.txt` in the
skill directory itself before vendoring anything new; the repository README's blanket
"many skills here are open source" is not a per-skill grant.
