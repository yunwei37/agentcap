# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 2c adversarial insight and novelty re-attack after Round 2b.

## What was checked

The reviewer re-attacked the latest paper after the Round 2b ABAC/provenance defense. The check focused on whether the paper still reads as stateful provenance/ABAC plus counters, whether the four owner classes read as a formal owner-equivalence result, whether evaluation reads as three core experiments, and whether ActPlane/bubblewrap remains too central.

## Findings

- Must-fix: a strong reviewer can still describe the idea as "stateful provenance/ABAC monitor + owner attributes + counters + atomic update." The paper should name the core claim as an interface obligation or litmus test: runtimes must linearize an authority-state commit object, and systems missing it must prove owner-equivalence and lifecycle-equivalence.
- Must-fix: E2 still risked looking like author-defined counterexamples against author-defined weak baselines. It needed a clearer three-step evidence chain: external artifacts provide field candidates; owner adjudication is independent of checker verdicts; same-event removals only replace issuer/lifecycle.
- Must-fix: the evaluation still had ledger language and R-id traces in E3. Primary text should keep E1/E2/E3 as the main experiments and move recovery, lease audit, and run provenance to supporting status.
- Must-fix: the four-owner model still introduced agent/instruction/tool/env before the owner-equivalence derivation. The text should start from protected fields, then safe merge, then the four prototype equivalence classes.
- Should-fix: OS/bubblewrap should be presented as backend/contrast evidence, not as a primary system contribution.
- Should-fix: abstract should reduce artifact-report numbers and emphasize the three evidence conclusions.
- Should-fix: typed-provenance state guard should be framed as a convergence baseline: once it adds parent-child same-transition update, it implements the IntentCap interface.

## Changes made

- Abstract: reduced artifact-report style result detail and removed the exact no-owner-collapse count from the abstract. The abstract now states the three evidence conclusions: same-event removals expose owner/lifecycle false accepts, local multi-boundary suites exercise the pre-effect commit across non-tool boundaries, and paired workflow separates same-source data use from control proof.
- Introduction: rewrote the strongest-alternative paragraph around an explicit interface obligation and litmus test. The text now says a monitor that exposes the commit object and uses checker-sole-writer lifecycle update implements the IntentCap interface; a runtime that does not expose the object must prove owner-equivalence and lifecycle-equivalence.
- Contributions: changed C1 to name the owner-equivalence and lifecycle-equivalence obligations, and changed C2 to define convergence to the IntentCap interface rather than list sandbox/backend details.
- Design authorization-input subsection: reordered the explanation from protected fields to owner-equivalence criterion to the four prototype classes. It also states earlier that delegation is a compound decision, not a fifth owner.
- Owner-class table: retitled it as field-owner equivalence classes rather than workload-derived context classes.
- E2 opening: inserted the three-step evidence chain and clarified that false accepts are attributed to collapsed/split commit objects under same-event removals.
- E3 opening and table caption: separated primary blockpoint rows from backend/contrast rows. Bubblewrap is now explicitly an OS contrast row, and R-id ledger phrasing was removed from the E3 narrative.

## Remaining concerns

- The novelty direction is stronger, but a future round should still verify whether a reviewer can construct the "reasonable reference-monitor interface, insufficient evidence for necessity" rejection.
- The evaluation now reads less like a ledger, but a writing pass should still consider moving Diagnostic Recovery and Lease Auditability out of the main evaluation flow.
- Evidence gaps remain: independent/blinded field-owner adjudication, benchmark-scale utility/recovery, approval-burden measurement, production MCP integration, and ActPlane/eBPF mediation.
