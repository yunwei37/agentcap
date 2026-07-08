# Round 8: Terminology and Claim Tone

Date: 2026-07-08

## Findings

Read-only Round 8 review checked invented terms, undefined compound phrases, and self-attacking claim tone in `docs/autopaper/intentcap-paper-zh.tex`.

Must-fix findings:

- The abstract introduced too many terms at once: `protected-decision transition`, `issuer-typed required fields`, `authority state`, and `delegation bounds`.
- The introduction mixed `transaction object`, `protected-decision transition`, and defensive novelty wording.
- `Authority Inputs` used `authority inputs`, `context planes`, `context classes`, and `issuer-typed fields` interchangeably.
- The context authority section overloaded `mode` as both an abstract influence mode and a trace/event field.
- The formal section used temporary terms such as `issuer-typed required-field` and `authorization transaction`.
- Implementation and limitations contained defensive language about not replacing production MCP brokers, OS sandboxes, and user simulators.
- E1 phrasing mixed protected-event safety, live utility, approval burden, and recovery as if they were one result.
- Related-work table headers used abbreviated labels that obscured the comparison.

## Changes Made

- Rewrote the abstract so it first explains the protected transition in plain language, then introduces lease fields.
- Reframed the introduction around future decision authority as consumable authorization state, instead of saying what the paper does not claim.
- Defined `agent`, `instruction`, `tool`, and `env` as four `authority-input classes`; kept `plane` only for figures and formal issuer boundaries.
- Clarified why four classes cannot collapse into three: agent proves intent/sink/approval, instruction proves workflow procedure, tool proves interface/sandbox/credential contract, and env proves runtime facts.
- Replaced generic `mode` wording with `decision-mode` / required influence language.
- Rewrote the typed-field rule paragraph as a checker transition over Skill instruction, tool interface, runtime environment, and agent workflow state.
- Reframed implementation scope as three verified boundary properties plus extension experiment boundaries.
- Rewrote E1, E2, E4, and limitations so current data support protected-event replay, lease audit, local boundary enforcement, and Qwen proposer safety without implying live end-to-end utility.
- Expanded related-work table headings (`Lease lifecycle`, `No promotion`, `Delegation`) and replaced `lease trans.` with `protected-decision lease`.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -quiet intentcap-paper-zh.tex`
- Warning scan for undefined citations/references, LaTeX warnings, and overfull boxes returned no matches.
- `git diff --check` passed.

## Remaining Concerns

- The paper now cleanly defines the four authority-input classes, but `docs/evaluation.md` should be updated next so the experiment plan mirrors the 3-4 core reviewer-facing blocks.
- Round 9 should check paragraph flow after the terminology rewrite, especially the transition from authority-input classes to formal rules.
