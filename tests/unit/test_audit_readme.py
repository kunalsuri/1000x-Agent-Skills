"""
Tests for the readme-designer quality auditor.

The rubric this file guards replaced one that paid for decoration: points
for `<br/>` tags, hero banners, badge rows and Mermaid diagrams. A rubric is
optimised against, so that one produced long, ornamental READMEs that scored
A+ while burying the command a reader came for. Most of what follows asserts
the new direction explicitly -- ornament must not out-score substance --
because a scoring change that is not pinned by tests drifts straight back.
"""

import pytest

pytestmark = pytest.mark.unit

LEAN_README = """# My Project

Turns a transcript into dated Markdown notes, for people who take minutes.

## Install

```bash
pip install my-project
```

## Usage

```bash
my-project transcript.txt
```

```text
# Notes -- 2026-08-31
```

## Contributing

Run `pytest` and open a pull request.

## License

Apache 2.0.
"""

ORNAMENTAL_README = """<div align="center">

# My Project

### *A punchy tagline goes here*

<br/>

[![Build](https://img.shields.io/badge/build-passing-green)](https://example.com)
[![Quality](https://img.shields.io/badge/Quality-Grade%20A%2B-10b981)](https://example.com)
[![Stars](https://img.shields.io/badge/stars-lots-blue)](https://example.com)
[![Made with](https://img.shields.io/badge/made%20with-love-red)](https://example.com)
[![Awesome](https://img.shields.io/badge/awesome-yes-purple)](https://example.com)
[![Shiny](https://img.shields.io/badge/shiny-very-orange)](https://example.com)

<br/>

[**Install**](#install) - [**Usage**](#usage)

<br/>

</div>

---

<br/>

## Install

<br/>

Run the installer.

<br/>

---

<br/>

## Usage

<br/>

Use the tool.

<br/>

---

<br/>

## License

<br/>

Apache 2.0.
"""


@pytest.fixture
def audit(load_script):
    return load_script("skills/custom/readme-designer/scripts/audit_readme.py")


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


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


class TestTheRubricPaysForSubstance:
    def test_missing_file_scores_zero(self, audit, tmp_path):
        result = audit.audit_markdown_file(tmp_path / "nope.md", tmp_path)
        assert result["score"] == 0 and result["grade"] == "F" and result["passed"] is False

    def test_a_lean_readme_outscores_an_ornamental_one(self, audit, tmp_path):
        """The whole point of the rewrite, in one assertion."""
        lean = audit.audit_markdown_file(
            write(tmp_path, "lean.md", LEAN_README), tmp_path)
        ornamental = audit.audit_markdown_file(
            write(tmp_path, "ornamental.md", ORNAMENTAL_README), tmp_path)
        assert lean["score"] > ornamental["score"]
        assert lean["passed"] and not ornamental["passed"]

    def test_a_runnable_command_near_the_top_is_credited(self, audit, tmp_path):
        result = audit.audit_markdown_file(
            write(tmp_path, "r.md", LEAN_README), tmp_path)
        assert result["metrics"]["orientation_pts"] == "20/20"
        assert result["metrics"]["first_command_line"] == 7

    def test_a_readme_with_no_command_at_all_loses_orientation_points(
            self, audit, tmp_path):
        result = audit.audit_markdown_file(
            write(tmp_path, "r.md", "# Title\n\nA sentence about the project "
                                    "that is long enough to count.\n"), tmp_path)
        assert result["metrics"]["orientation_pts"] == "10/20"

    def test_a_buried_command_scores_below_a_prominent_one(self, audit, tmp_path):
        buried = "# Title\n\nA sentence about the project, long enough to count.\n" \
                 + ("\nfiller line\n" * 60) + "\n```bash\nrun it\n```\n"
        result = audit.audit_markdown_file(
            write(tmp_path, "buried.md", buried), tmp_path)
        prominent = audit.audit_markdown_file(
            write(tmp_path, "lean.md", LEAN_README), tmp_path)
        assert result["metrics"]["first_command_line"] > 80
        assert result["metrics"]["orientation_pts"] == "10/20"
        assert result["score"] < prominent["score"]
        assert any("almost nobody scrolls" in rec
                   for rec in result["recommendations"])


class TestTheRubricPenalisesOrnament:
    def test_padding_tags_cost_restraint_points(self, audit, tmp_path):
        padded = LEAN_README.replace("## Install", "<br/>\n" * 12 + "## Install")
        lean = audit.audit_markdown_file(
            write(tmp_path, "lean.md", LEAN_README), tmp_path)
        result = audit.audit_markdown_file(
            write(tmp_path, "padded.md", padded), tmp_path)
        assert result["metrics"]["br_tags_count"] == 12
        assert result["score"] < lean["score"]

    def test_a_self_awarded_grade_badge_is_a_warning(self, audit, tmp_path):
        result = audit.audit_markdown_file(
            write(tmp_path, "r.md", ORNAMENTAL_README), tmp_path)
        assert any("self-awarded" in w for w in result["warnings"])

    def test_an_ordinary_badge_row_is_not_warned_about(self, audit, tmp_path):
        content = LEAN_README.replace(
            "# My Project",
            "# My Project\n\n[![Build](https://img.shields.io/badge/build-passing-green)](https://x.test)")
        result = audit.audit_markdown_file(write(tmp_path, "r.md", content), tmp_path)
        assert result["warnings"] == []

    def test_length_is_scored_against_a_budget(self, audit, tmp_path):
        bloated = LEAN_README + ("\nAnother paragraph of reference material.\n" * 400)
        result = audit.audit_markdown_file(
            write(tmp_path, "bloated.md", bloated), tmp_path)
        assert result["metrics"]["brevity_pts"] == "0/15"
        assert any("manual, not a README" in rec for rec in result["recommendations"])


class TestLinkIntegrity:
    def test_a_broken_relative_link_is_an_error_not_a_style_note(
            self, audit, tmp_path):
        content = LEAN_README + "\nSee [the guide](./docs/GUIDE.md).\n"
        result = audit.audit_markdown_file(write(tmp_path, "r.md", content), tmp_path)
        assert result["errors"] and not result["passed"]
        assert result["metrics"]["link_integrity_pts"] == "15/20"

    def test_a_broken_anchor_is_reported(self, audit, tmp_path):
        content = LEAN_README + "\nJump to [nowhere](#does-not-exist).\n"
        result = audit.audit_markdown_file(write(tmp_path, "r.md", content), tmp_path)
        assert any("does-not-exist" in err for err in result["errors"])

    def test_a_resolvable_link_costs_nothing(self, audit, tmp_path):
        (tmp_path / "LICENSE").write_text("Apache 2.0", encoding="utf-8")
        content = LEAN_README + "\nSee [the licence](./LICENSE).\n"
        result = audit.audit_markdown_file(write(tmp_path, "r.md", content), tmp_path)
        assert result["errors"] == []


class TestThisRepository:
    def test_score_stays_within_bounds(self, audit, tmp_path):
        result = audit.audit_markdown_file(
            write(tmp_path, "r.md", LEAN_README), tmp_path)
        assert 0 <= result["score"] <= 100

    def test_the_repository_readme_passes_its_own_rubric(self, audit, repo_root):
        """A skill that grades READMEs is judged by the one it ships with."""
        result = audit.audit_markdown_file(repo_root / "README.md", repo_root)
        assert result["passed"], (result["score"], result["errors"],
                                  result["recommendations"])
