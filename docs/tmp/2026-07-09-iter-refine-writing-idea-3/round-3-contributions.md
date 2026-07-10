# Round 3 - Contributions and Design Goals

Date: 2026-07-10

## What Was Checked

Target: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Focus: whether the contribution list and design goals are claim-facing, independently testable, and aligned with the motivation and evaluation.

Reviewer: subagent `Feynman`.

## Findings

Must-fix findings:

1. The contribution list still had artifact-first wording. C4 especially read like an experiment list rather than an evidence claim.

2. G1 and G2 both mapped to E2 and could be read as the same issuer-collapse goal. G1 should be authority-root/minting; G2 should be decision-specific influence over protected fields.

3. The system contribution is still bounded to local adapter feasibility. This is honest but not yet a strong integrated system result.

4. Owner-class evidence remains author-adjudicated. Independent/blinded field-owner adjudication remains the main evidence gap.

Should-fix findings:

1. The abstract foregrounded the 38-event local suite too strongly.

2. Audit id should remain implementation support for auditability, not part of a proven necessary semantic core.

3. Evaluation text should be organized around three claim-facing blocks: expressiveness guardrail, mechanism necessity, and system boundary enforcement.

## What Was Changed

The main paper was revised to:

- Make the contribution list claim-facing: model, runtime contract, system substrate, and evaluation evidence.
- Clarify that G1 is about authority roots and lease mint/bounds, while G2 is about decision-specific influence and protected-field ownership.
- Rephrase the abstract result so the main numerical emphasis is E1 coverage and E2 false-accept ablation; the E3 result is described as local multi-boundary feasibility with 0 unsafe executions/placements.
- Keep audit id as auditability/debugging support rather than a proven necessary semantic field.
- Introduce the evaluation as three claim-facing blocks before discussing baselines and oracles.

## Remaining Concerns

Two reviewer-level gaps require new experiments rather than wording changes:

1. Independent/blinded field-owner and unsafe-substitution adjudication.

2. A more integrated workflow that exercises prompt/context builder, Skill/manual placement, local env gateway, tool/MCP-like gateway, and delegation monitor in one end-to-end run.
