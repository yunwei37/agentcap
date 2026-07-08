# Round 3: Contributions and Goals

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Lorentz`, read-only. The reviewer focused on whether contributions are independent top-conference deliverables, whether design goals map to evidence, and whether claims overreach current results.

## Findings

Must-fix:

- C3 overclaimed by saying the current evidence showed mechanism necessity, while the E3 text itself says independent labels and more natural events are still missing.
- C2 read like an artifact inventory: transition API, prototype, live probes, and ActPlane lowering were all packed into one sentence.
- G4 over-suggested production MCP/ActPlane coverage instead of implemented/probed boundaries.

Should-fix:

- Goal-map obligations should be concrete metrics rather than vague reduction claims.
- E2 auditability should remain auxiliary evidence, not a main expert-oracle claim.
- C1 should read as a model deliverable: field owner, no-substitution, and atomic lifecycle.

## Changes

- Contribution list now has three bounded deliverables: model, system API/adapter contract, and evidence.
- C3 now says controlled false accepts under issuer-owner/lifecycle ablations rather than claiming completed mechanism necessity.
- C2 now centers on the checker-centered protected-transition API and adapter contract; live probes and ActPlane-style lowering are left to implementation/evaluation.
- G4 now covers implemented/probed boundaries and explicitly treats ActPlane as an env lowering target.
- Goal-map obligations now name metrics: dangerous accepts, no-owner ablation false accepts, split-state stale reuse/over-delegation false accepts, unsafe side effects/placements/handoffs, and checker-monitor mismatch.
- Evaluation matrix now calls E3 `Issuer/lifecycle ablation` rather than `Mechanism necessity`.

## Remaining Concerns

- The contribution structure is now scoped to current evidence, but the paper still needs stronger independent/natural evidence before claiming full necessity.
- Writing-refine will need to shorten the expanded prose; this idea round preserved technical claim boundaries rather than optimizing length.
