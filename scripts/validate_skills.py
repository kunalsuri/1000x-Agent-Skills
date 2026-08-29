#!/usr/bin/env python3
"""
Skill Validator CLI for 1000x-Agent-Skills.
Validates all skills against the Agent Skills specification, attestation requirements,
and evaluation test coverage.
"""

import sys
import os
import re
import json
from pathlib import Path

def validate_skill(skill_dir: Path) -> dict:
    errors = []
    warnings = []
    skill_md = skill_dir / "SKILL.md"
    attestation_json = skill_dir / "attestation.json"
    evals_json = skill_dir / "evals" / "test-cases.json"

    if not skill_md.exists():
        return {"name": skill_dir.name, "errors": ["Missing SKILL.md file."], "warnings": []}

    content = skill_md.read_text(encoding="utf-8")
    
    # 1. Frontmatter Validation
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if not fm_match:
        errors.append("Missing YAML frontmatter (enclosed by '---').")
    else:
        fm_text = fm_match.group(1)
        
        # Name check
        name_match = re.search(r"^name:\s*([^\r\n]+)", fm_text, re.MULTILINE)
        if not name_match:
            errors.append("Frontmatter missing 'name' field.")
        else:
            name = name_match.group(1).strip().strip("'\"")
            if name != skill_dir.name:
                errors.append(f"Skill name '{name}' does not match directory name '{skill_dir.name}'.")
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                errors.append(f"Invalid name format '{name}'. Must be lowercase alphanumeric with single hyphens.")

        # Description check
        desc_match = re.search(r"^description:\s*(.*?)(?=\n[a-z0-9_-]+:|\Z)", fm_text, re.DOTALL | re.MULTILINE)
        if not desc_match:
            errors.append("Frontmatter missing 'description' field.")
        else:
            desc = " ".join(desc_match.group(1).split())
            if len(desc) > 1024:
                errors.append(f"Description exceeds 1024 characters ({len(desc)} chars).")
            if not re.search(r"(use when|trigger|when)", desc, re.IGNORECASE):
                warnings.append("Description should contain explicit trigger context (e.g. 'Use when...').")

        # Version check
        if not re.search(r"^version:\s*\d+\.\d+\.\d+", fm_text, re.MULTILINE):
            warnings.append("Missing semantic version (e.g., 'version: 1.0.0').")

    # 2. Body Length Check
    lines = content.splitlines()
    if len(lines) > 500:
        warnings.append(f"SKILL.md is {len(lines)} lines (> 500 lines limit). Move references to references/.")

    # 3. Attestation check
    if not attestation_json.exists():
        warnings.append("Missing attestation.json (skill is un-attested).")
    else:
        try:
            att_data = json.loads(attestation_json.read_text(encoding="utf-8"))
            if not att_data.get("attestation_status"):
                warnings.append("attestation.json missing 'attestation_status'.")
        except Exception as e:
            errors.append(f"Malformed attestation.json: {e}")

    # 4. Evaluation test-cases check
    if not evals_json.exists():
        warnings.append("Missing evals/test-cases.json.")

    return {
        "name": skill_dir.name,
        "path": str(skill_dir),
        "errors": errors,
        "warnings": warnings,
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS")
    }

def main():
    # Force UTF-8 output encoding if possible
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    repo_root = Path(__file__).resolve().parent.parent
    skills_root = repo_root / "skills"
    
    if not skills_root.exists():
        print(f"[ERROR] Skills directory not found at {skills_root}")
        sys.exit(1)

    all_results = []
    print("=" * 65)
    print(" [SKILL DOCTOR] 1000x-Agent-Skills Validation Suite")
    print("=" * 65)

    for cat_dir in sorted(skills_root.iterdir()):
        if cat_dir.is_dir():
            for skill_dir in sorted(cat_dir.iterdir()):
                if skill_dir.is_dir():
                    res = validate_skill(skill_dir)
                    all_results.append(res)
                    icon = "[PASS]" if res["status"] == "PASS" else ("[WARN]" if res["status"] == "WARN" else "[FAIL]")
                    print(f"{icon} [{cat_dir.name}/{res['name']}] -> {res['status']}")
                    for err in res["errors"]:
                        print(f"    - Error: {err}")
                    for warn in res["warnings"]:
                        print(f"    - Warn:  {warn}")

    total = len(all_results)
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    warned = sum(1 for r in all_results if r["status"] == "WARN")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")

    # 5. Verify README.md Catalog Parity
    readme_errors = []
    readme_path = repo_root / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
        # Match links to skills: ./skills/<category>/<skill-name>/...
        referenced_skills = re.findall(r'\(\.?/?skills/([a-z0-9_-]+)/([a-z0-9_-]+)(?:/SKILL\.md)?\)', readme_content)
        for cat, name in referenced_skills:
            target_skill_dir = skills_root / cat / name
            if not target_skill_dir.exists() or not (target_skill_dir / "SKILL.md").exists():
                readme_errors.append(f"README.md references non-existent skill '{name}' in category '{cat}'.")

    if readme_errors:
        print("\n [README AUDIT] ❌ Found mismatched or phantom skills in README.md:")
        for r_err in readme_errors:
            print(f"    - {r_err}")
        failed += len(readme_errors)
    else:
        print("\n [README AUDIT] ✅ README.md skills catalog matches physical filesystem 1:1.")

    print("\n" + "=" * 65)
    print(f" Summary: {total} skills scanned | {passed} Passed | {warned} Warnings | {failed} Failed")
    print("=" * 65)

    if failed > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()

