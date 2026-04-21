from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort candidates by score in descending order and assign rank numbers.

    Args:
        candidates: List of candidate dictionaries. Each candidate must contain
            a numeric 'score' field.

    Returns:
        A new list sorted from highest score to lowest score, with 'rank' added.

    Raises:
        TypeError: If candidates is not a list.
        KeyError: If any candidate does not contain the 'score' key.
        ValueError: If any score is not numeric.
    """
    if not isinstance(candidates, list):
        raise TypeError("candidates must be a list")

    validated_candidates: list[dict[str, Any]] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise TypeError("Each candidate must be a dictionary")
        if "score" not in candidate:
            raise KeyError("Each candidate must contain a 'score' key")
        if not isinstance(candidate["score"], (int, float)):
            raise ValueError("Candidate 'score' must be numeric")

        validated_candidates.append(candidate.copy())

    ranked = sorted(validated_candidates, key=lambda x: x["score"], reverse=True)

    for index, candidate in enumerate(ranked, start=1):
        candidate["rank"] = index

    return ranked


def generate_shortlist(
    candidates: list[dict[str, Any]],
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """
    Return the top N ranked candidates.

    Args:
        candidates: Ranked candidate list.
        top_n: Number of top candidates to keep.

    Returns:
        The shortlisted candidates.

    Raises:
        TypeError: If candidates is not a list.
        ValueError: If top_n is less than 1.
    """
    if not isinstance(candidates, list):
        raise TypeError("candidates must be a list")

    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    return candidates[:top_n]


def build_ranking_summary(
    ranked_candidates: list[dict[str, Any]],
    shortlist: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a compact summary of ranking results.

    Args:
        ranked_candidates: Full ranked candidate list.
        shortlist: Top shortlisted candidates.

    Returns:
        Summary dictionary containing useful report metadata.
    """
    highest_score = ranked_candidates[0]["score"] if ranked_candidates else None
    lowest_score = ranked_candidates[-1]["score"] if ranked_candidates else None

    risk_distribution: dict[str, int] = {}
    for candidate in ranked_candidates:
        risk_level = str(candidate.get("risk_level", "Unknown"))
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1

    return {
        "total_candidates": len(ranked_candidates),
        "shortlisted_count": len(shortlist),
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "risk_distribution": risk_distribution,
        "generated_at": datetime.utcnow().isoformat(),
    }


def save_report(
    report: str,
    output_path: str = "outputs/final_report.txt",
) -> None:
    """
    Save the final report to a text file.

    Args:
        report: Final recruiter report text.
        output_path: Path where the report should be saved.

    Raises:
        TypeError: If report is not a string.
    """
    if not isinstance(report, str):
        raise TypeError("report must be a string")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def save_ranked_candidates(
    ranked_candidates: list[dict[str, Any]],
    output_path: str = "outputs/ranked_candidates.json",
) -> None:
    """
    Save ranked candidate data to a JSON file.

    Args:
        ranked_candidates: Ranked candidate list.
        output_path: Path where ranked candidates should be saved.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ranked_candidates, indent=2), encoding="utf-8")


def save_shortlist(
    shortlist: list[dict[str, Any]],
    output_path: str = "outputs/shortlist.json",
) -> None:
    """
    Save shortlisted candidate data to a JSON file.

    Args:
        shortlist: Shortlisted candidate list.
        output_path: Path where shortlist should be saved.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(shortlist, indent=2), encoding="utf-8")


def append_trace_to_state(
    state: dict[str, Any],
    agent_name: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Append a structured execution trace entry into the shared state.

    Args:
        state: Shared MAS state.
        agent_name: Name of the current agent.
        input_data: Input payload received by the agent.
        output_data: Output payload produced by the agent.

    Returns:
        Updated shared state.
    """
    if "execution_trace" not in state:
        state["execution_trace"] = []

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent_name,
        "input": input_data,
        "output": output_data,
    }

    state["execution_trace"].append(event)
    return state


def log_agent_trace_to_file(
    agent_name: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    log_path: str = "outputs/trace_log.jsonl",
) -> None:
    """
    Write a structured execution trace entry to a JSONL file.

    Args:
        agent_name: Name of the current agent.
        input_data: Input payload received by the agent.
        output_data: Output payload produced by the agent.
        log_path: Output path for the JSONL log file.
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent_name,
        "input": input_data,
        "output": output_data,
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")

def save_ranking_summary(
    ranking_summary: dict[str, Any],
    output_path: str = "outputs/ranking_summary.json",
) -> None:
    """
    Save ranking summary data to a JSON file.

    Args:
        ranking_summary: Ranking summary dictionary.
        output_path: Path where ranking summary should be saved.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ranking_summary, indent=2), encoding="utf-8")        