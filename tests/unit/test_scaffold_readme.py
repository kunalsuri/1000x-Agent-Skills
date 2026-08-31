"""Tests for the readme-designer generator."""

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def generator(load_script):
    return load_script("skills/custom/readme-designer/scripts/scaffold_readme.py")


@pytest.fixture
def readme(generator):
    return generator.generate_readme_content(
        "Demo Project", "A punchy tagline", "A longer description.",
        "Test Author", "Apache 2.0")


class TestGeneration:
    def test_project_name_appears_in_the_h1(self, readme):
        h1 = next(line for line in readme.splitlines() if line.startswith("# "))
        assert "Demo Project" in h1

    def test_tagline_and_description_are_included(self, readme):
        assert "A punchy tagline" in readme and "A longer description." in readme

    def test_author_and_licence_are_included(self, readme):
        assert "Test Author" in readme and "Apache 2.0" in readme

    def test_output_is_not_trivially_short(self, readme):
        assert len(readme.splitlines()) > 20

    def test_special_characters_in_the_name_survive(self, generator):
        content = generator.generate_readme_content(
            "C++ & Friends", "t", "d", "a", "MIT")
        assert "C++ & Friends" in content


class TestGeneratedReadmeSatisfiesTheAuditor:
    def test_the_generator_output_passes_its_own_audit(self, generator, load_script, tmp_path):
        """
        This skill both writes READMEs and grades them. If its own output
        scored badly, the grader and the generator would be describing
        different standards.
        """
        audit = load_script("skills/custom/readme-designer/scripts/audit_readme.py")
        path = tmp_path / "README.md"
        path.write_text(generator.generate_readme_content(
            "Demo", "Tagline", "Description.", "Author", "Apache 2.0"), encoding="utf-8")
        result = audit.audit_markdown_file(path, tmp_path)
        assert result["passed"], (result["score"], result["recommendations"])

    def test_the_template_ships_none_of_the_ornament_the_rubric_penalises(
            self, readme):
        """
        A template is edited down, not up. Shipping a badge wall, padding tags
        or a self-awarded grade badge means they get filled in and kept.
        """
        assert "<br/>" not in readme
        assert "shields.io" not in readme
        assert "align=\"center\"" not in readme
