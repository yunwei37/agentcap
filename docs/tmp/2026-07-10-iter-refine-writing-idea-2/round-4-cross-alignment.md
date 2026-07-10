# 2026-07-10 Iter-Refine-Writing-Idea Round 4

## What Was Checked

Round 4 checked cross-alignment across the problem framing, insight, design goals, contribution list, formal model, implementation, and evaluation in `docs/autopaper/intentcap-paper-zh.tex`.

## Findings

Reviewer `019f4b65-19f7-74c2-ba96-d47d874f591b` reported that the paper mostly tells one story, but several phrases still made the evidence look broader than it is.

Must-fix items:

- `tool/MCP gateway` wording in the abstract, evaluation overview, and integrated workflow could be read as production MCP broker integration.
- \(C_{agent}\) contained `plan stage` and `agent role` without saying these must be trusted/canonical fields, not LLM-generated plan text.
- \(C_{inst}\) included MCP prompts without saying default MCP prompts and tool descriptions are not trusted instruction-owner fields.
- The top-level context-to-decision wording was broader than the current owner-substitution and lifecycle evidence.
- The ActPlane observability caption described delegation as if it were a fifth proof owner.

Should-fix items:

- C3's title should cover E1/E2/E3 rather than only tested removals.
- Recovery evidence should be separated from the E1 main subsection and marked diagnostic.
- Implementation wording should distinguish local runtime surfaces from benchmark replay and local Qwen diagnostics.

## Changes Made

- Replaced production-sounding `tool/MCP gateway` claims with `local tool/MCP-style` or `local method gateway` wording in the abstract, design overview, architecture node, and integrated workflow text.
- Restricted \(C_{agent}\) to trusted/canonical plan stage and role issued by UI, policy, or checker state; LLM/compiler plan text remains an untrusted proposal.
- Restricted \(C_{inst}\) to trusted system/developer instructions, canonicalized workflow preferences, Skill/manual text, and separately endorsed MCP prompts; default MCP prompts/tool descriptions/server annotations remain tool metadata or env text.
- Narrowed the top-level safety wording from broad context-to-decision influence to owner substitution, context-class promotion, and lifecycle violations over instrumented protected-decision boundaries.
- Rewrote P2 as `No unauthorized owner/provenance influence`.
- Renamed C3 to bounded evidence for model and system claims, so E1 can be a guardrail under the evidence contribution.
- Moved the recovery microbenchmark into its own `Diagnostic: Recovery` subsection and added a diagnostic row to the evaluation summary table.
- Split the implementation claim so runtime surfaces support local side-effect/placement/handoff, while benchmark replay and Qwen runs are diagnostic evidence rather than production integration.
- Fixed the ActPlane observability caption to say delegation is checker-owned state, not a fifth issuer owner.

## Remaining Concerns

The paper is now better aligned around the limited current claim. Remaining evidence gaps are unchanged: independent field-owner adjudication, production-like MCP/prompt/subagent integration, real ActPlane/kernel mediation, and benchmark-scale utility/recovery.
