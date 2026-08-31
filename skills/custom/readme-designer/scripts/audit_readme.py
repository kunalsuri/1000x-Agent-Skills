#!/usr/bin/env python3
"""
README quality auditor.

Grades a README the way a reader meets it: can they tell what this is, and
run it, without scrolling? Ornament is scored too -- downward, once it
outruns the content it decorates.

An earlier version of this rubric awarded points for `<br/>` tags, hero
divs, badge rows, Mermaid diagrams and callouts. Rubrics get optimised
against, and that one paid for decoration, so it grew 700-line READMEs that
scored A+ while burying the one command a reader needed. The checks below
pay for orientation, substance, restraint, brevity and working links --
nothing for looks.
"""

import sys
import re
import argparse
from pathlib import Path

# A README is an entry point. Past these, the content belongs in docs/.
LINE_BUDGET_EXCELLENT = 200
LINE_BUDGET_ACCEPTABLE = 350
LINE_BUDGET_BLOATED = 600

# Where a reader should have met the first runnable command.
FIRST_COMMAND_EXCELLENT = 40
FIRST_COMMAND_ACCEPTABLE = 80

COMMAND_LANGUAGES = ("bash", "sh", "shell", "console", "zsh", "powershell", "ps1")

# Badges nobody can check: a grade, a score or a seal the project awards to
# itself. They read as evidence and are not, which is worse than no badge.
SELF_AWARDED_BADGE_RE = re.compile(
    r"!\[[^\]]*\]\(https://img\.shields\.io/badge/[^)]*"
    r"(grade|quality|score|health|verified|certified|production[-_%]?ready|100%25|A%2B)",
    re.IGNORECASE,
)
BADGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)]*(?:shields\.io|badge)[^)]*)\)",
                      re.IGNORECASE)
EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F000-\U0001F2FF"
    "\U00002B00-\U00002BFF" "\U0000FE0F" "]"
)
FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")


def slugify_header(text: str) -> str:
    """Converts header text to standard GitHub markdown anchor slugs."""
    text = re.sub(r'<[^>]+>', '', text)  # remove HTML tags
    text = text.lower().strip()
    # Remove emoji and punctuation except hyphens and alphanumeric
    text = re.sub(r'[^\w\s-]', '', text)
    # Convert spaces to single hyphens
    slug = re.sub(r'\s+', '-', text).strip('-')
    return slug


def code_blocks(lines: list) -> list:
    """Every fenced block as (language, start_line_number, body)."""
    blocks = []
    language = None
    start = 0
    body: list = []
    for index, line in enumerate(lines, start=1):
        match = FENCE_RE.match(line.strip())
        if match and language is None:
            language, start, body = match.group(1).lower(), index, []
        elif line.strip().startswith("```") and language is not None:
            blocks.append((language, start, "\n".join(body)))
            language = None
        elif language is not None:
            body.append(line)
    return blocks


def first_meaningful_prose(lines: list) -> int:
    """
    Line number of the first sentence of plain prose after the H1.

    HTML, badges, links-only lines and an italic tagline are not it: a reader
    who has just landed needs a sentence saying what the thing is.
    """
    seen_h1 = False
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not seen_h1:
            seen_h1 = stripped.startswith("# ")
            continue
        if not stripped or stripped.startswith(("#", "<", ">", "|", "```", "---")):
            continue
        if stripped.startswith(("[", "![", "*", "_")) and stripped.endswith(("]", ")", "*", "_")):
            continue
        without_marks = re.sub(r"[*_`]", "", stripped)
        if len(without_marks.split()) >= 6:
            return index
    return 0


def audit_markdown_file(file_path: Path, workspace_root: Path) -> dict:
    if not file_path.exists():
        return {
            "file": str(file_path),
            "score": 0,
            "grade": "F",
            "passed": False,
            "errors": [f"File not found: {file_path}"],
            "warnings": [],
            "metrics": {},
            "recommendations": []
        }

    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    score = 0
    max_score = 100
    errors = []
    warnings = []
    recommendations = []
    metrics = {}

    blocks = code_blocks(lines)
    headers = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    header_text = " \n ".join(headers).lower()
    body_lower = content.lower()

    # 1. Orientation (20 pts) -- what a reader gets before scrolling.
    orientation_pts = 0
    has_h1 = any(line.startswith("# ") for line in lines)
    if has_h1:
        orientation_pts += 5
    else:
        recommendations.append("Start with a single `# Title` line -- it is the "
                               "first thing a reader and every renderer looks for.")

    prose_line = first_meaningful_prose(lines)
    if prose_line and prose_line <= 15:
        orientation_pts += 5
    elif prose_line:
        orientation_pts += 2
        recommendations.append(
            f"The first sentence describing the project is at line {prose_line}. "
            f"Say what this is immediately after the title; badges and navigation "
            f"can wait.")
    else:
        recommendations.append("No plain-language sentence says what this project "
                               "is. A tagline in italics is not that sentence.")

    command_blocks = [b for b in blocks if b[0] in COMMAND_LANGUAGES]
    first_command = command_blocks[0][1] if command_blocks else 0
    metrics["first_command_line"] = first_command or "none"
    if first_command and first_command <= FIRST_COMMAND_EXCELLENT:
        orientation_pts += 10
    elif first_command and first_command <= FIRST_COMMAND_ACCEPTABLE:
        orientation_pts += 5
        recommendations.append(
            f"The first runnable command is at line {first_command}. Move it "
            f"above the architecture and the philosophy -- it is what most "
            f"readers came for.")
    elif first_command:
        recommendations.append(
            f"The first runnable command is at line {first_command}, past where "
            f"almost nobody scrolls. Lead with it.")
    else:
        recommendations.append("No runnable command anywhere. Show the one command "
                               "that installs or runs this.")
    score += orientation_pts
    metrics["orientation_pts"] = f"{orientation_pts}/20"

    # 2. Substance (25 pts) -- the things a reader actually needs.
    substance_pts = 0
    if command_blocks:
        substance_pts += 6
    output_blocks = [b for b in blocks if b[0] in ("text", "txt", "output", "json", "yaml")]
    if output_blocks or len(blocks) >= 3:
        substance_pts += 5
    else:
        recommendations.append("Show what the command prints. Real output is the "
                               "cheapest proof that the project works.")
    if re.search(r"(install|quickstart|getting started|usage|run it)", header_text):
        substance_pts += 5
    else:
        recommendations.append("Add an install or usage heading a reader can jump to.")
    if re.search(r"\((\./)?LICEN[SC]E", content) or "license" in header_text:
        substance_pts += 4
    else:
        recommendations.append("State the licence and link the LICENSE file.")
    if re.search(r"(contribut|development|dev-test|hacking|pull request)", body_lower):
        substance_pts += 5
    else:
        recommendations.append("Say how someone runs the tests and sends a change.")
    score += substance_pts
    metrics["substance_pts"] = f"{substance_pts}/25"

    # 3. Restraint (20 pts) -- decoration is scored downward past the point
    #    where it stops helping a reader and starts costing them scrolling.
    br_count = len(re.findall(r'<br\s*/?>', content, re.IGNORECASE))
    badges = BADGE_RE.findall(content)
    self_awarded = SELF_AWARDED_BADGE_RE.findall(content)
    emoji_count = len(EMOJI_RE.findall(content))
    emoji_density = (emoji_count / max(len(lines), 1)) * 100

    restraint_pts = 0
    if br_count == 0:
        restraint_pts += 8
    elif br_count <= 3:
        restraint_pts += 5
    elif br_count <= 10:
        restraint_pts += 2
        recommendations.append(f"{br_count} `<br/>` tags. Blank lines already "
                               f"separate blocks in Markdown; the tags mostly add "
                               f"scrolling.")
    else:
        recommendations.append(f"{br_count} `<br/>` tags is layout by padding. "
                               f"Delete them and let the content set the rhythm.")

    if self_awarded:
        warnings.append(
            f"{len(self_awarded)} self-awarded badge(s) (grade, score, quality or "
            f"'verified'). A project grading itself is not evidence; link a CI run "
            f"or drop the badge.")
    elif len(badges) <= 5:
        restraint_pts += 6
    elif len(badges) <= 8:
        restraint_pts += 3
        recommendations.append(f"{len(badges)} badges. Keep the ones a reader acts "
                               f"on -- build status, licence, version.")
    else:
        recommendations.append(f"{len(badges)} badges is a wall. Three or four earn "
                               f"their place; the rest are noise.")

    if emoji_density <= 8:
        restraint_pts += 6
    elif emoji_density <= 20:
        restraint_pts += 3
    else:
        recommendations.append(f"{emoji_count} emoji across {len(lines)} lines. Past "
                               f"a point they stop marking anything, because "
                               f"everything is marked.")
    score += restraint_pts
    metrics["restraint_pts"] = f"{restraint_pts}/20"
    metrics["br_tags_count"] = br_count
    metrics["badge_count"] = len(badges)
    metrics["emoji_count"] = emoji_count

    # 4. Brevity (15 pts) -- a README is an entry point, not the manual.
    line_count = len(lines)
    if line_count <= LINE_BUDGET_EXCELLENT:
        brevity_pts = 15
    elif line_count <= LINE_BUDGET_ACCEPTABLE:
        brevity_pts = 10
    elif line_count <= LINE_BUDGET_BLOATED:
        brevity_pts = 4
        recommendations.append(f"{line_count} lines. Move the reference material to "
                               f"docs/ and link it; the README is the doorway.")
    else:
        brevity_pts = 0
        recommendations.append(f"{line_count} lines is a manual, not a README. Nobody "
                               f"reads to the end. Cut it to the promise, the "
                               f"command, and links.")
    score += brevity_pts
    metrics["brevity_pts"] = f"{brevity_pts}/15"
    metrics["line_count"] = line_count

    # 5. Link & anchor integrity (20 pts) -- the only hard defect here.
    header_slugs = set(slugify_header(h) for h in headers)
    link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    broken_links = []

    for text, target in link_matches:
        target = target.strip()
        if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
            continue
        elif target.startswith("#"):
            raw_anchor = target[1:].lower().strip()
            clean_anchor = re.sub(r'-+', '-', re.sub(r'^[-\s]+|[-\s]+$', '', raw_anchor))
            # Match against raw or cleaned slug variants
            matched = any(
                clean_anchor in re.sub(r'-+', '-', s) or re.sub(r'-+', '-', s) in clean_anchor or raw_anchor == s
                for s in header_slugs
            )
            if not matched and clean_anchor:
                broken_links.append(f"Anchor '{target}' (link text: '{text}') does not match any header in document.")
        else:
            clean_target = target.split("#")[0].split("?")[0]
            if clean_target:
                target_path = (file_path.parent / clean_target).resolve()
                if not target_path.exists():
                    broken_links.append(f"Relative path '{target}' does not exist on disk.")

    link_pts = max(0, 20 - (len(broken_links) * 5))
    errors.extend(broken_links)
    score += link_pts
    metrics["link_integrity_pts"] = f"{link_pts}/20"

    # Compute Final Grade
    if score >= 90: grade = "A+"
    elif score >= 80: grade = "A"
    elif score >= 70: grade = "B"
    elif score >= 55: grade = "C"
    else: grade = "F"

    return {
        "file": str(file_path),
        "score": min(score, max_score),
        "grade": grade,
        "passed": score >= 80 and len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "recommendations": recommendations
    }


def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description="Audit a README for orientation, substance, restraint, "
                    "brevity and link integrity.")
    parser.add_argument("--target", default="README.md", help="Path to README.md or markdown file to audit.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 unless the file passes: score >= 80 with no "
                             "broken links.")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    workspace_root = Path.cwd().resolve()

    res = audit_markdown_file(target_path, workspace_root)

    print("=" * 72)
    print(" [README AUDIT] orientation, substance, restraint, brevity, links")
    print("=" * 72)
    print(f" Target File   : {res['file']}")
    print(f" Quality Score : {res['score']}/100 - Grade {res['grade']}")
    print("-" * 72)
    print(" Metrics Breakdown:")
    for k, v in res["metrics"].items():
        print(f"   - {k:<28}: {v}")
    print("-" * 72)

    if res["errors"]:
        print(" Errors / broken links:")
        for err in res["errors"]:
            print(f"   - {err}")
        print("-" * 72)

    if res["warnings"]:
        print(" Warnings:")
        for warn in res["warnings"]:
            print(f"   - {warn}")
        print("-" * 72)

    if res["recommendations"]:
        print(" What would help a reader most:")
        for rec in res["recommendations"][:5]:
            print(f"   - {rec}")
        print("-" * 72)

    if res["passed"]:
        print(" AUDIT RESULT: PASSED -- a reader can orient, run something, and "
              "every link resolves.")
    else:
        print(" AUDIT RESULT: NEEDS IMPROVEMENT (apply the notes above)")
    print("=" * 72)

    if args.strict and not res["passed"]:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
