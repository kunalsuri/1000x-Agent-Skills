"""
Parity between the two copies of a vendored upstream skill.

skill-creator exists twice on purpose: skills/anthropic/skill-creator is the
catalogue entry a reader browses, and .claude/skills/skill-creator is the copy
Claude Code actually loads for sessions in this repository. Claude Code only
loads project skills from .claude/skills/, so neither copy can be replaced by a
link to the other.

Two copies of anything drift. This test fails the build when they do. The
catalogue copy carries two files the loaded copy has no use for -- attestation.json
and evals/, which this repository's tooling requires and upstream does not ship --
so those are excluded; everything else must be byte-identical upstream content.
"""

import filecmp
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CATALOGUE = "skills/anthropic/skill-creator"
LOADED = ".claude/skills/skill-creator"

# Present only in the catalogue copy: required by this repository, not by upstream.
CATALOGUE_ONLY = {"attestation.json", "evals"}


def compare_trees(left: Path, right: Path, differences: list, prefix: str = "") -> None:
    result = filecmp.dircmp(left, right)
    for name in result.left_only:
        if prefix or name not in CATALOGUE_ONLY:
            differences.append(f"missing from the loaded copy: {prefix}{name}")
    for name in result.right_only:
        differences.append(f"only in the loaded copy: {prefix}{name}")
    for name in result.diff_files:
        differences.append(f"content differs: {prefix}{name}")
    for name in result.common_dirs:
        compare_trees(left / name, right / name, differences, f"{prefix}{name}/")


def test_both_copies_exist(repo_root):
    assert (repo_root / CATALOGUE / "SKILL.md").exists(), f"{CATALOGUE} is missing"
    assert (repo_root / LOADED / "SKILL.md").exists(), f"{LOADED} is missing"


def test_vendored_copies_do_not_drift(repo_root):
    differences: list = []
    compare_trees(repo_root / CATALOGUE, repo_root / LOADED, differences)
    assert not differences, (
        "The two copies of the vendored skill-creator have drifted:\n  "
        + "\n  ".join(differences)
        + f"\n\nRe-vendor rather than patching one side: replace both directories from "
          f"upstream, then re-run 'python scripts/skill_digest.py --update'."
    )


def test_loaded_copy_carries_no_attestation(repo_root):
    """A copy outside skills/ is never digest-checked, so an attestation there
    would be an unenforced claim -- the exact thing content_digest exists to stop."""
    assert not (repo_root / LOADED / "attestation.json").exists()
