# 🤖 AGENTS.md — Global Multi-Agent System Rules & Guidelines

This document defines standard conventions, operating protocols, and execution principles for all autonomous coding agents interacting with the **1000x-Agent-Skills** repository.

---

## 🎯 Core Operating Principles

1. **Declared & Attested First**: Before executing complex workflows, consult `skills/` to check if a standardized skill matches the user's intent.
2. **Progressive Disclosure**: Only index skill headers (frontmatter) at startup. Load detailed `SKILL.md` bodies only when task relevance is confirmed.
3. **Durable & Resumable Execution**: On multi-step tasks, commit intermediate milestones or write persistent checklist artifacts to survive token quota limits and session restarts.
4. **Code Quality & Non-Destructive Edits**: Never rewrite entire files when targeted replacements suffice. Preserve existing comments, types, and architectural conventions.

---

## 🏗️ Multi-Agent Role Definitions

| Role | Primary Responsibility | Associated Skills |
|---|---|---|
| **Architect / Planner** | Breaks down ambiguous requests into milestone checklists and specifications. | `resumable-sdd`, `artifact-driven-dev` |
| **Implementer / Coder** | Implements clean, targeted code changes according to approved plans. | `tdd-workflow`, `clean-refactor` |
| **Diagnostician / Debugger** | Formulates falsifiable hypotheses to isolate regressions and bugs. | `systematic-debugging` |
| **Reviewer / Gatekeeper** | Validates code correctness, security constraints, and attestation data. | `code-review-gate`, `skill-doctor` |

---

## ⚙️ Standard Tool Usage Conventions

- **File Inspection**: Use precise line ranges (`view_file`) rather than loading huge files into context.
- **Search**: Use regex-aware or targeted pattern search (`grep_search`) before scanning full directory trees.
- **File Modifications**: Use chunk-based replacements (`replace_file_content` / `multi_replace_file_content`) to prevent context corruption.
- **Shell Commands**: Avoid running non-terminating commands without timeout safeguards. Never change directories with `cd` in persistent sessions.

---

## 🔗 Cross-Agent References & Documentation Links
- [Agent Skills Open Specification](SPECIFICATIONS.md)
- [Attestation & Verification Standard](ATTESTATION-SPEC.md)
- [Evaluation Framework](EVALUATION-FRAMEWORK.md)
- [Latest Agentic Ecosystem Updates](ECOSYSTEM-TRACKER.md)
- [Student Onboarding Guide](STUDENT-GUIDE.md)
