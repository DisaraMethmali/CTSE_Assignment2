# test_run_member2.py  (temporary file - delete after confirming it works)

from agents.member2_job_fit_analysis import run_job_fit_agent

# Simulate what Member 1 would put into the shared state
test_state = {
    "job_description": """
    We are looking for a Software Engineer with strong Python and SQL skills.
    The candidate should have experience with Docker and REST APIs.
    A minimum of 2 years of experience is required.
    A Bachelor's degree in Computer Science or a related field is preferred.
    """,
    "parsed_candidates": [
        {
            "candidate_id": "cand_001",
            "name": "John Silva",
            "skills": ["Python", "SQL", "React"],
            "experience_years": 3,
            "education": "BSc in IT",
            "certifications": ["AWS Cloud Practitioner"],
            "projects": ["Inventory System"]
        },
        {
            "candidate_id": "cand_002",
            "name": "Anne Perera",
            "skills": ["Python", "SQL", "Docker", "REST API"],
            "experience_years": 4,
            "education": "BSc in Computer Science",
            "certifications": [],
            "projects": ["E-commerce Platform"]
        }
    ],
    "fit_results": [],
    "job_requirements": {},
    "resume_files": [],
    "scoring_results": [],
    "ranked_candidates": [],
    "final_report": "",
    "execution_trace": []
}

result_state = run_job_fit_agent(test_state)

import json
print("\n=== FIT RESULTS ===")
print(json.dumps(result_state["fit_results"], indent=2))