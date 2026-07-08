# Round 2b: Insight Defense

Date: 2026-07-07

## What Was Checked

Defended the paper against the Round 2a novelty attack:
- "IntentCap is just capability + provenance/IFC + workflow state."
- "A stateful policy engine could add counters, expiry, and delegation graph."
- "Context influence modes are just taint labels with more policy dimensions."

## Findings Being Addressed

Round 2a's strongest attack:

> The paper does not yet show a new invariant, a minimal decomposition, or a workload property that forces these pieces to be unified as "intent-carrying leases" rather than implemented as a conventional stateful provenance policy.

Target defense:

> IntentCap's novelty is the atomic authority lifecycle object for future agent decisions, not the individual ingredients.

## What Was Changed

1. Protected decisions reframed as lifecycle transitions.
   - Before, line 36 used `mint/select/widen/consume/delegate`.
   - After, line 36 defines protected decisions as authority lifecycle events that `create`, `select`, `widen`, `spend`, or `transfer` authority.

2. Thesis strengthened from "lease lifecycle" to "authority-state transition".
   - Before, line 40 said agent extensions need a run-time lease lifecycle.
   - After, line 40 says protected agent decisions should be modeled as authority-state transitions, not events checked only after action materialization. It also states that the lease is the atomic authorization object binding trusted mint provenance, decision-specific influence authority, consumption/expiration, and delegation attenuation in the same state update.

3. Context influence modes distinguished from taint labels.
   - Before, line 153 described influence modes as decision-specific authority.
   - After, line 153 explains that they are not merely taint-policy dimensions; they specify whether context may participate in an authority-state transition, and they prevent reuse of context authority across lifecycle states only when bound to the same lease as intent/budget/expiry/delegation.

4. Formal invariant made atomic.
   - Before, line 236 said checker state stores lease fields and updates them atomically.
   - After, line 236 states why this atomicity is necessary: splitting mint provenance, influence authority, consumption/expiration, and delegation bound across independent labels/ACLs/counters/records requires proving no stale authority reuse, cross-object widening, or consumed-state bypass.

5. Equivalence condition clarified.
   - Before, line 276 said a baseline must introduce trusted mint, budget consumption, expiration, and monotone delegation state.
   - After, line 276 says an equivalent baseline must introduce an equivalent atomic authorization object covering trusted mint, decision-specific influence, budget consumption, expiration, and monotone delegation state.

6. E3 made into a novelty test.
   - Before, lines 367-369 compared full IntentCap to named ablations and strong provenance/taint baselines.
   - After, lines 367-369 require incremental lifecycle ablations over strict subsets of `{trusted mint, decision-specific influence, consumption/expiry, delegation partial order}` and treat any baseline with an equivalent atomic object as semantic-equivalent rather than weaker by definition.

7. Related-work difference sharpened.
   - Before, line 423 said IntentCap maintains four kinds of state.
   - After, line 423 says an equivalent system must bind provenance labels, ACL rules, counters, and delegation graph into the same atomic authority transition.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`.
- Build completed successfully.
- Final log check found no undefined citations, undefined references, fatal errors, or LaTeX errors.

## Remaining Concerns

- Round 2c must test whether the new "atomic authority transition object" framing is enough, or whether a reviewer can still say a conventional stateful policy engine with transaction semantics is equivalent.
