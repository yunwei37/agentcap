# 2026-07-10 Iter-Refine-Writing-Idea Round 2a

## What Was Checked

Round 2a asked a read-only reviewer to attack the novelty of `docs/autopaper/intentcap-paper-zh.tex`, focusing on the central claim that four proof-owner context classes plus an authority-state commit object are not merely ABAC/IFC/provenance predicates with counters.

## Findings

Reviewer `019f4b4a-21bc-7f93-b7dc-0fecc7ba39c2` reported four must-fix issues:

- The central insight could still be rejected as an ABAC/IFC/provenance composite unless the paper framed the contribution as a required runtime transition API and writer discipline.
- The four proof-owner classes could still look author-defined unless the paper derived them from protected fields and a safe-merge relation.
- E2 still had a circularity risk because the protected-decision oracle already appeared to encode the owner classes that the ablation then validated.
- The implementation section still read like prototype gateways and replay suites rather than a general adapter-facing system interface.

The reviewer also suggested sharpening the four-context explanation, making ActPlane a layered env-projection backend rather than a competitor, and stating in the abstract that same-event ablations hold actions and arguments fixed.

## Concrete Reviewer Attack

The strongest reject argument was:

> This paper combines ABAC/IFC/provenance, capability leases, and linearizable state update, then renames the result as four proof owners and a commit object. It lacks independent evidence that the four classes are not defined by the paper's own oracle.

## Resulting Defense Direction

The next edit should make the paper argue from protected fields to owner partitions, from runtime writer discipline to the authority-state commit object, and from same-event false accepts to non-equivalence of collapsed interfaces.

## Remaining Concerns

Round 2c still needs a fresh re-attack after the defense edits. If a reviewer can still easily say "this is just a policy DSL with more attributes", the idea layer needs another defense pass.
