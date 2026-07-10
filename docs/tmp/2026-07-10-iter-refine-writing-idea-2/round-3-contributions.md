# 2026-07-10 Iter-Refine-Writing-Idea Round 3

## What Was Checked

Round 3 reviewed the contribution statements and design goals in `docs/autopaper/intentcap-paper-zh.tex` against the idea-quality checklist Section 3.

## Findings

Reviewer `019f4b5d-44e8-7d82-bab6-1be5f64aac25` reported that the paper's contribution list and design goals needed sharper alignment with the current core story: four proof-owner contexts, field-owned protected-decision leases, and the adapter-facing `check_and_consume` authority-state commit interface.

Must-fix items:

- C1/C2 overlapped because both described a commit model or contract.
- C2 still said `monitor-style replay target`, which could be read as production OS/ActPlane integration.
- G4 overclaimed boundary coverage beyond the current local adapters.
- C3 mixed E2 unsafe-accept metrics with E3 unsafe-execution/placement metrics.
- G2 promised broad data/control separation, while E2 mainly proves owner no-substitution/no-promotion.
- The first occurrence of 8,696/3,593/48-style numbers needed to say these are artifact-derived, author-adjudicated design evidence.

Should-fix items:

- Use `field-owned protected-decision lease model` for C1 and `authority-state commit interface` for C2.
- Clarify that agent context means trusted issuer canonicalized authority root, not model self-issued context.
- Treat recovery as diagnostic evidence, not a fifth top-level claim.
- Map G2 to C1+C2 because owner proofs must be submitted through the commit interface.
- Add a concrete C2 implementation acceptance criterion.

## Changes Made

- Rewrote C1 as the field-owned lease model over agent/instruction/tool/env proof owners.
- Rewrote C2 as the adapter-facing `check_and_consume` authority-state commit interface and explicitly excluded production OS/ActPlane integration.
- Rewrote C3 to separate E2 false-accept evidence from E3 unsafe execution/placement evidence.
- Added a short contribution-scope sentence: four contexts are proof-owner partitions, not component taxonomies, and the paper does not claim global taxonomy minimality, production ActPlane integration, or benchmark-scale utility.
- Narrowed G2 to field-owner no-substitution and no-promotion.
- Narrowed G4 to instrumented adapters and moved production MCP, prompt builder, subagent runtime, and kernel/ActPlane mediation to missing evidence.
- Added the C2 acceptance criterion: typed field proofs, versioned lease id, holder/scope state, pre-effect blockpoint, and checker-owned consume/delegate update.
- Marked recovery as diagnostic status in the evidence-boundary table.
- Added the author-adjudicated design-evidence caveat at the first numeric problem-characterization paragraph.
- Replaced remaining contribution-facing `monitor-style` wording with env-projection replay/lowering wording.

## Remaining Concerns

Independent field-owner adjudication, production-like MCP/prompt/subagent adapter integration, and benchmark-scale utility/recovery remain evidence gaps rather than current paper claims.
