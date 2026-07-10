# Round 4 - Cross-Alignment

Date: 2026-07-09

## What Was Checked

Read-only cross-alignment review of problem framing, insight, design goals, contributions, implementation scope, and evaluation claims in `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`.

## Findings

The reviewer found the main line coherent:

- Problem: issuer collapse plus authority-state split.
- Insight: a multi-issuer, lifecycle-mutating protected-decision transition must be exposed as a pre-effect runtime linearization object.
- Goals: G1/G2 address issuer ownership, G3 addresses lifecycle mutation, and G4 addresses boundary exposure.
- Evidence: E3 is the core mechanism experiment, E4 is the system-interface experiment, and E1/audit are guardrail/supporting evidence.

Must-fix items:

1. G4 and C3 implied broader Tool/MCP/MCP-broker coverage than E4's primary evidence. E4 covers local env, context placement, delegation, Skill placement, and OS-monitor-style lowering; live callable gateway is implemented surface but not E4's primary row.

2. The `Subagent handoff` row in the owner-class table used `Agent + Env` as an owner class, conflicting with the formal rule that each protected field proof has a unique issuer owner.

3. C3 used broad wording around tool/MCP and OS-monitor-style lowering, while the evidence boundary explicitly says production MCP broker and production ActPlane/kernel mediation are not complete.

Should-fix items:

1. Later writing rounds should reduce repeated context-class tables.

2. Implementation and E4 prose still have some artifact/result-log flavor.

3. E1 wording should keep emphasizing replay consistency / implementation sanity.

4. Related-work tables should avoid visual strawman yes/no matrices.

## What Was Changed

1. C3 now says the system implements the contract on implemented local callable, env side-effect, prompt/Skill placement, delegation boundaries, and OS-monitor-style replay lowering.

2. G4 now says local callable/env side effects, prompt/Skill placement, and authority handoff must expose the same protected transition. It no longer implies production MCP broker coverage.

3. The goal map G4 row now matches the narrowed claim.

4. The subagent handoff row now says `Required projections: Agent(parent authority, child role) + Env(context slice)` rather than listing `Agent + Env` as an owner class.

5. E4 now explicitly says live callable gateway is an implemented surface, while E4's primary claim is tool-call-outside pre-side-effect, pre-placement/handoff, and monitor-lowering equivalence.

6. The evidence-boundary table now lists production MCP broker as missing evidence for a stronger deployment claim.

7. The policy-DSL paragraph now states that the paper makes the required runtime object explicit, rather than inventing a stronger predicate.

## Remaining Concerns

The remaining issues are writing-level presentation problems: table redundancy, implementation prose sounding like an artifact list, E4 prose sounding like a result log, and related-work table tone. These should be handled in `iter-refine-writing`.
