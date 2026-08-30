"""
Pre-flight smoke tests.

These check that the harness itself is wired correctly. A smoke test that
cannot fail tells you nothing, so each of these asserts on something that
genuinely breaks when the environment is misconfigured.
"""

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke


def test_test_environment_variables_are_set() -> None:
    assert os.getenv("TESTING") == "true"
    assert os.getenv("ENV") == "test"


def test_database_url_points_at_memory_not_a_real_host() -> None:
    """A leaked real DATABASE_URL is how a test suite writes to production."""
    assert os.getenv("DATABASE_URL") == "sqlite:///:memory:"


def test_outbound_network_access_is_blocked() -> None:
    """The hermetic guarantee, asserted rather than assumed."""
    import socket
    from conftest import NetworkAccessDenied
    with pytest.raises(NetworkAccessDenied):
        socket.create_connection(("example.com", 80), timeout=1)


def test_repository_tooling_is_importable(load_script) -> None:
    for script in ("scripts/validate_skills.py", "scripts/audit_skill_safety.py",
                   "scripts/skill_digest.py", "scripts/install_to_agent.py"):
        assert load_script(script) is not None


def test_python_version_is_supported() -> None:
    assert sys.version_info >= (3, 9), "the tooling uses modern typing syntax"
