# Round 2d - Insight Defense

Date: 2026-07-09

## What Was Changed

Updated `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` after Round 2c re-attack.

## Changes

1. Reframed the core insight as authorization granularity.

Line 30 now states that the right unit is a multi-issuer, lifecycle-mutating protected-decision transition that must be exposed as a runtime linearization object before side effects, prompt placement, or delegation.

2. Weakened abstract safety-number framing.

Lines 36--38 now describe saved replay as implementation sanity / coverage guardrail and the local suite as boundary-feasibility evidence, rather than presenting `0 unsafe` rows as the main security proof.

3. Added a one-sentence insight and record schema.

Line 59 states the one-sentence insight: the authorization unit is the pre-effect multi-issuer protected-decision transition, not a filtered tool call. Line 65 gives the minimal `check_and_consume` record schema: event, decision class, lease id, issuer-typed field proofs, data/control provenance, sigma version, consume/delegate update, and audit id request.

4. Fixed proof-projection formalization.

Line 311 now says the disjoint union is over canonicalized proof cells, not raw artifacts or components. Line 606 similarly defines context class as the canonical owner of a proof cell.

5. Tightened delegation monotonicity.

The attenuation prose and rule now require \(K_c \sqsubseteq K_{parent(a)}\) / \(K_c \sqsubseteq K_\sigma(p)\), binding child authority to the concrete parent active capability set.

6. Reframed R241 as an equivalence boundary.

Line 863 now says the typed-provenance state guard row is not important because of the numeric `1/7`; it is evidence that once a strong baseline adds parent-child lease comparison, checker sole-writer state, and same-transition child update, it implements the IntentCap commit interface on that residual class.

## Remaining Concerns

The next idea round should decide whether the paper needs another re-attack or can move to Round 3 contribution/design-goal alignment. Writing rounds should later reduce table redundancy and soften related-work matrices.
