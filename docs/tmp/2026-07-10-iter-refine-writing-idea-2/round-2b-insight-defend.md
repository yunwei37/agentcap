# 2026-07-10 Iter-Refine-Writing-Idea Round 2b

## What Was Changed

Round 2b applied the defense against the Round 2a novelty attack in `docs/autopaper/intentcap-paper-zh.tex`.

## Changes Made

- Strengthened the abstract to say same-event ablations keep action, arguments, and provenance fixed while replacing only issuer ownership or lifecycle ownership.
- Reframed the introduction's central insight as an adapter-facing authority-state transition API with checker sole-writer discipline, rather than a new set of policy predicates.
- Sharpened the four-context explanation: agent answers who may authorize, instruction answers which procedure may guide, tool answers which interface may execute, and env answers what happened in the run.
- Added a safe-merge derivation in the design and formal model: owner classes are derived from protected field families and can be merged only when issuer, forgeability surface, observation point, and state-write authority are equivalent.
- Added an `Adapter-Facing Transition API` implementation subsection specifying required inputs, checker state ownership, linearization guarantee, failure semantics, concurrency semantics, and audit binding for `check_and_consume`.
- Added a field-owner adjudication protocol table to E2, separating owner-label assignment from the checker ablation result.
- Rewrote the ActPlane positioning as layered env-projection enforcement below IntentCap's pre-OS authority decision.

## Verification

Verification is recorded in the follow-up paper audit run for this step.

## Remaining Concerns

The defense still needs Round 2c re-attack. The current paper now better states the intended novelty, but an adversarial reviewer may still ask for independent owner-label adjudication or a broader production adapter implementation.
