# Round 5: Reviewer Stress Test

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Mencius`, read-only.

## Findings

The reviewer concluded that a strong novelty reject is no longer easy to construct. The core paper idea is now stable:

> The authorization unit is not a tool, action, flow, or context label, but an atomic protected-decision transition carrying issuer-owned field proof, provenance, budget/expiry/delegation state, and lifecycle update.

The three contributions are coherent:

- C1 is a clear model contribution.
- C2 is a checker-centered transition API and adapter contract, upstream of ActPlane/SkillGuard.
- C3 is bounded evidence and no longer overclaims complete mechanism necessity.

## Remaining Rejection Path

The strongest remaining rejection is evidence maturity, not idea novelty:

- Natural traces still need independent field-owner labels.
- Utility/recovery still needs real closed-loop workflows with task success, false denial, denial recovery, and approval prompts.
- System evidence still needs at least one or two more realistic adapters, such as prompt builder, MCP broker, subagent runtime, or production ActPlane/kernel integration.
- Baseline artifact risk remains because closest baselines are policy-family abstractions; a stronger sufficient-DSL baseline with and without issuer-owned projection / atomic lifecycle object would make the abstraction boundary harder to dismiss.

## Decision

The idea-refinement cycle can close. The next work should shift to evidence/build work and writing refinement rather than continuing to argue idea novelty.
