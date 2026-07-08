# Round 2b: Insight Defense

Date: 2026-07-08

Checked: `/home/yunwei37/workspace/agentcap/docs/autopaper/intentcap-paper-zh.tex`

## Changes Made

- Intro now states the key abstraction boundary directly: ordinary provenance policy asks where a value came from; IntentCap asks whether that source owns the relevant field in the current lease mint, consume, or delegate transition.
- The authority-inputs design subsection now defines the four inputs as non-interchangeable signing interfaces with independent issuers, failure modes, and authority fields, rather than as taxonomy labels.
- The lifecycle/formal section now includes concrete split-state interleavings: stale budget reads, delegation over old authority, and policy-cache reuse after expiry. This explains why capability, provenance, counter, expiry, and delegation checks must be one atomic `check_and_consume` transition.
- The related-work table caption now says it compares default authorization objects as atomic transition state, and notes that a DSL adding all columns atomically would be simulating IntentCap's authorization object.
- The ActPlane related-work paragraph now distinguishes OS-event enforcement from issuer-proof policy synthesis using the GitHub repo example.
- The Skill/MCP related-work paragraph now emphasizes field ownership: even per-run manifests fail if the package/server can declare agent-owned sink, approval, or delegation fields.

## Remaining Concerns

- Round 2c must re-attack novelty after these edits. The likely remaining risk is whether reviewers accept “atomic protected-decision transition” as a new systems abstraction or still view it as policy-language engineering.
- These edits did not add new experiments. They only sharpen how existing E3/R220/R224/R225 evidence maps to novelty.
