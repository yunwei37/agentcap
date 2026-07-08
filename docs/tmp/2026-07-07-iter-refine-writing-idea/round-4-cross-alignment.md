# Round 4: Cross-Alignment

Date: 2026-07-07

## What Was Checked

Round 4 checked whether problem statement, insight, threat model/goals, four-context design, formal model, implementation boundary, E1--E4 evaluation, related work, and conclusion tell one coherent story.

## Findings

The reviewer judged the main story coherent: the problem is context privilege; the insight is that protected decisions are authority-state transitions; the design is a four-input authorization transaction; the formal model has lease lifecycle and no-promotion; E1 is end-to-end outcome and E3 is mechanism proof. The paper no longer reads like a simple EIM/bpftime/ActPlane variant.

Must-fix findings:

- `Env context` was described as including lease state / lease consumption state, which conflicted with the formal checker state \(\sigma\).
- C2 still needed a hard system landing point for env/local side effects.
- C3 remains a research-stage evidence boundary, not a final top-conference results contribution.

Should-fix findings:

- E3 should explicitly state that it is not a task-utility experiment.
- ActPlane should remain an optional backend, but the paper should connect it to local script/process/network side effects.

## Changes Made

- Removed lease state and lease consumption state from `C_env` and the Env adapter description; lease tables and counters now belong only to checker state \(\sigma\).
- Added `examples/env_adapter_side_effect_suite.json`, a representative env/local side-effect trace covering local exec, fs.read, fs.write, script-output promotion, and net.connect.
- Added a test for the env side-effect suite in `tests/test_analyze_checker_ablation.py`.
- Ran `scripts/analyze_checker_ablation.py` as R210E3ENV. Full checker preserves 4 authorized side effects and rejects 6 violations; object-only false-accepts 4, lease-constraints/no-provenance false-accepts 2, and full-event-args/no-provenance false-accepts 6.
- Updated the Chinese paper and `docs/evaluation.md` to report R210 as trace-level ActPlane-style env event evidence, not production OS enforcement.

## Remaining Concerns

- R210 is still event-level env evidence, not a real ActPlane or sandbox backend.
- Final C3 must become a quantitative result contribution once E1--E4 are complete.
