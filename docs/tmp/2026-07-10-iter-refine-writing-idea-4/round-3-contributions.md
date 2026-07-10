# Iter Refine Writing Idea Round 3: Contributions and Design Goals

Date: 2026-07-10

Skill workflow: `iter-refine-writing-idea`, Round 3 contributions and design-goal review.

Reviewed file: `docs/autopaper/intentcap-paper-zh.tex`

Reviewer: read-only subagent `Hypatia`.

## What Was Checked

The subagent reviewed whether the contribution list, design goals, theorem statement, implementation summary, and evaluation questions align with the Round 2 protected-decision linearization framing. It checked for artifact-first contribution bullets, compound contributions, orphan goals, evaluation-goal mismatch, and overclaiming beyond evidence.

## Findings

Overall verdict: C1/C2/C3 are close to an OSDI/SOSP-style model/system/evidence structure, but the list still mixed system artifacts, implementation scope, and evidence boundaries.

Must-fix items:

- C2 was too compound and artifact-first because it listed interface, replay, local side effects, context/Skill placement, delegation, and MCP broker in one contribution sentence.
- C3 was inconsistent: the contribution list described it as bounded evaluation evidence, but a later paragraph made C3 sound like cross-boundary implementation plus evidence.
- The repeated claim that LLM/compiler is outside the TCB was not mapped to design goals or evaluation, risking an orphan claim.
- G4's name, `Local adapter feasibility`, sounded like implementation scope rather than a design goal.

Should-fix items:

- Make C1/C2/C3 read as model / system / evidence.
- In the abstract, make the 3,813/3,813 number clearly a reference-action representability proxy, not an end-to-end utility claim.
- Make C1 explicitly say the protected-decision transition is the tested linearization point.
- Keep typed-provenance state guard framed as a convergence boundary, not a defeated prior system.
- Consider renaming formal `agent` notation to avoid confusion with LLM self-authorization.

## Changes Applied

- Abstract line 35 now calls the 3,813/3,813 result a `reference-action representability proxy`.
- C1 now says protected-decision transition is the tested linearization point for authority-state updates and defines safe-merge plus equivalence obligations.
- C2 now states a checker-centered runtime contract and prototype, rather than listing every adapter artifact.
- C3 now states bounded evaluation evidence only.
- The paragraph after the contribution list now fixes the C2/C3 boundary: C2 is runtime/system, C3 is evidence.
- The design-goal paragraph now states that the untrusted LLM/compiler outside the TCB is an implementation invariant of G1 and G3: it may propose leases/events but cannot mint authority or write checker-owned state.
- G4 was renamed to `Multi-boundary pre-effect exposure`.
- The goal map now includes the untrusted compiler minting/mutation invariant under G1/G3.
- The evaluation-method paragraph now describes typed-provenance state guard as the same strong composite named in E2.

## Not Changed

- Formal notation still uses `agent` for the intent/agent-runtime owner in some formulas and result-table labels. This was left unchanged because scripts, saved artifacts, tests, and paper audit anchors use the same historical field name. The paper already states that `agent` is a notation shortcut for intent/agent-runtime owner, not LLM self-issued authority.
- No quantitative values were changed.
- No new experiment was run in this writing step.

## Remaining Concerns

Independent/blinded field-owner adjudication remains the highest-value next evidence gate. The next idea-refinement round should check cross-alignment after these contribution and goal edits.
