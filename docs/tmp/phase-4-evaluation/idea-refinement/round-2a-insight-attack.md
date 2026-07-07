# Round 2a: Insight Attack

Date: 2026-07-07

## What Was Checked

Insight and novelty framing in `docs/autopaper/intentcap-paper-zh.tex`, especially the thesis around lines 40--44, the contribution list around lines 49--52, and related work positioning around lines 267--273, against checklist Section 2.

## Findings

Subagent reviewer (skeptical novelty attack) reported:

> The strongest novelty attack still holds. The broad claim that the system asks "which context may influence which decision" is too close to AuthGraph, PACT, AIRGuard, and SkillGuard-style provenance-authority systems.

> The lease sentence currently looks like a bundle of existing fields: holder, op, args, intent, provenance, flow, temporal, budget, delegation. Without a new issuance/attenuation/consumption invariant, it reads as engineering packaging.

> The related work distinction only says "proof-carrying, attenuable leases plus unified checking"; that is not yet a sharp delta against PACT capability contracts, AIRGuard step authority, and AuthGraph intent/provenance graphs.

> Contribution 4 is an evaluation plan, not a paper contribution.

## What Was Changed

No paper text was changed in this sub-round. This was an adversarial attack pass only.

## Remaining Concerns

The defense must move the center from "context influence/provenance authorization is new" to "intent-derived, proof-carrying leases are the lifecycle object for future decision authority across Skills, MCP, local execution, and subagents."
