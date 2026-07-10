# Round 0: Macro Structure

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Skill path: `iter-refine-writing`, Round 0 macro structure. A read-only forked reviewer checked the paper against `check-paper-structure-flow` Level 1 and `common-pitfalls.md`.

## Findings

The reviewer found that the Chinese paper has the right top-level shape: introduction, background/motivation, threat model, design, formal model, implementation, evaluation, limitations, related work, and conclusion. The main remaining macro risk is that parts of the body still read like an evidence ledger rather than a top-conference systems paper.

Must-fix findings:

- Evaluation reads like a run ledger rather than three or four core experiments. The reviewer asked to keep E1, E2, and E3 as the main experiments, and move internal run IDs to the artifact/evaluation ledger.
- The formal model is too long relative to the implementation section. This remains for a later round.
- Implementation is too short for a system contribution. This remains for a later round.
- There are too many tables. This remains for a later round.
- Background/motivation includes evaluation-like numbers too early.

Should-fix findings:

- Intro has some defensive boundary statements too early.
- Design and formal model overlap in places.
- The four-context story would benefit from a conceptual figure.
- Evaluation should start with a one-screen takeaway.
- Limitations should read more like discussion plus limitations.

## Changes Made

Applied in this round:

- Renamed `Pre-Design Characterization` to `Problem Characterization`.
- Rewrote the characterization into three design observations: multiple issuer classes, runtime/env proof necessity, and class-substitution attempts. Detailed label protocol is now pointed to E2 rather than fully narrated in motivation.
- Rewrote the evaluation opening into three reviewer-facing questions with primary results for E1, E2, and E3.
- Removed internal run IDs from the main paper text and replaced them with stable experiment names such as `tested-removal matrix`, `integrated workflow`, `semantic candidate names`, and `candidate-only prompts`.
- Condensed the E1 recovery diagnostic from a run-by-run account into a condition-by-condition summary.

Not applied yet:

- Formal-model shortening.
- Implementation expansion.
- Table reduction or appendix migration.
- Conceptual figure for raw artifacts to four proof projections to protected-decision commit.
- Limitations restructuring.

## Remaining Concerns

The most important next macro fixes are implementation expansion and formal-section compression. The paper now has less run-ledger language in the evaluation section, but the table count and the evidence-boundary table remain heavy for a main paper.
