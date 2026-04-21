from __future__ import annotations

from typing import Any, TypedDict


class MASState(TypedDict):
    """
    Shared global state passed between all agents in the multi-agent system.
    """

    job_description: str
    job_requirements: dict[str, Any]
    resume_files: list[str]
    parsed_candidates: list[dict[str, Any]]
    fit_results: list[dict[str, Any]]
    scoring_results: list[dict[str, Any]]
    ranked_candidates: list[dict[str, Any]]
    shortlisted_candidates: list[dict[str, Any]]
    ranking_summary: dict[str, Any]
    final_report: str
    report_metadata: dict[str, Any]
    execution_trace: list[dict[str, Any]]