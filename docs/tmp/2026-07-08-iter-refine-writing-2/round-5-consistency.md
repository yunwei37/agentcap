# Round 5: Consistency Audit

Scope: `docs/autopaper/intentcap-paper-zh.tex` and the paper-facing summary in `docs/evaluation.md`.

Skill path: `iter-refine-writing` round 5, with `audit-paper-consistency`.

## Issues Fixed

- Result wording: changed the 3,746 result from "dangerous protected events" to "protected-event replay cases with 0 dangerous accepts" in the abstract, introduction, and E1.
- Metric naming: unified `tool-oracle tasks` to `tool-oracle checks`.
- E1 mapping: added the saved local-Qwen replay result to the E1 body, matching the evaluation matrix and evidence table.
- E4 accounting: separated Qwen model aborts from checker-submitted attempts. The E4 table now reports `8 (+2 aborts)` for the Qwen row and the text reports 38 checker-submitted attempts.
- Adapter API: unified the runtime interface to `check_and_consume(e, lease_id, field_proofs, prov, sigma)` and clarified that arguments are carried by `e`.
- Rxxx leakage: removed visible R220/R224/R218-style run IDs from the main paper narrative where they distracted from claim-facing experiment families.
- ActPlane wording: changed result claims to `OS-monitor-style replay target inspired by ActPlane` and preserved production ActPlane/kernel integration as missing evidence.
- E3 tone: rewrote E3 as two evidence layers, trace characterization and controlled residual replay, instead of saying the "complete" experiment is unfinished.
- Evaluation document: aligned `docs/evaluation.md` with the three-main-experiment plus auxiliary-audit paper organization.

## Current Claim Boundaries

- Supported: instrumented protected-event replay safety, benign reference-action coverage, controlled issuer/lifecycle residual false accepts for weakened variants, and local multi-boundary pre-side-effect/placement/handoff enforcement.
- Auxiliary only: project-author lease-label audit and policy-distance sanity checks.
- Not yet supported: benchmark-scale end-to-end utility, approval burden reduction, independent expert-oracle least privilege, production prompt builder/subagent runtime integration, and production ActPlane/kernel syscall mediation.

## Remaining Writing Risks

- The main paper still contains some historical English terms and mixed Chinese/English phrasing; later language rounds should tighten these without changing the technical claims.
- The related-work comparison table may still read subjective because it uses compact coverage labels. A later terminology/claim-tone pass should either mechanize the column names further or soften the table introduction.
