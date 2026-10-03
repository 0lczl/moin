# Phases: Moin V3 — Spoken English and French Output Quality

This is Stage 3 of the [model-selection sequence](../model-selection.md), after
ASR and translation selection. Its anonymous listening review page is planned,
not present in the existing `nine-local-v1` translation review. Current machine
speech playback is provisional and does not establish a selected TTS winner.

> Source spec: .specs/moin-v3-spoken-output/spec.md

## Architectural Decisions

Durable decisions that apply across all phases:

- **Speech boundary:** V3 receives only a safe, frozen V2 target-language outcome. It never translates Arabic or changes approved target text.
- **Voice configuration:** English and French have independently selected, versioned voice configurations with non-secret identity, engine/provider, voice, settings, and selection date.
- **Speech evidence:** Every voice sample has a stable ID, language, immutable approved-text reference, tags, source state, and membership in either voice development or confirmation.
- **Speech outcome:** Each attempt records source Moin outcome, target language, text reference, voice configuration, safety state, generation timing, and playback state, with no credentials or unnecessary audio retention.
- **Safety states:** Ordinary translation, trusted Qur'an rendering, withheld uncertainty, and recoverable speech failure remain distinct all the way through playback.
- **Laptop surface:** `/spoken-output` is the laptop demo view. It renders output and controls but contains no provider logic or text transformation.

---

## Phase 1: Safe Text-to-Speech Replay

**User stories**: #1, #2, #6, #7, #8, #9
**Depends on**: V2 Phase 1

### What to build

Deliver one complete laptop path from a frozen V2 outcome to generated English or French audio, its safe-state handling, and an inspectable speech trace. Start with one candidate voice per language so the team can hear real output while preserving the immutable-text boundary.

### Acceptance criteria

- [ ] An ordinary frozen V2 outcome can generate playable English and French audio from exactly its approved target text.
- [ ] A trusted Qur'an outcome speaks only the rendering selected by V2 and retains its source identity.
- [ ] A withheld outcome produces no English or French speech.
- [ ] Speech-service and playback failures produce recoverable, traceable failure outcomes without changing the underlying text or safety state.

### Manual QA plan

1. **Synthesize ordinary English**: Run `moin-speech replay --language en --input <safe-v2-ordinary-outcome>`. **Expected**: laptop audio plays the displayed English text, and the result exposes the frozen composition, candidate voice, timing, and normal safety state.
2. **Synthesize ordinary French**: Run `moin-speech replay --language fr --input <safe-v2-ordinary-outcome>`. **Expected**: laptop audio plays the displayed French text and creates a separate French trace.
3. **Check Qur'an protection**: Run `moin-speech replay --language en --input <safe-v2-quran-outcome>`. **Expected**: the trace identifies a trusted rendering source; no alternate machine-generated wording is played.
4. **Check withholding**: Run `moin-speech replay --language fr --input <withheld-v2-outcome>`. **Expected**: no target-language audio is created and the result clearly states that Moin withheld it.
5. **Check a provider failure**: Run the ordinary replay with an intentionally unavailable voice configuration. **Expected**: a clear recoverable speech failure is recorded; the approved text and its safety state remain visible and unchanged.

---

## Phase 2: Blind English and French Voice Selection

**User stories**: #4, #5, #6, #8
**Depends on**: Phase 1

### What to build

Build the complete evidence path for selecting English and French voice configurations: a documented spoken-output sample set, no more than three anonymous candidate voices per language, human listening review, independent language results, and a frozen selected voice for each language.

### Acceptance criteria

- [ ] The review set includes ordinary teaching, dense religious terms, natural phrasing, and trusted Qur'an renderings for each target language.
- [ ] No more than three fully specified voice configurations per language are compared before selection.
- [ ] Reviewers hear anonymous samples and label each clear and faithful, understandable but flawed, or unacceptable, with terminology/Qur'an issue flags.
- [ ] English and French selected voices are reported and frozen independently with an honest comparison record.

### Manual QA plan

1. **Validate the spoken sample set**: Run `moin-speech corpus validate --split voice-development`. **Expected**: it lists all required content categories for English and French and reports immutable approved-text references for every sample.
2. **Create a blind listening package**: Run `moin-speech review-package create --split voice-development`. **Expected**: samples use anonymous labels and do not reveal provider, engine, or voice names.
3. **Submit a listening judgement**: Listen to one English and one French sample containing religious terminology, then mark each `clear and faithful`, `understandable but flawed`, or `unacceptable`, and add a terminology comment. **Expected**: the two reviews save separately under anonymous labels.
4. **Check incomplete-review behavior**: Generate the voice report before all required judgements are submitted. **Expected**: it identifies missing language/sample reviews and does not select a voice.
5. **Freeze selection**: Complete the reviews and run `moin-speech voices select`. **Expected**: the report reveals voice identities only after scoring and produces one frozen selected configuration for English and one for French.

---

## Phase 3: Laptop Playback and Trace Experience

**User stories**: #1, #2, #3, #6, #7, #8, #9
**Depends on**: Phase 2

### What to build

Make the frozen selected voices available through the laptop’s `/spoken-output` view. A listener can start, pause, replay, and switch English/French audio while seeing the immutable text, visible safety state, trusted Qur'an source when relevant, and a non-secret trace.

### Acceptance criteria

- [ ] `/spoken-output` displays English and French playback availability for ordinary safe V2 outcomes.
- [ ] Playback controls do not change the displayed or spoken target text.
- [ ] Qur'an, withheld, and recoverable failure states are unmistakable and never masquerade as normal audio.
- [ ] A reviewer can inspect the speech trace and reach the linked V1 evidence without exposing secrets.

### Manual QA plan

1. **Use normal controls**: Open `/spoken-output` with an ordinary V2 outcome, choose English, then use Play, Pause, Replay, and switch to French. **Expected**: each selected track plays the matching displayed text; replay does not create altered wording.
2. **Check readable presentation**: Open the same view at 1280×720 and 375×812. **Expected**: language controls, safety state, and the Arabic/English/French text are readable without overlap or horizontal scrolling.
3. **Check Qur'an presentation**: Open `/spoken-output` with a Qur'an outcome. **Expected**: the trusted-rendering label and source appear before playback; a normal-translation label is not shown.
4. **Check withheld and failed presentation**: Open one withheld outcome and one recoverable speech failure. **Expected**: neither presents a usable target-language audio track; each has clear wording and the failed state offers a retry only where appropriate.
5. **Inspect trace**: Open the trace for a successful playback. **Expected**: it shows selected voice, frozen composition, text reference, safety state, timing, and playback outcome, with no credentials.

---

## Phase 4: Live Laptop Speech Demonstration

**User stories**: #1, #2, #3, #6, #7, #8, #9
**Depends on**: Phase 3

### What to build

Connect the spoken-output surface to the V2 live microphone flow, preserving the frozen text composition and selected voices. The finished slice lets a demo operator speak Arabic, receive the existing V2 text outcome, and play safe English/French speech on the laptop with honest failure and withholding behavior.

### Acceptance criteria

- [ ] A live V2 ordinary outcome becomes available for selected English and French playback without manual text editing.
- [ ] Live speech uses only V2’s frozen composition and Phase 2’s frozen voice configurations.
- [ ] Qur'an, withheld, and speech-failure live outcomes retain the same behavior as replayed outcomes.
- [ ] The laptop demonstration pairs its spoken result with the V1 evidence report and does not claim offline operation or universal accuracy.

### Manual QA plan

1. **Run the live happy path**: Open `/spoken-output`, start the V2 microphone flow, and speak a 20–30 second Arabic teaching statement. **Expected**: Arabic, English, and French text appear automatically, then both selected-language tracks can be played without manual text edits.
2. **Check two consecutive turns**: Speak two Arabic statements with a short pause between them. **Expected**: each produces a separately traceable result and the listener can replay either language for each result.
3. **Check live withholding**: Feed a known ambiguous/withheld V2 input through the live flow. **Expected**: the surface shows the withheld state and produces no English or French audio.
4. **Check recovery**: Cause a temporary selected-voice service failure during a live ordinary result, then restore it and retry. **Expected**: the failure remains honest and traceable; retry creates playable audio from the unchanged approved text.
5. **Rehearse for a judge**: At a 1280×720 laptop/projector setup, demonstrate ordinary speech, a recorded Qur'an outcome, and a withheld/failure fallback. **Expected**: an observer can distinguish the states, hear both languages, and see the link between the demo and V1 evidence.
