# Design

Last updated: 2026-07-03
Stage at update: stage 3 adapter-informed design
Source/command: AgentDojo export adapter and MCPTox artifact/response export probes
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
| Runtime adapters | Enforce accepted leases | trusted per boundary | accepted lease set, event stream | scoped context, exposed tools, MCP calls, sandbox policies |
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
- AgentDojo workspace injection tasks split into two useful classes. Six of 14 injection tasks provide non-empty ground-truth tool-call traces, which can be replayed as explicit protected-decision events. The remaining eight are natural-language attack goals without ground-truth calls, so they need a separate goal-to-event classifier or online agent run.
- The current AgentDojo exporter labels `agentdojo_injection_goal:*` as untrusted context that may `parameterize` tool arguments or be summarized, but may not control `sink_select` or `authorize` decisions. This directly tests IntentCap's central distinction between data influence and authority-bearing control influence.
- MCPTox should be modeled differently from AgentDojo replay: the poisoned MCP tool description is the untrusted context source, and the protected event is often a legitimate downstream tool call selected or parameterized under that metadata's control. The adapter should therefore emit provenance such as `mcp_tool_description:<server>:<tool>` rather than treating the tool output as the attacker source.
- The first MCPTox exporter follows that model: each response labeled `Success` is parsed into one or more concrete `mcp.call` events, while the poisoned tool description is recorded as control and data provenance. The label for that metadata allows only quote/summarize use, so protected `authorize`, `sink_select`, and `tool_select` decisions are denied even if an overbroad operation lease exists.
- MCPTox also creates a useful parser robustness problem: some successful responses contain malformed dicts, embedded JavaScript, or nested code blocks. These should become parser-coverage and oracle-quality metrics rather than silent drops.
- Benchmark adapters should preserve raw benchmark identifiers in each event so denial explanations can be traced back to a task, server, tool, attack template, or risk category.

## Next Design Action
Implement the next benchmark adapter that can classify a small set of actions as:

- allowed data use,
- denied wrong-sink influence,
- denied unauthorized tool choice,
- denied approval-scope inflation,
- unknown provenance false denial.
