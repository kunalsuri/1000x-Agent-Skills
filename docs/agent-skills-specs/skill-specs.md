---
title: "Agent Skills Specification & Format Guidelines"
specification_standard: "https://agentskills.io/specification"
status: "active"
created: "2026-09-09"
last_verified: "2026-10-31"
next_review_due: "2027-01-29"
metadata_manifest: "./skill-specs.meta.yaml"
---

# 📐 Agent Skills: Specification & Authoring Guidelines

> [!IMPORTANT]
> **Last verified against upstream sources: 2026-10-31.** Next review due: **2027-01-29** (90 days).
> `python scripts/validate_skills.py` reads `last_verified` from [`skill-specs.meta.yaml`](./skill-specs.meta.yaml) and warns once this page is more than 90 days old.
> To refresh it, run the *Agent-Skills Specs Audit* prompt in [`docs/prompts/general-prompts.md`](../prompts/general-prompts.md), update both files, and add a `recon` note to [`docs/lessons-learnt/`](../lessons-learnt/).

This page is a working summary for this repository, not the standard itself. Where it and an upstream source disagree, **the upstream source wins**; please fix this page. Every rule below names its source. Section 10 lists what could not be verified.

---

## 1. Sources and how they were checked

| Source | What it governs | How checked on 2026-10-31 |
|---|---|---|
| [Agent Skills specification](https://agentskills.io/specification) | The portable `SKILL.md` format | Read in full from its source, `agentskills/agentskills` `docs/specification.mdx` on GitHub (the agentskills.io host was not reachable from the audit sandbox) |
| [agentskills.io best practices](https://agentskills.io/skill-creation/best-practices), [optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions), [evaluating skills](https://agentskills.io/skill-creation/evaluating-skills), [using scripts](https://agentskills.io/skill-creation/using-scripts) | Authoring guidance | Read from the same GitHub source |
| [Claude Code: skills](https://code.claude.com/docs/en/skills) | Claude Code's extensions and discovery paths | Fetched; the second half of the page was read through a summariser, so treat fine details marked † below as lower confidence |
| [Claude: skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Anthropic's authoring rules | Fetched in full |
| [Claude Code: plugins](https://code.claude.com/docs/en/plugins), [plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) | Distribution through `/plugin` | Fetched; this repo's manifest passes `claude plugin validate .` |
| [`vercel-labs/skills`](https://github.com/vercel-labs/skills) | The `npx skills` installer used by skills.sh | README and `docs/` fetched |
| [`anthropics/skills`](https://github.com/anthropics/skills) | Reference catalogue layout | `README.md` and `.claude-plugin/marketplace.json` fetched |

---

## 2. Directory structure

**Portable skill (spec).** A skill is a directory with at least a `SKILL.md`. `scripts/`, `references/` and `assets/` are recommended conventions; any other files are allowed.

```text
<skill-name>/
├── SKILL.md          # required: frontmatter + instructions
├── scripts/          # optional: executable code
├── references/       # optional: docs loaded on demand
├── assets/           # optional: templates, data, images
└── evals/            # optional (agentskills.io evaluating guide): evals.json
```

**This repository's profile.** Skills live at `skills/<skill-name>/` (flat, since 2026-10-31). That is the layout of `anthropics/skills`, of a Claude Code plugin (`<plugin>/skills/<name>/SKILL.md`), and the first place `npx skills add` searches. On top of the portable files every skill here also ships:

| File | Purpose | Standard? |
|---|---|---|
| `attestation.json` | Declared capabilities, provenance, status, `content_digest` | Repository extension ([spec](../ATTESTATION-SPEC.md), [schema](../schemas/attestation.schema.json)) |
| `evals/test-cases.json` | Trigger prompts (positive / negative) | Repository extension; the upstream equivalent for triggering is an `eval_queries.json` list of `{query, should_trigger}` |
| `evals/evals.json` | Output-quality cases | Upstream format (`prompt`, `expected_output`, `files`, `assertions`) |

Exported skills only need the portable files; the extensions are harmless to clients that ignore them.

---

## 3. Frontmatter

### 3.1 The six spec fields (source: agentskills.io specification)

| Field | Required | Constraints (quoted or closely paraphrased from the spec) |
|---|---|---|
| `name` | Yes | 1–64 chars; lowercase `a-z`, `0-9` and `-`; no leading/trailing hyphen; no `--`; **must match the parent directory name**. |
| `description` | Yes | 1–1024 chars. "Should describe both what the skill does and when to use it" and include keywords that help agents identify relevant tasks. |
| `license` | No | License name or name of a bundled licence file. |
| `compatibility` | No | 1–500 chars. Environment requirements (intended product, system packages, network). "Most skills do not need the `compatibility` field." |
| `metadata` | No | A map from string keys to string values. Use reasonably unique key names. |
| `allowed-tools` | No | Space-separated string of pre-approved tools. **Experimental**; support varies by client. |

Anything else at the top level is outside the spec. Claude Code's docs state that claude.ai uploads, the Skills API and `package_skill.py` accept only these six keys and reject others with `Unexpected key(s) in SKILL.md frontmatter` †. **So `version`, `author` and `tags` go under `metadata`**, with `version` quoted (`"1.0.0"`) so it stays a string. `scripts/validate_skills.py` enforces this.

```yaml
---
name: pdf-processing
description: Extracts text and tables from PDFs, fills forms and merges files. Use when the user works with PDF documents or mentions forms or document extraction, even if they do not say "PDF".
license: Apache-2.0
metadata:
  author: Jane Doe
  version: "1.2.0"
  tags: pdf, forms, extraction
---
```

### 3.2 Platform-specific naming rules (source: Claude authoring best practices)

Anthropic's platform additionally forbids XML tags in `name` and `description`, and the reserved words `anthropic` and `claude` in `name`. It suggests gerund names (`processing-pdfs`) as an option, and lists `pdf-processing` as acceptable. Avoid vague names (`helper`, `utils`, `tools`).

### 3.3 Claude Code extensions (source: Claude Code skills docs)

Claude Code accepts these in addition to the spec. Other clients ignore them, and claude.ai uploads reject them, so they make a skill less portable. The validator warns rather than fails.

| Key | Effect |
|---|---|
| `when_to_use` | Extra trigger context appended to `description` in the listing (counts toward the cap). |
| `disable-model-invocation` | `true`: only the user can invoke (`/name`); the description is not kept in context. |
| `user-invocable` | `false`: hidden from the `/` menu; only the model can invoke. |
| `allowed-tools` / `disallowed-tools` | Pre-approve or remove tools for the turn that invokes the skill. Claude Code accepts a string or a YAML list. |
| `argument-hint`, `arguments` | Autocomplete hint; named positional arguments for `$name` substitution. Also `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`. |
| `model`, `effort` | Override model or effort for the rest of the turn. |
| `context: fork`, `agent`, `background` | Run the skill in a forked subagent (`Explore`, `Plan`, `general-purpose` or a custom agent). |
| `paths` | Globs that limit automatic activation to matching files. |
| `hooks` | Hooks registered when the skill is invoked. |
| `shell` | `bash` (default) or `powershell` for `` !`command` `` dynamic-context lines, which Claude Code runs before the model sees the skill. |

Useful substitutions †: `${CLAUDE_SKILL_DIR}` (portable path to the skill's own files), `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SESSION_ID}`.

---

## 4. Progressive disclosure and budgets

| Stage | What loads | Budget | Source |
|---|---|---|---|
| Startup | `name` + `description` of every skill | ~100 tokens per skill | spec |
| Activation | Whole `SKILL.md` body | < 5,000 tokens recommended; **< 500 lines** | spec; Claude best practices |
| On demand | `scripts/`, `references/`, `assets/` | Only what the task needs | spec |

Client-specific limits in Claude Code †: `description` + `when_to_use` are truncated at **1,536 characters** in the listing; the whole listing is budgeted at about 1% of the context window, and when it overflows the least-used skills lose their descriptions first. After compaction, each invoked skill keeps its first 5,000 tokens. Keep the key use case at the **start** of the description.

**File references:** relative paths from the skill root (`references/guide.md`, `scripts/run.py`), forward slashes only, **one level deep** from `SKILL.md`. Give reference files over 100 lines a table of contents. Never use absolute `file:///` links; they break as soon as the skill is installed elsewhere.

---

## 5. Writing the description (the trigger)

The description carries the whole burden of triggering (agentskills.io). Rules from the two primary guides:

1. Say **what** and **when**, in the user's words rather than the implementation's.
2. Be explicit, even a little "pushy": list contexts where the skill applies, including ones where the user does not name the domain. Agents tend to *under*-trigger.
3. Agents usually skip skills for simple one-step tasks they can do alone, so trigger tests should use tasks that genuinely need the skill.
4. Voice: agentskills.io recommends imperative framing ("Use this skill when…"); Anthropic recommends third person ("Processes Excel files…") and warns against "I can…" or "You can…". These are compatible: **"Processes X. Use when Y."**
5. Measure it: ~20 realistic queries, 8–10 should-trigger and 8–10 **near-miss** should-not-trigger; run each several times; keep a held-out validation split so you do not overfit.

---

## 6. Writing the body

From agentskills.io best practices and Anthropic's authoring guide:

- **Start from real expertise.** Extract the skill from a task you actually did with an agent (your corrections, inputs and outputs, project facts). LLM-generated generic advice makes weak skills.
- **Add what the agent lacks, omit what it knows.** Ask of each paragraph: does it justify its tokens?
- **Match specificity to fragility.** Loose guidance where many approaches work; exact commands where a mistake is costly ("run exactly this script").
- **Provide defaults, not menus.** One recommended path, with escape hatches.
- **Gotchas section.** Concrete, environment-specific facts that defy reasonable assumptions. Add one every time you have to correct the agent.
- **Templates** for output formats; **checklists** for multi-step work; **validation loops** (run → check → fix → repeat); **plan-validate-execute** for risky operations.
- **No time-sensitive statements** in skill bodies; move legacy behaviour to an "old patterns" section.
- **Consistent terminology.**
- **MCP tools** by fully qualified name (`ServerName:tool_name`).

---

## 7. Scripts (source: agentskills.io *using scripts*; Claude best practices)

- **Solve, don't punt:** handle errors in the script instead of leaving them to the agent. Document magic numbers.
- **Self-contained:** declare dependencies inline (Python: [PEP 723](https://peps.python.org/pep-0723/) `# /// script` block) or stay on the standard library, as every script in this repo does.
- **Non-interactive:** never wait for input; fail with a clear message instead.
- **`--help`** documents usage, flags and exit codes.
- **Structured output** (JSON or delimited) to stdout; diagnostics to stderr.
- **Meaningful exit codes**, **idempotent** operations, **`--dry-run`** for anything stateful, explicit flags (`--apply`, `--force`) for destructive steps.
- **Predictable output size:** harnesses truncate long output (roughly 10–30K characters); summarise by default and paginate on request.

---

## 8. Evaluation (source: agentskills.io *evaluating skills*; Claude best practices)

- Write evals **before** polishing the skill; Anthropic's checklist asks for at least three.
- `evals/evals.json`: each case has `prompt`, `expected_output`, optional `files`, and `assertions` that can be checked from the output.
- Run every case **with and without** the skill (or against the previous version), grade the assertions, aggregate pass rate, time and tokens, and have a human read the outputs.
- Review the assertions themselves: drop ones that always pass or can never be checked.
- Test with every model you intend to support.
- Anthropic's `skill-creator` (vendored here in `.claude/skills/`) automates this loop.

---

## 9. Distribution

| Route | How | Notes |
|---|---|---|
| Claude Code plugin marketplace | `.claude-plugin/marketplace.json` at the repo root; users run `/plugin marketplace add owner/repo` then `/plugin install <plugin>@<marketplace>` | Validate with `claude plugin validate .`. Plugin skills are namespaced `/<plugin>:<skill>`. |
| `npx skills` (skills.sh) | `npx skills add owner/repo [--skill name] [-a agent] [-g]` | Needs Node.js 22.20+. Searches `skills/`, `.agents/skills/`, `.claude/skills/` and many agent directories up to 3 levels deep; also reads `.claude-plugin/` manifests. |
| Project-local | Commit to `.claude/skills/<name>/` (Claude Code) or `.agents/skills/<name>/` | Claude Code also discovers nested `.claude/skills/` in subdirectories. |
| This repo's installer | `python scripts/install_to_agent.py --target claude --all [--apply]` | Refuses skills that fail the safety audit. |

**Supply-chain caution.** Public marketplaces aggregate skills without mandatory review, and malicious skills have been found in them ([Snyk, 2026](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/)). Read any third-party skill before installing it, or run [`third-party-skill-verifier`](../../skills/third-party-skill-verifier/SKILL.md).

---

## 10. Not verified on 2026-10-31

These are stated in earlier versions of this page or in other repo docs but could **not** be checked against a primary source today. Treat them as unconfirmed.

- **OpenAI Codex** skill discovery paths, the `agents/openai.yaml` sidecar, and `$skill-name` invocation: `developers.openai.com` was unreachable. Note that `openai/skills` on GitHub now marks itself **deprecated** and points to `openai/plugins` and a Codex "Build plugins" guide.
- **Cursor** skill support and discovery paths: `cursor.com` was unreachable. `scripts/install_to_agent.py --target cursor` still writes to `.cursor/rules`, which may no longer be the right place.
- **Google Antigravity** paths (`~/.gemini/config/skills`, `.agents/skills`): no primary source checked.
- **The number of clients supporting the spec** (previous versions said "35+"): not re-counted.
- † Fine details of the Claude Code skills page that were read through a summariser.

---

## 11. Repository checklist (enforced by `scripts/validate_skills.py` unless noted)

- [ ] `skills/<name>/SKILL.md` at exactly that depth; `name` matches the folder.
- [ ] Only the six spec keys at the top level (Claude Code extensions warn).
- [ ] `compatibility` is one string ≤ 500 chars; `description` ≤ 1,024 chars and contains "when" context.
- [ ] `metadata.version` is quoted semver.
- [ ] Body ≤ 500 lines.
- [ ] `attestation.json` passes the schema, declares capabilities the code does not exceed (`audit_skill_safety.py`), and its `content_digest` matches (`skill_digest.py`).
- [ ] `VERIFIED` status only with an `evidence_url` (warning).
- [ ] `evals/test-cases.json` has ≥ 3 positive prompts.
- [ ] Listed in `README.md` and `.claude-plugin/marketplace.json`; mirrored byte-for-byte in `.agents/skills/` (pytest).
- [ ] *(manual)* Relative links only, one level deep; a `## Gotchas` section; `evals/evals.json` for output quality.
