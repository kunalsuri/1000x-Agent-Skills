#!/usr/bin/env python3
"""
README & Documentation Quality Auditor CLI.
Audits Markdown documentation for visual hierarchy, spacing, badges,
comparative tables, diagrams, link integrity, and completeness.
"""

import sys
import os
import re
import argparse
from pathlib import Path

def slugify_header(text: str) -> str:
    """Converts header text to standard GitHub markdown anchor slugs."""
    text = re.sub(r'<[^>]+>', '', text)  # remove HTML tags
    text = text.lower().strip()
    # Remove emoji and punctuation except hyphens and alphanumeric
    text = re.sub(r'[^\w\s-]', '', text)
    # Convert spaces to single hyphens
    slug = re.sub(r'\s+', '-', text).strip('-')
    return slug

def audit_markdown_file(file_path: Path, workspace_root: Path) -> dict:
    if not file_path.exists():
        return {
            "file": str(file_path),
            "score": 0,
            "grade": "F",
            "passed": False,
            "errors": [f"File not found: {file_path}"],
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

    # 1. Check Hero / Center Header (15 pts)
    has_centered_hero = bool(re.search(r'<div\s+align=[\'"]center[\'"]>', content, re.IGNORECASE))
    has_h1 = any(line.startswith("# ") for line in lines)
    has_tagline = bool(re.search(r'^###\s+\*.*\*', content, re.MULTILINE))
    has_badges = bool(re.search(r'img\.shields\.io', content))
    has_nav_bar = bool(re.search(r'\[\*\*.*?\*\*\]\(#.*?\)', content))

    hero_pts = 0
    if has_centered_hero: hero_pts += 3
    if has_h1: hero_pts += 3
    if has_tagline: hero_pts += 3
    if has_badges: hero_pts += 3
    if has_nav_bar: hero_pts += 3
    score += hero_pts
    metrics["hero_section_pts"] = f"{hero_pts}/15"

    if not has_centered_hero:
        recommendations.append("Consider wrapping your main title, tagline, and badges in a centered hero (<div align='center'>).")
    if not has_badges:
        recommendations.append("Add status shields/badges (e.g., license, version, tests, spec) for immediate credibility.")
    if not has_nav_bar:
        recommendations.append("Add a quick navigation link bar directly under the hero badges.")

    # 2. Check Breathing Room & Spacing (20 pts)
    br_count = len(re.findall(r'<br\s*/?>', content, re.IGNORECASE))
    divider_count = len(re.findall(r'^---$', content, re.MULTILINE))
    bold_count = len(re.findall(r'\*\*.*?\*\*', content))

    spacing_pts = 0
    if br_count >= 8:
        spacing_pts += 8
    elif br_count >= 4:
        spacing_pts += 5
    elif br_count >= 1:
        spacing_pts += 2
    else:
        recommendations.append("Add purposeful <br/> spacing tags around headers and major sections to improve reading flow.")

    if divider_count >= 4:
        spacing_pts += 6
    elif divider_count >= 2:
        spacing_pts += 4
    else:
        recommendations.append("Add thematic dividers (---) between major sections for distinct visual partitioning.")

    if bold_count >= 10:
        spacing_pts += 6
    elif bold_count >= 4:
        spacing_pts += 3

    score += spacing_pts
    metrics["spacing_and_typography_pts"] = f"{spacing_pts}/20"
    metrics["br_tags_count"] = br_count
    metrics["dividers_count"] = divider_count
    metrics["bold_elements_count"] = bold_count

    # 3. Check Visual Artifacts: Diagrams, Alerts, Tables (25 pts)
    has_mermaid = "```mermaid" in content
    has_ascii_box = bool(re.search(r'┌[─┬]+┐', content))
    has_github_alerts = bool(re.search(r'>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', content))
    has_tables = bool(re.search(r'\|[-:]+\|', content))
    has_code_blocks = len(re.findall(r'```[a-z0-9_-]*\n', content)) >= 2

    visual_pts = 0
    if has_mermaid or has_ascii_box: visual_pts += 8
    if has_github_alerts: visual_pts += 5
    if has_tables: visual_pts += 6
    if has_code_blocks: visual_pts += 6
    score += visual_pts
    metrics["visual_elements_pts"] = f"{visual_pts}/25"

    if not (has_mermaid or has_ascii_box):
        recommendations.append("Include a Mermaid flowchart/sequence diagram or ASCII architecture frame to visualize runtime flow.")
    if not has_github_alerts:
        recommendations.append("Use GitHub alert callouts (> [!NOTE], > [!TIP], > [!IMPORTANT]) to emphasize essential insights.")
    if not has_tables:
        recommendations.append("Add a comparative matrix or feature table instead of plain long lists.")

    # 4. Essential Sections Completeness (25 pts)
    section_checks = {
        "1-Liner / Quick Install": bool(re.search(r'(quick install|instant install|one-liner|1-liner|installation)', content, re.IGNORECASE)),
        "Overview / Problem Statement": bool(re.search(r'(what is|overview|problem|why\s+)', content, re.IGNORECASE)),
        "Core Pillars / Architecture": bool(re.search(r'(architecture|pillars|specification|design|how it works)', content, re.IGNORECASE)),
        "Quickstart / Usage": bool(re.search(r'(quickstart|usage|getting started|how to use)', content, re.IGNORECASE)),
        "Governance / License": bool(re.search(r'(license|governance|contributing|security)', content, re.IGNORECASE)),
    }

    sec_pts = sum(5 for present in section_checks.values() if present)
    score += sec_pts
    metrics["sections_pts"] = f"{sec_pts}/25"

    for sec_name, present in section_checks.items():
        if not present:
            recommendations.append(f"Add a dedicated section for: '{sec_name}'.")

    # 5. Link & Anchor Integrity (15 pts)
    all_headers = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    header_slugs = set(slugify_header(h) for h in all_headers)

    # Relative links and anchor check
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

    link_pts = 15
    if broken_links:
        link_pts = max(0, 15 - (len(broken_links) * 5))
        errors.extend(broken_links)
    score += link_pts
    metrics["link_integrity_pts"] = f"{link_pts}/15"

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

    parser = argparse.ArgumentParser(description="Audit README and Markdown files for visual design and structure.")
    parser.add_argument("--target", default="README.md", help="Path to README.md or markdown file to audit.")
    parser.add_argument("--strict", action="store_true", help="Fail if score is below 90 or any error is found.")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    workspace_root = Path.cwd().resolve()

    res = audit_markdown_file(target_path, workspace_root)

    print("=" * 72)
    print(" 🎨 [README DESIGNER] Markdown Visual Hierarchy & Quality Audit")
    print("=" * 72)
    print(f" Target File   : {res['file']}")
    print(f" Quality Score : {res['score']}/100 — Grade {res['grade']}")
    print("-" * 72)
    print(" Metrics Breakdown:")
    for k, v in res["metrics"].items():
        print(f"   • {k:<28}: {v}")
    print("-" * 72)

    if res["errors"]:
        print(" ❌ Errors / Broken Links Detected:")
        for err in res["errors"]:
            print(f"   - {err}")
        print("-" * 72)

    if res["recommendations"]:
        print(" 💡 Recommended Visual & Content Enhancements:")
        for rec in res["recommendations"][:5]:
            print(f"   • {rec}")
        print("-" * 72)

    if res["passed"]:
        print(" ✨ AUDIT RESULT: PASSED (Documentation meets world-class visual standards!)")
    else:
        print(" ⚠️  AUDIT RESULT: NEEDS IMPROVEMENT (Apply recommendations above)")
    print("=" * 72)

    if args.strict and (not res["passed"] or res["score"] < 90):
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
