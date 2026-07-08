# Round 6: Language, Sentence Structure

Scope: `docs/autopaper/intentcap-paper-zh.tex`.

Skill path: `iter-refine-writing` round 6, with `paper-writing-style` focused on sentence structure.

## Findings

- Must-fix: colon-style definitions and long explanatory sentences in the introduction, authorization-input section, adapter API description, formal comparison paragraph, evaluation setup, and limitations.
- Should-fix: overloaded result sentences in the abstract, E3/E4 setup and result paragraphs, related-work backend paragraph, and conclusion.
- Consider: split the running example attack chain, shorten the related-work table caption, and separate the final conclusion claim from its scope boundary.

## Changes Made

- Replaced `issuer collapse:` and `authority-state split:` patterns with short definitional sentences.
- Split the running example attack chain into separate steps for approval widening/delegation and stale reuse/policy update.
- Split the abstract's multi-boundary result into two sentences.
- Rewrote the adapter API explanation so `field_proofs` is explained as four short issuer-specific proof sentences.
- Split the formal typed-interface comparison into separate projection, owner, proof-consistency, and lifecycle requirements.
- Split evaluation setup into separate model-call, replay, oracle, and baseline-scope sentences.
- Rewrote E3 variant comparison, trace-characterization explanation, and residual result paragraph as sentence-level claims rather than colon/semicolon lists.
- Rewrote E4 setup and result paragraphs in paper style rather than experiment-note style.
- Split the limitations paragraph into four short evidence-boundary paragraphs.
- Shortened the related-work comparison caption and moved `partial`/expressiveness caveats into the surrounding prose.
- Removed Chinese semicolon joins from narrative prose.

## Remaining Concerns

- Several paragraphs remain dense because the paper mixes Chinese explanation with English technical terms. Round 7 should focus on word choice and reduce repeated compound terms without changing claims.
- Long table rows remain dense by nature, but they are tables rather than narrative sentences.
