"""
Parity between skills/custom/ and the .agents/skills/ mirror.

The mirror exists so non-Claude agents find the same skills. Duplicated
content drifts silently: before this test, .agents/skills/ was missing
saas-app-builder entirely and nothing noticed. The mirror is also the reason
the safety allowlist can exempt a mirrored path by pointing at the reviewed
original -- that argument only holds while the copy is genuinely identical.
"""

import filecmp
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CANONICAL = "skills/custom"
MIRROR = ".agents/skills"


def canonical_skills(repo_root: Path):
    return sorted(p for p in (repo_root / CANONICAL).iterdir() if (p / "SKILL.md").exists())


def mirror_skills(repo_root: Path):
    base = repo_root / MIRROR
    return sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []


def compare_trees(left: Path, right: Path, differences: list, prefix: str = "") -> None:
    result = filecmp.dircmp(left, right)
    for name in result.left_only:
        differences.append(f"missing from mirror: {prefix}{name}")
    for name in result.right_only:
        differences.append(f"only in mirror: {prefix}{name}")
    for name in result.diff_files:
        differences.append(f"content differs: {prefix}{name}")
    for name in result.common_dirs:
        compare_trees(left / name, right / name, differences, f"{prefix}{name}/")


class TestMirrorParity:
    def test_every_canonical_skill_is_mirrored(self, repo_root):
        canonical = {p.name for p in canonical_skills(repo_root)}
        mirrored = {p.name for p in mirror_skills(repo_root)}
        assert canonical - mirrored == set(), (
            f"skills present under {CANONICAL} but absent from {MIRROR}: "
            f"{sorted(canonical - mirrored)}")

    def test_mirror_contains_no_orphans(self, repo_root):
        canonical = {p.name for p in canonical_skills(repo_root)}
        mirrored = {p.name for p in mirror_skills(repo_root)}
        assert mirrored - canonical == set(), (
            f"{MIRROR} contains skills with no canonical source: "
            f"{sorted(mirrored - canonical)}")

    def test_mirrored_trees_are_byte_identical(self, repo_root):
        differences: list = []
        for canonical in canonical_skills(repo_root):
            mirror = repo_root / MIRROR / canonical.name
            if mirror.exists():
                compare_trees(canonical, mirror, differences, f"{canonical.name}/")
        assert not differences, "\n".join(differences)
