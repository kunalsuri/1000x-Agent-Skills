"""
Tests for scripts/skill_digest.py.

The digest is what stops `"attestation_status": "VERIFIED"` from being a
sticker that outlives the content it was granted for. These tests hold that
property: any change to any covered file must break the seal.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def digest(load_script):
    return load_script("scripts/skill_digest.py")


class TestDigestStability:
    def test_digest_is_deterministic(self, digest, skill_factory):
        skill = skill_factory()
        assert digest.compute_skill_digest(skill) == digest.compute_skill_digest(skill)

    def test_digest_has_the_expected_shape(self, digest, skill_factory):
        value = digest.compute_skill_digest(skill_factory())
        assert value.startswith("sha256:") and len(value) == len("sha256:") + 64

    def test_digest_is_independent_of_where_the_skill_lives(self, digest, skill_factory,
                                                            tmp_path):
        """
        A user who copies a skill out of this repo must be able to reproduce
        the published digest on their own machine, at their own path.
        """
        import shutil
        source = skill_factory("skill-a")
        elsewhere = tmp_path / "somewhere" / "else" / "skill-a"
        elsewhere.parent.mkdir(parents=True)
        shutil.copytree(source, elsewhere)
        assert digest.compute_skill_digest(source) == digest.compute_skill_digest(elsewhere)


class TestTamperDetection:
    def test_editing_skill_md_breaks_the_seal(self, digest, skill_factory):
        skill = skill_factory()
        assert digest.verify_skill(skill)[0] is True
        (skill / "SKILL.md").write_text("---\nname: x\n---\ntampered\n", encoding="utf-8")
        ok, detail = digest.verify_skill(skill)
        assert ok is False and "content has changed" in detail

    def test_adding_a_script_breaks_the_seal(self, digest, skill_factory):
        """The likeliest real attack: slip an extra file into an attested skill."""
        skill = skill_factory()
        before = digest.compute_skill_digest(skill)
        (skill / "scripts").mkdir()
        (skill / "scripts" / "payload.py").write_text("print('x')\n", encoding="utf-8")
        assert digest.compute_skill_digest(skill) != before

    def test_removing_a_file_breaks_the_seal(self, digest, skill_factory):
        skill = skill_factory()
        before = digest.compute_skill_digest(skill)
        (skill / "evals" / "test-cases.json").unlink()
        assert digest.compute_skill_digest(skill) != before

    def test_a_single_byte_change_breaks_the_seal(self, digest, skill_factory):
        skill = skill_factory()
        before = digest.compute_skill_digest(skill)
        path = skill / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        assert digest.compute_skill_digest(skill) != before

    def test_editing_attestation_does_not_break_the_seal(self, digest, skill_factory):
        """attestation.json holds the digest, so it cannot be covered by it."""
        skill = skill_factory()
        before = digest.compute_skill_digest(skill)
        data = json.loads((skill / "attestation.json").read_text(encoding="utf-8"))
        data["attested_by"] = "Someone Else"
        (skill / "attestation.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert digest.compute_skill_digest(skill) == before


class TestVerifyAndUpdate:
    def test_missing_attestation_fails_verification(self, digest, skill_factory):
        skill = skill_factory()
        (skill / "attestation.json").unlink()
        ok, detail = digest.verify_skill(skill)
        assert ok is False and "no attestation.json" in detail

    def test_attestation_without_a_digest_fails_verification(self, digest, skill_factory):
        skill = skill_factory(with_digest=False)
        ok, detail = digest.verify_skill(skill)
        assert ok is False and digest.DIGEST_KEY in detail

    def test_update_then_verify_round_trips(self, digest, skill_factory):
        skill = skill_factory(with_digest=False)
        changed, value = digest.update_skill(skill)
        assert changed is True
        ok, detail = digest.verify_skill(skill)
        assert ok is True and detail == value

    def test_update_is_idempotent(self, digest, skill_factory):
        skill = skill_factory()
        changed, _ = digest.update_skill(skill)
        assert changed is False, "re-running update on unchanged content must be a no-op"

    def test_manifest_excludes_pycache(self, digest, skill_factory):
        skill = skill_factory()
        before = digest.compute_skill_digest(skill)
        cache = skill / "scripts" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "mod.cpython-311.pyc").write_bytes(b"\x00\x01")
        assert digest.compute_skill_digest(skill) == before

    def test_manifest_lists_relative_posix_paths(self, digest, skill_factory):
        manifest = digest.build_manifest(skill_factory())
        assert "SKILL.md  " in manifest
        assert "evals/test-cases.json  " in manifest
        assert "attestation.json" not in manifest
        assert "\\" not in manifest


class TestRepositoryState:
    def test_every_shipped_skill_verifies(self, digest, repo_root):
        """Regression guard: a skill edited without re-attesting fails here."""
        failures = []
        for skill_dir in digest.discover_skills(repo_root):
            ok, detail = digest.verify_skill(skill_dir)
            if not ok:
                failures.append(f"{skill_dir.relative_to(repo_root)}: {detail}")
        assert not failures, "\n".join(failures)

    def test_mirror_digests_match_their_canonical_source(self, digest, repo_root):
        for canonical in sorted((repo_root / "skills" / "custom").iterdir()):
            mirror = repo_root / ".agents" / "skills" / canonical.name
            if not mirror.exists():
                continue
            assert digest.compute_skill_digest(canonical) == digest.compute_skill_digest(mirror)
