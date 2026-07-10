# 2026-07-10 Iter-Refine-Writing-Idea Round 1

## What Was Checked

Round 1 checked the problem framing of `docs/autopaper/intentcap-paper-zh.tex` after the R281 pairwise owner-merge coverage update. The review focused on the abstract, introduction, motivation, design goals, four-context framing, and E2 merge-coverage wording.

## Findings

Read-only reviewer `019f4b41-29d9-7f20-80c5-06315d7d5a9b` reported four must-fix issues:

- The running example mixed delegation, stale reuse, approval widening, and policy update, making the minimal failure trace harder to see.
- The root cause named issuer collapse and authority-state split, but did not directly connect the four proof owners to authority root, procedure endorsement, interface contract, and runtime observation.
- The problem characterization used `checker-denied events`, which could look circular because the paper is evaluating the checker's categories.
- The non-adversarial motivation implied approval-burden and false-denial claims that the current main evidence does not carry.

The reviewer also flagged that the new `6/6 tested pairwise owner-merge families` wording could be misread as global taxonomy minimality.

## Changes Made

- Rewrote the introduction's PDF-to-issue example into a minimal trace: user authorizes one issue, PDF may affect issue body, PDF induces authority transfer/reuse, repo argument remains legal, and one-shot authority is still violated.
- Replaced the two-root-cause framing with three structural mismatches: authority-root collapse, procedure/interface/observation collapse, and authority-state split.
- Added the direct mapping from those mismatches to the four proof owners: agent-owned authority root, instruction-owned procedure endorsement, tool-owned interface contract, and env-owned runtime observation.
- Reworded non-adversarial motivation as a union-authority granularity problem instead of promising approval-burden or false-denial results.
- Changed problem characterization and E2 evidence-boundary wording from `checker-denied` to `protected-decision-oracle-denied`.
- Changed owner merge from `命题 1` to `判据 1（owner merge counterexample criterion）` and emphasized that E2 instantiates this criterion in artifacts and controlled suites.
- Reworded the R281 merge-coverage result as coverage over the six pairwise merge removals under tested adapter surfaces, not a proof of global taxonomy minimality or every three-class design being unsafe.
- Changed the abstract's `OS-monitor-style replay target` phrasing to `deterministic replay target` and explicitly said it is not a production OS monitor.
- Strengthened contribution C3 from `Evaluation methodology and evidence` to `Evaluation evidence`.

## Verification

- `python3 -m pytest tests/test_audit_paper_evidence_numbers.py -q`: passed.
- `python3 scripts/audit_paper_evidence_numbers.py --run-id R283PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R283PAPERAUDIT`: 104/104 checks passed.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`: passed.

## Remaining Concerns

This round completed problem-framing fixes only. The full idea-refinement loop still needs Round 2 novelty attack/defense, Round 3 contribution/design-goal review, Round 4 cross-alignment, and Round 5 reviewer stress test. The paper still should not claim natural prevalence, global taxonomy minimality, independent expert minimality, production OS/ActPlane integration, or benchmark-scale utility/recovery.
