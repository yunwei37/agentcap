# Round 1: Micro Structure

## Reviewer Focus

Applied the iter-refine-writing Round 1 pass on paragraph roles and local section flow. The main concern was that the draft still mixed paper roles: the abstract read like a mini-outline, the introduction carried too much running-example detail, implementation paragraphs bundled distinct mechanisms, and the evaluation section mixed final experiment design with current evidence status.

## Must-Fix Items Addressed

1. Rewrote the abstract as one coherent paragraph with four beats: problem, IntentCap abstraction, checker/runtime architecture, and current claim boundary.
2. Split introduction roles: the intro now introduces context privilege, protected decisions, related defenses, and the lease-lifecycle insight; the detailed PDF trace moved to Motivation.
3. Added `sec:motivation` and expanded Motivation with the context-to-decision influence trace.
4. Reduced repeated lifecycle residual prose in the formal section and left one concise takeaway after the trace table.
5. Rewrote E1/E2 so they define final hypotheses, baselines, metrics, and interpretation boundaries instead of reporting pilot run history.
6. Renamed the evidence subsections to `Artifact Boundary` and `Claim Boundaries` to avoid a self-attacking tone while preserving conservative claim discipline.

## Should-Fix Items Addressed

1. Split `TraceGateway` and `LiveToolGateway` into separate paragraphs.
2. Split local LLM compiler probes from tau2/tau3 runtime binding.
3. Added a why-before-what sentence to Runtime Lowering, clarifying why a single tool gateway is insufficient.
4. Split the longest related-work paragraph on prompt injection/provenance/IFC into background and differentiation paragraphs.
5. Rewrote the conclusion to end on the thesis rather than only on missing experiments.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- A first `latexmk -pdf` attempt failed because it used `pdflatex`, which is incompatible with the Chinese font setup; this is an invocation issue, not a manuscript error.
- Remaining warnings are font script and underfull hbox warnings.

## Remaining Risks

The paper is structurally clearer, but it is still longer and more mixed-language than a polished submission. Later rounds should tighten section conventions, terminology consistency, and citation grounding.
