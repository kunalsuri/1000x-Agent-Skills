"""
Tests for the public-repo-release-review audit engine.

Its whole value is catching a credential that would otherwise reach a public
repository, so each detector is exercised against a known-positive and a
known-negative. A secret scanner that has never been shown a secret is a
scanner nobody has any reason to trust.
"""

import pytest

pytestmark = pytest.mark.unit

SCRIPT = "skills/custom/public-repo-release-review/scripts/audit_repo.py"


@pytest.fixture
def audit(load_script):
    return load_script(SCRIPT)


def messages(findings):
    return " | ".join(f["message"] for f in findings)


class TestSecretDetection:
    @pytest.mark.parametrize("secret,label", [
        ("AKIA" + "Q" * 16, "AWS Access Key ID"),
        # Assembled rather than written literally: a real PEM header in this
        # file would be a true positive for the repository's own secret scan.
        ("-" * 5 + "BEGIN RSA PRIVATE KEY" + "-" * 5, "Private Cryptographic Key"),
        ("ghp_" + "a" * 36, "GitHub Personal Access Token"),
        ("sk-" + "a" * 40, "OpenAI API Key"),
        ("sk-ant-" + "b" * 40, "Anthropic API Key"),
    ])
    def test_known_credential_shapes_are_detected(self, audit, tmp_path, secret, label):
        (tmp_path / "config.txt").write_text(f"token = {secret}\n", encoding="utf-8")
        findings = audit.scan_secrets(tmp_path)
        assert any(f["type"] == "secret_leak" for f in findings), f"missed {label}"
        assert all(f["severity"] == "CRITICAL"
                   for f in findings if f["type"] == "secret_leak")

    def test_hardcoded_assignment_is_detected(self, audit, tmp_path):
        (tmp_path / "s.py").write_text('api_key = "' + "z" * 30 + '"\n', encoding="utf-8")
        assert any(f["type"] == "secret_leak" for f in audit.scan_secrets(tmp_path))

    def test_documented_placeholders_are_not_flagged(self, audit, tmp_path):
        """Docs must be able to show the shape of a key without tripping the scanner."""
        (tmp_path / "README.md").write_text(
            "Example: AKIAIOSFODNN7EXAMPLE\nAlso sk-example-not-a-real-key\n", encoding="utf-8")
        assert [f for f in audit.scan_secrets(tmp_path) if f["type"] == "secret_leak"] == []

    def test_ordinary_prose_is_not_flagged(self, audit, tmp_path):
        (tmp_path / "doc.md").write_text(
            "Store your API key in the environment, never in source.\n", encoding="utf-8")
        assert [f for f in audit.scan_secrets(tmp_path) if f["type"] == "secret_leak"] == []

    def test_finding_reports_a_line_number(self, audit, tmp_path):
        (tmp_path / "c.env.txt").write_text("a\nb\nghp_" + "c" * 36 + "\n", encoding="utf-8")
        leaks = [f for f in audit.scan_secrets(tmp_path) if f["type"] == "secret_leak"]
        assert leaks and leaks[0]["line"] == 3


class TestSensitiveFiles:
    @pytest.mark.parametrize("name", [".env", "id_rsa", "credentials.json", "server.pem"])
    def test_sensitive_filenames_are_flagged(self, audit, tmp_path, name):
        (tmp_path / name).write_text("placeholder\n", encoding="utf-8")
        assert any(f["type"] == "sensitive_file" for f in audit.scan_secrets(tmp_path))

    def test_ordinary_filenames_are_not_flagged(self, audit, tmp_path):
        (tmp_path / "settings.json").write_text("{}\n", encoding="utf-8")
        assert [f for f in audit.scan_secrets(tmp_path) if f["type"] == "sensitive_file"] == []

    def test_ignored_directories_are_skipped(self, audit, tmp_path):
        vendored = tmp_path / "node_modules" / "pkg"
        vendored.mkdir(parents=True)
        (vendored / ".env").write_text("x\n", encoding="utf-8")
        assert audit.scan_secrets(tmp_path) == []


class TestGovernance:
    def test_missing_required_files_are_reported(self, audit, tmp_path):
        status = audit.check_governance(tmp_path)
        assert status["LICENSE"]["found"] is False
        assert status["LICENSE"]["required"] is True

    def test_present_files_are_found(self, audit, tmp_path):
        (tmp_path / "LICENSE").write_text("Apache-2.0\n", encoding="utf-8")
        assert audit.check_governance(tmp_path)["LICENSE"]["found"] is True

    def test_alternate_locations_are_accepted(self, audit, tmp_path):
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "SECURITY.md").write_text("policy\n", encoding="utf-8")
        result = audit.check_governance(tmp_path)["SECURITY.md"]
        assert result["found"] is True and result["path"] == ".github/SECURITY.md"

    def test_this_repository_satisfies_every_required_file(self, audit, repo_root):
        status = audit.check_governance(repo_root)
        missing = [k for k, v in status.items() if v["required"] and not v["found"]]
        assert missing == []


class TestMarkdownLinks:
    def test_broken_relative_link_is_reported(self, audit, tmp_path):
        (tmp_path / "a.md").write_text("See [spec](./missing.md).\n", encoding="utf-8")
        broken = audit.check_markdown_links(tmp_path)
        assert len(broken) == 1 and broken[0]["target"] == "./missing.md"

    def test_valid_relative_link_is_accepted(self, audit, tmp_path):
        (tmp_path / "spec.md").write_text("spec\n", encoding="utf-8")
        (tmp_path / "a.md").write_text("See [spec](./spec.md).\n", encoding="utf-8")
        assert audit.check_markdown_links(tmp_path) == []

    def test_external_urls_are_not_resolved(self, audit, tmp_path):
        """Link checking is filesystem-only; the auditor never makes a request."""
        (tmp_path / "a.md").write_text("[site](https://example.com/x)\n", encoding="utf-8")
        assert audit.check_markdown_links(tmp_path) == []

    def test_anchors_and_mailto_are_skipped(self, audit, tmp_path):
        (tmp_path / "a.md").write_text(
            "[top](#heading) and [mail](mailto:a@example.com)\n", encoding="utf-8")
        assert audit.check_markdown_links(tmp_path) == []

    def test_links_inside_fenced_code_blocks_are_skipped(self, audit, tmp_path):
        (tmp_path / "a.md").write_text(
            "```\n[example](./nope.md)\n```\n", encoding="utf-8")
        assert audit.check_markdown_links(tmp_path) == []


class TestHygiene:
    def test_os_junk_is_reported(self, audit, tmp_path):
        (tmp_path / ".DS_Store").write_bytes(b"\x00")
        issues = audit.check_codebase_hygiene(tmp_path)
        assert any(i["type"] == "os_junk" for i in issues)

    def test_a_clean_tree_reports_nothing(self, audit, tmp_path):
        (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
        assert audit.check_codebase_hygiene(tmp_path) == []
