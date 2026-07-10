import scripts.analyze_tau2_runtime_evidence_filter_policies as analyzer


def candidate(
    *,
    step: str,
    rank_position: int,
    correctness: str,
    score: int = 50,
    margin: int = 0,
    fallback: bool = False,
    proof_probe: bool = False,
    tool: str = "tool",
) -> dict[str, str]:
    return {
        "source_run_id": "RTEST",
        "domain": "retail",
        "task_id": "1",
        "step": step,
        "rank_position": str(rank_position),
        "tool": tool,
        "args_json": '{"id": "x"}',
        "rank_score": str(score),
        "rank_margin_to_next": str(margin),
        "candidate_correctness": correctness,
        "selected_by_ranked_fallback": str(fallback),
        "proof_status": "proof_probe_complete" if proof_probe else "proof_complete",
        "proof_probe": str(proof_probe),
    }


def metrics_by_policy(rows):
    result = analyzer.evaluate_policies(rows)
    return {row["policy"]: row for row in result["policy_metrics"]}


def test_oracle_exact_next_upper_bound_abstains_when_missing():
    rows = [
        candidate(step="1", rank_position=1, correctness="same_tool_wrong_args"),
        candidate(step="1", rank_position=2, correctness="exact_next_reference"),
        candidate(step="2", rank_position=1, correctness="exact_future_reference"),
    ]

    metrics = metrics_by_policy(rows)["oracle_exact_next_if_available"]

    assert metrics["selected_steps"] == 1
    assert metrics["selected_exact_next"] == 1
    assert metrics["exact_next_precision"] == 1.0
    assert metrics["steps_without_exact_next_candidate"] == 1


def test_r125_ranked_fallback_replay_selects_only_recorded_fallbacks():
    rows = [
        candidate(step="1", rank_position=1, correctness="exact_next_reference"),
        candidate(
            step="2",
            rank_position=1,
            correctness="non_reference_tool",
            fallback=True,
        ),
    ]

    metrics = metrics_by_policy(rows)["r125_ranked_fallback_replay"]

    assert metrics["selected_steps"] == 1
    assert metrics["selected_non_reference_tool"] == 1
    assert metrics["exact_next_precision"] == 0.0


def test_rank_margin_filter_suppresses_ties_but_not_positive_margin_wrong_candidate():
    rows = [
        candidate(step="1", rank_position=1, correctness="same_tool_wrong_args", margin=0),
        candidate(step="1", rank_position=2, correctness="exact_next_reference", margin=0),
        candidate(step="2", rank_position=1, correctness="non_reference_tool", margin=10),
        candidate(step="2", rank_position=2, correctness="exact_future_reference", margin=0),
    ]

    metrics = metrics_by_policy(rows)

    assert metrics["rank_score_ge_50_margin_ge_1"]["selected_steps"] == 1
    assert metrics["rank_score_ge_50_margin_ge_1"]["selected_non_reference_tool"] == 1
    assert metrics["rank_score_ge_50_margin_ge_11"]["selected_steps"] == 0


def test_no_proof_probe_filter_suppresses_probe_candidates():
    rows = [
        candidate(
            step="1",
            rank_position=1,
            correctness="exact_next_reference",
            score=12,
            proof_probe=True,
        ),
        candidate(
            step="2",
            rank_position=1,
            correctness="exact_future_reference",
            score=52,
            proof_probe=False,
        ),
    ]

    metrics = metrics_by_policy(rows)

    assert metrics["rank_score_ge_50_no_proof_probe"]["selected_steps"] == 1
    assert metrics["rank_score_ge_50_no_proof_probe"]["selected_exact_future"] == 1
