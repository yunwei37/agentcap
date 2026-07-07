# Round 2d: Lifecycle Defense

Date: 2026-07-07

## What Was Checked

Defense against the Round 2c re-attack that lease lifecycle was still prose rather than calculus.

## Findings Addressed

Round 2c found that the novelty attack remained viable unless the paper defined lifecycle transitions such as mint, check, consume, expire, attenuate, and no-amplification.

## What Was Changed

- Intro line 44 now gives a residual example: a one-shot `create_issue(repo=org/repo-x)` approval lease is consumed after first use; later reuse, scope expansion, or subagent delegation is denied by lifecycle state even when some final action fields still look intent-aligned.

- Contribution line 49 now names a `stateful run-time lease calculus` and lists the lifecycle transitions directly.

- Formal model lines 170--181 now define the lifecycle as state transitions over runtime state `sigma`: Mint, Check, Consume, Expire, Attenuate, and Deny amplification.

- The residual case is repeated in the formal model to show why final action provenance alone is an unnatural fit for one-shot approval reuse, unauthorized minting, and non-monotone delegation.

## Verification

Ran:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. Existing font/box warnings remain; no fatal LaTeX errors.

## Remaining Concerns

Round 2e must verify whether the revised calculus framing is enough to move past the novelty attack, or whether more changes are needed before Round 3.
