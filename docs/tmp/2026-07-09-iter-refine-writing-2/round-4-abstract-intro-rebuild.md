# Round 4 — Abstract/Intro Rebuild (Run 2)
Date: 2026-07-09

## Mapping Diagnosis

### Abstract sentences
| # | Text (abbreviated) | Role | Issue |
|---|---|---|---|
| S1 | "LLM agents take real actions..." | Context | OK |
| S2 | "This creates a security and safety challenge..." | Problem | OK, long |
| S3 | "Current defenses control operations but not inputs..." | Gap | OK |
| S4 | "Unlike traditional systems..." | Root cause / insight setup | Mixed |
| S5 | "Our key insight is that..." | Insight | OK |
| S6 | "IntentCap composes capabilities..." | This paper | OK |
| S7 | "Task plans compile into..." | This paper (mechanism) | OK |
| S8-S10 | Three result sentences | Results | Heavy (3 sentences) |

### Intro paragraphs
| ¶ | Current role | Should be |
|---|---|---|
| P1 (L59-68) | Background + problem pivot | Background only |
| P2 (L70-83) | Existing solutions + example | Problem + example |
| P3 (L85-92) | Root cause + this-paper | Root cause → insight → this-paper |

### Logic chain issues
1. **Missing intro insight**: Abstract S5 ("capabilities should be scoped to task intent") has no corresponding intro paragraph
2. **P1 merges background + problem**: the problem pivot ("any input can influence any action") should start P2 or a new paragraph
3. **P3 merges root cause + this-paper**: need at least a sentence break

## Reorganization Plan

For a 2-page paper, splitting into 5+ paragraphs would be too many. Plan: **3 paragraphs, each with a clean role**.

- **P1 (Background)**: Keep L59-66. Move problem pivot (L67-68) to open P2.
- **P2 (Problem + existing solutions fail)**: Open with problem pivot. Keep PDF example. Keep "existing defenses" content. This merges problem+existing-solutions, which is acceptable in 2 pages.
- **P3 (Root cause → Insight → This-paper)**: Keep root cause (L85-88). ADD the insight sentence that currently only appears in abstract S5 ("capabilities should be scoped to task intent, not to a sandbox or session lifetime"). Then the this-paper sentence (L91-92) follows naturally.

This adds ~1 sentence (the insight) and moves 1 sentence (problem pivot), fixing the logic chain without adding a paragraph.

## Changes to apply
1. End P1 after "generated report" (L65); move problem pivot to open P2
2. Add insight sentence to P3 between root cause and this-paper
3. Abstract: no changes needed (user-controlled, and the abstract-intro correspondence is fixed by adding the insight to the intro)
