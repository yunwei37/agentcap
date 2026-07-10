# Round 1: Micro Structure

Date: 2026-07-09

Skill workflow: `iter-refine-writing`, Round 1. A read-only reviewer pass focused on paragraph roles, duplicated thesis statements, section load-bearing sentences, and whether evaluation prose read like a paper rather than a run log.

## Findings

Must fix:

- The abstract was too dense and introduced too many core terms at once.
- The introduction contained two thesis paragraphs that repeated the policy-DSL equivalence point.
- The intro evidence paragraph read like an experiment summary instead of a claim-facing proof sketch.
- The authorization-input subsection overloaded definition, env rationale, safe merge, and falsifier logic in one block.
- The formal model still stacked definitions around owner projections, typing, and equivalence.

Should fix:

- Background subsections needed load-bearing sentences explaining why the section matters.
- The design overview needed to transition directly into the pre-effect checker transition.
- Implementation contained duplicate "implemented surface" roles.
- E2's opening paragraph mixed setup, baselines, and strongest-counterargument framing.
- Evaluation prose exposed historical run ids and made the section look like a lab notebook.

Consider later:

- Related work still has two table-like comparison blocks and may need a single sharper synthesis.
- Limitations can be made less self-attacking by grouping missing evidence by claim extension.

## Changes Made

- Rewrote the abstract into a four-beat structure: problem, mechanism, system, and bounded evidence.
- Collapsed the introduction's policy-DSL discussion into one runtime-commit-object thesis.
- Replaced the intro evidence run-log paragraph with three claim-facing sentences for E1, E2, and E3.
- Added load-bearing sentences to the background subsections on agent extensions and provenance.
- Reframed the design overview around the pre-effect checker transition and audit commit id.
- Split the authorization-input explanation into definition, env rationale, safe-merge criterion, and falsifier paragraphs.
- Tightened the formal-model discussion of owner projections, typed proof obligations, equivalence boundary, and lease lifecycle.
- Removed the duplicate implementation-surface subsection role.
- Split E2's setup from its baseline description.
- Replaced visible historical run-id prose with semantic labels such as "authority traces", "workflow residuals", and "typed-provenance baseline suites".

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R253PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R253PAPERAUDIT`
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

- This pass improved micro structure but did not run a full citation audit or related-work merge.
- The evaluation still deliberately reports bounded evidence rather than benchmark-scale utility, expert-oracle lease scoring, or fresh online API/model conclusions.
- The next writing pass should focus on section conventions: whether each major section opens with the right promise, closes with the right takeaway, and avoids re-proving earlier points.
