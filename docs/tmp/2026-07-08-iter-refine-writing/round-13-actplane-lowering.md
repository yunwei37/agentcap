# Round 13: ActPlane-Style Env Lowering

Date: 2026-07-08

## What Was Checked

This round checked whether the env/local-execution lease contract can be lowered into a deterministic OS-monitor-shaped policy without collapsing IntentCap's four authority-input model into object/path checks.

## Implementation

Added `scripts/lower_env_leases_actplane.py`.

The script reads `examples/env_adapter_side_effect_suite.json`, extracts active env leases, and emits a deny-by-default ActPlane-style policy with rules for:

- `process.exec`
- `filesystem.read`
- `filesystem.write`
- `context.use`

The generated policy includes operation/object/holder/argument constraints, invocation budget, control/data provenance constraints, and context-label influence predicates.

Added `tests/test_lower_env_leases_actplane.py`.

## Run

Command:

```bash
python3 scripts/lower_env_leases_actplane.py --trace examples/env_adapter_side_effect_suite.json --output-dir results/eval/R218ACTLOWER --run-id R218ACTLOWER
```

Result summary:

- Events: 10
- Lowered rules: 4
- Checker allowed / blocked: 4 / 6
- Monitor allowed / blocked: 4 / 6
- Decision mismatches: 0
- Checker-allowed monitor denials: 0
- Unsafe monitor allows: 0
- Input trace SHA-256: `a1d5fa355deb0a837e8d5848467bcfbb02697ddff9b94ca5fa4a48fb8e3fdccf`
- Script SHA-256 in run summary: `5e2bacab0290db68c27439a86fad0428be4f961315391e689f3233aff963fe66`

## Claim Boundary

R218 supports an E4 system-boundary claim: the same IntentCap env lease contract can be represented as a deny-by-default monitor policy target while preserving context-label and influence checks.

R218 does not support a production OS enforcement claim. It is not a kernel, seccomp, Landlock, or production ActPlane integration. The next production-backend gate is to enforce the same contract in a real sandbox or ActPlane-style runtime and measure mediation coverage and overhead.

## Paper Changes

Updated:

- `docs/autopaper/intentcap-paper-zh.tex`
- `docs/evaluation.md`
- `docs/implementation.md`
- `docs/design.md`
- `docs/idea-story.md`
- `docs/background-related-work.md`

The paper now treats R218 as E4 evidence, not as a new experiment block. The four main experiment blocks remain E1 safety/utility proxy, E2 lease audit, E3 mechanism necessity, and E4 system-boundary practicality.
