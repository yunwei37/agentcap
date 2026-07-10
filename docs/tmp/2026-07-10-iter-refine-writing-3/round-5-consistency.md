# Round 5: Consistency and Claim Calibration

Date: 2026-07-10

## What Was Checked

This round checked `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` for consistency between the four proof-owner classes and the paper's abstract, introduction, design, formal model, implementation, evaluation, related work, and conclusion.

The target consistency question was whether `intent/agent-runtime`, `instruction`, `tool/interface`, and `runtime-observation/env` are consistently treated as proof owners rather than raw component categories, and whether the paper overclaims production MCP, production ActPlane/eBPF, benchmark-scale utility, approval burden, or independent expert-oracle evidence.

## Findings

The read-only reviewer found that the four proof-owner model is coherent across the paper. The paper repeatedly states that the classes are canonicalized proof cells, not Skill/tool/document/component taxonomy. The main risks were local wording issues:

- The abstract's local multi-boundary result could be read as independently proving all owner substitution, context promotion, and lifecycle violations, while E2 supplies the owner/lifecycle ablation evidence and E3 supplies local adapter feasibility.
- `agent` is used as shorthand for `intent/agent-runtime` in formal notation and tables, which could be misread as the LLM agent self-authorizing.
- The env-projection lowering wording sounded too close to production ActPlane/eBPF lowering.
- The implementation section used some evaluation/conclusion language that made the artifact boundary louder than necessary.
- The replay gateway and workload provenance wording could imply independent expert labels or freshly synchronized public traces.

## Changes Made

- Abstract result sentence:
  - Before: local multi-boundary results were phrased as directly blocking owner substitution, context promotion, and lifecycle violations.
  - After: the abstract says the same pre-effect interface is placed before side effect, placement, handoff, and MCP-style local broker execution; combined with owner/lifecycle ablations, it blocks tested violations on instrumented boundaries.

- Contribution C3:
  - Before: `Bounded evaluation evidence`.
  - After: `Evaluation evidence for the interface`, with stronger benchmark-scale utility, approval burden, independent oracle, and production backend evidence moved into the evidence-boundary clause.

- Runtime lowering table and formal notation:
  - Replaced table prefixes such as `agent:` with `intent/runtime:`.
  - Renamed `A_d: agent fields` to `A_d: intent/agent-runtime fields`.
  - Added a formal clarification that `agent` owner means issuer-canonicalized intent/agent-runtime proof cells, not the LLM agent, compiler, or parent subagent self-signing authority.

- Implementation and evaluation provenance:
  - Replaced broad env/OS lowering wording with monitor-shaped policy over the modeled env/local-effect projection, explicitly scoped to Python replay runtime rather than production ActPlane/eBPF integration.
  - Replaced implementation-section conclusion prose with a runtime-path statement for E1--E3.
  - Changed TraceGateway wording to `author-adjudicated lease-audit distance`.
  - Changed workload provenance to `public benchmark-derived saved artifacts` rather than implying fresh public trace synchronization.

## Remaining Concerns

No Must-fix consistency issue remains from this round. The next writing pass should still split a long related-work paragraph around the "equivalent systems converge to the IntentCap interface" point and continue sentence-level polish without changing experimental numbers.
