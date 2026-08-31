"""
Tests for scripts/validate_skills.py.

The validator is what every other guarantee in this repository rests on, so
its failure modes are tested directly: each test builds a skill with exactly
one defect and asserts the validator names it.
"""

import json

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def validator(load_script):
    return load_script("scripts/validate_skills.py")


def errors_of(result):
    return " | ".join(result["errors"])


def warnings_of(result):
    return " | ".join(result["warnings"])


class TestEstimateTokens:
    def test_counts_words_and_punctuation(self, validator):
        assert validator.estimate_tokens("name: value") == 3

    def test_empty_input_never_returns_zero(self, validator):
        """Downstream code divides by / compares against this; 0 would mislead."""
        assert validator.estimate_tokens("") == 1

    def test_longer_text_scores_higher(self, validator):
        assert validator.estimate_tokens("a b c d") > validator.estimate_tokens("a b")


class TestHealthySkill:
    def test_a_well_formed_skill_passes_cleanly(self, validator, skill_factory):
        result = validator.validate_skill(skill_factory())
        assert result["status"] == "PASS", errors_of(result) + warnings_of(result)
        assert result["score"] == 100
        assert result["grade"] == "A+"

    def test_capabilities_are_surfaced_in_the_metrics(self, validator, skill_factory):
        result = validator.validate_skill(skill_factory())
        assert "network=none" in result["metrics"]["capabilities"]

    def test_content_digest_is_surfaced_in_the_metrics(self, validator, skill_factory):
        assert "content_digest" in validator.validate_skill(skill_factory())["metrics"]


class TestFrontmatterDefects:
    def test_missing_skill_md_fails(self, validator, skill_factory):
        skill = skill_factory()
        (skill / "SKILL.md").unlink()
        result = validator.validate_skill(skill)
        assert result["status"] == "FAIL" and result["score"] == 0

    def test_missing_frontmatter_fails(self, validator, skill_factory):
        skill = skill_factory()
        (skill / "SKILL.md").write_text("# No frontmatter here\n", encoding="utf-8")
        assert "frontmatter" in errors_of(validator.validate_skill(skill)).lower()

    def test_name_mismatching_the_directory_fails(self, validator, skill_factory):
        skill = skill_factory("sample-skill", frontmatter=(
            "name: different-name\ndescription: Use when testing.\nversion: 1.0.0\n"))
        assert "does not match directory name" in errors_of(validator.validate_skill(skill))

    def test_invalid_name_format_fails(self, validator, skill_factory):
        skill = skill_factory("Bad_Name", frontmatter=(
            "name: Bad_Name\ndescription: Use when testing.\nversion: 1.0.0\n"))
        assert "Invalid name format" in errors_of(validator.validate_skill(skill))

    def test_missing_description_fails(self, validator, skill_factory):
        skill = skill_factory(frontmatter="name: sample-skill\nversion: 1.0.0\n")
        assert "description" in errors_of(validator.validate_skill(skill))

    def test_overlong_description_fails(self, validator, skill_factory):
        skill = skill_factory(frontmatter=(
            f"name: sample-skill\ndescription: Use when {'x' * 1100}\nversion: 1.0.0\n"))
        assert "exceeds 1024 characters" in errors_of(validator.validate_skill(skill))

    def test_description_without_trigger_language_warns(self, validator, skill_factory):
        skill = skill_factory(frontmatter=(
            "name: sample-skill\ndescription: A library of helpers.\nversion: 1.0.0\n"))
        assert "trigger context" in warnings_of(validator.validate_skill(skill))

    def test_missing_version_warns(self, validator, skill_factory):
        skill = skill_factory(frontmatter=(
            "name: sample-skill\ndescription: Use when testing.\n"))
        assert "semantic version" in warnings_of(validator.validate_skill(skill))

    def test_body_over_the_line_limit_warns(self, validator, skill_factory):
        skill = skill_factory(body="line\n" * 600)
        assert "500 lines" in warnings_of(validator.validate_skill(skill))


class TestAttestationEnforcement:
    """
    These are the checks that make the badge mean something. Before them, the
    validator confirmed only that the word "VERIFIED" was present.
    """

    def test_missing_attestation_is_an_error_not_a_warning(self, validator, skill_factory):
        skill = skill_factory()
        (skill / "attestation.json").unlink()
        result = validator.validate_skill(skill)
        assert result["status"] == "FAIL"
        assert "un-attested" in errors_of(result)

    def test_malformed_attestation_fails(self, validator, skill_factory):
        skill = skill_factory()
        (skill / "attestation.json").write_text("{ not json", encoding="utf-8")
        assert "Malformed attestation.json" in errors_of(validator.validate_skill(skill))

    def test_attestation_without_capabilities_fails(self, validator, skill_factory):
        skill = skill_factory()
        path = skill / "attestation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["capabilities"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert "capabilities" in errors_of(validator.validate_skill(skill))

    def test_incomplete_capabilities_fail(self, validator, skill_factory):
        skill = skill_factory()
        path = skill / "attestation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["capabilities"] = {"network": "none"}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert result_has(validator, skill, "capabilities")

    def test_invalid_capability_value_fails_the_schema(self, validator, skill_factory):
        skill = skill_factory()
        path = skill / "attestation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["capabilities"]["network"] = "sometimes"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert "schema" in errors_of(validator.validate_skill(skill))

    def test_verified_status_without_platforms_fails_the_schema(self, validator, skill_factory):
        """The schema's own rule: VERIFIED must name what verified it."""
        skill = skill_factory()
        path = skill / "attestation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["attestation_status"] = "VERIFIED"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert "tested_platforms" in errors_of(validator.validate_skill(skill))

    def test_content_edited_after_attestation_fails(self, validator, skill_factory):
        """The core anti-tamper property, exercised through the validator."""
        skill = skill_factory()
        assert validator.validate_skill(skill)["status"] == "PASS"
        (skill / "SKILL.md").write_text(
            "---\nname: sample-skill\ndescription: Use when testing.\nversion: 1.0.0\n---\n"
            "\nSomething was slipped in here after attestation.\n", encoding="utf-8")
        result = validator.validate_skill(skill)
        assert result["status"] == "FAIL"
        assert "Content digest check failed" in errors_of(result)


class TestEvaluationDataset:
    def test_missing_eval_file_warns(self, validator, skill_factory):
        skill = skill_factory()
        (skill / "evals" / "test-cases.json").unlink()
        assert "test-cases.json" in warnings_of(validator.validate_skill(skill))

    def test_malformed_eval_file_errors(self, validator, skill_factory):
        skill = skill_factory()
        (skill / "evals" / "test-cases.json").write_text("{ nope", encoding="utf-8")
        assert "Malformed evals" in errors_of(validator.validate_skill(skill))

    def test_too_few_positive_prompts_warns(self, validator, skill_factory):
        skill = skill_factory(evals={"trigger_evaluation": {
            "positive_prompts": [{"id": "pos-01", "prompt": "x", "expected_trigger": True}],
            "negative_prompts": []}})
        assert "positive prompts" in warnings_of(validator.validate_skill(skill))


class TestRepositoryState:
    def test_every_shipped_skill_passes(self, validator, repo_root):
        skills_root = repo_root / "skills"
        results = [
            validator.validate_skill(skill_md.parent)
            for skill_md in sorted(skills_root.rglob("SKILL.md"))
        ]
        assert results, "no skills discovered"
        failed = [f"{r['name']}: {errors_of(r)}" for r in results if r["errors"]]
        assert not failed, "\n".join(failed)


class TestReadmeCatalogParity:
    """audit_readme_parity must fail in BOTH directions: a README link to a
    skill that does not exist, and a skill on disk the README never mentions.
    The second direction is the one that historically let the catalog drift
    under a green build."""

    @staticmethod
    def _build(tmp_path, listed, on_disk):
        skills_root = tmp_path / "skills"
        for cat, name in on_disk:
            skill_dir = skills_root / cat / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        readme = tmp_path / "README.md"
        readme.write_text(
            "\n".join(f"[`{n}`](./skills/{c}/{n}/SKILL.md)" for c, n in listed),
            encoding="utf-8",
        )
        return readme, skills_root

    def test_phantom_readme_reference_is_an_error(self, validator, tmp_path):
        readme, skills_root = self._build(tmp_path, listed=[("custom", "ghost")], on_disk=[])
        errors = validator.audit_readme_parity(readme, skills_root)
        assert len(errors) == 1 and "non-existent skill 'ghost'" in errors[0]

    def test_unlisted_disk_skill_is_an_error(self, validator, tmp_path):
        readme, skills_root = self._build(tmp_path, listed=[], on_disk=[("custom", "hidden")])
        errors = validator.audit_readme_parity(readme, skills_root)
        assert len(errors) == 1 and "custom/hidden" in errors[0]
        assert "never referenced" in errors[0]

    def test_matching_catalog_passes(self, validator, tmp_path):
        pair = [("custom", "alpha"), ("custom", "beta")]
        readme, skills_root = self._build(tmp_path, listed=pair, on_disk=pair)
        assert validator.audit_readme_parity(readme, skills_root) == []

    def test_missing_readme_reports_disk_skills_as_unlisted(self, validator, tmp_path):
        readme, skills_root = self._build(tmp_path, listed=[], on_disk=[("custom", "alpha")])
        readme.unlink()
        errors = validator.audit_readme_parity(readme, skills_root)
        assert len(errors) == 1 and "custom/alpha" in errors[0]

    def test_shipped_readme_lists_every_shipped_skill(self, validator, repo_root):
        errors = validator.audit_readme_parity(repo_root / "README.md", repo_root / "skills")
        assert errors == [], "\n".join(errors)


def result_has(validator, skill, needle):
    result = validator.validate_skill(skill)
    return needle in errors_of(result) or needle in warnings_of(result)
