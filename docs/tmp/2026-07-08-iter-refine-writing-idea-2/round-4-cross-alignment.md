# Round 4: Cross-Alignment

Date: 2026-07-08

## What Was Checked

A read-only reviewer checked whether problem, insight, goals, contributions, evaluation, evidence boundary, and claim ladder tell one coherent story in `docs/autopaper/intentcap-paper-zh.tex`. The review also checked terminology consistency around protected-decision transition, protected event, authority-state transition, four planes, issuer-typed fields, and transaction API.

## Findings

Must-fix findings:

- The formal model said a protected event needed all four projections, while later text said required fields vary by decision class.
- G4 was a multi-boundary transaction API goal, but E4 was framed mostly as compiler/checker/recovery practicality.
- C2 still needed cleaner implementation-boundary wording: implemented tool/env gateways versus trace-level instruction/delegation contracts.
- The evaluation introduction said run IDs are not main experiment numbers, but E3/evidence text still used R IDs prominently.

Should-fix findings:

- Add a terminology explanation: decision class, protected event, and protected-decision transition.
- Avoid "intersection" wording for four context planes.
- Reduce E1/E4 metric lists into primary/secondary outcomes.
- Clarify that related-work matrix is abstraction coverage, not implementation maturity.
- Add issuer-plane closure in the conclusion.

## What Was Changed

- Contributions, line 52 before edit: "prototype adapter set" wording still blurred implemented and trace-level surfaces.
  After edit: C2 now says "implemented tool/MCP and local-env gateways" plus "trace-level instruction/delegation adapter contracts."

- Motivation, after protected-decision definition before edit: terms were used consistently enough for authors but not explicitly mapped.
  After edit: added a terminology paragraph defining decision class, protected event, and protected-decision transition.

- Goals and E4 before edit: G4 pointed to E4, but E4 mainly evaluated compiler/recovery.
  After edit: E4 is renamed "Transaction API and Recovery Practicality." Its primary outcome is whether context placement, tool/MCP, local env side effects, and delegation handoff call the same checker before side effects or authority transfer. Recovery remains a secondary outcome.

- Formal model, lines around projection before edit: "four projections" sounded like all four planes are always required.
  After edit: a protected event is accepted only when `Req(d)`-required projections match the lease; unrequired planes may be empty, and required fields cannot be supplied across planes.

- E1/E4 metrics before edit: long flat metric lists.
  After edit: E1 has primary outcome `attack success under bounded utility loss`; E4 has primary outcome `valid recovery without broad authority or dangerous execute`; supporting metrics are secondary.

- E3/current evidence before edit: local residual paragraph and evidence table used run IDs directly.
  After edit: E3 describes a 9-event local workflow-policy sanity check without run IDs; evidence table rows describe result classes rather than R-number history.

- Related-work matrix before edit: IntentCap lowering was "multi-boundary contract."
  After edit: lowered to "prototype + contract" to avoid implying production-grade coverage on every boundary.

- Conclusion before edit: returned to context influence but did not mention issuer-typed fields.
  After edit: final sentence now says each protected field must be proven by its owning issuer plane.

## Verification

Compiled from `docs/autopaper` with:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex
```

Checked for undefined citations, undefined references, and overfull boxes. No matching warnings remained; only underfull table warnings remained.

## Remaining Concerns

- E3 still needs the actual workload characterization and strongest composite baseline before the full novelty claim is evidence-complete.
- Current C3 remains correct for an extended abstract. A full paper should replace it with completed characterization/evaluation results.
