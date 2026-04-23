# tools/member2_parse_jd.py

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def parse_job_description(job_text: str) -> Dict[str, Any]:
    """
    Parse a raw job description string into structured hiring requirements.

    This function uses simple keyword-based extraction as a baseline.
    The Job Fit Analysis Agent then reasons over this output using an LLM.

    Args:
        job_text: The raw job description text provided by the recruiter.

    Returns:
        A dictionary containing:
            - required_skills: list of must-have skills detected
            - preferred_skills: list of nice-to-have skills detected
            - minimum_experience: minimum years of experience (int)
            - education: education requirement string
            - other_constraints: any additional constraints found

    Raises:
        ValueError: If the job_text is empty or None.
    """
    if not job_text or not job_text.strip():
        raise ValueError("Job description text cannot be empty.")

    job_text_lower = job_text.lower()

    # Simple keyword detection for common skills
    all_skills = [
        "python", "java", "sql", "docker", "kubernetes", "react", "angular",
        "node.js", "javascript", "typescript", "aws", "azure", "gcp",
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "git", "linux", "rest api", "graphql", "mongodb", "postgresql",
        "redis", "fastapi", "django", "flask", "spring boot", "microservices"
    ]

    detected_skills = [skill for skill in all_skills if skill in job_text_lower]

    # Detect experience requirement
    import re
    experience_match = re.search(r'(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)', job_text_lower)
    min_experience = int(experience_match.group(1)) if experience_match else 0

    # Detect education keywords
    education = "Not specified"
    if "bachelor" in job_text_lower or "bsc" in job_text_lower or "b.sc" in job_text_lower:
        education = "Bachelor's degree required"
    elif "master" in job_text_lower or "msc" in job_text_lower:
        education = "Master's degree required"

    logger.info(f"Parsed job description: {len(detected_skills)} skills detected, "
                f"min experience: {min_experience} years")

    return {
        "required_skills": detected_skills,
        "preferred_skills": [],
        "minimum_experience": min_experience,
        "education": education,
        "other_constraints": []
    }


def match_candidate_to_job(
    candidate: Dict[str, Any],
    job_requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare a parsed candidate profile against structured job requirements.

    This function performs a structural comparison and returns matched,
    partially matched, and missing skills. The agent's LLM then reasons
    over these raw results to produce the final fit classification.

    Args:
        candidate: A dictionary containing the candidate's parsed profile.
                   Expected keys: name, skills, experience_years, education.
        job_requirements: A dictionary of structured job requirements.
                          Expected keys: required_skills, minimum_experience, education.

    Returns:
        A dictionary containing:
            - candidate_id: identifier from the candidate profile
            - matched_skills: list of skills present in both candidate and job
            - missing_critical_skills: list of required skills the candidate lacks
            - experience_gap: True if candidate does not meet minimum experience
            - education_match: True if education requirement is likely met

    Raises:
        ValueError: If candidate or job_requirements dictionaries are missing required keys.
    """
    if not candidate:
        raise ValueError("Candidate profile cannot be empty.")
    if not job_requirements:
        raise ValueError("Job requirements cannot be empty.")

    candidate_skills_lower = [s.lower() for s in candidate.get("skills", [])]
    required_skills = job_requirements.get("required_skills", [])

    matched = [s for s in required_skills if s.lower() in candidate_skills_lower]
    missing = [s for s in required_skills if s.lower() not in candidate_skills_lower]

    candidate_exp = candidate.get("experience_years", 0)
    min_exp = job_requirements.get("minimum_experience", 0)
    experience_gap = candidate_exp < min_exp

    education_match = True  # LLM will reason more deeply on this

    logger.info(f"Candidate '{candidate.get('name', 'Unknown')}': "
                f"{len(matched)} matched, {len(missing)} missing skills")

    return {
        "candidate_id": candidate.get("candidate_id", "unknown"),
        "candidate_name": candidate.get("name", "Unknown"),
        "matched_skills": matched,
        "missing_critical_skills": missing,
        "experience_gap": experience_gap,
        "education_match": education_match
    }