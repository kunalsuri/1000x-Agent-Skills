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

# The six top-level fields of the Agent Skills open specification
# (https://agentskills.io/specification). Verified against the upstream source
# on 2026-10-31.
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# Claude Code accepts these on top of the spec (https://code.claude.com/docs/en/skills).
# Checked 2026-10-31. Other clients ignore them.
CLAUDE_CODE_KEYS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
    "user-invocable", "disallowed-tools", "model", "effort", "context", "agent",
    "background", "hooks", "paths", "shell",
}


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

        # Top-level keys: the open spec defines exactly six. Anything else at
        # the top level is rejected outright by claude.ai uploads, the Skills
        # API and package_skill.py, so a skill that carries it is not portable.
        # Claude Code's own extensions are legitimate but client-specific, so
        # they warn rather than fail.
        top_keys = re.findall(r"^([A-Za-z0-9_-]+):", fm_text, re.MULTILINE)
        for key in top_keys:
            if key in SPEC_KEYS:
                continue
            if key in CLAUDE_CODE_KEYS:
                warnings.append(
                    f"Frontmatter key '{key}' is a Claude Code extension; other clients "
                    f"ignore it and claude.ai uploads reject it.")
                score -= 2
            else:
                errors.append(
                    f"Frontmatter key '{key}' is not in the Agent Skills spec. Move it "
                    f"under 'metadata:' (e.g. metadata.{key}).")
                score -= 5

        compat = re.search(r"^compatibility:[ \t]*(.*)$", fm_text, re.MULTILINE)
        if compat:
            value = compat.group(1).strip()
            if value.startswith("[") or not value:
                errors.append("'compatibility' must be a single string (max 500 chars), not a list.")
                score -= 5
            elif len(value.strip("'\"")) > 500:
                errors.append("'compatibility' exceeds 500 characters.")
                score -= 5

        tools = re.search(r"^allowed-tools:[ \t]*(.*)$", fm_text, re.MULTILINE)
        if tools and (tools.group(1).strip().startswith("[") or not tools.group(1).strip()):
            warnings.append(
                "'allowed-tools' should be a space-separated string (spec); "
                "YAML lists are a Claude Code-only convenience.")
            score -= 2

        # Version lives under metadata in the spec, not at the top level.
        if not re.search(r"^[ \t]+version:[ \t]*[\"']?\d+\.\d+\.\d+", fm_text, re.MULTILINE):
            warnings.append("Missing semantic version (put it under metadata, e.g. 'metadata:\\n  version: \"1.0.0\"').")
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

            # The schema defines VERIFIED as "multi-platform verified with linked
            # evidence". A VERIFIED status with no evidence_url on any PASS row is
            # therefore a claim the attestation's own schema says it cannot make.
            if att_data.get("attestation_status") == "VERIFIED":
                rows = att_data.get("tested_platforms") or []
                if not any(r.get("status") == "PASS" and r.get("evidence_url") for r in rows):
                    warnings.append(
                        "attestation_status is VERIFIED but no PASS row in tested_platforms "
                        "carries an evidence_url. Link a transcript/CI run, or lower the "
                        "status to TESTED.")
                    score -= 5

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

def audit_tree_layout(skills_root: Path) -> list:
    """Every SKILL.md under skills/ must sit at skills/<skill>/SKILL.md.

    This validator walks exactly one level. scripts/audit_skill_safety.py and
    scripts/skill_digest.py both rglob for SKILL.md and so reach any depth. A
    skill nested deeper therefore used to be audited and digested but never
    health-checked, and nothing said so -- it was skipped in silence, which is
    the worst way for a check to decline to run. Reporting the layout error is
    what keeps the three tools looking at the same set of skills.

    The flat layout matches anthropics/skills, the Claude Code plugin format
    (<plugin>/skills/<name>/SKILL.md) and what `npx skills add` discovers first.
    """
    errors = []
    if not skills_root.exists():
        return errors
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        # (skill, "SKILL.md")
        parts = skill_md.relative_to(skills_root).parts
        if len(parts) != 2:
            found = "skills/" + "/".join(parts)
            errors.append(
                f"'{found}' is not at skills/<skill>/SKILL.md, so this "
                f"validator never sees it -- while the safety auditor and the digest "
                f"tool both do. Move it to the canonical depth."
            )
    return errors


def iter_skill_dirs(skills_root: Path):
    """Yield every skills/<skill>/ directory that contains a SKILL.md."""
    if not skills_root.exists():
        return
    for skill_dir in sorted(skills_root.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            yield skill_dir


def audit_readme_parity(readme_path: Path, skills_root: Path) -> list:
    """Two-way parity between the root README's skill links and skills/ on disk.

    Direction 1: every skill the README links to must exist on disk (no
    phantom references). Direction 2: every skill on disk must be linked
    somewhere in the README (no unlisted skills) -- without this direction a
    skill can land in the repository and pass CI while the catalog silently
    omits it. Returns a list of error strings; empty means parity holds.
    """
    errors = []
    referenced = set()
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
        referenced = set(re.findall(
            r'\(\.?/?skills/([a-z0-9-]+)/?(?:SKILL\.md)?\)', readme_content))
        for name in sorted(referenced):
            target_skill_dir = skills_root / name
            if not (target_skill_dir / "SKILL.md").exists():
                errors.append(f"README.md references non-existent skill '{name}'.")
    for skill_dir in iter_skill_dirs(skills_root):
        if skill_dir.name not in referenced:
            errors.append(
                f"Skill '{skill_dir.name}' exists on disk but is never referenced in README.md.")
    return errors


def audit_spec_freshness(meta_path: Path, today=None, max_age_days: int = 90) -> list:
    """Warn when docs/agent-skills-specs has not been re-verified recently.

    The spec summary in docs/ tracks a moving target (agentskills.io and each
    client's docs). Its `last_verified` stamp is the only honest statement of
    how current it is, so the validator reads it rather than trusting it.
    Returns warnings, never errors: staleness is a prompt to re-check, not a
    reason the skills themselves are broken.
    """
    import datetime as _dt
    if not meta_path.exists():
        return [f"{meta_path.name} is missing; the spec summary has no freshness stamp."]
    match = re.search(r"^\s*last_verified:\s*[\"']?(\d{4}-\d{2}-\d{2})",
                      meta_path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        return [f"{meta_path.name} has no document.last_verified date."]
    stamp = _dt.date.fromisoformat(match.group(1))
    today = today or _dt.date.today()
    age = (today - stamp).days
    if age > max_age_days:
        return [f"docs/agent-skills-specs was last verified {stamp} ({age} days ago, "
                f"limit {max_age_days}). Re-run the 'Agent-Skills Specs Audit' prompt "
                f"in docs/prompts/general-prompts.md and bump last_verified."]
    return []


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

    for skill_dir in iter_skill_dirs(skills_root):
        if args.skill and skill_dir.name != args.skill:
            continue
        res = validate_skill(skill_dir)
        all_results.append(res)
        icon = "[PASS]" if res["status"] == "PASS" else ("[WARN]" if res["status"] == "WARN" else "[FAIL]")
        print(f"{icon} [{res['name']}] -> Health Score: {res['score']}/100 [Grade {res['grade']}]")
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

    # 5. Verify README.md Catalog Parity (both directions)
    readme_errors = audit_readme_parity(repo_root / "README.md", skills_root)
    layout_errors = audit_tree_layout(skills_root)

    print("-" * 72)
    if layout_errors:
        print(" [LAYOUT AUDIT] \u274c skills/ contains a SKILL.md this validator cannot reach:")
        for l_err in layout_errors:
            print(f"    - {l_err}")
        failed += len(layout_errors)
    else:
        print(" [LAYOUT AUDIT] \u2705 every SKILL.md sits at skills/<skill>/.")

    if readme_errors:
        print(" [README AUDIT] ❌ README.md catalog and skills/ tree have drifted:")
        for r_err in readme_errors:
            print(f"    - {r_err}")
        failed += len(readme_errors)
    else:
        print(" [README AUDIT] ✅ README.md catalog and skills/ tree match in both directions.")

    freshness = audit_spec_freshness(repo_root / "docs" / "agent-skills-specs" / "skill-specs.meta.yaml")
    if freshness:
        for f_warn in freshness:
            print(f" [SPEC FRESHNESS] \u26a0\ufe0f  {f_warn}")
    else:
        print(" [SPEC FRESHNESS] \u2705 docs/agent-skills-specs verified within the last 90 days.")

    print("=" * 72)
    print(f" Summary: {total} skills scanned | {passed} Passed | {warned} Warnings | {failed} Failed")
    print("=" * 72)

    if failed > 0 or (args.strict and warned > 0):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
