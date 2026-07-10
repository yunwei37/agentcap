# Round 2e - Insight and Novelty Re-Attack

Date: 2026-07-10

## What Was Checked

Target: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Focus: whether the post-R270 framing can still be rejected as ordinary ABAC, reference-monitor state, proof-carrying capabilities, ActPlane policy synthesis, or Skill/MCP permission engineering.

Reviewer: subagent `Averroes`.

## Findings

Round 2e found that the direct novelty rejection is no longer strong. The paper now centers the runtime-visible authority-state commit object for agent authority-changing decisions, and the equivalence-boundary section makes clear that an ABAC, DSL, IFC runtime, or reference monitor that exposes the same owner projections, checker-owned lease state, and same-transition lifecycle update is implementing the same IntentCap interface.

Remaining must-fix issues:

1. The core characterization and field-owner labels are still author-derived or author-adjudicated. A reviewer may accept the abstraction while still asking for independent/blinded field-owner and unsafe-substitution adjudication.

2. The paper listed audit binding as one of the core interface objects while R270 explicitly recorded audit-id removal as a gap. The paper should either add an isolated audit-binding ablation or demote audit id to an auditability/implementation binding field.

3. E3 is currently local adapter feasibility over 38 checker-submitted events. It supports that the contract is executable, but not production integrated MCP/prompt/subagent/ActPlane enforcement.

Should-fix issues:

1. Make explicit that the formal model permits finer field owners. The four context classes are workload-derived safe-merge owner-equivalence classes, not a universal taxonomy.

2. Related work should read as an interface-difference audit: each row should state the published runtime object and why it does not, by default, linearize lease lifecycle.

3. Qwen/Qwen3.6 results are already scoped as diagnostics, but the paper should keep them supporting rather than competing with the E1/E3 main claims.

## What Was Changed

This log records the reviewer findings. The main paper edits are applied in the following defense step.

## Remaining Concerns

The strongest remaining evidence gap is independent field-owner/substitution adjudication and a more integrated end-to-end system workflow. The novelty framing itself is no longer the main blocker.
