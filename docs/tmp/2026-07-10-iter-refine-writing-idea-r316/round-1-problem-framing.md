# R316 idea refinement

Date: 2026-07-10
Target: docs/autopaper/intentcap-paper-zh.tex
Focus: Round 1 problem framing after R313/R314 benchmark-derived denied-call recovery evidence.

## What was checked

Round 1 checked whether the abstract, introduction, problem characterization, and design goals state the problem before the mechanism, avoid making EIM/bpftime/ActPlane the conceptual center, and keep the evidence boundary visible.

## Findings

Reviewer findings used for this round:

- Must-fix: the intro jumped too quickly from the PDF example into internal terms such as field-owned lease and commit object. The first pass needed a minimal authority-state failure trace before system vocabulary.
- Must-fix: the root-cause hierarchy was unstable. The paper used three structural mismatches in one place, two roots in another, and a three-layer storyline elsewhere.
- Must-fix: the abstract result sentence sounded broader than the current evidence. It needed to say that the evidence is artifact-derived replay and local prototype experimentation, not production MCP/ActPlane/eBPF or benchmark-scale utility evidence.
- Must-fix: the characterization numbers needed an early source and label-independence boundary. They should be framed as design-granularity evidence, not natural prevalence.
- Should-fix: mention the strongest alternative as a stateful provenance/ABAC monitor, then define the exact condition under which that alternative converges to the IntentCap interface.
- Should-fix: explain why the four context classes are not arbitrary component names: they are separated when issuer, forgeability surface, observation point, and lifecycle authority differ.
- Should-fix: reword G4 as local adapter feasibility rather than a production enforcement claim.

## Changes made

- Abstract, lines 29--34: clarified that the lease is the authority object and the commit interface is the runtime linearization point. Added that current results are based on artifact-derived replay and local prototype experiments, and explicitly excluded benchmark-scale end-to-end utility, approval-burden reduction, production MCP integration, and ActPlane/eBPF enforcement claims.
- Introduction, line 43: replaced the old list of mismatches with one root cause: current runtimes linearize actions but not authority-state transitions. Recast the three symptoms as authority-root collapse, owner-boundary collapse, and lifecycle/boundary split.
- Introduction, line 43: added the safe-merge criterion for the four owner classes: fields may share an owner only when issuer, forgeability surface, observation point, and lifecycle authority are equivalent.
- Introduction, line 45: added the strongest-baseline framing: a stateful provenance/ABAC monitor can implement part of the interface if it exposes issuer-owned field proofs, a unique checker writer, and same-transition lifecycle mutation.
- Problem Characterization, line 94: changed the source statement to saved benchmark-derived traces, local adapter suites, and controlled counterexample artifacts.
- Design goals, lines 127--151: replaced the outdated "two roots" mapping with one root cause plus three failure forms, and renamed G4 to "Local adapter feasibility for multi-boundary transitions."

## Remaining concerns

- This round improved framing, but it did not complete the full idea-refinement cycle. Remaining rounds should stress-test novelty against stateful provenance/ABAC, Skill/MCP permission systems, and OS-only enforcement.
- The evidence boundary is now clearer in the abstract, but the paper still needs stronger future evidence for benchmark-scale utility, approval burden, independent expert labels, and production enforcement integration before making broader top-conference claims.
