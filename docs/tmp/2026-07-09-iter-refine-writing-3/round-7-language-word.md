# Round 7: Language, Word Choice

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 7, using `paper-writing-style` word-choice checks. Focus: project-report phrasing, vague result subjects, and weak status-update openings.

## Findings

Must fix:

- Several sentences used vague subjects such as `这个结果` or `当前原型`, which made the prose read like a progress report rather than a paper argument.

Should fix:

- Replace vague result subjects with the actual evidence object, such as `该切片`, `这些结果`, or `这些 checks`.
- Remove unnecessary `当前` when the surrounding section already scopes the claim to the present prototype or evaluation.

Consider:

- Full word-choice cleanup across the 42-page Chinese draft would be larger than this round. This pass focused on high-impact, low-risk replacements.

## Changes Made

- Replaced abstract `当前评估` with `评估`.
- Replaced intro `当前原型的评估目标` with `原型评估目标`.
- Replaced `这个 TCB statement` with `TCB 边界`.
- Replaced implementation `当前原型还包含` with `原型还包含`.
- Replaced `这个结果支持的结论很窄` with `该切片只支持一个窄结论`.
- Replaced E3 and support-audit `这个结果说明/支撑` phrasing with more specific subjects.

Number of sentences changed: 7.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R260PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R260PAPERAUDIT`
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

- The next terminology/claim-tone pass should handle invented compound terms and self-attacking phrasing more systematically.
