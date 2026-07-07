# Round 3: Contributions and Design Goals

Date: 2026-07-07

## What Was Checked

Contribution statements, design goals, and their mapping to evaluation questions.

## Findings

Subagent reviewer reported:

> The direction is right, and the three contributions plus four main experiments are basically reasonable.

Must-fix issues:

> Contribution 2 packs compiler, checker, runtime prototype, TCB boundary, and multi-boundary lowering into one sentence.

> Design goals are five unnumbered bullets, while evaluation uses E1--E4; the goal-to-contribution-to-experiment mapping is implicit.

> E2 currently depends on project-author oracle labels, so the paper should not phrase least-privilege evidence as a strong expert-oracle result until an independent reviewer validates it.

## What Was Changed

- Contributions now use explicit C1/C2/C3 labels:
  - C1 is the model contribution.
  - C2 is the system contribution.
  - C3 is the evidence and claim-gate contribution.
- Added section labels and contribution references to the formal model, design, implementation, and evaluation sections.
- Replaced the five unnumbered design bullets with four testable goals G1--G4:
  - G1 intent-bounded authority maps to C1 and E1/E2.
  - G2 context influence separation maps to C1/C2 and E1/E3.
  - G3 stateful least-privilege lifecycle maps to C1/C2 and E2/E3.
  - G4 untrusted compiler with deterministic recovery maps to C2 and E4.
- Evaluation design now states that each experiment should be read through hypothesis, baselines, metrics, success gate, and current evidence gap.
- E2 now calls the current labels an author-adjudicated oracle with machine audit, and keeps blinded expert leases as the target methodology.

## Verification

Ran:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex
```

Result: passed. A large contribution-list overfull warning was fixed by splitting C1; remaining warnings are existing font, underfull, and small overfull layout warnings.

## Remaining Concerns

Round 4 should check whether problem, thesis, goals, contributions, formal model, implementation, and E1--E4 now tell one coherent story without forcing readers to infer the mapping.
