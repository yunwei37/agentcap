# Round 2a: Insight Attack

Date: 2026-07-07

## What Was Checked

Adversarial novelty review of `docs/autopaper/intentcap-paper-zh.tex`, focusing on:
- Thesis and insight framing in the introduction.
- Context influence modes.
- Protected decision abstraction.
- Formal lifecycle trace and related-work positioning.
- Checklist Section 2: insight novelty, non-obviousness, and whether the idea is more than an artifact.

## Findings

Reviewer findings, quoted/paraphrased from the fork review:

> The current thesis should prove that agent security is not just action/tool permission, but future decision authority lifecycle state. The paper already narrows the claim to stateful intent-carrying leases, but a skeptical reviewer can still attack it as a composition of capability systems, provenance/IFC labels, and workflow counters.

Strongest rejection argument:

> The paper correctly identifies that agent decisions should be provenance-aware, but the proposed solution is a straightforward composition of known ideas: user intent as policy root, taint/IFC labels for untrusted context, attenuable capabilities for authority, temporal/budget state for workflow control, and delegation monotonicity from capability systems. The paper does not yet show a new invariant, a minimal decomposition, or a workload property that forces these pieces to be unified as "intent-carrying leases" rather than implemented as a conventional stateful provenance policy.

Key vulnerabilities:
- `line 40`: mint/check/consume/expire/attenuate/no-amplification may look like known attenuable capability machinery.
- `lines 421-423`: the related-work distinction says IntentCap maintains four kinds of state, but a reviewer can argue existing systems could add counters, temporal guards, and a delegation graph.
- `lines 151-153`: context influence modes can be read as decision-specific taint labels.
- `lines 278-296`: the residual trace could still be encoded by a strong stateful provenance policy baseline.
- `lines 161-167`: compiler/checker is still described at a framework level and could look like a standard policy compiler.

## Required Defense Direction

The next revision should not claim novelty from individually known ingredients. It should claim:

> IntentCap's novelty is the atomic authority lifecycle object for future agent decisions, not the individual ingredients.

Concrete direction:
- Rephrase protected decisions as authority-state transitions rather than events checked after materialization.
- Explain that mint provenance, decision-specific influence authority, consumption/expiry, and delegation must be updated atomically over the same authorization object.
- Strengthen E3 so the novelty test is whether any strict subset of the lifecycle components admits a residual violation.

## What Was Changed

No paper edits in Round 2a. This round is adversarial review only.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`.
- Build completed successfully.
- Final log check found no undefined citations, undefined references, fatal errors, or LaTeX errors.

## Remaining Concerns

- Round 2b must revise the thesis and formal/evaluation framing so that "lease" is not merely a container for existing policy components, but the atomic unit that makes authority transitions indivisible at decision time.
