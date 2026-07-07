# Round 5: Sentence Structure

## Reviewer Focus

Improved local readability without changing technical claims. The main target was overlong sentences that bundled multiple roles: mechanism, evidence boundary, baseline fidelity, and claim selection.

## Fixes Applied

1. Split the introduction's context-privilege paragraph so the model/context flow and the guard limitation are separate sentences.
2. Split the design data-flow paragraph into certificate/labeling and compiler/checker/runtime phases.
3. Rewrote the formal checker judgment paragraph so each acceptance condition is a separate sentence rather than one long semicolon chain.
4. Split the implementation surface paragraph into implemented components and what those components support.
5. Split the evaluation introduction into experiment organization and shared methodology.
6. Split the E3 baseline paragraph into one sentence per checker variant.
7. Split the claim-selection paragraph into separate E1 and E2/E3/E4 claim gates.
8. Replaced two remaining `完整 \sys` phrases with `full-mechanism \sys checker`.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The draft is easier to parse, but word choice is still mixed and sometimes literal. Round 6 should focus on replacing project-management phrasing with paper-native phrasing while preserving conservative claims.
