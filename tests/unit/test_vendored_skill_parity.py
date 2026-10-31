"""
Guards on the one vendored upstream skill: .claude/skills/skill-creator.

Until 2026-10-31 skill-creator existed twice -- a catalogue copy under
skills/anthropic/ and the copy Claude Code loads from .claude/skills/ -- and
this file checked that the two never drifted. The catalogue copy (and the
skills/anthropic/ category) was removed when the catalogue was flattened to
skills/<skill>/ and narrowed to original skills only. What remains is the
loaded copy, which still has to stay honest about being someone else's code.
"""

import pytest

pytestmark = pytest.mark.unit

LOADED = ".claude/skills/skill-creator"


def test_loaded_copy_exists_with_its_upstream_licence(repo_root):
    """Vendored Apache-2.0 code must ship with the licence it was received under."""
    assert (repo_root / LOADED / "SKILL.md").exists(), f"{LOADED} is missing"
    licence = (repo_root / LOADED / "LICENSE.txt").read_text(encoding="utf-8")
    assert "Apache License" in licence and "Version 2.0" in licence


def test_vendored_skill_is_not_in_the_catalogue(repo_root):
    """skills/ holds original work only; a vendored copy there would be digested,
    attested and listed in the README as if it were authored here."""
    assert not (repo_root / "skills" / "skill-creator").exists()
    assert not (repo_root / "skills" / "anthropic").exists()


def test_loaded_copy_carries_no_attestation(repo_root):
    """A copy outside skills/ is never digest-checked, so an attestation there
    would be an unenforced claim -- the exact thing content_digest exists to stop."""
    assert not (repo_root / LOADED / "attestation.json").exists()
