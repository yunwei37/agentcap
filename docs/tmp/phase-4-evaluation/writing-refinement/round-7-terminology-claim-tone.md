# Round 7: Terminology and Claim Tone

## Reviewer Focus

Audited terminology and claim tone. The goal was to keep the core English technical terms that matter for the paper, while reducing overly defensive or overly absolute wording.

## Fixes Applied

1. Replaced `novelty claims` in the abstract with `novelty statement`.
2. Replaced `论文必须放弃...` with a narrower conditional formulation: if the strongest baseline explains all denials, the paper should narrow the claim to proof-carrying lease compiler/checker organization.
3. Replaced `论文必须把它写成...` with `论文应把它写成...` for semantic baseline variants.
4. Changed the evidence table caption from `不能单独写成` to `尚不足以单独支撑`.
5. Rephrased the claim boundary around context-influence residuals so it says \sys should emphasize lease lifecycle organization unless residuals survive strong baselines.
6. Replaced `不能声称 intent/provenance authorization 本身是新的` with a positioning statement: the paper does not use that as the novelty claim.
7. Replaced `不应被写成第一个 agent permission system` with a clearer positioning statement: \sys is not positioned as the first agent permission system.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The claim tone is now more defensible. Round 8 should do a final flow/polish pass across transitions and conclusion so the paper reads as one argument rather than a sequence of safeguards.
