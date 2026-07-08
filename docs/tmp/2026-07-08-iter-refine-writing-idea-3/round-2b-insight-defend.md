# Round 2b: Insight Defense

Date: 2026-07-08

What changed:
- Abstract now says leases bind issuer-typed authority fields from agent/instruction/tool/env inputs, not merely four context labels.
- Intro now adds a closest-prior-work stress paragraph: provenance/action-authority systems can ask whether a parameter or action came from a trusted source, but IntentCap additionally checks issuer ownership, active lease state, budget consumption, expiry, and delegation bounds in one transition.
- Contribution C1 now names an issuer-typed protected-decision lease model with no-substitution, atomic lifecycle, and delegation attenuation.
- Formal model now states an emulation boundary for ABAC/IFC/policy DSLs: equivalence requires four projections, field ownership, proof objects, atomic check-and-consume, budget/expiry, and delegation state.
- E1 now explicitly tests the ACL/tool-visibility gap, while E3 tests residual semantics beyond provenance/action-authority families.
- E3 now says R219 is a benchmark-derived mechanism stress test, not natural-prevalence, online utility, or primary novelty evidence.
- Related work now adds a concrete SkillGuard/SkillScope contrast: the same PDF Skill gets different leases under local-XLSX versus GitHub-issue intents, while package-level manifests tend toward union authority.
- Related-work table caption now avoids strawman wording by saying prior work may encode similar policies, but the comparison is about first-class authorization objects and evaluated lifecycle.

Remaining concerns:
- Round 2c should verify whether a skeptical reviewer can still reject the insight as "just a policy DSL plus provenance."
