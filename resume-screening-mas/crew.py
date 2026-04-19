from __future__ import annotations
from pathlib import Path

from agents.member3_risk_scoring import run_member3
from state.shared_state import save_state

JD_PATH          = "data/jd.txt"
RESUME_FOLDER    = "data/resumes"
OUTPUT_PATH      = "outputs/shortlist.md"
REQUIRED_SKILLS  = ["Python", "SQL", "Docker", "REST APIs"]
PREFERRED_SKILLS = ["Kubernetes", "AWS", "FastAPI"]
REQUIRED_YEARS   = 3


def main() -> None:
    Path("outputs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Seed state manually until Members 1 & 2 are implemented
    state = {
        "job_requirements": {
            "required_skills":    REQUIRED_SKILLS,
            "preferred_skills":   PREFERRED_SKILLS,
            "minimum_experience": REQUIRED_YEARS,
        },
        # Dummy candidates to test Member 3 end-to-end
        "fit_results": [
            {
                "name": "Anne Perera",
                "skills": ["Python", "SQL", "Docker", "FastAPI", "AWS"],
                "experience_years": 4,
                "missing_critical_skills": [],
            },
            {
                "name": "John Silva",
                "skills": ["Python", "REST APIs"],
                "experience_years": 2,
                "missing_critical_skills": ["SQL", "Docker"],
            },
            {
                "name": "Kasun Fernando",
                "skills": ["Python", "SQL", "Docker", "REST APIs", "Kubernetes"],
                "experience_years": 5,
                "missing_critical_skills": [],
            },
        ],
    }
    save_state(state)

    print("\n" + "="*50)
    print("MEMBER 1 — Resume Intelligence Agent")
    print("="*50)
    print("  [Not implemented yet — using dummy fit_results]")

    print("\n" + "="*50)
    print("MEMBER 2 — Job Fit Analysis Agent")
    print("="*50)
    print("  [Not implemented yet — using dummy fit_results]")

    print("\n" + "="*50)
    print("MEMBER 3 — Risk and Scoring Agent")
    print("="*50)
    state = run_member3(state)

    # Print results so you can verify output
    for r in state.get("scoring_results", []):
        print(f"  {r['name']}: score={r['score']}  risk={r['risk_level']}")
        if r["risk_flags"]:
            for flag in r["risk_flags"]:
                print(f"    ⚠ {flag}")

    print("\n" + "="*50)
    print("MEMBER 4 — Ranking and Report Agent")
    print("="*50)
    print("  [Not implemented yet]")

    print("\n" + "="*50)
    print("DONE")
    print(f"State   → state/shared_state.json")
    print("="*50)


if __name__ == "__main__":
    main()