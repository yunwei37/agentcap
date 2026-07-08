# Round 2b: Insight Defense

Date: 2026-07-08

## What Changed

- Abstract, lines 29-32: inserted the main insight that the safety object is not an action, resource, or flow, but a protected-decision transition jointly submitted by issuer-owned fields and atomically changing authority state.
- Abstract, lines 30-32: renamed the core object as a field-owned protected-decision lease and clarified that only required issuer classes need to provide proof.
- Introduction, lines 51-55: reframed prior-work positioning around runtime authorization object and adapter contract, not predicate expressiveness. Added the sentence that EIM/bpftime and ActPlane execute resource policy, while IntentCap decides which issuer proof can change authority state.
- Introduction, lines 59-63: stated that the system contribution is a protected-transition API plus adapter contract across context construction, Skill instruction placement, tool/MCP policy events, local env execution, and delegation handoff, not a new sandbox.
- Evaluation preview, lines 63-65: organized the evidence by E1/E3/E4 and tied E3 to class-substitution false accepts.
- Design goals, lines 143-151: tied each goal to a forcing failure: legal arguments but illegal approval, legal data flow but illegal authority field, legal first call but illegal reuse, and legal tool guard but unsafe prompt/delegation placement.
- Effect IR, lines 295-297: clarified that field proofs come from trusted UI canonicalization, fresh approval, tool registry/schema, runtime observers, context placement gateway, or explicit context cells. Model-generated fields do not themselves produce proof.
- Formal model, lines 416-452: added the merge criterion for classes and the four proof questions: user authorization, procedure constraint, interface declaration, and runtime fact.
- Lease lifecycle, lines 542-548: added a two-trace example where identical `create_issue(repo=org/repo-x)` calls with matching provenance differ only in checker state, so action/provenance guards cannot distinguish them.
- Formal model, lines 597-600: added a lemma-style proof sketch that accepted traces imply no-substitution, no-promotion, and atomic lifecycle, with E3 ablations as counterexamples when premises are removed.

## Verification Plan

- Recompile the Chinese paper.
- Re-run paper evidence audit.
- Run focused tests for audit and residual gateway behavior.

## Remaining Concerns

- Round 2c should check whether the "runtime authorization object" framing is now strong enough or still sounds like policy DSL repackaging.
