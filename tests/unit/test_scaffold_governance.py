"""Tests for the public-repo-release-review governance scaffolder."""

import pytest

pytestmark = pytest.mark.unit

REQUIRED = ["SECURITY.md", "COLLABORATORS.md", "CITATION.cff",
            "CODE_OF_CONDUCT.md", "SUPPORT.md"]


@pytest.fixture
def governance(load_script):
    return load_script("skills/custom/public-repo-release-review/scripts/scaffold_governance.py")


@pytest.fixture
def scaffolded(governance, tmp_path):
    governance.scaffold(tmp_path, "solo", "Test Author", "author@example.com", "demo-repo")
    return tmp_path


class TestScaffolding:
    @pytest.mark.parametrize("filename", REQUIRED)
    def test_each_governance_file_is_created(self, scaffolded, filename):
        assert (scaffolded / filename).is_file()

    def test_issue_and_pr_templates_are_created(self, scaffolded):
        assert (scaffolded / ".github" / "PULL_REQUEST_TEMPLATE.md").is_file()
        assert (scaffolded / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").is_file()

    def test_no_file_is_left_empty(self, scaffolded):
        for filename in REQUIRED:
            assert (scaffolded / filename).read_text(encoding="utf-8").strip()

    def test_author_details_are_substituted(self, scaffolded):
        text = (scaffolded / "CITATION.cff").read_text(encoding="utf-8")
        assert "Test Author" in text or "author@example.com" in text

    def test_contact_email_reaches_the_security_policy(self, scaffolded):
        assert "author@example.com" in (scaffolded / "SECURITY.md").read_text(encoding="utf-8")

    def test_open_mode_differs_from_solo_mode(self, governance, tmp_path):
        solo, open_ = tmp_path / "solo", tmp_path / "open"
        solo.mkdir(); open_.mkdir()
        governance.scaffold(solo, "solo", "A", "a@example.com", "r")
        governance.scaffold(open_, "open", "A", "a@example.com", "r")
        assert ((solo / "COLLABORATORS.md").read_text(encoding="utf-8")
                != (open_ / "COLLABORATORS.md").read_text(encoding="utf-8"))


class TestScaffoldedOutputSatisfiesTheAuditor:
    def test_the_scaffolder_output_passes_the_governance_audit(self, governance,
                                                               load_script, tmp_path):
        """
        The two halves of this skill must agree: what it writes should satisfy
        what it checks. Otherwise it scaffolds a repo that then fails its own
        release review.
        """
        audit = load_script("skills/custom/public-repo-release-review/scripts/audit_repo.py")
        (tmp_path / "LICENSE").write_text("Apache-2.0\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        governance.scaffold(tmp_path, "solo", "A", "a@example.com", "demo")
        status = audit.check_governance(tmp_path)
        missing = [k for k, v in status.items() if v["required"] and not v["found"]]
        assert missing == []
