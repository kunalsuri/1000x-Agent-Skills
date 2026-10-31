# 🎓 Student & Contributor Guide

How to use the skills in this repository, write a new one, and submit it.
*Last reviewed: 2026-10-31.*

---

## ⚡ Install the skills

Pick one route (details in the [root README](../README.md#-install)):

```text
# Claude Code, inside a session
/plugin marketplace add kunalsuri/1000x-Agent-Skills
/plugin install 1000x-agent-skills@1000x-agent-skills
```

```bash
# Any Agent Skills client (Node.js 22.20+)
npx skills add kunalsuri/1000x-Agent-Skills --skill lessons-learnt

# From a clone: preview first, then apply
git clone https://github.com/kunalsuri/1000x-Agent-Skills.git && cd 1000x-Agent-Skills
python scripts/install_to_agent.py --target claude --skill lessons-learnt
python scripts/install_to_agent.py --target claude --skill lessons-learnt --apply
```

---

## 🛠️ Create a new skill

1. **Pick a task you have actually done.** A skill distilled from a real session (your steps, the corrections you had to make, the gotchas) beats one written from general knowledge. Agents already know general best practice; a skill earns its tokens with what they *don't* know.
2. **Draft it.** In Claude Code, ask for a new skill (the vendored `skill-creator` in `.claude/skills/` takes over), or use the prompt in [`utils/skill-creator/SKILL-CREATOR-PROMPT.md`](../utils/skill-creator/SKILL-CREATOR-PROMPT.md).
3. **Write the description last, and test it.** It is the only part the agent sees before deciding to load the skill. Say what the skill does *and* when to use it, in user language, including cases where the user doesn't name the domain. Keep it under 1,024 characters.
4. **Add a `## Gotchas` section.** Every time the agent gets something wrong while you test, add the correction there.
5. **Write evals.**
   - `evals/test-cases.json`: about 5+ prompts that should trigger and 4+ **near-miss** prompts that share vocabulary but should not.
   - `evals/evals.json` (recommended): 2–3 realistic tasks with `expected_output` and checkable `assertions` ([format](https://agentskills.io/skill-creation/evaluating-skills)). Compare with-skill vs. without-skill.
6. **Attest honestly.** Fill `attestation.json` from [`utils/skill-creator/attestation-template.json`](../utils/skill-creator/attestation-template.json). Start at `DRAFT`. Use `PASS` only for runs you did, and link evidence (`evidence_url`) before claiming `VERIFIED`.
7. **Run the gate:**
   ```bash
   python scripts/skill_digest.py --update     # binds the attestation to your exact files
   python scripts/sync_mirror.py --write       # refreshes .agents/skills/
   python scripts/audit_skill_safety.py --strict
   python scripts/validate_skills.py
   python -m pytest
   ```
8. **List it** in the root `README.md` catalogue and in `.claude-plugin/marketplace.json` (CI checks both), then open a pull request from a branch named `feat/skill-<name>`.
9. **Record what you learned** with the `lessons-learnt` skill.

---

## 💡 Submission checklist

- [ ] Folder is `skills/<name>/` and `name:` matches it (`^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64 chars).
- [ ] Frontmatter uses only the six spec keys; `version`, `author`, `tags` are under `metadata:`.
- [ ] `compatibility`, if present, is one string (≤ 500 chars), not a list.
- [ ] Description says **what** and **when**, in user language; ≤ 1,024 characters.
- [ ] `SKILL.md` body is under 500 lines; long material is in `references/`, one level deep, linked with relative paths.
- [ ] Scripts are non-interactive, have `--help`, print structured output to stdout and diagnostics to stderr, and use distinct exit codes.
- [ ] `attestation.json` capabilities match what your code does (the auditor will tell you if not).
- [ ] `evals/test-cases.json` has near-miss negatives, not just obviously unrelated prompts.
- [ ] All five gate commands above pass.
