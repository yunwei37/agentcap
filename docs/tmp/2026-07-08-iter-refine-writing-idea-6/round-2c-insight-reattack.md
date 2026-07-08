# Round 2c - Insight Re-Attack

Date: 2026-07-08

What was checked:
- Current `docs/autopaper/intentcap-paper-zh.tex` after Round 2b.
- Focus: whether novelty can still be easily rejected as stateful ABAC, a policy DSL, provenance namespaces, or a reference monitor transaction.

Findings:
- Verdict: novelty is no longer an easy reject against MCP/tool guards, Skill permissions, or ActPlane-style backend framing.
- Remaining strongest attack: stateful ABAC / policy DSL / reference monitor transaction.
- Must-fix: make the positive contribution a missing runtime commit interface, not predicate expressiveness.
- Must-fix: define commit semantics: checker sole writer, `allow(sigma', audit)` as linearization point, no adapter caching, side effects bound to commit id, parallel adapters serialized or CAS-style.
- Must-fix: state that four context classes are the current adapter surface's coarsest safe partition under observed falsifiers, not a universal ontology.
- Must-fix: explain R241 as convergence-to-\sys: when a typed-provenance baseline adds parent-child lease-set commit and same-transition update, it has implemented the \sys commit interface.
- Should-fix: add runtime-object audit for closest systems and workload provenance for E4.
- Should-fix: reduce abstract density and avoid overclaiming with "prove".

What changed:
- Abstract: removed the typed-provenance `6/7` detail from the abstract and left it in E3.
- Introduction/formal: strengthened the positive claim that \sys defines the minimum pre-side-effect authority-state commit object, not a more expressive predicate language.
- Running example: already changed in Round 2b to show PDF text influences `spawn(summarizer, K_child)`, making final repo/body/tool provenance appear clean while the handoff transition is wrong.
- Four-context model: added "current adapter surface", "default owner equivalence classes", and "coarsest safe partition under observed falsifiers" language.
- Runtime/API: added commit semantics with checker as sole lease-state writer, `allow(sigma', audit)` as the linearization point, commit id binding, no cached allow, and serial/CAS semantics for parallel adapters.
- E3: rewrote R217/R241 as a convergence-to-\sys experiment rather than a one-rule gap.
- E4: added a workload provenance table showing which boundary rows are live side-effect, model-generated, placement/handoff tests, or monitor-rule replay audits.
- Related work: added a runtime object audit table over AuthGraph/AIRGuard, PACT, CaMeL/IFC, SkillGuard/SkillScope, ActPlane, AgentSpec/PCAS, and \sys.
- Evaluation: changed "E1 proves" style wording to "E1 shows / E3 tests / E4 validates within instrumented boundaries."
- Design doc: synchronized commit semantics and the coarsest-safe-partition contract.

Remaining concerns:
- The idea-layer easy reject is reduced, but evidence maturity remains the main risk.
- Stronger closed-loop utility/recovery, independent labels, and production-like multi-boundary integration are still needed for a top-conference-strength claim.
