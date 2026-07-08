# Round 7: Language Word Choice

Date: 2026-07-08

## What Was Checked

Applied the `paper-writing-style` word-choice pass to `docs/autopaper/intentcap-paper-zh.tex`, with emphasis on jargon inflation, vague referents, internal artifact terms, redundant hedging, and prose that sounded like an experiment ledger rather than a paper.

## Findings

Must-fix findings:

- The abstract used internal run names such as `probes`, `checker-submitted attempts`, and `OS-monitor-style replay target inspired by ActPlane`.
- The introduction introduced the four input classes with loose wording such as `这个根因`, `generic context`, and `ontology claim`.
- The implementation section used project-log phrasing such as `Python-based harness`, `probes`, `policy target`, and `fresh user-simulator loop`.
- The evaluation methodology used `closest baseline labelers`, `trace-level policy-family abstractions`, and `artifact reproduction`, which obscured the baseline being compared.
- The evidence-boundary section mentioned the internal `Rxxx artifact ledger`, which belongs in artifact documentation rather than the paper body.

Should-fix findings:

- Reduce compound-term clustering around `issuer collapse`, `authority-state split`, `authority field`, and `context privilege`.
- Replace vague `这个/这些/这里` where a concrete referent was easy to name.
- Make the formal comparison with policy DSLs neutral rather than argumentative.
- Recast E1/E3/E4 from artifact/run names into claim-facing evidence.
- Reduce repeated `residual` terminology and use `counterexample` or `weakened-variant test` where appropriate.
- Make limitations sound like evidence boundaries rather than progress status.

## Changes Made

- Abstract result sentence:
  - Before: “当前原型执行 ... 本地 probes ... checker-submitted attempts ... OS-monitor-style replay target inspired by ActPlane.”
  - After: “原型在 ... 边界执行 lease checks ... 本地多边界执行实验 ... 模拟 OS monitor 的 replay backend.”

- Four-class motivation:
  - Before: “这个根因要求系统区分四类 proof boundary ... generic context ... ontology claim.”
  - After: “Issuer collapse 和 authority-state split 要求系统区分四个 proof-carrying input classes ... 四类划分是 checker interface claim.”

- Implementation surface:
  - Before: “Python-based agent authorization harness”, “context/delegation probes”, “policy target”, and “wrapper matrices.”
  - After: “agent authorization runtime”, “boundary tests”, “OS-monitor-style replay backend”, and “baseline policy comparisons.”

- Baseline language:
  - Before: “closest baseline labelers / trace-level policy-family abstractions / artifact reproduction.”
  - After: “checkable baseline predicates” and “not complete system reproductions.”

- E1/E3/E4 evidence:
  - Before: “3,746-event matrix”, “residual tests”, “placement probes”, and “object-only wrappers.”
  - After: “protected-event cases”, “controlled counterexample suite”, “placement tests”, and “object-only policies.”

- Evidence boundary:
  - Removed the internal “Rxxx artifact ledger” sentence from the main paper.
  - Rewrote limitation language from “current project-author first-pass” style toward bounded evidence claims.

## Remaining Concerns

- Some English technical terms remain intentionally because they are part of the paper vocabulary: `protected decision`, `lease`, `checker`, `provenance`, `target` as in `delegation target`, and table status `Target`.
- The pass did not alter any quantitative result, citation, theorem statement, or claim boundary.
