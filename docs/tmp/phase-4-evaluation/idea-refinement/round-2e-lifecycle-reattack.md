# Round 2e: Lifecycle Re-Attack

Date: 2026-07-07

## What Was Checked

Re-attack of the paper after lifecycle bullets and residual examples were added.

## Findings

Subagent reviewer reported:

> The paper has improved, but Round 2 should not stop yet. Mint/Check/Consume/Expire/Attenuate/Deny amplification are still prose bullets rather than a transition system.

> The paper must state one non-reducibility invariant: authority state cannot be minted, refreshed, widened, or delegated through untrusted provenance, even when final action arguments are individually valid.

> The one-shot approval example should be a compound lifecycle case, not merely a counter or temporal guard.

> Contribution 3 should become an evaluation contribution rather than "claim-gated empirical analysis."

## What Was Changed

No paper text was changed in this sub-round. It motivates the next focused defense patch.

## Remaining Concerns

Add a compact transition block, sharpen the invariant, strengthen the residual example, and then run one final re-attack before Round 3.
