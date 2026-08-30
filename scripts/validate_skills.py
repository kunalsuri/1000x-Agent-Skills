#!/usr/bin/env python3
"""
Skill Doctor & Specification Validator CLI for 1000x-Agent-Skills.
Validates all skills against the Agent Skills Open Specification,
frontmatter token budgets, line limits, attestation schemas, and evaluation datasets.
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "attestation.schema.json"

# Digest verification lives alongside this file. Importing it by path keeps
# `python scripts/validate_skills.py` working from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_digest import verify_skill as verify_skill_digest  # noqa: E402

# jsonschema is optional on purpose. The structural checks below are
# stdlib-only so anyone can validate a skill without installing anything;
# when jsonschema IS available (as it is in CI) the full schema runs too.
try:
    import jsonschema  # type: ignore
    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - exercised by the no-dependency path
    _HAS_JSONSCHEMA = False

CAPABILITY_KEYS = ("network", "process_execution", "dynamic_code_execution", "filesystem")


def load_attestation_schema():
    """Return the parsed attestation schema, or None when it is unavailable."""
    if not SCHEMA_PATH.exists():
        return None
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def estimate_tokens(text: str) -> int:
    """Heuristic token estimation (~4 chars/token or word split)."""
    return max(1, len(re.findall(r'\w+|[^\w\s]', text)))

def validate_skill(skill_dir: Path) -> dict:
    errors = []
    warnings = []
    score = 100
    metrics = {}

    skill_md = skill_dir / "SKILL.md"
    attestation_json = skill_dir / "attestation.json"
    evals_json = skill_dir / "evals" / "test-cases.json"

    if not skill_md.exists():
        return {
            "name": skill_dir.name,
            "path": str(skill_dir),
            "errors": ["Missing SKILL.md file."],
            "warnings": [],
            "score": 0,
            "grade": "F",
            "status": "FAIL",
            "metrics": {}
        }

    content = skill_md.read_text(encoding="utf-8", errors="replace")
    
    # 1. Frontmatter Validation
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if not fm_match:
        errors.append("Missing YAML frontmatter (enclosed by '---').")
        score -= 40
    else:
        fm_text = fm_match.group(1)
        fm_tokens = estimate_tokens(fm_text)
        metrics["frontmatter_tokens"] = fm_tokens
        
        if fm_tokens > 200:
            warnings.append(f"Frontmatter is ~{fm_tokens} tokens (> 150 token budget). Consider trimming description.")
            score -= 10
        
        # Name check
        name_match = re.search(r"^name:\s*([^\r\n]+)", fm_text, re.MULTILINE)
        if not name_match:
            errors.append("Frontmatter missing 'name' field.")
            score -= 20
        else:
            name = name_match.group(1).strip().strip("'\"")
            if name != skill_dir.name:
                errors.append(f"Skill name '{name}' does not match directory name '{skill_dir.name}'.")
                score -= 15
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                errors.append(f"Invalid name format '{name}'. Must be lowercase alphanumeric with single hyphens.")
                score -= 10

        # Description check
        desc_match = re.search(r"^description:\s*(.*?)(?=\n[a-z0-9_-]+:|\Z)", fm_text, re.DOTALL | re.MULTILINE)
        if not desc_match:
            errors.append("Frontmatter missing 'description' field.")
            score -= 20
        else:
            desc = " ".join(desc_match.group(1).split())
            if len(desc) > 1024:
                errors.append(f"Description exceeds 1024 characters ({len(desc)} chars).")
                score -= 10
            if not re.search(r"(use when|trigger|when)", desc, re.IGNORECASE):
                warnings.append("Description should contain explicit trigger context (e.g. 'Use when...').")
                score -= 5

        # Version check
        if not re.search(r"^version:\s*\d+\.\d+\.\d+", fm_text, re.MULTILINE):
            warnings.append("Missing semantic version (e.g., 'version: 1.0.0').")
            score -= 5

    # 2. Body Length Check
    lines = content.splitlines()
    body_lines = len(lines)
    metrics["body_lines"] = body_lines

    if body_lines > 500:
        warnings.append(f"SKILL.md is {body_lines} lines (> 500 lines limit). Move references to references/.")
        score -= 15

    # 3. Attestation: schema conformance, declared capabilities, content binding.
    #    Checking that the string "VERIFIED" is merely present proves nothing --
    #    anyone can type it. These three checks are what make the badge mean
    #    something: it conforms to a published schema, it declares what the code
    #    may do, and it is bound to the exact bytes it was granted for.
    if not attestation_json.exists():
        errors.append("Missing attestation.json (skill is un-attested and cannot be verified).")
        score -= 25
    else:
        try:
            att_data = json.loads(attestation_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"Malformed attestation.json: {e}")
            score -= 25
            att_data = None

        if att_data is not None:
            metrics["attestation_status"] = att_data.get("attestation_status", "UNKNOWN")

            schema = load_attestation_schema()
            if schema is None:
                warnings.append(
                    "docs/schemas/attestation.schema.json is missing; attestation "
                    "content could not be validated against a schema."
                )
                score -= 5
            elif _HAS_JSONSCHEMA:
                validator = jsonschema.Draft202012Validator(schema)
                for err in sorted(validator.iter_errors(att_data), key=lambda e: list(e.path)):
                    location = "/".join(str(part) for part in err.path) or "(root)"
                    errors.append(f"attestation.json fails schema at '{location}': {err.message}")
                    score -= 10
            else:
                # Stdlib fallback: enforce the schema's required top-level keys
                # so a missing declaration still fails without jsonschema present.
                for key in schema.get("required", []):
                    if key not in att_data:
                        errors.append(f"attestation.json missing required field '{key}'.")
                        score -= 10

            capabilities = att_data.get("capabilities")
            if not isinstance(capabilities, dict):
                errors.append(
                    "attestation.json has no 'capabilities' object. Without it "
                    "scripts/audit_skill_safety.py has nothing to enforce the code against."
                )
                score -= 15
            else:
                missing_caps = [k for k in CAPABILITY_KEYS if k not in capabilities]
                if missing_caps:
                    errors.append(f"attestation.json capabilities missing: {missing_caps}.")
                    score -= 10
                else:
                    metrics["capabilities"] = ",".join(
                        f"{k}={capabilities[k]}" for k in CAPABILITY_KEYS
                    )

        digest_ok, digest_detail = verify_skill_digest(skill_dir)
        if digest_ok:
            metrics["content_digest"] = digest_detail[:19] + "..."
        else:
            errors.append(f"Content digest check failed: {digest_detail}")
            score -= 25

    # 4. Evaluation test-cases check
    if not evals_json.exists():
        warnings.append("Missing evals/test-cases.json.")
        score -= 10
    else:
        try:
            eval_data = json.loads(evals_json.read_text(encoding="utf-8"))
            pos = eval_data.get("trigger_evaluation", {}).get("positive_prompts", [])
            neg = eval_data.get("trigger_evaluation", {}).get("negative_prompts", [])
            metrics["eval_prompts_count"] = f"{len(pos)} pos / {len(neg)} neg"
            if len(pos) < 3:
                warnings.append(f"evals/test-cases.json has only {len(pos)} positive prompts (recommend >= 3).")
                score -= 5
        except Exception as e:
            errors.append(f"Malformed evals/test-cases.json: {e}")
            score -= 10

    # Grade computation
    score = max(0, min(100, score))
    if score >= 90: grade = "A+"
    elif score >= 80: grade = "A"
    elif score >= 70: grade = "B"
    elif score >= 55: grade = "C"
    else: grade = "F"

    return {
        "name": skill_dir.name,
        "path": str(skill_dir),
        "errors": errors,
        "warnings": warnings,
        "score": score,
        "grade": grade,
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
        "metrics": metrics
    }

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Skill Doctor & Validator CLI for 1000x-Agent-Skills.")
    parser.add_argument("--skill", type=str, default=None, help="Validate a specific skill name.")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    skills_root = repo_root / "skills"
    
    if not skills_root.exists():
        print(f"[ERROR] Skills directory not found at {skills_root}")
        sys.exit(1)

    all_results = []
    print("=" * 72)
    print(" 🩺 [SKILL DOCTOR] Specification & Health Diagnostic Suite")
    print("=" * 72)

    for cat_dir in sorted(skills_root.iterdir()):
        if cat_dir.is_dir():
            for skill_dir in sorted(cat_dir.iterdir()):
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    if args.skill and skill_dir.name != args.skill:
                        continue
                    res = validate_skill(skill_dir)
                    all_results.append(res)
                    icon = "[PASS]" if res["status"] == "PASS" else ("[WARN]" if res["status"] == "WARN" else "[FAIL]")
                    print(f"{icon} [{cat_dir.name}/{res['name']}] -> Health Score: {res['score']}/100 [Grade {res['grade']}]")
                    if res["metrics"]:
                        m_str = " | ".join(f"{k}: {v}" for k, v in res["metrics"].items())
                        print(f"    ℹ️  {m_str}")
                    for err in res["errors"]:
                        print(f"    ❌ Error: {err}")
                    for warn in res["warnings"]:
                        print(f"    ⚠️  Warn:  {warn}")

    total = len(all_results)
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    warned = sum(1 for r in all_results if r["status"] == "WARN")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")

    # 5. Verify README.md Catalog Parity
    readme_errors = []
    readme_path = repo_root / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
        referenced_skills = re.findall(r'\(\.?/?skills/([a-z0-9_-]+)/([a-z0-9_-]+)(?:/SKILL\.md)?\)', readme_content)
        for cat, name in referenced_skills:
            target_skill_dir = skills_root / cat / name
            if not target_skill_dir.exists() or not (target_skill_dir / "SKILL.md").exists():
                readme_errors.append(f"README.md references non-existent skill '{name}' in category '{cat}'.")

    print("-" * 72)
    if readme_errors:
        print(" [README AUDIT] ❌ Found mismatched or phantom skills in README.md:")
        for r_err in readme_errors:
            print(f"    - {r_err}")
        failed += len(readme_errors)
    else:
        print(" [README AUDIT] ✅ README.md catalog matches physical filesystem 1:1.")

    print("=" * 72)
    print(f" Summary: {total} skills scanned | {passed} Passed | {warned} Warnings | {failed} Failed")
    print("=" * 72)

    if failed > 0 or (args.strict and warned > 0):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
