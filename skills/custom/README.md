# Custom Agent Skills

This directory hosts custom, production-ready agent skills designed, tested, and attested specifically for high-leverage software engineering and multi-agent workflows.

---

## 🎯 Purpose & Scope

Unlike vendor-specific directories, `skills/custom/` focuses on:
- **Cross-Agent Tooling & Sync**: Skills that maintain configuration, rule synchronization, and documentation across Claude Code, Google Antigravity, Cursor, and OpenAI Codex (e.g., [`multi-agent-docs`](./multi-agent-docs/SKILL.md)).
- **Resilient Engineering Workflows**: Workflows like Resumable Spec-Driven Development (`resumable-sdd`), test harness automation, and session handoffs.
- **Domain-Specific & Student Contributions**: Reusable procedural knowledge created using the [`/utils/skill-creator/`](../../utils/skill-creator/) lab and validated with [`Skill Doctor`](../../utils/Skill-Doctor.html).

---

## 📋 Standard Requirements for Custom Skills

Every skill introduced here must follow the repository's 3 core pillars:
1. **`SKILL.md`**: Validated frontmatter (`name`, `description` with explicit triggers, `version`), $\le 500$ lines.
2. **`attestation.json`**: Multi-model verification records and resilience checks.
3. **`evals/test-cases.json`**: Precision and recall intent test cases for benchmark evaluation.

---

## 🚀 Active Skills

| Skill | Status | Description |
|---|---|---|
| [`cross-platform-dev-scripts`](./cross-platform-dev-scripts/SKILL.md) | `🟢 Checks passing` | Scaffolds and validates turnkey, cross-platform dev setup & test scripts (`scripts/win`, `scripts/linux`) with dual-engine `uv`/`venv` fallback. |
| [`multi-agent-docs`](./multi-agent-docs/SKILL.md) | `🟢 Checks passing` | Scaffolds & synchronizes identical `CLAUDE.md` and `AGENTS.md` across platforms. |
| [`preflight-test-engineer`](./preflight-test-engineer/SKILL.md) | `🟢 Checks passing` | Pre-flight codebase analysis, /tests/ suite generation, and 4-stage verification for Python & TypeScript/React. |
| [`public-repo-release-review`](./public-repo-release-review/SKILL.md) | `🟢 Checks passing` | Expert pre-flight audit for public GitHub releases: security/secret leaks, governance files, and link integrity. |
| [`readme-designer`](./readme-designer/SKILL.md) | `🟢 Checks passing` | Modernizes and designs high-impact, world-class READMEs and documentation with rich spacing (`<br/>`), dividers (`---`), comparison matrices, and Mermaid diagrams. |
| [`third-party-skill-verifier`](./third-party-skill-verifier/SKILL.md) | `🟢 Checks passing` | Statically verifies a skill written by someone else before you install it: reads every file in the bundle, reports what its code can actually do, and grades what runs without being invoked. Never fetches, writes, or executes. |
| [`saas-app-builder`](./saas-app-builder/SKILL.md) | `🟢 Checks passing` | Scaffolds and implements full-stack SaaS apps with React 19, Tailwind CSS v4, shadcn/ui, single-port Express serving, and an integrated 4-harness test suite. |

---

## 💡 Proposing New Custom Skills

Have a custom multi-agent workflow to contribute?
- Use the templates in [`utils/skill-creator/`](../../utils/skill-creator/) to draft your skill.
- Test in [`Skill Doctor`](../../utils/Skill-Doctor.html) and submit a PR to `skills/custom/<skill-name>/`.

