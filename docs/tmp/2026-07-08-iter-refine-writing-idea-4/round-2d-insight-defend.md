# Round 2d: Insight Defense

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

## Changes Made

- Abstract now includes the short insight: provenance tracks value origin; IntentCap checks whether the source owns the field in the current authority-state transition.
- Formal section now states the expressiveness boundary explicitly: a DSL can encode the rules only by exposing issuer-owned field proofs and lifecycle updates as one atomic transition, otherwise it needs an external cross-guard coherence proof.
- E3 was renamed and reframed as `Necessity of Issuer-Owned Atomic Transitions`. It now defines the intended comparison as full IntentCap vs no-owner collapsed context vs split-state lifecycle checking.
- E3 now separates current evidence from remaining top-conference evidence gaps: R220/R221 provide trace-derived field-owner characterization and a label packet, while R217/R219/R224 provide controlled residual false accepts; independent labels and natural-event false-accept rates remain required.
- Implementation text now states that the system contribution is the multi-boundary transition API and adapter contract; ActPlane-style lowering is only an env adapter target.
- Skill/MCP related work now includes a minimal field-ownership counterexample where a per-run manifest claims a different repo or broader GitHub scope than the user authorized.

## Remaining Concerns

- The current paper still needs independent field-owner adjudication and more natural-event false-accept rates for the strongest E3 necessity claim.
- This defense edit sharpens claim boundaries but does not add new experimental evidence.
