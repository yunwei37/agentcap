# Round 5: Reviewer Stress Test

Date: 2026-07-07

## What Was Checked

Final skeptical OSDI/SOSP-style reject argument after Round 1--4 idea fixes.

## Findings

Subagent reviewer reported:

> I see no obvious idea/framing blocker. The paper no longer looks like EIM/bpftime or ActPlane renamed.

The surviving paper spine is:

> context influence -> intent-derived stateful lease lifecycle -> checker/runtime -> four claim-gated experiments.

The strongest remaining reject argument is evidence-based:

> The current artifact shows a deterministic checker can reject modeled violations in traces, but the paper has not shown that a live agent can complete realistic workflows under these leases, nor that the lease lifecycle blocks attacks that cannot be naturally handled by a strong stateful provenance/IFC policy baseline. The least-privilege results rely on author-adjudicated labels.

## What Was Changed

- Runtime Lowering now explicitly separates design contracts from implemented adapters.
- The paper now says the prototype implements checker verdicts, trace replay gateway, live local callable gateway, and benchmark-derived MCP/delegation events.
- Full MCP broker and production sandbox are explicitly described as future enforcement backends, not completed artifact boundaries.
- The formal section now names the checker state schema fields: active/exhausted lease table, per-lease consumption counters, temporal automata state, mint proof records, and parent-child delegation graph.

## Verification

Ran:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. Remaining warnings are font and underfull layout warnings from mixed Chinese/English prose and tables.

## Remaining Concerns

Idea refinement is complete. The paper is now blocked by experiments, not idea framing:

- E1 needs same-model online security+utility comparison.
- E3 needs the decisive residual comparison against strong provenance/IFC/stateful-policy baselines.
- E2 needs independent blinded expert-oracle review or a clearly lowered author-oracle claim.
- C3 must become measured evidence before a final OSDI/SOSP full-paper contribution list.
