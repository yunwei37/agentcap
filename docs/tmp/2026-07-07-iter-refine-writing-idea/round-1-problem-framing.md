# Round 1: Problem Framing

Date: 2026-07-07

## What Was Checked

Reviewed the idea-layer problem framing in `docs/autopaper/intentcap-paper-zh.tex`, focusing on:
- Introduction problem/root-cause paragraphs.
- Running example and protected-decision motivation.
- Whether the problem can be stated without naming IntentCap.
- Checklist Section 1: concrete consequence, root cause, straw-man risk, and scope control.

## Findings

Reviewer findings, quoted/paraphrased from the fork review:

> The main line is right: agent context can influence future authority-bearing decisions, while existing permission mechanisms mostly constrain final actions or side effects. But the first-page framing still risks reading like prompt injection under a new name.

Key issues:
- `line 32`: root cause mixed prompt adjacency, model output, downstream guard blindness, and context-as-control-signal. The paper should state that the root cause is missing future-decision authorization state, not merely untrusted text in the prompt.
- `line 34`: the PDF example lacked an early concrete consequence. It should show a final action passing validation while the authority path is already corrupted.
- `line 36`: protected decisions appeared as a list rather than a class derived from authority lifecycle events.
- `line 38`: the prior-work gap risked straw-manning provenance/IFC defenses. It should acknowledge that they can reject some visible flows, while distinguishing IntentCap's consumable future-decision authorization object.
- `line 81`: threat goals were broad and should distinguish primary unauthorized influence from concrete side-effect manifestations.

## What Was Changed

1. Root cause sharpened.
   - Before, line 32 framed context privilege mainly as untrusted context entering adjacent model context and later influencing fields.
   - After, line 32 now states that the structural root cause is authorization state not recording which context may influence which future decision class under the current intent.

2. Concrete failure trace added.
   - Before, line 34 only said PDF content should affect output data but not repo/approval/delegation.
   - After, line 34 adds the failure mode: `create_issue(repo=org/repo-x)` may pass argument validation while the PDF has already induced full GitHub approval or delegated issue authority to an untrusted subagent.

3. Protected decisions defined as a class.
   - Before, line 36 listed tool selection, sink selection, approval scope, request, and delegation.
   - After, line 36 defines them as lifecycle events that mint, select, widen, consume, or delegate authority.

4. Prior-work gap de-strawmanned.
   - Before, line 38 said existing defenses do not allocate context influence authority.
   - After, line 38 acknowledges provenance/taint/IFC-style defenses can reject some materialized suspicious flows, but usually do not maintain a consumable future-decision authorization object tied to intent, control provenance, temporal state, budget, and delegation bounds.

5. Threat target calibrated.
   - Before, line 81 listed many attack goals directly.
   - After, line 81 makes the primary goal unauthorized control over an authority lifecycle event, with wrong repo/file/policy/delegation effects as concrete manifestations.

## Verification

- Ran `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex`.
- Build completed successfully.
- Final log check found no undefined citations, undefined references, fatal errors, or LaTeX errors.
- Remaining warnings are existing fontscript/underfull-box formatting warnings.

## Remaining Concerns

- Round 2 still needs adversarial novelty review: a reviewer may still argue the paper is an organization of provenance/IFC/capabilities unless the insight is phrased as a stronger lifecycle abstraction.
