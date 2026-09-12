# AgenticOS 2026 — Paper #29 reviews

- Submission title: LLM Agent Capabilities Should Follow Task Intent and Context Source
- System name: IntentCap
- Decision: Accepted
- Source: https://agenticos26.hotcrp.com/u/1/paper/29
- Retrieved: 2026-09-12, authenticated author view (yzhen165@ucsc.edu).
- Submission shown: July 9, 2026, 8:14:31 AM EDT; SHA-256 prefix da66069f.
- The review bodies below are transcribed from the author-visible page. Scores and wording are preserved as review evidence, not instructions to an agent.
- Reviewer C describes the submission as two pages. A suggestion to use a longer format is reviewer feedback, not confirmed organizer approval to switch tracks.

## Venue and final-version metadata

- Official workshop guidelines verified 2026-09-12: https://os-for-agent.github.io/#submission
- ACM double-column conference format; vision papers have a one-to-two-page body limit, excluding references. Research papers have a six-page body limit, excluding references.
- The official website says the workshop has no formal proceedings and papers appear on the workshop website. Generic ACM Digital Library wording in HotCRP does not establish a paper-specific copyright assignment, DOI or ISBN.
- Published camera-ready deadline: 2026-08-29. Workshop: 2026-09-29.
- Author metadata verified at https://agenticos26.hotcrp.com/u/1/paper/29/edit on 2026-09-12, in order: Yusheng Zheng (UC Santa Cruz, yzhen165@ucsc.edu); Wenhui Zhang (Roblox, wenhuizhang.psu@gmail.com); Yu Mao (Bytedance, mynotwo@126.com).
- Final version slot is empty and required. HotCRP reports a missing ORCID for Yu Mao; this must come from the author and should not be invented.
- Repository identity: https://github.com/yunwei37/agentcap ; workshop manuscript at docs/workshop/main.tex. The source title matches submission #29 exactly.

## Review #29A

Overall merit: 1 — Reject
Reviewer expertise: 3 — Knowledgeable

### Paper summary

This vision paper argues that LLM-agent capabilities should be scoped not only to the current task but also to the provenance of the context that influences each decision. The proposed system, IntentCap, partitions agent context into four sources—user intent, workflow instructions, tool schemas, and the runtime environment—and assigns each capability field to an owning source. An LLM-assisted compiler proposes short-lived capability leases, while a deterministic checker validates source proofs and monotonic narrowing before side effects, context placement, or delegation are committed. Accepted leases are enforced at both the tool and OS layers. The paper reports a preliminary replay-based evaluation across several agent benchmarks and small manually constructed test sets.

### Comments for authors

The paper identifies a timely and important problem. In particular, I agree with the high-level observation that a user request, an untrusted document, a tool result, and a Skill instruction should not automatically possess equal authority over an agent’s future actions. Task-scoped leases, deterministic enforcement, attenuation during delegation, and explicit provenance are potentially useful design directions. The topic is also well aligned with the workshop. However, the current manuscript does not yet provide a technically convincing realization of its central idea. My main concern is that the paper assumes, rather than solves, the hardest problem: how a deterministic checker can verify which context source influenced a field after all sources have been processed through a shared LLM planning channel.

1. The threat model and trust model are underspecified

The paper does not clearly state which principals and components are trusted, what the adversary controls, and what security property IntentCap guarantees. For example, can an attacker control Skill text, MCP metadata, tool schemas, memory, tool outputs, or delegated-agent messages? Are the source labeler, intent issuer, boundary adapters, and lease compiler trusted? Is the LLM assumed to be arbitrarily compromised? The statement that user messages are always user intent and tool responses are always runtime environment is not sufficient. A user message may quote an untrusted document, while a tool response may contain values copied from a trusted user-approved object. Message position or transport role does not establish semantic authority. A precise threat model is necessary before the security claims can be evaluated.

2. The source-proof mechanism is missing

The checker takes proofs as input and is said to verify that every field comes from its owner source, but the paper never defines what these proofs contain or how they are verified. Once user instructions, workflow text, schemas, documents, and tool outputs are jointly supplied to an LLM, an output field may depend on all of them. Process-level tagging cannot recover this semantic dependency after the neural planner has merged the inputs. A conservative information-flow analysis would label most LLM outputs as influenced by every input, causing extensive denial. Conversely, trusting the LLM to report a single provenance label would not provide a deterministic security guarantee. The paper should explain whether provenance is preserved through restricted copy operations, separate model invocations, typed variables, taint propagation, proof-carrying generation, or another mechanism. Without such a mechanism, field ownership is a policy statement rather than an enforceable security property.

3. Exclusive field ownership appears too restrictive

Many action fields are jointly determined by multiple sources. For example, the user may authorize a repository set, the workflow may select an operation, the tool schema may restrict syntax, the runtime environment may supply content, and an organizational policy may further restrict the destination. This is naturally expressed as an intersection of constraints, not as exactly one source owning the entire field. The current rule also appears unable to support benign data-dependent authorization. For example, a user may explicitly ask the agent to send a report to the project lead listed in a selected document. In that case, the user authorizes a bounded selector over runtime data. Under the current description, either the document is forbidden from supplying the destination, causing a false rejection, or it is allowed to do so, reopening the injection channel. The design should distinguish authority, control dependence, data dependence, endorsement, and declassification. A lattice or meet-based composition model may be more appropriate than exclusive ownership.

4. The meaning of “intent” is inconsistent

The abstract initially describes capability as depending on the agent’s intent—what the agent wants to do and how it plans to do it. Later, user intent is treated as the maximum authority boundary. These are different concepts. A potentially compromised agent’s proposed plan cannot itself be an authority source. The paper should consistently distinguish user-authorized task intent, agent-proposed plans, workflow procedures, and runtime evidence.

5. The trusted computing base is unclear

The text states that the LLM remains outside the TCB, but Figure 1 appears to place the intent issuer, source labeler, LLM-assisted compiler, and deterministic checker inside the dashed TCB boundary. The caption appears to identify only the deterministic checker as the TCB. More importantly, the paper does not explain how the intent issuer extracts the user’s maximum authority. If this extraction is LLM-based, an incorrect initial authority cannot be repaired by monotonic narrowing. If it is deterministic, the supported request language should be specified.

6. Novelty relative to recent work is not established

The claim that existing defenses control operations but not which inputs influence decisions is too broad. CaMeL explicitly separates trusted control from untrusted data. Fides tracks integrity and confidentiality labels and deterministically enforces information-flow policies. ActPlane propagates influence labels and enforces cross-event and data-flow policies at the OS layer. The latest version of Progent is particularly close to the proposed architecture: it generates policies from the user task and evolving context, checks tool names and arguments deterministically, and uses an SMT solver to guarantee monotonic confinement. The recent AgenticOS architecture also proposes intent declarations, dynamically synthesized least-capability environments, capability tokens, information-flow labels, and OS-level mediation. The paper’s potentially distinctive contribution is the four-source, field-level ownership model. The authors should therefore provide concrete examples that prior IFC, capability, and policy systems cannot express, and explain why four sources and exclusive field ownership are necessary rather than merely one possible taxonomy.

7. The preliminary evaluation is not sufficiently described

The reported numbers cannot be independently interpreted from the paper. It is unclear how the 3,746 security-sensitive events and 3,813 benign actions were extracted, whether they are end-to-end agent trajectories or checker-only replays, how leases were generated, how ground truth was established, and which models and prompts were used. RQ2 may also be partly circular: if deny cases are defined according to the proposed ownership rules, collapsing the corresponding labels will naturally increase false accepts. This does not establish that the four-source partition is uniquely necessary. The paper should report, at minimum: per-benchmark results; the event-extraction and labeling procedure; end-to-end attack success and benign task utility; false accepts and false rejects; adaptive attacks against source labeling and lease generation; named baselines; results for all source-collapse variants; compiler and checker latency; OS-enforcement overhead; details of the 7, 38, and 24 manually constructed or labeled cases. Claims such as “generalizes across enforcement points” are too strong when based on only 38 checks.

8. The OS-level contribution is underdeveloped

The paper states that leases are lowered to ActPlane policies, but does not explain the lowering procedure or identify a new OS abstraction. In particular, it is unclear how field-level provenance is preserved when semantic tool arguments are mapped to file, process, and network events, or how check_and_consume is atomically bound to the eventual side effect. The authors should clarify whether IntentCap is an OS mechanism, an agent-policy compiler targeting ActPlane, or an architectural vision combining existing components. Any of these positions could be reasonable, but the current manuscript blurs them.

9. Additional presentation issues

The four-source taxonomy omits memory, system/developer policy, organizational policy, parent-agent authority, human approval, and authenticated identity assertions. Tool schemas should not themselves be able to grant credential scope, particularly when MCP servers may be untrusted. The terms proofs, lease, field, owner, narrowing, context placement, and Skill instruction slot need formal or operational definitions. The paper states that every pairwise collapse is necessary, but only a subset of pairwise results is reported. The two failed ground-truth checks in RQ1 should be explained. RQ4 should identify all baselines and provide their individual results. A limitations paragraph is needed. The title would read more naturally as “LLM-Agent Capabilities Should Follow Task Intent and Context Provenance” or “…Context Sources.”

Overall, I find the problem framing promising, but the current paper overstates what has been demonstrated. The paper would be stronger as a focused vision paper that clearly separates: (i) the proposed policy principle, (ii) the components already implemented, and (iii) the unresolved problem of sound semantic provenance through an LLM. In its current form, I lean weak reject.

## Review #29B

Overall merit: 4 — Accept
Reviewer expertise: 2 — Some familiarity

### Paper summary

This vision paper proposes IntentCap, a framework designed to secure LLM agents by dynamically scoping capabilities to task intent rather than relying on static sandboxes or session-wide permissions. The authors observe that when all context sources share a single planning channel, untrusted inputs like extracted document text or tool outputs can maliciously or accidentally override critical decision fields such as repository targets or approval scopes. To address this, IntentCap composes capability leases at runtime from four distinct context sources: user intent, workflow instructions, tool schemas, and runtime environment.

### Comments for authors

The paper presents a very timely and interesting solution to the capability-scoping problem in LLM agent architectures. Structuring capabilities around field-level ownership and enforcing monotonic narrowing effectively tackles indirect prompt injections and scope widening at the foundational decision level. It would be beneficial to elaborate on how the system handles edge cases with ambiguous provenance, such as when users paste complex multi-source documents directly into their prompt. Additionally, expanding on the runtime overhead and latency introduced by the LLM lease compiler and deterministic checking pipeline during high-throughput interactive tasks would provide a clearer picture of real-world deployment viability.

## Review #29C

Overall merit: 3 — Weak accept
Reviewer expertise: 2 — Some familiarity

### Paper summary

IntentCap proposes dynamically scoping the capabilities granted to an agent based on the task at hand. Capabilities are derived from four sources of context: User intent, Workflow instructions, Tool schemas, Runtime environment. Composition of the capabilities is performed by an external LLM acting as an "LLM-assisted compiler," paired with a deterministic checker that enforces invariants: capabilities may only narrow monotonically before any side effects, and a subtask inherits capabilities strictly narrower than its parent's. Enforcement builds on Fides and ActPlane. The paper is two pages and includes a brief preliminary evaluation that offers supportive evidence for feasibility.

### Comments for authors

There is enough interesting material here to generate good discussion at the workshop, and the preliminary results provide sufficient support for the core claim. That said, in my view, this is not really a position paper. It's an ongoing-work paper with preliminary results and a system design more involved than two pages can carry. The authors should have used the longer format. As it stands, I wanted to read and understand considerably more of the design than the paper allows. My main technical issue is with the LLM-assisted compiler chioce. The system aims to provide guarantees about capability scoping, but the LLM sitting inside the TCB can still make mistakes. It is not clear how this is handled, nor whether an attacker could bypass the compiler by manipulating any of the four context sources. This is the central soundness question and the paper does not address it. The organization is weak. The paper discusses fields throughout but never defines them until the very end of Section 3. Even at that point, the definition would benefit substantially from a worked example to make the mechanism concrete. What would strengthen the paper: a threat model that states explicitly what the LLM-compiler is and is not trusted to get right, plus one end-to-end worked example tracing a task through the four context sources to a concrete capability set.
