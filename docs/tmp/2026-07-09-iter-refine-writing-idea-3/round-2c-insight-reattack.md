# Round 2c - Insight and Novelty Re-Attack

Date: 2026-07-10

## What Was Checked

Target: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Focus: whether the Round 2b defense still allows a reviewer to reject the work as ordinary ABAC, policy DSL, reference monitor state, Skill/MCP permissions, or ActPlane policy synthesis.

Reviewer: subagent `Tesla`.

## Findings

Round 2c found that the direct "this is just ABAC / ActPlane" rejection is now much weaker because the paper centers the runtime authorization object and states equivalence conditions for DSLs/reference monitors.

Remaining must-fix issues:

1. The paper still risked overclaiming "minimal authorization object." Current evidence showed false accepts for tested owner/lifecycle collapses, but not global minimality across all possible commit fields.

2. Pre-design characterization still looked author-derived rather than independently adjudicated. The paper already scoped it away from natural prevalence, but reviewers could still treat it as internal consistency evidence unless independent/blinded adjudication is added.

3. The "just reference monitor state" attack had residual force. The paper needed to emphasize that the contribution is the runtime object decomposition and linearization point for agent protected decisions across prompt placement, tool/cmd execution, and delegation.

Should-fix issues:

1. Abstract and contribution wording could still imply production OS/ActPlane integration. It should say deterministic replay lowering, not kernel/ActPlane mediation.

2. E3's 38-event local-boundary result should be framed as local adapter contract feasibility, not complete multi-boundary enforcement.

3. Four context classes should consistently be described as proof-boundary quotients induced by issuer, forgeability, observation point, and lifecycle authority.

Consider items:

1. Keep recovery as a diagnostic, not a novelty pillar.

2. Related-work table should avoid a self-defined "missing object" tone.

3. Conclusion should state that the paper does not invent capability, taint, lease, or monitor primitives; it defines the runtime linearization object for agent authority-changing decisions.

## Remaining Concerns

The strongest remaining top-conference gap is evidence, not the basic novelty framing: independent/blinded field-owner adjudication and broader benchmark-derived protected-decision prevalence are still needed for stronger workload-driven claims.
