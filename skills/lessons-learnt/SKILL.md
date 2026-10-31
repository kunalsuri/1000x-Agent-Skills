---
name: lessons-learnt
description: Captures the important, reusable knowledge from the current session (decisions, rules we now follow, what failed and why, facts gathered with sources) as dated markdown files in a `lessons-learnt/` folder, written so both an AI agent and a human can use them. Use when the user asks to "write the lessons learnt", "record what we learned", "add this session to lessons-learnt", or at the end of a long working session.
---

# lessons-learnt

Turn what this session taught us into durable notes so the next session starts
from what is already known instead of re-deriving it (fewer tokens, fewer
repeated mistakes). Notes are for two readers: an AI agent that has no memory of
this session, and a human skimming for the "why".

## 1. Find or create the folder

Look in the repo root, in this order, and use the first that exists:
`docs/lessons-learnt/`, `lessons-learnt/`.
If neither exists, create `docs/lessons-learnt/` when a `docs/` folder exists,
otherwise `lessons-learnt/`. Never put it inside a build, vendor or generated
folder. If the folder has a `README.md`, read it first and follow its rules
(index format, append-only, kinds). If the project's `AGENTS.md`/`CLAUDE.md`
protects this folder or any file you would touch, stop and tell the user.

## 2. Name the files

`YYYY-MM-DD_HHMM_<kind>_<topic>.md`, local time, from `date +%Y-%m-%d_%H%M`
(run it, do not guess). Example: `2026-10-31_1506_failures_guardrails.md`.

- `<kind>` is one of:
  - `session`: decisions and outcomes of the session (the "why is it like this").
  - `failures`: what broke or was missed, plus the rules we now follow.
  - `recon`: facts gathered from outside the repo (versions, docs, tool
    behaviour), each with its source and date.
- `<topic>`: 1-4 lowercase words joined with `-`, naming the subject, not the day.
- Write one file per kind that has real content; skip empty kinds. Use the same
  timestamp for files written in the same run.

## 3. Decide what goes in (be selective)

Include only what would **change what someone does next time** and cannot be
read from the code or git history:

- Decisions and the reason behind them; alternatives rejected and why.
- Things that failed, the root cause (not just the symptom) and the fix.
- Rules distilled from those failures, phrased as instructions.
- Non-obvious facts about the environment, tools, sandbox or permissions.
- Commands or checks that proved something, so they can be re-run.
- Open follow-ups only a human can do, and anything **not verified** (say what
  access was missing).

Leave out: step-by-step narration, file contents already in the repo, anything
git log records, guesses presented as facts.
**Never write secrets** (tokens, keys, passwords, private URLs, personal data).

## 4. File template

Every file starts with a title, a `Written:` line (date, time, timezone) and one
sentence saying **when to read it**. Then:

```markdown
# <Kind> <date>: <one-line subject>

**Written:** YYYY-MM-DD HH:MM <TZ>. **Read when:** <the situation that makes this file relevant>.

## TL;DR
- 2-5 bullets: the outcome and the rules that matter most.

## Rules we now follow        (failures files: put this first)
1. **<Imperative rule>.** Why, in one sentence. *(evidence: file, command or ID)*

## What happened / decisions   (session files)
- <Decision or event> — because <reason>. Rejected: <alternative> (<why>).

## What broke (one line each)  (failures files)
- (H/M/L) <ID> <symptom> → <root cause> → <fix or status>.

## Facts and sources           (recon files)
- <Fact>. Source: <URL or doc>. Checked: YYYY-MM-DD. Re-check by: <date or trigger>.

## How to re-check
- `<command>`: what a pass or fail means.

## Open items
- [ ] <human or agent follow-up>. Not verified: <what and why>.
```

Writing style: short sentences, concrete names (paths, commands, rule IDs),
imperative rules, severity or status tags where useful. A human should get the
gist from the TL;DR; an agent should be able to act from the rules and commands
without reading anything else. Link related files with relative links.

Example of one good rule line (specific, causal, re-checkable):

```markdown
17. **Every command in `permissions.allow` must be safe to run unattended, including `make run`.** It launches agent-written code with the user's file access. *(G-07; check: `grep -n "make run" .claude/settings.json`)*
```

A weak version to avoid: "Be careful with permissions." (no cause, no check).

## 5. Update the index

If a `README.md` exists in the folder, add one row per new file at the top of
its index (newest first) with a one-line summary, matching the existing format.
If none exists, create a short one: purpose, the file-name pattern, the kinds
table, the rules ("important things only", "no secrets", "append-only"), and the
index. If the README has a checklist for the next session, add only lessons that
are genuinely new.

## 6. Rules for the files themselves

- **Append-only.** Never edit or delete an existing dated file. To correct an
  old fact, write a new file that says "supersedes <file>". Only `README.md`
  (the index) is edited in place.
- Do not paste whole transcripts or logs; quote the one line that proves a point.
- Do not run commit or push. Tell the user which files were written and let
  them decide.

## 7. Finish

Reply with the list of files written (as links), a one-line summary of each, and
anything you left out on purpose or could not verify.
