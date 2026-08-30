# 🛡️ Attestation Specification — Proven Capability

In **1000x-Agent-Skills**, every production skill is **Attested**.

An attestation is only worth something if it can fail. A JSON file saying
`"attestation_status": "VERIFIED"` is a string anybody can type, and it keeps
saying VERIFIED no matter what happens to the code afterwards. So this
specification separates two very different kinds of statement, and marks
clearly which is which:

| | **Enforced** | **Recorded** |
|---|---|---|
| What it is | Checked mechanically on every push and pull request | A human's report of something they observed once |
| Examples | `capabilities`, `content_digest`, schema conformance | `tested_platforms`, `performance_summary` |
| If it is wrong | CI fails | Nothing happens automatically |
| How to trust it | Re-run the command yourself; it is deterministic | Read the caveats, check the date, re-run it |

Both belong in an attestation. Confusing one for the other is what makes a
badge misleading.

---

## 📄 Schema

The machine-readable schema is [`docs/schemas/attestation.schema.json`](./schemas/attestation.schema.json),
and every `attestation.json` references it in its `$schema` field.
`scripts/validate_skills.py` validates against it on every run.

```json
{
  "$schema": "https://raw.githubusercontent.com/kunalsuri/1000x-Agent-Skills/main/docs/schemas/attestation.schema.json",
  "skill_name": "readme-designer",
  "version": "1.0.0",
  "attestation_status": "VERIFIED",

  "capabilities": {
    "network": "none",
    "process_execution": "none",
    "dynamic_code_execution": "none",
    "filesystem": "workspace-write"
  },
  "capabilities_rationale": "audit_readme.py is read-only; scaffold_readme.py writes a README into the target repository.",

  "attested_by": "Kunal Suri",
  "attestation_date": "2026-08-29",

  "tested_platforms": [
    {
      "platform": "Claude Code",
      "model": "claude-3-7-sonnet",
      "status": "PASS",
      "version_tag": "1.0.0",
      "notes": "Verified README audit scoring and scaffold generation.",
      "evidence_url": "https://github.com/…/runs/…",
      "currency_caveat": "Not re-run since attestation_date."
    }
  ],

  "performance_summary": {
    "success_rate_percent": 100,
    "average_token_consumption": 1450,
    "recovery_resilience": "High",
    "methodology_caveat": "Illustrative, not the output of a repeatable measurement."
  },

  "security_audit": {
    "tool": "scripts/audit_skill_safety.py",
    "method": "AST capability analysis of every script plus an instruction-surface scan of every Markdown file.",
    "last_run_date": "2026-08-30",
    "last_run_result": "PASS",
    "reproduce": "python scripts/audit_skill_safety.py --skill readme-designer --strict"
  },

  "provenance": {
    "source_type": "original",
    "origin_url": "https://github.com/kunalsuri/1000x-Agent-Skills",
    "license": "Apache-2.0"
  },

  "content_digest": "sha256:e71bd85f50fe7d523dd267d9a8b6636ca87182e9992eeafd7428aed3f10f01c4"
}
```

---

## 🔐 `capabilities` — enforced

Declares what the skill's code is permitted to do. Each value is a rung on a
ladder from least to most powerful.

| Field | Values | Meaning of the lowest value |
|---|---|---|
| `network` | `none`, `outbound` | No module granting network access is imported anywhere in the skill. |
| `process_execution` | `none`, `subprocess` | The skill cannot spawn a process. |
| `dynamic_code_execution` | `none`, `eval` | No `eval`/`exec`/`compile`/`__import__`, no `pickle`, `marshal` or `importlib`. |
| `filesystem` | `read-only`, `workspace-write`, `workspace-delete`, `unrestricted` | The skill only reads. `unrestricted` must be declared by anything writing outside the target workspace. |

`scripts/audit_skill_safety.py` derives these same values structurally from
the source with Python's `ast` module and **fails the build when the code
exceeds its declaration**. Declaring more than you use is allowed and merely
warns; using more than you declared is a hard failure. Any capability above
its lowest value requires a `capabilities_rationale` explaining why.

This is what makes "capability-declared" a property of the repository rather
than a slogan: a skill claiming `network: none` that imports `urllib` cannot
be merged.

---

## 🔗 `content_digest` — enforced

A SHA-256 over a canonical manifest of every file in the skill except
`attestation.json` itself:

```
<posix relative path>  <sha256 of file bytes>\n
```

sorted by path. Edit a SKILL.md, a script, or a reference doc after
attestation and the digest no longer matches, so `scripts/validate_skills.py`
fails. Re-attesting becomes a deliberate act with a reviewable diff, rather
than something that silently never happens.

```bash
python scripts/skill_digest.py --check                     # verify every skill
python scripts/skill_digest.py --update                    # re-bind after a reviewed change
python scripts/skill_digest.py --print skills/custom/NAME  # show the manifest
```

The digest is path-independent, so anyone who copies a skill out of this
repository can recompute it and compare against the published value.

---

## 🧾 `tested_platforms` and `performance_summary` — recorded

These describe what a person observed on a particular day. Nothing re-checks
them, so read them with that in mind:

- **`status: "PASS"` with no `evidence_url` is a claim, not a proof.** Prefer
  linking a transcript or CI run.
- **`version_tag`** records which version of the skill the row was run
  against. A row without one predates any subsequent change.
- **`currency_caveat`** states plainly what a row no longer covers. A PASS
  from three versions ago is not a statement about today's code.
- **`methodology_caveat`** is required whenever a figure in
  `performance_summary` is illustrative rather than measured. A bare number
  implies a rigour it may not have; say so instead.

---

## 🎖️ Attestation status levels

| Status | Badge | Definition |
|---|---|---|
| **DRAFT** | 🟡 Draft | Authored and passes the linter, pending multi-model evaluation. |
| **TESTED** | 🔵 Tested | Evaluated on at least one primary model with a passing trigger test suite. |
| **VERIFIED** | 🟢 Verified | Multi-platform verified. The schema requires at least one `tested_platforms` entry — VERIFIED must name what verified it. |
| **DEPRECATED** | 🔴 Deprecated | Superseded by newer workflows or updated agent runtime APIs. |

Note what these levels do **not** measure: they say nothing about safety. A
skill's safety posture is the `capabilities` block and the CI audit, both of
which apply at every status level including DRAFT.

---

## ✅ Verifying a skill yourself

None of this requires trusting the maintainer, or installing anything — the
tooling is stdlib-only by design:

```bash
python scripts/audit_skill_safety.py --strict   # capabilities and hidden instructions
python scripts/skill_digest.py --check          # content matches its attestation
python scripts/validate_skills.py               # schema, frontmatter, evaluation coverage
```

Run them against a copy you downloaded, not just against this repository.
