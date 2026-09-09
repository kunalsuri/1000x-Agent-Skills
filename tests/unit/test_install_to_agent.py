"""
Tests for scripts/install_to_agent.py.

This is the only tool here that writes outside the repository, into the
user's home directory, and the only one that deletes a directory to do it.
The tests concentrate on the two things that matter at that blast radius:
it does not write unless asked, and it refuses to delete anything that is
not demonstrably a skill it is replacing.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _can_symlink() -> bool:
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "s"
            src.mkdir()
            dst = Path(td) / "d"
            dst.symlink_to(src, target_is_directory=True)
        return True
    except OSError:
        return False


CAN_SYMLINK = _can_symlink()
SYMLINK_SKIP = "Symlink creation not permitted in this environment"


@pytest.fixture
def installer(load_script):
    return load_script("scripts/install_to_agent.py")


class TestTargetResolution:
    def test_claude_target_resolves_under_home(self, installer):
        assert installer.get_target_path("claude") == Path.home() / ".claude" / "skills"

    def test_antigravity_target_resolves_under_home(self, installer):
        expected = Path.home() / ".gemini" / "config" / "skills"
        assert installer.get_target_path("antigravity") == expected

    def test_cursor_target_is_workspace_relative(self, installer):
        assert installer.get_target_path("cursor") == Path.cwd() / ".cursor" / "rules"

    def test_unknown_target_raises(self, installer):
        with pytest.raises(ValueError):
            installer.get_target_path("emacs")


class TestDiscovery:
    def test_only_canonical_skills_are_installable(self, installer, repo_root):
        """The .agents/ mirror is a copy; installing from it would double-install.

        This asserted "skills/custom" in the path until skills/anthropic/ was
        populated with vendored upstream skills. That was never the invariant --
        discover_installable rglobs all of skills/ and always did -- it was just
        incidentally true while custom was the only category with anything in it.
        The invariant is that a source lives under skills/<category>/<skill> and
        never under the mirror, so that is what is checked here.
        """
        found = installer.discover_installable(repo_root)
        assert found
        assert not any(".agents" in p.parts for p in found)
        for skill_dir in found:
            relative = skill_dir.relative_to(repo_root)
            assert relative.parts[0] == "skills", f"{relative} is outside skills/"
            assert len(relative.parts) == 3, f"{relative} is not skills/<category>/<skill>"

    def test_every_discovered_directory_is_a_skill(self, installer, repo_root):
        assert all((p / "SKILL.md").exists() for p in installer.discover_installable(repo_root))

    def test_empty_tree_discovers_nothing(self, installer, tmp_path):
        assert installer.discover_installable(tmp_path) == []


class TestReplacementGuard:
    """
    is_replaceable_skill_dir stands between a typo and an rmtree in $HOME.
    Every one of these must stay a refusal.
    """

    def make_skill(self, path: Path) -> Path:
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        return path

    def test_a_real_skill_directory_is_replaceable(self, installer, tmp_path):
        target = tmp_path / "skills"
        target.mkdir()
        dest = self.make_skill(target / "demo")
        ok, _ = installer.is_replaceable_skill_dir(dest, target)
        assert ok is True

    def test_directory_without_skill_md_is_refused(self, installer, tmp_path):
        target = tmp_path / "skills"
        (target / "notaskill").mkdir(parents=True)
        ok, why = installer.is_replaceable_skill_dir(target / "notaskill", target)
        assert ok is False and "SKILL.md" in why

    @pytest.mark.skipif(not CAN_SYMLINK, reason=SYMLINK_SKIP)
    def test_symlink_is_refused(self, installer, tmp_path):
        """Following a symlink would let a link in the target delete anything."""
        target = tmp_path / "skills"
        target.mkdir()
        real = self.make_skill(tmp_path / "elsewhere")
        link = target / "demo"
        link.symlink_to(real, target_is_directory=True)
        ok, why = installer.is_replaceable_skill_dir(link, target)
        assert ok is False and "symlink" in why

    @pytest.mark.skipif(not CAN_SYMLINK, reason=SYMLINK_SKIP)
    def test_symlink_pointing_inside_the_target_is_still_refused(self, installer, tmp_path):
        """
        The case the symlink check exists for: a link whose resolved parent IS
        the target directory, so containment alone would wave it through.
        """
        target = tmp_path / "skills"
        target.mkdir()
        self.make_skill(target / "real")
        link = target / "demo"
        link.symlink_to(target / "real", target_is_directory=True)
        ok, why = installer.is_replaceable_skill_dir(link, target)
        assert ok is False and "symlink" in why

    def test_path_outside_the_target_directory_is_refused(self, installer, tmp_path):
        target = tmp_path / "skills"
        target.mkdir()
        outside = self.make_skill(tmp_path / "outside")
        ok, why = installer.is_replaceable_skill_dir(outside, target)
        assert ok is False and "not directly inside" in why

    def test_nested_path_inside_the_target_is_refused(self, installer, tmp_path):
        target = tmp_path / "skills"
        nested = self.make_skill(target / "a" / "b")
        ok, why = installer.is_replaceable_skill_dir(nested, target)
        assert ok is False and "not directly inside" in why

    def test_a_file_where_a_directory_belongs_is_refused(self, installer, tmp_path):
        target = tmp_path / "skills"
        target.mkdir()
        (target / "demo").write_text("not a directory", encoding="utf-8")
        ok, why = installer.is_replaceable_skill_dir(target / "demo", target)
        assert ok is False and "not a directory" in why


class TestPreviewIsTheDefault:
    def run(self, installer, monkeypatch, tmp_path, argv):
        monkeypatch.setattr("sys.argv", argv)
        monkeypatch.setattr(installer, "get_target_path", lambda target: tmp_path / "dest")
        with pytest.raises(SystemExit) as exit_info:
            installer.main()
        return exit_info.value.code

    def test_a_bare_run_writes_nothing(self, installer, monkeypatch, tmp_path, capsys):
        code = self.run(installer, monkeypatch, tmp_path,
                        ["install_to_agent.py", "--target", "claude", "--all"])
        assert code == 0
        assert not (tmp_path / "dest").exists(), "preview must not create the destination"
        assert "PREVIEW ONLY" in capsys.readouterr().out

    def test_preview_reports_capabilities_and_digest(self, installer, monkeypatch,
                                                     tmp_path, capsys):
        self.run(installer, monkeypatch, tmp_path,
                 ["install_to_agent.py", "--target", "claude", "--all"])
        out = capsys.readouterr().out
        assert "capabilities:" in out and "sha256:" in out and "safety audit:" in out

    def test_apply_actually_installs(self, installer, monkeypatch, tmp_path, capsys):
        code = self.run(installer, monkeypatch, tmp_path,
                        ["install_to_agent.py", "--target", "claude",
                         "--skill", "readme-designer", "--apply"])
        assert code == 0
        assert (tmp_path / "dest" / "readme-designer" / "SKILL.md").exists()

    def test_apply_twice_replaces_cleanly(self, installer, monkeypatch, tmp_path):
        argv = ["install_to_agent.py", "--target", "claude",
                "--skill", "readme-designer", "--apply"]
        self.run(installer, monkeypatch, tmp_path, argv)
        assert self.run(installer, monkeypatch, tmp_path, argv) == 0
        assert (tmp_path / "dest" / "readme-designer" / "SKILL.md").exists()

    def test_unknown_skill_name_is_an_error(self, installer, monkeypatch, tmp_path):
        code = self.run(installer, monkeypatch, tmp_path,
                        ["install_to_agent.py", "--target", "claude",
                         "--skill", "does-not-exist"])
        assert code != 0

    def test_selection_is_required(self, installer, monkeypatch, tmp_path):
        """A bare --target must not mass-install by accident."""
        monkeypatch.setattr("sys.argv", ["install_to_agent.py", "--target", "claude"])
        with pytest.raises(SystemExit) as exit_info:
            installer.main()
        assert exit_info.value.code == 2

    def test_dry_run_and_apply_conflict(self, installer, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.argv", ["install_to_agent.py", "--target", "claude",
                                         "--all", "--dry-run", "--apply"])
        with pytest.raises(SystemExit) as exit_info:
            installer.main()
        assert exit_info.value.code == 2
