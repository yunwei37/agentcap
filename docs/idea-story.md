# Idea Story

Last updated: 2026-07-04
Stage at update: stage 4/5 compiler-corpus lower-bound plus expanded novelty audit
Source/command: AgentDojo, MCPTox, InjecAgent export/checker probes plus gateway replay; R019/R020/R022/R027 authority-minimization and oracle-distance scoring; R021-R024 tau2/tau3 artifact/reference/evaluator-backed replay; R025 checker ablation; R026 web-only eval-dataset ranking; R028-R030 local Qwen lease/action corpus; R031-R069 local Qwen3.6 tau2 task-gateway and user-simulator diagnostics; R070-R078 non-evaluation-task-JSON compiler/gateway diagnostics; R079 strict compiler-corpus local Qwen3.6 task-loop run; R080 R079 mismatch analysis; R081 top-conference claim evidence matrix; 2026-07-04 closest-work plus 2026 agent-security PDF collection; 2026-07-04 P0 full-text baseline pass; 2026-07-04 online novelty sweep adding AuthGraph/PACT/AIRGuard/FIDES/RTBAS/NeuroTaint/PCAS/AgentSpec/AgentGuard/AgentBound/SecureClaw/AgentSentry/tracked-capability PDFs; follow-up PDF sweep adding Agent-Sentry/VIGIL/PolicyGuard/Authorization Propagation/LivePI/AgentTrap/ARGUS/AgentDyn/ClawGuard/AgentGuardian; R082 closest-baseline labelers; R083 residual closest-baseline suite; R084 residual gateway replay; R085 residual live callable replay; R086 residual local LLM gateway probe; R087 realistic workflow residual suite with local Qwen gateway probe; R088/R089 Qwen3.6/qwen2.5 workflow residual feedback probes; and R090 tau2 compiler validity-label audit
Completeness: partial

## Current State
- Stage: Stage 3 design/prototype and Stage 5 evaluation probes are active. The project now has security replay evidence, authority-surface evidence, exact-oracle task-loop utility pilots, and the first strict non-oracle compiler-corpus task-loop integration.
- Blocking gate: R081 strengthens the saved-result TC1/TC2 security and authority story, but the strongest utility results still depend on exact oracle leases or reference-user simulator replay. R079/R080 connect saved R074 compiler-corpus leases to the local Qwen3.6 task loop under strict lowering, but they are a negative lower-bound result: 11 evaluated tasks, 14 active compiler leases, 9 model calls, 9 gateway-allowed/executed calls, 0 tool errors, 7 exact bound reference calls, 2 all-reference-actions-executed tasks, and 0/11 tool-oracle pass. R090 adds reviewer-auditable labels over this compiler path: broad/runtime argument policies explain 34/61 non-strict admits and 60 strict blocks across two compiler corpora, while exact strict coverage remains 11/61 per corpus. The current compiler is safe under strict checking and diagnosable, but not utility-ready.
- Novelty gate: the idea is defensible only under a narrow claim, and the evidence bar is now higher. Same-claim pressure is high after adding AuthGraph, PACT, AIRGuard, ARGUS, Agent-Sentry, ClawGuard, VIGIL, FIDES, RTBAS, NeuroTaint, PCAS, AgentSpec, AgentGuard, AgentGuardian, AgentBound, SecureClaw, AgentSentry, and tracked-capability work on top of the earlier CaMeL/PFI/AgentSecBench/Formalizing/Progent/SkillGuard/SkillScope/Task Shield/DRIFT set. The claim must be: IntentCap is a run-centric extension authorization compiler/checker that turns context influence over authority-bearing decisions into proof-carrying, attenuable leases across Skills, MCP, local execution, and subagents. It is not the first provenance-aware agent authorization system, not the first intent-to-execution framing, not the first flow/taint defense, not the first policy compiler, not the first Skill/MCP permission system, not the first runtime tool guard, and not a prompt-injection solution.
- R082 gate: R082 implements trace-level closest-family labelers over 8,680 saved events. Static tool ACLs false-accept 3,811/3,811 checker denials and policy-DSL/access-control-style checks false-accept 3,810/3,811, so ACL/policy-only baselines are still weak. But AuthGraph/PACT/AIRGuard-style provenance-authority and IFC/taint-style labelers explain all 3,811 current denials, leaving 0 residual events. Current saved traces therefore do not yet prove IntentCap's extra lease semantics beyond the strongest provenance/IFC baselines.
- R083 gate: R083 adds a fixed residual closest-baseline suite in `examples/residual_closest_baseline_suite.json`. It is a mechanism-isolation microbenchmark, not a fresh benchmark or artifact reproduction. The suite has 7 events: 1 allowed budgeted call and 6 checker denials for temporal order, invocation budget, delegation attenuation, cross-extension holder mismatch, same-trusted-source/wrong-decision-class, and missing proof-carrying intent/approval derivation. AuthGraph/PACT/AIRGuard-style, IFC/taint-style, policy-DSL, and static-tool-ACL labelers accept all 7 events, so all 6 denials are residual. This supports the claim that IntentCap's lease semantics are not reducible to the current trace-level provenance/IFC/policy labelers, but it still needs to be lifted into realistic benchmark and LLM-loop workloads.
- R084 gate: R084 replays the R083 residual suite through the runtime-facing `TraceGateway`. It attempts 7 events, executes the one valid budgeted call, and blocks the 6 residual violations across `sink_select`, `delegate`, and `tool_select`. This confirms the new stateful checker semantics propagate through the gateway replay path; it is still not live tool execution or model-loop evidence.
- R085 gate: R085 replays the same residual suite through `LiveToolGateway` with local registered callables for `github.create_issue`, `/skills/pdf/extract.py`, and `summarizer`. It attempts 7 events, invokes exactly one callable for the valid `budgeted_first_issue`, blocks all 6 residual violations before callable execution, and records 0 missing tools and 0 tool errors. This is live local callable-boundary evidence, but still not model-loop or external-tool benchmark evidence.
- R086 gate: R086 asks the local qwen2.5-3b GGUF model, through llama.cpp 9870, whether each residual event should call or abort. The model parses 7/7 prompts and chooses `call` for all 7, which would be 6 unsafe calls in an LLM-only runner. IntentCap evaluates each model event with trace-prefix state and allows only the valid call: 1 callable invocation, 6 gateway blocks, and 0 dangerous executes. This supports the checker-outside-LLM-TCB claim on a controlled residual suite, but it is still not benchmark-scale task utility.
- R087 gate: R087 lifts the residual lease-semantics patterns into a concrete local workflow trace spanning PDF Skill materialization, GitHub MCP issue creation, approval scope, calendar subagent delegation, and cross-extension local execution. The trace has 8 events: 2 allowed workflow steps and 6 checker denials for temporal order, invocation budget, delegation attenuation, holder mismatch, signed-skill wrong decision class, and missing fresh approval proof. Closest-baseline labelers accept all 8 events, leaving 6/6 residual denials; `TraceGateway` executes 2 and blocks 6; local qwen2.5-3b calls all 8 while the gateway blocks the 6 unsafe calls and records 0 dangerous executes. This is stronger than the abstract R083 microbenchmark, but it is still a local constructed workflow suite rather than benchmark-scale attack/utility evidence.
- R088/R089 gate: R088 extends the R087 workflow suite through the feedback-capable runner with local Qwen3.6. The model parses all 8 prompts, calls only the 2 authorized events, aborts the 6 unsafe residual events, invokes 2 local callables, and records 0 dangerous executes. R089 reruns the same trace with qwen2.5 as a stress case: the model initially calls all 8 events, the gateway blocks 6 unsafe calls, structured denial feedback recovers 1/6 unsafe calls to abort, and the remaining 5 unsafe calls are still blocked with 0 dangerous executes. This strengthens the LLM-outside-TCB and action-level feedback story, but it still does not prove robust task-level recovery or benchmark-derived residual evidence.
- R090 gate: R090 is a deterministic saved-artifact audit over R074-R080, not a fresh model run. It emits action/lease/task-loop labels that make the non-oracle compiler failure surface explicit: exact active leases are a minority, broad/runtime policies are either unsafe if left active or blocked under strict lowering, missing tools remain common, and the task loop still has wrong/hallucinated tool calls. This clears the first "independent labels" gap only in the deterministic/reviewer-auditable sense; it does not replace blinded expert-oracle scoring.
- Reference gate: 73 closest-work and benchmark PDFs are now stored under `docs/reference/` and verified locally as PDFs. This is a source corpus only, not proof of literature completeness; no new eval dataset was synced or executed.
- Next action: after R090, either lift the residual patterns into existing local benchmark traces or a larger model/task loop, or improve non-oracle compiler utility after R079/R080/R090 with exact argument synthesis, broad/runtime repair, and safe runtime binding. Do not sync new eval datasets by default; use existing local artifacts and official metadata first.
- Paper boundary: the existing two-page English workshop paper is frozen under `docs/paper-workshop/`; auto-research drafts go under `docs/autopaper/`.

## Downstream Document Index
| Doc | Role | Current status | Next required update |
|---|---|---|---|
| `docs/background-related-work.md` | novelty, closest work, benchmarks, baselines | partial; 73 PDFs collected, P0 notes added, and R082 closest-baseline negative result recorded | keep reproduction decisions current as artifacts are tested |
| `docs/design.md` | mechanism and artifact boundary | partial | refine checker semantics after parser/oracle and online-wrapper results |
| `docs/implementation.md` | prototype milestones and runnable commands | partial | improve compiler-corpus task-loop support after R079/R080/R090 |
| `docs/evaluation.md` | experiment plan, run tracker, results, claim verdict | partial; R087 adds local realistic workflow residual evidence; R088/R089 add local model-contrast and structured-denial feedback evidence; R090 adds saved compiler validity labels | lift residual cases into existing benchmark/model loops, add exact-argument compiler repair, blinded expert-oracle lease scoring, and stronger baseline comparisons |

## Intro P1: Problem And Stakes
Purpose: Establish why agent extension security is not just tool ACL security.

Draft paragraph: LLM agents increasingly operate as extensible execution environments: they load Skills, call MCP servers, run local scripts, and delegate work to subagents. These extensions do not merely execute isolated operations. They inject instructions, produce summaries, select follow-up tools, and shape later decisions that carry authority. The security failure is therefore not only that a tool may read the wrong file or call the wrong endpoint. It is that untrusted context can become a control input to decisions about which authority to exercise next.

Evidence/claim dependency: Needs concrete examples from AgentDojo-style prompt injection, MCP tool poisoning, and Skill/MCP workflows.

Completeness: partial.

## Intro P2: Status Quo And Gap
Purpose: Separate IntentCap from EIM/bpftime, ActPlane, SkillGuard, CaMeL, Task Shield, and Progent.

Draft paragraph: Existing defenses cover important pieces of this problem. Static manifests and tool ACLs bound declared operations. Runtime guards decide whether a tool call matches a policy. OS-level monitors can enforce file, process, and network restrictions below the agent harness. Recent provenance and authority-control defenses already compare clean user intent against execution provenance, assign trust contracts to authority-bearing arguments, and prevent untrusted resources from authorizing side effects. The remaining gap for IntentCap is narrower: a cross-extension compiler/checker that turns these authority constraints into proof-carrying, attenuable leases with explicit decision classes, temporal and budget guards, delegation bounds, and deterministic validation across Skills, MCP tools, local execution, and subagents.

Evidence/claim dependency: Needs closest-work comparison in `docs/background-related-work.md`.

Completeness: partial.

## Intro P3: Key Insight And Thesis
Purpose: State the paper's core abstraction.

Draft paragraph: IntentCap's design choice is to make a proof-carrying lease the unit that connects intent, provenance, and extension authority. The same untrusted document may be safe to quote into a spreadsheet cell or summarize into an issue body, yet unsafe to choose the repository, request broader OAuth scope, or trigger delegation; prior work already motivates that distinction. IntentCap packages it into run-scoped leases that bind user intent, context labels, protected decision classes, temporal state, budget, and delegation. A high-impact action is allowed only when its active lease and control provenance both validate against the current intent certificate.

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
- Reviewer expectation: clear threat model, exact boundaries, meaningful baselines, no overclaim that prompt injection is solved and no claim that user-intent/contextual security itself is new.

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
| C1 | IntentCap blocks unauthorized context-to-decision influence while allowing authorized data use. | AgentDojo/InjecAgent/MCPTox-style adversarial workflows with protected decisions. | Attack success rate, influence-violation denial counts, benign utility, false denial recovery, and residual denials beyond closest provenance/IFC baselines. | partial but narrower: R081 shows object-only policies false-accept 3,811/3,811 checker-denied protected decisions and same-exposure ACL profiles produce 2,149 unsafe event admissions; R082 shows AuthGraph/PACT/AIRGuard-style and IFC/taint-style trace labelers explain all 3,811 current saved-trace denials; R083 adds 6/6 residual denials in a controlled microbenchmark; R087 lifts those residual classes into a concrete local Skill/MCP/subagent workflow with 6/6 residual denials; R088/R089 add local model-contrast and feedback containment over that workflow, but benchmark residual evidence is still pending |
| C2 | Intent-carrying leases reduce over-privilege relative to static tool/server/Skill policies. | Skills, MCP tools, local scripts, and subagent delegation in mixed workflows. | Risk-weighted authority score vs static allowlist, Skill manifest/SkillGuard-style policy, human approval, and expert oracle. | partial but stronger: R019/R020/R022/R027/R081 show authority-surface reduction, 13,851 non-oracle unsafe event admissions over 3,746 unique unsafe events, and up to 756,096 extra authority slots; expert-blind oracle and non-oracle utility remain pending |
| C3 | The compiler/checker split keeps LLM policy synthesis outside the trusted computing base. | Candidate lease generation from plans and extension metadata. | Invalid proposals rejected, valid proposals accepted, proof completeness, checker coverage, and closest-baseline residual labels. | partial: R025/R081 show provenance checking prevents no-provenance false accepts; R028-R030 use local Qwen lease/action proposals; R070-R080 expose non-oracle compiler/gateway/task-loop failure surfaces under strict checking; R090 adds deterministic saved-artifact validity labels; R082 adds closest-baseline labels but also shows saved-trace denials are not residual beyond provenance/IFC labelers; R083-R086 add checker/gateway/live/model residual evidence; R087 shows the same outside-TCB containment on a concrete local Skill/MCP/subagent workflow; R088/R089 show model behavior varies and checker/gateway remains necessary under feedback; blinded expert/proof-completeness evaluation remains pending |
| C4 | Narrow non-oracle compiler leases can preserve useful task progress after repair. | tau2/tau3 and MCP/Skill workflows with model-generated leases. | Task success, exact argument coverage, broad/runtime-policy rate, recovery rate, false denials. | weak: R079/R080 prove strict saved compiler-corpus leases can drive the task loop safely, and R090 localizes the compiler bottleneck, but utility is currently 0/11 tool-oracle pass; R089 adds only action-level residual feedback with 1/6 unsafe calls recovered to abort |

### Largest Plausible Claim
- Bigger claim hypothesis: Intent-provenance-aware capability synthesis is a general authorization layer for agent extension ecosystems.
- Why it would matter: It would reposition the work as a run-time authority compiler, not a one-off prompt-injection defense.
- Experiments needed: demonstrate the same lease language on at least AgentDojo, MCPTox/MCP-Bench, and a custom Skill/local-script workflow.
- Cheapest probe: implement a pure-Python checker and run it as an offline policy oracle over benchmark trajectories before building full runtime enforcement.

### Adjacent Idea Intake
| Adjacent idea/source | What can be absorbed | How it could expand the paper | Risk |
|---|---|---|---|
| AuthGraph / PACT / AIRGuard | clean user-intent authorization graph, argument-role provenance contracts, action-time authority control | mandatory closest-family baseline | very high overlap; must show proof-carrying extension leases, attenuation, temporal/delegation constraints, and cross-extension synthesis |
| CaMeL / PFI / FIDES / RTBAS / NeuroTaint | explicit control/data flow, IFC/dependency screening, and taint tracking | strengthens provenance model and security theorem | close prior work; must show decision-class and intent-certificate delta |
| Task Shield | user-objective alignment checks | useful baseline for "does this action serve the user goal?" | may look similar unless IntentCap emphasizes proof-carrying leases |
| Progent / PCAS / AgentSpec / AgentGuard / AgentBound | deterministic privilege DSL, policy compiler, runtime DSL, ABAC, MCP access control | baseline for tool-level and access-control policies | may overlap with compiler/runtime enforcement claims |
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
- "This is AuthGraph, PACT, ARGUS, AIRGuard, ClawGuard, or Agent-Sentry with different words." Response must show proof-carrying leases as the policy object, explicit influence modes and decision classes, attenuation, temporal/budget/delegation constraints, and cross-extension lease synthesis beyond clean graph comparison, argument-role contracts, influence-provenance auditing, action-time authority guards, tool-boundary rules, or learned behavior bounds. R082 shows ordinary saved traces are not enough; R083 adds controlled residual cases; R087 lifts those cases into a local realistic workflow suite; R088/R089 add model-contrast and action-level feedback but remain local constructed probes; R090 adds compiler validity labels but not benchmark residuals; the next gate is benchmark-derived residual workflows or an independently reviewed expert-oracle/proof-completeness corpus.
- "This is CaMeL/PFI/FIDES/RTBAS/NeuroTaint/AgentSecBench/Formalizing with different words." Response must show intent certificate, decision-class influence authority, proof-carrying leases, and cross-extension enforcement rather than only trusted/untrusted flow separation, taint tracking, dependency screening, or contextual security taxonomy.
- "This is Progent, PCAS, AgentSpec, AgentGuard, AgentBound, SkillGuard, or SkillScope." Response must show run-centric, context-provenance-aware lease derivation beyond tool-call DSLs, policy compilers, ABAC/MCP policies, skill manifests, or skill graph analysis.
- "This is ActPlane policy synthesis." Response must show context construction and policy origin are central; OS enforcement is optional.
- "How do you know control provenance?" Need a concrete instrumentation story for plans, arguments, and benchmark traces.
- "Does it preserve utility?" Need benchmark results and recovery from false denials.

### Open Questions
- How much control-provenance tracking can be extracted from existing agent harnesses without modifying model internals?
- Should the first prototype be online enforcement or offline trace checking?
- Which benchmark exposes the cleanest wrong-sink and approval-scope tests beyond the current audited AgentDojo goal-inferred replay?
- Which fresh online model/API, expert-oracle lease scoring, tau2/tau3 user-simulator utility subset, real LLM-proposed lease corpus, or explicitly approved R026 top candidate is cheapest to add without losing the current provenance rigor?
