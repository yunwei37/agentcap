# Round 8 - Terminology and Claim Tone

Date: 2026-07-10

## What Was Checked

Round 8 of `iter-refine-writing` checked `docs/autopaper/intentcap-paper-zh.tex` for invented-term density, unstable terminology, and self-attacking claim tone. The pass used the `paper-writing-style` focus on terminology/claim tone and the shared `common-pitfalls.md` rules, especially:

- avoid jargon inflation after first definition;
- keep scope-bearing hedges, but remove apology-like or reviewer-rebuttal phrasing;
- use one canonical term where possible.

## Reviewer Findings

Must-fix findings:

- The abstract introduced too many coined terms before definition: `pre-effect commit`, `field-owned`, `proof-owner`, `no-owner collapse`, and `protected decisions`.
- The introduction used self-attacking tone in the sentence beginning "原型评估只支持..." even though the intended claim is a bounded positive safety property.
- The core insight paragraph mixed `runtime-visible pre-effect commit record`, `field-owned lease`, `safe-merge criterion`, `proof owners`, and four owner names before the formal section.
- The owner/context vocabulary used too many near-synonyms: `authority-input owner classes`, `proof-owner equivalence classes`, `owner class`, `proof-owner class`, `issuer class`, and `context class`.

Should-fix findings:

- The motivating workflow repeated the local-XLSX vs GitHub-issue authority contrast.
- The four proof questions were clear but should appear in plainer language before the dense formal vocabulary.
- E3 repeated the production-MCP/ActPlane/subagent/prompt-runtime boundary in consecutive sentences.
- The bubblewrap paragraph ended with rebuttal-like negative phrasing.
- The current-evidence table title "but expert minimality is not yet proven" weakened the row.
- The diagnostic recovery row reads like a run ledger, but it contains audit-required boundary tokens.

Consider findings:

- `pre-effect commit`, `protected-decision`, `owner class`, and `env projection` remain frequent; after definition, use plainer phrases when possible.
- Use `runtime observation` in prose before abbreviating to `env`.
- Avoid whole English result sentences in the Chinese abstract.

## Changes Made

- Abstract:
  - Replaced the early coined phrase "pre-effect commit" with "副作用、prompt placement 或 handoff 前提交的决策记录".
  - Replaced `field-owned, intent-derived capability lease` / `proof-owner` wording with "带字段签发者证明的 intent-derived capability lease" and four plain proof sources.
  - Rewrote the final result sentence in Chinese.

- Introduction:
  - Replaced "linearize actions / protected-decision transitions" with "只串行化 actions，没有在副作用前提交产生这些 actions 的受保护决策".
  - Rewrote the core-insight paragraph around four proof questions and a unified pre-effect check point, leaving `safe merge` and owner-equivalence details to later sections.
  - Replaced "原型评估只支持..." with a positive bounded safety claim.
  - Shortened the contribution labels to reduce compound jargon.

- Motivation and authorization input:
  - Merged the repeated local-XLSX / GitHub-issue Skill authority example.
  - Standardized prose on `owner class` as the canonical term.
  - Replaced `authority-input owner classes`, `proof-owner equivalence classes`, and related synonyms with `owner classes`.
  - Reworded the table caption from `Field-owner equivalence classes` to `Field-owner classes`.

- Formal model:
  - Changed the safe-merge condition explanation from "not all systems must..." phrasing to "更细或更粗的实现必须证明同样的接受关系不被改变".
  - Replaced "接受...必须和状态更新一起线性化" with "一起提交".
  - Replaced the self-attacking "不是本文反驳的表达力问题" sentence with a direct interface condition.
  - Reframed the ontology boundary as "本文 claim 限定在覆盖的 ... boundaries".

- Evaluation and related work:
  - Consolidated E3's scope boundary into one positive setup paragraph.
  - Reframed E3 as `local multi-boundary enforceability`.
  - Rewrote the bubblewrap row as an OS-contrast probe rather than a rebuttal about what it is not.
  - Changed the evidence table row title to `Lease auditability and minimality boundary`.
  - Reworded related-work positioning around default runtime authorization objects and removed the remaining `linearize` prose.
  - Replaced the conclusion's `runtime linearization object` with "运行时提交对象".

## Deliberate Non-Changes

- The diagnostic recovery row in Table `current-evidence` remains verbose. It contains audit-required scope tokens such as `0 feedback-attempted tasks`, `recovery gate`, `0/2 tool-oracle passes`, and `retail tasks 3 and 4`. Compressing it without updating the audit script would break the paper-number/scope-token consistency gate.
- Numeric values and citations were treated as read-only in this language round.

## Remaining Concerns

- The paper still uses `pre-effect commit` and `protected-decision` frequently because they are the core model terms. The current pass reduced front-loaded terminology and removed unstable synonyms, but later flow/layout rounds can still replace some post-definition occurrences with "提交记录" or "受保护转移" where no precision is lost.
- E3 is clearer, but the current evidence boundary still needs stronger future experiments for production MCP, ActPlane/eBPF, independent expert labels, and end-to-end utility/recovery.
