# 2026-07-10 Iter-Refine-Writing-Idea Round 2c

## What Was Checked

Round 2c re-attacked the updated novelty framing in `docs/autopaper/intentcap-paper-zh.tex` after the Round 2b defense edits.

## Findings

Reviewer `019f4b53-91b0-7f62-85a2-5a21ba0b57b7` reported that a strong novelty reject is no longer easy, but a bounded reject remains possible:

> The paper has moved from "new policy language" to "runtime linearization object for agent authority transitions." The remaining concern is whether four owners and the commit API are derived from agent runtime/protocol gaps rather than renamed stateful ABAC/IFC.

Must-fix items:

- The safe-merge derivation still needed more operational adjudication steps.
- The runtime-interface claim needed a concrete audit of MCP, Skill, tool gateway, prompt placement, subagent handoff, and OS/local monitor boundaries.
- E2 remains author-adjudicated; a top-conference version needs blinded second-pass or independent adjudication.
- E3 is still a local feasibility suite; a stronger systems claim needs at least one production-like adapter path.

Should-fix items:

- The safe-merge formula mentioned issuer/forge/observe/write but not lifecycle authority.
- User-provided instruction text could be misread as both authority root and instruction context.
- Some earlier sections still used `OS-monitor-style` where `env-projection replay/lowering` is more precise.

## Verdict

Strong novelty reject is no longer easy, but the remaining next evidence gates are independent field-owner adjudication and a more realistic adapter implementation.

## Remaining Concerns

Round 2d should fix the text-level issues without pretending that independent adjudication or production adapter integration is already complete.
