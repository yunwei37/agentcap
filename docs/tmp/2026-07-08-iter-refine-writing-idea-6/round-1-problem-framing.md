# Round 1 - Problem Framing

Date: 2026-07-08

What was checked:
- The problem statement, root cause, and motivation in `docs/autopaper/intentcap-paper-zh.tex`.
- Focus: whether the introduction makes a systems-paper argument before introducing solution vocabulary.
- Checklist: `iter-refine-writing-idea` Section 1 problem framing.

Findings:
- Must-fix: Abstract and introduction introduced terms such as multi-issuer commit protocol, protected-decision transition, and field-owned lease before the reader fully saw why existing tool/argument/provenance checks fail.
- Must-fix: The minimal failure trace mixed approval widening, delegation, stale reuse, and policy update, making it read like an attack catalog rather than a single root-cause example.
- Must-fix: The four context classes need to appear as proof-boundary safe-merge criteria, not as renamed ABAC attributes.
- Must-fix: The system contribution should name the concrete API and adapter contract earlier.
- Should-fix: Tie design goals to the two root causes.
- Should-fix: State the evaluation thesis as E1/E3/E4 proving the root-cause story.
- Should-fix: Re-emphasize that related-work comparison is about default authorization object, not theoretical DSL expressiveness.

What changed:
- Abstract: changed the opening from solution-heavy vocabulary to the failure shape: legal parameters, plausible provenance, and sandbox-visible side effects can still hide an incorrect authority-state transition.
- Introduction: narrowed the main failure trace to PDF text causing illegal delegation of a one-shot GitHub issue lease, then mentioned approval widening, stale reuse, and policy update as same-root variants.
- Introduction: moved the four-class model into a safe-merge criterion: two classes can be merged only if issuer, forgeability surface, owned fields, observation boundary, and lifecycle authority match.
- System contribution: named `check_and_consume(e, lease_id, field_proofs, prov, sigma)` as the core protected-transition API.
- Design goals: added explicit mapping from G1/G2 to issuer collapse, G3 to authority-state split, and G4 to multi-boundary enforcement.
- Evaluation: rewrote the overview to state the experiment logic: E1 checks event-model feasibility, E3 tests whether removing root-cause fixes recreates unsafe paths, and E4 tests non-tool boundary placement.
- Related work: updated the closest-abstraction table caption to state that a policy DSL with the same atomic issuer-owned lease transition is equivalent on covered fields and transitions.

Remaining concerns:
- The abstract is still dense because it includes paper-facing result numbers needed by the evidence audit.
- A later writing pass should reduce repeated terminology and smooth the introduction once experiment results are settled.
