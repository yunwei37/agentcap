# Iter Refine Writing Idea Round 4: Cross-Alignment

Date: 2026-07-10

Skill workflow: `iter-refine-writing-idea`, Round 4 cross-alignment.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Lovelace`.

## What Was Checked

The subagent checked whether problem, insight, goals, contributions, formal model, implementation, evaluation, related work, and limitations tell one coherent story. The review focused on the protected-decision linearization framing, the four proof-owner classes, safe-merge projection, C1/C2/C3, G1--G4, E1/E2/E3, and whether experiments read as claim-bearing evidence rather than run logs.

## Findings

Overall judgment: the main spine is now coherent. The paper is centered on protected-decision transition as the authority-state linearization point, four context classes as proof-owner projections rather than component taxonomy, and E1/E2/E3 as expressiveness, mechanism-necessity, and multi-boundary enforceability evidence.

Must-fix findings:

- The recovery/task-loop diagnostic paragraph still read like an experiment ledger rather than a claim-facing paper result.
- G1 mapped "untrusted compiler cannot mint authority" too directly to E2, even though E2 primarily tests non-owner issuer substitution; compiler-outside-TCB belongs to C2/G3 runtime contract and E3/proof-audit evidence.
- E2's core removal evidence still depends on author-adjudicated labels and must keep saying so unless a blinded second-pass label gate is added.

Should-fix findings:

- Explain the two E1 tool-oracle misses so they are not read as checker false denials.
- Strengthen C2 as an adapter contract plus checker sole-writer state, not a list of scripts or probes.
- Keep ActPlane/eBPF as future deployment/backend evidence unless a production integration is actually added.
- Qualify authority-surface shrinkage as a matched/local observation, not a top-level expert-oracle least-privilege claim.

Consider findings:

- Eventually rename formal `agent` notation to `intent` or `issuer`; this was not changed because saved artifacts and audit anchors still use the historical field name.
- Make the E3 table read as "one contract, many blockpoints."
- End with a clear statement of what is proved and what is not.

## Changes Applied

- Narrowed the G1 row in the goal map to intent-owned minting and high-impact bounds. The untrusted compiler invariant now maps to C2/G3 runtime contract and E3/proof-audit evidence.
- Added implementation wording that C2's system artifact is an adapter-facing pre-effect commit contract plus checker-owned authority state, not a collection of probes.
- Marked production MCP, prompt/subagent runtime, ActPlane/eBPF integration, and online user-simulator loops as stronger deployment evidence rather than current C2 contribution.
- Qualified runtime exact lease authority-surface shrinkage as a matched/local observation, not an independent expert-oracle least-privilege result.
- Added a sentence explaining the two E1 tool-oracle misses as reference replay/evaluator reconstruction issues, with 0 checker blocks and 0 unsupported tasks.
- Reworded E2 label dependence as "predeclared author-adjudicated labels" and kept blinded second-pass/independent replication in the evidence-boundary table.
- Compressed the benchmark recovery/task-loop diagnostic into one claim-facing paragraph: protocol/context failures were isolated, but benchmark-scale recovery remains open with 1/5 action-reward, 0/5 tool-oracle, and 22/46 bound reference calls on the cited slice.
- Added a short E3 table lead-in explaining that every row tests the same missing-pre-effect-commit falsifier at a different block point.
- Updated the conclusion to state that current evidence supports owner/lifecycle safety and local multi-boundary enforceability, but not benchmark-scale utility, production ActPlane/MCP deployment, approval-burden reduction, or independent oracle minimality.

## Remaining Concerns

The highest-value next evidence gate remains blinded/second-pass field-owner adjudication for E2. The strongest deployment gate remains production MCP or ActPlane/eBPF mediation with overhead. The utility gate remains free-form benchmark recovery and stronger planner/compiler recall.
