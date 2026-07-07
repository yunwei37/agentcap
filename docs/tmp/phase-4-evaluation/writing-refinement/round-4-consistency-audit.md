# Round 4: Consistency Audit

## Reviewer Focus

Audited cross-section consistency after the structure and logic passes. The goal was to ensure the same claim boundaries, system maturity, and core terms are used in Abstract, Introduction, Threat Model, Design, Implementation, Evaluation, Discussion, and Related Work.

## Issues Found

1. The running example used the literal name `IntentCap` instead of the paper macro `\sys`.
2. The Discussion mixed `artifact` and `prototype evidence`, while the implementation section now frames the system as a prototype.
3. E1 and E3 used `完整 \sys`, which could be misread as a production-complete system rather than the evaluated full-mechanism checker configuration.
4. E4 used `artifact gap`, while adjacent sections now use prototype/evidence boundary language.

## Fixes Applied

1. Replaced the naked `IntentCap` occurrence with `\sys`.
2. Changed `已有 artifact` to `已有 prototype evidence`.
3. Replaced `完整 \sys` with `evaluated \sys configuration` in E1 and `full-mechanism \sys checker` in E3.
4. Replaced `artifact gap` with `prototype gap`.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The terminology is now more consistent, but the prose still uses many English technical nouns inside Chinese sentences. The next rounds should improve sentence structure, word choice, and readability without weakening the calibrated claims.
