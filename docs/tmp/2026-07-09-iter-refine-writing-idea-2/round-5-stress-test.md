# Round 5 - Reviewer Stress Test

Date: 2026-07-09

## What Was Checked

Read-only reviewer stress test of `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` after Round 4 cross-alignment fixes.

## Findings

The reviewer found that a pure idea/framing reject is no longer easy. The paper no longer reads like an EIM/ActPlane/tool-permission variant. The remaining strongest reject was:

> The paper has converged to a linearizable reference monitor with typed capabilities, provenance labels, one-shot leases, and audit records. The four context classes are useful engineering projections, but the paper does not yet prove they are a new abstraction rather than a chosen factoring of issuer attributes. The strongest baseline is admitted to become equivalent once it exposes the same commit object, so the novelty reduces to naming an adapter API.

Idea-level must-fix items:

1. Sharpen the boundary with reference monitors: the contribution is not a checker, but identifying the agent-specific multi-issuer protected-decision transition as a required runtime-exposed authorization object.

2. Move owner-equivalence evidence earlier so the four classes do not look like an author taxonomy.

3. Align the `context influence` claim with what the system proves: adapter-supplied structured context proofs cannot fill protected fields or be accepted as control proof when they lack the required owner/mode. The paper does not prove internal LLM causality.

4. Present typed-provenance state guard as an equivalence-boundary baseline rather than a small numerical win.

Writing-level cleanup items remain for later writing rounds: table redundancy, related-work table tone, and E4 result prose.

## What Was Changed

1. The abstract now talks about structured proof paths and protected fields rather than implying that the system observes true internal LLM influence.

2. The abstract now frames saved replay as replay consistency and coverage, not as the main safety proof.

3. The intro now says the four authority-input classes are the coarsest safe owner-equivalence classes observed in the current adapter surface, and it moves the E3 characterization result earlier: 8,691/8,696 authority events require multiple issuer classes.

4. The policy-DSL/reference-monitor paragraph now states that reference monitors are possible implementations, not the problem definition or contribution.

5. The evaluation overview now states that typed-provenance state guard is an equivalence-boundary baseline: after adding parent-child lease comparison, checker sole-writer state, and same-transition child update, it implements the IntentCap commit interface on that residual class.

6. The E3 table row for typed-provenance state guard now says it is a convergence boundary rather than presenting the `1/7` result as a broad quantitative advantage.

## Remaining Concerns

Idea-layer refinement has reached the point where remaining concerns are primarily writing presentation and evidence scope. The next stage should run `iter-refine-writing` to reduce table redundancy, improve implementation/evaluation prose, and soften related-work matrices, while keeping the current conservative evidence boundaries.
