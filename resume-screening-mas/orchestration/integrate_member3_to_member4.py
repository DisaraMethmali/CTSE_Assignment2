from __future__ import annotations

from typing import Any


def adapt_member3_output_for_member4(state: dict[str, Any]) -> dict[str, Any]:
    """
    Convert Member 3 shared-state output into the format expected by Member 4.

    Member 3 writes:
        state["scored_candidates"]

    Member 4 expects:
        state["scoring_results"]

    This function also merges fit reasoning from fit_analyses.
    """
    scored_candidates = state.get("scored_candidates", [])
    fit_analyses = state.get("fit_analyses", [])

    fit_lookup = {
        item.get("candidate_name"): item
        for item in fit_analyses
    }

    scoring_results: list[dict[str, Any]] = []

    for scored in scored_candidates:
        candidate_name = scored.get("candidate_name", "Unknown")
        fit_data = fit_lookup.get(candidate_name, {})

        scoring_results.append({
            "name": candidate_name,
            "score": scored.get("final_score", 0),
            "risk_level": scored.get("risk_level", "Unknown"),
            "risk_flags": scored.get("risk_flags", []),
            "fit_reasoning": fit_data.get("fit_reasoning", "Fit reasoning not available."),
            "score_reasoning": scored.get("score_reasoning", "Score reasoning not available."),
        })

    state["scoring_results"] = scoring_results
    return state