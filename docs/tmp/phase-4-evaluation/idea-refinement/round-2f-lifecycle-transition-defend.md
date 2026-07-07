# Round 2f: Lifecycle Transition Defense

Date: 2026-07-07

## What Was Checked

Defense patch after the Round 2e reviewer argued that lifecycle was still mostly prose and therefore reducible to action-provenance checking.

## Findings

The prior re-attack required four changes:

> Mint/Check/Consume/Expire/Attenuate/Deny amplification are still prose bullets rather than a transition system.

> The paper must state one non-reducibility invariant: authority state cannot be minted, refreshed, widened, or delegated through untrusted provenance, even when final action arguments are individually valid.

> The one-shot approval example should be a compound lifecycle case, not merely a counter or temporal guard.

> Contribution 3 should become an evaluation contribution rather than "claim-gated empirical analysis."

## What Was Changed

- Abstract, line 25: reframed the core abstraction as a run-time lease lifecycle that records mint, consume, delegation attenuation, provenance, temporal state, and budget.
- Introduction, line 40: added the invariant that authority state cannot be minted, refreshed, widened, or delegated through untrusted provenance, even when final action arguments are individually legal.
- Introduction, line 44: strengthened the residual example from a wrong-repo case to a compound lifecycle case involving consumed approval, full-scope refresh, and delegation beyond parent authority.
- Contributions, lines 49--51: made the first contribution a stateful lease calculus, the second the compiler/checker/runtime realization, and the third the trace-level safety and evaluation contribution.
- Formal model, lines 170--212: added lifecycle semantics with Mint, Check, Consume, Expire, Attenuate, and NoAmp transitions plus a compact state-transition block.
- Related work, lines 312--319: clarified that provenance labels are checker inputs, while leases are mintable, consumable, and delegable authorization objects.

## Verification

Ran:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed; LaTeX reported all targets up to date.

## Remaining Concerns

Run one final adversarial novelty re-attack. If the reviewer can still easily reduce the contribution to existing intent/provenance systems, Round 2 needs another defense patch; otherwise proceed to contribution and design-goal alignment.
