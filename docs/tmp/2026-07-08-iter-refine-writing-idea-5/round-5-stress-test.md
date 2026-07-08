# Round 5 - Reviewer Stress Test

Date: 2026-07-08

## What Was Checked

Stress-tested the current Chinese IntentCap paper against the idea-quality checklist, especially novelty, systems contribution, contribution/evaluation alignment, and whether the paper remains too close to provenance/policy/ActPlane-style work.

## Findings

Must-fix findings from the read-only reviewer:

- The strongest remaining easy reject is no longer "too close to EIM/bpftime/ActPlane"; it is "the abstraction is plausible, but the implemented system and evaluation are too local/proxy-heavy for a full top-conference systems claim."
- E4 must be framed as an authorization substrate/protected-transition API prototype unless a full production prompt builder, MCP broker, subagent runtime, and ActPlane/kernel backend are integrated.
- E3 needed a stronger baseline than collapsed/no-owner context: a typed provenance policy DSL that keeps source class, field owner, and state predicates but lacks the atomic lease commit.
- E1 utility must remain a reference-action/replay proxy until a larger closed-loop local-Qwen/API task experiment measures task success, unsafe attempts, false denials, and recovery.
- Author-adjudicated labels must remain supporting audit evidence unless independent blinded label replication is added.

Should-fix findings:

- Add an artifact-level system table so the implementation reads like one authorization runtime rather than many scripts.
- Add an "atomic transition" dimension in related work and state that a DSL implementing the same check-and-consume object is equivalent on that boundary.
- Move Qwen diagnostic out of the main E4 boundary table to avoid implying it is the main utility/model experiment.

## What Changed

- The abstract and contribution list now describe \sys as an authorization-substrate prototype instead of an implied production multi-boundary system.
- The paper now reports R241: a strong typed-provenance state-guard baseline blocks 6/7 R217 workflow residuals but false-accepts 1/7 delegation attenuation case without an atomic parent-child lease-set commit.
- Section 6 now includes an artifact-level prototype table mapping checker core, state schema, tool/local gateway, context gateway, delegation monitor, and monitor lowering target to evidence blocks.
- E4's main boundary table no longer includes the Qwen proposer row; Qwen is described in text as an env-boundary diagnostic.
- The related-work table now includes an "Atomic transition" column.
- `docs/evaluation.md` and `docs/implementation.md` now document R241 as an equivalence-boundary baseline, not a broad win over all policy DSLs.

## Remaining Concerns

- A full top-conference systems claim still needs a closed-loop task-level local-Qwen/API experiment over more tasks and a production-like integration path.
- Independent blinded field-owner/adjudication replication is still missing.
- Production ActPlane/kernel enforcement and overhead remain future engineering evidence, not a current claim.
