# IntentCap AutoPaper Draft

Last updated: 2026-07-03
Status: early research draft; not the frozen two-page workshop abstract

## Working Title
IntentCap: Intent-Carrying Capabilities for LLM Agent Extensions

## Abstract Draft
LLM agents increasingly rely on extension ecosystems: Skills that provide workflow instructions and scripts, MCP servers that expose tool catalogs and external data, local programs that transform files, and subagents that decompose tasks. These extensions create authority even when they do not hold credentials directly. Their text can influence future decisions about which tool to call, which sink to use, which approval to request, or which component should receive delegated authority. Existing defenses largely authorize operations after a policy exists: tool-call guards validate invocations, manifests describe extension permissions, and OS monitors enforce file or network restrictions. They do not directly specify which context may influence which authority-bearing decision under the user's current intent.

IntentCap treats user intent as the root principal and context influence as a least-privilege capability. A trusted intent certificate records the current goal, selected objects, authorized sinks, constraints, approvals, and expiry. Context cells receive provenance labels and allowed influence modes. A capability lease authorizes an operation only when the operation is derivable from the intent certificate and the operation's control provenance is allowed to influence that decision class. An LLM-assisted frontend may propose plans and leases, but a deterministic checker validates provenance, flow, temporal, budget, and delegation constraints before enforcement.

The research plan is to validate IntentCap first as an offline trace checker and then as an online enforcement layer across context construction, tool calls, MCP mediation, local execution, and delegation. The evaluation will adapt existing benchmark families rather than rely only on toy examples: AgentDojo and InjecAgent for indirect prompt injection, MCPTox for MCP tool poisoning, and tau/MCP benchmarks for benign utility and policy-following. The intended claim is scoped: within modeled decision classes and enforced boundaries, IntentCap blocks unauthorized context-to-decision influence while preserving useful data use.

## Paper Shape
1. Introduction: context is a source of control authority in agents.
2. Threat model: untrusted documents, tool outputs, Skill instructions, MCP descriptions/results, and subagent summaries try to steer authority-bearing decisions.
3. Model: intent certificates, context labels, influence modes, decision classes, data/control provenance.
4. Design: lease compiler, deterministic checker, runtime adapters, delegation attenuation.
5. Prototype: offline checker first; online tool/MCP/context adapters second.
6. Evaluation: AgentDojo, InjecAgent, MCPTox, tau/MCP utility tasks, lease minimization, ablations.
7. Related work: CaMeL, Task Shield, Progent, SkillGuard, ActPlane, EIM/bpftime, agent benchmarks.

## Current Non-Negotiable Claims
- Do not claim IntentCap solves prompt injection.
- Do not claim perfect script-behavior inference.
- Do not claim OS enforcement is unnecessary.
- Do not frame the work as EIM for agents or ActPlane policy synthesis.
- Do claim context influence as least-privilege authority, with user intent as the root of run-time authority.

## Current Evidence Snapshot
- Local motivating trace: the checker allows user-selected PDF-to-spreadsheet and user-selected-repository issue actions while denying a PDF-controlled wrong-repository issue action.
- AgentDojo workspace probe: task/tool metadata loads from the local v1.2.2 install. Six of 14 workspace injection tasks expose non-empty ground-truth tool-call traces; these produce 10 IntentCap protected-decision events. Under the current labels, all 10 are denied because untrusted injection goals are not authorized to control `sink_select` or `authorize` decisions.
- AgentDojo goal-inferred replay and audit: R011 adds a conservative adapter for the eight workspace injection tasks whose `ground_truth()` returns no calls. The resulting trace has 10 official ground-truth events plus 54 goal-inferred abstract events, all blocked by the checker and gateway. R014 audits the saved R011 artifacts and confirms the reporting split: 10 paper-ready benchmark trajectory events from 6 tasks, and 54 adapter-only inferred events from 8 tasks. The inferred events are explicitly marked `official_ground_truth: false`, so they can support adapter coverage but not benchmark-provided trajectory claims.
- MCPTox probe: the official public artifact is available and locally cloned. Its JSON files expose 45 server groups, 485 tool entries/files, 11 attack scopes, and 1,348 cases, making it a plausible next adapter for MCP tool-description poisoning.
- MCPTox successful-response replay: from 1,834 benchmark responses labeled `Success`, the current exporter now parses 2,148 concrete MCP calls: 2,033 structured parses and 115 bounded fallback parses for malformed outputs. IntentCap denies all 2,148 because poisoned MCP tool descriptions are not authorized to control `authorize`, `sink_select`, or `tool_select` decisions. This is the strongest current evidence for the context-authority claim, but it is still offline trace replay rather than an online wrapper result.
- MCPTox limitation: fallback-extracted events preserve only the tool name and a bounded raw argument prefix, so paper-level counts must distinguish structured parses from fallback parses until oracle reconciliation is complete.
- InjecAgent base-setting replay: the local artifact at `f19c9f2` contains 1,054 base-setting synthesized test cases, matching the benchmark headline count. These cases produce 1,598 attacker-tool events across 17 user tools and 63 unique attacker-tool names in the local artifact. IntentCap denies all 1,598 because injected tool-response context is not authorized to control `authorize` or `sink_select` decisions.
- InjecAgent limitation: the README says 62 attacker tools, while the local base cases expose 63 unique attacker-tool names because `GmailSendEmail` is used as the repeated exfiltration sink. This must be reconciled before final numeric claims.
- Gateway replay: `TraceGateway` now replays exported traces through a runtime-facing block/execute interface instead of only emitting batch checker verdicts. Across AgentDojo R004, MCPTox R007, and InjecAgent R008, the gateway blocks 3,756 of 3,756 attempted protected events. This is still trace replay, but it validates the same per-action decision shape needed by a tool/MCP gateway.
- Mixed InjecAgent replay: R010 extends the InjecAgent adapter to emit the benchmark's benign user-tool call as trusted user-intent control before the injected attacker-tool calls. In 1,054 base-setting cases, the checker and gateway allow/execute 1,054 trusted `tool_select` events and deny/block 1,598 injected `authorize`/`sink_select` events. This is the first evidence that the same trace format can preserve benign tool-choice utility while blocking injected authority-bearing decisions, but it remains deterministic replay rather than live model/tool execution.
- InjecAgent enhanced-setting replay: R012 runs the same mixed exporter on the enhanced setting and produces identical event/verdict counts to R010. This is useful as an adapter consistency check, but it does not expand the current security claim because no new decision classes or tool families appear under the current extraction.
- Local live gateway smoke: R013 adds a `LiveToolGateway` path that executes registered Python callables only after checker approval. The smoke run executes one trusted `product.lookup` callable, blocks one registered `email.send` callable controlled by untrusted tool-result text, and records zero sent-email side effects. This validates runtime wrapper mechanics but is not a model-based benchmark run.

## Next Drafting Gate
No more polished claims should be added until one benchmark path produces an end-to-end table with task IDs, protected decision classes, gateway decisions, and an oracle/limitation column, plus at least one live benchmark utility/attack run. R014 supplies the AgentDojo audit table for R011; the remaining immediate candidates are MCPTox oracle reconciliation and connecting `LiveToolGateway` to a benchmark/model subset.
