# Round 4 — Abstract / Intro Rebuild

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Skill path: `rewrite-abstract-intro`. The main agent read `rewrite-abstract-intro/references/abstract-intro-structure.md` and `iter-refine-writing/references/common-pitfalls.md`, then applied the Round 4 procedure without pausing because this invocation is inside the `iter-refine-writing` loop.

## Mapping Diagnosis

Abstract sentence roles:

- S1: context; LLM agents are extensible execution environments.
- S2: problem setup; extension text and runtime outputs influence later authority-bearing decisions.
- S3: permission gap; current mechanisms authorize formed calls/resources but not which context proves fields.
- S4-S6: system/insight; \sys uses pre-effect commit, field-owned leases, four owner classes, and deterministic checker.
- S7-S8: results; reference-action coverage, no-owner false accepts, and local multi-boundary contract evidence.

Introduction paragraph roles before edit:

- P1: background/context.
- P2: problem and PDF example.
- P3: root cause.
- P4: early insight/four-owner explanation, appearing before prior-work limitations.
- P5: existing approaches and limitations.
- P6: insight restatement.
- P7: challenges.
- P8-P9: system and example.
- P10: evaluation/scope preview.
- Contributions: present and mostly aligned.

Logic-chain issue:

- The insight appeared before existing-solution limitations, which weakened the conventional flow from cause to prior-work gap to insight.
- The system paragraph and PDF paragraph were separated even though they explain the same pre-effect commit contract.
- The abstract used `authority-state transition` while the edited design increasingly uses `pre-effect commit`.

## Reorganization Plan

- Keep P1 and P2 intact because they already provide context and the concrete problem.
- Keep P3 as root cause.
- Move existing-solution limitations immediately after root cause.
- Merge the previous four-owner and insight paragraphs into one insight paragraph centered on runtime-visible pre-effect commit.
- Keep the challenges paragraph but make it follow the insight directly.
- Merge system and PDF example into one this-paper paragraph.
- Keep evaluation/scope preview, but add the key E1/E2 numbers so it corresponds exactly to the abstract result sentence.
- Derive the abstract terminology from the revised intro by replacing `authority-state transition` with `pre-effect commit`.

## Changes Made

1. Introduction role order:
   - Reordered the middle of the intro into background, problem, root cause, prior-work limitations, insight, challenges, system/example, evaluation, and contributions.
   - Moved the prior-work paragraph before the insight paragraph.
   - Merged the system overview and PDF workflow example so the running example directly demonstrates the commit interface.

2. Abstract correspondence:
   - Replaced `authority-state transition` with `pre-effect commit` in the abstract.
   - Kept the two audited result anchors: 3,813/3,813 reference-action coverage and 3,593/3,823 no-owner false accepts.

3. Evidence and claim boundaries:
   - Kept the intro boundary statement as a single forward reference to the evidence-boundary section.
   - Did not add new claims, numbers, citations, or experiments.

## Self-Check

- Required intro roles are present and ordered.
- Root cause remains warranted because the system insight directly answers action-linearization and owner/lifecycle collapse.
- Challenges remain warranted because the system contribution is the runtime contract needed to realize the insight across multiple boundaries.
- Abstract terms now map to intro terms: context, protected decision, pre-effect commit, field-owned lease, four owner classes, deterministic checker, E1/E2/E3 evidence.

## Open Items

- The intro is still long for a final venue-formatted paper; later language and structure passes should trim repeated English technical terms.
- The E2 and formal sections still carry more detail than the opening needs, but their compression belongs to later structural rounds.
