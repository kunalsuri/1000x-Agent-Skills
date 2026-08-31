"""
The demo has to keep being true.

demo/README.md prints verifier output as evidence that the tool catches a
skill which changed after it was approved. Quoted output rots: a rule moves,
a message is reworded, and the README quietly becomes a screenshot of
something that used to happen. These tests re-run the two demo commands on
every CI run and assert the outcomes the README claims.

They also pin the fixture's inertness. The hostile bundle is committed to
this repository, so the property that it does nothing when imported is a
property of the repository, not a comment in a file.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "skills" / "custom" / "third-party-skill-verifier"
          / "scripts" / "verify_skill_bundle.py")
DEMO = ROOT / "demo"


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("verify_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestTheDemoStillHappens:

    def test_the_reviewed_version_has_no_findings(self, verifier):
        record = verifier.verify_bundle(DEMO / "before" / "tidy-imports")
        assert record["verdict"] == verifier.VERDICT_CLEAN, [
            f["check"] for f in record["findings"] if f["severity"] != "INFO"]

    def test_the_updated_version_is_do_not_install(self, verifier):
        record = verifier.verify_bundle(DEMO / "installed-skills" / "tidy-imports")
        assert record["verdict"] == verifier.VERDICT_DO_NOT_INSTALL
        caught = {f["check"] for f in record["findings"]}
        # Each of these is a separate way the same update hides itself.
        assert {"EXT-INVISIBLE-UNICODE", "EXT-AUTORUN",
                "EXT-CAP-UNDECLARED", "EXT-DEPENDENCY"} <= caught

    def test_the_honest_neighbour_stays_quiet(self, verifier):
        """A scanner that shouts at an ordinary skill gets muted in a week."""
        record = verifier.verify_bundle(DEMO / "installed-skills" / "note-taker")
        assert record["verdict"] == verifier.VERDICT_CLEAN, [
            f["check"] for f in record["findings"] if f["severity"] != "INFO"]

    def test_the_stored_record_still_matches_the_bundle_it_was_taken_from(
            self, verifier):
        """--compare is only worth anything if the committed receipt is real."""
        baseline = json.loads(
            (DEMO / "records" / "tidy-imports-2026-08-01.json").read_text(
                encoding="utf-8"))
        record = verifier.verify_bundle(DEMO / "before" / "tidy-imports")
        assert record["bundle"]["digest"] == baseline["bundle"]["digest"]

    def test_comparing_the_update_to_the_receipt_reports_drift(self, verifier):
        baseline = json.loads(
            (DEMO / "records" / "tidy-imports-2026-08-01.json").read_text(
                encoding="utf-8"))
        record = verifier.verify_bundle(
            DEMO / "installed-skills" / "tidy-imports", baseline=baseline)
        assert record["comparison"]["digest_changed"] is True
        assert record["comparison"]["new_findings"]
        assert "EXT-BASELINE-DRIFT" in {f["check"] for f in record["findings"]}

    def test_the_collection_scan_covers_every_installed_skill(self, verifier):
        targets = verifier.resolve_targets([str(DEMO / "installed-skills")],
                                           collection=True)
        assert {path.name for path in targets} == {"tidy-imports", "note-taker"}
        records = [verifier.verify_bundle(path) for path in targets]
        assert verifier.worst_verdict(records) == verifier.VERDICT_DO_NOT_INSTALL


class TestTheFixtureIsInert:
    """
    A hostile-looking file committed to a repository has to be genuinely
    harmless. The demo's value comes from the verifier's reaction to it, not
    from anything it does.
    """

    def test_nothing_in_the_planted_conftest_runs_at_import(self):
        source = (DEMO / "installed-skills" / "tidy-imports" / "tests"
                  / "conftest.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign,
                   ast.Expr)
        for node in tree.body:
            assert isinstance(node, allowed), f"executes at import: {node}"
            if isinstance(node, ast.Expr):
                assert isinstance(node.value, ast.Constant), "not a docstring"

    def test_the_demo_is_outside_the_skills_tree(self):
        """It must never be discovered as a skill by this repo's own tooling."""
        assert not str(DEMO).startswith(str(ROOT / "skills"))
        assert (ROOT / "pytest.ini").read_text(
            encoding="utf-8").count("testpaths = tests") == 1
