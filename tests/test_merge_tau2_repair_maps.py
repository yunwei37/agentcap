import csv
from pathlib import Path

import scripts.merge_tau2_repair_maps as merger


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_merge_repair_maps_unions_fields_and_deduplicates(tmp_path: Path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    base_fields = [
        "domain",
        "task_id",
        "event_id",
        "tool",
        "args_json",
        "candidate_json",
        "eligible",
        "proof_status",
        "earliest_synthesis_step",
    ]
    write_rows(
        first,
        base_fields,
        [
            {
                "domain": "retail",
                "task_id": "0",
                "event_id": "retail:0:0_2",
                "tool": "get_order_details",
                "args_json": '{"order_id": "#1"}',
                "candidate_json": '{"tool": "get_order_details", "arguments": {"order_id": "#1"}}',
                "eligible": "True",
                "proof_status": "repair_candidate_ready",
                "earliest_synthesis_step": "2",
            }
        ],
    )
    write_rows(
        second,
        [*base_fields, "planner_candidate_rank_score"],
        [
            {
                "domain": "retail",
                "task_id": "0",
                "event_id": "retail:0:0_2",
                "tool": "get_order_details",
                "args_json": '{"order_id": "#1"}',
                "candidate_json": '{"tool": "get_order_details", "arguments": {"order_id": "#1"}}',
                "eligible": "True",
                "proof_status": "repair_candidate_ready",
                "earliest_synthesis_step": "2",
                "planner_candidate_rank_score": "12",
            },
            {
                "domain": "airline",
                "task_id": "1",
                "event_id": "airline:1:1_1",
                "tool": "get_reservation_details",
                "args_json": '{"reservation_id": "ABC123"}',
                "candidate_json": (
                    '{"tool": "get_reservation_details", '
                    '"arguments": {"reservation_id": "ABC123"}}'
                ),
                "eligible": "True",
                "proof_status": "repair_candidate_ready",
                "earliest_synthesis_step": "1",
                "planner_candidate_rank_score": "20",
            },
        ],
    )

    result = merger.merge_repair_maps(
        run_id="RTEST",
        repair_maps=[first, second],
        output_dir=tmp_path / "out",
        output_csv=tmp_path / "out" / "merged.csv",
    )

    summary = result["summary"]
    assert summary["input_rows"] == 3
    assert summary["output_rows"] == 2
    assert summary["duplicate_rows_dropped"] == 1
    assert summary["eligible_repair_ready_rows"] == 2

    with (tmp_path / "out" / "merged.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert "planner_candidate_rank_score" in (reader.fieldnames or [])
        assert "merge_source_csv" in (reader.fieldnames or [])
    assert {row["event_id"] for row in rows} == {"retail:0:0_2", "airline:1:1_1"}
