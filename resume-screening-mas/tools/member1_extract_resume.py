"""
tools/member1_extract_resume.py
Member 1 — Deterministic resume extraction tools.
"""
from __future__ import annotations
import re
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SKILL_ALIASES: dict[str, str] = {
    "py": "Python", "python3": "Python", "python 3": "Python",
    "mysql": "SQL", "postgresql": "SQL", "postgres": "SQL",
    "sqlite": "SQL", "mssql": "SQL",
    "docker-compose": "Docker", "dockerfile": "Docker",
    "k8s": "Kubernetes", "kube": "Kubernetes",
    "rest": "REST APIs", "rest api": "REST APIs", "restful": "REST APIs",
    "restful api": "REST APIs",
    "amazon web services": "AWS", "amazon aws": "AWS",
    "fast api": "FastAPI",
    "js": "JavaScript",
    "ts": "TypeScript",
    "nodejs": "Node.js", "node js": "Node.js",
    "reactjs": "React", "react.js": "React",
}

KNOWN_SKILLS: dict[str, str] = {
    "python": "Python", "java": "Java", "sql": "SQL", "docker": "Docker",
    "kubernetes": "Kubernetes", "react": "React", "angular": "Angular",
    "node.js": "Node.js", "javascript": "JavaScript", "typescript": "TypeScript",
    "aws": "AWS", "azure": "Azure", "gcp": "GCP",
    "machine learning": "Machine Learning", "deep learning": "Deep Learning",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "git": "Git", "linux": "Linux",
    "rest apis": "REST APIs", "graphql": "GraphQL",
    "mongodb": "MongoDB", "postgresql": "PostgreSQL",
    "redis": "Redis", "fastapi": "FastAPI", "django": "Django",
    "flask": "Flask", "spring boot": "Spring Boot",
    "microservices": "Microservices", "ci/cd": "CI/CD", "devops": "DevOps",
}

def extract_candidate_fields(raw: dict[str, Any]) -> dict[str, Any]:
    text: str = raw.get("raw_text", "") or ""
    text_lower = text.lower()
    return {
        "name":             raw.get("name", "Unknown"),
        "file":             raw.get("file", ""),
        "path":             raw.get("path", ""),
        "raw_text":         text,
        "email":            _extract_email(text),
        "experience_years": _extract_years_of_experience(text_lower),
        "skills":           _extract_skills(text_lower),
        "education":        _extract_education(text_lower),
    }

def normalise_skills(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw_skill in skills:
        s = raw_skill.strip().lower()
        if not s:
            continue
        if s in SKILL_ALIASES:
            canonical = SKILL_ALIASES[s]
        elif s in KNOWN_SKILLS:
            canonical = KNOWN_SKILLS[s]
        else:
            canonical = raw_skill.strip().title()
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return sorted(result)

def validate_candidate_profile(fields: dict[str, Any], job_requirements: dict[str, Any] | None = None) -> dict[str, Any]:
    notes: list[str] = []
    job_requirements = job_requirements or {}
    name = fields.get("name", "")
    if not name or name == "Unknown":
        notes.append("Candidate name missing or could not be parsed.")
    skills = fields.get("skills", [])
    if not skills:
        notes.append("No skills could be extracted from the resume.")
    exp_years = fields.get("experience_years")
    if exp_years is None:
        notes.append("Years of experience could not be determined.")
    required_skills  = [s.lower() for s in job_requirements.get("required_skills",  [])]
    preferred_skills = [s.lower() for s in job_requirements.get("preferred_skills", [])]
    min_exp          = job_requirements.get("minimum_experience", 0) or 0
    cand_skills_lower = [s.lower() for s in skills]
    matched_req  = [s for s in required_skills  if s in cand_skills_lower]
    matched_pref = [s for s in preferred_skills if s in cand_skills_lower]
    missing_req  = [s for s in required_skills  if s not in cand_skills_lower]
    if missing_req:
        notes.append(f"Missing required skills: {', '.join(missing_req)}")
    if exp_years is not None and min_exp and exp_years < min_exp:
        notes.append(f"Experience shortfall: {exp_years} yr(s) vs {min_exp} yr(s) required.")
    req_score  = (len(matched_req)  / max(len(required_skills),  1)) * 60
    pref_score = (len(matched_pref) / max(len(preferred_skills), 1)) * 20 if preferred_skills else 0
    exp_score  = 20 if (exp_years is not None and (not min_exp or exp_years >= min_exp)) else 0
    match_score = round(min(100, req_score + pref_score + exp_score))
    valid = len(notes) == 0 or (bool(skills) and name not in ("", "Unknown"))
    return {"valid": valid, "notes": notes, "match_score": match_score}

def _extract_email(text: str) -> str:
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else ""

def _extract_years_of_experience(text_lower: str) -> int | None:
    """
    Extract years of experience from resume text.

    Handles patterns like:
      - "3+ years of experience"
      - "3+ years of software development experience"
      - "3+ years of professional experience"
      - "3 years experience"
      - "experience of 3+ years"
      - "3+ yrs experience"
    """
    patterns = [
        # "3+ years of experience"  or  "3+ years of <anything up to 4 words> experience"
        r'(\d+)\+?\s*years?\s+of\s+(?:\w+\s+){0,4}experience',

        # "3+ years experience"  (no "of")
        r'(\d+)\+?\s*years?\s+experience',

        # "experience of 3+ years" / "experience: 3 years"
        r'experience[:\s]+(?:of\s+)?(\d+)\+?\s*years?',

        # "3+ yrs of <anything> experience"
        r'(\d+)\+?\s*yrs?\s+of\s+(?:\w+\s+){0,4}experience',

        # "3+ yrs experience"
        r'(\d+)\+?\s*yrs?\s+experience',
    ]

    for pat in patterns:
        m = re.search(pat, text_lower)
        if m:
            return int(m.group(1))

    # Fallback — infer span from calendar years found in the document
    years_found = re.findall(r'\b(20\d{2})\b', text_lower)
    if len(years_found) >= 2:
        years_int = sorted(set(int(y) for y in years_found))
        span = years_int[-1] - years_int[0]
        if 0 < span <= 40:
            return span

    return None

def _extract_skills(text_lower: str) -> list[str]:
    found: list[str] = []
    for keyword, display in KNOWN_SKILLS.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            found.append(display)
    return found

def _extract_education(text_lower: str) -> str:
    if re.search(r'\bph\.?d\b|doctor(?:ate)?', text_lower):
        return "PhD / Doctorate"
    if re.search(r"\bmaster'?s?\b|m\.sc\.?|msc\b|m\.eng", text_lower):
        return "Master's degree"
    if re.search(r"\bbachelor'?s?\b|b\.sc\.?|bsc\b|b\.eng|b\.tech", text_lower):
        return "Bachelor's degree"
    if re.search(r'\bdiploma\b|\bhnd\b', text_lower):
        return "Diploma / HND"
    return "Not specified"