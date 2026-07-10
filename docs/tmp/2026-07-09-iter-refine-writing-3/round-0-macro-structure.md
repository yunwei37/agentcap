# Round 0 - Macro Structure

Date: 2026-07-09

Paper: `docs/autopaper/intentcap-paper-zh.tex`

## What Was Checked

This round applied the `iter-refine-writing` macro-structure guidance after a read-only macro review of the Chinese IntentCap paper. The review focused on section ordering, table density, design/implementation separation, formal-model readability, and whether the evaluation reads as a small number of claim-facing experiments rather than an experiment log.

## Findings

Must-fix findings from the macro review:

- The four-context discussion had too many overlapping tables. The running-example table, collapse table, authority-input table, owner-class table, and decision-requirement table repeated the same idea at different abstraction levels.
- The formal model was technically rich but under-sectioned. Events, owner projections, equivalence conditions, lease lifecycle, and safety properties were all in one long section.
- The implementation section read like an artifact inventory. Two adjacent tables listed components and adapter surfaces separately instead of explaining the implemented contract surfaces.
- The evaluation organization exposed E1/Audit/E3/E4, with no E2 and with the audit appearing as a peer to the main experiments. The paper needed three core experiments plus supporting audit evidence.

Should-fix findings applied in this round:

- The E3/E4 numbering drift should be fixed everywhere visible to readers.
- E3 result prose should not read like a chronological list of small experiments.
- Internal labels should follow the new visible E2/E3 structure where practical.

## Changes Made

- Reduced context-boundary tables:
  - Removed the running-example context-boundary table.
  - Removed the class-collapse consequence table.
  - Removed the broad authority-input taxonomy table.
  - Kept the workload-derived owner-class table and the per-decision requirement table as the two core tables.

- Reorganized the formal model:
  - Added `Events and Proof Projections`.
  - Added `Issuer Ownership and Safe Merge`.
  - Replaced the run-in `Equivalence rule` paragraph with `Equivalence Boundary`.
  - Added `Lease Lifecycle and Commit Semantics`.
  - Kept `Safety Properties` as the final formal-model subsection.

- Rebuilt the implementation surface:
  - Replaced the artifact-components table and adapter-surface table with one `Implemented contract surfaces` table.
  - Reframed implementation around the commit record, block point, evidence role, and implementation status.
  - Clarified that OS-monitor-style lowering is a replay target, not production ActPlane integration.

- Reorganized evaluation:
  - E1 is now event-model feasibility and reference-action coverage.
  - E2 is now mechanism necessity: issuer ownership and lifecycle commit.
  - E3 is now local multi-boundary adapter practicality.
  - Lease auditability is now `Support`, not a fourth core experiment.
  - Removed visible E4 references.
  - Rewrote E3 result prose around three claims: pre-side-effect blocking, shared placement/handoff commit point, and monitor-lowering equivalence.

## Verification

- `PYTHONPATH=src python3 scripts/audit_paper_evidence_numbers.py --run-id R252PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R252PAPERAUDIT`
  - Passed: 78/78 checks.
  - The audit reports `no_dataset_sync: true`, `not_a_model_run: true`, and `not_a_new_experiment: true`.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
  - Passed.
  - No undefined references, undefined citations, overfull boxes, fatal errors, or LaTeX errors were found in the checked log patterns.
- `PYTHONPATH=src python3 -m pytest tests/test_audit_paper_evidence_numbers.py tests/test_build_e1_matched_online_comparison.py tests/test_analyze_e3_typed_provenance_baseline.py tests/test_lower_env_leases_actplane.py -q`
  - Passed: 4/4 tests.
- `git diff --check`
  - Passed.

## Remaining Concerns

- Related work still has two comparison tables. A later writing round should decide whether both are needed or whether one can move to an appendix.
- The Chinese paper is still longer than a final top-conference paper. Later writing rounds should compress background and related work after claims and evaluation stabilize.
- The current evidence boundary is intentionally conservative. Stronger claims still require production MCP/ActPlane integration, independent expert adjudication, and larger online utility/recovery experiments.
