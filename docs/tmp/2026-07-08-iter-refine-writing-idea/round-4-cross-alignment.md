# Round 4: Cross-Alignment

Date: 2026-07-08

Skill workflow: `iter-refine-writing-idea`, Round 4 cross-alignment review.

## What Was Checked

The reviewer checked whether problem, insight, goals, contributions, design, implementation, and evaluation tell one coherent story in `docs/autopaper/intentcap-paper-zh.tex`.

## Findings

Must-fix findings:

1. C3 said "four-block evaluation results," while the evidence section later said current evidence is pilot/mechanism evidence and does not replace E1-E4.
2. The abstract sounded like final results, while the evaluation section was still phrased as planned experiments.
3. G4 promised recovery/refinement but the current evidence table does not yet include recovery rate or recovered task-correct executions.
4. G5 multi-boundary lowering sounded broader than the implemented adapter surface.
5. Agent context and env context boundaries drifted: both appeared to include selected objects/files.
6. `policy_update` appeared in the formal model and protected-decision list but not in evaluation/residual workloads.

Should-fix findings:

1. Terminology drift across protected decision, protected event, authority lifecycle event, and authority-state transition.
2. E3 should be foregrounded as the novelty experiment.
3. Approval burden was motivated but not fully represented in evaluation metrics.

## Changes Made

Updated `docs/autopaper/intentcap-paper-zh.tex`:

- Abstract now says the current draft presents design, formalization, and pilot evidence; full end-to-end utility, recovery, and independent expert-oracle conclusions are left to E1-E4 closure.
- C3 was changed from a final result contribution to "Evidence plan and pilot results," with current artifact numbers explicitly scoped as pilot/mechanism evidence.
- G4 was narrowed to fail-closed denial feedback: no broad-permission fallback; recovery must use evidence-bound narrower leases or fresh approval.
- G5 was narrowed to selected-boundary adapter-contract lowering; instruction/delegation are identified as trace-level contracts, and production script/file/process/network enforcement remains an ActPlane-style backend target.
- Added approval count, approval-scope breadth, and broad approval avoided to E1/E4 metrics.
- Clarified authority-plane boundary:
  - Agent context authorizes which objects/sinks were selected.
  - Env context only proves runtime existence and observed values; it cannot authorize object selection.
- Defined the main term `protected-decision transition`; `protected event` is now an implementation encoding.
- Added a policy-update residual case and included policy-update attempts in E3 workloads.

## Remaining Concerns

The paper is now internally consistent as a design + pilot evidence draft. It is not yet internally consistent as a final OSDI/NeurIPS full-results submission because the main result closures are still missing:

- E1 full end-to-end security/utility with recovery and approval accounting.
- E2 independent expert-oracle replication.
- E3 benchmark-derived residual lift against strongest semantic baselines.
- E4 planner/CEGAR recovery that improves task-correct progress without broad leases.
