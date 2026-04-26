from __future__ import annotations

from pathlib import Path

from state.shared_state import load_state, save_state
from agents.member3_risk_scoring import run_member3
from agents.member4_report_agent import member4_ranking_report_node
from orchestration.integrate_member3_to_member4 import adapt_member3_output_for_member4


REQUIRED_SKILLS = ["Python", "SQL", "Docker", "REST APIs"]
PREFERRED_SKILLS = ["Kubernetes", "AWS", "FastAPI"]
REQUIRED_YEARS = 3


def main() -> None:
    Path("outputs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    state = {
        "job_description": "Backend Developer role requiring Python, SQL, Docker, and 2+ years experience.",
        "job_requirements": {
            "required_skills": REQUIRED_SKILLS,
            "preferred_skills": PREFERRED_SKILLS,
            "minimum_experience": REQUIRED_YEARS,
        },
        "candidates": [
            {
                "name": "Anne Perera",
                "skills": ["Python", "SQL", "Docker", "FastAPI", "AWS"],
                "experience_years": 4,
            },
            {
                "name": "John Silva",
                "skills": ["Python", "REST APIs"],
                "experience_years": 2,
            },
            {
                "name": "Kasun Fernando",
                "skills": ["Python", "SQL", "Docker", "REST APIs", "Kubernetes"],
                "experience_years": 5,
            },
        ],
        "parsed_candidates": [],
        "fit_analyses": [
            {
                "candidate_name": "Anne Perera",
                "missing_critical_skills": [],
                "fit_reasoning": "Matches all core skills and exceeds experience requirement.",
            },
            {
                "candidate_name": "John Silva",
                "missing_critical_skills": ["SQL", "Docker"],
                "fit_reasoning": "Strong backend fit but lacks Docker and SQL.",
            },
            {
                "candidate_name": "Kasun Fernando",
                "missing_critical_skills": [],
                "fit_reasoning": "Strong match with required backend and infrastructure skills.",
            },
        ],
        "scored_candidates": [],
        "scoring_results": [],
        "ranked_candidates": [],
        "shortlisted_candidates": [],
        "ranking_summary": {},
        "final_report": "",
        "report_metadata": {},
        "execution_trace": [],
    }

    save_state(state)

    run_member3(
        required_skills=REQUIRED_SKILLS,
        preferred_skills=PREFERRED_SKILLS,
        required_years=REQUIRED_YEARS,
    )

    state = load_state()
    state = adapt_member3_output_for_member4(state)
    save_state(state)

    state = member4_ranking_report_node(state, model_name="mistral:7b", top_n=2)
    save_state(state)

    print("\n=== Ranked Candidates ===")
    for candidate in state["ranked_candidates"]:
        print(
            f"Rank {candidate['rank']}: "
            f"{candidate['name']} - Score {candidate['score']} - Risk {candidate.get('risk_level', 'Unknown')}"
        )

    print("\n=== Shortlisted Candidates ===")
    for candidate in state["shortlisted_candidates"]:
        print(f"Rank {candidate['rank']}: {candidate['name']}")

    print("\n=== Ranking Summary ===")
    print(state["ranking_summary"])

    print("\n=== Final Report ===")
    print(state["final_report"])

    print("\n=== Report Metadata ===")
    print(state["report_metadata"])

    print("\n=== Execution Trace Count ===")
    print(len(state.get("execution_trace", [])))


if __name__ == "__main__":
    main()