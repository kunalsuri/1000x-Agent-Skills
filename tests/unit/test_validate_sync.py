"""
Tests for the multi-agent-docs parity validator.

Its job is to notice when CLAUDE.md and AGENTS.md drift apart, which is the
exact failure this repository's own CLAUDE.md warns about.
"""

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def sync(load_script):
    return load_script("skills/custom/multi-agent-docs/scripts/validate_sync.py")


class TestCommandExtraction:
    def test_command_bullets_are_extracted(self, sync):
        text = "- **Test**: `pytest -q`\n- **Build**: `make all`\n"
        assert sync.extract_commands(text) == {"pytest -q", "make all"}

    def test_commands_under_a_command_heading_are_extracted(self, sync):
        text = "## Essential Commands\n\n- `npm run build`\n- `npm test`\n"
        assert sync.extract_commands(text) == {"npm run build", "npm test"}

    def test_todo_placeholders_are_ignored(self, sync):
        assert sync.extract_commands("- **Test**: `TODO: add tests`\n") == set()

    def test_prose_without_commands_yields_nothing(self, sync):
        assert sync.extract_commands("Just some ordinary prose.\n") == set()

    def test_extraction_stops_at_the_next_heading(self, sync):
        text = "## Commands\n\n- `make build`\n\n## Notes\n\n- `not-a-command.md`\n"
        assert "make build" in sync.extract_commands(text)

    def test_this_repository_documents_its_commands(self, sync, repo_root):
        commands = sync.extract_commands((repo_root / "CLAUDE.md").read_text(encoding="utf-8"))
        assert commands, "CLAUDE.md documents no commands"


class TestArchitecturePaths:
    def test_paths_under_an_architecture_heading_are_extracted(self, sync):
        text = "## Directory Architecture\n\n- `src/`: source\n- `docs/`: documentation\n"
        assert sync.extract_arch_paths(text) == {"src/", "docs/"}

    def test_non_path_code_spans_are_ignored(self, sync):
        text = "## Architecture\n\n- `someFunction`: not a path\n"
        assert sync.extract_arch_paths(text) == set()

    def test_windows_separators_are_normalised(self, sync):
        text = "## Architecture\n\n- `src\\\\lib/`: code\n"
        assert all("\\" not in p for p in sync.extract_arch_paths(text))


class TestSimilarity:
    def test_identical_documents_score_one(self, sync):
        assert sync.compute_jaccard_similarity("alpha beta", "alpha beta") == 1.0

    def test_disjoint_documents_score_zero(self, sync):
        assert sync.compute_jaccard_similarity("alpha beta", "gamma delta") == 0.0

    def test_empty_input_scores_zero_rather_than_dividing_by_zero(self, sync):
        assert sync.compute_jaccard_similarity("", "alpha") == 0.0
        assert sync.compute_jaccard_similarity("alpha", "") == 0.0

    def test_partial_overlap_lands_between(self, sync):
        score = sync.compute_jaccard_similarity("alpha beta gamma", "beta gamma delta")
        assert 0.0 < score < 1.0

    def test_comparison_is_case_insensitive(self, sync):
        assert sync.compute_jaccard_similarity("Alpha Beta", "alpha beta") == 1.0

    def test_similarity_is_symmetric(self, sync):
        a, b = "alpha beta gamma", "beta delta"
        assert sync.compute_jaccard_similarity(a, b) == sync.compute_jaccard_similarity(b, a)


class TestValidateSync:
    def test_missing_files_are_reported(self, sync, tmp_path):
        result = sync.validate_sync(tmp_path)
        joined = " ".join(result["errors"])
        assert "CLAUDE.md" in joined and "AGENTS.md" in joined

    def test_this_repository_keeps_its_agent_docs_in_sync(self, sync, repo_root):
        """The repository's own stated rule, enforced instead of merely stated."""
        result = sync.validate_sync(repo_root)
        assert result["errors"] == [], result["errors"]
        assert result["warnings"] == [], result["warnings"]

    def test_this_repository_scaffolds_both_agent_directories(self, sync, repo_root):
        """CLAUDE.md and AGENTS.md each describe a directory; both must exist."""
        assert (repo_root / ".claude").is_dir()
        assert (repo_root / ".agents").is_dir()

    def test_nested_agents_doc_matches_the_root_one(self, sync, repo_root):
        root = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
        nested = (repo_root / ".agents" / "AGENTS.md").read_text(encoding="utf-8")
        assert root == nested
