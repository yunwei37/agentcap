# Iter Refine Writing Round 1: Micro Structure

Date: 2026-07-10

Skill workflow: `iter-refine-writing`, Round 1 micro structure.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Maxwell`.

## What Was Checked

The subagent used `check-paper-structure-flow` at Levels 2--3 and first read `iter-refine-writing/references/common-pitfalls.md`. The review focused on abstract sentence roles, introduction paragraph roles, topic sentences, one idea per paragraph, why-before-what flow in design/evaluation, and subsection title consistency.

## Findings

Must-fix findings:

- The abstract followed the rough beat order but read like compressed body text. It introduced decision transitions, tool-call linearization, safe merge, four proof owners, TCB/compiler boundaries, and results before the reader had context.
- The abstract result sentences listed numbers without enough claim-facing explanation.
- The introduction contribution list was followed by a second explanatory paragraph that repeated C1/C2/C3 and sounded defensive.
- The design `授权输入` subsection mixed design explanation, motivation, formal `Solve`, safe-merge derivation, component taxonomy, and rebuttal material.
- The formal `Issuer Ownership and Safe Merge` subsection still mixes definitions, examples, theorem setup, E2 mapping, and prior-work defense.
- E2 still has run-led paragraphs where trace characterization, labels, audit notes, ablation results, and three-class coverage are close together.
- E3 paragraph starts were workload-first rather than claim-first.
- `Additional Diagnostics` interrupted the E1/E2/E3 evaluation spine.

Should-fix findings:

- Background paragraphs ended with mechanism conclusions rather than staying neutral.
- Problem characterization previewed experiment artifacts too early.
- Implementation subsection titles were not parallel.
- Evaluation titles mix English claim titles and bucket labels.
- Related work had a long EIM/ActPlane paragraph carrying too many roles.

Consider findings:

- A submission version should treat this Chinese paper as a technical base and move ledger/formal detail to appendix.
- The `agent` owner name remains a possible source of confusion.
- Run-in theorem/criterion labels may need theorem environments in a compressed submission version.

## Changes Applied

- Rewrote the abstract into a cleaner 4-beat structure: context, problem, IntentCap mechanism, and claim-facing results. The result sentences now explain what each number checks before giving the number.
- Replaced the repeated post-contribution C1/C2/C3 paragraph with one bounded-scope sentence.
- Made the background section more neutral by removing conclusion-heavy tails.
- Rewrote `Problem Characterization` as a qualitative transition problem instead of an early experiment preview.
- Compressed the design `授权输入` subsection by removing the design-local `Solve` formula and moving safe-merge details by forward reference to the formal section. The subsection now focuses on four proof-owner roles.
- Renamed implementation subsections to more parallel noun phrases: `Prototype Components`, `Transition API`, `Boundary Adapters`, `Replay and Live Gateways`, and `Compiler Frontend`.
- Rewrote E3 paragraph openings as claim-first sentences for pre-side-effect adapters, prompt/delegation placement, MCP-style broker, integrated workflow, paired data/control workflow, env lowering, and bubblewrap.
- Renamed `Additional Diagnostics and Supporting Audits` to `Supporting Diagnostics` and made its first sentence explicit that it is not a fourth primary experiment.
- Removed run-id-style missing-path detail from the E2 label-boundary paragraph while preserving the author-adjudicated limitation.
- Split the Related Work EIM/ActPlane paragraph into a substrate paragraph and a backend-relation paragraph.

## Remaining Concerns

The largest remaining Round 1 concern is structural compression, not a single paragraph edit. The formal section and E2 still contain more detail than a submission main body should carry. A later pass should move pairwise merge coverage, prior-derived interface audit, detailed E2 characterization rows, and recovery/lease-audit diagnostics into appendix or a separate compressed submission draft. The current edits improve paragraph roles without deleting evidence from the technical base.
