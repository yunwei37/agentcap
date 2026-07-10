# Round 1: Problem Framing

Date: 2026-07-09

## What Was Checked

Read-only reviewer `Halley` checked `docs/autopaper/intentcap-paper-zh.tex` against the idea-quality checklist Section 1, focusing on the introduction problem statement, root cause, four authority-input motivation, and bounded safety claim after the R244 matched E1 update.

## Findings

Must-fix findings:

- The opening failure example used IntentCap terms too early (`one-shot lease`, `handoff transition`, delegated capability). It should first read as an ordinary runtime failure.
- The root cause needed a lower-level statement independent of IntentCap terminology: current agent runtimes do not expose both field ownership and authority-state consumption/update at the point of high-impact decision submission.
- The four-context explanation in the introduction was too formal and introduced `coarsest safe partition` and `Accept_h => Accept` before the reader had the intuition.
- The bounded safety claim was correct but too late and too terse, which could make result numbers look broader than the instrumented-boundary claim.

Should-fix findings:

- R244 matched E1 numbers needed explicit artifact provenance.
- The `env context` term should be introduced as runtime-observation/env to avoid confusion with Unix environment variables.

## What Changed

- Rewrote the first failure example in the introduction as a plain four-step runtime failure: user selects a repository, PDF text controls a subagent handoff, final tool parameters remain legal, and the violation is the PDF-controlled permission transfer.
- Added a lower-level root-cause sentence before `issuer collapse` and `authority-state split`.
- Replaced the early formal four-context paragraph with the intuitive roles: agent proves what the user authorized, instruction proves the allowed process, tool proves the interface, and runtime-observation/env proves what was actually observed.
- Shortened the EIM/bpftime and ActPlane positioning in the introduction and left detailed discussion to related work.
- Expanded the bounded safety claim before the contribution list: accepted events must have owner-field proof, active lease, intent derivation, provenance constraints, and atomic lifecycle update; the claim does not cover uninstrumented boundaries, LLM-internal causality, production sandbox integrity, or all prompt-injection variants.
- Updated the E1 matched local-Qwen paragraph to name `results/eval/R244E1MATCH214215`, R214 leased, and R215 all-tools as its provenance.
- Changed the authorization-input introduction to say `runtime-observation/env context` before using the shorter `env` abbreviation.

## Remaining Concerns

- The reviewer suggested claim-facing subtitles for E1/E3/E4 and a more visible safe-merge test. These are good candidates for the next idea/writing rounds rather than blocking Round 1.
