"""
test_member3_scoring.py
Complete test suite for Member 3 — Risk and Scoring Agent.

Covers:
  - Tool correctness
  - Edge cases
  - Security / bias prevention
  - Boundary conditions
"""
from __future__ import annotations
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.member3_score_tool import calculate_candidate_score, detect_risk_flags


# ─────────────────────────────────────────────────────────────
# Shared test data
# ─────────────────────────────────────────────────────────────

JD_REQUIRED  = ["Python", "SQL", "Docker", "REST APIs"]
JD_PREFERRED = ["Kubernetes", "AWS", "FastAPI"]
JD_MIN_YEARS = 3


@pytest.fixture
def strong_candidate() -> dict:
    """Candidate who meets all requirements."""
    return {
        "skills":           ["Python", "SQL", "Docker", "REST APIs", "Kubernetes"],
        "years":            5,
        "missing_critical": [],
    }


@pytest.fixture
def partial_candidate() -> dict:
    """Candidate who meets some requirements."""
    return {
        "skills":           ["Python", "SQL"],
        "years":            3,
        "missing_critical": ["Docker"],
    }


@pytest.fixture
def weak_candidate() -> dict:
    """Candidate who meets almost no requirements."""
    return {
        "skills":           ["Excel", "PowerPoint"],
        "years":            1,
        "missing_critical": ["Python", "SQL", "Docker", "REST APIs"],
    }


# ─────────────────────────────────────────────────────────────
# calculate_candidate_score tests
# ─────────────────────────────────────────────────────────────

class TestCalculateCandidateScore:

    def test_strong_candidate_scores_high(self, strong_candidate):
        result = calculate_candidate_score(
            candidate_skills        = strong_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = strong_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = strong_candidate["missing_critical"],
        )
        assert result["base_score"] >= 70, (
            f"Strong candidate should score >= 70, got {result['base_score']}"
        )

    def test_weak_candidate_scores_low(self, weak_candidate):
        result = calculate_candidate_score(
            candidate_skills        = weak_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = weak_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = weak_candidate["missing_critical"],
        )
        assert result["base_score"] < 40, (
            f"Weak candidate should score < 40, got {result['base_score']}"
        )

    def test_strong_scores_higher_than_weak(self, strong_candidate, weak_candidate):
        strong = calculate_candidate_score(
            candidate_skills        = strong_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = strong_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = strong_candidate["missing_critical"],
        )
        weak = calculate_candidate_score(
            candidate_skills        = weak_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = weak_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = weak_candidate["missing_critical"],
        )
        assert strong["base_score"] > weak["base_score"]

    def test_score_always_within_0_to_100(self, partial_candidate):
        result = calculate_candidate_score(
            candidate_skills        = partial_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = partial_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = partial_candidate["missing_critical"],
        )
        assert 0 <= result["base_score"] <= 100

    def test_matched_and_missing_skills_correct(self, partial_candidate):
        result = calculate_candidate_score(
            candidate_skills        = partial_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = partial_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = partial_candidate["missing_critical"],
        )
        assert "python" in result["matched_required"]
        assert "sql"    in result["matched_required"]
        assert "docker" in result["missing_required"]

    def test_critical_penalty_reduces_score(self):
        no_penalty = calculate_candidate_score(
            candidate_skills        = ["Python", "SQL", "Docker", "REST APIs"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = [],
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = [],
        )
        with_penalty = calculate_candidate_score(
            candidate_skills        = ["Python", "SQL", "Docker", "REST APIs"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = [],
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = ["Docker"],
        )
        assert no_penalty["base_score"] > with_penalty["base_score"]

    def test_critical_penalty_capped_at_minus_30(self):
        result = calculate_candidate_score(
            candidate_skills        = ["Python"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = [],
            candidate_years         = 2,
            required_years          = 3,
            missing_critical_skills = ["Docker", "SQL", "REST APIs", "Kubernetes", "AWS"],
        )
        assert result["critical_penalty"] >= -30

    def test_preferred_skills_add_to_score(self):
        with_preferred = calculate_candidate_score(
            candidate_skills        = ["Python", "SQL", "Docker", "REST APIs", "Kubernetes"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = [],
        )
        without_preferred = calculate_candidate_score(
            candidate_skills        = ["Python", "SQL", "Docker", "REST APIs"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = [],
        )
        assert with_preferred["base_score"] > without_preferred["base_score"]

    def test_unknown_experience_gives_partial_not_zero(self):
        result = calculate_candidate_score(
            candidate_skills        = ["Python", "SQL"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = [],
            candidate_years         = None,
            required_years          = 3,
            missing_critical_skills = [],
        )
        assert result["experience_score"] > 0
        assert result["experience_score"] < 30

    def test_risk_level_low_for_perfect_candidate(self, strong_candidate):
        result = calculate_candidate_score(
            candidate_skills        = strong_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = strong_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = strong_candidate["missing_critical"],
        )
        assert result["risk_level"] == "Low"

    def test_risk_level_high_for_weak_candidate(self, weak_candidate):
        result = calculate_candidate_score(
            candidate_skills        = weak_candidate["skills"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = weak_candidate["years"],
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = weak_candidate["missing_critical"],
        )
        assert result["risk_level"] == "High"

    def test_empty_candidate_skills_does_not_crash(self):
        result = calculate_candidate_score(
            candidate_skills        = [],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = 2,
            required_years          = 3,
            missing_critical_skills = ["Python", "SQL"],
        )
        assert result["base_score"] >= 0
        assert result["matched_required"] == []

    def test_empty_required_skills_no_division_by_zero(self):
        result = calculate_candidate_score(
            candidate_skills        = ["Python"],
            required_skills         = [],
            preferred_skills        = [],
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = [],
        )
        assert result["base_score"] >= 0

    def test_all_skills_matched_gives_full_skills_score(self):
        result = calculate_candidate_score(
            candidate_skills        = ["Python", "SQL", "Docker", "REST APIs"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = [],
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = [],
        )
        assert result["skills_score"] == 40.0

    # ── BIAS / SECURITY TEST ──────────────────────────────────
    def test_identical_inputs_give_identical_scores(self):
        """
        Same inputs must always produce the same score.
        The tool must be purely deterministic — no randomness,
        no name-based logic, no hidden bias.
        """
        inputs = dict(
            candidate_skills        = ["Python", "SQL", "Docker", "REST APIs"],
            required_skills         = JD_REQUIRED,
            preferred_skills        = JD_PREFERRED,
            candidate_years         = 4,
            required_years          = JD_MIN_YEARS,
            missing_critical_skills = [],
        )
        result_a = calculate_candidate_score(**inputs)
        result_b = calculate_candidate_score(**inputs)
        assert result_a["base_score"] == result_b["base_score"], (
            "Tool must be deterministic — same inputs must always give same score"
        )

    def test_score_does_not_accept_name_parameter(self):
        """
        The tool signature must not include a name parameter.
        Names must never influence the numeric score.
        """
        import inspect
        sig = inspect.signature(calculate_candidate_score)
        assert "name" not in sig.parameters, (
            "Tool must not accept a name parameter — names cause bias"
        )

    def test_case_insensitive_skill_matching(self):
        """
        Skill matching must be case-insensitive.
        'python' and 'Python' and 'PYTHON' are the same skill.
        """
        result = calculate_candidate_score(
            candidate_skills        = ["PYTHON", "sql", "Docker"],
            required_skills         = ["Python", "SQL", "Docker", "REST APIs"],
            preferred_skills        = [],
            candidate_years         = 3,
            required_years          = 3,
            missing_critical_skills = [],
        )
        assert "python" in result["matched_required"]
        assert "sql"    in result["matched_required"]
        assert "docker" in result["matched_required"]


# ─────────────────────────────────────────────────────────────
# detect_risk_flags tests
# ─────────────────────────────────────────────────────────────

class TestDetectRiskFlags:

    def test_missing_critical_skill_creates_flag(self):
        flags = detect_risk_flags(
            missing_critical_skills = ["Docker"],
            candidate_years         = 3,
            required_years          = 3,
            base_score              = 65.0,
        )
        assert any("Docker" in f for f in flags)

    def test_multiple_missing_skills_each_get_a_flag(self):
        flags = detect_risk_flags(
            missing_critical_skills = ["Docker", "Kubernetes"],
            candidate_years         = 2,
            required_years          = 3,
            base_score              = 50.0,
        )
        assert any("Docker"     in f for f in flags)
        assert any("Kubernetes" in f for f in flags)

    def test_insufficient_experience_creates_flag(self):
        flags = detect_risk_flags(
            missing_critical_skills = [],
            candidate_years         = 1,
            required_years          = 3,
            base_score              = 60.0,
        )
        assert any("experience" in f.lower() for f in flags)

    def test_unknown_experience_creates_flag(self):
        flags = detect_risk_flags(
            missing_critical_skills = [],
            candidate_years         = None,
            required_years          = 3,
            base_score              = 55.0,
        )
        assert any("experience" in f.lower() for f in flags)

    def test_low_score_creates_weak_match_flag(self):
        flags = detect_risk_flags(
            missing_critical_skills = [],
            candidate_years         = 3,
            required_years          = 3,
            base_score              = 30.0,
        )
        assert any("weak match" in f.lower() for f in flags)

    def test_perfect_candidate_has_no_flags(self):
        flags = detect_risk_flags(
            missing_critical_skills = [],
            candidate_years         = 5,
            required_years          = 3,
            base_score              = 90.0,
        )
        assert flags == [], f"Expected no flags but got: {flags}"

    def test_returns_list_type(self):
        flags = detect_risk_flags(
            missing_critical_skills = ["Docker"],
            candidate_years         = 2,
            required_years          = 3,
            base_score              = 50.0,
        )
        assert isinstance(flags, list)

    def test_no_flags_when_experience_exceeds_requirement(self):
        flags = detect_risk_flags(
            missing_critical_skills = [],
            candidate_years         = 10,
            required_years          = 3,
            base_score              = 85.0,
        )
        exp_flags = [f for f in flags if "experience" in f.lower()]
        assert exp_flags == []