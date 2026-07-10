# Iter Refine Writing Round 0: Macro Structure

Date: 2026-07-10

Skill workflow: `iter-refine-writing`, Round 0 macro structure.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Parfit`.

## What Was Checked

The subagent used `check-paper-structure-flow` at Level 1 macro structure and first read `iter-refine-writing/references/common-pitfalls.md`. The review checked required section order, whether design and implementation are separated, whether an architecture figure exists, subsection balance, claim-driven evaluation organization, and whether limitations and related work are placed appropriately.

## Findings

Must-fix findings:

- The paper has the right section sequence but reads like a technical report: design, formal model, and evaluation dominate the manuscript, while intro, motivation, and threat model are compressed.
- Background and motivation are too compressed. The existing `背景与动机` section had four subsections in roughly 35 lines and mixed substrate background, running example, protected-decision definitions, and problem characterization.
- The formal section is too heavy for a submission main body. It simultaneously defines the model, defends novelty, states equivalence boundaries, and includes proof sketches.
- Evaluation is claim-driven in the right way, but E2/E3 details and diagnostics still risk reading like a run history.
- Implementation mixes system description with evidence/scope defense.

Should-fix findings:

- Architecture figure exists and is useful; eventual submission layout should move it as early as possible in the design section.
- Threat model is too short for a security systems paper and needs a clearer table of attacker, TCB, labeler limits, adapter coverage, and non-goals.
- Subsection balance is uneven: `Issuer Ownership and Safe Merge` is much longer than implementation subsections and E1.
- `范围与局限` is placed correctly but should read more like discussion plus limitations.

Consider findings:

- The current Chinese draft is a complete technical base. A real submission version should probably be a compressed main-paper draft rather than continuing to put all artifact detail in the main body.
- Related work placement is good, but the closest-abstractions table is heavy.
- The main macro conclusion is: the paper is not structurally chaotic anymore, but still reads like a complete experiment ledger plus formal notes. The submission spine should be one core abstraction, three necessary experiments, and one explicit boundary.

## Changes Applied

- Split `背景与动机` into separate `背景` and `动机与问题刻画` sections. This makes the substrate background distinct from the PDF-to-issue motivation and four-owner argument.
- Added a motivation paragraph explaining why Skills, MCP servers, commands, and documents are not mutually exclusive component types: each can carry multiple owner projections, so capabilities must be derived from field owners rather than component identity.
- Added a threat-model table covering attacker-controlled inputs, trusted roots, labeler duty, protected transitions, and backends. The table clarifies that the labeler canonicalizes observable channels and endorsements rather than inferring semantic trust from arbitrary text.
- Rewrote the implementation opening around a four-layer runtime path: checker core, adapter-facing API, boundary adapters, and lowering backends.
- Moved production-scope wording out of the implementation opening by pointing deployment evidence to the discussion/limitations section.
- Renamed `范围与局限` to `讨论与局限`.

## Remaining Concerns

The largest macro-structure concern is not fully fixed in this round: the current Chinese paper is still a long technical base, not a compressed submission manuscript. A later restructuring pass should move detailed pairwise merge tables, long formal equivalence audit, diagnostic recovery details, and some E2/E3 ledger text to an appendix or separate compressed submission draft. Round 1 should next inspect paragraph roles and topic flow before attempting a large-scale compression.
