"""
Tests for docs/schemas/attestation.schema.json.

Every attestation.json in this repository points its `$schema` at this file.
Until it existed, those pointers resolved to nothing and no attestation was
ever checked against anything. These tests keep the schema real: valid in
itself, satisfied by everything shipped, and strict enough to reject the
specific shapes it exists to prevent.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def schema():
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "docs" / "schemas" / "attestation.schema.json").read_text(
        encoding="utf-8"))


@pytest.fixture
def validate(schema):
    validator = jsonschema.Draft202012Validator(schema)

    def check(document):
        return [e.message for e in validator.iter_errors(document)]

    return check


@pytest.fixture
def valid_attestation():
    return {
        "skill_name": "sample-skill",
        "version": "1.0.0",
        "attestation_status": "TESTED",
        "capabilities": {
            "network": "none",
            "process_execution": "none",
            "dynamic_code_execution": "none",
            "filesystem": "read-only",
        },
        "attested_by": "Test Harness",
        "attestation_date": "2026-01-01",
        "content_digest": "sha256:" + "0" * 64,
        "provenance": {"source_type": "original", "license": "Apache-2.0"},
    }


class TestSchemaItself:
    def test_schema_is_a_valid_2020_12_schema(self, schema):
        jsonschema.Draft202012Validator.check_schema(schema)

    def test_schema_id_matches_where_attestations_point(self, schema, repo_root):
        """A $schema pointing somewhere the schema is not is how this broke before."""
        declared = schema["$id"]
        for attestation in sorted((repo_root / "skills").rglob("attestation.json")):
            data = json.loads(attestation.read_text(encoding="utf-8"))
            assert data["$schema"] == declared, f"{attestation} points elsewhere"

    def test_schema_file_lives_where_its_id_says(self, schema, repo_root):
        suffix = schema["$id"].split("/main/", 1)[1]
        assert (repo_root / suffix).exists()


class TestShippedAttestations:
    def test_every_attestation_in_the_repository_conforms(self, validate, repo_root):
        failures = []
        for attestation in sorted(repo_root.rglob("attestation.json")):
            if ".git" in attestation.parts:
                continue
            # demo/ holds bundles written by imaginary strangers, for the
            # verifier to read. Holding them to this repository's schema would
            # be holding a stranger's file to a standard they never agreed to
            # -- which is exactly the assumption the verifier refuses to make.
            if "demo" in attestation.parts:
                continue
            for message in validate(json.loads(attestation.read_text(encoding="utf-8"))):
                failures.append(f"{attestation.relative_to(repo_root)}: {message}")
        assert not failures, "\n".join(failures)

    def test_every_shipped_skill_declares_all_four_capabilities(self, repo_root):
        for attestation in sorted((repo_root / "skills").rglob("attestation.json")):
            caps = json.loads(attestation.read_text(encoding="utf-8"))["capabilities"]
            assert set(caps) == {"network", "process_execution",
                                 "dynamic_code_execution", "filesystem"}

    def test_non_minimal_capabilities_carry_a_rationale(self, repo_root):
        """A raised capability with no stated reason is an unexplained privilege."""
        minimal = {"network": "none", "process_execution": "none",
                   "dynamic_code_execution": "none", "filesystem": "read-only"}
        for attestation in sorted((repo_root / "skills").rglob("attestation.json")):
            data = json.loads(attestation.read_text(encoding="utf-8"))
            if data["capabilities"] != minimal:
                assert data.get("capabilities_rationale"), (
                    f"{attestation.relative_to(repo_root)} raises a capability "
                    f"without explaining why")


class TestSchemaRejections:
    def test_baseline_document_is_accepted(self, validate, valid_attestation):
        assert validate(valid_attestation) == []

    def test_unknown_capability_value_is_rejected(self, validate, valid_attestation):
        valid_attestation["capabilities"]["network"] = "inbound"
        assert validate(valid_attestation)

    def test_missing_capabilities_block_is_rejected(self, validate, valid_attestation):
        del valid_attestation["capabilities"]
        assert validate(valid_attestation)

    def test_missing_content_digest_is_rejected(self, validate, valid_attestation):
        del valid_attestation["content_digest"]
        assert validate(valid_attestation)

    def test_malformed_content_digest_is_rejected(self, validate, valid_attestation):
        valid_attestation["content_digest"] = "sha256:short"
        assert validate(valid_attestation)

    def test_unknown_attestation_status_is_rejected(self, validate, valid_attestation):
        valid_attestation["attestation_status"] = "TOTALLY_VERIFIED"
        assert validate(valid_attestation)

    def test_verified_without_tested_platforms_is_rejected(self, validate, valid_attestation):
        valid_attestation["attestation_status"] = "VERIFIED"
        assert validate(valid_attestation), "VERIFIED must name what verified it"

    def test_verified_with_a_platform_is_accepted(self, validate, valid_attestation):
        valid_attestation["attestation_status"] = "VERIFIED"
        valid_attestation["tested_platforms"] = [
            {"platform": "Claude Code", "model": "some-model", "status": "PASS"}]
        assert validate(valid_attestation) == []

    def test_unknown_platform_status_is_rejected(self, validate, valid_attestation):
        valid_attestation["tested_platforms"] = [
            {"platform": "P", "model": "m", "status": "PROBABLY"}]
        assert validate(valid_attestation)

    def test_success_rate_above_one_hundred_is_rejected(self, validate, valid_attestation):
        valid_attestation["performance_summary"] = {"success_rate_percent": 150}
        assert validate(valid_attestation)

    def test_typo_in_a_top_level_key_is_rejected(self, validate, valid_attestation):
        """additionalProperties:false, so a typo cannot silently do nothing."""
        valid_attestation["capabilties"] = {}
        assert validate(valid_attestation)

    def test_non_semver_version_is_rejected(self, validate, valid_attestation):
        valid_attestation["version"] = "v1"
        assert validate(valid_attestation)
