# AgenticOS 2026 paper #29 — next-stage response plan (handoff)

Scope of this document: **planning only**. It records what the reviews ask for and a
prioritized order for addressing them in a later content stage. No review text is
paraphrased or rewritten here; the verbatim archive lives in
`docs/workshop/reviews/agenticos26-reviews.md` and remains the evidence of record.

Stage-1 (this branch) deliberately did **not** revise the body, did **not** compress it,
and did **not** change track. What stage-1 did: fixed the workshop build, added the three
verified authors, and produced a real PDF. See "Stage-1 outcome" at the end.

## 1. Venue and track facts (do not change without organizer confirmation)

- The paper appears on the official workshop schedule under **Lightning Talks**
  (<https://os-for-agent.github.io/>). It is not listed under the research-paper session.
- Official track definitions: **Track 1 — Vision Papers, 1–2 pages excluding references**;
  Track 2 — Research Papers, up to 6 pages excluding references. ACM double-column format.
- Reviewer #29C writes that the authors "should have used the longer format." That is
  reviewer feedback on the paper's length, **not** organizer authorization to move from
  the vision/lightning track to the 6-page research track. Treat any track change as a
  separate decision that requires explicit organizer confirmation.
- The workshop has **no formal proceedings**; accepted papers appear only on the workshop
  website. Therefore: do **not** invent copyright blocks, DOI, ISBN, or ACM rights data.
  The HotCRP generic ACM Digital Library wording does not establish a paper-specific
  copyright assignment.

## 2. Author and submission metadata (verified 2026-09-12)

Recorded separately from the review text; these are submission-form facts, not review
content.

- Ordered contact-author list (from the authenticated HotCRP edit page
  `https://agenticos26.hotcrp.com/u/1/paper/29/edit`), now mirrored in `main.tex`:
  1. Yusheng Zheng — UC Santa Cruz — `yzhen165@ucsc.edu`
  2. Wenhui Zhang — Roblox — `wenhuizhang.psu@gmail.com`
  3. Yu Mao — Bytedance — `mynotwo@126.com`
- **Final version (camera-ready) upload slot is empty and is required.**
- **Yu Mao's ORCID is missing** in the form. Must be obtained from the author;
  do not invent it.
- Published camera-ready deadline: 2026-08-29. Workshop date: 2026-09-29 (Prague).
- Upstream committed workshop PDF SHA-256:
  `da66069fa8dff0afddf1d1809dc3e56692444ededdd93024d91bb08f66b87c17`, matching the live
  HotCRP submission prefix `da66069f` (submitted July 9, 2026, 8:14:31 AM EDT).

## 3. Review signal, grouped

Three reviews: #29A merit 1 (reject), #29B merit 4 (accept), #29C merit 3 (weak accept).
Decision was **Accept**. The recurring technical asks, consolidated:

**T1 — Trust/threat model and TCB membership.** What the adversary controls; whether the
source labeler, intent issuer, boundary adapters and lease compiler are trusted; whether
the LLM is assumed arbitrarily compromised; and the fact that Figure 1's dashed TCB box
appears to include the LLM-assisted compiler while the caption names only the checker.
Also: how the intent issuer derives the user's maximum authority, and whether that step is
LLM-based (in which case an incorrect initial authority cannot be repaired by narrowing).

**T2 — Source proofs.** What a proof contains and how the checker verifies it. The central
soundness question: after several sources are jointly consumed by one neural planner, how
can a deterministic checker recover which source influenced a given field? Needs an
explicit answer for: restricted copying / proof-carrying generation / another mechanism,
or an honest statement that this is the open problem.

**T3 — Exclusive field ownership.** Jointly determined fields (user authorizes a repo set,
workflow selects an operation, schema restricts syntax, environment supplies content,
policy restricts destination) read more naturally as an intersection of constraints than
as exactly one owner. Also benign data-dependent authorization (user asks to send a report
to the project lead *named in a selected document*).

**T4 — "Intent" terminology.** The abstract's agent-intent framing vs. the later
user-authorized-authority framing are conflated. A compromised agent's proposed plan
cannot itself be an authority source. Distinguish user-authorized intent, agent-proposed
plans, workflow procedures, runtime evidence.

**T5 — Novelty positioning.** The blanket claim "existing defenses control operations but
not which inputs influence decisions" is too broad given CaMeL, Fides, ActPlane, recent
Progent, and the AgenticOS architecture proposal. Needs a precise differentiator.

**T6 — Evaluation description.** How the 3,746 events and 3,813 benign actions were
extracted; end-to-end trajectories vs checker-only replays; how leases were generated; how
ground truth was established; models/prompts used. RQ2 is possibly circular (deny cases
defined by the proposed ownership rules, so collapsing labels raises false accepts by
construction). Missing: per-benchmark results, the two failed ground-truth checks,
RQ4 baselines, and the full pairwise-collapse set.

**T7 — OS-level contribution.** Lowering procedure to ActPlane, how field provenance
survives the mapping to file/process/network events, atomicity of `check_and_consume`
against the eventual side effect. Is this an OS mechanism, an agent-policy compiler, or an
architectural vision?

**T8 — Presentation / structure.** Define field, lease, proof, owner, narrowing, context
placement, Skill instruction slot early rather than at the end of Section 3; add one
end-to-end worked example; note omitted sources (memory, developer/system policy,
organizational policy, parent-agent authority, human approval, authenticated identity);
flag that tool schemas should not grant credential scope when MCP servers may be
untrusted; add a limitations paragraph.

**T9 — Empirics/extensions.** Runtime overhead and latency of the compiler + checker
pipeline; handling of ambiguous provenance (e.g. user pastes a complex multi-source
document).

## 4. Prioritized next-stage order

Ordered by what most reduces rejection risk. P0 items are cheap, high-leverage, and can
be done within the length budget; later items may force a length decision.

- **P0 — Restore credibility of the claimed guarantee.**
  1. Add an explicit threat model + trusted-components list; state plainly which parts are
     in the TCB and that the LLM-assisted compiler is *not* trusted for accept/deny
     (T1). Fix the Figure 1 caption/box inconsistency while doing so.
  2. Define the proof object and the checker's verification procedure, or state precisely
     and honestly what is not yet sound (T2). This is the single most damaging gap across
     #29A and #29C.
  3. Fix "intent" terminology throughout: one consistent scheme for user-authorized
     intent vs. agent plan vs. workflow vs. runtime evidence (T4).
  4. Add a limitations paragraph (T8) and a short evaluation-procedure paragraph covering
     extraction, replay-vs-end-to-end, lease generation, and ground truth (T6).
- **P1 — Position against prior work.** Rewrite the novelty claim as a concrete
  differentiator against CaMeL, Fides, ActPlane, Progent and the AgenticOS architecture
  proposal, rather than a blanket negative (T5).
- **P2 — Tighten the observed weak spots.** Address the exclusive-ownership objection
  with either an intersection formulation or an explicit bounded-selector mechanism, and
  state the shipped behavior (T3). Add per-benchmark numbers, the full pairwise-collapse
  results, RQ4 baselines, and an explanation of the two failed ground-truth checks (T6).
- **P3 — Structure and framing.** Move definitions before first use; add one worked
  end-to-end example (T8). Consider the reviewer-suggested title wording **only as a
  separate, explicit decision** — the accepted title is currently preserved.
- **P4 — New measurements.** Runtime overhead/latency and ambiguous-provenance handling
  (T9); these are the most likely to require space beyond the current budget.

## 5. Length decision still to be made

The body currently exceeds the vision-track limit (numbers in §6). Any reduction is a
**content** decision and was intentionally out of scope for stage 1. Options, in order of
preference:

1. Keep the vision/lightning track and compress the body to ≤2 pages excluding references
   — but only after the P0 correctness edits, since those edits may add text.
2. Request organizer confirmation before any move to the 6-page research track; do not
   treat reviewer #29C's suggestion as that confirmation.

Do **not** resolve this by silently cutting the argument; the reviews specifically ask for
*more* mechanism, not less.

## 6. Stage-1 outcome (facts for the handoff)

- Branch: `camera-ready/agenticos26-paper29`.
- Build fix: `docs/workshop/Makefile` no longer depends on the absent
  `figures/benchmarks.pdf` / `figures/make_benchmarks.py` (the manuscript has no
  `\includegraphics`; its only figure is an inline TikZ picture), and now points
  `TEXINPUTS`/`BSTINPUTS` at the repository root where `acmart.cls` and
  `ACM-Reference-Format.bst` are vendored, with the local directory first so the bare
  document name resolves to the workshop source.
- Build is clean: 0 undefined citations, 0 undefined references. Remaining warnings are
  benign: 13 BibTeX field-completeness warnings, one overfull hbox, a few underfull
  vboxes, and acmart's "possible image without description" notice for the TikZ figure.
- No appendix exists in the source, so the "technically disabled in output but preserved
  in source" condition is already met.
- Page counts (see the delivery report for the exact figures): 3 total pages; body content
  on pages 1–3 with page 3 only partially used; References begin on page 3 and share that
  page with the tail of Discussion — same shared-page status as the upstream PDF.
