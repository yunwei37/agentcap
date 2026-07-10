# 2026-07-10 Three-Class Merge Follow-Up

## What Was Checked

The previous four-context paper revision still had one explicit coverage gap in the three-class merge table: `instruction+tool` was marked as not separately isolated. That made the paper vulnerable to the reviewer objection that four owner classes might collapse to three if procedure text and interface metadata shared one proof channel.

## Finding

The existing aggregate traces already covered four pairwise merge families from R239, and local Skill placement covered `instruction+env` from R224. The missing case was `instruction+tool`, where Skill/manual procedure text and tool/callable schema metadata are merged.

## What Changed

- Added `examples/three_class_merge_coverage_suite.json` with two fixed-shape controlled cases:
  - signed Skill instruction supplying a tool-owned executable/interface proof;
  - tool schema metadata supplying an instruction-owned trusted workflow slot.
- Added `scripts/analyze_three_class_merge_coverage.py` and `tests/test_analyze_three_class_merge_coverage.py`.
- Generated `results/eval/R281MERGECOV/`.
- Updated `docs/autopaper/intentcap-paper-zh.tex` so the three-class merge table now reports `instruction+tool` as `2/2 controlled false accepts; full checker 0/2 unsafe accepts`.
- Updated `scripts/audit_paper_evidence_numbers.py` so future paper-number audits check the R281 paper-facing tokens.
- Updated `docs/evaluation.md` with the R281 source addendum, tracker row, and reproducibility checklist entries.

## Remaining Concerns

R281 is coverage over tested pairwise owner-merge families. It is not a natural prevalence estimate, not a benchmark-scale distribution claim, and not a proof that the four-owner taxonomy is globally minimal over every possible agent runtime. The paper should keep that boundary explicit.
