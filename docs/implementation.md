# Implementation

Last updated: 2026-07-02 America/Vancouver
Stage at update: stage 4 implementation planning
Source/command: fallback implementation planning through auto-research goal
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
| `src/intentcap/` | proposed prototype package | not created yet |
| `scripts/probe_agentdojo.py` | AgentDojo setup/suite sanity probe | created |
| `benchmarks/` | ignored external benchmark clone workspace | created; AgentDojo cloned locally |
| `results/` | raw result outputs and run logs | created; R001-R003 recorded |

## Implementation Milestones
| Milestone | Deliverable | Exit condition | Status |
|---|---|---|---|
| M0: Research scaffold | canonical docs, workshop snapshot, autopaper draft | docs exist and identify next benchmark/action | in progress |
| M1: Core schema/checker | Python checker for intent labels, effects, leases, and verdicts | unit tests for allow/deny examples | partial: minimal JSON checker exists |
| M2: Offline trace checker | CLI that reads JSON events and policy/lease files | can reproduce the PDF wrong-sink example without an LLM | partial: local sanity trace passes |
| M3: AgentDojo adapter | load AgentDojo task metadata/traces or wrap benchmark agent calls | one benign and one adversarial task dry-run logged | todo |
| M4: InjecAgent/MCPTox adapters | parse cases into protected decision events | at least one setup/dry-run or documented blocker per benchmark | todo |
| M5: Lease compiler prototype | heuristic compiler from task intent and effect list to candidate leases | compares LLM-only/wide leases vs minimized leases | todo |
| M6: Online enforcement harness | tool gateway/MCP broker/context constructor wrappers | blocks wrong sink in a live toy workflow | todo |
| M7: Evaluation scripts | aggregate utility, attack success, over-privilege, false denial, recovery | generates tables for `docs/autopaper` | todo |

## Current Implementation Status
- A minimal offline checker exists under `src/intentcap/`.
- The checker supports exact/prefix/suffix/one-of argument predicates, lease matching, control provenance checks, data provenance checks, and context-label influence-mode checks.
- AgentDojo is cloned locally under ignored `benchmarks/agentdojo` at commit `089ed468` and installed editable into `.venv`.
- AgentDojo suite metadata and workspace ground-truth checks are recorded in `results/agentdojo/R002/` and `results/agentdojo/R003/`.
- The next benchmark step is to understand the R003 injection-task failures before treating AgentDojo security results as reliable.

## Build/Run Commands
| Purpose | Command | Status |
|---|---|---|
| Build current workshop PDF | `make` | works as of commit `4ce9892`; root paper should remain frozen |
| Verify workshop PDF page count | `pdfinfo main.pdf | rg '^Pages'` | works; expected `Pages: 2` |
| Unit tests | `PYTHONPATH=src python -m pytest -q` | works: 2 tests passed; `pytest.ini` restricts discovery to this repo's `tests/` |
| Local checker sanity | `PYTHONPATH=src python -m intentcap.checker examples/local_pdf_wrong_sink.json` | works; see `results/local/R001/verdicts.json` |
| AgentDojo suite count probe | `. .venv/bin/activate && python scripts/probe_agentdojo.py --benchmark-version v1.2.2 --suite workspace` | works; see `results/agentdojo/R002/` |
| AgentDojo workspace ground-truth check | `. .venv/bin/activate && python scripts/probe_agentdojo.py --benchmark-version v1.2.2 --suite workspace --check` | warning; see `results/agentdojo/R003/` |

## Integration Constraints
- Do not mutate the frozen workshop paper unless explicitly requested.
- Keep durable research memory in the canonical docs; raw benchmark outputs should go under `results/`.
- Record every nontrivial experiment command, commit, machine, seed/repetition policy, and result path in `docs/evaluation.md`.
- Avoid requiring model API keys for smoke tests. Use local/static traces first where possible.
- Treat benchmark setup failures as useful evidence and record them.

## Known Technical Debt And Open Engineering Tasks
- Need choose Python package layout and dependency policy.
- Need define a small JSON schema for traces that can be generated without model APIs.
- Need inspect AgentDojo APIs to determine whether offline trajectory checking is easier than online wrapping.
- Need decide whether external benchmark repos are vendored, submodules, or cloned into ignored `benchmarks/`.
- Need add `.gitignore` rules before generating raw results or external clones.

## Next Engineering Action
Clone/install AgentDojo in an isolated external path or `benchmarks/` and record the first setup command in the run tracker. Keep using the local checker sanity trace as the regression test while adding benchmark adapters.
