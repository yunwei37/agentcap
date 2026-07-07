# Round 2c: Insight Re-Attack

Date: 2026-07-07

## What Was Checked

Re-attack of the revised lease-lifecycle novelty framing after Round 2b edits, focusing on lines 25, 40--44, 49--51, and related work lines 265--272.

## Findings

Subagent reviewer reported:

> The strongest attack no longer says this is merely prompt injection plus taint tracking. The narrower attack is that IntentCap may be AuthGraph/PACT/AIRGuard-style intent/provenance/action checking plus traditional capability fields packaged into one token.

> The paper repeatedly says leases are minted, checked, consumed, attenuated, and delegated, but the formal model does not define those transitions. Without transition rules, the lifecycle claim is prose rather than calculus.

> The formal model has `lease(kappa)` as an event but no mint rule, consume rule, expiration transition, or delegation attenuation judgment.

> The paper needs a decisive example where final action provenance alone is insufficient or unnatural, such as reuse of a consumed approval lease, delegation beyond parent authority, temporal guard violation, or a lease minted from untrusted tool output.

## What Was Changed

No paper text was changed in this sub-round. This was an adversarial re-attack pass only.

## Remaining Concerns

The next defense must add explicit lifecycle transitions and align the contribution list to model / system / evidence. Otherwise the novelty attack remains viable as "capability/provenance packaging."
