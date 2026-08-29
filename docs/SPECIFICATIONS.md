# 📐 Agent Skills Specification & Format Guidelines

The **Agent Skills** format is an open specification ([agentskills.io](https://agentskills.io/specification)) supported by Anthropic Claude Code, Google Antigravity, Cursor, OpenAI Codex, and GitHub Copilot.

---

## 1. Directory Structure

A compliant skill is encapsulated in a single self-contained directory:

```text
skills/<category>/<skill-name>/
├── SKILL.md                 # Required: Frontmatter + core procedural workflow
├── attestation.json         # Proof of verification across models & dates
├── evals/                   # Trigger evaluation datasets & test cases
│   └── test-cases.json
└── references/              # Extended documentation, schemas, and API tables
    └── deep-dive.md
```

---

## 2. YAML Frontmatter Specification

```yaml
---
name: systematic-debugging
version: 1.0.0
author: Kunal Suri <kunal@example.com>
description: Systematic hypothesis-driven root cause analysis. Use when diagnosing code regressions, flaky tests, or mysterious runtime exceptions.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [view_file, run_command, replace_file_content, grep_search]
tags: [debugging, tdd, root-cause]
license: Apache-2.0
---
```

### Field Definitions

| Field | Type | Required? | Rules & Constraints |
|---|---|---|---|
| `name` | string | **Yes** | Lowercase alphanumeric with hyphens (`^[a-z0-9-]+$`). $\le 64$ chars. Must strictly match parent directory name. |
| `description` | string | **Yes** | $\le 1024$ characters. Must declare **WHAT** the skill does and **WHEN** the agent must trigger it. |
| `version` | string | **Yes** (attestation) | Semver string (e.g. `1.0.0`, `1.2.1`). |
| `author` | string | Optional | Author name and/or email/GitHub handle. |
| `compatibility` | list | Optional | Platforms where the skill has passed attestation testing. |
| `allowed-tools` | list | Optional | Tools permitted or prioritized during skill execution. |
| `license` | string | Optional | SPDX license identifier (e.g., `Apache-2.0`, `MIT`). |

---

## 3. Progressive Disclosure Architecture

```
[Agent Boot]
   │
   ▼
[Scan Frontmatters (~100 tokens/skill)]  ───> Low token footprint
   │
   ▼
[User Intent Matches "description"]
   │
   ▼
[Load full SKILL.md (<500 lines)]        ───> Actionable workflow loaded
   │
   ▼
[Read references/ if needed]            ───> Deep context on-demand
```

1. **Header Budget**: Keep frontmatter under $\approx 150$ tokens.
2. **Body Budget**: Keep `SKILL.md` body under $500$ lines.
3. **References Subfolder**: Delegate lengthy schemas, API docs, and large code examples to `references/`.
