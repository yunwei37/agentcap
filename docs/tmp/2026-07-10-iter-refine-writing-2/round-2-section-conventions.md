# Round 2 — Section Conventions

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Skill path: `iter-refine-writing`, Round 2. The review subagent was instructed to use `check-paper-structure-flow` with section-convention focus for a full systems paper, after reading `iter-refine-writing/references/common-pitfalls.md`.

## What Was Checked

- Abstract length and 4-beat structure.
- Intro paragraph roles and causal order.
- Design goals and goal/evaluation mapping.
- Evaluation setup and RQ alignment.
- Related work grouping, generosity, and table placement.
- Conclusion structure and no-new-information rule.
- Centralization of limitations and scope boundaries.

## Reviewer Findings

Must-fix findings:

- Abstract was close to the 4-beat convention, but the mechanism beat still introduced too many implementation objects.
- Introduction had the right roles but overloaded the system overview paragraph with proof classes, API, runtime lowering, ActPlane boundary, and running example.
- G4 and the goal map mixed requirements with evidence-boundary language.
- Evaluation had RQs but still read partly like an evidence ledger.
- Related Work opened with the interface audit table, making it feel like another design/evaluation section before narrative grouping.
- Scope and negative boundary statements were still scattered.
- Conclusion was two paragraphs rather than the one-paragraph full-paper convention.

Should-fix findings:

- `Problem Characterization` still behaves like preliminary evaluation.
- `授权输入` still carries safe-merge formalism and should eventually be split between Design, Model, and E2.
- Several subsection titles remain English technical phrases.
- C3 sounded like an organization/evaluation-method contribution rather than a system/evidence contribution.

## Changes Made

1. Abstract:
   - Compressed the mechanism sentence by removing the adapter list and local MCP-style broker detail.
   - Kept the abstract centered on four proof-owner classes, pre-effect commit, deterministic checker, and E1/E2/E3 results.

2. Introduction:
   - Split the overloaded system overview paragraph.
   - Removed ActPlane/env-projection detail from the intro system overview.
   - Added a compact PDF workflow paragraph that shows required proofs and one-shot lease consumption.

3. Design goals and contributions:
   - Removed production-MCP/prompt/subagent/kernel caveat from G4.
   - Simplified G4's falsifier in the goal/evaluation map.
   - Renamed C3 from `Claim-driven evaluation methodology and prototype evidence` to `Cross-boundary prototype and removal evaluation`.

4. Related Work:
   - Moved the closest-abstraction comparison table after the topic-group narrative.
   - Rewrote the opening so the section first explains the four related-work groups.
   - Rephrased the table column from a `missing` framing to `Additional commit fields for this paper's transition`.
   - Shortened the explanatory paragraph after the table and made it focus on what each line of work linearizes by default.

5. Conclusion:
   - Merged the conclusion into one paragraph.
   - Kept the final sentence on the thesis that agent extension security must control what context can prove, influence, and transfer.

## Remaining Concerns

- E2 remains a dense subsection with multiple sub-results; a later logic-flow or structure round should compress it into a clearer RQ/setup/baseline/metric/result/interpretation sequence.
- `Problem Characterization` still contains numbers in Background/Motivation; moving it fully into E2 setup would be a larger structural edit.
- `授权输入` still mixes design explanation with formal safe-merge material.
- Several section titles remain English or bilingual; a later terminology/style round should normalize them if the Chinese draft is meant to read as a polished Chinese manuscript.
