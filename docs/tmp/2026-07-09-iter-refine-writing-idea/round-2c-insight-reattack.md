# Round 2c: Insight Re-attack

Date: 2026-07-09

## Remaining attack

- Evidence doesn't test two-class or three-class baselines
- 38-event boundary test too small to validate architectural choice
- Paper shows provenance tracking helps (known from IFC), not that THIS four-class decomposition is canonical
- A simple high-trust/low-trust IFC baseline could plausibly pass same benchmarks

## Assessment

This is a valid evidence gap, not a framing problem. The writing fix is:
- Frame the four classes as grounded in forgeable-surface analysis, not as the universal answer
- Emphasize the composition model (field-level ownership + priority) as the insight, not the specific count
- Acknowledge the two-class baseline gap as future work in Discussion
