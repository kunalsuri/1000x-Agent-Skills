---
name: readme-designer
version: 2.0.0
author: Kunal Suri <kunal.suri@cea.fr>
description: Rewrite a README so a reader can tell what the project is and run it without scrolling, then check the result against a scoring rubric and fix every broken link. Cuts bloat, ornament and self-awarded badges; keeps the promise, the command, the output and the links. Use when creating, redesigning, modernizing, shortening, improving the readability of, or polishing a project README, repository documentation, or landing page.
compatibility: [claude-code, antigravity, cursor, codex]
allowed-tools: [run_command, view_file, write_to_file, replace_file_content]
tags: [readme, documentation, technical-writing, markdown, editing, open-source]
license: Apache-2.0
---

# README Designer

Make a README a reader finishes.

## What this optimises for

A README is read by someone deciding, in about twenty seconds, whether this
project is worth their afternoon. They want to know what it is, see it run,
and find the rest. Everything that delays those three things is cost.

This skill previously optimised for the opposite. Its rubric awarded points
for `<br/>` tags, hero banners, badge rows, Mermaid diagrams and callouts,
and rubrics get optimised against: the result was a 736-line README that
scored A+ while the one command a reader needed sat at line 470. Version 2
pays for orientation, substance, restraint, brevity and working links, and
pays nothing for looks.

## The rubric

`scripts/audit_readme.py` scores out of 100. Every number below is a
deliberate opinion, not a measurement:

| Dimension | Points | What earns them |
|---|---|---|
| Orientation | 20 | An `# H1`; a plain sentence saying what this is within 15 lines; the first runnable command within 40 lines. |
| Substance | 25 | A command block; real output; an install or usage heading; a licence; how to test and contribute. |
| Restraint | 20 | Few or no `<br/>` tags, at most five badges, emoji under 8 per 100 lines, no self-awarded grade badges. |
| Brevity | 15 | 200 lines or fewer. 350 is acceptable; past 600 it is a manual, not a README. |
| Links | 20 | Every relative path exists and every anchor matches a header. Broken links are the only hard error. |

`--strict` exits 1 unless the file scores 80 or more with no broken link.

## Workflow

### 1. Audit before touching anything

```bash
python skills/custom/readme-designer/scripts/audit_readme.py --target README.md
```

Read `first_command_line` and `line_count` first. They usually explain the
score on their own.

### 2. Cut before you write

Most bad READMEs are not badly written, they are too long. In order:

1. **Move reference material to `docs/`** and link it. Repository trees,
   full CLI catalogues, specification tables, architecture essays.
2. **Delete every `<br/>`.** Markdown already separates blocks. The tags are
   layout by padding and cost the reader scrolling.
3. **Delete decorative badges.** Keep the ones a reader acts on: build
   status, licence, version. A badge the project awards itself -- a grade, a
   score, "production ready" -- reads as evidence and is not; the auditor
   warns about these by name.
4. **Delete the emoji that mark nothing.** When every heading has one, none
   of them is a signal.
5. **Delete diagrams that restate the text.** A diagram earns its place by
   showing something prose cannot: a real flow, a real shape.

If the archived original is worth keeping, keep it -- `docs/archive/` with a
note at the top, links rewritten for the new location.

### 3. Structure what remains

```markdown
# Project Name

One or two sentences: what this is, who it is for. No tagline in italics.

## The thing to try first

The single command, then its real output in a ```text block.

## Install / Usage

The other commands, with what they print.

## How it works

Two or three paragraphs. Longer goes to docs/ with a link.

## Contributing

How to run the tests and send a change.

## License
```

Order by what a reader needs, not by what the project is proud of. If the
project has one thing worth trying, put a real run of it -- real command,
real output -- above everything else.

### 4. Write honestly

- **Claims match evidence.** "Checks passing" with a CI badge, not "Grade A"
  from your own tool. If a number is not measured, do not print it.
- **Say what is unfinished.** One line of "work in progress, here is what is
  and is not verified" buys more trust than any badge.
- **Cut adjectives.** "Ultra-modern, world-class, blazing-fast" is noise a
  reader discounts. The command and its output are the argument.

### 5. Re-audit until it passes

```bash
python skills/custom/readme-designer/scripts/audit_readme.py --target README.md --strict
```

Fix broken links first -- they are the only defect here that is unambiguously
wrong. Then read the top recommendations; each names the reader cost.

## Starting from nothing

```bash
python skills/custom/readme-designer/scripts/scaffold_readme.py \
  --name "Project Name" --tagline "A tool that does one thing well" \
  --output README.md
```

The template is deliberately short and scores 100 on the rubric above. It is
meant to be edited **down**, not up: a template that ships placeholders for a
banner, a badge wall and a diagram gets them filled in rather than deleted.

## What this skill will not do

- It will not add decoration to raise a score. If a change would not help a
  reader, it does not belong in the file.
- It will not invent metrics, grades or endorsements to fill a badge row.
- It will not delete content it cannot see a home for. Long material moves to
  `docs/` and gets linked; it is not silently dropped.

## Auditing other Markdown

The rubric assumes a README. Pointed at a guide or a specification, the
brevity and orientation checks are the wrong shape -- a specification is
supposed to be long. Use the link-integrity result, which is universal, and
read the rest as advice rather than as a grade.
