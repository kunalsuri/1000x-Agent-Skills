<div align="center">

# 🧩 1000x Agent Skills

### *The Capability-Declared, Attested & Evaluated Skills Suite for Autonomous AI Coding Agents*

<br/>

[![Spec: Agent Skills Open Spec](https://img.shields.io/badge/Specification-Agent%20Skills%20Open%20Spec-8A2BE2?style=for-the-badge&logo=codeforces&logoColor=white)](https://agentskills.io/specification)
[![Multi-Agent Ready](https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Antigravity%20%7C%20Cursor%20%7C%20Codex-6366f1?style=for-the-badge&logo=anthropic&logoColor=white)](#-multi-agent-ecosystem-support)
[![Skill Doctor: Grade A](https://img.shields.io/badge/Skill%20Doctor-Health%20Grade%20A-10b981?style=for-the-badge&logo=shield&logoColor=white)](./utils/Skill-Doctor.html)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](./scripts/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-f59e0b?style=for-the-badge&logo=apache&logoColor=white)](./LICENSE)

<br/>

[**🩺 Launch Skill Doctor**](./utils/Skill-Doctor.html) &nbsp;•&nbsp; [**⚡ Quickstart & CLI**](#-quickstart--cli) &nbsp;•&nbsp; [**🧩 Skills Catalog**](#-skills-catalog) &nbsp;•&nbsp; [**📚 Docs Hub**](./docs/) &nbsp;•&nbsp; [**🎓 Student Guide**](./docs/STUDENT-GUIDE.md) &nbsp;•&nbsp; [**🧠 Creator Lab**](./utils/skill-creator/)

<br/>

</div>

---

<div align="center">

**⚡⚡NOTE: Work in Progress (WIP)**

Limited human-in-the-loop verification is currently applied. Output stability is expected to improve after the first pre-release.

</div>

---

<br/>

### ⚡ Instant Install (1-Liner)

Install any production skill directly into your project in **one command** — zero cloning required:

<br/>

```bash
# 🟣 Install to Anthropic Claude Code (.claude/skills)
npx degit kunalsuri/1000x-Agent-Skills/skills/custom/multi-agent-docs .claude/skills/multi-agent-docs

# 🔵 Install to Google Antigravity / Cursor / OpenAI Codex (.agents/skills)
npx degit kunalsuri/1000x-Agent-Skills/skills/custom/multi-agent-docs .agents/skills/multi-agent-docs
```

<br/>

---

<br/>

## 💡 What is 1000x-Agent-Skills?

Most agent prompt repositories provide static text snippets, unverified copy-paste prompts, or monolithic system instructions. In real-world software engineering, these create **severe bottlenecks**:

- ❌ **Context Exhaustion**: Massive system prompts eat into the model's effective context window before coding even begins.
- ❌ **Instruction Drift**: Different agents (Claude, Antigravity, Cursor) drift out of synchronization as rules are edited haphazardly.
- ❌ **Hallucinations & Tool Breakage**: Un-attested workflows fail silently when invoked on live CLI tools or LLM backends.
- ❌ **False Positive Triggers**: Overly broad descriptions cause agents to load heavy instructions for unrelated user tasks.

<br/>

**`1000x-Agent-Skills`** solves this with a **standardized, production-grade procedural knowledge library and developer toolchain** engineered for autonomous AI developer environments (**Claude Code**, **Google Antigravity**, **Cursor**, and **OpenAI Codex**).

<br/>

> [!IMPORTANT]
> **Core Architectural Philosophy: Progressive Disclosure**  
> Every skill operates on a 4-tier progressive discovery model. The agent loads **only ~100 tokens** at startup, expanding into full workflows and specialized references **on-demand** only when the user's intent matches the skill's declared trigger.

<br/>

```mermaid
flowchart TD
    subgraph AgentBoot ["🚀 1. Agent Startup (Ultra-Lightweight)"]
        A["Scan YAML Frontmatters<br/><b>(~100 tokens / skill budget)</b>"]
    end

    subgraph TriggerMatch ["🎯 2. Precision Intent Matching"]
        B{"User Prompt Matches<br/><b>Skill Trigger Description?</b>"}
    end

    subgraph SkillExec ["⚡ 3. On-Demand Procedural Execution"]
        C["Load Full <b>SKILL.md</b> (&le; 500 lines)"]
        D["Execute Deterministic Tooling<br/><b>(e.g., scaffold.py, audit_repo.py)</b>"]
        E["Run Semantic LLM Synthesis<br/><b>& Parity Validation Steps</b>"]
    end

    subgraph DeepContext ["📖 4. Deep Domain Context (Loaded As Needed)"]
        F["Read <b>references/</b>, Schemas & Guidelines<br/><i>(Loaded on-demand only if required)</i>"]
    end

    AgentBoot --> TriggerMatch
    TriggerMatch -- "No Match" --> G["<b>Skill remains inert</b><br/>(Zero token waste / Zero distraction)"]
    TriggerMatch -- "Match Found" --> SkillExec
    SkillExec --> DeepContext
```

<br/>

---

<br/>

## ⚖️ Architectural Comparison

| Dimension | ❌ Traditional Monolithic Prompts | 🌟 1000x-Agent-Skills Architecture |
|---|---|---|
| **Context Overhead** | Heavy (5,000 – 20,000+ tokens loaded continuously) | **Ultra-lightweight (~100 tokens at boot, full body on-demand)** |
| **Verification & Proof** | None (Untested static markdown text) | **Machine-enforced attestation**: declared capabilities checked against the code by AST analysis, and a SHA-256 `content_digest` binding each attestation to exact bytes — both re-verified on every commit |
| **Trigger Evaluation** | Blind activation / high false triggers | **Positive and negative prompt datasets** (`evals/test-cases.json`), present and schema-checked for every skill. Automated scoring against a live model is not yet wired up — see [Enforced vs. recorded](#-enforced-vs-recorded) |
| **Multi-Agent Parity** | Fragmented per IDE / out-of-sync instructions | **Synchronized across Claude Code, Antigravity, Cursor & Codex** |
| **Deterministic Tooling** | Unassisted LLM hallucinations | **Integrated Python CLI engines + semantic LLM verification** |
| **Quality Control** | Manual inspection | **Interactive `Skill-Doctor.html`, a pytest suite with 400+ tests, and a CI safety audit that blocks undeclared capabilities and hidden instructions** |

<br/>

---

<br/>

## 🔍 Enforced vs. Recorded

Claims in this repository fall into two categories, and it matters which is which:

| | **Enforced** | **Recorded** |
|---|---|---|
| Checked by | CI, on every push and pull request | A person, once, on a given day |
| Covers | Declared capabilities, content digests, attestation schema, agent-doc parity, the test suite | `tested_platforms` rows, `performance_summary` figures |
| If it is wrong | The build fails | Nothing happens automatically |
| How to trust it | Re-run the command yourself — it is deterministic | Read the caveat, check the date, re-run it |

Recorded claims carry their own `currency_caveat` and `methodology_caveat`
fields stating plainly what they do and do not cover. A `PASS` with no
`evidence_url` is a claim, not a proof, and is labelled as such.

<br/>

### ✅ Verify it yourself

You do not have to take any of this on trust, and you do not have to install
anything first — the audit tooling is stdlib-only by design:

```bash
# Does any skill do something it did not declare? Is anything hidden in the Markdown?
python scripts/audit_skill_safety.py --strict

# Does every skill's content still match the attestation it was granted?
python scripts/skill_digest.py --check

# Does every skill conform to the published attestation schema?
python scripts/validate_skills.py
```

Run them against a copy you downloaded, not just against this repository.
CI runs the same three commands on a bare interpreter with no third-party
packages installed, so the "no dependencies needed to audit" claim is itself
tested rather than asserted. (Or skip typing all three by hand — see
[One-command setup & test](#one-command-setup-test-recommended) below.)

<br/>

**What the safety audit actually checks.** A skill has two attack surfaces:

- **Its scripts**, which run on your machine. Analysed structurally with
  Python's `ast` module — a `subprocess.run(...)` call cannot hide from an AST
  walk the way it can from a skim-read of a 2,000-line file. Every skill
  declares `network`, `process_execution`, `dynamic_code_execution` and
  `filesystem` levels in its `attestation.json`, and the build fails if the
  code exceeds its declaration.
- **Its Markdown**, which is injected into an agent's context and *becomes
  instructions*. This surface is the sneakier of the two and is rarely
  scanned: invisible Unicode (including the Tags block used to smuggle whole
  instructions), bidirectional overrides, directive-bearing HTML comments,
  encoded payloads, pipe-to-shell one-liners, and credential-exfiltration
  patterns.

Reviewed false positives live in [`docs/safety-allowlist.json`](./docs/safety-allowlist.json),
each pinned to a content fingerprint and a written justification. Edit the
line an exemption covers and the fingerprint changes, the exemption stops
applying, and the finding resurfaces for a fresh review. Suppressed findings
are still printed — suppressed, never hidden.

<br/>

### 🖥️ One-command setup & test (recommended)

Running the three commands above by hand, plus the release audit and the
pytest suite, is exactly what `.github/workflows/ci.yml` does on every push.
Two small scripts wrap that whole sequence into one command each — one pair
for Linux/macOS, one for Windows — so a local "all green" predicts a green
CI run instead of hoping for one.

<table>
<tr><th></th><th>Linux / macOS</th><th>Windows (PowerShell)</th></tr>
<tr>
<td><b>Set up once</b></td>
<td><pre><code>./scripts/linux/dev-setup.sh</code></pre></td>
<td><pre><code>.\scripts\win\dev-setup.ps1</code></pre></td>
</tr>
<tr>
<td><b>Run every check</b></td>
<td><pre><code>./scripts/linux/dev-test.sh</code></pre></td>
<td><pre><code>.\scripts\win\dev-test.ps1</code></pre></td>
</tr>
</table>

`dev-setup` creates `.venv/` at the repository root — or, if one already
exists, just brings its packages up to date — so it is always safe to
re-run. It uses [**uv**](https://docs.astral.sh/uv/) when available (an
order-of-magnitude faster resolver/installer than pip, and the closest
thing Python currently has to a "state of the art" package manager) and
falls back to the standard library's `venv` + `pip` automatically when uv
isn't installed. Nothing here is required for the repository's own audit
tooling to work — that stays stdlib-only — uv only speeds up installing the
three *test* dependencies in `requirements-dev.txt`.

`dev-test` then runs, in the same order CI does, cheapest and most
security-relevant first:

```text
1000x-Agent-Skills — local test report
repo: /path/to/1000x-Agent-Skills

▶ Skill safety audit... ✓ Skill safety audit (0.4s)
▶ Content digest check... ✓ Content digest check (0.1s)
▶ Skill Doctor validator... ✓ Skill Doctor validator (0.2s)
▶ Pre-flight release audit... ✓ Pre-flight release audit (0.2s)
▶ Pytest suite (coverage >= 60%)... ✓ Pytest suite (coverage >= 60%) (6.8s)

────────────────────────────────────────────────────────────
 Summary
────────────────────────────────────────────────────────────
 PASS  Skill safety audit                            0.4s
 PASS  Content digest check                          0.1s
 PASS  Skill Doctor validator                        0.2s
 PASS  Pre-flight release audit                      0.2s
 PASS  Pytest suite (coverage >= 60%)                6.8s
────────────────────────────────────────────────────────────
 5/5 checks passed in 7.7s

This matches what CI checks — safe to push.
```

If a step fails, the full output of *only* that step is printed underneath
the summary — no need to re-run anything to see what broke.

**Useful flags**, identical on both platforms:

| Flag | Linux/macOS | Windows | Effect |
|---|---|---|---|
| Rebuild the environment from scratch | `dev-setup.sh --clean` | `dev-setup.ps1 -Clean` | Deletes and recreates `.venv/` |
| Skip uv even if installed | `dev-setup.sh --no-uv` | `dev-setup.ps1 -NoUv` | Forces the `venv` + `pip` path |
| Install uv first, then use it | `dev-setup.sh --with-uv` | `dev-setup.ps1 -WithUv` | A normal `pip install uv` — never a piped remote script |
| Run only matching tests | `dev-test.sh -k EXPR` | `dev-test.ps1 -K EXPR` | Forwards to `pytest -k`, skips the audit steps |
| Show output for passing steps too | `dev-test.sh -v` | `dev-test.ps1 -Verbose2` | Default only shows output for failures |
| Fail instead of auto-installing | `dev-test.sh --no-setup` | `dev-test.ps1 -NoSetup` | `dev-test` normally runs `dev-setup` once for you if `.venv/` doesn't exist yet |

**What these scripts do NOT do, by design**, matching the trust posture of
everything else in this repository: they never touch anything outside the
repo (the only thing created or modified is `.venv/`), they never require
`sudo` or an elevated/Administrator prompt, and they never pipe a
downloaded script into a shell — `--with-uv`/`-WithUv` is a plain
`pip install`, the one place either script installs anything beyond the
pinned contents of `requirements-dev.txt`. Both scripts are plain,
readable shell/PowerShell with no obfuscation — read them before running
them, the same advice that applies to any script from any repository.

A dedicated test
([`tests/unit/test_dev_scripts.py`](./tests/unit/test_dev_scripts.py)) keeps
the two platforms honest with each other: it fails if the Linux and Windows
variants ever run a different number of checks, a different set of checks,
or checks in a different order — the same drift `multi-agent-docs` already
guards against for `CLAUDE.md`/`AGENTS.md`.

<br/>

---

<br/>

## 🎯 The 3 Core Pillars

Every skill in this repository is governed by three non-negotiable engineering checks, each re-run on every commit:

<br/>

```
┌─────────────────────────────────┐      ┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│          1. DECLARED            │      │          2. ATTESTED            │      │          3. EVALUATED           │
│   Strict YAML Frontmatter       │ ───> │   Empirical Proof & Logs        │ ───> │   Intent Precision & Recall     │
│   Schema, Tools & Token Budgets │      │   Multi-Model Resilience Matrix │      │   Automated Test-Case Suite     │
└─────────────────────────────────┘      └─────────────────────────────────┘      └─────────────────────────────────┘
```

<br/>

| Pillar | File / Artifact | What Is Checked & Technical Specification |
|---|---|---|
| **1. 📋 Declared** | [`SKILL.md`](./skills/custom/multi-agent-docs/SKILL.md) | **Strict YAML frontmatter interface** (`name`, `version`, `description`, `allowed-tools`, `compatibility`, `tags`). Concise body limit ($\le 500$ lines) containing actionable procedural instructions. |
| **2. 🛡️ Attested** | [`attestation.json`](./docs/ATTESTATION-SPEC.md) | Two things, kept distinct. **Enforced:** a `capabilities` declaration checked against the code by AST analysis, plus a `content_digest` that breaks if any file changes after attestation. **Recorded:** per-model run reports (Claude, Gemini and GPT backends — see each skill's `attestation.json` for the exact models), each carrying its own currency caveat. |
| **3. 🧪 Evaluated** | [`evals/test-cases.json`](./docs/EVALUATION-FRAMEWORK.md) | **Positive and negative trigger datasets** for every skill, validated for structure and minimum size on every CI run. Precision $\ge 85\%$ and recall $\ge 90\%$ are the **design targets** these datasets exist to measure; scoring them against a live model is not yet automated, so no measured figure is claimed. |

<br/>

---

<br/>

## 🤖 Multi-Agent Ecosystem Support

A single unified skill library engineered to seamlessly empower all autonomous AI developer platforms:

<br/>

| Agent Platform | Directives / Config | Native Integration Path | Target Directory |
|---|---|---|---|
| **🟣 Anthropic Claude Code** | `CLAUDE.md` + `.claude/` | Native `skills/` declaration & CLI execution | `~/.claude/skills/` or `.claude/skills/` |
| **🔵 Google Antigravity** | `AGENTS.md` + `.agents/` | Global plugin root & local workspace skills | `~/.gemini/config/skills/` or `.agents/skills/` |
| **🟢 Cursor Agent** | `.cursorrules` + `.cursor/` | Rule injection & progressive context prompts | `.cursor/rules/` or workspace rules |
| **🔴 OpenAI Codex / Canvas** | `AGENTS.md` root prompt | Capability injection & workflow scripts | Active workspace root |

<br/>

---

<br/>

## 🧩 Skills Catalog

Skills are curated into **Custom** (cross-platform, multi-agent workflows), **Anthropic** (Claude-focused workflows), and **Google** (Antigravity & Gemini workflows).

<br/>

### 🟢 Production-Ready & Attested Skills

<br/>

| Skill & Link | Version | Status | Highlights & Capabilities | Trigger Context |
|---|:---:|:---:|---|---|
| [**`multi-agent-docs`**](./skills/custom/multi-agent-docs/SKILL.md) | `v1.1.0` | `🟢 Checks passing` | • Deterministic project scaffolding (`scaffold.py`)<br/>• Automated multi-agent parity validation (`validate_sync.py`)<br/>• Synchronizes `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.agents/` | **Use when** configuring a repository for multi-agent workflows (Claude Code, Antigravity, Cursor, Codex) or when resolving instruction drift. |
| [**`preflight-test-engineer`**](./skills/custom/preflight-test-engineer/SKILL.md) | `v1.0.0` | `🟢 Checks passing` | • Codebase AST & stack analyzer (`analyze_codebase.py`)<br/>• Deterministic `/tests/` test suite generator (`scaffold_tests.py`)<br/>• 4-stage pre-flight runner (`run_preflight.py`) | **Use when** asked to test a codebase before running, scaffold a test suite into `/tests/`, verify test coverage, or execute pre-flight sanity checks. |
| [**`public-repo-release-review`**](./skills/custom/public-repo-release-review/SKILL.md) | `v1.0.0` | `🟢 Checks passing` | • Pre-flight public release audit engine (`audit_repo.py`)<br/>• Deep secret leak scanner & governance verification<br/>• Scaffolding for `SECURITY.md`, `COLLABORATORS.md`, `CITATION.cff` | **Use when** reviewing a codebase before public release, auditing repository security and governance, or preparing for public launch. |
| [**`readme-designer`**](./skills/custom/readme-designer/SKILL.md) | `v1.0.0` | `🟢 Checks passing` | • Markdown visual design, spacing (`<br/>`) & structure<br/>• Automated diagnostic quality auditor (`audit_readme.py`)<br/>• Scaffolding engine for modern READMEs (`scaffold_readme.py`) | **Use when** creating, redesigning, formatting, modernizing, improving readability of, or polishing a project README, documentation, or landing page. |
| [**`saas-app-builder`**](./skills/custom/saas-app-builder/SKILL.md) | `v1.0.0` | `🟢 Checks passing` | • Full-stack SaaS scaffolding engine (`scaffold_saas.py`)<br/>• React 19, Tailwind CSS v4, shadcn/ui, single-port Express (3031)<br/>• Integrated 4-harness test suite & scaffold auditor (`audit_scaffold.py`) | **Use when** asked to create a SaaS app, scaffold a full-stack monorepo, or build a modern web application with integrated tests. |
| [**`third-party-skill-verifier`**](./skills/custom/third-party-skill-verifier/SKILL.md) | `v1.0.0` | `🟢 Checks passing` | • Static verification of skills written by **other people** (`verify_skill_bundle.py`)<br/>• Reads **every file in the bundle**, including the ones `SKILL.md` never mentions<br/>• Grades auto-executing files, shipped bytecode, hidden Unicode, and capability dishonesty<br/>• Findings carry **OWASP Agentic Skills Top 10** identifiers<br/>• Never fetches, never writes, never executes | **Use when** you have downloaded, cloned, or been sent a skill and need to know what it can do before installing it, or when re-checking an installed skill after an update. |

<br/>

> [!TIP]
> **Explore Category Indexes**:
> - 📂 [**Custom Skills Index (`skills/custom/`)**](./skills/custom/README.md)
> - 📂 [**Anthropic Skills Index (`skills/anthropic/`)**](./skills/anthropic/README.md)
> - 📂 [**Google Skills Index (`skills/google/`)**](./skills/google/README.md)

<br/>

---

<br/>

## 🩺 Built-In Developer Tooling & Diagnostics

<br/>

### 1. 🩺 Skill Doctor & Health Suite (`Skill-Doctor.html`)

An interactive, zero-dependency offline web application built with vanilla web technologies to **lint, benchmark, score, format, and generate compliant skills**.

<br/>

- **📝 Live SKILL.md Inspector & Linter**: Real-time YAML parser, regex validation, header token estimator ($\le 150$), line tracker ($\le 500$), and 1-click **Auto-Fix** & **Copy**.
- **✨ Interactive Skill Builder**: Visual form builder to author compliant `SKILL.md` packages with structured steps and instant downloads.
- **📐 Open Specification & Format Guide**: Interactive reference covering specification rules, attestation schemas, and evaluation metrics.
- **🚀 Zero Setup Required**: Open [`utils/Skill-Doctor.html`](./utils/Skill-Doctor.html) in any modern browser!

<br/>

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🩺 SKILL DOCTOR: Health Score: 100 [GRADE A - PRODUCTION READY]            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [✓] YAML Frontmatter Valid          [✓] Header Token Budget: ~85 (<=150)   │
│  [✓] Trigger Context Explicit        [✓] Body Line Budget: 58 (<=500)       │
│  [✓] Attestation Schema Verified     [✓] Intent Benchmark Evals Present     │
└─────────────────────────────────────────────────────────────────────────────┘
```

<br/>

### 2. 🧠 Skill Creator Lab (`/utils/skill-creator/`)

A guided co-design prompt framework for authoring compliant agent skills alongside Claude or Antigravity:

- 📄 [`SKILL-CREATOR-PROMPT.md`](./utils/skill-creator/SKILL-CREATOR-PROMPT.md): Step-by-step LLM co-design prompt.
- 📄 [`SKILL-TEMPLATE.md`](./utils/skill-creator/SKILL-TEMPLATE.md): Clean boilerplate template.
- 📄 [`attestation-template.json`](./utils/skill-creator/attestation-template.json): Attestation boilerplate schema.
- 📄 [`evals-template.json`](./utils/skill-creator/evals-template.json): Intent evaluation test-case boilerplate.

<br/>

---

<br/>

## ⚡ Quickstart & CLI

<br/>

### 1. 1-Liner Skill Installation via `npx`

Install any skill directly into your project without cloning this repository:

<br/>

```bash
# 🟣 Install multi-agent-docs to Claude Code
npx degit kunalsuri/1000x-Agent-Skills/skills/custom/multi-agent-docs .claude/skills/multi-agent-docs

# 🔵 Install public-repo-release-review to Antigravity / Cursor
npx degit kunalsuri/1000x-Agent-Skills/skills/custom/public-repo-release-review .agents/skills/public-repo-release-review
```

<br/>

### 2. Local Python Installer CLI (`scripts/install_to_agent.py`)

If you have cloned the repository locally, use the cross-platform Python installer CLI:

<br/>

```bash
# 🚀 Install all skills to Google Antigravity global config (~/.gemini/config/skills)
python scripts/install_to_agent.py --target antigravity --all

# 🚀 Install all skills to Claude Code global config (~/.claude/skills)
python scripts/install_to_agent.py --target claude --all

# 🚀 Install a specific skill to Cursor (.cursor/rules)
python scripts/install_to_agent.py --target cursor --skill multi-agent-docs
```

<br/>

### 3. Run the Automated CI Validation Suite (`scripts/validate_skills.py`)

Verify YAML frontmatter, line limits, attestation schemas, and evaluation datasets across all repository skills:

<br/>

```bash
python scripts/validate_skills.py
```

<br/>

```text
========================================================================
 🩺 [SKILL DOCTOR] Specification & Health Diagnostic Suite
========================================================================
[PASS] [custom/multi-agent-docs] -> Health Score: 100/100 [Grade A+]
    ℹ️  frontmatter_tokens: 140 | body_lines: 59 | attestation_status: VERIFIED
        | capabilities: network=none,process_execution=none,
          dynamic_code_execution=none,filesystem=workspace-write
        | content_digest: sha256:440e88cf64b3... | eval_prompts_count: 3 pos / 2 neg
[PASS] [custom/preflight-test-engineer] -> Health Score: 100/100 [Grade A+]
[PASS] [custom/public-repo-release-review] -> Health Score: 100/100 [Grade A+]
[PASS] [custom/readme-designer] -> Health Score: 100/100 [Grade A+]
[PASS] [custom/saas-app-builder] -> Health Score: 100/100 [Grade A+]
[PASS] [custom/third-party-skill-verifier] -> Health Score: 100/100 [Grade A+]
------------------------------------------------------------------------
 [README AUDIT] ✅ README.md catalog and skills/ tree match in both directions.
========================================================================
 Summary: 6 skills scanned | 6 Passed | 0 Warnings | 0 Failed
========================================================================
```

<br/>

### 4. Execute Flagship Skill Engines Directly

<br/>

```bash
# 🛠️ Scaffold multi-agent documentation (.claude/, .agents/, CLAUDE.md, AGENTS.md)
python skills/custom/multi-agent-docs/scripts/scaffold.py --target .

# 🔄 Validate that CLAUDE.md and AGENTS.md are in exact parity
python skills/custom/multi-agent-docs/scripts/validate_sync.py --target .

# 🔒 Run pre-flight release audit for public GitHub readiness
python skills/custom/public-repo-release-review/scripts/audit_repo.py --target . --strict

# 📝 Scaffold missing open-source governance files (SECURITY.md, COLLABORATORS.md, CITATION.cff)
python skills/custom/public-repo-release-review/scripts/scaffold_governance.py --target . --collaborators-mode solo

# 🎨 Audit Markdown / README visual hierarchy, spacing, badges & link integrity
python skills/custom/readme-designer/scripts/audit_readme.py --target README.md --strict

# 🛡️ Audit every skill for undeclared capabilities and hidden instructions
python scripts/audit_skill_safety.py --strict --show-info

# 🔗 Verify (or re-bind) the content digest that anchors each attestation
python scripts/skill_digest.py --check
python scripts/skill_digest.py --update

# 🧪 Run the full test suite with a coverage floor
python -m pytest --cov=scripts --cov=skills --cov=utils --cov-fail-under=60

# 📦 Preview an install (writes nothing), then apply it
python scripts/install_to_agent.py --target claude --all
python scripts/install_to_agent.py --target claude --all --apply

# ✨ Scaffold an ultra-modern README boilerplate from scratch
python skills/custom/readme-designer/scripts/scaffold_readme.py --name "My Project" --tagline "Awesome AI Project"
```

<br/>

---

<br/>

## 📁 Repository Architecture

<br/>

```text
1000x-Agent-Skills/
├── .agents/                      # Antigravity / Cursor / Codex agent configuration
│   ├── skills/                   # Byte-identical mirror of skills/custom (CI-enforced parity)
│   └── AGENTS.md                 # Agent operating directives (mirrors root AGENTS.md)
├── .claude/                      # Claude Code project configuration
│   └── README.md                 # What belongs here, and what deliberately does not
├── .github/                      # GitHub issue forms, PR template, CODEOWNERS & CI
│   ├── ISSUE_TEMPLATE/           # bug_report.yml, feature_request.yml
│   ├── workflows/                # ci.yml (safety audit, digests, validation, tests)
│   ├── CODEOWNERS                # Review ownership, incl. every trust-critical path
│   ├── dependabot.yml            # Weekly GitHub Actions & pip update PRs
│   └── PULL_REQUEST_TEMPLATE.md  # Standard pull request checklist
├── docs/                         # Specification & Engineering Documentation Hub
│   ├── schemas/
│   │   └── attestation.schema.json  # JSON Schema every attestation.json is validated against
│   ├── safety-allowlist.json     # Reviewed safety exemptions, each pinned to a content hash
│   ├── capability-declarations.json # Declared capabilities for repo tooling users execute
│   ├── SPECIFICATIONS.md         # Open Agent Skills format and schema guidelines
│   ├── ATTESTATION-SPEC.md       # Attestation schema, enforced vs recorded claims
│   ├── EVALUATION-FRAMEWORK.md   # Precision / recall benchmark dataset design
│   ├── ECOSYSTEM-TRACKER.md      # Living directory of agent specs, papers & tooling
│   ├── STUDENT-GUIDE.md          # Step-by-step student authoring & assignment guide
│   └── AGENTS.md                 # Multi-agent operating rules & directives
├── scripts/                      # CLI Maintenance, Audit & Deployment Tools (stdlib-only)
│   ├── validate_skills.py        # Skill Doctor: frontmatter, schema, digests, evals
│   ├── audit_skill_safety.py     # Capability audit + hidden-instruction scan
│   ├── skill_digest.py           # Computes and verifies attestation content digests
│   ├── install_to_agent.py       # Installer for Claude, Antigravity & Cursor (previews by default)
│   ├── linux/                    # One-command dev environment for Linux/macOS
│   │   ├── dev-setup.sh          # Create or update .venv (uv, or venv+pip fallback)
│   │   └── dev-test.sh           # Run the full CI-equivalent suite, print a report
│   └── win/                      # One-command dev environment for Windows (PowerShell)
│       ├── dev-setup.ps1         # Create or update .venv (uv, or venv+pip fallback)
│       └── dev-test.ps1          # Run the full CI-equivalent suite, print a report
├── skills/                       # Production Skills Catalog
│   ├── custom/                   # Cross-agent & workflow skills
│   │   ├── multi-agent-docs/     # Synchronized multi-agent documentation skill
│   │   ├── preflight-test-engineer/ # Codebase analysis & test-suite scaffolding
│   │   ├── public-repo-release-review/ # Pre-flight public release review & audit
│   │   ├── readme-designer/      # README & documentation visual design skill
│   │   ├── saas-app-builder/     # Full-stack SaaS application scaffolder
│   │   ├── third-party-skill-verifier/ # Static verifier for skills you did not write
│   │   └── README.md             # Custom skills index & requirements
│   ├── anthropic/                # Claude-focused engineering workflows
│   │   └── README.md
│   └── google/                   # Antigravity & Gemini-focused workflows
│       └── README.md
├── tests/                        # Pytest suite (400+ tests) for all tooling & skill scripts
│   ├── unit/                     # Validators, safety auditor, digests, every skill script
│   ├── smoke/                    # Harness sanity: env isolation & network blocking
│   ├── fixtures/                 # Deterministic test data factories
│   └── conftest.py               # Hermetic harness: real outbound-network guard
├── utils/                        # Developer Lab & Diagnostics
│   ├── Skill-Doctor.html         # Interactive offline web-app linter & health dashboard
│   ├── skill_doctor.py           # CLI wrapper around scripts/validate_skills.py
│   └── skill-creator/            # Co-design prompt, starters & schema templates
├── AGENTS.md                     # Root multi-agent directives (Antigravity/Cursor/Codex)
├── CLAUDE.md                     # Root Claude Code configuration & guidelines
├── CITATION.cff                  # Machine-readable software citation metadata (CFF)
├── CITATIONS.md                  # Human-readable citation formats (BibTeX, APA, IEEE)
├── CODE_OF_CONDUCT.md            # Contributor Covenant v2.1 Code of Conduct
├── COLLABORATORS.md              # Solo-maintainer & contribution policy
├── LICENSE                       # Apache 2.0 Open Source License
├── pytest.ini                    # Test discovery, markers & strict config
├── requirements-dev.txt          # Pinned CI/test dependencies (never needed to audit a skill)
├── README.md                     # Repository overview & quickstart
├── SECURITY.md                   # Security vulnerability disclosure & triage policy
└── SUPPORT.md                    # Support channels & discussion guidelines
```

<br/>

---

<br/>

## 🛠️ How to Author & Submit a Skill

<br/>

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Contributor / Student
    participant Lab as Skill Creator Lab
    participant Doc as Skill Doctor (HTML/CLI)
    participant Repo as 1000x-Agent-Skills

    Dev->>Lab: 1. Ideate workflow with SKILL-CREATOR-PROMPT.md
    Lab-->>Dev: 2. Generate SKILL.md, attestation.json & evals/
    Dev->>Doc: 3. Lint & score in Skill Doctor (Health Grade >= 85)
    Dev->>Doc: 4. Run `python scripts/validate_skills.py`
    Dev->>Repo: 5. Open Pull Request to `skills/<category>/<skill-name>/`
```

<br/>

1. **💡 Ideate**: Identify a recurring, high-value developer workflow or domain-specific expertise.
2. **✍️ Draft with LLM**: Use [`utils/skill-creator/SKILL-CREATOR-PROMPT.md`](./utils/skill-creator/SKILL-CREATOR-PROMPT.md) with Claude Code or Antigravity.
3. **🩺 Lint in Skill Doctor**: Open [`utils/Skill-Doctor.html`](./utils/Skill-Doctor.html) and achieve a **Grade A Health Score ($\ge 85$)**.
4. **🛡️ Attest & Evaluate**:
   - Provide realistic trigger prompts in `evals/test-cases.json`.
   - Record tested model backends and resilience metrics in `attestation.json`.
5. **🚀 Verify & Submit**:
   - Run `python scripts/validate_skills.py` locally.
   - Submit a clean Pull Request into `skills/<category>/<your-skill-name>/`.

<br/>

---

<br/>

## 📚 Ecosystem & Specifications Hub

<br/>

| Document | Description | Key Focus Area |
|---|---|---|
| 📖 [**Agent Skills Specification (`docs/SPECIFICATIONS.md`)**](./docs/SPECIFICATIONS.md) | Official Open Agent Skills specification | Frontmatter syntax, parameters, token budgets |
| 🛡️ [**Attestation Specification (`docs/ATTESTATION-SPEC.md`)**](./docs/ATTESTATION-SPEC.md) | Multi-model proof schemas & audit levels | LLM execution logs, resilience matrix |
| 📊 [**Evaluation Framework (`docs/EVALUATION-FRAMEWORK.md`)**](./docs/EVALUATION-FRAMEWORK.md) | Trigger precision & recall benchmarking | Test-case design, synthetic datasets |
| 🌐 [**Ecosystem Tracker (`docs/ECOSYSTEM-TRACKER.md`)**](./docs/ECOSYSTEM-TRACKER.md) | Living directory of agent protocols & papers | MCP, tool standards, research papers |
| 🎓 [**Student & Contributor Guide (`docs/STUDENT-GUIDE.md`)**](./docs/STUDENT-GUIDE.md) | Practical step-by-step authoring walkthrough | Coursework submission checklist & rubric |

<br/>

---

<br/>

## 📜 Open-Source Governance, Security & Citations

<br/>

- 🛡️ **[Security Policy (`SECURITY.md`)](./SECURITY.md)**: Vulnerability disclosure channels, threat triage guidelines, and responsible disclosure timeline.
- 👥 **[Collaborator Guidelines (`COLLABORATORS.md`)](./COLLABORATORS.md)**: Project maintainership status, issue protocol, and contribution policy.
- 📑 **[Citation Metadata (`CITATION.cff`)](./CITATION.cff)** & **[Citations Guide (`CITATIONS.md`)](./CITATIONS.md)**: Academic and software citations (BibTeX, APA, IEEE).
- 🤝 **[Code of Conduct (`CODE_OF_CONDUCT.md`)](./CODE_OF_CONDUCT.md)**: Contributor Covenant v2.1 standards.
- 💬 **[Support Channels (`SUPPORT.md`)](./SUPPORT.md)**: Help resources, discussions, and issue guidelines.

<br/>

```bibtex
@software{suri2025_1000x_agent_skills,
  author       = {Kunal Suri},
  title        = {1000x-Agent-Skills: The Capability-Declared, Attested & Evaluated Skills Suite for Autonomous AI Coding Agents},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/kunalsuri/1000x-Agent-Skills}
}
```

<br/>

---

<br/>

## 📄 License

This project is licensed under the **Apache 2.0 License** — see the [LICENSE](./LICENSE) file for complete details.

<br/>

<div align="center">

**Built with ❤️ for the Autonomous AI Developer Community**

[⭐ Star on GitHub](https://github.com/kunalsuri/1000x-Agent-Skills) • [🐛 Report an Issue](https://github.com/kunalsuri/1000x-Agent-Skills/issues) • [🤝 Submit a Skill](https://github.com/kunalsuri/1000x-Agent-Skills/pulls)

</div>
