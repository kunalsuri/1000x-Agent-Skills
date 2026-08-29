# 🌐 Agent Ecosystem Tracker & Reference Index

A living index of the latest specifications, tools, protocols, and papers shaping autonomous coding agents.

---

## 🏛️ Official Specifications & Standards

| Resource | Organization / Maintainer | Description & Links |
|---|---|---|
| **Agent Skills Open Spec** | Anthropic & Community | Standard specification for `SKILL.md` format and progressive loading. <br>🔗 [agentskills.io](https://agentskills.io/specification) |
| **Model Context Protocol (MCP)** | Anthropic & Open Source | Open standard for connecting AI models to external data sources and execution tools. <br>🔗 [modelcontextprotocol.io](https://modelcontextprotocol.io/) |
| **Google Antigravity Customizations** | Google DeepMind | Skills, Rules, and Plugins architecture for Antigravity IDE & CLI. <br>🔗 [Antigravity Docs](https://deepmind.google/technologies/antigravity) |

---

## 🛠️ Major Agent Platforms & CLI Tools

- **Claude Code**: Anthropic's CLI-first agentic coding environment (`claude`). Supports native `skills/` and system subagents.
- **Google Antigravity**: Autonomous agent pair programmer with planning mode, browser subagent, task scheduler, and customizations (`.gemini/config/skills` & `.agents/skills`).
- **Cursor**: AI-native code editor supporting `.cursorrules` and Agent Mode.
- **OpenAI Codex / Canvas**: OpenAI's agentic code generation and canvas interfaces.

---

## 📚 Key Research Papers & Benchmarks

- **SWE-bench / SWE-bench Verified**: The gold standard benchmark for evaluating LLMs and agent frameworks on real-world GitHub issues.
- **Progressive Tool & Skill Retrieval**: Studies demonstrating $40\%+$ token efficiency improvements through progressive metadata loading vs. monolith system prompts.
- **Spec-Driven & Resumable Agent Workflows**: Architectures for committing execution state to git to prevent catastrophic context exhaustion during multi-hour agent sessions.

---

## 🔄 Community Repositories & Hubs
- [Anthropic Skill Creator](https://github.com/anthropics/anthropic-quickstarts)
- [MCP Servers Directory](https://github.com/modelcontextprotocol/servers)
- [Google Science & Coding Skills](https://github.com/google-deepmind)
