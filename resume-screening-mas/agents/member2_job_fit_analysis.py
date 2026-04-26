# agents/member2_job_fit_analysis.py

import json
import logging
from typing import Dict, Any

import ollama

from tools.member2_parse_jd import parse_job_description, match_candidate_to_job
from state.shared_state import save_state, log_agent_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "qwen2.5:7b"

SYSTEM_PROMPT = """You are a Job Fit Analysis Agent working in a professional hiring system.

Your job is to compare a candidate's profile against the requirements of a job description.

You will receive:
1. The job requirements (skills, experience, education)
2. A candidate profile (skills, experience, education)
3. A preliminary structural comparison result

Your task is to:
- Identify which required skills the candidate clearly meets
- Identify which required skills the candidate partially meets (similar but not exact)
- Identify which required skills are missing
- Assess experience fit
- Assess education fit
- Classify the overall fit level as: Strong, Moderate, or Weak
- Write a clear one-paragraph explanation

Rules:
- Do NOT overstate the candidate's suitability
- Do NOT invent skills the candidate does not have
- If evidence is unclear, say so honestly
- Return ONLY valid JSON. No preamble. No extra text.

Return this exact JSON structure:
{
  "candidate_id": "string",
  "candidate_name": "string",
  "matched_skills": ["skill1", "skill2"],
  "partial_matches": ["skill3"],
  "missing_critical_skills": ["skill4"],
  "experience_fit": "Meets requirement" or "Does not meet requirement" or "Unclear",
  "education_fit": "Relevant" or "Not relevant" or "Not specified",
  "fit_level": "Strong" or "Moderate" or "Weak",
  "fit_reasoning": "One paragraph explanation here."
}
"""


def run_job_fit_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job Fit Analysis Agent node for LangGraph.

    Reads the job description and all parsed candidates from shared state,
    runs fit analysis for each candidate using the qwen2.5:7b model,
    and writes the results back to the shared state.

    Args:
        state: The shared LangGraph state dictionary.

    Returns:
        Updated state with 'fit_results' populated.
    """
    logger.info("=== Job Fit Analysis Agent started ===")

    job_text = state.get("job_description", "")
    parsed_candidates = state.get("parsed_candidates", [])

    if not job_text:
        logger.error("No job description found in state.")
        return state

    if not parsed_candidates:
        logger.warning("No parsed candidates found in state.")
        return state

    # Step 1: Parse the job description using the tool
    logger.info("Parsing job description using tool...")
    job_requirements = parse_job_description(job_text)
    state["job_requirements"] = job_requirements
    logger.info(f"Job requirements extracted: {job_requirements}")

    fit_results = []

    for candidate in parsed_candidates:
        logger.info(f"Analysing candidate: {candidate.get('name', 'Unknown')}")

        # Step 2: Run structural comparison using the tool
        structural_comparison = match_candidate_to_job(candidate, job_requirements)

        # Step 3: Build the prompt for the LLM
        user_prompt = f"""
Job Requirements:
{json.dumps(job_requirements, indent=2)}

Candidate Profile:
{json.dumps(candidate, indent=2)}

Preliminary Structural Comparison:
{json.dumps(structural_comparison, indent=2)}

Perform a full fit analysis and return the JSON result.
"""

        # Step 4: Call the LLM
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )

            raw_output = response["message"]["content"].strip()
            logger.info(f"LLM raw output for {candidate.get('name')}: {raw_output[:200]}...")

            # Step 5: Parse and validate the JSON output
            fit_result = json.loads(raw_output)

            # Ensure required fields exist
            required_fields = [
                "candidate_id", "candidate_name", "matched_skills",
                "partial_matches", "missing_critical_skills",
                "experience_fit", "education_fit", "fit_level", "fit_reasoning"
            ]
            for field in required_fields:
                if field not in fit_result:
                    fit_result[field] = "unknown"

            fit_results.append(fit_result)
            logger.info(f"Fit result for {candidate.get('name')}: {fit_result.get('fit_level')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON for candidate "
                         f"{candidate.get('name')}: {e}")
            fit_results.append({
                "candidate_id": candidate.get("candidate_id", "unknown"),
                "candidate_name": candidate.get("name", "Unknown"),
                "matched_skills": structural_comparison.get("matched_skills", []),
                "partial_matches": [],
                "missing_critical_skills": structural_comparison.get("missing_critical_skills", []),
                "experience_fit": "Unclear",
                "education_fit": "Unclear",
                "fit_level": "Weak",
                "fit_reasoning": "Could not parse LLM output. Structural comparison used as fallback."
            })

        except Exception as e:
            logger.error(f"LLM call failed for candidate {candidate.get('name')}: {e}")

    # Step 6: Write results back to shared state
    state["fit_results"] = fit_results

    # Save state to disk and log the event for observability
    save_state(state)
    log_agent_event(
        agent_name="Job Fit Analysis Agent",
        tool_called="parse_job_description, match_candidate_to_job",
        input_summary=f"{len(parsed_candidates)} candidates analysed",
        output_summary=f"{len(fit_results)} fit results produced"
    )

    logger.info(f"=== Job Fit Analysis Agent completed. {len(fit_results)} candidates analysed. ===")
    return state