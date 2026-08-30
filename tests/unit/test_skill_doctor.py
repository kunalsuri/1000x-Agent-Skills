"""Tests for utils/skill_doctor.py, the convenience wrapper around the validator."""

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def doctor(load_script):
    return load_script("utils/skill_doctor.py")


class TestWrapper:
    def test_wrapper_exposes_the_validator_entry_point(self, doctor):
        assert callable(doctor.main)

    def test_wrapper_delegates_to_validate_skills(self, doctor, load_script):
        """A wrapper that drifted from what it wraps would validate nothing."""
        validator = load_script("scripts/validate_skills.py")
        assert doctor.main.__module__ == validator.main.__module__ or \
            doctor.main.__name__ == validator.main.__name__

    def test_wrapper_runs_and_reports_on_this_repository(self, doctor, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["skill_doctor.py"])
        with pytest.raises(SystemExit) as exit_info:
            doctor.main()
        assert exit_info.value.code == 0
        assert "SKILL DOCTOR" in capsys.readouterr().out
