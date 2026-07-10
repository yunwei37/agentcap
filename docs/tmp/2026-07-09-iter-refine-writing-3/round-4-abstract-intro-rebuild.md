# Round 4: Abstract / Intro Rebuild

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 4, using `rewrite-abstract-intro`. Focus: full-paper abstract and introduction role order, strict abstract-to-intro correspondence, and causal logic chain.

## Role Diagnosis

Current intro mapping before the edit:

- Paragraph 1: background/context.
- Paragraph 2: problem/example.
- Paragraph 3: root cause, but too long and mixed with design terminology.
- Paragraph 4: authority-input taxonomy plus evaluation number; this belonged mostly in design/evaluation, not the intro role chain.
- Paragraph 5: benign/non-adversarial importance; useful but redundant with motivation.
- Paragraph 6: existing solutions and limitations.
- Paragraph 7: key insight.
- Paragraph 8: relation to extension/sandbox work; better as part of existing-solutions limitations.
- Paragraphs 9-11: challenges plus system details and an intro-local commit-record table; too detailed for the intro.
- Paragraphs 12-13: evaluation and safety boundary.
- Paragraph 14: contributions.

Target mapping:

- Paragraph 1: background/context.
- Paragraph 2: problem and concrete failure example.
- Paragraph 3: root cause: issuer collapse and authority-state split.
- Paragraph 4: existing mechanisms and why they do not expose the needed commit object.
- Paragraph 5: key insight: pre-effect protected-decision transition.
- Paragraph 6: realization challenges: field ownership, checker-owned lifecycle state, and multi-boundary exposure.
- Paragraph 7: this paper/system: field-owned lease, four proof classes, `check_and_consume`, and adapter surfaces.
- Paragraph 8: evaluation results and bounded safety claim.
- Paragraph 9: contributions.

Abstract diagnosis:

- The abstract already had the right context/problem/system/results order.
- It was split into multiple LaTeX paragraphs by blank lines, violating the full-paper one-paragraph convention.

## Changes Made

- Compressed the introduction into the target role order.
- Removed the intro-local commit-record table and replaced it with one sentence explaining the PDF workflow proof obligations.
- Merged the evaluation and safety-boundary paragraphs so the intro closes the claim before listing contributions.
- Kept all intro citations and all paper-facing quantitative results unchanged.
- Removed blank lines inside the abstract so it is one LaTeX paragraph.

Content intentionally moved out of the intro:

- The `8,691/8,696` authority-input characterization detail remains in E2.
- The full commit-record mechanics remain in the design and formal sections.
- Detailed limitations remain in the scope/limitations section.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R257PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R257PAPERAUDIT`
  - Passed 78/78 checks.
  - `no_dataset_sync: true`
  - `not_a_model_run: true`
  - `not_a_new_experiment: true`
- `(cd docs/autopaper && latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex)`
  - Passed; final check reported nothing to do after the last text-only timestamp update.
- `rg -n "Undefined|LaTeX Warning: Reference|Citation .* undefined|Overfull|Fatal|Error" docs/autopaper/intentcap-paper-zh.log`
  - No matches.
- `PYTHONPATH=src python3 -m pytest tests/test_audit_paper_evidence_numbers.py tests/test_build_e1_matched_online_comparison.py tests/test_analyze_e3_typed_provenance_baseline.py tests/test_lower_env_leases_actplane.py -q`
  - Passed 4/4 tests.
- `git diff --check`
  - Passed.

## Remaining Concerns

- The introduction is now role-ordered, but paragraph 7 is still dense because it introduces the four proof classes and the system API together. A later language pass should split or tighten it without changing claims.
- The abstract is structurally aligned with the intro, but a later sentence-level pass should reduce mixed English/Chinese compound terms if the target venue requires a fully Chinese or fully English style.
