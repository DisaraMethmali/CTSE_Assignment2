from __future__ import annotations

from typing import Any
from ollama import chat

from state.shared_state import MASState
from tools.report_logger_tool import (
    append_trace_to_state,
    generate_shortlist,
    log_agent_trace_to_file,
    rank_candidates,
    save_report,
)

AGENT_NAME = "Member4_Ranking_Report_Agent"

SYSTEM_PROMPT = """
You are the Ranking and Report Agent in a locally hosted multi-agent hiring system.

Your responsibilities:
1. Review the candidate scoring results provided by previous agents.
2. Rank candidates from strongest to weakest.
3. Recommend a shortlist.
4. Write a concise recruiter-friendly final report.
5. Do not invent facts.
6. Use only the candidate data provided.
7. Clearly mention strengths, weaknesses, and final recommendation.

Return plain text only.
""".strip()


def build_report_prompt(
    ranked_candidates: list[dict[str, Any]],
    shortlist: list[dict[str, Any]],
) -> str:
    """
    Build the user prompt sent to the LLM for final report generation.

    Args:
        ranked_candidates: Full ranked candidate list.
        shortlist: Top shortlisted candidates.

    Returns:
        Prompt text for the LLM.
    """
    return f"""
Ranked candidates:
{ranked_candidates}

Shortlist:
{shortlist}

Task:
Write a final hiring report for the recruiter.

Include these sections:
1. Candidate ranking summary
2. Shortlisted candidates
3. Key strengths
4. Important weaknesses or risks
5. Final recommendation

Keep the report clear, professional, and factual.
""".strip()


def generate_report_text(
    ranked_candidates: list[dict[str, Any]],
    shortlist: list[dict[str, Any]],
    model_name: str = "mistral:7b",
) -> str:
    """
    Call the Ollama model to generate the final recruiter report.

    Args:
        ranked_candidates: Full ranked candidate list.
        shortlist: Top shortlisted candidates.
        model_name: Local Ollama model name.

    Returns:
        Final report text.
    """
    prompt = build_report_prompt(ranked_candidates, shortlist)

    response = chat(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    return response["message"]["content"]


def member4_ranking_report_node(
    state: MASState,
    model_name: str = "mistral:7b",
    top_n: int = 3,
) -> MASState:
    """
    Member 4 agent node.
    Reads scoring_results from shared state, ranks candidates, generates
    a shortlist, calls the LLM for a final report, updates shared state,
    saves outputs, and logs execution trace.

    Args:
        state: Shared global MAS state.
        model_name: Ollama model used for report generation.
        top_n: Number of candidates to include in the shortlist.

    Returns:
        Updated shared state.

    Raises:
        KeyError: If scoring_results is missing from the state.
        ValueError: If scoring_results is empty.
    """
    if "scoring_results" not in state:
        raise KeyError("Shared state must contain 'scoring_results'")

    scoring_results = state["scoring_results"]

    if not scoring_results:
        raise ValueError("No scoring results found for Member 4 to rank")

    ranked_candidates = rank_candidates(scoring_results)
    shortlist = generate_shortlist(ranked_candidates, top_n=top_n)
    final_report = generate_report_text(
        ranked_candidates=ranked_candidates,
        shortlist=shortlist,
        model_name=model_name,
    )

    state["ranked_candidates"] = ranked_candidates
    state["final_report"] = final_report

    output_data = {
        "ranked_candidates": ranked_candidates,
        "shortlist": shortlist,
        "final_report": final_report,
    }

    save_report(final_report, output_path="outputs/final_report.txt")

    append_trace_to_state(
        state=state,
        agent_name=AGENT_NAME,
        input_data={"scoring_results": scoring_results},
        output_data=output_data,
    )

    log_agent_trace_to_file(
        agent_name=AGENT_NAME,
        input_data={"scoring_results": scoring_results},
        output_data=output_data,
        log_path="outputs/trace_log.jsonl",
    )

    return state