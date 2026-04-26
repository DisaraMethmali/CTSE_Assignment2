# tests/test_member2_fit_agent.py

import pytest
from tools.member2_parse_jd import parse_job_description, match_candidate_to_job


# ─── Tests for parse_job_description ───────────────────────────────────────────

def test_parse_job_description_detects_skills():
    """Tool should detect skills mentioned in job description."""
    jd = "We need a developer with Python, SQL, and Docker experience."
    result = parse_job_description(jd)
    assert "python" in result["required_skills"]
    assert "sql" in result["required_skills"]
    assert "docker" in result["required_skills"]


def test_parse_job_description_detects_experience():
    """Tool should extract minimum years of experience."""
    jd = "Requires 3+ years of experience in software development."
    result = parse_job_description(jd)
    assert result["minimum_experience"] == 3


def test_parse_job_description_detects_education():
    """Tool should detect education requirements."""
    jd = "A Bachelor's degree in Computer Science is required."
    result = parse_job_description(jd)
    assert "bachelor" in result["education"].lower()


def test_parse_job_description_raises_on_empty():
    """Tool should raise ValueError when given empty input."""
    with pytest.raises(ValueError):
        parse_job_description("")


def test_parse_job_description_raises_on_none():
    """Tool should raise ValueError when given None."""
    with pytest.raises(ValueError):
        parse_job_description(None)


def test_parse_job_description_returns_required_keys():
    """Tool output must always contain the required dictionary keys."""
    jd = "Looking for a Python developer with 2 years experience."
    result = parse_job_description(jd)
    assert "required_skills" in result
    assert "preferred_skills" in result
    assert "minimum_experience" in result
    assert "education" in result
    assert "other_constraints" in result


# ─── Tests for match_candidate_to_job ──────────────────────────────────────────

def test_match_detects_matched_skills():
    """Matched skills should appear when candidate has required skills."""
    candidate = {
        "candidate_id": "c001",
        "name": "John Silva",
        "skills": ["Python", "SQL", "React"],
        "experience_years": 3,
        "education": "BSc in IT"
    }
    job_req = {
        "required_skills": ["python", "sql"],
        "minimum_experience": 2,
        "education": "Bachelor's degree"
    }
    result = match_candidate_to_job(candidate, job_req)
    assert "python" in result["matched_skills"]
    assert "sql" in result["matched_skills"]


def test_match_detects_missing_critical_skills():
    """Missing required skills should be listed as missing_critical_skills."""
    candidate = {
        "candidate_id": "c002",
        "name": "Anne Perera",
        "skills": ["Python"],
        "experience_years": 2,
        "education": "BSc in IT"
    }
    job_req = {
        "required_skills": ["python", "docker"],
        "minimum_experience": 2,
        "education": "Bachelor's degree"
    }
    result = match_candidate_to_job(candidate, job_req)
    assert "docker" in result["missing_critical_skills"]


def test_match_detects_experience_gap():
    """Experience gap should be True if candidate has fewer years than required."""
    candidate = {
        "candidate_id": "c003",
        "name": "Sam Fernando",
        "skills": ["Python"],
        "experience_years": 1,
        "education": "BSc"
    }
    job_req = {
        "required_skills": ["python"],
        "minimum_experience": 3,
        "education": "Bachelor's degree"
    }
    result = match_candidate_to_job(candidate, job_req)
    assert result["experience_gap"] is True


def test_match_no_experience_gap_when_sufficient():
    """Experience gap should be False when candidate meets the requirement."""
    candidate = {
        "candidate_id": "c004",
        "name": "Lisa Mendis",
        "skills": ["Python"],
        "experience_years": 5,
        "education": "BSc"
    }
    job_req = {
        "required_skills": ["python"],
        "minimum_experience": 3,
        "education": "Bachelor's degree"
    }
    result = match_candidate_to_job(candidate, job_req)
    assert result["experience_gap"] is False


def test_match_raises_on_empty_candidate():
    """Function should raise ValueError when candidate is empty."""
    with pytest.raises(ValueError):
        match_candidate_to_job({}, {"required_skills": ["python"]})


def test_match_raises_on_empty_job_requirements():
    """Function should raise ValueError when job requirements are empty."""
    with pytest.raises(ValueError):
        match_candidate_to_job({"name": "Test", "skills": []}, {})


def test_match_returns_correct_candidate_id():
    """Result should carry through the correct candidate_id."""
    candidate = {
        "candidate_id": "cand_99",
        "name": "Test Person",
        "skills": ["Python"],
        "experience_years": 2,
        "education": "BSc"
    }
    job_req = {
        "required_skills": ["python"],
        "minimum_experience": 1,
        "education": ""
    }
    result = match_candidate_to_job(candidate, job_req)
    assert result["candidate_id"] == "cand_99"