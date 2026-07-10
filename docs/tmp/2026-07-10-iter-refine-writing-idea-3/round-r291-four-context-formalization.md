# R291 Four-Context Formalization Pass

Date: 2026-07-10

## What Was Checked

Focused idea-layer pass over `docs/autopaper/intentcap-paper-zh.tex` after the paired data/control experiment.
The check asked whether the paper answers the user-facing concern: why `agent`, `instruction`, `tool`, and `env` are four authority-input owners rather than an arbitrary three-class context taxonomy.

## Findings

- The paper already defines the four classes as proof-owner projections rather than component names.
- The paper already gives the safe-merge relation over issuer, forgeability surface, observation point, state writer, and lifecycle authority.
- The paper already reports R281/E2 merge coverage for all six pairwise owner merges.
- The remaining weakness was presentation: the formal section did not state the direct corollary that any three-class partition must merge at least one pair, and the E2 section did not explicitly connect the six-pair coverage table to that corollary.
- A read-only reviewer pass found three additional must-fixes: safe merge should be framed as a semantic `Accept_h => Accept` obligation rather than literal five-attribute equality; E2 should foreground that owner labels come from external evidence before checker replay; and E3/current-evidence wording should separate deterministic adapter rows from the local Qwen proposer diagnostic.

## Changes Made

- Added `推论 1（tested no three-class collapse）` after the owner-merge counterexample criterion.
- The corollary states that any three-class owner partition over `{agent, inst, tool, env}` must merge at least one pair, and that the six tested pairwise false-accept witnesses rule out the collapsed-owner interface on the tested adapter surfaces.
- Added an E2 paragraph connecting Table `three-class-merge-coverage` to the corollary.
- Preserved the scope boundary: this does not rule out an implementation whose external API has three labels but internally retains per-field owner projections and same-transition lifecycle update.
- Rewrote the safe-merge paragraph so the five source attributes are a conservative sufficient test and audit heuristic, while the formal semantic criterion remains `Accept_h => Accept`.
- Reframed E2's field-owner protocol as the first `label-independence protocol` step and explicitly states that E2 proves false-accept existence under predeclared labels, not natural prevalence or independent expert agreement.
- Revised the current-evidence table so the local Qwen proposer row is diagnostic-only rather than part of the primary deterministic multi-boundary adapter claim.
- Tightened the introduction so the four proof owners are presented as the workload-specific instance of field ownership plus same-transition lifecycle requirements, not as a prior taxonomy.

## Remaining Concerns

- This is still tested removal-family coverage, not a global taxonomy minimality proof.
- Independent field-owner adjudication remains needed before using stronger expert-oracle language.
- Production MCP broker, prompt builder, subagent runtime, and ActPlane/kernel integration remain outside the current evidence boundary.
