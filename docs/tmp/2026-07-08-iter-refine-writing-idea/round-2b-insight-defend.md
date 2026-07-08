# Round 2b: Insight Defense Edits

Date: 2026-07-08

Skill workflow: `iter-refine-writing-idea`, Round 2 defense pass.

## Edits Made

Updated `docs/autopaper/intentcap-paper-zh.tex` to defend against the "ABAC + provenance + counters" rejection.

Main changes:

1. Abstract now states that the core abstraction is not a tool permission, context label, or observed action, but an intent-minted protected-decision transition that changes future authority state.
2. Introduction now states the least-privilege unit explicitly: tool/resource/context/action are the wrong units; the right unit is the authority-state transition.
3. Contributions were narrowed and strengthened:
   - C1: authorization unit moves from operation/resource to intent-minted decision transition.
   - C2: system contribution is a checker-centered four-plane transaction runtime over instruction, tool/MCP, local environment, and delegation boundaries.
4. The four context classes are now defined as independent authority planes with issuer, update frequency, forgery surface, influence classes, forbidden fields, and adapter.
5. Added the ABAC distinction:
   - ABAC asks whether attributes satisfy a policy rule.
   - IntentCap asks whether four independently issued authority planes jointly authorize one authority-state transition.
   - A missing field in one plane cannot be supplied by another plane.
6. Added a table explaining what fails when planes are collapsed:
   - Agent + Instruction lets workflow advice widen sink or approval.
   - Tool + Env lets runtime output choose tool, binary, or sandbox.
   - Instruction + Env lets untrusted data plan, delegate, or request authority.
7. Lease lifecycle now uses a concrete workload fact: the same `create_issue(repo=org/repo-x)` argument can be valid, stale, improperly delegated, or widened depending on mint/consume/delegation/approval provenance.
8. E3 now includes a stronger composite baseline: stateful ABAC + taint labels + capability counters + delegation table, plus a split-state variant without a unified `check_and_consume` transaction.
9. Related work now says a sufficiently extended ABAC/IFC system can encode equivalent semantics only by adopting the same intent-minted, consumed, attenuated protected-decision lease.

## Resulting Claim Boundary

This pass does not claim that IntentCap invents provenance, taint tracking, capabilities, or stateful counters. The claim is narrower:

IntentCap proposes the protected-decision transition as the authorization unit for agent least privilege, and requires agent, instruction, tool, and env authority planes to jointly authorize that transition under no-promotion, consumption, expiry, and delegation attenuation.

## Verification

The LaTeX build was checked after the edits. A single overfull warning caused by long baseline names was fixed by replacing those long names with short Chinese labels in the E3 paragraph.
