# Round 3: Contributions and Design Goals

Date: 2026-07-08

Skill workflow: `iter-refine-writing-idea`, Round 3 contribution/goals review.

## What Was Checked

The reviewer checked the contribution list, design goals, and goal-to-evaluation mapping in `docs/autopaper/intentcap-paper-zh.tex` against Section 3 of the idea-quality checklist.

## Findings

Must-fix findings:

1. C3 was still progress-shaped: it described an evaluation framework and evidence boundary rather than a result contribution.
2. G4 promised deterministic recovery, but recovery was not clearly a system contribution with completed metrics.
3. G5 multi-boundary lowering sounded stronger than the current implementation, because production sandbox/ActPlane lowering is still a target rather than an implemented backend.
4. Goal-to-contribution-to-evaluation mapping was too implicit.

Should-fix findings:

1. C1 compressed too many mechanisms into one list.
2. C2 needed to name the central checker API and implementation boundary more concretely.
3. Approval burden should become a real metric if kept as a motivation/evaluation promise.
4. E3 should be presented as the flagship novelty experiment.

## Changes Made

Updated `docs/autopaper/intentcap-paper-zh.tex`:

- C1 now defines the model around protected-decision leases, four-plane requirements, no-promotion, check-and-consume lifecycle, and P1-P4 trace-level properties.
- C2 now names the four central checker API classes: minting, check-and-consume, attenuation, and expiry; the formal section keeps the exact API names.
- C3 now states a positive evidence contribution using current artifact results: 0 dangerous events over 3,746 protected events, 6/6 denied local env events blocked before side effects with 0 unsafe effects, and 18-task local-Qwen authority reduction from 14.72 to 2.61 visible schemas while action reward remains 8/18.
- G4 was narrowed from "deterministic recovery" to "fail-closed refinement": rejected proposals cannot fall back to broad permission; recovery must come through narrower evidence-bound leases or fresh approval.
- G5 was narrowed from broad multi-boundary lowering to adapter-contract lowering on selected implemented boundaries, while keeping ActPlane-style backend as a production target.
- Added Table `tab:goal-map` mapping G1-G5 to contributions, evaluation sections, and primary falsifiable metrics.
- Evaluation opening now states that E3 is the flagship novelty experiment for four-plane no-promotion and check-and-consume lifecycle.

## Remaining Concerns

The contribution list is now paper-shaped for the current draft, but the final top-conference version still needs stronger completed evidence:

- E3 benchmark-derived residual lift.
- E4 planner/CEGAR recovery with task-correct progress and zero dangerous execute.
- Independent replication of E2 expert-oracle lease labels.
- Broader E1 recovery/approval accounting and adversarial workloads.
