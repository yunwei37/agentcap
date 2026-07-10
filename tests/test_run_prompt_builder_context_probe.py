import json
from pathlib import Path

import scripts.run_prompt_builder_context_probe as probe


def test_prompt_builder_context_probe_blocks_authority_promotions(tmp_path):
    repo = Path(__file__).parents[1]
    result = probe.run_probe(
        suite_path=repo / "examples" / "prompt_builder_context_suite.json",
        output_dir=tmp_path / "R292",
        run_id="TESTPROMPTBUILDER",
    )
    summary = result["summary"]

    assert summary["events"] == 10
    assert summary["owner_classes_exercised"] == ["agent", "env", "instruction", "tool"]
    assert summary["owner_class_count"] == 4
    assert summary["authority_section_count"] == 4
    assert summary["intentcap_placed"] == 6
    assert summary["intentcap_blocked"] == 4
    assert summary["intentcap_authority_section_placements"] == 3
    assert summary["intentcap_unsafe_authority_placements"] == 0
    assert summary["intentcap_blocked_unsafe_promotions"] == 4
    assert summary["paired_source_promotions"] == 4
    assert summary["paired_source_promotions_blocked"] == 4
    assert summary["object_only_placed"] == 10
    assert summary["object_only_unsafe_authority_placements"] == 4
    assert summary["object_only_paired_promotions_unsafe"] == 4
    assert summary["not_a_model_run"] is True
    assert summary["no_dataset_sync"] is True

    intentcap_prompt = json.loads((tmp_path / "R292" / "intentcap_prompt.json").read_text())
    object_prompt = json.loads((tmp_path / "R292" / "object_only_prompt.json").read_text())
    assert len(intentcap_prompt["prompt.data_section"]) == 3
    assert "prompt.delegation_section" not in intentcap_prompt
    assert len(object_prompt["prompt.delegation_section"]) == 1

    unsafe_event_ids = {
        "pdf_text_promotes_instruction_section",
        "tool_result_promotes_policy_section",
        "tool_schema_promotes_policy_section",
        "subagent_summary_promotes_delegation_section",
    }
    intentcap_event_ids = {
        cell["event_id"]
        for section in intentcap_prompt.values()
        for cell in section
    }
    object_only_event_ids = {
        cell["event_id"]
        for section in object_prompt.values()
        for cell in section
    }
    assert unsafe_event_ids.isdisjoint(intentcap_event_ids)
    assert unsafe_event_ids <= object_only_event_ids

    rows = (tmp_path / "R292" / "prompt_builder_context_rows.csv").read_text()
    assert "pdf_text_promotes_instruction_section" in rows
    assert "tool_schema_promotes_policy_section" in rows

    saved_summary = json.loads(
        (tmp_path / "R292" / "prompt_builder_context_summary.json").read_text()
    )
    assert saved_summary["run_id"] == "TESTPROMPTBUILDER"
