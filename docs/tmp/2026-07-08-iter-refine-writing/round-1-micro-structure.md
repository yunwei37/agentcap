# Round 1: Micro Structure

Date: 2026-07-08

## What Was Checked

Round 1 checked paragraph roles and local flow in `docs/autopaper/intentcap-paper-zh.tex`: abstract beats, introduction role separation, section paragraph purpose, evaluation subsection shape, and whether the prose reads like a paper rather than an internal project tracker. The read-only reviewer used `check-paper-structure-flow` with Level 2-3 micro-structure focus and checked the `iter-refine-writing` common pitfalls.

## Findings

Must-fix findings:

- Abstract read like a paper status report. The last sentence mixed pilot evidence, E1--E4 gaps, and incomplete conclusions.
- Introduction compressed the key insight, transaction API, lease semantics, baseline distinction, and compiler/checker architecture into two long paragraphs.
- Contribution C3 and Evaluation used project-tracker wording such as "full-paper scaffold", "should/must/needs", and "最终论文应".
- Evaluation E1--E4 were written as experiment plans rather than paper experiments with question, setup, metric, and interpretation.
- Evidence Boundary table used a "Supports / Not yet supports" structure that looked like a gap list.
- Formal Model had a long lease lifecycle paragraph containing multiple ideas.

Should-fix findings:

- Intro scope paragraph interrupted the causal chain.
- System Overview mixed architecture walkthrough with novelty/evaluation claim.
- Design Goals repeated contribution/evaluation mapping already present in the goal table.
- Authority Inputs and Formal Model repeat the four context planes; this remains for a later tightening pass.
- Implemented Surface read like an artifact README.

Consider findings:

- `Property N` subsection titles added too much heading noise.
- Related Work has defensive baseline equivalence wording. This remains for later logic/consistency rounds.
- Global Chinese/English terminology density remains high. This is intentionally deferred to language rounds.

## Changes Made

- Rewrote the abstract into six short beats: context, problem, system insight, lease mechanism, checker/adapters, and bounded pilot results.
- Split the introduction insight into separate paragraphs for problem boundary, transaction-interface requirement, lease abstraction, and compiler/checker architecture.
- Replaced contribution C3 with "Evaluation methodology and pilot evidence", removing "full-paper scaffold" and "最终论文应" wording.
- Reworked `System Overview` so it walks through issuer, labeler, compiler, checker, and adapters.
- Simplified `Design Goals` so each item states only the goal; the mapping remains in the table.
- Split the lease lifecycle formal paragraph into guard failure, stateful lease object, and atomic transition/state fields.
- Split `Implemented Surface` into checker/gateway, env/model-loop probes, and unsupported production boundaries.
- Rewrote Evaluation intro, methodology, and E1--E4 into paper-style experiment questions and metrics instead of proposal notes.
- Changed Evidence Boundary table columns from `Supports / Not yet supports` to `Evidence / Boundary`.
- Replaced four `Property N` subsections with one `Safety Properties` subsection and a numbered list.
- Removed remaining `full-paper`, `当前稿`, `最终论文`, `TODO`, and `Not yet supports` markers from the paper source.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex` from `docs/autopaper`.
- Checked the LaTeX log for undefined citations, undefined references, LaTeX warnings, and overfull boxes; no matching warnings were found.
- Checked that project-tracker phrases no longer appear in the paper source.
- Cleaned generated LaTeX artifacts before committing.

## Remaining Concerns

- Evaluation still contains methodology and pilot evidence, not the completed E1--E4 benchmark package.
- Authority Inputs and Formal Model still repeat some four-plane definitions; the next structure/convention rounds should reduce redundancy without deleting technical content.
- Related Work still contains some defensive phrasing around semantic-equivalent baselines.
- Sentence-level issues remain, especially semicolon-heavy bilingual prose and dense coined terms; those belong to later language rounds.
