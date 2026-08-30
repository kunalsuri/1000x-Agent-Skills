"""Tests for the readme-designer quality auditor."""

import pytest

pytestmark = pytest.mark.unit

RICH_README = """<div align="center">

# My Project

### *A punchy tagline goes here*

[![Build](https://img.shields.io/badge/build-passing-green)](https://example.com)

[**Install**](#install) • [**Usage**](#usage)

</div>

---

## Install

Run the installer.

## Usage

Use the tool.
"""


@pytest.fixture
def audit(load_script):
    return load_script("skills/custom/readme-designer/scripts/audit_readme.py")


class TestSlugify:
    @pytest.mark.parametrize("header,expected", [
        ("Getting Started", "getting-started"),
        ("## Install", "install"),
        ("🚀 Quick Start", "quick-start"),
        ("<b>Bold</b> Header", "bold-header"),
        ("Multiple   Spaces", "multiple-spaces"),
        ("Trailing punctuation!", "trailing-punctuation"),
    ])
    def test_headers_slugify_to_github_anchors(self, audit, header, expected):
        assert audit.slugify_header(header.lstrip("# ")) == expected

    def test_empty_header_yields_empty_slug(self, audit):
        assert audit.slugify_header("") == ""


class TestAudit:
    def test_missing_file_scores_zero(self, audit, tmp_path):
        result = audit.audit_markdown_file(tmp_path / "nope.md", tmp_path)
        assert result["score"] == 0 and result["grade"] == "F" and result["passed"] is False

    def test_a_rich_readme_outscores_a_bare_one(self, audit, tmp_path):
        rich = tmp_path / "rich.md"
        bare = tmp_path / "bare.md"
        rich.write_text(RICH_README, encoding="utf-8")
        bare.write_text("# Title\n\nsome text\n", encoding="utf-8")
        assert (audit.audit_markdown_file(rich, tmp_path)["score"]
                > audit.audit_markdown_file(bare, tmp_path)["score"])

    def test_hero_elements_are_credited(self, audit, tmp_path):
        path = tmp_path / "r.md"
        path.write_text(RICH_README, encoding="utf-8")
        result = audit.audit_markdown_file(path, tmp_path)
        assert result["metrics"]["hero_section_pts"] == "15/15"

    def test_score_stays_within_bounds(self, audit, tmp_path):
        path = tmp_path / "r.md"
        path.write_text(RICH_README, encoding="utf-8")
        assert 0 <= audit.audit_markdown_file(path, tmp_path)["score"] <= 100

    def test_this_repository_readme_is_audited_without_error(self, audit, repo_root):
        result = audit.audit_markdown_file(repo_root / "README.md", repo_root)
        assert result["score"] > 0 and "hero_section_pts" in result["metrics"]
