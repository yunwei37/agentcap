# Round 6: Language, Sentence Structure

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 6, using `paper-writing-style` sentence-structure checks. Focus: semicolons joining independent clauses, colon-as-claim patterns, overlong sentences, and vague connective structure in the abstract and introduction.

## Findings

Must fix:

- The abstract results sentence used semicolons to join three independent result clauses.
- Several introduction sentences used semicolons or colons for `claim: explanation` structure instead of causal or separate sentences.
- The system paragraph introduced four proof classes, the system API, compiler trust boundary, adapter lowering, and the running example in one long sentence cluster.

Should fix:

- Split independent clauses in the abstract and introduction into separate sentences.
- Replace non-list colons with direct causal phrasing.
- Keep the intro's role order from Round 4 while reducing sentence-level load.

Consider:

- Broader sentence cleanup is still needed in later sections, but this round prioritized the paper opening because it carries the main reviewer first impression.

## Changes Made

- Split abstract result clauses into three result sentences.
- Replaced independent semicolon joins in the intro with periods.
- Rewrote `claim: explanation` patterns around approval-widening variants, issuer collapse, authority-state split, and the bounded safety claim.
- Split the system paragraph so the four proof classes, `check_and_consume`, compiler trust boundary, runtime adapters, and PDF workflow example are separate sentences.
- Left all numbers, citations, section labels, and claims unchanged.

Number of sentences changed: 9.

Categories of changes:

- Semicolon removal.
- Colon pattern cleanup.
- Long-sentence splitting.
- Vague connective replacement.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R259PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R259PAPERAUDIT`
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

- Later language rounds should inspect the evaluation and related-work sections for the same semicolon/colon patterns.
- Some short definitional sentences in the system paragraph were intentionally kept because they clarify proof-class ownership.
