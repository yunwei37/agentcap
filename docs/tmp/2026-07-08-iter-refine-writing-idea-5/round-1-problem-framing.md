# Round 1: Problem Framing

Date: 2026-07-08

## What Was Checked

Checked `docs/autopaper/intentcap-paper-zh.tex` for problem framing against the idea-quality checklist Section 1: concrete failure consequence, root cause, four authority-input motivation, distinction from EIM/bpftime and ActPlane, and scoped safety claim.

## Findings

Reviewer findings:

- Must-fix: The abstract introduced four context classes before explaining why the existing authorization object is wrong. It also sounded as if every lease must always contain all four proofs.
- Must-fix: The introduction's motivating failure combined approval widening, delegation, stale reuse, and policy update too densely.
- Must-fix: The introduction distinguished tool guards and OS sandboxes, but did not explicitly position EIM/bpftime and ActPlane before related work.
- Must-fix: The introduction lacked a theorem-shaped, falsifiable safety claim before the contribution list.
- Should-fix: The paper should say earlier that run-specific authority matters even without malicious input.
- Should-fix: The four-class argument should include a compact explanation of why common three-class collapses fail.
- Consider: Use `runtime-observation/env` on first mentions of env context.

## What Changed

- Abstract, lines 25-36: added the root-cause sentence that current authorization objects mix or split authority issuers, interface metadata, runtime evidence, and lifecycle; changed "each lease separately takes proof from four classes" to "each protected decision takes proof from the owner class of its required fields"; added saved-trace/reference-proxy/controlled-local qualifiers to result numbers.
- Introduction, lines 43-45: narrowed the motivating failure to a minimal path where `repo=org/repo-x` stays legal but approval scope or delegated capability is controlled by PDF text; moved stale reuse and policy update into follow-on variants.
- Introduction, lines 45-49: made issuer collapse and authority-state split jointly motivate the protected-decision transition as the authorization object; added the non-adversarial union-permission/broad-approval/false-denial motivation.
- Introduction, lines 47-53: clarified the four authority-input classes, including the user-text split into agent-owned intent fields and instruction-owned preferences; added concrete collapse failures for env-to-tool, instruction-to-tool, and tool/instruction-to-agent.
- Introduction, lines 51-53: added early positioning against EIM/bpftime and ActPlane, describing them as possible backends or related abstractions rather than the default authorization object.
- Introduction, lines 63-65: added a falsifiable safety claim over instrumented boundaries and linked E3 to class-substitution false accepts rather than claiming global uniqueness of the four classes.

## Verification

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error intentcap-paper-zh.tex` passed.
- Paper evidence audit passed: 52/52 checks, 0 failures.

## Remaining Concerns

- The paper is now 37 pages in the local draft format, so later writing rounds should tighten language and tables.
- Round 2 should stress-test whether "issuer-owned atomic protected-decision transition" is sufficiently novel relative to provenance/action-authority systems and policy DSLs.
