"""
tests/test_member1_resume_agent.py
Complete test suite for Member 1 — Resume Intelligence Agent.

Covers:
  - Tool correctness  (extract_candidate_fields, normalise_skills, validate_candidate_profile)
  - Edge cases        (empty input, None values, malformed data)
  - Security / bias   (name must not influence extraction, deterministic output)
  - Boundary conditions
"""
from __future__ import annotations

import sys
import os
import inspect

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.member1_resume_tool import (
    extract_candidate_fields,
    normalise_skills,
    validate_candidate_profile,
)


# ─────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def complete_candidate() -> dict:
    """A fully populated candidate dictionary."""
    return {
        "name":             "Anne Perera",
        "skills":           ["Python", "SQL", "Docker", "FastAPI", "AWS"],
        "experience_years": 4,
        "education":        "BSc Computer Science",
        "email":            "anne@example.com",
        "phone":            "+94771234567",
    }


@pytest.fixture
def minimal_candidate() -> dict:
    """A candidate with only the mandatory fields."""
    return {
        "name":             "Kasun Fernando",
        "skills":           ["Python"],
        "experience_years": 2,
    }


@pytest.fixture
def empty_candidate() -> dict:
    """A candidate dict with no useful data."""
    return {
        "name":   "",
        "skills": [],
    }


# ─────────────────────────────────────────────────────────────
# extract_candidate_fields tests
# ─────────────────────────────────────────────────────────────

class TestExtractCandidateFields:

    def test_extracts_name_correctly(self, complete_candidate):
        result = extract_candidate_fields(complete_candidate)
        assert result["name"] == "Anne Perera"

    def test_extracts_skills_as_list(self, complete_candidate):
        result = extract_candidate_fields(complete_candidate)
        assert isinstance(result["skills"], list)
        assert "Python" in result["skills"]
        assert "Docker" in result["skills"]

    def test_extracts_experience_years_as_int(self, complete_candidate):
        result = extract_candidate_fields(complete_candidate)
        assert result["experience_years"] == 4
        assert isinstance(result["experience_years"], int)

    def test_missing_optional_fields_get_defaults(self, minimal_candidate):
        result = extract_candidate_fields(minimal_candidate)
        assert result["education"] == "Not specified"
        assert result["email"]     == ""
        assert result["phone"]     == ""
        assert result["raw_text"]  == ""

    def test_skills_as_comma_string_parsed_to_list(self):
        raw = {"name": "Test", "skills": "Python, SQL, Docker"}
        result = extract_candidate_fields(raw)
        assert isinstance(result["skills"], list)
        assert "Python" in result["skills"]
        assert "SQL"    in result["skills"]

    def test_experience_years_string_coerced_to_int(self):
        raw = {"name": "Test", "skills": ["Python"], "experience_years": "5"}
        result = extract_candidate_fields(raw)
        assert result["experience_years"] == 5

    def test_experience_years_none_stays_none(self):
        raw = {"name": "Test", "skills": ["Python"]}
        result = extract_candidate_fields(raw)
        assert result["experience_years"] is None

    def test_invalid_experience_years_becomes_none(self):
        raw = {"name": "Test", "skills": ["Python"], "experience_years": "not-a-number"}
        result = extract_candidate_fields(raw)
        assert result["experience_years"] is None

    def test_empty_skills_list_returns_empty_list(self):
        raw = {"name": "Test", "skills": []}
        result = extract_candidate_fields(raw)
        assert result["skills"] == []

    def test_raises_type_error_for_non_dict(self):
        with pytest.raises(TypeError):
            extract_candidate_fields("not a dict")

    def test_raises_value_error_for_empty_dict(self):
        with pytest.raises(ValueError):
            extract_candidate_fields({})

    def test_whitespace_stripped_from_name(self):
        raw = {"name": "  Anne Perera  ", "skills": ["Python"]}
        result = extract_candidate_fields(raw)
        assert result["name"] == "Anne Perera"

    # ── BIAS / SECURITY TEST ──────────────────────────────────
    def test_extraction_is_deterministic(self, complete_candidate):
        """Same input must always produce the same output — no randomness."""
        result_a = extract_candidate_fields(complete_candidate)
        result_b = extract_candidate_fields(complete_candidate)
        assert result_a == result_b, (
            "extract_candidate_fields must be deterministic — same input, same output"
        )

    def test_all_guaranteed_keys_present(self, minimal_candidate):
        """Output must always contain all six guaranteed keys."""
        result = extract_candidate_fields(minimal_candidate)
        for key in ("name", "skills", "experience_years", "education", "email", "phone"):
            assert key in result, f"Key '{key}' missing from extracted fields"


# ─────────────────────────────────────────────────────────────
# normalise_skills tests
# ─────────────────────────────────────────────────────────────

class TestNormaliseSkills:

    def test_removes_duplicate_skills_case_insensitive(self):
        result = normalise_skills(["Python", "python", "PYTHON"])
        assert result.count("Python") == 1

    def test_preserves_original_casing_of_first_occurrence(self):
        result = normalise_skills(["FastAPI", "fastapi"])
        assert result[0] == "FastAPI"

    def test_removes_empty_strings(self):
        result = normalise_skills(["Python", "", "  ", "SQL"])
        assert "" not in result
        assert "  " not in result

    def test_strips_whitespace_from_each_skill(self):
        result = normalise_skills(["  Python  ", " SQL "])
        assert "Python" in result
        assert "SQL"    in result

    def test_empty_list_returns_empty_list(self):
        result = normalise_skills([])
        assert result == []

    def test_single_skill_returned_as_single_item_list(self):
        result = normalise_skills(["Python"])
        assert result == ["Python"]

    def test_raises_type_error_for_non_list(self):
        with pytest.raises(TypeError):
            normalise_skills("Python, SQL")

    def test_order_preserved_for_unique_skills(self):
        skills = ["Python", "SQL", "Docker"]
        result = normalise_skills(skills)
        assert result == ["Python", "SQL", "Docker"]

    def test_large_skill_list_no_duplicates(self):
        skills = ["Python"] * 50 + ["SQL"] * 50
        result = normalise_skills(skills)
        assert len(result) == 2

    # ── BIAS / SECURITY TEST ──────────────────────────────────
    def test_normalise_is_deterministic(self):
        """Same list must always produce the same output."""
        skills = ["Python", "SQL", "docker", "Python", "FastAPI"]
        assert normalise_skills(skills) == normalise_skills(skills)

    def test_does_not_accept_name_parameter(self):
        """Tool signature must not include a name parameter — names cause bias."""
        sig = inspect.signature(normalise_skills)
        assert "name" not in sig.parameters, (
            "normalise_skills must not accept a name parameter"
        )


# ─────────────────────────────────────────────────────────────
# validate_candidate_profile tests
# ─────────────────────────────────────────────────────────────

class TestValidateCandidateProfile:

    def test_valid_complete_profile_passes(self, complete_candidate):
        fields = extract_candidate_fields(complete_candidate)
        result = validate_candidate_profile(fields)
        assert result["valid"] is True
        assert result["notes"] == []

    def test_missing_name_fails_validation(self):
        profile = {"name": "", "skills": ["Python"], "experience_years": 3}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is False
        assert any("name" in note.lower() for note in result["notes"])

    def test_unknown_name_fails_validation(self):
        profile = {"name": "Unknown", "skills": ["Python"], "experience_years": 3}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is False

    def test_empty_skills_list_fails_validation(self):
        profile = {"name": "Test Candidate", "skills": [], "experience_years": 3}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is False
        assert any("skill" in note.lower() for note in result["notes"])

    def test_none_experience_years_passes_validation(self):
        profile = {"name": "Test Candidate", "skills": ["Python"], "experience_years": None}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is True

    def test_negative_experience_years_fails_validation(self):
        profile = {"name": "Test Candidate", "skills": ["Python"], "experience_years": -1}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is False

    def test_valid_profile_with_zero_experience(self):
        profile = {"name": "Test Candidate", "skills": ["Python"], "experience_years": 0}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is True

    def test_returns_dict_with_valid_and_notes_keys(self, complete_candidate):
        fields = extract_candidate_fields(complete_candidate)
        result = validate_candidate_profile(fields)
        assert "valid" in result
        assert "notes" in result

    def test_notes_is_always_a_list(self, complete_candidate):
        fields = extract_candidate_fields(complete_candidate)
        result = validate_candidate_profile(fields)
        assert isinstance(result["notes"], list)

    def test_raises_type_error_for_non_dict(self):
        with pytest.raises(TypeError):
            validate_candidate_profile("not a dict")

    def test_raises_value_error_for_empty_dict(self):
        with pytest.raises(ValueError):
            validate_candidate_profile({})

    def test_multiple_failures_all_reported_in_notes(self):
        profile = {"name": "", "skills": [], "experience_years": -5}
        result  = validate_candidate_profile(profile)
        assert result["valid"] is False
        assert len(result["notes"]) >= 2

    # ── BIAS / SECURITY TEST ──────────────────────────────────
    def test_validation_is_deterministic(self, complete_candidate):
        """Same profile must always produce the same validation result."""
        fields    = extract_candidate_fields(complete_candidate)
        result_a  = validate_candidate_profile(fields)
        result_b  = validate_candidate_profile(fields)
        assert result_a == result_b

    def test_does_not_accept_job_title_parameter(self):
        """
        Tool signature must not include job_title or similar demographic
        parameters that could introduce bias into profile validation.
        """
        sig = inspect.signature(validate_candidate_profile)
        assert "job_title"  not in sig.parameters
        assert "gender"     not in sig.parameters
        assert "nationality" not in sig.parameters