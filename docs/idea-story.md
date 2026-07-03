# Idea Story

Last updated: 2026-07-03
Stage at update: stage 3/5 trace-level benchmark probes
Source/command: AgentDojo, MCPTox, InjecAgent export/checker probes plus gateway replay, including R010 mixed replay, R011 AgentDojo goal inference, R012 InjecAgent enhanced replay, R013 local live smoke, R014 AgentDojo inferred-event audit, R015 MCPTox reconciliation audit, R016 benchmark-derived live gateway execution, R017 official cached prompted-output gateway replay, R018 cached-output aggregate, R019 InjecAgent authority-minimization analysis, R020 MCPTox authority-minimization analysis, R021 tau2/tau3 artifact probe, R022 tau2/tau3 reference-action authority minimization, and R023 tau2/tau3 reference-action live gateway execution
Completeness: partial

## Current State
- Stage: Stage 3 design/prototype and Stage 5 evaluation probes are active. Stage 0 framing is good enough to seed claims, and the first benchmark artifacts are now locally probed.
- Blocking gate: no fresh online model/API IntentCap-wrapper utility/security run yet; current evidence is trace-level gateway replay across AgentDojo, MCPTox, and InjecAgent, a mixed InjecAgent replay where trusted user-tool choices execute and injected attacker-tool choices are blocked, an audited AgentDojo goal-inferred replay for natural-language-only injection tasks, reconciled MCPTox count/oracle units, an InjecAgent enhanced-setting consistency replay, a local live tool gateway smoke, a benchmark-derived local live gateway run over saved InjecAgent trace events, official cached GPT-4 ReAct InjecAgent output replay, a multi-model cached-output aggregate over the released InjecAgent archive, authority-minimization evidence from InjecAgent R019 and MCPTox R020, tau2/tau3 utility-substrate evidence from R021, tau2/tau3 reference-action authority evidence from R022, and tau2/tau3 real-toolkit live gateway execution from R023.
- Next action: connect `LiveToolGateway` to a fresh online model/API benchmark subset, turn R023 into a tau2/tau3 simulator-backed utility benchmark, or extend R019/R020/R022/R023 into expert-oracle lease scoring.
- Paper boundary: the existing two-page English workshop paper is frozen under `docs/paper-workshop/`; auto-research drafts go under `docs/autopaper/`.

## Downstream Document Index
| Doc | Role | Current status | Next required update |
|---|---|---|---|
| `docs/background-related-work.md` | novelty, closest work, benchmarks, baselines | partial | add online-baseline notes after first benchmark live-wrapper run |
| `docs/design.md` | mechanism and artifact boundary | partial | refine checker semantics after parser/oracle and online-wrapper results |
| `docs/implementation.md` | prototype milestones and runnable commands | partial | formalize trace schema and improve adapter coverage |
| `docs/evaluation.md` | experiment plan, run tracker, results, claim verdict | partial | add online model/API utility/attack run, expert-oracle lease scoring, or non-InjecAgent utility benchmark |

## Intro P1: Problem And Stakes
Purpose: Establish why agent extension security is not just tool ACL security.

Draft paragraph: LLM agents increasingly operate as extensible execution environments: they load Skills, call MCP servers, run local scripts, and delegate work to subagents. These extensions do not merely execute isolated operations. They inject instructions, produce summaries, select follow-up tools, and shape later decisions that carry authority. The security failure is therefore not only that a tool may read the wrong file or call the wrong endpoint. It is that untrusted context can become a control input to decisions about which authority to exercise next.

Evidence/claim dependency: Needs concrete examples from AgentDojo-style prompt injection, MCP tool poisoning, and Skill/MCP workflows.

Completeness: partial.

## Intro P2: Status Quo And Gap
Purpose: Separate IntentCap from EIM/bpftime, ActPlane, SkillGuard, CaMeL, Task Shield, and Progent.

Draft paragraph: Existing defenses cover important pieces of this problem. Static manifests and tool ACLs bound declared operations. Runtime guards decide whether a tool call matches a policy. OS-level monitors can enforce file, process, and network restrictions below the agent harness. Prompt-injection defenses such as task alignment and control/data separation reduce specific attack paths. What remains under-modeled is the authority of context itself: whether a PDF, tool result, Skill instruction, or subagent summary may influence a sink choice, policy request, delegation decision, or lease expansion.

Evidence/claim dependency: Needs closest-work comparison in `docs/background-related-work.md`.

Completeness: partial.

## Intro P3: Key Insight And Thesis
Purpose: State the paper's core abstraction.

Draft paragraph: IntentCap starts from the observation that context influence should be a least-privilege capability. The same untrusted document may be safe to quote into a spreadsheet cell or summarize into an issue body, yet unsafe to choose the repository, request broader OAuth scope, or trigger delegation. IntentCap makes user intent the root of authority and labels each context source with the decision classes it may influence. A high-impact action is allowed only when its control provenance is authorized for that decision and the action is derivable from the current intent certificate.

Evidence/claim dependency: Needs formal checker invariant and benchmark cases where data use is allowed while authority influence is denied.

Completeness: partial.

## Intro P4: Proposed Artifact Or Method
Purpose: Describe the artifact boundary without making it look like an OS monitor.

Draft paragraph: The artifact is a capability compiler and deterministic checker for agent runs. An untrusted LLM-assisted frontend proposes a task plan, effect graph, and candidate leases from user intent, Skill metadata, MCP schemas, scripts, and benchmark-specific tool catalogs. A trusted checker validates leases against provenance, influence, flow, temporal, budget, and delegation rules. Runtime adapters then enforce accepted leases at context construction, tool invocation, MCP mediation, sandbox execution, and subagent delegation boundaries.

Evidence/claim dependency: Needs prototype implementation and enforcement adapters; ActPlane remains optional backend, not the contribution.

Completeness: partial.

## Intro P5: Claims And Evaluation Promise
Purpose: Convert the idea into falsifiable research claims.

Draft paragraph: The evaluation should show that intent-carrying leases reduce over-broad authority and block context-driven wrong-sink, exfiltration, approval inflation, and delegation attacks while preserving benign task utility. The primary evidence should come from adapting existing agent-security and tool-use benchmarks rather than only custom examples: AgentDojo for dynamic indirect prompt injection, InjecAgent for broad IPI cases, MCPTox for MCP tool poisoning, and MCP/tau-style benchmarks for utility and policy-following pressure.

Evidence/claim dependency: Needs reproduced or adapted benchmark runs and oracle definitions for influence violations.

Completeness: partial.

## Intro P6: Contributions, Scope, And Non-Goals
Purpose: Keep claims credible for security reviewers.

Draft paragraph: IntentCap contributes a context-authority model, intent-carrying capability leases, a compiler/checker architecture, and a multi-boundary enforcement plan for LLM agent extensions. It does not claim to solve prompt injection, infer arbitrary script behavior perfectly, replace OS sandboxing, or prove globally minimal permissions over all possible plans. Its safety claim is scoped: within modeled decision classes and enforced boundaries, accepted high-impact events cannot have unauthorized context-to-decision control dependencies.

Evidence/claim dependency: Needs formal model, explicit modeled decision classes, and negative-result handling.

Completeness: partial.

## Supporting Research State

### Problem Anchor
- Bottom-line problem: Agent systems currently authorize operations more explicitly than they authorize context influence over future decisions.
- Must-solve bottleneck: Distinguishing allowed data dependence from forbidden control dependence at runtime.
- Success condition: A checker can deny influence violations while allowing benign workflows to continue through narrower leases or structured refinement.

### Why Now
- Technical/scientific change: Skills, MCP servers, subagents, and tool-rich coding assistants make extension-provided text an operational control surface.
- New deployment pressure or workload shift: Real agents now touch GitHub, email, documents, calendars, shells, and cloud APIs in the same workflow.
- Why prior approaches are newly insufficient: Tool ACLs and OS monitors do not by themselves know whether the repository, recipient, sink, or approval scope came from trusted user intent or untrusted context.

### Target Audience And Venue Bar
- Venue family: systems/security/agent infrastructure workshop first; OSDI/SOSP/USENIX Security style if prototype and evaluation become strong.
- Reviewer expectation: clear threat model, exact boundaries, meaningful baselines, no overclaim that prompt injection is solved.

### Method Thesis
- Thesis sentence: IntentCap improves least-privilege security for LLM agent extensions because it authorizes context influence over decisions, not only tool/resource operations.
- Smallest adequate mechanism: intent certificate + context labels + effect IR + deterministic lease checker + tool/MCP/context enforcement adapters.
- Why the mechanism should work: prompt injection attacks require untrusted context to become a control dependency of a protected decision; the checker can reject that dependency before the action executes.

### Dominant Claim
- Core claim: IntentCap blocks unauthorized context-to-decision influence in representative agent-extension workflows while preserving benign completion through narrow leases.
- Stretch claim: IntentCap can serve as a portable policy synthesis layer across Skills, MCP servers, local scripts, and subagents, with enforcement backends ranging from tool gateways to OS monitors.
- Evidence needed to promote stretch claim: at least two independent benchmark families plus one MCP/security benchmark with comparable utility and attack metrics.

### Core Mechanism
- Intent certificate rooted in trusted user selections and approvals.
- Context authority labels over influence modes and decision classes.
- Effect IR separating data provenance from control provenance.
- Proof-carrying capability leases checked deterministically.
- Runtime adapters for context, tool, MCP, local execution, and delegation boundaries.

### Scope And Non-Goals
- In scope: prompt-injection-driven wrong sinks, exfiltration through unauthorized tools, approval-scope inflation, malicious delegation, over-broad capability synthesis, and MCP/Skill/tool-result authority confusion.
- Out of scope: malicious kernel/hypervisor, perfect static analysis of arbitrary scripts, model-level jailbreak robustness, and semantic misinformation that never reaches a modeled protected decision.

### Claim Ledger
| ID | Claim | Scope | Metric/evidence needed | Status |
|---|---|---|---|---|
| C1 | IntentCap blocks unauthorized context-to-decision influence while allowing authorized data use. | AgentDojo/InjecAgent/MCPTox-style adversarial workflows with protected decisions. | Attack success rate, influence-violation denial counts, benign utility, false denial recovery. | partial: local trace plus AgentDojo, reconciled MCPTox, InjecAgent, mixed InjecAgent, audited AgentDojo goal-inferred, InjecAgent enhanced consistency replay, local live gateway smoke, benchmark-derived local live InjecAgent execution, official cached GPT-4 ReAct output replay, and multi-model cached-output aggregate; no fresh online model/API benchmark run yet |
| C2 | Intent-carrying leases reduce over-privilege relative to static tool/server/Skill policies. | Skills, MCP tools, local scripts, and subagent delegation in mixed workflows. | Risk-weighted authority score vs static allowlist, Skill manifest, human approval, and expert oracle. | partial: R019 shows one-shot IntentCap leases expose 1.0 tool/case and admit 0/1,598 injected attacker events on the InjecAgent mixed trace, while toolkit/static policies expose more tools and admit more attacks; R020 shows exact-tool MCP ACLs expose the same 1.0 tool/event as IntentCap but still admit 2,148/2,148 poisoned-description-controlled calls without provenance checks; R022 shows exact tau2/tau3 reference-event leases cover 3,813 assistant reference actions while domain/global static policies expose 8.97x-101.89x more tool slots; R023 shows those exact leases are executable through real tau2 domain toolkit callables with 3,795/3,813 successful direct tool executions and 0 unsupported/checker-blocked events; expert oracle and simulator/model utility remain pending |
| C3 | The compiler/checker split keeps LLM policy synthesis outside the trusted computing base. | Candidate lease generation from plans and extension metadata. | Invalid proposals rejected, valid proposals accepted, proof completeness, checker coverage. | proposed |

### Largest Plausible Claim
- Bigger claim hypothesis: Intent-provenance-aware capability synthesis is a general authorization layer for agent extension ecosystems.
- Why it would matter: It would reposition the work as a run-time authority compiler, not a one-off prompt-injection defense.
- Experiments needed: demonstrate the same lease language on at least AgentDojo, MCPTox/MCP-Bench, and a custom Skill/local-script workflow.
- Cheapest probe: implement a pure-Python checker and run it as an offline policy oracle over benchmark trajectories before building full runtime enforcement.

### Adjacent Idea Intake
| Adjacent idea/source | What can be absorbed | How it could expand the paper | Risk |
|---|---|---|---|
| CaMeL | explicit control/data flow extraction | strengthens provenance model and security theorem | close prior work; must show decision-class and intent-certificate delta |
| Task Shield | user-objective alignment checks | useful baseline for "does this action serve the user goal?" | may look similar unless IntentCap emphasizes proof-carrying leases |
| Progent | deterministic privilege DSL | baseline for tool-level policies | may overlap with runtime policy enforcement |
| AgentDojo | utility/security benchmark oracles | primary reproducible security testbed | adapters may need effort |
| MCPTox | MCP tool poisoning cases | expands from document/tool output injection to tool-description poisoning | artifact and adapter are available; R015 reconciles count/oracle units; online utility still pending |

### Expansion Agenda
| Expansion axis | Bigger experiment | Claim upside | Cost/risk | Probe |
|---|---|---|---|---|
| Benchmark breadth | AgentDojo + InjecAgent + MCPTox + tau/MCP utility tasks | cross-ecosystem claim | medium setup cost | three security benchmark adapters and a gateway replay path exist; R010 adds mixed benign/attack replay; R011 adds AgentDojo goal-inferred coverage; R012 checks InjecAgent enhanced consistency; R013 adds local live wrapper mechanics; R014 audits AgentDojo paper-ready versus adapter-only events; R015 reconciles MCPTox count units; R016 adds benchmark-derived local live execution; R017 adds official cached GPT-4 ReAct output replay; R018 broadens cached-output replay across released InjecAgent result sets; R019/R020 add authority-minimization evidence; R021 adds tau2/tau3 artifact coverage; R022 adds tau2/tau3 reference-action authority minimization; R023 adds tau2/tau3 real-toolkit live gateway execution; fresh online model utility still pending |
| Enforcement backend | tool gateway + MCP broker + sandbox lowering | backend-independent authorization claim | implementation cost | offline checker first, runtime enforcement second |
| Authority minimization | compare generated leases to expert oracle | least-privilege claim | requires manual oracle design | R019 compares object-scope policies on InjecAgent; R020 adds MCP exact-tool/server policy comparison; R022 adds tau2/tau3 utility-label authority comparison; R023 validates tau2 exact leases against executable toolkits; next add expert oracle leases and simulator-backed utility |
| Refinement | denied action -> narrower lease -> continue | utility preservation claim | requires agent loop integration | simulate with recorded traces |

### Reviewer Attack Surface
- "This is CaMeL with different words." Response must show intent certificate, decision-class influence authority, and cross-extension leases.
- "This is Progent or SkillGuard." Response must show run-centric, context-provenance-aware lease derivation beyond tool-call DSLs or skill manifests.
- "This is ActPlane policy synthesis." Response must show context construction and policy origin are central; OS enforcement is optional.
- "How do you know control provenance?" Need a concrete instrumentation story for plans, arguments, and benchmark traces.
- "Does it preserve utility?" Need benchmark results and recovery from false denials.

### Open Questions
- How much control-provenance tracking can be extracted from existing agent harnesses without modifying model internals?
- Should the first prototype be online enforcement or offline trace checking?
- Which benchmark exposes the cleanest wrong-sink and approval-scope tests beyond the current audited AgentDojo goal-inferred replay?
- Which fresh online model/API, expert-oracle lease scoring, or tau2/tau3 simulator-backed utility subset is cheapest to add after R023 without losing the current provenance rigor?
