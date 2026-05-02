# tools/member2_parse_jd.py

import re
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def parse_job_description(job_text: str) -> Dict[str, Any]:
    """
    Parse a raw job description string into structured hiring requirements.
    """
    if not job_text or not job_text.strip():
        raise ValueError("Job description text cannot be empty.")

    job_text_lower = job_text.lower()

    all_skills = [
        "python", "java", "sql", "docker", "kubernetes", "react", "angular",
        "node.js", "javascript", "typescript", "aws", "azure", "gcp",
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "git", "linux", "rest api", "graphql", "mongodb", "postgresql",
        "redis", "fastapi", "django", "flask", "spring boot", "microservices",
    ]

    detected_skills = [s for s in all_skills if s in job_text_lower]

    experience_match = re.search(
        r'(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)', job_text_lower
    )
    min_experience = int(experience_match.group(1)) if experience_match else 0

    education = "Not specified"
    if "bachelor" in job_text_lower or "bsc" in job_text_lower or "b.sc" in job_text_lower:
        education = "Bachelor's degree required"
    elif "master" in job_text_lower or "msc" in job_text_lower:
        education = "Master's degree required"

    logger.info(
        "Parsed JD: %d skills detected, min experience: %d yr(s)",
        len(detected_skills), min_experience,
    )

    return {
        "required_skills":   detected_skills,
        "preferred_skills":  [],
        "minimum_experience": min_experience,
        "education":         education,
        "other_constraints": [],
    }


def match_candidate_to_job(
    candidate: Dict[str, Any],
    job_requirements: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare a parsed candidate profile against structured job requirements.
    """
    if not candidate:
        raise ValueError("Candidate profile cannot be empty.")
    if not job_requirements:
        raise ValueError("Job requirements cannot be empty.")

    candidate_skills_lower = [s.lower() for s in candidate.get("skills", [])]
    required_skills = job_requirements.get("required_skills", [])

    matched = [s for s in required_skills if s.lower() in candidate_skills_lower]
    missing = [s for s in required_skills if s.lower() not in candidate_skills_lower]

    # ── FIX: treat None experience as 0 so the comparison never crashes ──
    candidate_exp: int = candidate.get("experience_years") or 0
    min_exp:       int = job_requirements.get("minimum_experience") or 0
    experience_gap: bool = candidate_exp < min_exp

    logger.info(
        "Candidate '%s': %d matched, %d missing, exp %d vs req %d",
        candidate.get("name", "Unknown"),
        len(matched), len(missing), candidate_exp, min_exp,
    )

    return {
        "candidate_id":           candidate.get("candidate_id", "unknown"),
        "candidate_name":         candidate.get("name", "Unknown"),
        "matched_skills":         matched,
        "missing_critical_skills": missing,
        "experience_gap":         experience_gap,
        "education_match":        True,   # LLM reasons further on this
    }