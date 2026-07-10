# Round 8: Terminology and Claim Tone

Date: 2026-07-10

Target: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Focus: invented terms, compound jargon, self-attacking sentences, redundant hedges, and scope-bearing hedges that must be preserved.

## Findings

Read-only subagent review found no core invented term that must be deleted. The main problems were term density in the abstract and several evidence-boundary sentences written as negative disclaimers.

Must-fix items:

- Contribution list: the evaluation contribution listed benchmark-scale utility, approval burden, independent oracle, and production backend gaps directly inside the contribution bullet. This made a scope boundary read like self-criticism.
- E3 boundary summary: the sentence "不是 production backend，也不是 benchmark-scale utility 结果" was a self-attacking scope statement.

Should-fix items:

- Abstract result sentences used too many internal labels before definitions, including `protected-event model`, `pre-effect commit interface`, and `owner/lifecycle`.
- The introduction sentence "四类来源不是 component taxonomy，而是 proof ownership" was correct but too abstract.
- The owner-class definition paragraph introduced too many terms at once.
- The formal safe-merge discussion used consecutive negative scope statements around taxonomy minimality.
- The lifecycle-equivalence paragraph inserted an audit-id experiment gap into theorem flow.
- Recovery and Qwen diagnostic paragraphs led with negative utility boundaries rather than the diagnostic purpose.

Consider items:

- Keep core terms such as `protected-decision`, `pre-effect commit`, `checker-owned`, and `authority-state`, because they are defined formal terms.
- Preserve scope-bearing hedges in the evidence-boundary section, but rewrite them as "current evidence supports X; extrapolation to Y needs Z."

## Changes Made

- Rewrote the abstract result sentences to use plainer terms before definitions: "带 lease 的事件模型", "同一提交接口", "字段代填", and "lease lifecycle violations".
- Rewrote the contribution bullet for evaluation so it states the current evidence and points extrapolation boundaries to Section~\\ref{sec:evidence-status}.
- Rephrased the four-context thesis in the introduction as proof ownership by protected field, not component taxonomy.
- Split the owner-class definition into a definition paragraph and a proof-role paragraph.
- Rewrote safe-merge and three-class-collapse scope statements as positive bounded claims over tested adapter surfaces and collapsed owner interfaces.
- Rewrote the lifecycle-equivalence paragraph so audit id is described as an audit/debug aid rather than an unproven safety-field gap.
- Rewrote E2, E3, Qwen diagnostic, recovery diagnostic, lease audit, and limitations prose to use neutral "evidence boundary / extrapolation object" language.
- Updated the paper evidence audit script to look for the new neutral boundary phrases instead of the old self-attacking phrases.

## Rejected Or Deferred

- Did not remove `protected-decision`, `pre-effect commit`, `checker-owned`, or `intent/agent-runtime`; these are core formal terms and already have definitions.
- Did not delete scope-bearing evidence boundaries. They are necessary to avoid overclaiming benchmark-scale utility, production ActPlane/MCP deployment, or independent expert minimality.
- Did not merge the motivation and design descriptions of the four owner classes. The motivation section answers "why four rather than three"; the design section gives the owner-class definition.

## Verification Plan

- Run the paper evidence audit after the wording changes, using a fresh run id.
- Run focused pytest targets covering evidence audit, protocol-gap analysis, local LLM task gateway, and local LLM lease corpus.
- Rebuild the Chinese paper with XeLaTeX.
