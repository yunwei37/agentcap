# Round 5: Reviewer Stress Test

Date: 2026-07-08

## What Was Checked

Round 5 stress-tested whether a skeptical systems reviewer can still reject the paper as "just EIM/bpftime/ActPlane/policy synthesis" or as an agent-security idea without a system boundary. The check focused on the current Chinese paper, the four-context authorization model, the formal no-promotion property, the implementation status table, and E1--E4.

## Findings

The strongest novelty rejection is no longer that the model is merely MCP/tool-call access control. The paper now has a defensible center: protected agent decisions are authority-state transitions, and each transition must be checked over four independent context inputs: agent, instruction, tool, and env.

The reviewer could still construct an evidence-based rejection if the paper overclaims. The most important remaining risks were:

- C3 cannot be a final contribution until E1--E4 produce claim-facing numbers; it should remain an evidence boundary for now.
- R210 was useful but only trace-level. The system needed a real env adapter probe where a local script/file operation would actually execute under a weaker policy and be blocked before side effects under IntentCap.
- E1 still needs a broader matched online model/task-loop result before the paper can claim end-to-end security plus utility.
- E2 labels are author-adjudicated unless independently replicated.

## Changes Made

- Added `scripts/run_env_backend_side_effect_probe.py`, a local env backend probe that runs the R210 env/local event suite in isolated IntentCap and object-only fixtures.
- Added `tests/test_run_env_backend_side_effect_probe.py` to assert the side-effect behavior directly.
- Ran `results/eval/R211ENVBACKEND/`: IntentCap executes 4 authorized effects, blocks 6 denied events before side-effect handlers, executes 0 unsafe effects, keeps the isolated secret file unchanged, and creates no wrong-output file. The object-only backend executes 8 effects, including 4 unsafe effects, writes the wrong output, and modifies the isolated `secrets.env`.
- Updated `docs/autopaper/intentcap-paper-zh.tex` so the system contribution and adapter table say "local env pre-side-effect probe" rather than only "trace-level env suite".
- Updated `docs/evaluation.md` to distinguish R210 semantic ablation from R211 real local backend evidence, while preserving the boundary that R211 is not a production ActPlane/kernel monitor.

## Remaining Concerns

- R211 closes the "no real env backend" stress-test gap, but it is still an isolated local probe. It does not replace production sandbox or OS-level enforcement.
- The next highest-value experiment is a broader matched online E1 run or an E3 residual lift into an existing benchmark/model loop.
- Only after those evidence gaps narrow should `iter-refine-writing` move from claim/framing fixes into prose polish.
