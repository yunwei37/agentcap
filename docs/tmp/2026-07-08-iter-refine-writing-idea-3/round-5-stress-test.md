# Round 5: Reviewer Stress Test

Date: 2026-07-08

What was checked:
- `docs/autopaper/intentcap-paper-zh.tex`
- Senior reviewer stress test after R220 decision-class characterization and Round 4 cross-alignment fixes.

Reviewer result:
- Reject is still not hard to write.

Strongest reject argument:
- The core abstraction is now clear: agent authorization should be an issuer-typed protected-decision transition rather than a tool/action/context label.
- The evidence still does not fully prove that agent workloads force this abstraction. A reviewer can argue that the paper defines agent/instruction/tool/env owner fields, then uses analyzer-derived labels and residual cases built around the same taxonomy.
- R220's 8,691/8,696 multi-issuer number is mainly derived from required-field templates such as agent+tool for tool/sink/authorize events. That demonstrates model consistency, not yet independent workload necessity.
- Instruction placement and delegation are central to the paper's novelty, but current implementation evidence is trace-level. The implemented system still looks closer to checker plus tool/local-env gateway than to complete cross-Skill/MCP/env/subagent runtime authorization.

Must-fix evidence gaps:
- Natural protected-decision characterization with sampled real trace events and human labels for required issuer, unsafe substitute, env runtime proof, and observed substitution attempt.
- Direct evidence that collapsing issuer pairs causes false accepts in real or benchmark-derived workflows, not only controlled residual suites.
- At least one live context-placement guard and one live delegation monitor if the paper wants full multi-boundary system contribution.
- Stronger env/OS backend evidence if ActPlane remains part of the system contribution, otherwise keep it as lowering feasibility.
- End-to-end online utility/recovery: task success, false denial, replan recovery, approval burden, latency.
- Blinded expert oracle if E2 is to support authority minimization rather than auditability.

Action taken:
- Do not mark idea refinement as passed.
- Keep current paper claims conservative.
- Update project plan to make the next research gates explicit before running full writing-polish iteration.

Remaining blockers before top-conference claim:
- Independent natural characterization.
- Real instruction/delegation enforcement.
- Online utility/recovery evidence.
- Independent expert-oracle lease scoring.
