"""Rank web-discovered eval dataset candidates without syncing them.

R026 is a planning/evidence step, not a benchmark execution. It turns official
web metadata gathered during literature search into a deterministic candidate
matrix for deciding which benchmark to request permission for next. The script
does not fetch, clone, or download any dataset.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FIELDNAMES = [
    "rank",
    "name",
    "category",
    "primary_source",
    "local_status",
    "next_action",
    "priority_score",
    "intentcap_specificity",
    "context_influence",
    "authority_decision",
    "oracle_strength",
    "runtime_feasibility",
    "skills_mcp_relevance",
    "utility_relevance",
    "safety_protocol_cost",
    "sync_risk",
    "why_it_matters",
]


@dataclass(frozen=True)
class Candidate:
    name: str
    category: str
    primary_source: str
    local_status: str
    context_influence: int
    authority_decision: int
    oracle_strength: int
    runtime_feasibility: int
    skills_mcp_relevance: int
    utility_relevance: int
    safety_protocol_cost: int
    sync_risk: int
    why_it_matters: str

    @property
    def intentcap_specificity(self) -> int:
        return (
            self.context_influence
            + self.authority_decision
            + self.skills_mcp_relevance
        )

    @property
    def local_bonus(self) -> int:
        return 4 if self.local_status == "existing_local" else 0

    @property
    def priority_score(self) -> int:
        return (
            (3 * self.context_influence)
            + (3 * self.authority_decision)
            + (2 * self.oracle_strength)
            + (2 * self.runtime_feasibility)
            + (2 * self.skills_mcp_relevance)
            + (2 * self.utility_relevance)
            + self.local_bonus
            - (2 * self.safety_protocol_cost)
            - self.sync_risk
        )

    @property
    def next_action(self) -> str:
        if self.local_status == "existing_local":
            return "use_existing_artifact_only"
        if self.safety_protocol_cost >= 3:
            return "write_safety_protocol_before_any_download"
        if self.sync_risk >= 3:
            return "web_metadata_only_until_explicit_approval"
        return "candidate_for_explicit_download_approval"

    def to_row(self, rank: int) -> dict[str, Any]:
        return {
            "rank": rank,
            "name": self.name,
            "category": self.category,
            "primary_source": self.primary_source,
            "local_status": self.local_status,
            "next_action": self.next_action,
            "priority_score": self.priority_score,
            "intentcap_specificity": self.intentcap_specificity,
            "context_influence": self.context_influence,
            "authority_decision": self.authority_decision,
            "oracle_strength": self.oracle_strength,
            "runtime_feasibility": self.runtime_feasibility,
            "skills_mcp_relevance": self.skills_mcp_relevance,
            "utility_relevance": self.utility_relevance,
            "safety_protocol_cost": self.safety_protocol_cost,
            "sync_risk": self.sync_risk,
            "why_it_matters": self.why_it_matters,
        }


CANDIDATES = [
    Candidate(
        "AgentDojo",
        "agent-security",
        "https://agentdojo.spylab.ai/",
        "existing_local",
        3,
        3,
        3,
        3,
        0,
        3,
        1,
        0,
        "Primary prompt-injection benchmark with utility/security oracles.",
    ),
    Candidate(
        "MCPTox",
        "mcp-security",
        "https://arxiv.org/abs/2508.14925",
        "existing_local",
        3,
        3,
        2,
        2,
        3,
        1,
        1,
        0,
        "Tool-description poisoning directly tests MCP metadata influence.",
    ),
    Candidate(
        "InjecAgent",
        "agent-security",
        "https://github.com/uiuc-kang-lab/InjecAgent",
        "existing_local",
        3,
        3,
        2,
        2,
        0,
        1,
        1,
        0,
        "Broad indirect prompt-injection corpus over user and attacker tools.",
    ),
    Candidate(
        "tau2/tau3-bench",
        "utility-policy",
        "https://github.com/sierra-research/tau2-bench",
        "existing_local",
        1,
        2,
        3,
        3,
        0,
        3,
        0,
        0,
        "Best current local utility substrate for policy-following tool agents.",
    ),
    Candidate(
        "Skill-Inject",
        "skill-security",
        "https://www.skill-inject.com/",
        "web_metadata_only",
        3,
        3,
        2,
        2,
        3,
        1,
        1,
        2,
        "Skill-file prompt injection is directly aligned with IntentCap's Skill story.",
    ),
    Candidate(
        "HarmfulSkillBench",
        "skill-safety",
        "https://github.com/TrustAIRLab/HarmfulSkillBench",
        "web_metadata_only",
        2,
        3,
        2,
        2,
        3,
        1,
        3,
        2,
        "Harmful Skills benchmark stresses refusal and skill-mediated authority.",
    ),
    Candidate(
        "MCPSecBench",
        "mcp-security",
        "https://arxiv.org/html/2508.13220v3",
        "web_metadata_only",
        3,
        3,
        2,
        2,
        3,
        1,
        1,
        2,
        "Systematic MCP security playground covers clients, servers, and attacks.",
    ),
    Candidate(
        "MCP-Bench",
        "mcp-utility",
        "https://github.com/Accenture/mcp-bench",
        "web_metadata_only",
        1,
        2,
        2,
        2,
        3,
        3,
        0,
        2,
        "Benign MCP utility benchmark can measure tool-exposure minimization.",
    ),
    Candidate(
        "ToolSandbox",
        "tool-utility",
        "https://machinelearning.apple.com/research/toolsandbox-stateful-conversational-llm-benchmark",
        "web_metadata_only",
        1,
        2,
        3,
        3,
        0,
        3,
        0,
        2,
        "Stateful conversational tool use is useful for denial-recovery experiments.",
    ),
    Candidate(
        "WorkBench",
        "workplace-utility",
        "https://arxiv.org/html/2405.00823v1",
        "web_metadata_only",
        1,
        2,
        3,
        2,
        0,
        3,
        0,
        2,
        "Workplace tools include email and scheduling sinks with state changes.",
    ),
    Candidate(
        "TheAgentCompany",
        "workplace-utility",
        "https://the-agent-company.com/",
        "web_metadata_only",
        1,
        2,
        3,
        2,
        0,
        3,
        0,
        3,
        "Consequential simulated company tasks stress multi-app authority.",
    ),
    Candidate(
        "Agent Security Bench",
        "agent-security",
        "https://github.com/agiresearch/asb",
        "web_metadata_only",
        2,
        3,
        2,
        2,
        0,
        1,
        2,
        2,
        "Broad attack/defense suite covers prompt injection and memory poisoning.",
    ),
    Candidate(
        "Agent-SafetyBench",
        "agent-safety",
        "https://github.com/thu-coai/Agent-SafetyBench",
        "web_metadata_only",
        1,
        2,
        2,
        2,
        0,
        1,
        3,
        2,
        "Agent safety environments can supply deny-only stress tests.",
    ),
    Candidate(
        "AgentHarm",
        "agent-safety",
        "https://huggingface.co/datasets/ai-safety-institute/AgentHarm",
        "web_metadata_only",
        1,
        2,
        2,
        2,
        0,
        1,
        3,
        1,
        "Misuse tasks are relevant but require a safety protocol before use.",
    ),
    Candidate(
        "HarmActionsEval",
        "action-safety",
        "https://agent-leaderboard.github.io/",
        "web_metadata_only",
        1,
        3,
        2,
        1,
        0,
        1,
        3,
        2,
        "Action-level harmful-tool benchmark matches gateway deny semantics.",
    ),
    Candidate(
        "R-Judge",
        "risk-awareness",
        "https://rjudgebench.github.io/",
        "web_metadata_only",
        1,
        1,
        2,
        2,
        0,
        0,
        2,
        1,
        "Risk-awareness records may help classify denial explanations.",
    ),
    Candidate(
        "OASB Skills Security Benchmark",
        "skill-scanner",
        "https://oasb.ai/benchmark",
        "web_metadata_only",
        2,
        2,
        2,
        1,
        3,
        0,
        1,
        2,
        "Skill-scanner labels are useful for static-scan baselines, not runtime utility.",
    ),
    Candidate(
        "WebArena/WorkArena/BrowserGym",
        "web-utility",
        "https://webarena.dev/",
        "web_metadata_only",
        1,
        2,
        2,
        2,
        0,
        3,
        0,
        3,
        "Browser workflows stress sink selection, web context, and task utility.",
    ),
    Candidate(
        "Mind2Web/Online-Mind2Web",
        "web-utility",
        "https://osu-nlp-group.github.io/Mind2Web/",
        "web_metadata_only",
        1,
        1,
        2,
        2,
        0,
        2,
        0,
        3,
        "Large web-task corpus has real web context but weak authority labels.",
    ),
    Candidate(
        "WebVoyager",
        "web-utility",
        "https://github.com/MinorJerry/WebVoyager",
        "web_metadata_only",
        1,
        1,
        1,
        2,
        0,
        2,
        0,
        3,
        "Live multimodal web tasks are useful later but oracle cost is high.",
    ),
    Candidate(
        "OSWorld",
        "desktop-utility",
        "https://os-world.github.io/",
        "web_metadata_only",
        1,
        2,
        3,
        1,
        0,
        2,
        0,
        3,
        "Desktop/file workflows are relevant to local authority but setup is heavy.",
    ),
    Candidate(
        "SWE-bench",
        "coding-utility",
        "https://www.swebench.com/",
        "web_metadata_only",
        1,
        2,
        3,
        2,
        0,
        2,
        0,
        2,
        "Coding-agent tasks can test repo/shell authority after core security runs.",
    ),
    Candidate(
        "GAIA",
        "assistant-utility",
        "https://hal.cs.princeton.edu/gaia",
        "web_metadata_only",
        1,
        1,
        2,
        2,
        0,
        2,
        0,
        2,
        "General assistant tasks stress web/file provenance but not protected actions.",
    ),
    Candidate(
        "BrowseComp",
        "browsing-utility",
        "https://openai.com/index/browsecomp/",
        "web_metadata_only",
        1,
        1,
        2,
        2,
        0,
        2,
        0,
        2,
        "Browsing tasks can exercise context provenance but lack side-effect actions.",
    ),
    Candidate(
        "BFCL",
        "function-calling",
        "https://gorilla.cs.berkeley.edu/leaderboard.html",
        "web_metadata_only",
        0,
        1,
        3,
        2,
        0,
        2,
        0,
        2,
        "Function-call accuracy is a useful tool-schema baseline, not a security test.",
    ),
    Candidate(
        "API-Bank",
        "tool-utility",
        "https://aclanthology.org/2023.emnlp-main.187/",
        "web_metadata_only",
        1,
        1,
        2,
        2,
        0,
        2,
        0,
        2,
        "Runnable API dialogs can supply old but simple tool-use baselines.",
    ),
    Candidate(
        "AgentBench",
        "general-agent",
        "https://github.com/THUDM/AgentBench",
        "web_metadata_only",
        1,
        1,
        2,
        1,
        0,
        2,
        0,
        2,
        "Broad multi-environment agent benchmark, but less aligned with context authority.",
    ),
    Candidate(
        "ToolEmu",
        "risk-emulation",
        "https://github.com/ryoungj/toolemu",
        "web_metadata_only",
        2,
        2,
        1,
        2,
        0,
        1,
        2,
        2,
        "LM-emulated tool risks may help generate adversarial refinement tests.",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank eval dataset candidates")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = analyze(CANDIDATES)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "candidate_scores.csv", result["rows"])
    (args.output_dir / "candidate_scores.json").write_text(
        json.dumps(result["rows"], indent=2, sort_keys=True)
    )
    (args.output_dir / "summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(candidates: list[Candidate]) -> dict[str, Any]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            item.priority_score,
            item.intentcap_specificity,
            item.oracle_strength,
            item.name,
        ),
        reverse=True,
    )
    rows = [candidate.to_row(index + 1) for index, candidate in enumerate(ranked)]
    local = [row for row in rows if row["local_status"] == "existing_local"]
    web_only = [row for row in rows if row["local_status"] != "existing_local"]
    explicit_approval = [
        row
        for row in rows
        if row["next_action"] == "candidate_for_explicit_download_approval"
    ]
    safety_protocol = [
        row
        for row in rows
        if row["next_action"] == "write_safety_protocol_before_any_download"
    ]
    summary = {
        "run_id": "R026",
        "benchmark": "web-only eval dataset candidate ranking",
        "candidate_count": len(rows),
        "local_candidate_count": len(local),
        "web_only_candidate_count": len(web_only),
        "top_existing_local": [row["name"] for row in local[:5]],
        "top_web_only": [row["name"] for row in web_only[:8]],
        "top_explicit_approval_candidates": [
            row["name"] for row in explicit_approval[:8]
        ],
        "safety_protocol_required": [row["name"] for row in safety_protocol],
        "no_sync_policy": (
            "R026 uses official web metadata only; it does not clone, sync, "
            "download, or execute any new dataset."
        ),
        "scoring_formula": (
            "3*context_influence + 3*authority_decision + 2*oracle_strength "
            "+ 2*runtime_feasibility + 2*skills_mcp_relevance "
            "+ 2*utility_relevance + local_bonus - 2*safety_protocol_cost "
            "- sync_risk"
        ),
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "machine": platform.platform(),
        "notes": [
            "Scores are for selecting the next IntentCap evidence step, not benchmark results.",
            "A high web-only rank means read/source approval priority, not permission to download.",
            "Safety-protocol candidates include harmful or misuse tasks and need separate handling.",
        ],
    }
    return {"summary": summary, "rows": rows}


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_output(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
