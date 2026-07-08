# Round 2e: Final Insight Re-Attack

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Einstein`, read-only.

## Findings

The reviewer concluded that a strong novelty rejection is no longer easy to construct. The paper now frames the idea as:

> agent extension 的授权单位不是 action、flow、tool permission 或 context label，而是带 issuer-owned field proof、provenance、budget/expiry/delegation update 的原子 protected-decision transition。

The reviewer found this framing visible in the abstract, introduction, authority-input section, and formal field-ownership rule.

## Residual Evidence Risks

- E3 still needs more independent field-owner labels over natural traces to prove issuer-substitution and split-state failures are not only author-constructed residual cases.
- E2 author-adjudicated labels should not support an expert-oracle least-privilege claim without blinded independent adjudication.
- E4 remains local adapters plus an ActPlane-style lowering target, not production ActPlane/kernel integration or full production agent runtime.
- End-to-end utility, approval burden, and recovery remain evidence gaps.

## Decision

The idea layer can proceed to Round 3 contributions/goals. The next task is to compress the contribution list and design goals into 3 top-conference-level claims that map cleanly to E1/E3/E4 and do not overclaim evidence maturity.
