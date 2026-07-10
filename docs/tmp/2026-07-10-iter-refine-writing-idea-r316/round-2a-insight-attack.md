# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 2a adversarial insight and novelty attack.

## What was checked

The reviewer was asked to attack whether the paper is merely a stateful provenance/ABAC monitor, a Skill/MCP permission framework, or OS/ActPlane policy synthesis.

## Findings

- Must-fix: the strongest rejection still says IntentCap is "provenance/ABAC plus atomic counters." The paper should not claim ABAC lacks expressiveness. It should claim agent runtimes need a specific pre-effect authority-state object that binds field proofs, active lease version, lifecycle mutation, and concrete effect.
- Must-fix: the four owner classes can still look like ordinary provenance labels. The paper should define \(owner(f)\) over protected fields and state a safe-merge condition with \(Accept_{merged} \land Deny_{full}\) counterexamples.
- Must-fix: the characterization numbers support design granularity and counterexamples, not natural prevalence or independent workload evidence.
- Must-fix: the evaluation story should read as three core experiments rather than a ledger of local probes.
- Must-fix: OS/bubblewrap/ActPlane-related results should be contrast evidence showing what OS substrates cannot decide, not evidence that the main contribution is OS policy synthesis.
- Should-fix: split the strongest-baseline paragraph so it first states the natural alternative and then states the necessary interface condition.
- Should-fix: add a minimal checker judgment with \(owner(f)\), \(proof_q(f)\), \(required(d)\), \(Accept(e)\), and consume/commit rules.

## Remaining concerns

The next re-attack should check whether the new formal rule is enough to prevent the "just ABAC with attributes" rejection, and whether the main evaluation still feels like too many small probes.
