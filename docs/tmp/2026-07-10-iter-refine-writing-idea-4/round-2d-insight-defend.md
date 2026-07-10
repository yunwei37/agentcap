# Iter Refine Writing Idea Round 2d: Insight Defense

Date: 2026-07-10

Target file: `docs/autopaper/intentcap-paper-zh.tex`

## What Changed

The Round 2c re-attack argued that the theorem could still read as a tautological interface definition and that the ablations could look like deliberately weakened baselines. The defense edits sharpened the insight into a protected-decision linearization claim and made the closest baseline more reviewer-recognizable.

## Changes Applied

- Abstract lines 28--29 now explain why tool-call granularity is tempting but insufficient: the final side effect often passes through a tool, yet the same action shape can consume, reuse, or delegate different authority.
- Introduction line 48 now says IntentCap does not claim policy DSL inexpressiveness. It identifies a missing runtime authorization object and tests whether adjacent default objects expose it.
- Contribution C1 was renamed from a field-owned lease abstraction to a `Protected-decision linearization model`.
- Formal section lines 559--562 now state the non-trivial point of Theorem 1: package-time, flow-time, action-time, and OS-time checks each miss part of the authority-state update, so protected-decision transition is the tested minimal linearization point.
- E2 line 956 now defines typed-provenance state guard as a strong prior-style composite combining CaMeL/IFC control provenance, PACT argument source, AuthGraph/AIRGuard intent-action edge, SkillGuard package policy, and stateful counters.
- E2 line 985 now calls 93.98% a `removal-family false-accept rate`, not a natural security prevalence rate.
- E2 lines 987--988 now state that the contribution is the safe-merge test and owner-projection obligation, while the four classes are the current workloads' canonical projection.
- Related work now states that adjacent systems naturally expose flow labels, argument contracts, authorization graph edges, or package policy, while IntentCap's runtime object is a pre-effect authority-state transition.

## Not Changed

- No quantitative values were changed.
- No new blinded adjudication experiment was run in this writing step.
- No claim was added that IntentCap is globally minimal or that all three-class designs are impossible.

## Remaining Concerns

The paper still needs a stronger evidence step for independent/blinded owner-label adjudication and, ideally, a concrete implementation of the strongest composite baseline beyond the paper-facing interface audit.
