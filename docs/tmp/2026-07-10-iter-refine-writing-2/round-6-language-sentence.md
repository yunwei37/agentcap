# Round 6: Language, Sentence Structure

Date: 2026-07-10

Scope: sentence structure only for `docs/autopaper/intentcap-paper-zh.tex`. Claims, citations, and quantitative values were treated as read-only.

Reviewer: read-only subagent `Cicero`, using `paper-writing-style` with the iter-refine-writing common pitfalls.

## Findings

Must-fix findings focused on long sentences and note-like semicolon chains in the abstract/introduction, the four-owner motivation, the PDF-to-issue walkthrough, E2 baseline explanation, the evidence table, and the ActPlane related-work positioning.

Should-fix findings focused on result sentences joined by semicolons, a colon-led architecture sentence, a long owner-derivation sentence, runtime-lowering prose, denial-recovery prose, and the limitations summary.

Consider findings flagged the intro related-work list, the problem-characterization paragraph, the evidence-table caption, and the conclusion sentence.

## Changes Made

- Abstract result sentence:
  - Before: one sentence joined the 3,813/3,813 coverage result and the 3,593/3,823 false-accept result with a semicolon.
  - After: the two results are split into two direct sentences.

- Introduction failure modes:
  - Before: three structural failures were listed in one colon-plus-semicolon sentence.
  - After: the sentence uses an explicit numbered list inside prose while preserving all three failure modes.

- Four proof-owner explanation:
  - Before: agent, instruction, tool, and env owners were defined through one semicolon chain.
  - After: each owner has its own short sentence explaining the proof question it answers.

- Running example and owner motivation:
  - Before: the PDF Skill examples and the four proof questions used long semicolon chains.
  - After: the examples are split by run, and the four proof questions are expressed as an explicit numbered sequence.

- System overview and walkthrough:
  - Before: architecture and PDF-to-issue flow used colon-led long sentences.
  - After: the architecture sentence is split, and the walkthrough is expressed as five ordered steps.

- Owner derivation and runtime lowering:
  - Before: safe-merge derivation and adapter differences were compressed into semicolon-linked sentences.
  - After: derivation is broken into three sentences, and adapter differences are stated after the shared checker transition.

- E2 baseline explanation:
  - Before: one long paragraph mixed baseline definition, residual results, convergence boundary, and removal-family interpretation.
  - After: the paragraph now separates the convergence question, strongest prior-derived baseline, lifecycle residual numbers, remaining false accept, and interface-invariant interpretation.

- Evidence table:
  - Before: the multi-boundary row read like a concatenated experiment ledger.
  - After: the row leads with the adapter contract claim, keeps the same numbers, and groups MCP-style broker, lowered-policy audit, and bubblewrap probe under the local-backend boundary point.

- Related work and conclusion:
  - Before: ActPlane positioning and the conclusion compressed mechanism, boundary, and claim in long sentences.
  - After: ActPlane is separated into env-projection backend, pre-OS authority layer, lowering contract, and non-issuer boundary. The conclusion now separates the linearization object from the evidence summary.

- System-name macro hygiene:
  - Replaced hardcoded `IntentCap` in prose/table cells with `\sys`, leaving only the macro definition.

## Consider Items

Accepted:

- Intro related-work list: converted several short list-like sentences into one flowing comparison sentence.
- Problem characterization: rewrote the "First/Second/Third" structure into a claim-first paragraph while preserving all counts.
- Evidence caption: normalized mixed Chinese/English punctuation.
- Conclusion: split the long mechanism sentence.

Rejected:

- None. All Consider items improved flow without changing the claim or numbers.

## Remaining Concerns

- Many semicolons remain elsewhere because this round applied targeted edits rather than whole-paper punctuation normalization. Several are inside formal explanations, table captions, or explicit contrast sentences and should be reviewed in later language-flow rounds.
- The evidence table still contains dense rows because the current paper is 55 pages and records several local diagnostic suites. Later rounds should decide whether to move some table detail into an appendix or compress evidence status further.
