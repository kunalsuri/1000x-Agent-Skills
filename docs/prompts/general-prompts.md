# 🧰 General Prompts

## Prompt Name: Prompt Refinement

Rewrite the following prompt to be clear, precise, and efficient. Preserve its intent and constraints, remove redundancy, and do not add assumptions:

[PASTE PROMPT]

---

## Prompt Name: Agent-Skills Specs Audit

Audit `docs/agent-skills-specs/skill-specs.md`, then verify its specifications against current authoritative online sources.

Requirements:

* Check each specification for accuracy and currency.
* Identify outdated, incorrect, unsupported, or missing information.
* Prefer primary or official sources.
* Clearly distinguish verified facts from anything that cannot be confirmed.
* Do not modify the file unless explicitly requested.

---

## Prompt Name: Session Summary (Caveman Style)

Based on everything learned in this session, write one short paragraph explaining:

* what I asked you to do,
* what you did,
* and why you did it.

Use caveman style: short, simple sentences, minimal words, no unnecessary detail.

---

## Prompt Name: Agent-Skills Specs Refresh (apply)

Run when `python scripts/validate_skills.py` prints a `[SPEC FRESHNESS]` warning.

Re-read every source listed in `docs/agent-skills-specs/skill-specs.md` §1 (fetch the agentskills.io pages from `github.com/agentskills/agentskills/docs` if the site is unreachable). Then:

* Update `skill-specs.md` and `skill-specs.meta.yaml` where upstream changed; upstream wins on conflict.
* Move anything you could not re-check into §10 "Not verified" instead of leaving it asserted.
* Bump `last_verified` and `next_review_due` (+90 days) in both files only after the re-check.
* If a rule changed, update `scripts/validate_skills.py` and its tests in the same change.
* Write a `recon` note with the `lessons-learnt` skill listing what changed, with sources and dates.

---
