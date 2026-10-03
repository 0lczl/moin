# Phases: Moin V2 — Live Religious Arabic Text Prototype

> Source spec: .specs/moin-v2-live-text/spec.md

## Architectural Decisions

Durable decisions that apply across all phases:

- **Composition:** V2 accepts only the versioned Moin composition frozen by V1. A changed composition receives a new identity and cannot inherit V1's final result.
- **Input boundary:** Live microphone and recorded audio both enter through the same canonical Arabic speech-input contract.
- **Outcome model:** Every outcome contains Arabic transcript, English text, French text, safety state, configuration identity, stage timing, and a normalized error when needed.
- **Safety states:** The presentation has exactly four distinguishable states: ordinary translation, trusted Qur'an rendering, withheld uncertainty, and recoverable processing failure.
- **Trace:** Every displayed outcome receives a non-secret trace record. It excludes unnecessary source-audio retention.
- **Presentation:** The text surface renders normalized outcomes without provider logic, translation transformations, or concealed safety states.

---

## Phase 1: Frozen Outcome Replay

**User stories**: #2, #3, #4, #5
**Depends on**: V1 Phase 3

### What to build

Deliver a complete replayable path from a recorded Arabic clip through the V1-frozen composition to an inspectable text outcome and trace. Establish the four safety states and prevent any unfrozen or changed configuration from being used by the prototype.

### Acceptance criteria

- [ ] A recorded Arabic clip produces Arabic, English, and French text through the frozen V1 composition without human edits.
- [ ] Qur'an, withheld, and recoverable-failure outcomes are distinct from ordinary translation in both output and trace.
- [ ] Every result has a non-secret configuration identity, input timestamp, safety outcome, and stage timing.
- [ ] An unfrozen or mismatched composition cannot execute as the V2 configuration.

### Manual QA plan

1. **Replay ordinary speech**: Run `moin-live replay --input <ordinary-arabic-audio>`. **Expected**: it prints or displays Arabic, English, French, the frozen composition identity, normal safety state, and stage timings.
2. **Replay Qur'an-adjacent speech**: Run `moin-live replay --input <quran-adjacent-audio>`. **Expected**: the result says that a trusted rendering was used, identifies its source, and does not present a machine-generated Qur'an translation.
3. **Replay an uncertain sample**: Run `moin-live replay --input <ambiguous-audio>`. **Expected**: the result visibly withholds translation and records why, rather than returning confident English or French text.
4. **Try a changed composition**: Run `moin-live replay --composition <non-frozen-or-altered-id> --input <ordinary-arabic-audio>`. **Expected**: execution is refused and the error makes clear that V2 accepts only V1's frozen identity.

---

## Phase 2: Inspectable Text Demo Surface

**User stories**: #2, #3, #4, #5, #6
**Depends on**: Phase 1

### What to build

Build the compact demo surface that turns a normalized replay outcome into an easy-to-read Arabic/English/French experience. It must show the safety state and let an operator inspect the non-secret trace, with a direct link to the honest V1 benchmark evidence.

### Acceptance criteria

- [ ] The demo surface shows Arabic transcript alongside English and French output for ordinary speech.
- [ ] Qur'an, withheld, and failed outcomes have unambiguous, visually distinct states with no hidden substitute text.
- [ ] The trace view exposes configuration identity, timestamp, safety outcome, and timing without exposing secrets.
- [ ] The demo includes a clear link or reference to the V1 benchmark report and does not claim universal Arabic accuracy.

### Manual QA plan

1. **View a normal result**: Open the live-text demo after running an ordinary replay. **Expected**: Arabic, English, and French appear together; all are readable at a 1280×720 presentation viewport without horizontal scrolling.
2. **View a Qur'an result**: Open a replay result with Qur'anic content. **Expected**: the trusted-rendering state and source are clear before the translated text; ordinary machine-translation styling is not used.
3. **View a withheld result**: Open a result marked withheld. **Expected**: the surface says Moin withheld the translation, explains the uncertainty in plain language, and shows no guessed target-language text.
4. **Inspect evidence and trace**: Select the result's trace control and then the V1 evidence reference. **Expected**: the trace contains non-secret diagnostic fields, and the evidence reference opens the separate V1 report rather than implying the live result itself earned the score.

---

## Phase 3: Live Microphone Demonstration

**User stories**: #1, #2, #3, #4, #5, #6
**Depends on**: Phase 2

### What to build

Replace replay input with live Arabic microphone capture while preserving exactly the same frozen composition, outcomes, text surface, trace, and safety behavior. The finished vertical slice gives a demo operator an automatic, recoverable live experience suitable for representative informal-halaqah speech.

### Acceptance criteria

- [ ] Arabic microphone speech automatically produces a V2 outcome without human correction before display.
- [ ] Live results use the same frozen composition and trace shape as replayed results.
- [ ] Loss of microphone access, provider availability, or processing produces the recoverable failed state and leaves the demo usable for the next attempt.
- [ ] The demo can show representative informal-halaqah speech live while pairing the experience with V1 evidence.

### Manual QA plan

1. **Run the happy path**: Open the live-text demo, choose the microphone input, and speak a 20–30 second ordinary Arabic teaching sentence. **Expected**: Arabic, English, and French appear automatically with a live trace and no operator text edit.
2. **Check continuing use**: Speak a second Arabic utterance after the first result. **Expected**: a new outcome appears with its own timestamp and trace; the first result is not silently overwritten as the only record.
3. **Check microphone failure**: Deny microphone permission or disconnect the selected microphone, then start capture. **Expected**: the surface shows a recoverable processing/input failure with a clear retry action and never invents translation text.
4. **Presentation review**: At a 1280×720 projector viewport, conduct one live ordinary-speech run and one recorded Qur'an/withheld fallback run. **Expected**: an observer can distinguish all outcomes, inspect the trace, and reach the V1 evidence in under a minute.
