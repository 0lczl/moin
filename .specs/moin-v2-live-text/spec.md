# Spec: Moin V2 — Live Religious Arabic Text Prototype

## Problem Statement

A benchmark report alone cannot demonstrate that Moin works in practice. After
V1 chooses the strongest quality configuration, the team needs a small,
automatic prototype that accepts real Arabic speech and shows faithful English
and French text without a person correcting the result.

The prototype must retain the qualities that made the chosen system credible:
its frozen configuration, safety decisions, uncertainty behavior, and traceable
output. It must not reopen model selection through ad hoc substitutions.

## Solution

Build a live Arabic microphone-to-text experience using the Moin configuration
frozen by V1. It displays the Arabic transcript, English translation, French
translation, and a clear safe state whenever Moin withholds a result or routes
Qur'anic material to a trusted rendering.

The prototype is intentionally narrow. It proves quality in a real interaction;
spoken output and offline optimization follow only after this version is
accepted.

## User Stories

1. As a demo operator, I want to speak Arabic into a microphone and see Moin's
   English and French text automatically, so that the quality result is tangible.
2. As a listener, I want to see the Arabic transcript alongside each target
   language, so that a bilingual reviewer can inspect the path to the result.
3. As a listener, I want a sourced Qur'an rendering when a quotation is
   detected, so that Moin never presents machine-generated Qur'an translation.
4. As a listener, I want an honest withheld state when the system is uncertain,
   so that a wrong meaning is not shown as confident text.
5. As the project lead, I want the running configuration and outcome traceable
   to the V1 winner, so that the live demo cannot quietly use a different model.
6. As a hackathon judge, I want a compact demonstration and the linked V1
   benchmark result, so that I can connect the live experience to its evidence.

## Acceptance Criteria

- [ ] The prototype receives Arabic microphone input and produces Arabic,
      English, and French text without human edits.
- [ ] It uses exactly the Moin candidate configuration frozen by V1; any change
      creates a new configuration that cannot inherit V1's final score.
- [ ] It displays one unambiguous state for normal translation, trusted Qur'an
      rendering, withheld uncertainty, and recoverable processing failure.
- [ ] It never outputs a machine-generated Qur'an translation after the safety
      layer identifies Qur'anic material.
- [ ] A reviewer can trace every displayed result to its configuration identity,
      input timestamp, safety outcome, and stage timing without exposing secrets.
- [ ] The prototype can demonstrate representative informal-halaqah speech live
      and requires no manual correction before output appears.
- [ ] The presentation pairs the working text experience with the honest V1
      report rather than claiming universal Arabic accuracy.

## Implementation Decisions

### Architecture & Schema

- **Frozen composition is the execution boundary.** The selected ASR,
  translation, prompt/context, and safety configuration form a versioned Moin
  composition. The live prototype receives this composition as one dependency.
- **Live input is interchangeable with recorded input.** Both use the same
  canonical speech input boundary, so benchmark clips can reproduce problems
  found during live demonstrations.
- **Text presentation is a thin surface.** It renders normalized Moin outcomes;
  it does not contain model-provider logic, Qur'an matching logic, or scoring
  rules.
- **Execution traces are auditable.** A result records input time, Arabic
  transcript, target-language outputs, safety state, timing, and configuration
  identity. Secrets and unnecessary source-audio retention are excluded.

### Interfaces & Contracts

- **Speech-input contract:** deliver canonical Arabic audio plus stream/end-of-
  utterance state to the frozen composition.
- **Moin outcome contract:** return Arabic transcript, English text, French
  text, safety state, configuration identity, timing, and a normalized error
  when no safe output is possible.
- **Presentation contract:** render an outcome without transforming the
  translation text or hiding safety status.
- **Trace contract:** make a non-secret record available for a demo operator or
  reviewer to inspect after each result.

### Behavior & Interactions

- Ordinary speech produces Arabic, English, and French text from the frozen
  configuration.
- Identified Qur'anic passages clearly indicate that a trusted rendering, not
  machine translation, was shown.
- When confidence or safety policy rejects output, the interface clearly says
  that Moin withheld the translation; it does not show a guessed sentence.
- A temporary provider, microphone, or processing failure is shown as
  recoverable and is recorded for later diagnosis.
- Quality is the priority, so V2 may use cloud services. The demo must not call
  itself an offline prototype until a later version proves that property.

## Testing Decisions

- Unit-test outcome-state mapping so normal, Qur'an, withheld, and failed states
  cannot be confused visually or in traces.
- Unit-test that only the frozen V1 configuration is accepted by the live flow.
- Integration-test microphone input with a controlled audio source and a known
  candidate outcome.
- Manually test representative live Arabic, a Qur'anic quotation, ambiguous
  speech, provider failure, and recovery before the presentation.

## Out of Scope

- **Comparing or selecting models:** V1 owns that decision.
- **Text-to-speech:** deferred until text quality is accepted.
- **Offline deployment and performance optimization:** deferred until quality is
  established.
- **Adding languages beyond English and French:** deferred until their own
  fidelity evaluation is defined.

## Open Questions

- Should the demo surface be a minimal browser interface or a local operator
  console?
- What exact wording and visual treatment should communicate withheld
  uncertainty to a user?
- What latency observation is acceptable for a live hackathon demonstration,
  while remaining outside V2's quality score?

## Further Notes

V2 may not claim that its live inputs prove the V1 final score. The 90% score
belongs only to V1's frozen hidden test; V2 shows that the same winning system
can operate automatically with a microphone.
