from __future__ import annotations

from agents.member4_report_agent import member4_ranking_report_node
from state.shared_state import MASState


def main() -> None:
    state: MASState = {
        "job_description": "Backend Developer role requiring Python, SQL, Docker, and 2+ years experience.",
        "job_requirements": {
            "required_skills": ["Python", "SQL", "Docker"],
            "minimum_experience": 2,
        },
        "resume_files": [],
        "parsed_candidates": [],
        "fit_results": [],
        "scoring_results": [
            {
                "name": "Anne Perera",
                "score": 91,
                "risk_level": "Low",
                "risk_flags": [],
                "fit_reasoning": "Matches all core skills and exceeds experience requirement.",
                "score_reasoning": "Excellent alignment with the role.",
            },
            {
                "name": "John Silva",
                "score": 78,
                "risk_level": "Medium",
                "risk_flags": ["Missing critical skill: Docker"],
                "fit_reasoning": "Strong backend fit but lacks Docker.",
                "score_reasoning": "Good candidate with one important technical gap.",
            },
            {
                "name": "Nimal Fernando",
                "score": 69,
                "risk_level": "Medium",
                "risk_flags": ["Limited relevant experience"],
                "fit_reasoning": "Some matching skills but lacks depth in required tools.",
                "score_reasoning": "Moderate suitability with visible weaknesses.",
            },
        ],
        "ranked_candidates": [],
        "shortlisted_candidates": [],
        "ranking_summary": {},
        "final_report": "",
        "report_metadata": {},
        "execution_trace": [],
    }

    updated_state = member4_ranking_report_node(state, model_name="mistral:7b", top_n=2)

    print("\n=== Ranked Candidates ===")
    for candidate in updated_state["ranked_candidates"]:
        print(
            f"Rank {candidate['rank']}: "
            f"{candidate['name']} - Score {candidate['score']} - Risk {candidate.get('risk_level', 'Unknown')}"
        )

    print("\n=== Shortlisted Candidates ===")
    for candidate in updated_state["shortlisted_candidates"]:
        print(f"Rank {candidate['rank']}: {candidate['name']}")

    print("\n=== Ranking Summary ===")
    print(updated_state["ranking_summary"])

    print("\n=== Final Report ===")
    print(updated_state["final_report"])

    print("\n=== Report Metadata ===")
    print(updated_state["report_metadata"])

    print("\n=== Execution Trace Count ===")
    print(len(updated_state["execution_trace"]))


if __name__ == "__main__":
    main()