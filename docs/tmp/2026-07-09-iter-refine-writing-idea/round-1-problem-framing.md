# Round 1: Problem Framing

Date: 2026-07-09

## Findings (from subagent)

1. **[HIGH, L33]** "Security challenge" framing too narrow — misses safety, auditability, usability
2. **[HIGH, L35-36]** Root cause named but not explained — WHY are existing systems built this way?
3. **[MEDIUM, L70-71]** "Text is not passive data" is ungrounded symptom, not root cause
4. **[MEDIUM, L73-76]** Straw-man gap — dismisses operation-centric defenses in one sentence, no concrete system named
5. **[MEDIUM, L83-84]** Motivating example adversarial-only — needs non-adversarial variant (accidental scope widening)
6. **[LOW, L38-39]** Scope creep: "not to a sandbox or session lifetime" is sweeping for single-task eval
7. **[LOW, L31]** Laundry-list opening delays reader's sense of pain

## Changes Applied

### Abstract S2 (L33): "security challenge" → broader framing
- Before: "This creates a security challenge: all inputs enter one shared planning state with equal influence"
- After: "This creates a security and safety challenge: all inputs enter one shared planning state with equal influence"

### Abstract: add non-adversarial dimension to S2
- Added "whether by malicious injection or accidental misconfiguration" to show both dimensions

### Intro ¶2: add non-adversarial example after adversarial PDF example
- Added sentence about accidental scope widening (Skill accidentally broadening tool call scope)

## Remaining Concerns
- Straw-man gap (finding 4): partially addressed by adding "necessary but incomplete" framing. Full fix would need naming specific systems (Capsicum, SELinux) but space is tight for 2-page.
- Scope creep (finding 6): will address if space allows.
