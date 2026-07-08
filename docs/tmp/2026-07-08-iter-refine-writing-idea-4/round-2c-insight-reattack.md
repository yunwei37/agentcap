# Round 2c: Insight Re-Attack

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Volta`, read-only. The reviewer was asked to test whether a strong novelty rejection remained easy after Round 2b.

## Findings

The reviewer concluded that a strong novelty rejection is no longer easy to construct. The paper now frames the abstraction as an atomic protected-decision transition with issuer ownership, proof, budget/expiry/delegation update, rather than as capability plus provenance plus counters.

Remaining must-fix points:

- The abstraction is now clearer than the evidence. E3 needed to be written as a necessity experiment over full IntentCap, no-issuer-owner, and split-state variants, rather than as a residual run list.
- The formal section needed a sharper boundary: the claim is not that a sufficiently expressive DSL cannot encode the rules, but that an equivalent implementation must expose issuer-owned field projections and lifecycle updates as one atomic authorization object.

Should-fix points:

- Keep the system contribution centered on multi-boundary transition API and adapter contract, not ActPlane integration.
- Add a minimal Skill/MCP per-run-manifest counterexample focused on field ownership.
- The related-work table remains potentially compressed, but its caption already bounds the comparison as default transition state rather than impossibility.

## Decision

Because novelty rejection is no longer easy but two must-fix clarification items remained, I made a focused Round 2d defense edit and will re-run re-attack before moving to Round 3.
