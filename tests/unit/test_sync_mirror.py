"""Tests for scripts/sync_mirror.py: dry run by default, exact copies, orphan removal."""

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def sync(load_script):
    return load_script("scripts/sync_mirror.py")


def make_skill(root, name, body="x"):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n{body}\n", encoding="utf-8")
    return d


def test_missing_mirror_plans_a_copy(sync, tmp_path):
    canonical, mirror = tmp_path / "skills", tmp_path / "mirror"
    make_skill(canonical, "alpha")
    to_copy, to_delete = sync.plan(canonical, mirror)
    assert [p.name for p in to_copy] == ["alpha"] and to_delete == []


def test_apply_makes_a_byte_identical_copy_and_ignores_os_litter(sync, tmp_path):
    canonical, mirror = tmp_path / "skills", tmp_path / "mirror"
    src = make_skill(canonical, "alpha")
    (src / ".DS_Store").write_bytes(b"\0")
    sync.apply(*sync.plan(canonical, mirror), mirror)
    assert (mirror / "alpha" / "SKILL.md").read_bytes() == (src / "SKILL.md").read_bytes()
    assert not (mirror / "alpha" / ".DS_Store").exists()
    assert sync.plan(canonical, mirror) == ([], [])


def test_content_drift_is_detected(sync, tmp_path):
    canonical, mirror = tmp_path / "skills", tmp_path / "mirror"
    make_skill(canonical, "alpha", body="new")
    make_skill(mirror, "alpha", body="old")
    to_copy, _ = sync.plan(canonical, mirror)
    assert [p.name for p in to_copy] == ["alpha"]


def test_orphans_in_the_mirror_are_planned_for_deletion(sync, tmp_path):
    canonical, mirror = tmp_path / "skills", tmp_path / "mirror"
    make_skill(canonical, "alpha")
    make_skill(mirror, "alpha")
    make_skill(mirror, "ghost")
    _, to_delete = sync.plan(canonical, mirror)
    assert [p.name for p in to_delete] == ["ghost"]


def test_directories_without_skill_md_are_not_mirrored(sync, tmp_path):
    canonical, mirror = tmp_path / "skills", tmp_path / "mirror"
    (canonical / "notes").mkdir(parents=True)
    assert sync.plan(canonical, mirror) == ([], [])


def test_this_repository_mirror_is_in_sync(sync):
    """Dry run against the real tree must find nothing to do (exit 0)."""
    assert sync.main([]) == 0
