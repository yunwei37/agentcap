# Implementation

Last updated: 2026-07-03
Stage at update: stage 4 implementation probes
Source/command: local checker, AgentDojo export adapter, MCPTox artifact/response/parser probes
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
| `scripts/probe_agentdojo.py` | AgentDojo setup/suite sanity probe | created |
| `scripts/export_agentdojo_intentcap.py` | exports AgentDojo task/tool/injection metadata and injection ground-truth calls into IntentCap JSON traces | created |
| `scripts/export_mcptox_intentcap.py` | exports MCPTox labeled successful model responses into IntentCap JSON traces | created |
| `benchmarks/` | ignored external benchmark clone workspace | created; AgentDojo cloned locally |
| `results/` | raw result outputs and run logs | created; R001-R007 recorded |

## Implementation Milestones
| Milestone | Deliverable | Exit condition | Status |
|---|---|---|---|
| M0: Research scaffold | canonical docs, workshop snapshot, autopaper draft | docs exist and identify next benchmark/action | in progress |
| M1: Core schema/checker | Python checker for intent labels, effects, leases, and verdicts | unit tests for allow/deny examples | partial: minimal JSON checker exists |
| M2: Offline trace checker | CLI that reads JSON events and policy/lease files | can reproduce the PDF wrong-sink example without an LLM | partial: local sanity trace passes |
| M3: AgentDojo adapter | load AgentDojo task metadata/traces or wrap benchmark agent calls | one benign and one adversarial task dry-run logged | partial: metadata and injection ground-truth export works; natural-language-only attack goals still pending |
| M4: InjecAgent/MCPTox adapters | parse cases into protected decision events | at least one setup/dry-run or documented blocker per benchmark | partial: MCPTox official artifact cloned, schema-count probe recorded, and successful-response trace exporter works; InjecAgent pending |
| M5: Lease compiler prototype | heuristic compiler from task intent and effect list to candidate leases | compares LLM-only/wide leases vs minimized leases | todo |
| M6: Online enforcement harness | tool gateway/MCP broker/context constructor wrappers | blocks wrong sink in a live toy workflow | todo |
| M7: Evaluation scripts | aggregate utility, attack success, over-privilege, false denial, recovery | generates tables for `docs/autopaper` | todo |

## Current Implementation Status
- A minimal offline checker exists under `src/intentcap/`.
- The checker supports exact/prefix/suffix/one-of argument predicates, lease matching, control provenance checks, data provenance checks, and context-label influence-mode checks.
- AgentDojo is cloned locally under ignored `benchmarks/agentdojo` at commit `089ed468` and installed editable into `.venv`.
- AgentDojo suite metadata, workspace ground-truth checks, and IntentCap trace export/checker outputs are recorded in `results/agentdojo/R002/`, `results/agentdojo/R003/`, and `results/agentdojo/R004/`.
- R004 exports 10 protected-decision events from the 6 AgentDojo workspace injection tasks that provide non-empty ground-truth tool calls; the checker denies all 10 as untrusted injection-goal control over `sink_select`/`authorize` decisions.
- MCPTox is cloned locally under ignored `benchmarks/mcptox` at commit `f85189f`; `results/mcptox/R005/` records an artifact probe over its JSON files.
- R006 exports 2,033 protected-decision events from MCPTox responses labeled `Success`; the checker denies all 2,033 as poisoned tool-description control over `authorize`, `sink_select`, or `tool_select` decisions.
- R007 improves parser coverage by adding bounded fallback extraction for malformed Python/JSON-like responses and nested code strings. It exports 2,148 protected-decision events from all 1,834 MCPTox `Success` labels; the checker denies all 2,148.
- The next benchmark step is to implement either an AgentDojo natural-language attack-goal adapter, a small online wrapper baseline, or an InjecAgent setup/adaptation probe.

## Build/Run Commands
| Purpose | Command | Status |
|---|---|---|
| Build current workshop PDF | `make` | works as of commit `4ce9892`; root paper should remain frozen |
| Verify workshop PDF page count | `pdfinfo main.pdf | rg '^Pages'` | works; expected `Pages: 2` |
| Unit tests | `PYTHONPATH=src python -m pytest -q` | works: 2 tests passed; `pytest.ini` restricts discovery to this repo's `tests/` |
| Local checker sanity | `PYTHONPATH=src python -m intentcap.checker examples/local_pdf_wrong_sink.json` | works; see `results/local/R001/verdicts.json` |
| AgentDojo suite count probe | `. .venv/bin/activate && python scripts/probe_agentdojo.py --benchmark-version v1.2.2 --suite workspace` | works; see `results/agentdojo/R002/` |
| AgentDojo workspace ground-truth check | `. .venv/bin/activate && python scripts/probe_agentdojo.py --benchmark-version v1.2.2 --suite workspace --check` | warning; see `results/agentdojo/R003/` |
| AgentDojo IntentCap trace export | `. .venv/bin/activate && PYTHONPATH=src python scripts/export_agentdojo_intentcap.py --benchmark-version v1.2.2 --suite workspace --output-dir results/agentdojo/R004 --check` | works; exports 10 events and denies all 10 under current labels |
| MCPTox artifact probe | `git clone --depth 1 https://github.com/zhiqiangwang4/MCPTox-Benchmark benchmarks/mcptox`; local JSON count probe in `results/mcptox/R005/schema_probe.txt` | works; 45 server groups, 485 tool entries/files, 1,348 cases |
| MCPTox IntentCap trace export | `PYTHONPATH=src python scripts/export_mcptox_intentcap.py --benchmark-dir benchmarks/mcptox --output-dir results/mcptox/R007 --check` | works; exports 2,148 events and denies all 2,148 under current labels |

## Integration Constraints
- Do not mutate the frozen workshop paper unless explicitly requested.
- Keep durable research memory in the canonical docs; raw benchmark outputs should go under `results/`.
- Record every nontrivial experiment command, commit, machine, seed/repetition policy, and result path in `docs/evaluation.md`.
- Avoid requiring model API keys for smoke tests. Use local/static traces first where possible.
- Treat benchmark setup failures as useful evidence and record them.

## Known Technical Debt And Open Engineering Tasks
- Need formalize the trace JSON schema currently implied by `src/intentcap/checker.py` and `scripts/export_agentdojo_intentcap.py`.
- Need improve checker denial selection once there are multiple plausible leases for the same operation; R004 uses a synthetic `_intentcap_event_id` field for deterministic event-scoped replay.
- Need implement natural-language attack-goal extraction for AgentDojo injection tasks with empty ground-truth calls.
- Need reconcile MCPTox fallback-extracted events with benchmark oracle semantics before reporting paper-level counts; R007 closes parser coverage but 115 events use bounded raw argument snippets rather than structured arguments.
- Need implement an online wrapper baseline so trace-level denials can be paired with utility/attack-success metrics.
- Need decide whether to keep external benchmark clones only as ignored local state or convert selected ones into submodules later.

## Next Engineering Action
Build the next evidence step: either classify AgentDojo natural-language injection goals into protected decision events, wrap a small live benchmark subset to measure utility and attack blocking under actual tool exposure, or add InjecAgent as a third benchmark family.
