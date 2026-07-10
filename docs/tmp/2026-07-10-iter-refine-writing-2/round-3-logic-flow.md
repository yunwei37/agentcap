# Round 3 — Logic Flow

Date: 2026-07-10

Paper: `docs/autopaper/intentcap-paper-zh.tex`

Skill path: `iter-refine-writing`, Round 3. The review subagent was instructed to use `critique-like-senior-systems-reviewer` with logic-flow focus for a full systems paper, after reading `iter-refine-writing/references/common-pitfalls.md`.

## What Was Checked

- Whether abstract, introduction, design, model, evaluation, and related work support the same OSDI/SOSP-level claim.
- Whether claim/evidence boundaries are calibrated without self-attacking caveats.
- Whether E1/E2/E3 read as a coherent argument rather than an evidence ledger.
- Whether the four-owner claim is presented as a tested safe-merge result rather than a global taxonomy proof.
- Whether the system contribution is a crisp runtime interface rather than a collection of adapters.

## Reviewer Findings

Must-fix findings:

- Abstract and introduction mixed the main claim with too many evidence-boundary caveats.
- E2 still read like a ledger because adjudication, trace characterization, collapse studies, prior-derived baselines, workflow residuals, and counterexamples appeared without a single question/setup/result frame.
- The formal section was too long for first-pass reviewer comprehension and needed a clearer statement of theorem assumptions.
- The four-owner claim risked being read as ontology minimality rather than tested safe-merge evidence.
- The system contribution needed a crisp adapter contract before listing runtime boundaries.

Should-fix findings:

- The abstract result sentence was too dense.
- Intro root-cause and challenge paragraphs partly repeated the same owner/state/boundary idea.
- The design-goal map still had some rebuttal-table flavor.
- E1 should remain a representability guardrail, not the main security result.
- Scope and related-work tables remain large and may still interrupt flow.

## Changes Made

1. Abstract and introduction:
   - Compressed the abstract result beat to keep the reference-action coverage and no-owner false-accept result, while summarizing E3 as a multi-boundary contract result.
   - Replaced the long intro caveat list with a single forward reference to the evidence-boundary section.

2. System contract:
   - Added a `Pre-effect commit contract` box to the design overview.
   - Made the required adapter submission explicit: event, lease id, field proofs, control/data provenance, and state version.
   - Stated that checker is the sole writer for lease table, budget, expiry, and delegation graph, and that allow returns updated state plus audit id.

3. Formal model:
   - Added a reviewer-facing dependency paragraph before the formal definitions.
   - Stated that safety properties depend on owner-typed proof projections, checker-owned lifecycle state, and adapter coverage.
   - Linked these dependencies to E2 and E3.

4. E2:
   - Renamed the section from `Issuer-Collapse and Lifecycle-Split Removal Study` to `Tested Owner and Lifecycle Removal Study`.
   - Rewrote the opening around a single falsifiable mechanism question.
   - Framed the result as a tested safe-merge/removal result, not a global proof that all systems must have exactly four context classes.
   - Added a PDF-to-issue bridge explaining how body data use, repo authorization, tool schema proof, and one-shot lease reuse map to E2 removals.

## Remaining Concerns

- E2 still contains too many tables for a final conference-length paper; later rounds should move trace characterization and prior-derived interface audit to an appendix or supporting-audit subsection.
- The formal section still contains long safe-merge and equivalence-boundary material; a later structural pass should compress it to definitions, judgment, obligations, and properties.
- The goal map and scope table still have some rebuttal flavor.
- Related work is improved but still relies heavily on the comparison table.
