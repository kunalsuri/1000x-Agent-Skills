<div align="center">

# 🧩 1000x Agent Skills

**Original Agent Skills for coding agents. Every skill declares what its code can do, and CI checks that claim against the code on every commit.**

[![CI](https://github.com/kunalsuri/1000x-Agent-Skills/actions/workflows/ci.yml/badge.svg)](https://github.com/kunalsuri/1000x-Agent-Skills/actions/workflows/ci.yml)
[![Agent Skills spec](https://img.shields.io/badge/format-Agent%20Skills%20open%20spec-8A2BE2)](https://agentskills.io/specification)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-6366f1)](#-install)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](./scripts/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-f59e0b)](./LICENSE)

[Install](#-install) · [Skills](#-the-skills) · [Why this repo](#-why-this-repo-is-different) · [Verify it yourself](#-verify-it-yourself) · [Write your own](#-write-your-own-skill) · [Docs](#-docs)

</div>

> [!NOTE]
> **Work in progress.** The tooling and CI gates are real and tested (450+ tests). Per-model trigger results in each `attestation.json` are *recorded* once by a person, not re-run automatically. See [Enforced vs. recorded](#enforced-vs-recorded).

---

## 🚀 Install

Skills follow the [Agent Skills open specification](https://agentskills.io/specification): a folder with a `SKILL.md`. Any client that supports the spec can load them. Pick the route that matches your agent.

**Claude Code: plugin marketplace (recommended).** Installs all skills and keeps them updatable.

```text
/plugin marketplace add kunalsuri/1000x-Agent-Skills
/plugin install 1000x-agent-skills@1000x-agent-skills
```

Skills installed this way are namespaced, e.g. `/1000x-agent-skills:lessons-learnt`.

**Any agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI, …): the `skills` CLI.** Requires Node.js 22.20+.

```bash
npx skills add kunalsuri/1000x-Agent-Skills --list                 # see what is available
npx skills add kunalsuri/1000x-Agent-Skills --skill third-party-skill-verifier
```

Add `-g` to install for your user instead of the current project, and `-a claude-code` (or `codex`, etc.) to target one agent.

**From a clone, with a safety gate.** The local installer refuses any skill that fails the safety audit, and previews by default.

```bash
git clone https://github.com/kunalsuri/1000x-Agent-Skills.git && cd 1000x-Agent-Skills
python scripts/install_to_agent.py --target claude --all            # preview, writes nothing
python scripts/install_to_agent.py --target claude --all --apply    # install to ~/.claude/skills
```

> [!TIP]
> Before installing **anyone's** skills, including these, run them through [`third-party-skill-verifier`](./skills/third-party-skill-verifier/SKILL.md). Independent audits of public skill marketplaces have found skills carrying malicious instructions and code ([Snyk, 2026](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/)).

---

## 🧰 The skills

| Skill | What it does | Try saying | Code can… |
|---|---|---|---|
| [`third-party-skill-verifier`](./skills/third-party-skill-verifier/SKILL.md) | Statically reads **every file** in someone else's skill and reports what its code can actually do, what runs without being invoked, and what was hidden from review. Never fetches, writes or executes. | *"I downloaded this skill from GitHub, can you check it before I install it?"* | read files only |
| [`public-repo-release-review`](./skills/public-repo-release-review/SKILL.md) | Pre-publication audit: secret leaks, governance files (`SECURITY.md`, `CITATION.cff`, …), link integrity, hygiene. Scaffolds missing files. | *"Audit this codebase before we push it to public GitHub."* | write in workspace |
| [`preflight-test-engineer`](./skills/preflight-test-engineer/SKILL.md) | Analyses a Python or TypeScript/React codebase, scaffolds a `tests/` suite, runs a multi-stage pre-flight. | *"Create a test suite for this codebase and verify it before we run the app."* | run processes, write in workspace |
| [`lessons-learnt`](./skills/lessons-learnt/SKILL.md) | Turns what a session taught you into dated, append-only notes an agent *and* a human can act on next time. | *"Write the lessons learnt from this session."* | nothing (instructions only) |
| [`multi-agent-docs`](./skills/multi-agent-docs/SKILL.md) | Scaffolds and keeps `CLAUDE.md`, `AGENTS.md`, `.claude/` and `.agents/` in sync so every agent gets the same project rules. | *"Our AGENTS.md and CLAUDE.md have drifted. Sync them."* | write in workspace |
| [`cross-platform-dev-scripts`](./skills/cross-platform-dev-scripts/SKILL.md) | Generates matching `scripts/linux` and `scripts/win` setup/test scripts (uv with venv fallback, no sudo, no pipe-to-shell) and checks their parity. | *"Add one-command dev-setup and dev-test scripts for Windows and Linux."* | run processes, write in workspace |
| [`readme-designer`](./skills/readme-designer/SKILL.md) | Redesigns a README for scannability and audits it (hierarchy, links, badges, callouts, Mermaid). | *"Make this README clearer and more inviting."* | write in workspace |
| [`saas-app-builder`](./skills/saas-app-builder/SKILL.md) | Scaffolds a full-stack SaaS app (React 19, Tailwind v4, shadcn/ui, Express) with a four-harness test suite. | *"Create a full-stack SaaS app with tests."* | write in workspace |

The **Code can…** column is the skill's `capabilities` block from its `attestation.json`, in plain words. CI fails if the code exceeds it. Each skill's attestation status (`DRAFT` / `TESTED` / `VERIFIED`) is in the same file; read its `tested_platforms` rows and caveats before relying on it.

---

## 💡 Why this repo is different

A skill is code plus Markdown that an agent obeys. Most skill collections ask you to trust both. This one gives you machine-checked evidence for the parts that can be checked, and labels the rest honestly.

| | Typical skill collection | This repository |
|---|---|---|
| What the code can do | Undeclared | Declared per skill (`network`, `process_execution`, `dynamic_code_execution`, `filesystem`) and **checked against the AST on every commit** |
| Hidden instructions in Markdown | Not scanned | Scanned: invisible/Tags-block Unicode, bidi overrides, directive HTML comments, encoded payloads, pipe-to-shell, credential exfiltration |
| Silent edits after review | Undetectable | Each attestation is bound to a SHA-256 `content_digest` of the skill's exact bytes |
| Trigger quality | Unmeasured | Positive and near-miss negative prompts in `evals/` for every skill |
| Spec conformance | Assumed | Frontmatter validated against the open spec by our validator **and** the spec's reference validator `skills-ref`; marketplace manifest checked by `claude plugin validate` |
| Third-party skills | Install and hope | A dedicated verifier skill with a no-network, no-exec, read-only guarantee |

### Enforced vs. recorded

| | **Enforced** | **Recorded** |
|---|---|---|
| Checked by | CI, on every push and pull request | A person, once, on a given day |
| Covers | Declared capabilities, content digests, attestation schema, spec conformance (ours and `skills-ref`), plugin manifest, mirror and catalogue parity, the test suite | `tested_platforms` rows, `performance_summary` figures |
| If it is wrong | The build fails | Nothing happens automatically |
| How to trust it | Re-run the command yourself; it is deterministic | Read the caveat, check the date, re-run it |

A `PASS` with no `evidence_url` is a claim, not a proof. The validator now warns when a skill is marked `VERIFIED` without one.

---

## ✅ Verify it yourself

The audit tooling uses the Python standard library only, so you can run it on a copy you downloaded without installing anything first. CI runs these same commands on a bare interpreter to keep that true.

```bash
python scripts/audit_skill_safety.py --strict   # undeclared capabilities, hidden instructions
python scripts/skill_digest.py --check          # content still matches its attestation
python scripts/validate_skills.py               # spec conformance, schema, evals, catalogue parity
```

Reviewed false positives live in [`docs/safety-allowlist.json`](./docs/safety-allowlist.json). Each is pinned to a content fingerprint and a written reason, so editing the covered line makes the finding come back for a fresh review. Suppressed findings are still printed.

**Full local CI in one command:**

| | Linux / macOS | Windows (PowerShell) |
|---|---|---|
| Set up once | `./scripts/linux/dev-setup.sh` | `.\scripts\win\dev-setup.ps1` |
| Run every check | `./scripts/linux/dev-test.sh` | `.\scripts\win\dev-test.ps1` |

**Staying current.** A weekly workflow ([`weekly-maintenance.yml`](./.github/workflows/weekly-maintenance.yml)) checks every version pin, runs the full suite against the *latest* test dependencies, and fails if the spec summary is over 90 days old. To apply updates locally: `python scripts/check_updates.py --write && python -m pytest`.

`dev-setup` creates `.venv/` using [uv](https://docs.astral.sh/uv/) when available, otherwise `venv` + `pip`. It never touches anything outside the repository, needs no `sudo`, and never pipes a downloaded script into a shell. `dev-test` runs the CI steps in CI's order and prints full output only for failing steps.

---

## ✍️ Write your own skill

This repository is used for teaching. The fastest path for students and mentees:

1. **Start from a real task, not a blank page.** Do the task once with an agent, then capture the steps, corrections and gotchas. Generic "best practices" make weak skills ([agentskills.io best practices](https://agentskills.io/skill-creation/best-practices)).
2. **Draft with `skill-creator`.** In Claude Code, ask for a new skill or run `/skill-creator` (vendored in [`.claude/skills/`](./.claude/skills/)). It drafts, runs with-skill vs. baseline evals and tunes the description.
3. **Add this repo's layer:** `metadata.version`, an honest `attestation.json`, `evals/test-cases.json` with near-miss negatives. Templates: [`utils/skill-creator/`](./utils/skill-creator/).
4. **Gate it:**
   ```bash
   python scripts/skill_digest.py --update   # re-attest: review the diff first
   python scripts/sync_mirror.py --write     # refresh the .agents/skills mirror
   python scripts/validate_skills.py && python -m pytest
   ```
5. **Record what you learned** with the [`lessons-learnt`](./skills/lessons-learnt/SKILL.md) skill. Past lessons: [`docs/lessons-learnt/`](./docs/lessons-learnt/).

Step-by-step walkthrough with a submission checklist: [Student & Contributor Guide](./docs/STUDENT-GUIDE.md).

---

## 📚 Docs

| Document | What it is |
|---|---|
| [Agent Skills spec summary](./docs/agent-skills-specs/skill-specs.md) | The open spec plus Claude Code extensions, distribution and script design, with a **last-verified timestamp**. The validator warns when it is over 90 days old. |
| [Repository audit, 2026-10-31](./docs/audits/2026-10-31-repo-audit.md) | Findings and recommendations from a full review against current best practice. |
| [Lessons learnt](./docs/lessons-learnt/) | Dated, append-only record of what this project has learned. |
| [Attestation spec](./docs/ATTESTATION-SPEC.md) | The `attestation.json` format and what each field does and does not prove. |
| [Evaluation framework](./docs/EVALUATION-FRAMEWORK.md) | How trigger and output evals are designed. |
| [Ecosystem tracker](./docs/ECOSYSTEM-TRACKER.md) | Specs, clients and research worth following. |
| [General prompts](./docs/prompts/general-prompts.md) | Reusable prompts, including the spec re-verification prompt. |
| [Other skills worth knowing](./other-skills.md) | Third-party skills and plugins we point students to (verify before installing). |

---

## 🗂️ Repository layout

```text
skills/<skill>/            canonical skills: SKILL.md, attestation.json, evals/, scripts/, references/
.agents/skills/<skill>/    byte-identical mirror for clients that read .agents/skills (CI-enforced)
.claude-plugin/            Claude Code plugin marketplace manifest
.claude/skills/            vendored skill-creator, loaded by Claude Code in this repo only
scripts/                   validator, safety auditor, digest tool, mirror sync, installer
docs/                      spec summary, schemas, allowlist, lessons learnt, audits
tests/                     pytest suite for the tooling and every skill script
```

---

## 🤝 Contributing, security and citation

- [Security policy](./SECURITY.md) · [Code of conduct](./CODE_OF_CONDUCT.md) · [Support](./SUPPORT.md) · [Collaborators](./COLLABORATORS.md)
- Agent instructions for this repo: [`CLAUDE.md`](./CLAUDE.md) and [`AGENTS.md`](./AGENTS.md) (kept in sync).
- Cite via [`CITATION.cff`](./CITATION.cff) or [`CITATIONS.md`](./CITATIONS.md):

```bibtex
@software{suri2026_1000x_agent_skills,
  author    = {Kunal Suri},
  title     = {1000x-Agent-Skills: Capability-Declared, Attested and Evaluated Agent Skills},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/kunalsuri/1000x-Agent-Skills}
}
```

Licensed under [Apache-2.0](./LICENSE). The checks described here reduce risk; they do not make any skill safe, and the licence's warranty disclaimer applies.
