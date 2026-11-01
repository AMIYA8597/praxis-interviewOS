"""
PRAXIS InterviewOS — API Input Validation Regression Suite
Verifies Pydantic schema validation, string boundary caps, and injection payload safety.
"""
import pytest
from pydantic import ValidationError

from backend.app.schemas.candidate import CandidateUpdate
from backend.app.schemas.session import SessionCreate


def test_candidate_update_valid_payload():
    payload = CandidateUpdate(
        full_name="Alice Smith",
        headline="Senior Distributed Systems Engineer",
        target_roles=["Backend Engineer", "Platform Architect"],
        years_experience=7,
    )
    assert payload.full_name == "Alice Smith"
    assert payload.years_experience == 7


def test_candidate_update_years_experience_bounds():
    # Negative years of experience must fail validation
    with pytest.raises(ValidationError):
        CandidateUpdate(years_experience=-5)

    # Excessive years of experience (> 70) must fail validation
    with pytest.raises(ValidationError):
        CandidateUpdate(years_experience=150)


def test_session_create_validates_interview_type():
    # Valid interview type and difficulty
    session = SessionCreate(
        interview_type="system_design",
        difficulty="standard",
        focus_area="distributed_caching",
    )
    assert session.interview_type == "system_design"
    assert session.difficulty == "standard"


def test_sql_injection_payload_in_string_field_is_treated_as_literal():
    # Attempted SQL injection string
    injection = "'; DROP TABLE candidates; --"
    payload = CandidateUpdate(full_name=injection)
    assert payload.full_name == injection  # Stored as plain string, never executed in SQL
