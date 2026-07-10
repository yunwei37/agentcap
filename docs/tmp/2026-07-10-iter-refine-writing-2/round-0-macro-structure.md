# Round 0 — Macro Structure

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Skill path: `iter-refine-writing`, Round 0. The review subagent was instructed to use `check-paper-structure-flow` with Level 1 macro focus and to read `iter-refine-writing/references/common-pitfalls.md` first.

## What Was Checked

- Required systems-paper sections and ordering.
- Separation between design, formal model, implementation, evaluation, limitations, and related work.
- Whether the architecture figure and walkthrough appear early enough.
- Whether evaluation reads as three core experiments rather than a long experiment ledger.
- Whether limitations are centralized rather than repeated defensively across the paper.

## Reviewer Findings

Must-fix findings:

- The paper has all necessary sections, but the main body still reads like a long technical report rather than a 12--14 page systems paper.
- The formal model is too long and interrupts the path from design to implementation and evaluation.
- Evaluation is diluted by diagnostic and support material, especially because recovery appeared between E1 and E2 and E2 contains many artifact-level subresults.
- Design and implementation still share some adapter/API detail.
- Evidence boundaries are repeated in abstract, intro, evaluation, and limitations, creating defensive self-attacking prose.

Should-fix findings:

- Introduction contains strong thesis material but too much rebuttal-style positioning before contributions.
- Background has short glossary-like subsections.
- Design opening needs a clearer operation walkthrough after the architecture figure.
- Related work table is heavy and performs some positioning work late in the paper.
- Evaluation setup should expose explicit RQ1--RQ3 aligned with E1--E3.

Consider findings:

- Title language is mixed Chinese/English.
- There are many tables; a submission draft should move several evidence-ledger tables to appendix.
- Threat model can be strengthened after the formal section is shortened.
- Conclusion should end with positive system contribution rather than defensive "not X" phrasing.

## Changes Made

1. Evaluation macro order:
   - Before: `E1 -> Diagnostic: Recovery -> E2 -> E3 -> Support: Lease Auditability`.
   - After: `E1 -> E2 -> E3 -> Additional Diagnostics and Supporting Audits`.
   - Recovery is now under `Additional Diagnostics and Supporting Audits / Denial-Targeted Recovery`.
   - Lease auditability is now a supporting audit under the same non-claim subsection.

2. Evaluation setup:
   - Added explicit RQ1--RQ3 immediately after the evaluation spine.
   - RQ1 maps to event/lease expressiveness.
   - RQ2 maps to owner separation and atomic lifecycle necessity.
   - RQ3 maps to multi-boundary pre-effect commit enforceability.

3. Introduction tone:
   - Rephrased the stateful ABAC/provenance monitor comparison from a defensive "we do not claim" form into an interface-object comparison.
   - Rephrased the contribution boundary paragraph so the paper positively states the linearization-interface contribution, with stronger claims deferred to the evidence-boundary section.

4. Design walkthrough:
   - Added a post-architecture-figure PDF-to-issue walkthrough showing the path from intent certificate, context labeling, compiler proposal, adapter proof submission, checker consume, and denial feedback.

5. Background balance:
   - Merged the two short glossary-like subsections `Agent Extensions` and `Authority and Provenance` into `Agent Extension Substrates and Authority`.

6. Formal section positioning:
   - Renamed `形式化模型` to `模型与安全性质`.
   - Rephrased the invariant paragraph to avoid bold run-in pseudo-headers.

7. Conclusion:
   - Split the single long conclusion into two paragraphs.
   - Replaced the defensive "not capability/taint/lease/monitor itself" close with a positive statement that IntentCap defines the runtime linearization object for authority-changing agent decisions.

## Remaining Concerns

- The formal section is still long. Round 0 improved the framing but did not yet move safe-merge/equivalence detail into an appendix.
- E2 remains long and table-heavy. A later structure pass should compress it into one main result table plus representative examples.
- Related work still includes a heavy comparison table; a later pass should decide whether it belongs in a discussion/appendix.
- The paper still targets a long-form Chinese autopaper, not a compressed OSDI/SOSP page-limited draft.
