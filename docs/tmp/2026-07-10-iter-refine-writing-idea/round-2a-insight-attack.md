# Round 2a: Insight And Novelty Attack

Date: 2026-07-10

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`, focusing on whether the idea can still be dismissed as ABAC, IFC, a policy DSL, Skill/MCP permissioning, or ActPlane policy synthesis.
- `iter-refine-writing-idea/references/idea-quality-checklist.md`, Section 2 insight and novelty.

Findings:
> Strongest rejection: This can still be read as a stateful reference monitor / ABAC / IFC policy interface with typed provenance, capabilities, counters, and delegation state. The paper renames these as field-owned leases and commit objects, then evaluates against variants that remove exactly those fields.

> Must-fix: The novelty boundary risks tautology. Do not only say a DSL is equivalent if it exposes the same object. Add the positive insight: agent runtimes split proof issuer, observation issuer, and lifecycle owner across prompt construction, tool registries, runtime observers, approval UI, and delegation adapters. The contribution is where this state must live and linearize, not a new boolean predicate.

> Must-fix: E2 could look like author-defined weak baselines. Add the strongest prior-derived baseline framing: a stateful provenance/ABAC guard with owner fields, approval, holder, temporal, budget, and delegation predicates. Show it either fails at a boundary or converges to the IntentCap interface.

> Must-fix: The four context classes can still read like ABAC namespaces. Make safe merge a theorem/test: a merge is safe only if the collapsed checker never accepts an event the full checker rejects. E2 should be described as counterexample evidence for tested merges, not a global ontology proof.

> Must-fix: Formal properties are too definition-driven. Add merge-unsoundness and split-lifecycle unsoundness propositions: without owner projections or same-transition lifecycle update, same-action traces can create stale reuse, substitution, or over-delegation.

> Must-fix: ActPlane positioning should avoid a strawman. State that an ActPlane-style backend receiving only OS events lacks upstream projections; if upstream supplies them and shares the same lease state, it becomes an IntentCap env/backend lowering.

What was changed in Round 2b:
- Introduction: added a positive insight sentence explaining that proof issuer, observation issuer, and lifecycle owner are split across agent runtime layers, so the novelty is state placement and linearization rather than predicate expressiveness.
- Formal model: added Proposition 1 for owner-merge unsoundness and Proposition 2 for split-lifecycle unsoundness, each scoped to tested decision classes and artifacts.
- E2: reframed the typed-provenance state guard as the strongest prior-derived policy-style baseline and a convergence boundary, not a weak strawman.
- Related work: reframed ActPlane-style enforcement as an env/local projection backend that needs upstream issuer projections and shared checker state to be semantically equivalent.

Remaining concerns:
- A fresh Round 2c re-attack is still required before the iter-refine-writing-idea cycle can move to contributions/goals review.
- The paper still needs stronger production-level ActPlane/kernel mediation and broader integrated utility experiments before making a deployment-scale enforcement claim.
