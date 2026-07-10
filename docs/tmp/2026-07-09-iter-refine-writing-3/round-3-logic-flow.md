# Round 3: Logic Flow

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 3, using senior systems reviewer logic-flow criteria. Focus: whether the paper's evidence story reads as a coherent argument rather than a collection of experiments, and whether the claim tone matches the current evidence.

## Findings

Must fix:

- The evaluation opening listed E1, E2, and E3, but did not explicitly state their dependency order. A reviewer could read the experiments as independent fragments rather than a staged argument: non-vacuous event model, mechanism necessity, then multi-boundary execution.
- The limitations closing sentence used `证明的是` for an empirical, boundary-limited result. This was stronger than the evidence warrants and risked implying a formal or end-to-end proof.

Should fix:

- Make the evaluation logic explicit before the per-experiment subsections.
- Calibrate the final limitations sentence so it states the supported property without overclaiming full workload utility, expert minimality, or production enforcement.

Consider:

- A later abstract/intro rebuild should make the same dependency order visible earlier in the paper.
- Related work and limitations still repeat some equivalence-boundary language; a later consistency pass should check whether those repetitions are all load-bearing.

## Changes Made

- Added a sentence in the evaluation opening that orders the experiments by claim dependency: E1 avoids vacuous safety, E2 tests issuer/lifecycle necessity, and E3 tests local multi-boundary enforcement.
- Replaced the limitations closing phrase `\sys 证明的是 ...` with a calibrated statement that current results support a property over instrumented protected-decision events and expose issuer/lifecycle collapse false-accept paths.
- Left all quantitative results unchanged.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R255PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R255PAPERAUDIT`
  - Passed 78/78 checks.
  - `no_dataset_sync: true`
  - `not_a_model_run: true`
  - `not_a_new_experiment: true`
- `(cd docs/autopaper && latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex)`
  - Passed.
- `rg -n "Undefined|LaTeX Warning: Reference|Citation .* undefined|Overfull|Fatal|Error" docs/autopaper/intentcap-paper-zh.log`
  - No matches.
- `PYTHONPATH=src python3 -m pytest tests/test_audit_paper_evidence_numbers.py tests/test_build_e1_matched_online_comparison.py tests/test_analyze_e3_typed_provenance_baseline.py tests/test_lower_env_leases_actplane.py -q`
  - Passed 4/4 tests.
- `git diff --check`
  - Passed.

## Remaining Concerns

- This round did not restructure the introduction.
- This round did not change the evidence boundary or add new experiments; it only made the existing logic chain clearer.
