# Round 2a - Insight and Novelty Attack

Date: 2026-07-09

## What Was Checked

Adversarial novelty review of `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`, focusing on whether the paper's core idea can be rejected as a renamed stateful policy DSL, IFC/provenance system, object-capability system, or reference monitor.

## Findings

The strongest rejection argument was:

> The paper can look like a composition of existing provenance / IFC / object capability / stateful reference monitor / policy DSL ideas, renamed as `agent/instruction/tool/env` and `commit record`.

The reviewer attack emphasized four must-fix risks.

1. Novelty should not be "we have a commit record." The stronger framing is that agent protected decisions require a runtime interface that current agent extension runtimes do not expose by default: field-owner projections, checker-owned lease state, same-transition lifecycle update, and effect-bound audit commit id.

2. The four context classes risk looking like an author-chosen taxonomy. The paper needs to derive them from workload boundaries and protected fields: Skills/manuals, MCP/cmd interfaces, runtime observations, and delegation.

3. E3 could look like a strawman if it only compares against variants with the central mechanism removed. The paper needs a strongest baseline: typed provenance plus stateful policy predicates, and then state where that baseline converges to IntentCap-equivalent behavior.

4. "0 unsafe accepts" can look tautological when the labels and checker are both project-controlled. E1/E4 should be framed as implementation consistency and boundary-safety sanity checks, while E3 carries the mechanism-necessity claim.

## Remaining Concerns

The next defense pass must make the equivalence boundary explicit: if a DSL, SkillGuard-style runtime, or ActPlane-backed policy system exposes the same atomic issuer-owned commit object, it is not a defeated baseline but an implementation of the same interface on those fields.
