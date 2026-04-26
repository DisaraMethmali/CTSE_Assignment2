from __future__ import annotations

import pytest

from pathlib import Path


from tools.report_logger_tool import (
    append_trace_to_state,
    build_ranking_summary,
    generate_shortlist,
    log_agent_trace_to_file,
    rank_candidates,
    save_ranked_candidates,
    save_report,
    save_shortlist,
)


def test_rank_candidates_descending_and_adds_rank() -> None:
    candidates = [
        {"name": "A", "score": 65},
        {"name": "B", "score": 92},
        {"name": "C", "score": 80},
    ]

    ranked = rank_candidates(candidates)

    assert ranked[0]["name"] == "B"
    assert ranked[1]["name"] == "C"
    assert ranked[2]["name"] == "A"
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2
    assert ranked[2]["rank"] == 3


def test_generate_shortlist_top_two() -> None:
    candidates = [
        {"name": "B", "score": 92, "rank": 1},
        {"name": "C", "score": 80, "rank": 2},
        {"name": "A", "score": 65, "rank": 3},
    ]

    shortlist = generate_shortlist(candidates, top_n=2)

    assert len(shortlist) == 2
    assert shortlist[0]["name"] == "B"
    assert shortlist[1]["name"] == "C"


def test_build_ranking_summary() -> None:
    ranked_candidates = [
        {"name": "B", "score": 92, "risk_level": "Low"},
        {"name": "C", "score": 80, "risk_level": "Medium"},
        {"name": "A", "score": 65, "risk_level": "Medium"},
    ]
    shortlist = ranked_candidates[:2]

    summary = build_ranking_summary(ranked_candidates, shortlist)

    assert summary["total_candidates"] == 3
    assert summary["shortlisted_count"] == 2
    assert summary["highest_score"] == 92
    assert summary["lowest_score"] == 65
    assert summary["risk_distribution"]["Medium"] == 2


def test_save_report_creates_file(tmp_path: Path) -> None:
    report_path = tmp_path / "final_report.txt"
    save_report("Test report", output_path=str(report_path))

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == "Test report"


def test_save_ranked_candidates_creates_file(tmp_path: Path) -> None:
    file_path = tmp_path / "ranked_candidates.json"
    save_ranked_candidates([{"name": "A", "score": 90}], output_path=str(file_path))

    assert file_path.exists()
    assert '"name": "A"' in file_path.read_text(encoding="utf-8")


def test_save_shortlist_creates_file(tmp_path: Path) -> None:
    file_path = tmp_path / "shortlist.json"
    save_shortlist([{"name": "A", "score": 90}], output_path=str(file_path))

    assert file_path.exists()
    assert '"name": "A"' in file_path.read_text(encoding="utf-8")


def test_append_trace_to_state() -> None:
    state = {"execution_trace": []}

    updated_state = append_trace_to_state(
        state=state,
        agent_name="Member4_Ranking_Report_Agent",
        input_data={"x": 1},
        output_data={"y": 2},
    )

    assert len(updated_state["execution_trace"]) == 1
    assert updated_state["execution_trace"][0]["agent"] == "Member4_Ranking_Report_Agent"


def test_log_agent_trace_to_file(tmp_path: Path) -> None:
    log_path = tmp_path / "trace_log.jsonl"

    log_agent_trace_to_file(
        agent_name="Member4_Ranking_Report_Agent",
        input_data={"x": 1},
        output_data={"y": 2},
        log_path=str(log_path),
    )

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "Member4_Ranking_Report_Agent" in lines[0]



def test_rank_candidates_raises_for_missing_score() -> None:
    candidates = [{"name": "A"}]
    with pytest.raises(KeyError):
        rank_candidates(candidates)


def test_generate_shortlist_raises_for_invalid_top_n() -> None:
    candidates = [{"name": "A", "score": 90, "rank": 1}]
    with pytest.raises(ValueError):
        generate_shortlist(candidates, top_n=0)    