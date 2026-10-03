# Moin machine roadmap

The user clarified on 2026-09-22 that the product is an Arabic religious-speech
machine. Version numbers organize work; they must not prevent building and
trying the complete pipeline. The nine-clip benchmark remains quality evidence,
not the whole product and not proof of general religious understanding.

## Product outcome

Accept recorded audio/video and eventually recorded or live YouTube sources;
produce Arabic transcription, English/French meaning, and playable speech.
Keep uncertain speech visible and use sourced Qur'an renderings where reliably
recognized. Provide a website interface after the processing contract works.
Evaluate smaller devices after measuring actual compute, latency, and quality.

## Agreed six-step sequence — updated 2026-09-23

Follow one step at a time: **1. ASR → 2. Translation → 3. TTS →
4. Research and formalize translation evaluation criteria → 5. Market and
competitor research → 6. Public Islamic religious translation benchmark.**
Step 1 is complete for the current product decision: the user approved pinned
Whisper large-v3. Step 2 (translation model selection) is now active. Its next work is candidate
shortlisting and a controlled comparison protocol. The ASR choice is based on the
nine-clip development sample, not a universal-best claim; fresh audio and additional ASR candidates remain non-blocking future
validation. Quality and correctness take priority over cost; paid candidates
are eligible, with spending subject to an agreed budget. The detailed roadmap
and component checklists are in [model-selection.md](model-selection.md).
This sequence takes precedence over earlier roadmap ordering. Product version
numbers below are implementation groupings, not the user's six steps.

| Stage | Identical input for each candidate | Evidence | Status |
| --- | --- | --- | --- |
| 1. ASR | The nine canonical Arabic recordings | Word/character errors against reviewed references, religious-term errors, listening review, timing | User-approved current product choice: pinned Whisper large-v3; broader validation remains future work |
| 2. Translation | The same corrected Arabic text | Blind Arabic–English and Arabic–French meaning review | Active; dedicated text-only comparison not built |
| 3. TTS | The same approved English/French text | Blind listening for pronunciation, clarity, naturalness, omissions, timing | Planned in V3; dedicated voice comparison page not built |
| Supporting complete-pipeline validation | The original recordings | Check how selected components work together, including safety and delay | Experimental playback exists; selected composition not validated |

The existing `base-station/benchmark-review/nine-local-v1/index.html` is a
translation-meaning review of two audio-to-text pipelines sharing the same ASR.
It is neither an ASR comparison nor an isolated translation-model comparison.
Keep its frozen outputs and pending labels intact as earlier pipeline evidence.
Completing it is not a prerequisite for translation-model selection and cannot
replace an isolated text-only MT comparison. Recruit bilingual reviewers for
English and French meaning judgments during Step 2.

V1 covers ASR and translation selection; V2 covers live text delivery; V3 covers
speech delivery and TTS selection. Version numbers do not correspond one-to-one
to the three model stages. This updated sequence takes precedence over older
wording that treats the existing V1 pipeline comparison as sufficient to choose
every language component.

## Earlier product delivery plan — background, not the current work order

Retained for implementation context. Follow the six-step sequence above for
current priorities; the list below does not authorize parallel or later-stage work.

1. Prepare the nine user-reviewed recordings and compare pinned local models.
   Preserve original ASR drafts, corrections, and unclear audio. Export blind
   English/French review; the user supplies judgements before a winner is named.
2. Build a usable recorded-media machine alongside the comparison. A provisional
   configuration can be exercised before a winner is selected, clearly labelled
   experimental. Save input, transcription, translations, safety decisions,
   timings, and playable output so the user can inspect each result.
3. Add recorded YouTube ingestion and a local website using the same machine
   contract. Show progress, errors, provenance, and playback. Network availability
   and source access failures must remain explicit.
4. Add live sources with bounded capture, segmentation, backpressure, cancellation,
   and measured delay. Do not treat a batch file run as a live demonstration.
5. Improve domain quality from reviewed errors. Compare changed configurations
   on identical audio; avoid reference leakage or claiming a model understands
   religious material merely because it emits fluent text.
6. Measure laptop and device feasibility, then choose remote/base-station/device
   compute placement. Hardware deployment depends on actual resource evidence.

## Evidence gates

- Automated tests establish software behavior, not translation correctness.
- Human EN/FR review remains necessary for translation model ranking and meaning
  claims. Arabic review for the current ASR decision is complete; further held-out
  Arabic validation remains a future generalization check.
- The same nine clips are used for selection and evaluation; report /9 and
  disclose reuse. No independent 90% claim or unseen-audio claim is earned.
- Local authorization to evaluate user-selected sources does not establish a
  publisher redistribution licence. Keep downloaded recordings local.
- Existing V1/V2/V3 specs remain useful detail; this sequence supersedes their
  strict prohibition on implementing later plumbing before human scoring.
