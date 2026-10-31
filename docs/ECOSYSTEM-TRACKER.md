# 🌐 Agent Skills Ecosystem Tracker

A living index of the specs, tools and research that shape this repository.
**Last reviewed: 2026-10-31.** Entries marked ✅ were opened and read on that
date; ⚠️ means listed but not re-checked. Add a dated `recon` note to
[`lessons-learnt/`](./lessons-learnt/) whenever you change this page.

---

## 🏛️ Specifications

| Resource | Maintainer | Notes |
|---|---|---|
| ✅ [Agent Skills specification](https://agentskills.io/specification) · [source](https://github.com/agentskills/agentskills) | Agent Skills project (originated at Anthropic) | The portable `SKILL.md` format. Our summary: [`agent-skills-specs/skill-specs.md`](./agent-skills-specs/skill-specs.md). Reference validator: `skills-ref validate <dir>`. |
| ✅ [agentskills.io creator guides](https://agentskills.io/skill-creation/best-practices) | Agent Skills project | Best practices, optimising descriptions, evaluating skills, using scripts. |
| ✅ [Claude skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Anthropic | Conciseness, degrees of freedom, evaluation-first, checklist. |
| ⚠️ [Model Context Protocol](https://modelcontextprotocol.io/) | MCP project | Tools and data for agents; complementary to skills (skills teach *how*, MCP provides *access*). |

## 🛠️ Clients and distribution

| Resource | Notes |
|---|---|
| ✅ [Claude Code skills](https://code.claude.com/docs/en/skills) | Spec plus extensions (`disable-model-invocation`, `context: fork`, `paths`, `hooks`, …). |
| ✅ [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) | How this repo is installable with `/plugin marketplace add`. |
| ✅ [`vercel-labs/skills`](https://github.com/vercel-labs/skills) / skills.sh | Cross-agent installer: `npx skills add owner/repo`. |
| ✅ [`anthropics/skills`](https://github.com/anthropics/skills) | Anthropic's reference catalogue, including `skill-creator` (vendored here in `.claude/skills/`). |
| ⚠️ [OpenAI Codex skills](https://developers.openai.com/codex/skills) | Not reachable on 2026-10-31. [`openai/skills`](https://github.com/openai/skills) is now marked deprecated in favour of `openai/plugins`. |
| ⚠️ [Cursor skills](https://cursor.com/docs/context/skills) | Not reachable on 2026-10-31. |
| ⚠️ Google Antigravity | No primary source checked; paths used by `install_to_agent.py` are unverified. |

## 🛡️ Skill security (read before installing third-party skills)

| Resource | Notes |
|---|---|
| ⚠️ [Snyk: ToxicSkills](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) | Industry audit of public skill marketplaces reporting confirmed malicious skills. Seen via search results only; numbers not re-checked. |
| ⚠️ [Agent Skills in the Wild (arXiv 2601.10338)](https://arxiv.org/abs/2601.10338) | Empirical study of vulnerabilities in public skills. Title and abstract seen in search only. |
| ⚠️ [awesome-agent-skills-security](https://github.com/LLMSecurity/awesome-agent-skills-security) | Curated list of attacks, defences and benchmarks. |

## 📚 Research and benchmarks

| Resource | Notes |
|---|---|
| ⚠️ SkillsBench (arXiv, 2026) | Reports agent pass rates falling when skills must be retrieved from a large collection rather than given. Seen via a search summary only; find and read the paper before citing it. |
| ⚠️ [SWE-bench Verified](https://www.swebench.com/) | Standard benchmark for coding agents on real GitHub issues. |

> Earlier versions of this page cited "studies demonstrating 40%+ token efficiency" from progressive loading. No source was given and none was found, so the claim was removed.
