# Round 3: Contributions and Design Goals

Date: 2026-07-08

## What Was Checked

A read-only reviewer checked `docs/autopaper/intentcap-paper-zh.tex` against `iter-refine-writing-idea/references/idea-quality-checklist.md` Section 3. The focus was contribution count, whether contributions are concrete deliverables, and whether goals align with contributions and evaluation.

## Findings

Must-fix findings:

- C3 still looked like a roadmap plus pilot numbers rather than a stable contribution.
- The text and goal map disagreed on which experiments support G1/G2/G3.
- C2 sounded broader than the implemented system surface because instruction/delegation are trace-level and ActPlane is only a target backend.
- Five design goals mixed top-level goals with implementation constraints.
- The claim ladder and contribution list conflicted because C3 embedded pilot numbers while the claim ladder said full-paper claims are not closed.

Should-fix findings:

- C1 packed too many items into one contribution sentence.
- C2 should emphasize the transaction API and prototype adapters, with trace-level/target status left to the implementation table.
- The authority-input formula should state that required protected fields come from owner planes; not every lease needs all four planes non-empty.

## What Was Changed

- Contributions, lines 50-53 before edit: C1 mixed model, four-plane requirements, lifecycle, and four properties; C2 implied broad runtime coverage; C3 included pilot numbers directly.
  After edit: C1 is a stateful protected-decision lease model; C2 is a checker-centered transaction API plus prototype adapter set; C3 is a falsifiable evaluation protocol with pilot evidence and defers concrete numbers to the evaluation/evidence sections.

- Design goals, lines 105-113 before edit: five goals mixed top-level design goals with fail-closed feedback and adapter coverage.
  After edit: compressed to four top-level goals: intent-bounded authority, context no-promotion/influence separation, stateful lease lifecycle, and multi-boundary transaction API. Fail-closed feedback and adapter coverage are now described as mechanism requirements.

- Goal map, lines 121-129 before edit: text/table mismatched evaluation mappings.
  After edit: one authoritative table now maps each goal to contribution and primary/secondary evaluations. G1 is E1/E2, G2 is E3/E1, G3 is E3/E2, and G4 is E4/E1,E3.

- Authority inputs, lines 229-236 before edit: wording still suggested capability is jointly determined by all four context planes.
  After edit: clarified that only required protected fields must be proven by their owner plane; unneeded planes can be empty.

## Verification

Compiled from `docs/autopaper` with:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex
```

Checked for undefined citations, undefined references, and overfull boxes. No matching warnings remained; only underfull table warnings remained.

## Remaining Concerns

- Full-paper contribution C3 must eventually become an actual evaluation result claim after E1-E4 are complete.
- If workload characterization is completed, the full-paper contribution list may become four items: model, system/runtime, workload characterization, and evaluation.
