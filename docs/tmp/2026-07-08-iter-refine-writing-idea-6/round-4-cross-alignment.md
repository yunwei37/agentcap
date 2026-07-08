# Round 4 - Cross-Alignment

Date: 2026-07-08

What was checked:
- Cross-section alignment in `docs/autopaper/intentcap-paper-zh.tex`: problem statement, root causes, core insight, design goals, contribution list, implementation scope, evaluation overview, E1/E3/E4, evidence boundary, and closest-work tables.
- Focus: whether the paper reads as one coherent systems argument rather than a collection of experiments or adapter demos.

Findings:
- Must-fix: E1 still mixed protected-event safety with reference-action coverage; it should be a feasibility/expressiveness guardrail, while E3 carries mechanism necessity.
- Must-fix: the multi-boundary prototype could be read as a set of small adapter demos; the paper needed a unifying invariant that every boundary submits the same pre-effect commit record and the checker is the sole lease-state writer.
- Must-fix: the "four classes versus three classes" point repeated too often and risked sounding like taxonomy defense rather than a field-owner projection interface.
- Must-fix: the evidence boundary table mixed lease auditability, authority exposure, and closed-loop recovery in one row.
- Should-fix: related-work tables should be framed as comparing default exposed objects in published designs, not all possible extensions.

What changed:
- Evaluation overview: E1 is now explicitly a feasibility/expressiveness guardrail; E3 is the mechanism necessity experiment; E4 is the system contract experiment.
- E1: renamed to `Event-Model Feasibility and Reference-Action Coverage`; the primary metric is reference-action coverage, with unsafe accept as a sanity check.
- E3: added a topic sentence naming it as the paper's necessity experiment over issuer ownership and same-transition lifecycle update.
- E4: reframed as proving three properties of one commit contract: pre-side-effect correctness, pre-placement/handoff correctness, and monitor-lowering equivalence.
- Implementation and C3: added the invariant that the contribution is one pre-effect commit contract across boundary types, not five separate adapters.
- Authorization-input/formal text: reduced repeated "three classes are insufficient" phrasing and shifted emphasis to owner projections, no-substitution, and safe-merge tests.
- Evidence boundary: split lease auditability from preliminary closed-loop utility/recovery.
- Related work: narrowed captions/headers to "default exposed object in published design" and reiterated that extensible DSLs could implement the same commit object.

Remaining concerns:
- R242/R243/R244 should be integrated only if the paired all-tools comparison yields a clear, scoped utility/authority-exposure result. Otherwise it belongs in limitations or supporting diagnostics.
- A future writing pass should still simplify abstract/result density and possibly add a small commit-interface figure.
