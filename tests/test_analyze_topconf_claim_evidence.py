import scripts.analyze_topconf_claim_evidence as analyzer


def test_topconf_claim_evidence_counts_same_exposure_unsafe_events():
    checker_summary = {
        "events": 6,
        "checker_denied": 3,
        "checker_denied_by_mode": {
            "authorize": 1,
            "sink_select": 1,
            "tool_select": 1,
        },
        "object_only_false_accept": 3,
        "object_only_false_accept_by_mode": {
            "authorize": 1,
            "sink_select": 1,
            "tool_select": 1,
        },
        "lease_constraints_no_provenance_false_accept": 2,
        "lease_constraints_no_provenance_false_accept_by_mode": {
            "authorize": 1,
            "sink_select": 1,
        },
        "full_event_args_no_provenance_false_accept": 3,
        "full_event_args_no_provenance_false_accept_by_mode": {
            "authorize": 1,
            "sink_select": 1,
            "tool_select": 1,
        },
    }
    distance_rows = [
        {
            "benchmark": "MCPTox",
            "baseline": "intentcap_provenance",
            "oracle_baseline": "intentcap_provenance",
            "is_oracle": "True",
            "unsafe_events_total": "10",
            "unsafe_events_admitted": "0",
            "unsafe_admit_rate": "0",
            "extra_authority_slots_vs_oracle": "0",
            "oracle_distance_score": "0",
            "distance_over_oracle_slots": "0",
            "description": "oracle",
        },
        {
            "benchmark": "MCPTox",
            "baseline": "exact_tool_acl",
            "oracle_baseline": "intentcap_provenance",
            "is_oracle": "False",
            "unsafe_events_total": "10",
            "unsafe_events_admitted": "10",
            "unsafe_admit_rate": "1.0",
            "extra_authority_slots_vs_oracle": "0",
            "oracle_distance_score": "10000",
            "distance_over_oracle_slots": "1000",
            "description": "same object, no provenance",
        },
        {
            "benchmark": "MCPTox",
            "baseline": "server_allowlist",
            "oracle_baseline": "intentcap_provenance",
            "is_oracle": "False",
            "unsafe_events_total": "10",
            "unsafe_events_admitted": "5",
            "unsafe_admit_rate": "0.5",
            "extra_authority_slots_vs_oracle": "90",
            "oracle_distance_score": "5090",
            "distance_over_oracle_slots": "509",
            "description": "server",
        },
        {
            "benchmark": "tau2-bench / tau3-bench",
            "baseline": "global_tools",
            "oracle_baseline": "intentcap_reference_events",
            "is_oracle": "False",
            "unsafe_events_total": "0",
            "unsafe_events_admitted": "0",
            "unsafe_admit_rate": "0",
            "extra_authority_slots_vs_oracle": "100",
            "oracle_distance_score": "100",
            "distance_over_oracle_slots": "10",
            "description": "utility over-exposure",
        },
    ]

    result = analyzer.analyze(
        run_id="test",
        checker_summary=checker_summary,
        distance_rows=distance_rows,
        input_paths=(),
    )

    summary = result["summary"]
    assert summary["object_only_false_accepts"] == 3
    assert summary["same_exposure_unsafe_event_admissions"] == 10
    assert summary["non_oracle_unsafe_event_admissions"] == 15
    assert summary["unique_unsafe_events_total"] == 10
    assert summary["max_extra_authority_slots_vs_oracle"] == 100

    object_only = next(
        row for row in result["security_rows"]
        if row["evidence_id"] == "checker_ablation.object_only"
    )
    assert object_only["authorize_violations"] == 1
    assert object_only["sink_select_violations"] == 1
    assert object_only["tool_select_violations"] == 1

    same_exposure_rows = [
        row for row in result["security_rows"]
        if row["comparison"] == "same exposed object count, missing provenance/argument authority"
    ]
    assert len(same_exposure_rows) == 1
    assert same_exposure_rows[0]["baseline"] == "exact_tool_acl"
    assert same_exposure_rows[0]["unsafe_or_false_accepts"] == 10

    tc1 = next(row for row in result["claim_rows"] if row["claim_id"] == "TC1")
    assert "same-exposure non-oracle baseline profiles produce 10 unsafe event admissions" in tc1["primary_evidence"]

    tc2 = next(row for row in result["claim_rows"] if row["claim_id"] == "TC2")
    assert "15 unsafe event admissions over 10 unique unsafe events" in tc2["primary_evidence"]

    tc4 = next(row for row in result["claim_rows"] if row["claim_id"] == "TC4")
    assert tc4["support_level"] == "weak/partial"


def test_topconf_ranking_prioritizes_unsafe_then_extra_authority():
    rows = [
        {
            "benchmark": "A",
            "baseline": "low_extra",
            "oracle_baseline": "oracle",
            "is_oracle": "False",
            "unsafe_events_total": "10",
            "unsafe_events_admitted": "1",
            "unsafe_admit_rate": "0.1",
            "extra_authority_slots_vs_oracle": "1000",
            "oracle_distance_score": "2000",
            "distance_over_oracle_slots": "20",
            "description": "",
        },
        {
            "benchmark": "A",
            "baseline": "high_unsafe",
            "oracle_baseline": "oracle",
            "is_oracle": "False",
            "unsafe_events_total": "10",
            "unsafe_events_admitted": "2",
            "unsafe_admit_rate": "0.2",
            "extra_authority_slots_vs_oracle": "0",
            "oracle_distance_score": "1000",
            "distance_over_oracle_slots": "10",
            "description": "",
        },
    ]

    ranking = analyzer._ranking_rows(rows)

    assert [row["baseline"] for row in ranking] == ["high_unsafe", "low_extra"]
