# Recon 2026-10-31: Agent Skills spec, Claude Code, plugins and installers

**Written:** 2026-10-31 22:53 UTC. **Read when:** you update `docs/agent-skills-specs/`, change frontmatter validation, or change how the repo is installed.

## TL;DR
- The open spec has exactly six frontmatter keys; everything custom goes under `metadata` (string → string).
- Flat `skills/<name>/` is the de-facto layout (anthropics/skills, Claude Code plugins, `npx skills`).
- Two public install routes now exist and work for this repo: Claude Code plugin marketplace, and `npx skills add`.

## Facts and sources
- Spec keys: `name` (≤64, `^[a-z0-9]+(-[a-z0-9]+)*$`, matches folder), `description` (≤1024), `license`, `compatibility` (≤500, string), `metadata` (map string→string), `allowed-tools` (space-separated, experimental). Source: https://raw.githubusercontent.com/agentskills/agentskills/main/docs/specification.mdx. Checked: 2026-10-31. Re-check by: 2027-01-29.
- Progressive disclosure budgets: ~100 tokens metadata, <5,000 tokens body, <500 lines. Source: same. Checked: 2026-10-31.
- Output evals live in `evals/evals.json` with `prompt`, `expected_output`, `files`, `assertions`; trigger evals are `{query, should_trigger}` lists, ~20 queries, near-miss negatives. Source: agentskills `docs/skill-creation/evaluating-skills.mdx`, `optimizing-descriptions.mdx`. Checked: 2026-10-31.
- Script design: non-interactive, `--help`, stdout data / stderr diagnostics, exit codes, `--dry-run`, bounded output (harnesses truncate ~10–30K chars), PEP 723 inline deps. Source: agentskills `docs/skill-creation/using-scripts.mdx`. Checked: 2026-10-31.
- Claude Code extra keys: `when_to_use`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `arguments`, `argument-hint`; listing truncates description+when_to_use at 1,536 chars. Source: https://code.claude.com/docs/en/skills (second half read via summariser). Checked: 2026-10-31.
- Anthropic: `name` must not contain `anthropic` or `claude`; description in third person; ≥3 evals; test with every target model. Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices. Checked: 2026-10-31.
- Marketplace: `.claude-plugin/marketplace.json` with `name`, `owner`, `plugins[{name, source, skills?}]`; `strict: false` lets one plugin point at `./skills/*` paths (pattern used by anthropics/skills). `claude plugin validate .` passes for this repo. Source: https://code.claude.com/docs/en/plugin-marketplaces and anthropics/skills `.claude-plugin/marketplace.json`. Checked: 2026-10-31.
- `npx skills add owner/repo` (`--skill`, `-a`, `-g`, `--list`), Node.js ≥ 22.20, searches `skills/`, `.agents/skills/`, `.claude/skills/` and reads `.claude-plugin/` manifests. Source: https://github.com/vercel-labs/skills (README, docs/commands.md, docs/creating-skills.md). Checked: 2026-10-31.
- `openai/skills` README marks the repo deprecated, pointing to `openai/plugins`. Source: https://raw.githubusercontent.com/openai/skills/main/README.md. Checked: 2026-10-31.

## How to re-check
- `curl -sS https://raw.githubusercontent.com/agentskills/agentskills/main/docs/specification.mdx | sed -n '/### Frontmatter/,/#### `name`/p'` : the six-row table.
- `claude plugin validate .` : "Validation passed".

## Open items
- [ ] Not verified: agentskills.io, developers.openai.com and cursor.com were unreachable from the sandbox (DNS failure). Codex and Cursor discovery paths, and Antigravity paths in `scripts/install_to_agent.py`, remain unconfirmed.
- [ ] Not verified: Snyk ToxicSkills figures and the SkillsBench result were seen in search summaries only.
