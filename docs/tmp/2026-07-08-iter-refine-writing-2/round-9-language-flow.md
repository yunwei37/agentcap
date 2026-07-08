# Round 9 - Language Flow and Polish

Date: 2026-07-08

## Findings

### Must-fix

1. The evaluation opening still read partly like an experiment inventory. It named E1/E3/E4 before stating the question each experiment answers.
2. The terminology cleanup from Round 8 left two stale metric phrases, `dangerous accept` and `dangerous executes`, which conflicted with the paper's `unsafe accept` / `unsafe execution` definitions.
3. The E4 table used the note-like phrase `not prod. ActPlane`, which looked like an internal caveat rather than paper prose.

### Should-fix

1. The introduction paragraph explaining why the model has four authority-input classes did not first state why three classes are insufficient.
2. Several evaluation paragraphs opened with the artifact or test name rather than the claim being tested.
3. A local environment result sentence mixed the positive boundary claim with a negative production-sandbox caveat.

### Consider

1. Keep the remaining limitation statements, because they are scope-bearing and prevent the evaluation from implying end-to-end utility, production ActPlane integration, or independent expert-oracle least privilege.

## Changes Made

- Reordered the introduction's four-class paragraph to lead with the three-class insufficiency claim before listing `agent`, `instruction`, `tool`, and `env`.
- Rewrote the evaluation opening around claim questions rather than experiment labels.
- Replaced stale `dangerous` metric names with `unsafe accept` and `unsafe executions`.
- Reworded E1, E3, and E4 result paragraphs so they state the claim boundary before the run details.
- Replaced `not prod. ActPlane` in the E4 table with the neutral scope label `replay only`.
- Rephrased the local env boundary paragraph as a positive pre-side-effect contract result, leaving production sandbox/ActPlane caveats to the evidence-boundary section.

## Remaining Concerns

- The paper still deliberately mixes English technical terms with Chinese prose; this is consistent with the current draft but should be revisited if the final venue requires a fully English paper.
- The evaluation remains evidence-bounded. It supports protected-decision safety and local multi-boundary enforceability, but not yet full online task utility, approval burden reduction, production ActPlane mediation, or independent expert-oracle minimality.
