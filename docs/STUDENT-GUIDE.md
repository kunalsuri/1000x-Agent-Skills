# 🎓 Student & Contributor Guide

Welcome! This guide explains how to use skills in this repository, test them in your projects, create new skills, and submit them for attestation.

---

## ⚡ Quickstart: Installing Skills

You can install any skill from this repository into your local agent environment using our helper script:

```bash
# Clone the repository
git clone https://github.com/kunalsuri/1000x-Agent-Skills.git
cd 1000x-Agent-Skills

# Install all skills into Google Antigravity
python scripts/install_to_agent.py --target antigravity --all

# Install a specific skill into Claude Code
python scripts/install_to_agent.py --target claude --skill resumable-sdd

# Export to Cursor rules
python scripts/install_to_agent.py --target cursor --skill systematic-debugging
```

---

## 🛠️ How to Create a New Skill

1. **Ideate**: Identify a repetitive process (e.g. debugging, API client generation, database migration).
2. **Draft with LLM**: Use the prompt in [`utils/skill-creator/SKILL-CREATOR-PROMPT.md`](file:///c:/Users/kunal/Documents/GitHub/1000x-Agent-Skills/utils/skill-creator/SKILL-CREATOR-PROMPT.md).
3. **Validate in Skill Doctor**:
   - Open [`utils/Skill-Doctor.html`](file:///c:/Users/kunal/Documents/GitHub/1000x-Agent-Skills/utils/Skill-Doctor.html) in your browser.
   - Paste your `SKILL.md` and ensure your health score is **$\ge 85$ (Grade A)**.
4. **Create Test Cases**:
   - Add positive and negative trigger queries into `evals/test-cases.json`.
5. **Attest**:
   - Complete `attestation.json` with the model, date, and results.
6. **Submit PR**:
   - Create a branch `feat/skill-<name>` and submit a Pull Request.

---

## 💡 Assignment Checklist for Students

- [ ] Skill name matches folder name (`^[a-z0-9-]+$`).
- [ ] Description includes **WHAT** it does and **WHEN** to trigger (e.g. "Use when...").
- [ ] Header token count is under $\approx 150$ tokens.
- [ ] Body length is under $500$ lines.
- [ ] `attestation.json` and `evals/test-cases.json` are present and valid.
- [ ] Passes automated CI linter (`python scripts/validate_skills.py`).
