from __future__ import annotations
from pathlib import Path

from agents.member3_risk_scoring import run_member3
from state.shared_state import save_state, load_state

JD_PATH          = "data/jd.txt"
RESUME_FOLDER    = "data/resumes"
OUTPUT_PATH      = "outputs/shortlist.md"
REQUIRED_SKILLS  = ["Python", "SQL", "Docker", "REST APIs"]
PREFERRED_SKILLS = ["Kubernetes", "AWS", "FastAPI"]
REQUIRED_YEARS   = 3


def main() -> None:
    Path("outputs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    
    state = {
        "job_requirements": {
            "required_skills":    REQUIRED_SKILLS,
            "preferred_skills":   PREFERRED_SKILLS,
            "minimum_experience": REQUIRED_YEARS,
        },
        "candidates": [
            {
                "name":             "Anne Perera",
                "skills":           ["Python", "SQL", "Docker", "FastAPI", "AWS"],
                "experience_years": 4,
            },
            {
                "name":             "John Silva",
                "skills":           ["Python", "REST APIs"],
                "experience_years": 2,
            },
            {
                "name":             "Kasun Fernando",
                "skills":           ["Python", "SQL", "Docker", "REST APIs", "Kubernetes"],
                "experience_years": 5,
            },
        ],
        "fit_analyses": [
            {
                "candidate_name":         "Anne Perera",
                "missing_critical_skills": [],
            },
            {
                "candidate_name":         "John Silva",
                "missing_critical_skills": ["SQL", "Docker"],
            },
            {
                "candidate_name":         "Kasun Fernando",
                "missing_critical_skills": [],
            },
        ],
    }
    save_state(state)

    print("\n" + "="*50)
    print("MEMBER 1 — Resume Intelligence Agent")
    print("="*50)
    print("  [Not implemented yet — using dummy candidates]")

    print("\n" + "="*50)
    print("MEMBER 2 — Job Fit Analysis Agent")
    print("="*50)
    print("  [Not implemented yet — using dummy fit_analyses]")

    print("\n" + "="*50)
    print("MEMBER 3 — Risk and Scoring Agent")
    print("="*50)
    run_member3(
        required_skills  = REQUIRED_SKILLS,
        preferred_skills = PREFERRED_SKILLS,
        required_years   = REQUIRED_YEARS,
    )

    # Print results from shared state
    results = load_state().get("scored_candidates", [])
    for r in results:
        print(f"  {r['candidate_name']}: score={r['final_score']}  risk={r['risk_level']}")
        if r.get("risk_flags"):
            for flag in r["risk_flags"]:
                print(f"    ⚠ {flag}")

    print("\n" + "="*50)
    print("MEMBER 4 — Ranking and Report Agent")
    print("="*50)
    print("  [Not implemented yet]")

    print("\n" + "="*50)
    print("DONE")
    print(f"Report  → {OUTPUT_PATH}")
    print(f"Log     → logs/agent_trace.log")
    print(f"State   → state/shared_state.json")
    print("="*50)


if __name__ == "__main__":
    main()