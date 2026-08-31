"""
The three tools must look at the same set of skills.

scripts/validate_skills.py walks exactly skills/<category>/<skill>. Both
scripts/audit_skill_safety.py and scripts/skill_digest.py rglob for SKILL.md and
so reach any depth. A skill nested one level deeper was therefore audited,
digested and never health-checked -- and nothing reported that, because the
validator's loop simply did not match it. A check that declines to run in
silence is worse than one that fails.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]

FRONTMATTER = "---\nname: {name}\ndescription: probe. Use when testing.\n---\n# probe\n"


@pytest.fixture(scope="module")
def validator():
    spec = importlib.util.spec_from_file_location(
        "layout_validator", ROOT / "scripts" / "validate_skills.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["layout_validator"] = module
    spec.loader.exec_module(module)
    return module


def place(skills_root: Path, relative: str, name: str) -> None:
    target = skills_root / relative
    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_text(FRONTMATTER.format(name=name), encoding="utf-8")


def test_canonical_depth_is_accepted(validator, tmp_path):
    skills_root = tmp_path / "skills"
    place(skills_root, "custom/well-placed", "well-placed")
    assert validator.audit_tree_layout(skills_root) == []


def test_nested_skill_is_reported(validator, tmp_path):
    """This is the case that used to pass in silence."""
    skills_root = tmp_path / "skills"
    place(skills_root, "custom/wrapper/inner", "inner")
    errors = validator.audit_tree_layout(skills_root)
    assert len(errors) == 1
    assert "custom/wrapper/inner/SKILL.md" in errors[0]


def test_skill_directly_under_skills_is_reported(validator, tmp_path):
    """Too shallow is just as invisible to the two-level walk as too deep."""
    skills_root = tmp_path / "skills"
    place(skills_root, "no-category", "no-category")
    errors = validator.audit_tree_layout(skills_root)
    assert len(errors) == 1
    assert "no-category/SKILL.md" in errors[0]


def test_missing_skills_root_is_not_an_error(validator, tmp_path):
    assert validator.audit_tree_layout(tmp_path / "nope") == []


def test_this_repository_is_laid_out_canonically(validator):
    assert validator.audit_tree_layout(ROOT / "skills") == []
