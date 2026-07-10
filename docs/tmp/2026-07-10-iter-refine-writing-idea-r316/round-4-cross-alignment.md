# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 4 cross-alignment across problem, insight, goals, contributions, formal model, implementation boundaries, and E1/E2/E3.

## What was checked

The reviewer checked whether the paper tells one coherent story after Round 3: the problem is authority-state transitions, the core abstraction is a field-owned protected-decision lease, the system contribution is a pre-effect commit interface with checker-owned lifecycle state, and E1/E2/E3 test the corresponding falsifiers.

## Findings

- Must-fix: the core-insight paragraph in the introduction still packed insight, novelty boundary, interface equivalence, tested-removal scope, and audit-binding limitation into one long paragraph.
- Must-fix: C1/C2/C3 were cleaner but C1 still mixed model, proof ownership, intent predicates, influence constraints, and lifecycle mutation. The goal map also used C1+C2 in ways that blurred model obligation versus runtime enforcement.
- Must-fix: the E2 three-class-collapse conclusion could still be read as a global impossibility claim against all three-class designs rather than a tested-removal claim against collapsed interfaces that do not preserve per-field owner projections.
- Should-fix: the abstract listed too many adapter artifacts as a main clause instead of emphasizing that the same commit interface is implemented across boundary classes.
- Should-fix: the implementation opening still mixed runtime path, experiment harness, contrast backend, and missing production deployments in one paragraph.
- Should-fix: the evaluation overview had the right E1/E2/E3 spine but could make each experiment's falsifier explicit.

## Changes made

- Abstract: rewrote the prototype sentence to say the same commit interface is implemented across five boundary classes, with local sandbox/replay lowering as a projection target and production MCP/ActPlane outside the current implementation.
- Introduction: split the dense core-insight paragraph into three paragraphs: core insight, authority-state commit object definition, and equivalence/tested-removal boundary.
- Contributions: narrowed C1 to the field-owned protected-decision lease abstraction, C2 to the pre-effect commit interface and checker-state discipline, and left C3 as the claim-driven evidence package.
- Goal map: changed G2/G3 rows from `C1+C2` to explicit "C1, enforced by C2" and "C2, specified by C1"; also updated the G2 falsifier so agent-owned context cannot act as a super-owner outside its fields.
- Formal model: rewrote the tested no-three-class-collapse corollary so it only excludes three-class collapsed interfaces that do not preserve per-field owner projections. Implementations that keep per-field projections and same-transition lifecycle update are described as implementing the IntentCap commit interface, not as collapsed baselines.
- Implementation: split the opening into a C2 checklist plus Runtime path / Experiment path / Contrast/backend path.
- Evaluation overview: added explicit falsifiers for E1, E2, and E3: security by refusing everything, owner/lifecycle as ordinary attributes, and tool-call-only applicability.

## Remaining concerns

- Later writing rounds should still shorten long authorization-input and related-work paragraphs.
- Safety properties P1/P2/P5 may still be tightened in a writing pass to reduce perceived overlap.
- ActPlane/OS positioning is correct but duplicated between E3 and related work; a later prose pass can reduce that repetition without changing the claim.
