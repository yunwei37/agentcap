# Round 2: Section Conventions

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 2, using `check-paper-structure-flow` section-convention criteria for a full systems paper. Focus: abstract/intro role alignment, design goals and overview, evaluation setup and research-question mapping, related-work grouping, and conclusion structure.

## Findings

Must fix:

- The evaluation opening promised three primary experiments plus a supporting audit, but the supporting audit text was embedded inside E1. This made E1 appear to carry two research questions.
- The conclusion ended by restating missing production runtime, end-to-end utility, and OS-level enforcement evidence. That content belongs in limitations, not the closing paragraph.

Should fix:

- Keep the evaluation subsections aligned to the table rows: E1, E2, E3, and Support should each have their own visible subsection.
- Close the paper with the paper's thesis and bounded evidence, not with future-work or limitation language.

Consider:

- Related work still uses two adjacent comparison tables. This may be acceptable for the current long Chinese draft, but a later layout pass should decide whether one table plus prose is enough.
- The introduction still has more paragraphs than a strict 12-page English submission would likely allow. A later abstract/intro rebuild pass should compress it only after the claim/evidence boundary is stable.

## Changes Made

- Moved the lease-audit paragraphs out of E1 into a separate `Support: Lease Auditability` subsection after E3.
- Left all quantitative results unchanged.
- Rewrote the conclusion's final sentence so it restates the thesis and bounded evidence instead of reopening the limitations.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R254PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R254PAPERAUDIT`
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

- This pass did not merge the two related-work comparison tables.
- This pass did not compress the long introduction; that should happen in the dedicated abstract/intro rebuild round so the causal argument is rewritten as a unit.
