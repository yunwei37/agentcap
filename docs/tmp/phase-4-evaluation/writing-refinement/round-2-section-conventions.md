# Round 2: Section Conventions

## Reviewer Focus

Checked whether each section plays a clean systems-paper role: Introduction motivates and states contributions, Background defines terms, Motivation carries the example, Design explains mechanisms, Formal Model states semantics and properties, Implementation describes artifact boundaries, Evaluation defines experiments, and Discussion separates evidence from final claim strength.

## Fixes Applied

1. Changed the third contribution from `Evidence` to `Evaluation` so the introduction does not present pilot evidence as a final result.
2. Replaced `当前结果` in the abstract with `Prototype evidence` to make the evidence status explicit.
3. Removed draft meta-language from the formal section by changing `Checker judgment 写作` to `Checker judgment is`.
4. Renamed the implementation subsection from `Artifact Boundary` to `Implemented Surface`, reserving evidence/claim boundaries for Discussion.
5. Renamed the Discussion subsection from `Artifact Boundary` to `Evidence Boundary`.
6. Renamed `最终 Claim Gate` to `Claim Selection` so the section reads as paper structure rather than project management notes.
7. Rephrased the opening of Discussion to separate prototype evidence from final claim strength without sounding like an apology.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Fixed-string checks found no remaining `\paragraph{}` headings and no stale `Artifact Boundary`, `尚不能支撑`, or `最终 Claim Gate` headings.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The structure is now cleaner, but the paper still has some mixed English/Chinese terminology and dense formal/evaluation paragraphs. Those belong to the later terminology and prose rounds.
