# Spec: Moin V3 — Spoken English and French Output Quality

## Problem Statement

Version Two can show a faithful Arabic-to-English/French result on a laptop, but listeners at a teaching circle need to hear that result as well as read it. Generic text-to-speech can sound unnatural, speak religious names or terms poorly, make the result hard to understand, or quietly diverge from the text that V1 proved.

The team needs a laptop-based spoken-output experience that preserves the frozen V1 meaning, uses a clearly selected voice for English and French, and handles Qur'anic and uncertain material as safely in audio as it does in text.

## Solution

Extend the V2 laptop experience so every safe Moin outcome can generate and play English and French speech using a voice configuration selected by blind human listening review. The system speaks the exact approved display text; it does not translate, rewrite, summarize, or invent content at the speech stage.

V3 keeps the quality-first posture. It may use cloud or local voice services on the laptop, but it evaluates spoken output with representative religious content before selecting the English and French voice configurations. Offline packaging follows in a later version.

## User Stories

1. As a listener, I want to hear the English result from a safe Moin outcome, so that I can follow without reading the screen continuously.
2. As a listener, I want to hear the French result from a safe Moin outcome, so that I can follow in French without reading the screen continuously.
3. As a listener, I want playback controls for each language, so that I can start, pause, replay, or switch the spoken result without changing its text.
4. As a bilingual reviewer, I want blind samples of candidate English and French voices on representative religious content, so that voice selection reflects clarity and naturalness instead of provider reputation.
5. As a bilingual reviewer, I want religious names, terms, and trusted Qur'an renderings to remain intelligible in speech, so that audio does not corrupt the meaning V1 established.
6. As a listener, I want a clearly identified trusted Qur'an rendering spoken when V2 has identified Qur'anic material, so that I know the wording did not come from machine translation.
7. As a listener, I want no spoken guess when Moin withholds its translation, so that uncertainty is not turned into confident audio.
8. As a demo operator, I want each spoken result traceable to the frozen text composition and selected voice configuration, so that the audio demo is credible and diagnosable.
9. As a demo operator, I want a recoverable spoken-output failure state, so that a temporary voice-service or playback failure does not misrepresent the translation or end the demo.

## Acceptance Criteria

- [ ] A safe V2 ordinary-translation outcome can generate and play English and French speech on the laptop without manual editing of the target text.
- [ ] English and French voice configurations are selected independently through blind review of no more than three candidate voice configurations per language on a documented spoken-output sample set.
- [ ] Reviewers assess each candidate sample as clear and faithful to approved text, understandable but flawed, or unacceptable; religious terminology and Qur'an rendering issues are recorded separately.
- [ ] The TTS stage receives approved target text and can never modify the text, call a translation model, or manufacture a replacement sentence.
- [ ] Qur'anic outcomes speak only the trusted rendering identified by V2 and visibly label its source before or during playback.
- [ ] Withheld outcomes do not produce English or French speech; they present a plain-language withheld notice instead.
- [ ] Ordinary, Qur'an, withheld, and recoverable failure states are visibly and audibly distinguishable.
- [ ] Every spoken result records the V1 composition identity, V2 safety state, selected voice identity, input text reference, generation timing, and playback outcome without storing credentials.
- [ ] The laptop demo can play representative informal-halaqah English and French output and pair it with the honest V1 evidence report.

## Implementation Decisions

### Architecture & Schema

- **Frozen text is the speech boundary.** V3 consumes the normalized, safe V2 outcome and treats its selected target text as immutable speech input. No TTS component can access Arabic audio, change model composition, or generate a translation.
- **Voice selection is language-specific.** English and French each have one versioned selected voice configuration. A configuration records provider or engine, voice identity, settings, selection date, and non-secret label.
- **Spoken sample set is first-class evidence.** Each sample has a stable ID, target language, approved source text reference, content tags, source state, and exactly one use: voice development or post-selection confirmation.
- **Speech outcomes are auditable.** A spoken result links the source Moin outcome, target language, immutable text reference, voice configuration, safety state, synthesis timing, and playback state. It excludes credentials and unnecessary retained audio.
- **Laptop presentation remains thin.** The surface renders speech availability, controls, and trace records. Voice-provider transport, retry behavior, audio generation, and caching stay behind a speech module.

### Interfaces & Contracts

- **Speech-input contract:** accept only a V2 outcome with a frozen composition identity, one safe target-language text value, and its safety state.
- **Voice contract:** synthesize immutable text for a specified selected voice configuration and return playable audio, generation timing, and a normalized failure state.
- **Voice-review contract:** present anonymous candidate samples and record one label—clear and faithful, understandable but flawed, or unacceptable—plus an optional comment and terminology/Qur'an issue flag.
- **Playback contract:** start, pause, replay, and switch audio without transforming the underlying text or concealing state.
- **Speech-trace contract:** expose a non-secret record after each attempt for the operator or reviewer to inspect.

### Behavior & Interactions

- An ordinary safe V2 outcome makes English and French playback available.
- Playback uses the exact target text already displayed by V2. It does not silently normalize wording beyond documented pronunciation settings.
- Voice candidates are judged anonymously on a small representative sample set with ordinary teaching, dense religious terms, natural phrasing, and trusted Qur'an renderings. English and French results are selected separately.
- A trusted Qur'an outcome clearly identifies its published rendering before the listener plays it. TTS may speak that trusted text, but may not replace it.
- A withheld outcome has no target-language audio. The interface states that Moin withheld the translation rather than emitting a fabricated or empty synthetic voice result.
- A synthesis or playback failure is recoverable: the interface explains that speech was unavailable, preserves the text/safety state, records the error, and allows a retry when appropriate.
- The default laptop demo may use cloud voice services while quality is being selected. It must not claim offline speech until V4 proves an offline path.

## Testing Decisions

- Unit-test safe speech-input validation, immutable text handoff, safety-state mapping, trace creation, and prevention of speech for withheld output.
- Unit-test voice-review record validation, anonymization boundaries, and independent English/French selection results.
- Integration-test the selected voice configuration and playback interface with controlled text fixtures and normalized provider failure responses.
- Manually assess ordinary teaching, dense terms, Qur'an rendering, withheld output, a voice-service failure, and repeat playback through laptop speakers and headphones before presenting.

## Out of Scope

- **Retuning ASR or translation models:** V1 owns the language-quality winner; V3 cannot alter it.
- **Offline voice packaging, quantization, or cost/performance optimization:** V4 owns the offline and efficient deployment proof.
- **Languages beyond English and French:** each needs its own voice-quality evidence before being added.
- **Voice cloning, imitation, emotional performance, or speaker identity:** the goal is clear neutral rendering, not reproducing a specific person.
- **Speaking Arabic source audio:** V3 speaks approved English and French outcomes only.

## Open Questions

- Which exact English and French voice candidates are available, affordable, and suitable for the laptop demonstration?
- What wording should introduce or label a trusted Qur'an rendering in audio without interrupting the listener too much?
- Should safe audio begin automatically after a V2 result or require an explicit Play action by default?
- What listening-quality threshold should a voice meet before it is selected for the hackathon demo?

## Further Notes

V3 measures speech quality, clarity, and safe delivery. It does not create a new claim about Arabic-to-target-language meaning: that claim belongs to the frozen V1 benchmark.
