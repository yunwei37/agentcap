# Round 5: Consistency

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 5, using `audit-paper-consistency`. Focus: terminology drift across abstract, introduction, design, formal model, evaluation, limitations, related work, and conclusion.

## Findings

Must fix:

- The abstract introduced `field-owned lease`, while the rest of the paper's primary term is `field-owned protected-decision lease` or `protected-decision lease`. This could make the abstract look like it names a different object.
- The introduction used `transition`, `commit object`, and `commit record` without an explicit bridge. The body defines the relationship, but the opening should not force readers to infer it.

Should fix:

- Clarify at first use that the runtime-exposed linearization record for a protected-decision transition is the commit object.

Consider:

- Later terminology rounds should reduce repeated compound terms, but this consistency pass should not globally rename terms that are already defined.

## Changes Made

- Replaced abstract `field-owned lease` with `field-owned protected-decision lease`.
- Added one bridge sentence in the insight paragraph: the runtime-exposed linearization record is the commit object.
- Left all quantitative results and citations unchanged.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R258PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R258PAPERAUDIT`
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

- No architectural contradiction was found in this pass.
- The next language rounds should handle density and term frequency rather than consistency.
