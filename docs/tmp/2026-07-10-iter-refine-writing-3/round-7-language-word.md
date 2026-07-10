# Round 7 -- Language: Word Choice

Date: 2026-07-10

## What was checked

Checked `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex` for Round 7 word-choice issues from `iter-refine-writing`: jargon inflation, nominalizations, weak referents, redundant hedging, verbose phrases, project-report wording, and repeated compound terms.

The read-only reviewer focused on the abstract, introduction, motivation, authorization-input definition, runtime lowering, safe-merge definition, implementation overview, E2/E3 result prose, discussion boundaries, and related work.

## Findings

Must-fix:

- The abstract used weak referents such as "该模型" and repeated "结果显示".
- The introduction said `\sys 保护 context influence`, which suggests preserving influence rather than limiting unauthorized influence.
- The introduction and discussion had weak phrases such as "这个 protected-decision interface", "claim dependency", and "局部 compiler/model-loop experiments".
- The limitations paragraph stacked English compound adjectives: `instrumented protected-decision events`, `intent-derived`, `provenance-gated`, and `consumable`.

Should-fix:

- The abstract and intro had dense runs of coined terms: `authority-bearing`, `authority-changing`, `checker-owned`, and `proof owners`.
- The motivation reused `run`, `authority`, and `union authority` too often.
- The protected-decision terminology paragraph still contained an old-draft trace: "旧稿中类似 ...".
- The authorization-input and safe-merge definitions mixed too many labels such as `owner classes`, `proof owners`, `protected fields`, `surfaces`, and `workloads`.
- The implementation and evaluation sections used project-report nouns such as `surface`, `checklist`, `block points`, `claim dependency`, and `system-surface summary`.
- Related work used rebuttal-like wording: "最强的相邻工作反驳是".

Consider:

- Keep the first abstract occurrence of `context influence 显式建模为 capability`, because it states the core claim.
- Do not rewrite contribution titles in this round. They are stable anchors for section cross-references and later terminology/claim-tone review can decide whether to translate them.
- Do not rewrite the formal section wholesale in this round. Round 8 terminology review should handle any remaining formal English/Chinese mixtures.
- Recovery diagnostics still use `microbenchmark`, `suite`, `gate`, and `diagnostic`; this round leaves them unchanged because those terms encode evidence scope and should be handled with the experiment narrative if changed.

## Changes Made

- Replaced weak abstract referents with direct mechanism subjects, including "带 lease 的 protected-event model".
- Replaced "本地多边界结果显示" with an experiment-subject sentence.
- Reduced abstract term density by changing `authority-bearing decision` to "高影响决策", `authority-changing transition` to "会改变权限的状态转移", `proof owners` to "owner", and `checker-owned state` to "checker 自有状态".
- Rewrote the introduction's attack consequences in clearer Chinese.
- Replaced `first-class object` with "结构化运行时对象".
- Rewrote `\sys 保护 context influence` as `\sys 限制 context 对 authority fields 的影响`.
- Replaced the prototype-evaluation weak referent with "把 authority-changing transition 作为运行时授权单位".
- Replaced repeated `union authority` wording with "权限并集".
- Removed the old-draft wording from the protected-decision terminology paragraph.
- Simplified authorization-input prose by using "字段", "证明来源", "边界", and "当前任务集" where the full coined terms were not needed.
- Rewrote runtime lowering, safe merge, implementation, and evaluation openings to reduce project-report vocabulary.
- Split the E2 tested-removal paragraph and rewrote the E3 aggregate as a de-duplicated boundary summary.
- Replaced `局部 compiler/model-loop experiments` with `bounded compiler/model-loop experiments`.
- Rewrote the limitations opening to avoid stacked English compound adjectives.
- Replaced the related-work rebuttal phrase with a natural question and simplified the closest-abstractions table explanation.

## Verification Notes

- Experimental numbers were not intentionally changed. A word-diff check found only preserved numeric anchors in rewritten sentences.
- A grep check found no remaining occurrences of the specific project-report phrases flagged by the reviewer: `旧稿`, `claim dependency`, `system-surface summary`, `最强的相邻工作反驳`, `first-class object`, `保护 context influence`, `该模型仍能表达`, `本地多边界结果显示`, or `局部 compiler`.
- Remaining expected risk: high-frequency core terms such as `protected-decision`, `pre-effect commit`, and `intent/agent-runtime` remain intentionally common because they name the paper's formal interface. Round 8 should decide whether any remaining occurrences are terminology inflation rather than necessary anchors.
