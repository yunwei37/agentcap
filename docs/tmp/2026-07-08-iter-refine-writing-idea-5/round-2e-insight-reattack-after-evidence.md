# Round 2e: Insight Re-Attack After E3/E4 Evidence

Date: 2026-07-08

## What Was Checked

A read-only reviewer re-attacked `docs/autopaper/intentcap-paper-zh.tex` after R239 weak-variant ablation and R240 adapter proof-completeness evidence were integrated. The focus was whether a top-conference reviewer could still easily reject the idea as provenance/IFC plus a stateful policy DSL and counters.

## Findings

Reviewer verdict: the easy novelty reject is no longer easy. R239 turns the four issuer-boundary claim into a falsifiable same-event ablation: no-owner/collapsed variants false-accept 3,593/3,823 denied protected decisions. R240 answers the adapter objection by showing 38/38 local boundary verdicts map to modeled proof obligations and 21/21 denials map to modeled denial classes.

Must-fix findings:

- Clarify that the novelty is the commit object, not the four class names. The four classes are issuer-owned projection boundaries for fields in one atomic `check_and_consume` transition, not an ABAC taxonomy.
- Make R239 look less like a strawman by explaining each weak variant as a natural design shortcut a policy DSL, IFC guard, or action guard might take without issuer-owned projections or atomic lifecycle state.
- State the equivalence condition more sharply: IntentCap is not more expressive than every possible DSL; it identifies the minimum runtime object a DSL must expose to be sound for agent protected decisions.

Should-fix findings:

- Move the strongest insight sentence earlier and repeat it in the design opening.
- Separate system contribution from policy-language contribution: the system contribution is requiring adapters to submit the same pre-effect field-proof commit record before placement, side effect, or handoff.
- Keep ActPlane/backend wording bounded to lowering feasibility unless production kernel mediation is implemented.

## What Changed

- Abstract, around lines 30-33: rewrote the core insight as a pre-effect, multi-issuer commit protocol over authority-state transitions, then explained it as a protected-decision transition jointly submitted and atomically consumed.
- Introduction, around lines 53-64: added the minimum-runtime-object boundary and changed the system contribution wording from generic atomic checker transition to a pre-effect field-proof commit record submitted before prompt write, side effect, or handoff.
- Design overview, around line 148: repeated the core insight at the design opening so the taxonomy is read as a consequence of the commit-object claim.
- Formal model, around line 523: sharpened the equivalence condition: a policy DSL can match IntentCap only if it exposes the same issuer-owned field proofs and lifecycle update as one runtime commit object.
- E3, around lines 750-797: described no-owner, per-edge collapse, post-hoc policy DSL, and split-lifecycle variants as natural collapsed/split-state shortcuts, and changed Table `tab:e3-weak-variant-ablation` to report the design shortcut each variant represents.
- Related work, around line 927: clarified that IntentCap is not claiming greater expressiveness than all possible DSLs; it identifies the runtime object a sound DSL must expose.

## Remaining Concerns

The novelty rejection is now weaker. The remaining high-risk objection is evidence maturity: the paper still has local adapter evidence, author-adjudicated lease labels, and replay/lowering feasibility rather than production prompt-builder/MCP/subagent runtime, independent expert agreement, or production ActPlane/kernel mediation.
