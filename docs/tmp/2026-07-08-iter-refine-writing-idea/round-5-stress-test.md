# Round 5: Reviewer Stress Test

Date: 2026-07-08

Skill workflow: `iter-refine-writing-idea`, Round 5 reviewer stress test.

## What Was Checked

The reviewer attempted to construct the strongest rejection argument against the current Chinese paper, focusing on idea-layer novelty, contribution/evidence alignment, system boundary, and whether the draft is top-conference-shaped.

## Findings

The reviewer verdict was:

> Idea layer is coherent but evidence gate remains.

Must-fix findings:

1. The strongest novelty attack remains that IntentCap could be seen as stateful ABAC + IFC/provenance + attenuated capabilities + counters.
2. The four context classes still needed to read more like system authority planes than taxonomy.
3. Control provenance for LLM decisions is the largest technical assumption; the paper needed an explicit provenance policy.
4. C3 is acceptable for a design/pilot draft but not for a final OSDI/NeurIPS result contribution.
5. System contribution and implementation boundary must remain scoped to checker API plus selected adapter contracts unless stronger production-like backend evidence is added.

Should-fix findings:

1. E3 should be the flagship novelty experiment.
2. Current utility evidence does not yet support "preserves task utility"; it supports a safety-layer and authority-surface claim.
3. Policy update and approval burden still require stronger evidence if kept as main claims.

## Changes Made

Updated `docs/autopaper/intentcap-paper-zh.tex`:

- Narrowed the system contribution to the central checker runtime plus implemented gateway/env probes and trace-level instruction/delegation contracts.
- Added an explicit, testable novelty claim: the key failure is cross-plane authority filling and stale lease reuse; the necessary mechanism is an atomic transition binding trusted mint, decision-specific influence, consumption/expiry, and delegation attenuation.
- Clarified that E3 is the main experiment for this novelty claim and that semantic-equivalent stateful ABAC/IFC/capability baselines are expected if they adopt the same transition object.
- Added a paragraph specifying each authority plane's independent issuer and unforgeable fields:
  - agent: goal, authorized objects/sinks, approvals,
  - instruction: workflow scope,
  - tool: schema, credential scope, binary descriptor, sandbox contract,
  - env: runtime object existence, values, tool results, script outputs.
- Added an explicit protected-field provenance policy:
  - authority-bearing fields require structured source proof,
  - missing/unattributable model-generated fields are conservatively over-approximated by visible non-policy context,
  - checker fails closed when any approximated control source lacks the required influence mode,
  - utility costs must be measured via false denial, proof completeness, and recovery metrics.

## Remaining Concerns

No easy "the idea is incoherent" rejection remains. The remaining blockers are evidence gates:

- E3 must produce benchmark-derived or at least stronger workflow-derived residual evidence against the strongest semantic baselines.
- E1/E4 must show task-correct recovery or explicitly present IntentCap as a safety enforcement layer.
- E2 must get independent expert-oracle replication before claiming expert least-privilege results.
- A stronger env/system backend is needed before claiming production-like multi-boundary enforcement.
