# Round 3: Contributions and Goals

Date: 2026-07-07

## What Was Checked

Round 3 checked whether the Chinese paper's contribution list, design goals, four-context model, ActPlane/env positioning, and E1--E4 evaluation goals align with the top-conference claim. A read-only subagent reviewed `docs/autopaper/intentcap-paper-zh.tex` against the idea-quality checklist.

## Findings

The reviewer judged that the paper no longer reads like a simple MCP/tool-call permission system. The four-context framing now reads as a system-level agent decision authorization model because authority is represented as a stateful transaction over agent, instruction, tool, and env context.

Must-fix findings:

- C3 was written as an evaluation plan, not a top-conference evidence contribution.
- C2 could still look implementation-light unless it is framed as a transaction API and the ActPlane/env boundary remains explicit.
- The formal model needed per-decision field requirements, not only `Solve_\Gamma(C_agent, C_inst, C_tool, C_env)`.

Should-fix findings:

- G4 combined untrusted compiler, deterministic recovery, lowering contracts, and prototype scope.
- The boundary between user-derived agent context and user-derived instruction context needed sharper wording.
- E1 should remain end-to-end outcome, while E3 should remain mechanism proof over same event schemas.

## Changes Made

- Rewrote C2 as a `four-input authorization transaction API` rather than a generic runtime.
- Rewrote C3 as current prototype evidence boundary plus final E1--E4 result requirement, not merely an experiment plan.
- Split the former G4 into `Untrusted compiler with deterministic recovery` and `Multi-boundary lowering`.
- Clarified that trusted issuer-canonicalized user intent enters agent context, while user workflow/procedure guidance enters instruction context and cannot authorize sinks, approvals, or delegation by itself.
- Added formal `Req(d)=<A_d,I_d,T_d,E_d>` per-decision requirements and a representative decision-requirement table.

## Remaining Concerns

- A representative env/ActPlane-style local script/file/process/network adapter experiment is still needed for a stronger system contribution.
- Final C3 must eventually become quantitative results, not a boundary statement.
