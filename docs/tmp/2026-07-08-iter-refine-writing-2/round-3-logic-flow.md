# Round 3: Logic Flow

Date: 2026-07-08

## What Was Checked

Read-only reviewer `Hubble` reviewed `docs/autopaper/intentcap-paper-zh.tex` for systems-paper logic flow after the four-authority-input update. Focus: whether the paper coherently supports (1) four authority-input classes as necessary proof boundaries rather than arbitrary taxonomy, (2) the system contribution as broader than MCP/tool-call guarding, (3) bounded non流水账 evaluation claims, and (4) abstract/intro/design/eval alignment.

## Findings

Must-fix:

- The paper explains why four classes are needed, but E3 needs a claim-facing table mapping each class collapse or lifecycle split to a false-accept counterexample, artifact source, full-checker result, and weakened-checker result.
- The system contribution must be made more concrete than a policy model. Add a specific adapter API and show how tool/MCP, instruction placement, env/runtime monitor, and delegation all submit the same proof object.
- The evaluation still contains too many Rxxx references in the main narrative. Main text should emphasize three experiment names, claim question, baseline failure mode, primary metric, and supported conclusion.

Should-fix:

- Clarify that delegation is a protected transition boundary, not a fifth authority-input class.
- Define env context as env/runtime observation context, not Unix environment variables.
- Align abstract result sentences to E1/E3/E4.

Consider:

- Keep the collapse soundness condition in the formal section, but move repetitive examples into claim-facing tables.
- In related work, make comparison columns match this paper's mechanism interfaces.

## Changes Made

- Abstract and intro result paragraphs now report E1, E3, and E4 separately instead of mixing all results into one aggregate paragraph.
- The first env definition now says `env/runtime observation context` and explicitly states that it is runtime observation and external-data evidence, not Unix environment variables.
- The runtime lowering section now defines a concrete API:

  `check_and_consume(e, lease_id, field_proofs, provenance, sigma) -> allow(sigma', audit) | deny(reason)`

  It also explains the four proof categories submitted by adapters and states that delegation is a protected transition boundary, not a fifth issuer.
- E3 now has Table `collapse-counterexamples`, mapping tool-to-agent, instruction-to-agent, env-to-instruction, lifecycle split, and delegation split to concrete false-accept counterexamples.
- E4 now has Table `e4-boundary-results`, listing block point, attempts, allowed, blocked, weak unsafe accepts, and whether the row is real local execution, local probe, or ActPlane-style replay target.
- Main E3 prose no longer cites R220/R221/R217/R219/R224 inline; it uses artifact-family names and leaves Rxxx provenance in `docs/evaluation.md`.
- `docs/evaluation.md` now records R235 as an oracle-leakage diagnostic and R236 as the blind residual feedback run: 1 unsafe duplicate one-shot call blocked, 1 feedback attempt, 1 recovered correct abort, final 0 dangerous executes.

## Remaining Concerns

- This round improves paper logic but does not close the large missing gate: benchmark-scale task-level recovery/utility with approval metrics remains pending.
- The E4 ActPlane row is still a lowering target/replay, not production kernel mediation or overhead evidence.
- Independent field-owner and expert-oracle adjudication are still needed before using stronger expert/minimality wording.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` succeeded.
- Warning scan found only the existing Fandol font warnings and no `Overfull`, `Float too large`, or generic `LaTeX Warning` entries after the E4 table width fix.
- `git diff --check` passed.
