from __future__ import annotations

from pathlib import Path

from tools.report_logger_tool import (
    append_trace_to_state,
    generate_shortlist,
    log_agent_trace_to_file,
    rank_candidates,
    save_report,
)


def test_rank_candidates_descending() -> None:
    candidates = [
        {"name": "A", "score": 65},
        {"name": "B", "score": 92},
        {"name": "C", "score": 80},
    ]

    ranked = rank_candidates(candidates)

    assert ranked[0]["name"] == "B"
    assert ranked[1]["name"] == "C"
    assert ranked[2]["name"] == "A"


def test_generate_shortlist_top_two() -> None:
    candidates = [
        {"name": "B", "score": 92},
        {"name": "C", "score": 80},
        {"name": "A", "score": 65},
    ]

    shortlist = generate_shortlist(candidates, top_n=2)

    assert len(shortlist) == 2
    assert shortlist[0]["name"] == "B"
    assert shortlist[1]["name"] == "C"


def test_save_report_creates_file(tmp_path: Path) -> None:
    report_path = tmp_path / "final_report.txt"
    save_report("Test report", output_path=str(report_path))

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == "Test report"


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