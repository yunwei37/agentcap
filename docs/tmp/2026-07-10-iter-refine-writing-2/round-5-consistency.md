# Round 5: Consistency Audit

Date: 2026-07-10

## What Was Checked

Ran a read-only consistency audit on `docs/autopaper/intentcap-paper-zh.tex` with the `audit-paper-consistency` checklist and the iter-refine writing common pitfalls. The audit focused on terminology drift and cross-section alignment after the abstract/intro rebuild:

- `pre-effect commit`, `pre-effect commit record`, `protected-decision transition`, and older `authority-state` wording.
- `check_and_consume` argument fields across the quote contract, formal design, and implementation section.
- `owner class`, `proof-owner class`, `issuer class`, and `context class`.
- C1/C2/C3 alignment with G1--G4 and E1/E2/E3.
- E3 aggregate numbers versus table rows.

## Findings

Must-fix findings:

- The paper used `pre-effect commit`, `authority-state commit object`, `authority-state transition`, and `protected-decision transition` without a clear mapping. This could make reviewers think the paper has several core abstractions.
- The `check_and_consume` signature differed across sections: the quote contract used `prov_C`, `prov_D`, and `state_version`, while later sections used `prov`, `version`, or even `sigma`.
- E3 reported a 58-attempt system-surface aggregate without explaining that it is a deduplicated summary, not the row-wise sum of the E3 table.

Should-fix findings:

- The paper mixed `owner class`, `proof-owner class`, `issuer class`, and `context class` without one alias sentence.
- C3 sounded too much like an evaluation-only contribution instead of a system implementation plus evidence suite.
- Captions and related-work tables should use the paper's main interface term, `pre-effect commit record`.

Consider findings:

- The abstract remains term-dense.
- One English line, `Checker judgment is:`, should be localized.
- ActPlane boundary caveats are correct but repeated; later language rounds can compress them.

## Changes Made

- Added a terminology bridge in the protected-decision terminology subsection:
  - `pre-effect commit` is the runtime submission interface.
  - `pre-effect commit record` is the concrete adapter-submitted record.
  - `protected-decision transition` is the authority-changing state transition atomically committed by that record.
  - Older `authority-state commit` wording now appears only as an explicitly mapped internal-state synonym.

- Replaced the old main terminology in the introduction, formal section, E2 captions, related-work comparison, and conclusion:
  - `authority-state transition` -> `protected-decision transition` when discussing semantic transitions.
  - `authority-state commit object/record` -> `pre-effect commit record` when discussing the runtime object.
  - `authority-state split` -> `lifecycle split`.

- Aligned the adapter API signature in design and implementation:
  - Before: `check_and_consume(e, lease_id, field_proofs, prov, sigma/version)`.
  - After: `check_and_consume(e, lease_id, field_proofs, prov_C, prov_D, state_version) -> allow(sigma', audit) | deny(reason)`.
  - Added that adapters submit only `state_version`; checker-owned `sigma` is not submitted or written by adapters.

- Added an alias sentence for the four owner terms:
  - `owner class`, `proof-owner class`, `issuer class`, and `context class` all refer to canonicalized proof-cell owners, not raw artifacts or runtime components.

- Reframed C3:
  - Before: `Cross-boundary prototype and removal evaluation`.
  - After: `Cross-boundary implementation and evidence suite`.
  - This keeps the contribution as a system/evidence deliverable rather than an evaluation-only item.

- Clarified E3 aggregate interpretation:
  - The 58 boundary attempts are from the deduplicated system-surface summary, not a row-wise sum of Table E3.
  - Integrated, paired, lowering, and sandbox rows reuse some underlying events to show different views of the same contract.

- Localized `Checker judgment is:` to `Checker judgment 写作：`.

## Remaining Concerns

- The abstract is still jargon-heavy; a later language/claim-tone round should decide whether to cut terms there without weakening the top-level claim.
- ActPlane/OS-backend caveats are accurate but repeated in several sections; a later flow-polish round can compress them after confirming no scope boundary is lost.
- This round did not change any quantitative result. The paper still needs the existing compile and evidence-number audit gates before committing.
