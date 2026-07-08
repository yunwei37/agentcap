# Round 2a: Insight Attack

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Idea-quality checklist Section 2: whether the insight is separable, non-obvious, and not already covered by adjacent work.

Strongest attack:
- A skeptical reviewer can argue that IntentCap is only a packaging of existing intent/provenance/action authority control, IFC/taint, policy DSLs, Skill permissions, and capability lifecycle into one lease object.
- The paper should not rest novelty on "context provenance" because adjacent work already studies user intent, action provenance, argument authority, and untrusted context influence.
- The stronger insight should be: trusted provenance is not enough; each authority field has an owner issuer and a stateful lifecycle. The right unit is an issuer-typed, stateful protected-decision transition.

Must-fix findings:
- Clarify that protected-decision transitions are not just authority-bearing actions with provenance.
- Elevate four context classes into issuer-typed authority fields with no-substitution, not an arbitrary taxonomy.
- Treat R219 as a mechanism stress test, not primary novelty or natural-prevalence evidence.
- Add an emulation boundary for policy DSLs: an equivalent DSL must expose four projections, field ownership, proof object, atomic check-and-consume, budget/expiry, and delegation.
- Sharpen SkillGuard/SkillScope distinction with a same-Skill different-intent example.

Remaining concerns:
- A future round should stress-test whether the revised intro now makes the insight defensible without sounding like generic provenance.
