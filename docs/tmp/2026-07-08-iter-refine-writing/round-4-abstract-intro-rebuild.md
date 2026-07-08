# Round 4: Abstract/Intro Rebuild

Date: 2026-07-08

## What Was Checked

Round 4 used the `rewrite-abstract-intro` skill procedure. I read `references/abstract-intro-structure.md`, mapped the existing abstract and introduction to the systems-paper role template, rewrote the introduction paragraph by paragraph, then derived the abstract from the revised introduction. Numbers were treated as read-only and kept consistent with the body.

## Mapping Diagnosis

Existing abstract:

- Sentence 1: context.
- Sentence 2: problem.
- Sentence 3: insight.
- Sentence 4-5: system/mechanism.
- Sentence 6: result numbers.

Existing introduction:

- Paragraph 1: background/context.
- Paragraph 2: problem example.
- Paragraph 3: root cause and context privilege.
- Paragraph 4: four context classes, but this detail belonged later in design.
- Paragraph 5: scope/protected decision definition.
- Paragraph 6: existing solutions and residual gap.
- Paragraph 7: insight.
- Paragraph 8: challenge.
- Paragraph 9: lease mechanism.
- Paragraph 10: system architecture.
- Paragraph 11: contributions.

Diagnosis:

- The intro had all required roles, but the four-context definition and protected-decision scope were too detailed for the opening.
- The insight, challenge, lease mechanism, and system paragraphs were adjacent but not cleanly separated by role.
- The abstract had the right broad order, but it did not explicitly state the concrete consequence before the insight.

## Reorganization Applied

- Abstract now follows context → problem → consequence → insight → mechanism → result.
- Intro paragraph 1 remains background/context.
- Intro paragraph 2 is now the concrete failure trace and consequence only.
- Intro paragraph 3 is root cause: context privilege and action-time guard timing.
- Intro paragraph 4 is existing solutions and residual gap.
- Intro paragraph 5 is key insight: protected-decision transition as authorization unit.
- Intro paragraph 6 is technical challenge: field ownership, provenance, consumption, expiry, and delegation must be checked together.
- Intro paragraph 7 is system: intent-carrying leases, four issuer-typed context classes, and checker state.
- Intro paragraph 8 is implementation/evaluation sketch: LLM-assisted compiler, deterministic checker, adapters, and prototype numbers.
- Contributions remain after the rebuilt opening.

## Self-Check

- Abstract numbers match the intro/body: 0 dangerous accepts on 3,746 protected events; 3,813 benign reference actions; 4 authorized and 6 blocked side effects; 4 unsafe Qwen3.6 calls blocked before side effects.
- The abstract does not introduce a concept missing from the intro.
- The intro no longer presents four-plane details before the problem and root cause.
- Optional root-cause and challenge paragraphs are justified because the paper's insight depends on structural context privilege and the implementation must bind provenance, lease lifecycle, and delegation atomically.
- `\cite{}` count did not decrease.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex` from `docs/autopaper`.
- Checked the LaTeX log for undefined citations, undefined references, LaTeX warnings, and overfull boxes; no matching warnings were found.
- Cleaned generated LaTeX artifacts before committing.

## Remaining Concerns

- Several intro paragraphs still use English technical terms densely. The later language and terminology rounds should localize or reduce repeated coined terms.
- The opening is now consistent with the body as a prototype-evaluation paper. A future full-result submission would need stronger E1--E4 numbers before changing the abstract to a broader end-to-end claim.
