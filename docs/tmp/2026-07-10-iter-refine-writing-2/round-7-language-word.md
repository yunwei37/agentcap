# Round 7: Language, Word Choice

Date: 2026-07-10

Scope: word choice only for `docs/autopaper/intentcap-paper-zh.tex`. Claims, citations, and quantitative values were preserved. This round targeted project-report wording, vague referents, redundant hedging, hardcoded system names, and over-strong terms.

Reviewer: read-only subagent `Hegel`, using `paper-writing-style` with the iter-refine-writing common pitfalls.

## Findings

Must-fix findings:

- The abstract used "Local multi-boundary suites further show", which read like experiment narration rather than a result.
- The introduction evaluation paragraph listed E1/E2/E3 as a project status update.
- Problem characterization used artifact-heavy wording.
- E2 used "strongest prior-derived policy-style baseline" and "this row", which sounded like internal ledger prose.
- E3 used "Artifact note" and "aggregate tokens", which exposed experiment bookkeeping.
- The current-evidence diagnostic row contained current-checkout and feedback-run details that read like a run log.

Should-fix findings:

- "当前已 instrumented boundaries" sounded like a status report.
- The core insight sentence stacked terms instead of giving the mechanism in prose.
- The contribution boundary used a defensive "only supports bounded evidence" tone.
- The motivating workflow repeated the prompt-injection transition before the benign-run example.
- E3 used table-organization terms such as primary rows and backend rows.
- Lease auditability opened with "Supporting audit" rather than the audit object.

Consider findings:

- Replace vague "这个组合" in background.
- Replace defensive "这些观察的作用不是..." in problem characterization.
- Replace "这些实验支持一个保守的系统结论" in evidence status.
- Replace mechanical "第一组/第二组/第三组/第四组" related-work setup.

## Changes Made

- Rewrote the abstract's multi-boundary result as a direct result sentence about moving the pre-effect commit contract beyond tool calls.
- Rewrote the introduction evaluation paragraph into a claim-facing bounded-evidence sentence while preserving 3,813/3,813 and 3,593/3,823.
- Replaced the dense "Context influence is / field-owned lease is / pre-effect commit is" chain with one mechanism sentence using `\sys` as subject.
- Changed "C3 only supports bounded evidence" to "C3 gives bounded system evidence".
- Replaced vague background referent "这个组合" with "这种由指令、metadata、外部数据和代码组成的扩展形态".
- Reworked the benign-run motivation transition so the local XLSX and GitHub issue examples follow the authorization-granularity claim.
- Replaced artifact-heavy characterization wording with "已有 artifact 和作者复核标签".
- Replaced defensive phrasing around design observations with a direct design-evidence sentence.
- Replaced "strongest baseline" with "closest baseline" and removed "这个 row" phrasing from E2.
- Replaced "Artifact note" with a direct system-surface summary sentence.
- Replaced "Supporting audit" with "Lease audit".
- Compressed the diagnostic recovery row in the current-evidence table so it reports the important boundaries: authority exposure changed without task-level utility improvement, benchmark-derived recovery remains 0, hand-written enumerated suites recover 14/14, and the eight-task suite recovers 8/8.
- Replaced the related-work section opener with a four-mechanism sentence.
- Removed an unnecessary strong word from the E1 matched-slice paragraph: "显著扩大" became "扩大".

## Rejected or Adjusted Suggestions

- The diagnostic recovery table rewrite was accepted in spirit but adjusted to retain the key boundary numbers: 0 recovered benchmark tasks, 14/14 hand-written recoveries, 0 dangerous executions, 6 surfaces, all four owner classes, and 8/8 authorized alternatives.
- No findings were rejected outright.

## Checks Before Verification

- `rg` found no hardcoded `IntentCap` outside the `\sys` macro definition.
- `rg` found no remaining instances of the targeted internal/status words: `current-checkout`, `Artifact note`, `这个 row`, `Supporting audit`, `strongest`, `显著`, `非常`, `基本上`, `实际上`, `需要注意`, or `值得注意`.

## Remaining Concerns

- The paper still contains dense technical vocabulary because the mechanism itself is vocabulary-heavy. Later terminology/claim-tone rounds should decide whether high-frequency terms such as `lease`, `owner`, `proof`, and `checker` need local substitutions or whether they are necessary formal terms.
- The current-evidence table remains dense by design. This round made it less like a run log, but a later layout round may still need to move detailed evidence status into an appendix.
