from __future__ import annotations


def calculate_candidate_score(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    candidate_years: int | None,
    required_years: int | None,
    missing_critical_skills: list[str],
) -> dict:
    """
    Compute a deterministic rule-based baseline score for a candidate.

    Scoring weights:
        - Skills match:           40 points max
        - Experience match:       30 points max
        - Preferred skills:       15 points max
        - Critical skill penalty: -10 per missing critical (capped at -30)

    Args:
        candidate_skills:        Skills from the candidate resume.
        required_skills:         Must-have skills from the JD.
        preferred_skills:        Nice-to-have skills from the JD.
        candidate_years:         Years of experience or None if unknown.
        required_years:          Minimum years required by JD or None.
        missing_critical_skills: Critical skills the candidate lacks.

    Returns:
        dict containing base_score, skills_score, experience_score,
        preferred_score, critical_penalty, matched_required,
        missing_required, preferred_matched, risk_level.
    """
    cand_set = {s.lower().strip() for s in candidate_skills}
    req_set  = {s.lower().strip() for s in required_skills}
    pref_set = {s.lower().strip() for s in preferred_skills}

    matched_required  = sorted(cand_set & req_set)
    missing_required  = sorted(req_set - cand_set)
    preferred_matched = sorted(cand_set & pref_set)

    # Skills score — 40 points max
    skills_score = round(
        len(matched_required) / max(len(req_set), 1) * 40, 2
    )

    # Experience score — 30 points max
    if required_years is not None and candidate_years is not None:
        exp_ratio = min(candidate_years / max(required_years, 1), 1.0)
    elif candidate_years is not None:
        exp_ratio = 0.7
    else:
        exp_ratio = 0.3
    experience_score = round(exp_ratio * 30, 2)

    # Preferred skills score — 15 points max
    if pref_set:
        pref_ratio = len(preferred_matched) / max(len(pref_set), 1)
    else:
        pref_ratio = 0.0
    preferred_score = round(pref_ratio * 15, 2)

    # Critical skill penalty — capped at -30
    critical_penalty = round(
        max(-30.0, len(missing_critical_skills) * -10.0), 2
    )

    # Final base score clamped 0-100
    base_score = round(
        max(0.0, min(100.0,
            skills_score + experience_score + preferred_score + critical_penalty
        )), 2
    )

    # Risk level
    if base_score >= 75 and len(missing_critical_skills) == 0:
        risk_level = "Low"
    elif base_score >= 50 or len(missing_critical_skills) <= 1:
        risk_level = "Medium"
    else:
        risk_level = "High"

    return {
        "base_score":        base_score,
        "skills_score":      skills_score,
        "experience_score":  experience_score,
        "preferred_score":   preferred_score,
        "critical_penalty":  critical_penalty,
        "matched_required":  matched_required,
        "missing_required":  missing_required,
        "preferred_matched": preferred_matched,
        "risk_level":        risk_level,
    }


def detect_risk_flags(
    missing_critical_skills: list[str],
    candidate_years: int | None,
    required_years: int | None,
    base_score: float,
) -> list[str]:
    """
    Identify specific hiring risk flags for a candidate.

    Args:
        missing_critical_skills: Critical skills absent from the resume.
        candidate_years:         Candidate years of experience or None.
        required_years:          Minimum years required by JD or None.
        base_score:              The computed base score from calculate_candidate_score.

    Returns:
        List of human-readable risk flag strings. Empty list means no flags.
    """
    flags: list[str] = []

    for skill in missing_critical_skills:
        flags.append(f"Missing critical skill: {skill}")

    if candidate_years is None:
        flags.append("Experience duration not stated on resume")
    elif required_years is not None and candidate_years < required_years:
        flags.append(
            f"Insufficient experience: has {candidate_years} yr(s), "
            f"requires {required_years} yr(s)"
        )

    if base_score < 40:
        flags.append("Overall profile is a weak match for this role")

    return flags