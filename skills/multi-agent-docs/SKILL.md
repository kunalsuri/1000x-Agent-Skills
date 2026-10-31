---
name: multi-agent-docs
version: 1.1.0
author: Kunal Suri <kunal.suri@cea.fr>
description: Deterministically scaffolds and synchronizes CLAUDE.md, AGENTS.md, .claude/, and .agents/ using automated manifest inspection scripts followed by semantic LLM refinement. Use when configuring a repository for multi-agent workflows (Claude Code, Antigravity, Cursor, Codex) or when resolving instruction drift.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [run_command, view_file, write_to_file, replace_file_content]
tags: [multi-agent, claude-md, agents-md, setup, sync, deterministic]
license: Apache-2.0
---

# Multi-Agent Project Docs & Conventions

## Purpose
Prevent instruction drift between tools by producing synchronized, high-accuracy `CLAUDE.md` and `AGENTS.md` configuration files alongside `.claude/` and `.agents/` project scaffolding through a **deterministic code + semantic synthesis** pipeline.

## Procedural Workflow

### Phase 1: Deterministic Scaffolding
Execute the built-in scaffolding script using `run_command`:

```bash
python <skill_path>/scripts/scaffold.py --target .
```

The script automatically:
1. Introspects repository manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.).
2. Extracts concrete build, test, lint, and run commands.
3. Creates `.claude/`, `.agents/`, and `.agents/rules/` directories.
4. Generates baseline synchronized `CLAUDE.md`, `AGENTS.md`, and `.agents/AGENTS.md` with companion sync headers.
5. Emits a structured JSON summary of detected facts and remaining TODO items.

---

### Phase 2: Semantic Content Synthesis & Refinement
Read the project source code and refine the generated `CLAUDE.md` and `AGENTS.md` files:

1. **Inspect Deep Project Context**:
   - Read key modules, entry points, and tests (`src/`, `lib/`, `tests/`, etc.).
   - Identify domain conventions, error-handling patterns, and naming standards.

2. **Update Placeholders in Both Files**:
   - Replace all `[TODO: ...]` placeholders with concrete architectural explanations.
   - Ensure `CLAUDE.md` and `AGENTS.md` have identical factual commands and architecture sections.
   - Preserve tool-specific sections:
     - `CLAUDE.md`: Claude Code subagent rules and instructions.
     - `AGENTS.md`: Tool-agnostic rules for Antigravity, Cursor, and Codex.

---

### Phase 3: Deterministic Sync Verification
Verify that both files are in parity and zero instruction drift occurred:

```bash
python <skill_path>/scripts/validate_sync.py --target .
```

- If validation passes (`[PASS]`), configuration is complete.
- If warnings (`[WARN]`) or errors (`[FAIL]`) are returned for command discrepancies, resolve the drift in `CLAUDE.md` or `AGENTS.md` using `replace_file_content`.
