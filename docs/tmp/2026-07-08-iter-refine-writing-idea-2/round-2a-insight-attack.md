# Round 2a: Insight and Novelty Attack

Date: 2026-07-08

## What Was Checked

Read `docs/autopaper/intentcap-paper-zh.tex` as a skeptical reviewer against `iter-refine-writing-idea/references/idea-quality-checklist.md` Section 2. The review focused on whether the paper's insight is separable from the artifact and whether IntentCap could be dismissed as a combination of existing capabilities, ABAC, IFC/provenance, counters, delegation tables, Skill/MCP permissions, or ActPlane-style enforcement.

## Findings

Strongest reject argument:

IntentCap can look like a stateful reference monitor that combines known pieces: capabilities, ABAC predicates, IFC/provenance labels, temporal counters, and delegation tables. The draft already says that a baseline with the same atomic transition object is semantic-equivalent, but that framing can sound like a renaming move unless the paper defines the minimum interface and shows which residual class appears when each part is absent.

Must-fix findings from the reviewer:

- The insight must be stated as a testable proposition: the dangerous unit in agent authorization is the authority-state transition, not the final action.
- The paper needs a minimum interface: `mint`, `check_and_consume`, `attenuate`, `expire`, issuer-typed required fields, control-provenance proofs, and atomic state update.
- Four planes should be typed authority fields, not just ABAC namespaces.
- E3 needs a workload characterization and strongest composite baseline, otherwise residual cases look hand-constructed.
- Related work needs a closest-abstraction matrix rather than only prose distinctions.

## Remaining Attack After Round 2a

A reviewer can still ask for actual E3 evidence against the strongest composite baseline. The writing can preempt the conceptual attack, but the experiment must still be implemented and reported before a full-paper novelty claim is safe.
