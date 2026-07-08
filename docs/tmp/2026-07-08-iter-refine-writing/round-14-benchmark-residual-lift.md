# Round 14: Benchmark-Derived Residual Lift

Date: 2026-07-08

What was checked:
- Whether the four authority-input model is clearly stated as three upper semantic sources plus one runtime/env system source.
- Whether the E3 mechanism claim has evidence beyond local controlled residual suites.
- Whether the paper and docs avoid overstating R219 as natural prevalence or online utility.

Findings:
- The Chinese paper already had the four classes, but the three-vs-four distinction needed to be explicit: agent, instruction, and tool are upper authority sources; env is the runtime/monitor source that proves concrete state.
- R217 was still local controlled evidence. R219 adds a benchmark-derived lift using existing MCPTox artifacts.
- R219 should be framed as field-ownership/no-substitution evidence: trusted tool metadata can prove schema/interface facts, but cannot prove policy authority or approval scope.

Changes made:
- Updated `docs/autopaper/intentcap-paper-zh.tex` to define agent/instruction/tool/env inputs, explain why they cannot collapse to three system classes, and formalize field ownership through `Req(d)` and `owner(f)`.
- Added R219 to the Chinese paper's E3 section and evidence table: 24 authentic MCPTox tool-metadata cases, 72 events, 24 schema-use allows, 48 policy/approval residual denials.
- Updated `docs/evaluation.md`, `docs/design.md`, `docs/implementation.md`, `docs/idea-story.md`, and `docs/background-related-work.md` so R219 is part of E3 rather than a separate experiment.
- Kept limitations explicit: R219 is benchmark-derived residual-lift evidence, not natural-prevalence, fresh online model, utility, or recovery evidence.

Remaining concerns:
- E3 still needs more residual classes and a natural-prevalence measurement over existing traces.
- E1 still needs recovery/approval accounting under an online agent loop.
- E2 still needs independent human replication of the project-author adjudicated labels.
- E4 still needs production MCP broker or real OS/ActPlane mediation with overhead before claiming production enforcement.
