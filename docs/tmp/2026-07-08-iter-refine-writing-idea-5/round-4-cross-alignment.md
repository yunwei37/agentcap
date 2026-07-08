# Round 4: Cross-Alignment

Date: 2026-07-08

## What Was Checked

A read-only reviewer checked whether the paper's problem, insight, design goals, contributions, and evaluation tell one coherent story. The review focused on the chain: issuer collapse and authority-state split -> protected-decision commit object -> four issuer-owned projections -> atomic checker transition -> E1/E3/E4 plus supporting audit.

## Findings

Must-fix findings:

- The runtime lowering table still mixed issuer classes, adapter boundaries, and checker state. It listed five adapters as if delegation were a fifth issuer, and it placed active/delegated lease state near submitted fields.
- E4 still read as a bundle of local env, Qwen proposer, placement tests, delegation tests, Skill tests, and monitor replay. The core system claim should be that the same transition API can be placed before multiple authority-changing boundaries.

Should-fix findings:

- G1's evaluation mapping should point more strongly to E3 issuer-collapse evidence and the G1-specific protected-event subset, not only E1 reference coverage.
- The goal map should explicitly include C3 as the evidence contribution.
- Related work should not make `oracle-distance audit` sound like a primary policy-family comparison.
- The related-work comparison table should describe IntentCap lowering as local adapters plus a replay lowering target, not as a production OS/ActPlane-level implementation.

Consider findings:

- Use `runtime-observation/env` in C1 for terminology consistency.
- Keep E1 diagnostics short so the main experiment does not read as run history.
- Keep the top-conference story fixed as C1 model, C2 protected-transition API/adapters, and C3 evidence over E1/E3/E4 plus supporting audit.

## What Changed

- Contribution C1, around line 86: changed `env` to `runtime-observation/env`.
- Goal map, around lines 179-183: changed G1's primary eval to `E3 + E1 protected-event subset`, added C3 to the contribution column, and added a sentence stating that C3 covers all evaluation rows.
- Runtime lowering section, around lines 327-359: rewrote the section and table so boundaries submit agent/instruction/tool/env projections while checker-owned state `sigma` reads/updates active leases, budgets, expiry, and delegation graph. Delegation is now clearly a handoff boundary, not a fifth issuer.
- E4, around lines 830-860: reorganized the experiment into three block points: pre-side-effect env boundary, pre-placement/handoff boundary, and monitor-lowering feasibility. Qwen3.6 is now explicitly a diagnostic over the env boundary rather than the subject of the system claim.
- Related work, around lines 922-939: changed IntentCap lowering to `local adapters + replay lowering target`, ActPlane to `OS substrate`, and clarified that controlled protected-decision counterexamples are the primary policy-family comparison while lease audit only checks representation/auditability.
- `docs/evaluation.md`: aligned C4 and E4 wording with the three-boundary structure and diagnostic status of Qwen3.6.
- `docs/implementation.md`: clarified that R199-R207 are supporting lease-auditability artifacts despite historical E2 run names.

## Remaining Concerns

The cross-section story is now coherent. Remaining risks are evidence maturity, not framing alignment: independent expert labels, benchmark-scale closed-loop utility/recovery, approval-burden measurements, and production prompt-builder/MCP/subagent or ActPlane/kernel integration are still missing.
