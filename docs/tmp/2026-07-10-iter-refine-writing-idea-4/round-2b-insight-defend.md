# Iter Refine Writing Idea Round 2b: Insight Defense

Date: 2026-07-10

Target file: `docs/autopaper/intentcap-paper-zh.tex`

## What Changed

The Round 2a attack argued that the paper could be rejected as a repackaging of provenance, capabilities, and stateful policy DSLs. The defense edits sharpened the insight into a minimal protected-decision interface theorem.

## Changes Applied

- Abstract lines 28--31 now state the safe authorization granularity directly: not a tool call, data-flow edge, or static capability object, but an authority-changing decision transition. The abstract also includes the safe-merge criterion.
- Introduction lines 47--49 now turn the “policy DSL can encode this” objection into an equivalence condition: a runtime converges to the paper's interface only if it exposes the owner-typed pre-effect record and same-transition lifecycle update.
- Contribution C1 now includes the interface theorem, not just the lease abstraction.
- Formal section lines 558--561 now state `minimal protected-decision interface` as a theorem with owner-equivalence and lifecycle-equivalence obligations.
- Formal section lines 532--534 now list minimal witness families for the unsafe owner merges, so four owners read as a safe-merge derivation rather than a taxonomy.
- Evaluation setup lines 893--908 now promotes typed-provenance state guard as the strongest prior-style composite baseline and makes E2 the mechanism-necessity experiment.
- Related work lines 1254--1256 now include an adversarial paragraph: CaMeL/AuthGraph/PACT/SkillGuard plus stateful capabilities converges to IntentCap only if it exposes the same pre-effect commit object and atomic lease/delegation update.
- Conclusion line 1293 now restates the strongest novelty sentence: the contribution is an authorization equivalence rule over proof ownership and lifecycle authority.

## Not Changed

- No quantitative values were changed.
- No new blinded adjudication experiment was added in this writing step. That remains the next evidence-side gate before claiming independent field-owner agreement.

## Remaining Concerns

Round 2c should re-attack novelty. The expected hard question is whether the new theorem is strong enough without a fresh blinded adjudication experiment.

