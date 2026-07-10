# Iter Refine Writing Round 3: Logic Flow

Date: 2026-07-10

Skill workflow: `iter-refine-writing`, Round 3 logic flow.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Mill`.

## What Was Checked

The subagent used `critique-like-senior-systems-reviewer` and first checked `iter-refine-writing/references/common-pitfalls.md`. The review focused on whether the paper's formal model, design, E2 mechanism-necessity experiment, E3 multi-boundary experiment, and diagnostics tell one coherent claim-supporting story rather than an artifact ledger.

## Findings

Must-fix findings:

- E2 still read like an adjudication/protocol/result/caveat ledger rather than a compact mechanism-necessity experiment.
- E2 mixed two questions: whether owner/lifecycle fields are necessary and whether author-adjudicated labels are independently validated.
- E3 read like a surface catalog instead of evidence that the same pre-effect commit contract runs across side-effect, placement, handoff, and broker boundaries.
- The formal section buried the theorem after safe-merge, baseline, and E2-preview material.
- The four owner classes were repeatedly re-explained across design, formal model, E2, and E3.
- Scope-boundary wording appeared too often and risked sounding self-attacking.

Should-fix findings:

- The E1 Qwen3.6 matched slice was diagnostic authority-surface evidence, not primary E1 reference-action coverage.
- Implementation and related-work prose should avoid turning evaluation conclusions into section openings.
- Related work should keep the equivalence boundary but avoid defensive repetition.
- Bubblewrap/ActPlane material should remain backend/contrast evidence rather than the main E3 contribution.
- The paper should standardize on `proof owner` terminology and avoid suggesting that the LLM agent can self-authorize.

Consider findings:

- A future submission cut should split main text and appendix.
- A future figure mapping claim, mechanism, and experiment would reduce repeated explanations.
- E2/E3 captions should state claim takeaways instead of artifact inventory.

## Changes Applied

- Rewrote the formal-section opening so it now promises definitions, obligations, and theorem first. The theorem is no longer introduced as an E2/E3 preview.
- Moved the core protected-decision interface theorem immediately after the checker commit rule. The later theorem location was converted into interpretation and equivalence-boundary prose.
- Moved the local Qwen3.6 matched slice from E1 into `Supporting Diagnostics` under `Local Qwen Visibility Diagnostic`. E1 now only supports reference-action coverage and unsafe-accept sanity.
- Rewrote the E2 opening into the order `RQ -> oracle/adjudication boundary -> PDF intuition -> main ablation result`. The label protocol is framed as an oracle setup, while same-event removal remains the primary mechanism test.
- Reframed E2 trace characterization as coverage evidence and controlled counterexample replay as the primary mechanism result.
- Rewrote the E3 opening around three claim-supporting blocks: pre-side-effect enforcement, pre-placement/handoff enforcement, and backend contrast/lowering. The table caption now reflects these roles.

## Verification

- `PYTHONPATH=src:. python3 scripts/audit_paper_evidence_numbers.py --run-id R366PAPERAUDIT --paper docs/autopaper/intentcap-paper-zh.tex --output-dir results/eval/R366PAPERAUDIT`
- Result: 192/192 paper-facing evidence checks passed, 0 failures.
- The audit reported `no_dataset_sync=true`, `not_a_model_run=true`, and `not_a_new_experiment=true`.

## Remaining Concerns

E2 and E3 are now clearer, but the Chinese paper remains a long technical base. A later submission-cut pass should move field-owner adjudication details, prior-derived interface audit, and per-surface E3 provenance into appendix/supporting material, while keeping only the main ablation table and the three-block boundary summary in the main text.
