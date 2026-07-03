# Background And Related Work

Last updated: 2026-07-03
Stage at update: stage 1 novelty scan plus artifact probes
Source/command: web search over primary benchmark, paper, and artifact pages; local MCPTox clone/schema/export/parser probes
Completeness: partial

## Search Log
| Date | Query/source | Purpose | Result |
|---|---|---|---|
| 2026-07-02 | `AgentDojo benchmark prompt injection attacks defenses LLM agents paper GitHub` | Find primary security benchmark and artifact | AgentDojo provides code, CLI, 97 realistic tasks, 629 security cases, 4 environments, and formal utility/security checks: https://arxiv.org/html/2406.13352v3 and https://github.com/ethz-spylab/agentdojo |
| 2026-07-02 | `InjecAgent indirect prompt injection tool integrated agents benchmark GitHub` | Find broad IPI test suite | InjecAgent reports 1,054 test cases across 17 user tools and 62 attacker tools: https://github.com/uiuc-kang-lab/InjecAgent |
| 2026-07-02 | `tau-bench benchmark LLM agents dynamic environments paper GitHub` | Find policy/tool/user benchmark | tau2/tau3 provides customer-service domains with tools, tasks, policies, user simulator, and current run command: https://github.com/sierra-research/tau2-bench |
| 2026-07-02 | `MCP benchmark LLM agents benchmark paper GitHub MCPBench LiveMCPBench` | Find MCP utility benchmarks | MCP-Bench and LiveMCPBench target MCP tool discovery/selection/use at scale: https://github.com/Accenture/mcp-bench and https://arxiv.org/html/2508.01780v1 |
| 2026-07-02 | `tool poisoning attacks MCP benchmark paper dataset GitHub` | Find MCP-specific security benchmark | MCPTox reports 45 real-world MCP servers, 353 tools, and 1,312 malicious cases: https://arxiv.org/html/2508.14925v1 |
| 2026-07-02 | `Task Shield CaMeL Progent prompt injection defense LLM agents` | Find defense baselines | Task Shield evaluates on AgentDojo; CaMeL provides control/data-flow design and code; Progent provides privilege-control DSL baseline: https://aclanthology.org/2025.acl-long.1435/, https://arxiv.org/abs/2503.18813, https://arxiv.org/html/2504.11703v2 |
| 2026-07-03 | `MCPTox MCP tool poisoning benchmark GitHub` plus local clone/export | Verify MCP security benchmark artifact availability and adapter viability | Official MCPTox repository exists at https://github.com/zhiqiangwang4/MCPTox-Benchmark. Local R005 clone at `f85189f` contains 45 server groups, 485 tool entries/files, 11 attack scopes, and 1,348 cases. R007 exports 2,148 protected events from all 1,834 benchmark responses labeled `Success`, including 115 bounded fallback parses. An Inspect AI reimplementation also exists at https://github.com/stefanoamorelli/inspect-evals-mcptox. |

## PDF Corpus
| Work | Local PDF path | Verification status | Why kept |
|---|---|---|---|
| None yet | N/A | not downloaded | Current phase used web-primary pages. Download PDFs only when we need offline citation/source artifacts. |

## Claim-Oriented Novelty Map
| Claim | Closest prior work | Same-claim risk | Novelty delta | Baselines implied | Expansion opportunity |
|---|---|---|---|---|---|
| C1: block unauthorized context-to-decision influence while allowing authorized data use | CaMeL, Task Shield, AgentDojo, InjecAgent | medium | CaMeL separates trusted-query control flow from untrusted data, but IntentCap adds structured user intent, named decision classes, lease proofs, and cross-extension authority over Skills/MCP/subagents. Task Shield checks task alignment, while IntentCap checks provenance-authorized influence and lease derivability. | AgentDojo built-in defenses, Task Shield, CaMeL, vanilla agent, tool filter/static allowlist | Evaluate the same untrusted context under multiple allowed/forbidden influence modes. |
| C2: reduce over-privilege vs static tool/server/Skill policies | Progent, SkillGuard, MCP-Bench, LiveMCPBench | medium | Progent constrains tool calls through policies; SkillGuard is Skill-centric. IntentCap is run-centric and mints leases from current intent and context provenance, not package identity alone. | Progent-style tool policy, Skill manifest baseline, static MCP server allowlist, expert oracle | Measure influence-mode breadth, not only tool count. |
| C3: LLM-assisted compiler plus deterministic checker keeps policy synthesis outside TCB | Progent, ActPlane, EIM/bpftime | medium | ActPlane is enforcement-focused; EIM/bpftime is extension-resource-focused. IntentCap's novelty is deciding which policy is justified by current intent and control provenance. | LLM-only lease generation, deterministic checker, OS-enforcement-only | Show invalid LLM-proposed leases are rejected and equivalent leases lower to multiple backends. |

## Closest Work
| Work | Claim | Method/artifact | Evaluation | Same problem/mechanism/metric/setting? | Gap relative to this project |
|---|---|---|---|---|---|
| AgentDojo | Dynamic environment to evaluate prompt injection attacks and defenses for LLM agents. | Python benchmark with stateful environments, tools, user tasks, injection tasks, and formal checks. | 97 realistic tasks, 629 security test cases, 70 tools, four suites: Workspace, Slack, Travel, Banking. | Same problem and benchmark setting; not the same mechanism. | Use as primary security benchmark; IntentCap should add decision-class/influence checks. |
| InjecAgent | Benchmark vulnerability of tool-integrated agents to indirect prompt injection. | Test cases spanning user and attacker tools. | 1,054 cases, 17 user tools, 62 attacker tools. | Same problem; simpler/simulated setting than AgentDojo. | Useful breadth benchmark for influence-violation taxonomy. |
| CaMeL | Defeat prompt injection by extracting control/data flows from trusted query and enforcing capabilities. | Protective system layer around LLM; released code. | Reports 77% AgentDojo tasks with provable security vs 84% undefended utility. | Same high-level security family and close mechanism. | IntentCap must distinguish itself via user intent certificates, influence modes, decision classes, and cross-extension lease synthesis. |
| Task Shield | Enforce task alignment: every instruction/tool call should serve user objective. | Test-time verifier. | AgentDojo; reports 2.07% attack success and 69.79% utility on GPT-4o. | Same defense setting; different policy basis. | Strong mandatory baseline for goal-derived action filtering. |
| Progent | Fine-grained programmable privilege control for LLM agents. | DSL for deterministic tool-call policies and fallbacks. | Tool-level policy enforcement across agent scenarios. | Same least-privilege problem; mostly tool-call/action level. | IntentCap must show context provenance and decision influence authority beyond operation predicates. |
| SkillGuard | Permission framework for Agent Skills. | Skill-centric permission and monitoring. | Skill workflows. | Same artifact family for Skills. | IntentCap is run-centric, intent-derived, and cross-extension. |
| ActPlane | OS-level programmable enforcement for agent harnesses. | OS/eBPF-style policy enforcement below tool layer. | System enforcement. | Complementary backend; not same policy source. | IntentCap decides what policy is justified before lowering to OS monitors. |
| EIM/bpftime | Safe and efficient application extension model. | Extension features represented as resources/capabilities. | Userspace extension/runtime evaluation. | Adjacent capability system, different protected object. | IntentCap protects authority-bearing decisions and context influence, not extension resource entry points. |
| MCPTox | Tool poisoning benchmark on real-world MCP servers. | Malicious tool descriptions and legitimate-tool execution targets; official artifact now cloned locally for schema probing and successful-response replay. | Paper/search result reports 45 MCP servers, 353 tools, and 1,312 malicious cases; local artifact exposes 45 server groups, 485 tool entries/files, and 1,348 cases in `response_all.json`; R007 parses 2,148 events from all 1,834 `Success` labels. | Same MCP security setting; attack vector is tool description poisoning. | Crucial expansion benchmark for "tool description may not authorize/choose sinks"; next step is adapter reconciliation between paper counts, artifact counts, fallback parse semantics, and online utility. |
| MCP-Bench / LiveMCPBench | Evaluate MCP tool discovery, selection, and use at scale. | MCP server/tool collections and evaluation frameworks. | MCP-Bench focuses end-to-end MCP tasks; LiveMCPBench targets large-scale MCP toolsets and daily tasks. | Same utility setting, not necessarily adversarial. | Use for benign utility/overhead and tool-exposure breadth. |
| tau2/tau3-bench | Evaluate customer-service agents that follow domain policies while using tools. | Domain policies, tools, tasks, simulated users, text/voice modes. | Domains include airline, retail, telecom, banking_knowledge; results saved under `data/simulations/`. | Same policy-following and tool-use pressure. | Good for benign task utility and policy-constrained sink/action selection. |

## Mandatory Baselines
| Baseline | Why reviewer will expect it | Reproduction risk | Fairness notes | Required for claim |
|---|---|---|---|---|
| Vanilla agent | Shows attack/utility starting point. | low to medium, depending on model APIs | Same model, prompts, tasks, and tool catalog as IntentCap. | C1, C2 |
| Static allowlist / tool filter | Natural least-privilege baseline and AgentDojo has a tool-filter defense path. | low | Match allowed tools to task category, not to full oracle. | C1, C2 |
| Human approval only | Common deployment baseline for high-impact actions. | medium, requires approval simulator | Approval prompt must not leak hidden malicious context as policy. | C1 |
| Task Shield | Strong published defense using AgentDojo and user-goal alignment. | medium, code availability must be checked | Use same benchmark/model where possible; otherwise compare methodology separately. | C1 |
| CaMeL | Closest principled control/data-flow defense. | medium to high | If full reproduction is hard, run paper artifact on AgentDojo subset or perform trace-level comparison. | C1, C3 |
| Progent-style privilege DSL | Closest programmable privilege-control baseline. | medium | Encode equivalent tool-call constraints without context influence modes. | C2, C3 |
| Skill manifest / SkillGuard-style policy | Directly addresses Skills. | high until artifact availability verified | Compare package-level permission to run-time lease. | C2 |
| OS enforcement only / ActPlane-style backend | Tests whether enforcement without IntentCap policy is sufficient. | medium | Same low-level denials, no intent/control-provenance constraints. | C1, C3 |

## Baseline Candidates
| Baseline | Why required | Reproduction risk | Fairness notes |
|---|---|---|---|
| AgentDojo built-in defenses | Provides prompt-injection defense baselines already integrated with benchmark. | low | Start here for first reproducible run. |
| MCP server allowlist | Natural MCP deployment baseline. | low | Server-level allowlist should be intentionally broader than per-tool lease. |
| LLM-only lease synthesis | Shows why deterministic checker matters. | low | Feed same proposed plans to checker and measure invalid accepted if checker removed. |
| Expert-written oracle leases | Needed for over-privilege distance. | medium | Start with 10 hand-labeled tasks before expanding. |

## Absorbable Ideas
| Source/community | Idea to absorb | Claim expansion enabled | Experiment implication | Risk |
|---|---|---|---|---|
| AgentDojo | Formal utility/security check functions over environment state | avoids LLM-as-judge for security metrics | implement IntentCap as agent wrapper or offline trajectory checker | adapter work |
| CaMeL | Query-derived control/data-flow extraction | stronger theorem and clearer TCB | compare IntentCap control provenance to CaMeL flows | same-claim risk |
| Task Shield | Objective-serving action check | better intent derivation rule | action must both serve intent and have provenance-authorized control | may blur novelty |
| MCPTox | Poisoned tool descriptions where poisoned tool is not executed | shows description/context influence can be dangerous without direct action | label MCP descriptions as forbidden for authorize/sink/tool-select decisions | artifact available; adapter has full `Success`-label coverage; count/oracle reconciliation and online wrapper pending |
| tau3 | Domain policies and user simulation | tests utility under realistic policies, not only attacks | add policy-as-intent certificates for airline/retail/banking tasks | setup complexity |
| MCP-Bench/LiveMCPBench | large MCP toolset retrieval and selection | tool-exposure minimization at scale | measure exposed tool count and wrong-tool selection under lease scoping | LLM-as-judge may be noisy |

## Adjacent Communities
| Community/venue family | Why relevant | Keywords/aliases | Useful papers or benchmarks |
|---|---|---|---|
| ML security / agent security | prompt injection, IPI, tool poisoning | AgentDojo, InjecAgent, MCPTox, Task Shield, CaMeL | primary security evidence |
| Agent benchmarks | tool-use utility and planning | AgentBench, ToolBench, tau-bench, MCP-Bench, LiveMCPBench | utility and scalability evidence |
| Systems security | capabilities, provenance, IFC, OS enforcement | ActPlane, Capsicum, Landlock/seccomp, EIM/bpftime | enforcement and model positioning |
| Human/approval workflows | approval burden and user intent | human-in-the-loop authorization, consent UX | approval-scope experiment design |

## Venue Evaluation Patterns
- Security reviewers will expect attack success rate, utility preservation, false denial, and adaptive attack discussion.
- Systems reviewers will expect an artifact boundary, TCB, enforcement points, overhead, compatibility, and ablations.
- Agent benchmark reviewers will expect fair model/prompt control, fixed seeds/repetitions where possible, and benchmark-specific oracles.
- Avoid making final paper numbers from LLM-as-judge alone for security outcomes; prefer state-based or rule-based oracles when available.

## Must-Read List
| Priority | Work | Why |
|---|---|---|
| P0 | AgentDojo paper and repository | first reproduction target and strongest security benchmark |
| P0 | CaMeL paper/artifact | closest same-mechanism risk |
| P0 | Task Shield | strong AgentDojo baseline and goal-alignment comparison |
| P0 | MCPTox | MCP-specific tool poisoning and decision-influence benchmark |
| P1 | InjecAgent | broad IPI taxonomy and test cases |
| P1 | Progent | least-privilege/tool-policy baseline |
| P1 | tau2/tau3-bench | realistic policy/tool/user utility benchmark |
| P1 | MCP-Bench/LiveMCPBench | MCP-scale benign utility and tool exposure |

## Novelty Verdict
- Overall same-claim risk: medium.
- Claims safe to keep: context influence as explicit capability; intent-carrying leases; deterministic checker outside LLM TCB; cross-extension run-centric authorization.
- Claims to narrow or drop: "first permission model for Skills/MCP" is too broad and conflicts with SkillGuard/Progent. "Solves prompt injection" must not be claimed.
- Larger claim opportunities: portable intent-provenance-aware policy compiler for agent extension ecosystems; offline trace checker first, runtime enforcer second.
- Absorbable ideas to import: AgentDojo oracles, CaMeL flow split, Task Shield goal alignment, MCPTox poisoned-tool-description cases, tau domain policies.
- Mandatory baselines: vanilla, static allowlist/tool filter, Task Shield, CaMeL, Progent-style policy, Skill manifest/SkillGuard-style policy, OS enforcement only.
- Next action: harden benchmark evidence, with priority on MCPTox oracle/count reconciliation, AgentDojo natural-language attack-goal extraction, InjecAgent setup, or a small online wrapper baseline.
