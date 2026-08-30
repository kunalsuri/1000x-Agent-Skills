"""
Global pytest configuration and hermetic harness.

Two things matter here:

  * `no_network` is a real guard, not a stub. It replaces the functions that
    actually open outbound connections, so a test that tries to reach the
    network fails loudly instead of silently succeeding on a machine that
    happens to be online. A test suite for a repository whose central claim
    is "these skills make no network calls" cannot itself be casual about
    network access.

  * `load_script` imports the repository's CLI scripts by path. They live in
    skills/*/scripts/ and scripts/ rather than an installed package, so
    normal imports do not reach them.
"""

import importlib.util
import socket
import sys
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
SKILLS = REPO_ROOT / "skills" / "custom"


class NetworkAccessDenied(RuntimeError):
    """Raised when a test attempts an outbound connection."""


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hermetic isolation: safe mock environment variables, no host leakage."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Block outbound network access for the whole suite.

    Sockets can still be constructed (some libraries do so harmlessly); what
    is blocked is connecting them, which is the operation that would leave
    the machine.
    """
    def deny(*args: Any, **kwargs: Any) -> None:
        raise NetworkAccessDenied(
            "This test attempted an outbound network connection. Nothing in "
            "this repository should need one."
        )

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


def _load(path: Path, name: str) -> Any:
    """
    Execute a script as a module.

    The script's own directory goes on sys.path for the duration, because
    several of these scripts import their siblings (run_preflight.py imports
    analyze_codebase) exactly as they do when run from the command line.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    script_dir = str(path.parent)
    added = script_dir not in sys.path
    if added:
        sys.path.insert(0, script_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        if added:
            sys.path.remove(script_dir)
    return module


@pytest.fixture(scope="session")
def load_script():
    """
    Load a repository script by relative path.

        module = load_script("scripts/validate_skills.py")
        module = load_script("skills/custom/readme-designer/scripts/audit_readme.py")
    """
    cache: Dict[str, Any] = {}

    def loader(rel_path: str) -> Any:
        if rel_path not in cache:
            path = REPO_ROOT / rel_path
            if not path.exists():
                raise FileNotFoundError(f"No such script: {rel_path}")
            cache[rel_path] = _load(path, "loaded_" + path.stem)
        return cache[rel_path]

    return loader


@pytest.fixture
def skill_factory(tmp_path: Path):
    """
    Build a minimal, valid skill directory on disk.

    Tests mutate the result to create the specific defect under test, which
    keeps each test's intent visible instead of buried in setup.
    """
    def build(name: str = "sample-skill", *, frontmatter: str = None,
              body: str = "# Sample\n\nBody text.\n",
              attestation: Dict[str, Any] = None,
              evals: Dict[str, Any] = None,
              with_digest: bool = True) -> Path:
        import json
        skill_dir = tmp_path / "skills" / "custom" / name
        (skill_dir / "evals").mkdir(parents=True)

        if frontmatter is None:
            frontmatter = (
                f"name: {name}\n"
                f"description: A sample skill. Use when exercising the validator.\n"
                f"version: 1.0.0\n"
            )
        (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")

        if attestation is None:
            attestation = {
                "skill_name": name,
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
                "provenance": {"source_type": "original", "license": "Apache-2.0"},
            }
        (skill_dir / "attestation.json").write_text(
            json.dumps(attestation, indent=2), encoding="utf-8")

        if evals is None:
            evals = {
                "skill_name": name,
                "trigger_evaluation": {
                    "positive_prompts": [
                        {"id": f"pos-0{i}", "prompt": f"Prompt {i}", "expected_trigger": True}
                        for i in range(1, 4)
                    ],
                    "negative_prompts": [
                        {"id": "neg-01", "prompt": "Unrelated", "expected_trigger": False}
                    ],
                },
            }
        (skill_dir / "evals" / "test-cases.json").write_text(
            json.dumps(evals, indent=2), encoding="utf-8")

        if with_digest:
            digest_mod = _load(SCRIPTS / "skill_digest.py", "digest_for_factory")
            digest_mod.update_skill(skill_dir)
        return skill_dir

    return build
