# Design

Last updated: 2026-07-03
Stage at update: stage 3 adapter-informed design
Source/command: AgentDojo, MCPTox, InjecAgent export/checker probes plus gateway replay, R014 AgentDojo inferred-event audit, R015 MCPTox reconciliation audit, R016 benchmark-derived live gateway execution, R017 official cached prompted-output gateway replay, R018 cached-output aggregate, R019 InjecAgent authority-minimization analysis, and R020 MCPTox authority-minimization analysis
Completeness: partial

## System-Under-Test Model
IntentCap is evaluated as a run-time authorization layer for LLM agent extensions. The first prototype should support two modes:

1. Offline trace checker: consumes benchmark trajectories, reconstructed plans, context labels, and candidate actions; reports whether each high-impact event has an authorized lease and allowed control provenance.
2. Online harness wrapper: exposes leased tools/MCP methods to an agent, validates arguments, and records provenance decisions before allowing execution.

The offline checker is the cheapest path to validate the core idea against existing benchmarks before implementing every enforcement adapter.

## Components And Data/Control Flow
| Component | Role | Trusted? | Inputs | Outputs |
|---|---|---|---|---|
| Intent certificate issuer | Canonicalizes user goal, selected objects, sinks, constraints, approvals, expiry | trusted | user request, selected files/resources, admin policy | structured intent certificate |
| Context labeler | Assigns origin, integrity, confidentiality, purpose, and influence modes | trusted for labels, not for content | tool outputs, documents, Skill/MCP metadata, user inputs | labeled context cells |
| Effect extractor | Converts plans/trajectories/actions into security-relevant events | untrusted/checked | model plan, benchmark trace, tool call, script call | effect IR with data/control provenance |
| Lease compiler | Proposes minimum-risk leases | untrusted | intent, labels, effect graph, extension summaries | candidate leases and proof objects |
| Deterministic checker | Accepts or rejects leases/events | trusted | policy, intent, labels, leases, effect | allow/deny plus reason |
| Gateway replay/runtime adapter | Enforce accepted leases one attempted event at a time | trusted per boundary | accepted lease set, event stream | exposed operation/object pairs, block/execute decisions, summaries |
| Live tool gateway | Execute registered tool callables only after checker allow decisions | trusted per boundary | accepted lease set, event stream, tool registry | tool results, blocked actions, side-effect audit |
| Audit logger | Preserves decisions for analysis | trusted | checker verdicts, runtime events | result files for evaluation |

## Interfaces And Instrumentation Points
- Intent certificate format: JSON/YAML object with actor, goal, objects, sinks, constraints, approvals, expiry.
- Context label format: JSON/YAML object keyed by context source ID and allowed influence modes per decision class.
- Effect IR: `ctx.use`, `tool.call`, `mcp.call`, `fs.read`, `fs.write`, `exec.run`, `net.connect`, `approve.request`, `subagent.spawn`.
- Lease format: holder, operation, object predicate, argument predicate, intent reference, influence constraints, flow constraints, temporal guards, budget, expiry, delegation.
- Checker API: `check_event(policy, state, leases, event) -> verdict`.
- Benchmark adapter API: `load_tasks()`, `label_context(task)`, `events_from_trace(trace)`, `oracle(task, verdicts)`.

## Protected Decision Classes
| Decision class | Examples | Required influence authority |
|---|---|---|
| Tool choice | choose Gmail vs GitHub vs shell | plan/tool-select |
| Sink selection | repo, recipient, host, account, ticket project | sink-select/authorize |
| Approval scope | request one issue vs broad repo token | authorize |
| Delegation | spawn subagent with context/leases | delegate |
| Policy update | load Skill, expand allowlist, change constraints | authorize |
| Local execution | script path, argv, file writes, network endpoint | execute/parameterize with trusted control |
| Data content | spreadsheet cells, issue body, summary text | quote/summarize/parameterize |

## Durable State And Trust/Failure Boundaries
- Trusted state: intent certificates, global policy, label rules, checker state, active leases, budgets, audit log.
- Untrusted state: LLM-generated plans, Skill instructions unless signed/trusted, MCP tool descriptions/results unless server trusted, external documents, subagent summaries, script stdout/stderr.
- Failure boundary: if provenance is unknown, the checker denies protected decisions but may allow low-authority data use.
- Delegation invariant: a child lease set must be a subset of parent authority unless a trusted issuer creates a fresh lease.

## Assumptions And Invariants
- The LLM can propose but cannot decide authority.
- A high-impact event must match an active lease and derive from the current intent certificate.
- Data provenance and control provenance are distinct; untrusted context may be data provenance for output content without being control provenance for sink/tool/approval decisions.
- Runtime adapters can enforce concrete allow/deny outcomes for the boundaries they cover.
- The first prototype may over-approximate provenance; false denials are acceptable if they are measured and recoverable.

## Alternatives Considered
| Alternative | Why insufficient alone | How IntentCap uses or compares |
|---|---|---|
| Static tool allowlist | misses context influence and is often over-broad | baseline |
| Skill manifest policy | Skill-centric rather than run-centric | baseline for Skill workflows |
| Human approval | users may approve broad scopes and may not see hidden influence | baseline and fresh intent source |
| OS monitor only | enforces effects after policy exists; does not know policy provenance | optional backend |
| Prompt-only defense | model remains the component being attacked | out-of-TCB comparison |
| CaMeL-style control/data split | strong but oriented around trusted-query program flow | closest conceptual comparison |

## Design Risks And Validation Hooks
| Risk | Validation hook |
|---|---|
| Control provenance is too hard to infer from natural model traces. | Start with benchmark traces and explicit event instrumentation; measure unknown-provenance denials. |
| Lease compiler overfits to hand-written policies. | Compare expert oracle, LLM-only compiler, and deterministic checker acceptance. |
| Intent certificates become broad approvals. | Track approval scope breadth and wrong-sink denials. |
| Utility collapses under strict checking. | Measure benign task completion and structured denial recovery. |
| Same-claim risk with CaMeL/Task Shield/Progent. | Keep ablations that isolate intent certificates, influence modes, and proof-carrying leases. |

## Adapter Findings So Far
- AgentDojo workspace injection tasks split into two useful classes. Six of 14 injection tasks provide non-empty ground-truth tool-call traces, which can be replayed as explicit protected-decision events. The remaining eight are natural-language attack goals without ground-truth calls; R011 adds a conservative goal-inferred adapter for them, but those inferred events are explicitly not official benchmark trajectories.
- The current AgentDojo exporter labels `agentdojo_injection_goal:*` as untrusted context that may `parameterize` tool arguments or be summarized, but may not control `sink_select` or `authorize` decisions. This directly tests IntentCap's central distinction between data influence and authority-bearing control influence.
- AgentDojo R011 expands workspace coverage from 10 ground-truth protected events to 64 total events: 10 official ground-truth events and 54 goal-inferred abstract events. The checker/gateway block all 64. The design implication is useful for coverage, but final paper counts must keep ground-truth and inferred events separate.
- R014 makes that separation mechanical. The task-level audit marks `injection_task_0` through `injection_task_5` as `official_ground_truth_replay` with 10 paper-ready benchmark trajectory events, and `injection_task_6` through `injection_task_13` as `goal_inferred_needs_review` with 54 adapter-only events. This audit gate should be applied to future benchmark adapters whenever they mix official trajectories with reconstructed protected decisions.
- MCPTox should be modeled differently from AgentDojo replay: the poisoned MCP tool description is the untrusted context source, and the protected event is often a legitimate downstream tool call selected or parameterized under that metadata's control. The adapter should therefore emit provenance such as `mcp_tool_description:<server>:<tool>` rather than treating the tool output as the attacker source.
- The first MCPTox exporter follows that model: each response labeled `Success` is parsed into one or more concrete `mcp.call` events, while the poisoned tool description is recorded as control and data provenance. The label for that metadata allows only quote/summarize use, so protected `authorize`, `sink_select`, and `tool_select` decisions are denied even if an overbroad operation lease exists.
- MCPTox also creates a useful parser robustness problem: some successful responses contain malformed dicts, embedded JavaScript, or nested code blocks. R007 addresses this with a bounded fallback extractor that preserves the tool name and a raw argument prefix. These fallback events should remain marked separately from structured parses for oracle-quality analysis.
- R015 reconciles MCPTox count units. The design rule is that benchmark cases, authentic tools, generated poisoned-tool records, model Success labels, and IntentCap replay events are different units: 1,348 cases, 353 authentic server tool-name references, 485 generated poisoned-tool records, 1,834 Success labels, and 2,148 replay events. Because 115 replay events are fallback parses with raw argument snippets, argument-level claims should use structured/fallback splits.
- InjecAgent exercises a different path from MCPTox. The untrusted source is not a poisoned MCP tool description; it is a benign user-tool response whose content contains an attacker instruction. The exported protected events are attacker-tool calls expected by the benchmark's synthesized cases. This gives a second tool-response/context-influence workload beyond AgentDojo's smaller ground-truth subset.
- InjecAgent base-setting export currently treats every attacker tool as a protected decision controlled by the injected tool response. Direct-harm tools are labeled `authorize`; exfiltration sinks such as `GmailSendEmail` are labeled `sink_select`; data-reading attacker tools in data-stealing chains are labeled `authorize`.
- The first runtime-facing layer is `TraceGateway`, a gateway replay adapter over the checker. It exposes leased operation/object pairs, authorizes each attempted event independently, and records whether the action would execute or be blocked. R009 validates the same gateway path over AgentDojo, MCPTox, and InjecAgent traces.
- R010 adds a mixed InjecAgent replay path: the benchmark's original user-tool call is labeled as trusted user-intent control and allowed as `tool_select`, while attacker-tool calls from the injected tool response remain denied as `authorize` or `sink_select`. This is the first adapter result that exercises allowed benign control and denied injected control in the same trace, though it is still deterministic replay rather than live model execution.
- R012 repeats the mixed InjecAgent replay on the enhanced setting. Under the current event extractor, enhanced and base settings produce identical event/verdict counts, so enhanced does not currently exercise a different IntentCap mechanism; it is a consistency check for the adapter.
- R013 adds a local `LiveToolGateway` smoke test. A trusted `product.lookup` callable executes and returns data, while a registered `email.send` callable controlled by untrusted product-review text is blocked before side effects occur. This validates the runtime boundary shape, but not model-driven benchmark utility.
- R016 extends the `LiveToolGateway` path to the full saved R010 mixed InjecAgent trace. The runner registers local no-op callables for all 79 tool objects in the trace, executes all 1,054 trusted user-tool events, and blocks all 1,598 registered attacker-tool events before their callables run. This validates live callable suppression over a benchmark-derived trace, but it is still not a prompted-model or external-tool benchmark execution.
- R017 connects `LiveToolGateway` to InjecAgent's released GPT-4 ReAct base outputs. The runtime executes trusted benchmark setup calls, then blocks all benchmark-labeled model-produced attacker decisions from those cached outputs. This is the first model-output-aware live gateway run, but it remains cached-output replay rather than fresh online inference. Its stage-2 data-stealing events are counterfactual because an actual IntentCap run would stop after the stage-1 denial.
- R018 aggregates that cached-output path across the released InjecAgent output archive. This validates that the live gateway decision shape is stable across many model/prompt/settings outputs, but it also exposes an artifact-integrity boundary: one released result row has incomplete case coverage. The design implication is that aggregate scripts must report coverage anomalies as first-class output, not silently fold them into totals.
- R019 adds an authority-minimization view over the R010 mixed trace. The key design implication is that object-scope policies are not enough even when they appear narrow: a per-task single-tool allowlist has the same tool count as IntentCap but still admits one injected same-tool event because it lacks provenance constraints. Toolkit/server-level static authorization is much wider, exposing 9.59 tools per case on average and admitting 77 injected attacker events. This supports keeping influence/provenance checks as first-class lease predicates, not only as a tool-exposure minimizer.
- R020 repeats the minimization question in MCPTox and makes the provenance point sharper. An exact-tool MCP ACL exposes the same 1.0 object per event as IntentCap but admits all 2,148 poisoned-description-controlled calls because it ignores control provenance. Authentic server-level MCP authorization exposes 9.76 tools per event and admits 2,058. The design implication is that IntentCap leases need both narrow object predicates and influence/provenance predicates; reducing visible tool count alone does not enforce context authority.
- Benchmark adapters should preserve raw benchmark identifiers in each event so denial explanations can be traced back to a task, server, tool, attack template, or risk category.

## Next Design Action
Implement the next online model/API wrapper or non-InjecAgent utility/minimization wrapper that can classify a small set of actions as:

- allowed data use,
- denied wrong-sink influence,
- denied unauthorized tool choice,
- denied approval-scope inflation,
- unknown provenance false denial.
