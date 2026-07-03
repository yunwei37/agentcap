# Implementation

Last updated: 2026-07-03
Stage at update: stage 4 implementation probes
Source/command: local checker, gateway replay, live tool gateway smoke, AgentDojo/MCPTox/InjecAgent export adapters, R010 mixed replay, R011 AgentDojo goal inference, R012 InjecAgent enhanced replay, R013 live smoke, R014 AgentDojo inferred-event audit, R015 MCPTox reconciliation audit, and R016 benchmark-derived live trace execution
Completeness: partial

## Repository Layout Relevant To The Project
| Path | Role | Status |
|---|---|---|
| `main.tex`, `main.pdf` | frozen two-page workshop abstract from the first drafting pass | existing; do not edit during auto-research |
| `docs/paper-workshop/` | snapshot of the two-page workshop paper | created |
| `docs/autopaper/` | evolving long-form research paper draft | created |
| `docs/idea-story.md` | canonical story, claims, current state | created |
| `docs/background-related-work.md` | canonical novelty, benchmarks, baselines | created |
| `docs/design.md` | canonical system design | created |
| `docs/implementation.md` | canonical implementation plan and commands | this file |
| `docs/evaluation.md` | canonical experiment plan and run tracker | created |
| `src/intentcap/` | prototype checker package | created |
| `src/intentcap/gateway.py` | gateway-style block/execute replay layer over checker verdicts | created |
| `src/intentcap/live_gateway.py` | local live tool wrapper that executes registered callables after checker allow decisions | created |
| `scripts/probe_agentdojo.py` | AgentDojo setup/suite sanity probe | created |
| `scripts/export_agentdojo_intentcap.py` | exports AgentDojo task/tool/injection metadata and injection ground-truth calls into IntentCap JSON traces | created |
| `scripts/audit_agentdojo_goal_inferred.py` | audits saved AgentDojo traces and separates official ground-truth events from adapter goal-inferred events | created |
| `scripts/export_mcptox_intentcap.py` | exports MCPTox labeled successful model responses into IntentCap JSON traces | created |
| `scripts/audit_mcptox_reconciliation.py` | audits MCPTox artifact counts, Success labels, parse methods, and IntentCap replay-event units | created |
| `scripts/export_injecagent_intentcap.py` | exports InjecAgent synthesized attacker-tool cases into IntentCap JSON traces | created |
| `scripts/replay_intentcap_gateway.py` | replays exported traces through the IntentCap gateway abstraction | created |
| `scripts/run_live_gateway_smoke.py` | executes a local live gateway smoke test with one allowed tool and one blocked sink | created |
| `scripts/run_live_trace_gateway.py` | executes saved benchmark-derived traces through the live gateway with registered local callables | created |
| `benchmarks/` | ignored external benchmark clone workspace | created; AgentDojo cloned locally |
| `results/` | raw result outputs and run logs | created; R001-R016 recorded |

## Implementation Milestones
| Milestone | Deliverable | Exit condition | Status |
|---|---|---|---|
| M0: Research scaffold | canonical docs, workshop snapshot, autopaper draft | docs exist and identify next benchmark/action | in progress |
| M1: Core schema/checker | Python checker for intent labels, effects, leases, and verdicts | unit tests for allow/deny examples | partial: minimal JSON checker exists |
| M2: Offline trace checker | CLI that reads JSON events and policy/lease files | can reproduce the PDF wrong-sink example without an LLM | partial: local sanity trace passes |
| M3: AgentDojo adapter | load AgentDojo task metadata/traces or wrap benchmark agent calls | one benign and one adversarial task dry-run logged | partial: metadata, injection ground-truth export, and goal-inferred natural-language replay work; online agent trajectories still pending |
| M4: InjecAgent/MCPTox adapters | parse cases into protected decision events | at least one setup/dry-run or documented blocker per benchmark | partial: MCPTox and InjecAgent trace exporters work; InjecAgent now supports mixed benign/attack traces; online wrappers pending |
| M5: Lease compiler prototype | heuristic compiler from task intent and effect list to candidate leases | compares LLM-only/wide leases vs minimized leases | todo |
| M6: Online enforcement harness | tool gateway/MCP broker/context constructor wrappers | blocks wrong sink in a live toy workflow | partial: local live tool gateway smoke and benchmark-derived live trace execution pass; prompted-model wrapper pending |
| M7: Evaluation scripts | aggregate utility, attack success, over-privilege, false denial, recovery | generates tables for `docs/autopaper` | todo |

## Current Implementation Status
- A minimal offline checker exists under `src/intentcap/`.
- The checker supports exact/prefix/suffix/one-of argument predicates, lease matching, control provenance checks, data provenance checks, and context-label influence-mode checks.
- AgentDojo is cloned locally under ignored `benchmarks/agentdojo` at commit `089ed468` and installed editable into `.venv`.
- AgentDojo suite metadata, workspace ground-truth checks, and IntentCap trace export/checker outputs are recorded in `results/agentdojo/R002/`, `results/agentdojo/R003/`, `results/agentdojo/R004/`, and `results/agentdojo/R011/`.
- R004 exports 10 protected-decision events from the 6 AgentDojo workspace injection tasks that provide non-empty ground-truth tool calls; the checker denies all 10 as untrusted injection-goal control over `sink_select`/`authorize` decisions.
- The AgentDojo exporter now supports `--include-goal-inferred-events`, which emits conservative abstract protected events for injection tasks whose benchmark `ground_truth()` returns no calls. These events are marked `intentcap_event_type: goal_inferred` and `official_ground_truth: false`.
- R011 exports 64 AgentDojo workspace protected events: 10 official ground-truth events and 54 goal-inferred events covering the eight natural-language-only injection tasks. The checker and gateway block all 64 events.
- R014 audits the saved R011 trace, checker verdicts, and gateway decisions. It confirms 6 tasks and 10 events are benchmark-provided ground-truth replay, while 8 tasks and 54 events are adapter-only goal-inferred coverage. All 64 events are denied/blocked, and the audit verdict is `warn` to prevent reporting inferred events as benchmark trajectories.
- MCPTox is cloned locally under ignored `benchmarks/mcptox` at commit `f85189f`; `results/mcptox/R005/` records an artifact probe over its JSON files.
- R006 exports 2,033 protected-decision events from MCPTox responses labeled `Success`; the checker denies all 2,033 as poisoned tool-description control over `authorize`, `sink_select`, or `tool_select` decisions.
- R007 improves parser coverage by adding bounded fallback extraction for malformed Python/JSON-like responses and nested code strings. It exports 2,148 protected-decision events from all 1,834 MCPTox `Success` labels; the checker denies all 2,148.
- R015 audits MCPTox count semantics. It records 45 servers, 353 authentic server tool names, 1,348 malicious cases/data records, 485 generated poisoned-tool records, 1,834 model responses labeled `Success`, and 2,148 IntentCap replay events. It also separates 2,033 structured events from 115 fallback-parsed events.
- InjecAgent is cloned locally under ignored `benchmarks/injecagent` at commit `f19c9f2`; `results/injecagent/R008/` records base-setting schema/export/checker outputs.
- R008 exports 1,598 protected-decision events from 1,054 base-setting InjecAgent cases; the checker denies all 1,598 as untrusted tool-response control over `authorize` or `sink_select` decisions.
- The InjecAgent exporter now supports `--include-user-tool-events`, which emits the benchmark's original user-tool call as trusted user-intent control before replaying injected attacker-tool calls from the same case.
- R012 exports enhanced-setting InjecAgent mixed traces with the same coverage as R010: 1,054 trusted user-tool events allowed/executed and 1,598 injected attacker-tool events denied/blocked. The saved base-vs-enhanced comparison has zero deltas for key counts under the current adapter.
- A reusable `TraceGateway` exists under `src/intentcap/gateway.py`; it exposes leased operation/object pairs, checks one attempted event at a time, and emits block/execute decisions plus aggregate summaries.
- A reusable `LiveToolGateway` exists under `src/intentcap/live_gateway.py`; it authorizes attempted events through the checker and executes registered Python callables only after an allow decision.
- R009 replays AgentDojo R004, MCPTox R007, and InjecAgent R008 through the gateway. The gateway blocks 3,756 of 3,756 attempted protected events.
- R010 replays mixed InjecAgent base-setting traces through the checker and gateway. The checker allows 1,054 trusted user-tool events and denies 1,598 injected attacker-tool events; the gateway executes the same 1,054 events and blocks the same 1,598 events.
- R013 runs a local live wrapper smoke test. It executes one trusted `product.lookup` callable, blocks one registered `email.send` callable controlled by untrusted tool-result text, and records zero sent-email side effects.
- R016 runs the full R010 mixed InjecAgent base trace through `LiveToolGateway` with local no-op callables registered for all 79 tool objects. It executes 1,054 trusted user-tool callables, blocks 1,598 registered attacker-tool callables before invocation, and records 0 missing tools and 0 tool errors.
- The next benchmark step is to build a prompted-model or benchmark-harness live wrapper baseline with utility measurement.

## Build/Run Commands
| Purpose | Command | Status |
|---|---|---|
| Build current workshop PDF | `make` | works as of commit `4ce9892`; root paper should remain frozen |
| Verify workshop PDF page count | `pdfinfo main.pdf | rg '^Pages'` | works; expected `Pages: 2` |
| Unit tests | `PYTHONPATH=src python -m pytest -q` | works: 16 tests passed; `pytest.ini` restricts discovery to this repo's `tests/` |
| Local checker sanity | `PYTHONPATH=src python -m intentcap.checker examples/local_pdf_wrong_sink.json` | works; see `results/local/R001/verdicts.json` |
| AgentDojo suite count probe | `. .venv/bin/activate && python scripts/probe_agentdojo.py --benchmark-version v1.2.2 --suite workspace` | works; see `results/agentdojo/R002/` |
| AgentDojo workspace ground-truth check | `. .venv/bin/activate && python scripts/probe_agentdojo.py --benchmark-version v1.2.2 --suite workspace --check` | warning; see `results/agentdojo/R003/` |
| AgentDojo IntentCap trace export | `. .venv/bin/activate && PYTHONPATH=src python scripts/export_agentdojo_intentcap.py --benchmark-version v1.2.2 --suite workspace --output-dir results/agentdojo/R004 --check` | works; exports 10 events and denies all 10 under current labels |
| AgentDojo goal-inferred trace export | `. .venv/bin/activate && PYTHONPATH=src python scripts/export_agentdojo_intentcap.py --benchmark-version v1.2.2 --suite workspace --include-goal-inferred-events --output-dir results/agentdojo/R011 --check` | works; exports 10 ground-truth events plus 54 goal-inferred events and denies all 64 |
| AgentDojo inferred-event audit | `PYTHONPATH=src python scripts/audit_agentdojo_goal_inferred.py --trace results/agentdojo/R011/intentcap_trace.json --verdicts results/agentdojo/R011/intentcap_verdicts.json --gateway-decisions results/agentdojo/R011/gateway/gateway_decisions.json --output-dir results/agentdojo/R014` | works; R014 records 10 paper-ready ground-truth events and 54 adapter-only inferred events |
| MCPTox artifact probe | `git clone --depth 1 https://github.com/zhiqiangwang4/MCPTox-Benchmark benchmarks/mcptox`; local JSON count probe in `results/mcptox/R005/schema_probe.txt` | works; 45 server groups, 485 tool entries/files, 1,348 cases |
| MCPTox IntentCap trace export | `PYTHONPATH=src python scripts/export_mcptox_intentcap.py --benchmark-dir benchmarks/mcptox --output-dir results/mcptox/R007 --check` | works; exports 2,148 events and denies all 2,148 under current labels |
| MCPTox reconciliation audit | `PYTHONPATH=src python scripts/audit_mcptox_reconciliation.py --benchmark-dir benchmarks/mcptox --trace results/mcptox/R007/intentcap_trace.json --verdicts results/mcptox/R007/intentcap_verdicts.json --output-dir results/mcptox/R015` | works; R015 separates 1,348 cases, 353 authentic tools, 1,834 Success labels, 2,148 replay events, and 115 fallback events |
| InjecAgent IntentCap trace export | `PYTHONPATH=src python scripts/export_injecagent_intentcap.py --benchmark-dir benchmarks/injecagent --setting base --attack-family all --output-dir results/injecagent/R008 --check` | works; exports 1,598 events and denies all 1,598 under current labels |
| InjecAgent mixed benign/attack export | `PYTHONPATH=src python scripts/export_injecagent_intentcap.py --benchmark-dir benchmarks/injecagent --setting base --attack-family all --include-user-tool-events --output-dir results/online/R010/export --check` | works; exports 1,054 trusted user-tool events and 1,598 injected attacker-tool events |
| InjecAgent enhanced mixed export | `PYTHONPATH=src python scripts/export_injecagent_intentcap.py --benchmark-dir benchmarks/injecagent --setting enhanced --attack-family all --include-user-tool-events --output-dir results/injecagent/R012/export --check` | works; same event/verdict counts as R010 under current adapter |
| Gateway replay | `PYTHONPATH=src python scripts/replay_intentcap_gateway.py results/injecagent/R008/intentcap_trace.json --output-dir /tmp/intentcap-gateway-smoke` | works; R009 records AgentDojo, MCPTox, and InjecAgent replay |
| Mixed InjecAgent gateway replay | `PYTHONPATH=src python scripts/replay_intentcap_gateway.py results/online/R010/export/intentcap_trace.json --output-dir results/online/R010/gateway` | works; R010 executes 1,054 trusted events and blocks 1,598 injected events |
| Enhanced InjecAgent gateway replay | `PYTHONPATH=src python scripts/replay_intentcap_gateway.py results/injecagent/R012/export/intentcap_trace.json --output-dir results/injecagent/R012/gateway` | works; R012 executes 1,054 trusted events and blocks 1,598 injected events |
| AgentDojo goal-inferred gateway replay | `PYTHONPATH=src python scripts/replay_intentcap_gateway.py results/agentdojo/R011/intentcap_trace.json --output-dir results/agentdojo/R011/gateway` | works; R011 blocks all 64 events |
| Live gateway smoke | `PYTHONPATH=src python scripts/run_live_gateway_smoke.py --output-dir results/live/R013` | works; R013 executes 1 trusted callable, blocks 1 injected sink callable, and records 0 sent emails |
| Benchmark-derived live trace gateway | `PYTHONPATH=src python scripts/run_live_trace_gateway.py --trace results/online/R010/export/intentcap_trace.json --output-dir results/live/R016` | works; R016 registers 79 tool callables, executes 1,054 benign calls, blocks 1,598 attacker calls, and records 0 missing tools/errors |

## Integration Constraints
- Do not mutate the frozen workshop paper unless explicitly requested.
- Keep durable research memory in the canonical docs; raw benchmark outputs should go under `results/`.
- Record every nontrivial experiment command, commit, machine, seed/repetition policy, and result path in `docs/evaluation.md`.
- Avoid requiring model API keys for smoke tests. Use local/static traces first where possible.
- Treat benchmark setup failures as useful evidence and record them.

## Known Technical Debt And Open Engineering Tasks
- Need formalize the trace JSON schema currently implied by `src/intentcap/checker.py` and `scripts/export_agentdojo_intentcap.py`.
- Need improve checker denial selection once there are multiple plausible leases for the same operation; R004 uses a synthetic `_intentcap_event_id` field for deterministic event-scoped replay.
- R014 separates current AgentDojo goal-inferred event templates from official ground-truth events; future AgentDojo paper counts should use the 10 official events unless an online trajectory run provides new benchmark evidence.
- R015 reconciles MCPTox count surfaces; future MCPTox paper counts should use 1,348 cases and 353 authentic tools, while keeping 1,834 Success labels, 2,148 replay events, and 115 fallback events as distinct units.
- R016 is benchmark-derived local live execution over saved trace events. It proves registered Python callables are invoked only on allowed events and suppressed on blocked events, but it is not a prompted-model, external-tool, or benchmark-harness utility/security run.
- Need reconcile InjecAgent README count of 62 attacker tools with the local base-case count of 63 unique attacker-tool names, where `GmailSendEmail` is the repeated exfiltration sink.
- Need implement a prompted-model or benchmark-harness live wrapper baseline so deterministic trace-level denials and local live execution can be paired with model/tool utility and attack-success metrics.
- Need extend live gateway from local Python callables to MCP/tool mediation with denial recovery.
- Need decide whether to keep external benchmark clones only as ignored local state or convert selected ones into submodules later.

## Next Engineering Action
Build the next evidence step: connect the live gateway to a prompted model or benchmark harness subset to measure model utility and attack blocking under actual tool exposure.
