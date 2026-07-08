# Round 2: Section Conventions

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Skill workflow: `iter-refine-writing`, Round 2 section conventions.

## Findings

The read-only reviewer checked abstract structure, introduction roles, design goals, evaluation setup, related-work grouping, and conclusion conventions. The main issues were:

- The abstract still carried too many results and technical terms for a 4-beat systems-paper abstract.
- The introduction had the right causal chain, but the system/result material was still slightly over-expanded.
- E1 contained an E3 explanation and therefore did not answer one question cleanly.
- E2 looked like a main experiment despite being an author-adjudicated auxiliary audit.
- The Skill/MCP related-work subsection packed permission-root comparison, field ownership, an example, and union-authority contrast into one long paragraph.
- The conclusion ended with a future-evidence list rather than a bounded final claim.

## Changes Made

- Compressed the abstract to eight sentences and kept only claim-facing numbers: 0 dangerous accepts on 3,746 protected events, 3,813/3,813 reference-action coverage, and 38 local boundary attempts with 0 unsafe effects/placements.
- Removed implementation-status caveat text from G4 and kept it as a clean design goal.
- Replaced design-section ActPlane mentions with generic OS/runtime monitor wording; concrete ActPlane positioning remains in implementation, E4, limitations, and related work.
- Changed the evaluation overview from four main questions to three main experiments plus one auxiliary audit.
- Renamed E2 to `辅助审计：Lease Auditability` and made the evaluation matrix label it as `Aux.`.
- Removed the E3 sentence from E1 so E1 only covers protected-event safety and benign reference coverage.
- Shortened the Evidence Boundary lead text and renamed section titles `证据边界` and `局限`.
- Split the Skill/MCP related-work subsection into permission-root comparison and field-ownership contrast.
- Rewrote the conclusion to end with a bounded claim rather than a future-work list.

## Remaining Concerns

- The draft still mixes English and Chinese technical vocabulary. Later language rounds should normalize titles and term density without changing claims.
- E3 still contains one detailed characterization table; it is useful for the four-context claim, but later flow/polish rounds may decide whether to move it out of the main text.
