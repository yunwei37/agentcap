# R303 Post-MCP-Broker Idea/Writing Review

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: subagent `019f4bcd-9ac0-7380-a829-b18c0a4b6771` (`Epicurus`), read-only.

## What Was Checked

- Whether the R301/R303 MCP-style JSON-RPC broker integration strengthens the system contribution without overclaiming production MCP deployment.
- Whether the paper still separates local broker evidence, prompt/subagent runtime evidence, bubblewrap namespace sandbox evidence, and ActPlane/eBPF integration limits.
- Which experiment should be prioritized next for an OSDI/NeurIPS-level claim.

## Findings

### Must-Fix

1. R301 artifact provenance was generated before the broker suite/script/test were committed, so its summary showed untracked source files and an old project head. The reviewer recommended a clean-head rerun.
2. `docs/evaluation.md` claim maps had not fully absorbed R298/R301 and still made the evidence look like appended run history.

### Should-Fix

1. The abstract and contribution list underclaimed the new local MCP-style JSON-RPC broker surface.
2. E3 read like an evidence ledger and should group surfaces by adapter blockpoint, broker/prompt/delegation surfaces, and env/OS lowering.
3. The E3 table caption did not mention the new MCP broker and bubblewrap rows.
4. The paper should emphasize the main R301/R303 insight: visible tool narrowing alone is insufficient because object-only also exposes only `github.create_issue` but still executes unsafe calls.

### Consider

- Current evidence table is too long for a final submission and should eventually be compressed, with run-level detail moved to appendix/ledger.
- The highest-value next experiment is an integrated online utility/recovery run using local Qwen3.6/llama.cpp over benchmark-derived multi-step tasks, with prompt builder, MCP broker, bwrap/env backend, and delegation monitor in one task loop.

## Changes Made

- Ran `R303MCPBROKERCLEAN` from clean committed source at head `979e94255544d1d41a3d09f32fdb3a2e8b05e540`; the result records clean git status `## main...origin/main`.
- Switched paper-facing MCP broker audit checks from `R301MCPBROKER` to `R303MCPBROKERCLEAN`.
- Updated `docs/evaluation.md` gate 4 and C4 claim map to include R298 local bubblewrap and R303 clean MCP broker evidence.
- Updated the abstract and contribution list in `docs/autopaper/intentcap-paper-zh.tex` to mention the local MCP-style JSON-RPC broker while preserving the non-production boundary.
- Split the E3 setup paragraph and revised the E3 boundary table caption.
- Added an explicit takeaway that object-only tool exposure is insufficient because it cannot enforce per-call provenance, sink owner, and one-shot budget state.
- Ran focused tests and paper audit:
  - `python3 -m pytest tests/test_run_mcp_broker_probe.py tests/test_audit_paper_evidence_numbers.py -q`
  - `python3 scripts/audit_paper_evidence_numbers.py --run-id R304PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R304PAPERAUDIT`

## Remaining Concerns

- R303 is still a local deterministic fake-server broker probe, not a deployed MCP server or network integration.
- Full pytest with `PYTHONPATH=src` still has two pre-existing missing-artifact failures unrelated to R303:
  - `results/eval/R222BOUNDARY/boundary_gateway_records.csv`
  - `results/mcptox/R007/intentcap_trace.json`
- The next high-value work should be a live integrated utility/recovery experiment rather than another isolated microprobe.
