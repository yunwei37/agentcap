import importlib.util
import sys
from pathlib import Path


def _load_ranker():
    path = Path(__file__).parents[1] / "scripts" / "rank_eval_dataset_candidates.py"
    spec = importlib.util.spec_from_file_location("rank_eval_dataset_candidates", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ranking_keeps_existing_artifacts_and_web_only_candidates_separate():
    ranker = _load_ranker()
    result = ranker.analyze(ranker.CANDIDATES)
    summary = result["summary"]

    assert "AgentDojo" in summary["top_existing_local"]
    assert "MCPTox" in summary["top_existing_local"]
    assert "Skill-Inject" in summary["top_web_only"]
    assert "MCPSecBench" in summary["top_web_only"]
    assert summary["local_candidate_count"] == 4
    assert summary["web_only_candidate_count"] == len(ranker.CANDIDATES) - 4


def test_ranking_never_recommends_unsupervised_sync():
    ranker = _load_ranker()
    rows = ranker.analyze(ranker.CANDIDATES)["rows"]

    assert all(row["next_action"] != "sync_now" for row in rows)
    assert all("sync" not in row["next_action"] for row in rows if row["local_status"] != "existing_local")
    assert {
        "write_safety_protocol_before_any_download",
        "web_metadata_only_until_explicit_approval",
        "candidate_for_explicit_download_approval",
        "use_existing_artifact_only",
    } >= {row["next_action"] for row in rows}


def test_candidate_scores_are_explainable_and_stable():
    ranker = _load_ranker()
    rows = ranker.analyze(ranker.CANDIDATES)["rows"]
    by_name = {row["name"]: row for row in rows}

    assert by_name["AgentDojo"]["priority_score"] > by_name["BFCL"]["priority_score"]
    assert by_name["Skill-Inject"]["skills_mcp_relevance"] == 3
    assert by_name["AgentHarm"]["next_action"] == "write_safety_protocol_before_any_download"
    assert by_name["TheAgentCompany"]["next_action"] == "web_metadata_only_until_explicit_approval"
