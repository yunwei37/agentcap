# IntentCap AutoPaper Draft

Last updated: 2026-07-02 America/Vancouver
Status: early research draft; not the frozen two-page workshop abstract

## Working Title
IntentCap: Intent-Carrying Capabilities for LLM Agent Extensions

## Abstract Draft
LLM agents increasingly rely on extension ecosystems: Skills that provide workflow instructions and scripts, MCP servers that expose tool catalogs and external data, local programs that transform files, and subagents that decompose tasks. These extensions create authority even when they do not hold credentials directly. Their text can influence future decisions about which tool to call, which sink to use, which approval to request, or which component should receive delegated authority. Existing defenses largely authorize operations after a policy exists: tool-call guards validate invocations, manifests describe extension permissions, and OS monitors enforce file or network restrictions. They do not directly specify which context may influence which authority-bearing decision under the user's current intent.

IntentCap treats user intent as the root principal and context influence as a least-privilege capability. A trusted intent certificate records the current goal, selected objects, authorized sinks, constraints, approvals, and expiry. Context cells receive provenance labels and allowed influence modes. A capability lease authorizes an operation only when the operation is derivable from the intent certificate and the operation's control provenance is allowed to influence that decision class. An LLM-assisted frontend may propose plans and leases, but a deterministic checker validates provenance, flow, temporal, budget, and delegation constraints before enforcement.

The research plan is to validate IntentCap first as an offline trace checker and then as an online enforcement layer across context construction, tool calls, MCP mediation, local execution, and delegation. The evaluation will adapt existing benchmark families rather than rely only on toy examples: AgentDojo and InjecAgent for indirect prompt injection, MCPTox for MCP tool poisoning, and tau/MCP benchmarks for benign utility and policy-following. The intended claim is scoped: within modeled decision classes and enforced boundaries, IntentCap blocks unauthorized context-to-decision influence while preserving useful data use.

## Paper Shape
1. Introduction: context is a source of control authority in agents.
2. Threat model: untrusted documents, tool outputs, Skill instructions, MCP descriptions/results, and subagent summaries try to steer authority-bearing decisions.
3. Model: intent certificates, context labels, influence modes, decision classes, data/control provenance.
4. Design: lease compiler, deterministic checker, runtime adapters, delegation attenuation.
5. Prototype: offline checker first; online tool/MCP/context adapters second.
6. Evaluation: AgentDojo, InjecAgent, MCPTox, tau/MCP utility tasks, lease minimization, ablations.
7. Related work: CaMeL, Task Shield, Progent, SkillGuard, ActPlane, EIM/bpftime, agent benchmarks.

## Current Non-Negotiable Claims
- Do not claim IntentCap solves prompt injection.
- Do not claim perfect script-behavior inference.
- Do not claim OS enforcement is unnecessary.
- Do not frame the work as EIM for agents or ActPlane policy synthesis.
- Do claim context influence as least-privilege authority, with user intent as the root of run-time authority.

## Next Drafting Gate
No more paper prose should be polished until at least one benchmark setup/dry-run and the local checker sanity test are recorded in `docs/evaluation.md`.
