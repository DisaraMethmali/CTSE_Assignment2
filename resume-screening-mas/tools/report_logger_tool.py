from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort candidates by score in descending order.

    Args:
        candidates: List of candidate dictionaries. Each candidate must contain
            a numeric 'score' field.

    Returns:
        A new list sorted from highest score to lowest score.

    Raises:
        TypeError: If candidates is not a list.
        KeyError: If any candidate does not contain the 'score' key.
        ValueError: If any score is not numeric.
    """
    if not isinstance(candidates, list):
        raise TypeError("candidates must be a list")

    for candidate in candidates:
        if "score" not in candidate:
            raise KeyError("Each candidate must contain a 'score' key")
        if not isinstance(candidate["score"], (int, float)):
            raise ValueError("Candidate 'score' must be numeric")

    return sorted(candidates, key=lambda x: x["score"], reverse=True)


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
        ValueError: If top_n is less than 1.
        TypeError: If candidates is not a list.
    """
    if not isinstance(candidates, list):
        raise TypeError("candidates must be a list")

    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    return candidates[:top_n]


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