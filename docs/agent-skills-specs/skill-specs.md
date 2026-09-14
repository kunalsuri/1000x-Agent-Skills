---
title: "Agent Skills Specification & Format Guidelines"
specification_standard: "https://agentskills.io/specification"
specification_version: "1.1.0"
status: "active"
created: "2026-09-09"
last_updated: "2026-09-14"
last_audit_date: "2026-09-14"
metadata_manifest: "./skill-specs.meta.yaml"
ecosystem:
  canonical_standard: "Agent Skills Open Specification (agentskills.io)"
  catalog_profile: "1000x-Agent-Skills Repository Architecture"
---

# 📐 Agent Skills Specification & Format Guidelines

> **Document Status**: Active Standard &middot; **Last Audited**: 2026-09-14 &middot; **Machine-Readable Metadata**: [`skill-specs.meta.yaml`](./skill-specs.meta.yaml)  
> **Canonical Standard**: [Agent Skills Open Specification (agentskills.io)](https://agentskills.io/specification)  
> **Supported Platforms**: Anthropic Claude Code, Google Antigravity, Cursor, OpenAI Codex / ChatGPT, GitHub Copilot / VS Code, JetBrains Junie, OpenHands, and 35+ ecosystem agents.

---

## 1. Directory Structure

The open standard defines an Agent Skill as a self-contained, portable folder containing instructions, executable code, and contextual resources.

### Canonical Skill Structure (Universal Open Standard)

A universal, cross-platform skill directory conforms to the following layout:

```text
<skill-name>/
├── SKILL.md                 # Required: Metadata frontmatter + procedural workflow
├── scripts/                 # Optional: Executable code (Python, Bash, JS) run on-demand
├── references/              # Optional: In-depth technical documentation, schemas, domain guides
├── assets/                  # Optional: Static resources, output templates, lookup tables
└── evals/                   # Optional: Evaluation test cases (evals/evals.json)
    └── evals.json
```

### Repository Profile Structure (1000x-Agent-Skills Catalog)

Inside this repository (`1000x-Agent-Skills`), production skills are organized into catalog partitions with safety and attestation bindings:

```text
skills/<category>/<skill-name>/
├── SKILL.md                 # Required: Frontmatter + core procedural workflow
├── attestation.json         # Repository Profile: Cryptographic digest + capability bounds
├── evals/                   # Repository Profile: Test harness evaluation dataset
│   ├── test-cases.json      # Repo-internal test cases (validated by scripts/validate_skills.py)
│   └── evals.json           # Standard Agent Skills evaluation suite (skill-creator format)
├── scripts/                 # Executable utility code & automated auditing scripts
├── references/              # Extended references, schemas, and API documentation
└── assets/                  # Static assets and formatting templates
```

> [!NOTE]
> `attestation.json` and `skills/<category>/` partitioning are **repository-profile governance extensions** enforced by `scripts/validate_skills.py` and `scripts/audit_skill_safety.py`. When distributing or exporting skills to external tools (such as Claude Code `~/.claude/skills/` or Codex `~/.codex/skills/`), only the root `<skill-name>/` directory and its standard contents (`SKILL.md`, `scripts/`, `references/`, `assets/`) are required.

---

## 2. YAML Frontmatter Specification

The `SKILL.md` file must open with strict YAML frontmatter delimited by `---` on the first line.

### Canonical Frontmatter Example

```yaml
---
name: systematic-debugging
description: Systematic hypothesis-driven root cause analysis. Use when diagnosing code regressions, flaky tests, or mysterious runtime exceptions.
license: Apache-2.0
compatibility: Requires git, bash, and Python 3.10+
allowed-tools: Bash(pytest:*) Bash(git:*) Read Grep
metadata:
  author: Kunal Suri <kunal@example.com>
  version: 1.0.0
  tags: debugging, tdd, root-cause
---
```

### Canonical Field Definitions (Open Standard)

The [Agent Skills Open Specification](https://agentskills.io/specification) strictly standardizes **6 top-level properties**:

| Field | Type | Required? | Rules & Constraints |
|---|---|---|---|
| `name` | string | **Yes** | 1–64 characters. Unicode lowercase alphanumeric and single hyphens (`^[a-z0-9]+(-[a-z0-9]+)*$`). **Must not** start or end with a hyphen, **must not** contain consecutive hyphens (`--`), and must strictly match the parent directory name. |
| `description` | string | **Yes** | 1–1024 characters. Non-empty. Must declare **WHAT** the skill does and **WHEN** the agent must trigger it. Use imperative framing (*"Use when..."*) and domain keywords. |
| `license` | string | Optional | Short license name, SPDX identifier (e.g., `Apache-2.0`, `MIT`), or reference to a bundled file (e.g., `Proprietary. LICENSE.txt has complete terms`). |
| `compatibility` | string | Optional | Max 500 characters. Single text string describing environment requirements (system packages, network access, runtime versions). **Must not be a list/array.** |
| `metadata` | map[string]string | Optional | Arbitrary key-value map for additional properties. This is the **official standard container** for `author`, `version`, `tags`, and tooling-specific metadata. |
| `allowed-tools` | string | Optional | Space-separated string of pre-approved tool patterns (e.g., `Bash(git:*) Read`). *Experimental in open standard.* |

> [!IMPORTANT]
> **Strict Packaging & Upload Rule**:  
> Official skill packagers (such as Anthropic's `package_skill.py` and claude.ai skill uploads) enforce a closed frontmatter schema. If properties such as `version`, `author`, or `tags` are declared as top-level keys rather than under `metadata`, packaging fails with a hard error:  
> `Unexpected key(s) in SKILL.md frontmatter: <field>. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name`.

### Client-Specific Frontmatter Extensions (Claude Code)

When authoring skills specifically for **Anthropic Claude Code**, the runtime supports additional frontmatter controls beyond the open standard:

| Extension Field | Type | Default | Purpose & Behavior |
|---|---|---|---|
| `disable-model-invocation` | boolean | `false` | When `true`, Claude will not automatically invoke the skill; it runs only when explicitly typed by the user as `/skill-name`. |
| `user-invocable` | boolean | `true` | When `false`, hides the skill from the user `/` menu; only the model can trigger it. |
| `context` | string | — | Set to `fork` to execute the skill in an isolated subagent context without inheriting prior chat history. |
| `agent` | string | `general-purpose` | Specifies the subagent configuration (`Explore`, `Plan`, or custom) when `context: fork` is active. |
| `arguments` | list / string | — | Declares named positional parameters for `$name` substitution in `SKILL.md`. |
| `argument-hint` | string | — | Autocomplete hint displayed in the CLI (e.g. `[issue-number]`). |
| `paths` | list / string | — | Glob patterns limiting automatic activation to specific file paths. |
| `shell` | string | `bash` | Controls execution shell for dynamic injection (`bash` or `powershell`). |
| `when_to_use` | string | — | Supplementary trigger context appended to `description` in skill listings. |

---

## 3. Progressive Disclosure Architecture

Agent Skills leverage **progressive disclosure** across three distinct phases to minimize token overhead and prevent context saturation:

```text
[Agent Startup / Discovery]
   │
   ▼
[Scan Frontmatter (~100 tokens/skill)]    ───> Low token footprint (name + description)
   │
   ▼
[User Intent Matches "description"]
   │
   ▼
[Load full SKILL.md (<500 lines)]         ───> Actionable workflow loaded into context
   │
   ▼
[On-Demand Resource Execution]
   ├──> Execute scripts/                  ───> Deterministic code execution without prompt drift
   ├──> Read references/                  ───> Domain documentation loaded only when triggered
   └──> Load assets/                      ───> Templates and data schemas fetched as needed
```

### Context & Budget Rules

1. **Header Budget**: Keep frontmatter concise ($\approx 100\text{--}150$ tokens). Claude Code caps combined description listings at 1% of the model's context window (up to 1,536 characters per skill).
2. **Body Budget**: Keep `SKILL.md` body under **500 lines** and **$< 5,000$ tokens**. State procedural steps clearly; avoid narrating basics the LLM already knows.
3. **Execution Offloading**: Delegate complex calculations, data transformations, and heavy schemas to `scripts/` (for execution) and `references/` or `assets/` (for targeted reference).
4. **File Reference Depth**: Keep file references one level deep from `SKILL.md` (e.g., `references/REFERENCE.md`, `scripts/extract.py`). Avoid deeply nested reference chains.
