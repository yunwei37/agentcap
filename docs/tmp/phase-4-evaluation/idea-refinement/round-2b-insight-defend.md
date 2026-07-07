# Round 2b: Insight Defense

Date: 2026-07-07

## What Was Checked

Defense against the Round 2a novelty attack. The paper text was revised in the abstract, thesis paragraphs, contribution list, and related work positioning.

## Findings Addressed

Round 2a found that the broad claim "context influence/provenance authorization is new" is vulnerable because AuthGraph, PACT, AIRGuard, SkillGuard, and IFC-style systems already cover adjacent provenance-authority checks.

## What Was Changed

- Abstract line 25 now says `IntentCap` does not claim intent/provenance checking itself is new. The core abstraction is a run-time lease lifecycle for future decision authority.

- Thesis line 40 was rewritten from a broad context-influence claim to a narrower lifecycle claim: agent extensions need run-time leases that record how authority is produced from current intent, checked and consumed before protected decisions, narrowed by temporal/budget guards, and attenuated during delegation.

- Lease paragraph line 42 now distinguishes `IntentCap` from action-time provenance guards: the lease is a future decision authority object with validity, budget, delegation, and lowering semantics, not just a field bundle checked after an action appears.

- Contribution list lines 49--51 was reduced from four items to three contribution-shaped items:
  1. a run-time lease calculus,
  2. proof-carrying leases plus checker semantics and trace-level properties,
  3. a cross-boundary prototype plus claim-gated empirical analysis.

- Related work line 266 now separates observed-action provenance checking from lease lifecycle management: provenance labels are checker inputs; leases are authorization objects that can be minted, consumed, attenuated, delegated, and lowered.

- Skill/MCP related work line 272 now explains the run-centric/cross-extension distinction as per-run, intent-rooted, consumable, non-self-amplifying leases rather than package-level manifests or server grants.

## Verification

Ran:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. Existing font/box warnings remain; no fatal LaTeX errors.

## Remaining Concerns

The revised framing is more defensible, but Round 2c must test whether the lease lifecycle claim is still easy to dismiss as capability/provenance packaging.
