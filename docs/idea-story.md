# Idea Story

Last updated: 2026-07-04
Stage at update: stage 4/5 compiler-corpus lower-bound plus novelty audit
Source/command: AgentDojo, MCPTox, InjecAgent export/checker probes plus gateway replay; R019/R020/R022/R027 authority-minimization and oracle-distance scoring; R021-R024 tau2/tau3 artifact/reference/evaluator-backed replay; R025 checker ablation; R026 web-only eval-dataset ranking; R028-R030 local Qwen lease/action corpus; R031-R069 local Qwen3.6 tau2 task-gateway and user-simulator diagnostics; R070-R078 non-evaluation-task-JSON compiler/gateway diagnostics; R079 strict compiler-corpus local Qwen3.6 task-loop run; R080 R079 mismatch analysis; and 2026-07-04 closest-work PDF collection
Completeness: partial

## Current State
- Stage: Stage 3 design/prototype and Stage 5 evaluation probes are active. The project now has security replay evidence, authority-surface evidence, exact-oracle task-loop utility pilots, and the first strict non-oracle compiler-corpus task-loop integration.
- Blocking gate: the strongest utility results still depend on exact oracle leases or reference-user simulator replay. R079/R080 connect saved R074 compiler-corpus leases to the local Qwen3.6 task loop under strict lowering, but they are a negative lower-bound result: 11 evaluated tasks, 14 active compiler leases, 9 model calls, 9 gateway-allowed/executed calls, 0 tool errors, 7 exact bound reference calls, 2 all-reference-actions-executed tasks, and 0/11 tool-oracle pass. The current compiler is safe under strict checking but not utility-ready.
- Novelty gate: the idea is defensible but not risk-free. Same-claim pressure is medium to medium-high from CaMeL, Progent, SkillGuard, Task Shield/DRIFT, and ActPlane. The claim must stay narrow: IntentCap is a run-centric intent/provenance capability compiler/checker for authority-bearing decisions, not the first generic agent permission model and not a prompt-injection solution.
- Reference gate: 23 closest-work and benchmark PDFs are now stored under `docs/reference/` and verified locally as PDFs. This is a source corpus only; no new eval dataset was synced or executed.
- Next action: improve non-oracle compiler utility after R079/R080 by adding exact argument synthesis, safe runtime binding for placeholder arguments, broad/runtime policy repair before execution, independent validity labels, and expert-oracle lease scoring. Do not sync new eval datasets by default; use official web metadata first and ask before cloning/downloading.
- Paper boundary: the existing two-page English workshop paper is frozen under `docs/paper-workshop/`; auto-research drafts go under `docs/autopaper/`.

## Downstream Document Index
| Doc | Role | Current status | Next required update |
|---|---|---|---|
| `docs/background-related-work.md` | novelty, closest work, benchmarks, baselines | partial; 23 PDFs collected under `docs/reference/` | full-text notes and baseline reproduction decisions for CaMeL, Progent, SkillGuard, Task Shield/DRIFT |
| `docs/design.md` | mechanism and artifact boundary | partial | refine checker semantics after parser/oracle and online-wrapper results |
| `docs/implementation.md` | prototype milestones and runnable commands | partial | improve compiler-corpus task-loop support after R079/R080 |
| `docs/evaluation.md` | experiment plan, run tracker, results, claim verdict | partial | add exact-argument compiler repair, expert-oracle lease scoring, and stronger baseline comparisons |

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
- Thesis sentence: IntentCap improves least-privilege security for LLM agent extensions because it authorizes context influence over authority-bearing decisions, not only tool/resource operations.
- Smallest adequate mechanism: intent certificate + context labels + effect IR + deterministic lease checker + tool/MCP/context enforcement adapters.
- Why the mechanism should work: prompt injection attacks require untrusted context to become a control dependency of a protected decision; the checker can reject that dependency before the action executes.

### Dominant Claim
- Core claim: IntentCap blocks unauthorized context-to-decision influence in representative agent-extension workflows and can preserve benign completion when narrow leases are paired with adequate argument grounding and recovery.
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
| C1 | IntentCap blocks unauthorized context-to-decision influence while allowing authorized data use. | AgentDojo/InjecAgent/MCPTox-style adversarial workflows with protected decisions. | Attack success rate, influence-violation denial counts, benign utility, false denial recovery. | partial: local trace plus AgentDojo, reconciled MCPTox, InjecAgent, mixed InjecAgent, cached-output replay, and MCPTox provenance results; still needs strong baseline reproduction and fresh online model/API wrapper |
| C2 | Intent-carrying leases reduce over-privilege relative to static tool/server/Skill policies. | Skills, MCP tools, local scripts, and subagent delegation in mixed workflows. | Risk-weighted authority score vs static allowlist, Skill manifest/SkillGuard-style policy, human approval, and expert oracle. | partial: R019/R020/R022/R027 show authority-surface reduction; R023/R024 show exact leases execute/evaluate on tau2 reference trajectories; R031-R069 show exact-oracle local Qwen3.6 task-loop pilots; expert oracle and non-oracle utility remain pending |
| C3 | The compiler/checker split keeps LLM policy synthesis outside the trusted computing base. | Candidate lease generation from plans and extension metadata. | Invalid proposals rejected, valid proposals accepted, proof completeness, checker coverage. | partial: R025 shows provenance checking prevents no-provenance false accepts; R028-R030 use local Qwen lease/action proposals; R070-R080 expose non-oracle compiler/gateway/task-loop failure surfaces under strict checking; independent labels and proof-completeness evaluation remain pending |
| C4 | Narrow non-oracle compiler leases can preserve useful task progress after repair. | tau2/tau3 and MCP/Skill workflows with model-generated leases. | Task success, exact argument coverage, broad/runtime-policy rate, recovery rate, false denials. | weak: R079/R080 prove strict saved compiler-corpus leases can drive the task loop safely, but utility is currently 0/11 tool-oracle pass |

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
| Benchmark breadth | AgentDojo + InjecAgent + MCPTox + tau/MCP utility tasks | cross-ecosystem claim | medium setup cost | three security benchmark adapters and a gateway replay path exist; R010 adds mixed benign/attack replay; R011 adds AgentDojo goal-inferred coverage; R012 checks InjecAgent enhanced consistency; R013 adds local live wrapper mechanics; R014 audits AgentDojo paper-ready versus adapter-only events; R015 reconciles MCPTox count units; R016 adds benchmark-derived local live execution; R017 adds official cached GPT-4 ReAct output replay; R018 broadens cached-output replay across released InjecAgent result sets; R019/R020 add authority-minimization evidence; R021 adds tau2/tau3 artifact coverage; R022 adds tau2/tau3 reference-action authority minimization; R023 adds tau2/tau3 real-toolkit live gateway execution; R024 adds official tau2 action/env evaluator-backed reference replay; R025 adds checker ablation across saved traces; R026 ranks web-only candidates without syncing them; fresh online model utility still pending; new candidates should come from web metadata first, not automatic dataset sync |
| Enforcement backend | tool gateway + MCP broker + sandbox lowering | backend-independent authorization claim | implementation cost | offline checker first, runtime enforcement second |
| Authority minimization | compare generated leases to expert oracle | least-privilege claim | requires manual oracle design | R019 compares object-scope policies on InjecAgent; R020 adds MCP exact-tool/server policy comparison; R022 adds tau2/tau3 utility-label authority comparison; R023 validates tau2 exact leases against executable toolkits; R024 validates most official tau2 action/env oracle outcomes under reference replay; next add expert oracle leases and fresh simulator-backed utility |
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
- Which fresh online model/API, expert-oracle lease scoring, tau2/tau3 user-simulator utility subset, real LLM-proposed lease corpus, or explicitly approved R026 top candidate is cheapest to add without losing the current provenance rigor?
