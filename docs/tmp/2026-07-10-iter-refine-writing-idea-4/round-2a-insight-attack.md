# Iter Refine Writing Idea Round 2a: Insight Attack

Date: 2026-07-10

Skill workflow: `iter-refine-writing-idea`, Round 2a adversarial insight and novelty attack.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Mendel`.

## What Was Checked

The subagent reviewed the paper against `idea-quality-checklist.md` Section 2, focusing on whether the central insight is separable, non-obvious, and defensible against provenance/IFC/capability/policy-DSL prior work.

## Findings

Overall novelty risk: High.

Strongest reject argument:

> This paper appears to repackage known ideas from capabilities, provenance/IFC, reference monitors, and agent policy systems into a new vocabulary. “Pre-effect commit record with issuer-owned fields and atomic lifecycle update” is a sensible engineering interface, but the paper does not yet prove it is a non-obvious abstraction rather than a stateful policy DSL with better bookkeeping.

Must-fix items:

- The central insight still sounded like “compose provenance + capabilities + stateful monitor.”
- Generic policy DSL convergence was conceded without being turned into a theorem.
- Four owner classes still risked looking arbitrary rather than derived.
- Novelty evidence depended on author-adjudicated or controlled artifacts; independent blinded adjudication remains a required stronger-evidence step.
- The closest-baseline comparison needed to promote typed-provenance state guard as the strongest prior-style composite.

Should-fix items:

- Put safe-merge in the abstract.
- Keep E1 as a guardrail, not novelty evidence.
- Reduce terminology drift.
- Add an adversarial related-work paragraph answering the strongest prior-work combination.
- Keep ActPlane as env-projection backend unless a real integration exists.

## Remaining Concerns

The paper still needs a separate stronger evidence step for blinded/second-pass field-owner adjudication. This round did not create new labels; it identified that as the next experiment-side gate.

