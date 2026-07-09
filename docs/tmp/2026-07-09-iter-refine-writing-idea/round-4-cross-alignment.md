# Round 4: Cross-alignment

Date: 2026-07-09

## Findings

1. **[Medium]** "memory" in abstract S1 but absent from four-class model in body
2. **[Medium]** Design goals (3) don't map to RQs (4) — RQ4 auditability unmotivated
3. **[Low]** "malicious injection" (abstract) vs "adversarial injection" (intro) drift
4. **[Low]** "task plans" in abstract not elaborated in Design
5. **[Low]** Motivating PDF example not directly instantiated in evaluation

## Changes Applied

- Fix 1: memory → clarify as part of runtime data (env context) in abstract or remove
- Fix 2: add "(4) auditable leases" to design goals
- Fix 3: unify terminology to "adversarial injection" everywhere
