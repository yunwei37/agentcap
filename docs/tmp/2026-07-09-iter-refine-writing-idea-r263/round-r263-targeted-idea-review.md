# R263 Targeted Idea-Layer Review

Date: 2026-07-09

Scope: targeted post-experiment review of the R263 closed-loop recovery evidence integration, not a full `iter-refine-writing-idea` five-round cycle.

Files checked:

- `docs/autopaper/intentcap-paper-zh.tex`
- `docs/evaluation.md`
- `scripts/run_closed_loop_recovery_suite.py`
- `results/eval/R263RECOVERY/`

Reviewer: forked read-only subagent using the idea-layer checklist focus from `iter-refine-writing-idea`.

## Findings

Must-fix:

- The Chinese paper said the model only saw structured denial feedback and the original candidate set. The actual feedback prompt also includes labels, leases, and candidate event details. This could overstate denial-only recovery.
- `docs/evaluation.md` had not yet added R263 to the reproducibility checklist even though R263 was already cited in the gate summary and paper evidence row.

Should-fix:

- `unsafe initial proposals` could be read as natural model proposals. R263 uses `initial_strategy=force-initial-event`, so the wording should say forced or denial-targeted initial events.
- The Chinese paper should explicitly say R263 is a hand-written/constructed local suite.
- The evaluation document still had E1/E3/E4 naming in the current consolidation, while the Chinese paper now uses E1/E2/E3 plus a supporting audit.

Consider:

- R263 candidate identifiers and descriptions are visibly semantic, and prompts expose leases. This is acceptable for a microbenchmark, but future runs should use blinded candidate IDs and neutral descriptions before claiming natural recovery.
- Do not move R263 into the abstract or contribution list.

## Changes Made

- In `docs/autopaper/intentcap-paper-zh.tex`, changed the R263 paragraph to say the suite is hand-written and that Qwen3.6 sees the task payload, labels, leases, candidate events, and structured denial feedback. The text now frames recovery as happening under a visible lease/candidate scaffold.
- In the evidence-boundary table, changed R263 wording to "hand-written denial-targeted six-task microbenchmark" and described visible labels/leases/candidate events.
- In `docs/evaluation.md`, changed R263 from "unsafe initial proposals" to "forced unsafe initial events" and clarified what the feedback payload contains.
- In `docs/evaluation.md`, aligned the current consolidation naming with the Chinese paper: E1 is reference coverage/security sanity, E2 is mechanism necessity, E3 is local multi-boundary adapter enforcement, and lease auditability is supporting evidence.
- In `docs/evaluation.md`, added R263RECOVERY to exact commands, commit/model/input metadata, machine/model records, fixed-input local-model stages, raw result paths, and checked-in scripts.

## Remaining Concerns

- This was a targeted idea-layer check, not the full 5-round idea refinement cycle or the full 11-round writing refinement cycle.
- R263 remains a microbenchmark. A stronger recovery claim needs benchmark-derived tasks, blinded candidate IDs/descriptions, approval-burden metrics, and task-level completion evidence.
