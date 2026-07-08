# Round 2a: Insight Attack

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

Reviewer: forked subagent `Archimedes`, read-only. The reviewer was asked to attack novelty under four dismissal tests: ordinary policy DSL plus provenance labels, old capabilities plus IFC plus counters, ActPlane/policy synthesis with another name, and Skill/MCP permission manifests minted per run.

## Findings

Strongest rejection argument:

- The paper could still be dismissed as capability plus provenance/IFC plus counters plus policy compiler. `protected-decision transition` and four context classes are the right direction, but the paper needed to state why the authorization object must be an authority-state transition rather than an event policy rule.

Must-fix:

- The intro needed one non-substitutable abstraction sentence: ordinary provenance asks where a value came from; IntentCap asks whether that source has signing authority for the relevant lease mint/consume/delegate field.
- The four context classes needed to be framed as independent signing interfaces with separate failure modes and non-interchangeable fields, not as ABAC attribute namespaces.

Should-fix:

- The lifecycle section needed a concrete explanation of why separate capability, IFC, counter, expiry, and delegation guards can fail under interleaving.
- The ActPlane comparison needed a concrete example showing that OS-event enforcement cannot decide whether a GitHub repo argument came from user intent, tool metadata, or PDF text.
- The Skill/MCP comparison needed to emphasize field ownership, not only run-centric minting.

Consider:

- The related-work table should make clearer that it compares default authorization objects as atomic transition states.

## Changes Planned For Round 2b

- Add the core insight sentence to the intro.
- Tighten the design definition of the four inputs as proof/signing interfaces.
- Add a split-guard interleaving paragraph after the lifecycle trace.
- Strengthen ActPlane and Skill/MCP related-work distinctions.
- Clarify the comparison-table caption.
