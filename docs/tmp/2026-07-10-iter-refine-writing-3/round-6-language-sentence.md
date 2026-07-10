# Round 6 -- Language: Sentence Structure

Date: 2026-07-10

## What was checked

Checked `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` for Round 6 sentence-structure issues from `iter-refine-writing`: semicolons joining independent clauses, fragment-like paragraph openings, dense subject-verb distance, colon-heavy unlabeled lists, and long result paragraphs that read like experiment logs rather than claim-oriented evidence.

The read-only reviewer focused on the abstract, introduction, four-owner definition, safe-merge definition, runtime lowering, E3 multi-boundary results, related work, and conclusion.

## Findings

Must-fix:

- Abstract combined the E3 evidence and owner/lifecycle implication with a semicolon, making the result sound like a run log rather than a claim.
- Introduction used a note-like three-failure sentence rather than a readable sequence.
- The four-owner definition paragraph packed ownership roles, non-taxonomy scope, issuer differences, and delegation into one dense sentence chain.
- The safe-merge paragraph joined field-property definitions and the semantic obligation in one long sentence.
- The E3 aggregate paragraph mixed coverage, de-duplication, numbers, and evidence boundary in one paragraph.

Should-fix:

- Contribution list, motivation, implementation lowering, evaluation opening, E3 paragraph openers, related-work boundary argument, and conclusion had several long semicolon-linked sentences.
- Several English paragraph openers in E3 made the Chinese paper read unevenly.

Consider:

- Keep all experimental numbers unchanged in this language round.
- Preserve explicit evidence boundaries so the paper does not overclaim benchmark-scale utility or production ActPlane/MCP deployment.

## Changes Made

- Split the abstract result sentence into an E3 boundary result and a separate owner/lifecycle implication.
- Rewrote the introduction's three missing runtime properties as "第一/第二/第三" sentences.
- Split the four-owner definition into shorter role statements and clarified that delegation is a compound protected decision, not a fifth owner.
- Split the safe-merge definition into source attributes, semantic obligation, and the conservative equality condition.
- Rewrote runtime lowering to make the shared checker transition and boundary-specific projections explicit.
- Rewrote implementation lowering to separate monitor-shaped policy evidence from the production ActPlane/eBPF boundary.
- Recast the evaluation opening around E1/E2/E3 claim dependency rather than script order.
- Replaced English E3 paragraph openers with Chinese claim-oriented openers.
- Split E3 cross-boundary aggregation into three paragraphs: system-contract conclusion, de-duplicated counting scope, and evidence boundary.
- Split the related-work counterargument into a convergence condition and a missing-lifecycle condition.
- Split the conclusion into the problem shift, current evidence, and final takeaway.

## Verification Notes

- Diff audit found no intended quantitative-result changes. Number-related diff hits were punctuation or wording changes around existing numbers.
- Remaining expected risk: dense tables may still create LaTeX overfull/underfull warnings; this round did not redesign tables.
- Next writing round should be Round 7 word choice, with attention to repeated compound terms such as `protected-decision`, `owner/lifecycle`, and `pre-effect commit record`.
