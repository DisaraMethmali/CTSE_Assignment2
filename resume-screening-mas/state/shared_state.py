from __future__ import annotations

from typing import Any, TypedDict

import json
import logging
from pathlib import Path


class MASState(TypedDict):
    """
    Shared global state passed between all agents in the multi-agent system.
    """

    job_description: str
    job_requirements: dict[str, Any]
    candidates: list[dict[str, Any]]
    parsed_candidates: list[dict[str, Any]]
    fit_analyses: list[dict[str, Any]]
    scored_candidates: list[dict[str, Any]]
    scoring_results: list[dict[str, Any]]
    ranked_candidates: list[dict[str, Any]]
    shortlisted_candidates: list[dict[str, Any]]
    ranking_summary: dict[str, Any]
    final_report: str
    report_metadata: dict[str, Any]
    execution_trace: list[dict[str, Any]]

STATE_FILE = Path("state/shared_state.json")
LOG_FILE   = Path("logs/agent_trace.log")

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("SharedState")


def load_state() -> dict:
    """Load the current shared state from disk."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    """Persist the updated shared state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    logger.info("State saved. Keys: %s", list(state.keys()))


def log_agent_event(
    agent_name: str,
    tool_called: str,
    input_summary: str,
    output_summary: str,
) -> None:
    """
    Record a structured agent execution event to the trace log.

    Args:
        agent_name:     Name of the agent.
        tool_called:    Name of the tool invoked.
        input_summary:  What was sent in.
        output_summary: What came out.
    """
    logger.info(
        "AGENT=%s | TOOL=%s | INPUT=%s | OUTPUT=%s",
        agent_name, tool_called, input_summary, output_summary
    )
