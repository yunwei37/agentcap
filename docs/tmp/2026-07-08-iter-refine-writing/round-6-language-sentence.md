# Round 6: Language - Sentence Structure

Date: 2026-07-08

## Findings

Read-only reviewer `Maxwell` invoked the sentence-structure pass for `paper-writing-style` and checked `references/common-pitfalls.md`.

Must-fix findings:

- Abstract result sentence used a semicolon to join independent result claims.
- Introduction failure trace compressed setup, attack, and consequence into one long colon/semicolon sentence.
- Existing-defense paragraph used a semicolon list that read like notes.
- The source-separation paragraph used semicolons to join Skill/manual, MCP/tool, and script/tool-result claims.
- The system/result paragraph mixed mechanism description and evaluation numbers into one overloaded sentence.
- Authority Inputs compressed plane criteria and four plane definitions into one sentence.
- Authority Inputs mixed required-field rule, four examples, raw-user-text partition, and lease purpose in one paragraph.
- Formal checker judgment used a dense semicolon list for the acceptance conditions.

Should-fix findings:

- Agent Extensions used a semicolon list for Skills/MCP/scripts/subagents.
- Protected-Decision Transitions used a colon definition followed by a semicolon implementation clause.
- Authority Inputs used two large semicolon chains for plane capabilities and collapse consequences.
- Context Authority introduced the key decision-specific point too late.
- Effect IR and Leases used a long conditional sentence for fail-closed provenance handling.
- Implementation status used a defensive semicolon/colon construction.
- Prototype Evidence read like an artifact ledger.
- Conclusion repeated the abstract result structure with semicolon-joined clauses.

Consider items accepted:

- Reduced repeated colon rhythm in the introduction by turning some definitions into causal prose.
- Kept the System Overview short notes mostly intact but removed one unnecessary semicolon.
- Replaced vague `This evidence` in E1 with `The replay results`.
- Translated the abrupt English related-work evaluation sentence into integrated Chinese prose.

## Changes Made

- Split abstract and introduction result claims into separate sentences while preserving all numbers.
- Rewrote the failure trace as setup, attack, and consequence sentences.
- Recast the existing-defense paragraph as prose instead of a semicolon list.
- Split the source-separation paragraph into three parallel sentences.
- Split the LLM/compiler/checker/adapters paragraph from the evaluation result paragraph.
- Rewrote Authority Inputs into criteria, plane definitions, collapse consequences, no-substitution rule, and raw-user-text partition paragraphs.
- Split Context Authority and Effect IR paragraphs so decision-specific influence and fail-closed control provenance are stated before details.
- Converted the checker judgment into a single lead sentence plus numbered conditions.
- Split implementation and prototype evidence status sentences so they no longer read like defensive project notes.
- Split the conclusion result sentence into three scoped result sentences.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- Warning scan for undefined citations/references, LaTeX warnings, and overfull boxes returned no matches.
- `git diff --check` passed.

## Remaining Concerns

- Many sentences still mix English terms with Chinese syntax. Round 7 and Round 9 should improve word choice and flow without changing quantitative claims.
- Some semicolons remain in tables, TikZ, math, and compact formal lists. These are structural or tabular uses rather than prose sentence joins.
