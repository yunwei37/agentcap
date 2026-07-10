# Round 1: Problem Framing

Date: 2026-07-10

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`, focusing on abstract, introduction, four-context framing, contribution list, E3 framing, and scope discipline.
- `iter-refine-writing-idea/references/idea-quality-checklist.md`, Section 1 problem framing.

Findings:
> Must-fix: 当前 framing 偏防御、偏窄。R274 后系统已经有 integrated workflow evidence，但摘要和引言仍反复说 “local / bounded / not production / not ActPlane”，读起来像在提前撤退。

> Must-fix: Root cause 有了 “issuer collapse” 和 “authority-state split”，但太快进入术语，缺少让读者先感到痛点的具体后果。

> Must-fix: Problem framing 有一点从 “context influence capability” 漂移到 “authority-state commit object”。需要明确三层 spine：context influence 是要保护的安全对象；field-owned lease 是授权表达；authority-state commit object 是 runtime linearization mechanism。

> Must-fix: 四类 context 的解释已经充分，但有些地方像 taxonomy defense。需要用 safe-merge theorem/test 作为主句。

> Must-fix: E3 的 R274 结果是当前最像系统实验的证据，但正文把它称为 “sanity check”。

> Must-fix: C4 写成 “evaluation contribution” 容易显得 padding。建议收成 3 个贡献：Model、Runtime/System、Evaluation Evidence。

What was changed:
- Abstract line 31: removed the defensive “not kernel/ActPlane mediation” phrasing from the first screen and reframed the OS-monitor path as a deterministic replay target.
- Introduction line 40: added a concrete failure trace: consumed-lease reuse, PDF-derived approval reason, and parent one-shot authority handed to child subagent.
- Introduction line 46: added the three-layer spine: context influence as protected object, field-owned lease as authorization expression, authority-state commit object as runtime linearization mechanism.
- Contributions lines 54-60: collapsed four bullets into three contribution classes: model, runtime/system, and evaluation evidence.
- Goal map lines 145-154: updated contribution mapping so G4 maps to C2 and the guardrail maps to C3.
- Authorization input section line 202: made safe-merge test the lead sentence and bounded the four-class claim to current workloads/adapters.
- Formal model lines 343-347: added a root-cause-to-invariant bridge from issuer collapse, authority-state split, and indirect boundary bypass to no-substitution/no-promotion, atomic check/consume, and pre-effect adapter contract.
- E3 lines 840 and 889-895: reframed R274 as an integrated local workflow experiment, not a sanity check, and stated its shared-session claim directly.
- Related work table lines 960-965: changed “does not default to” wording to an equivalence-interface criterion.

Remaining concerns:
- Abstract still contains several numbers. This is acceptable for now because paper-number audit tracks them, but the writing refinement pass should consider moving some detail to the evaluation summary.
- Threat-model wording remains conservative. Later writing rounds should ensure scope boundaries are stated in `范围与局限` without weakening the first-screen claim.
- The full iter-refine-writing-idea cycle still requires novelty attack/defense, contributions/goals review, cross-alignment, and stress-test rounds.
