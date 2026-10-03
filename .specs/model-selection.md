# Moin model selection checklist

User decision: 2026-09-23. Follow the six steps below in order, one active step
at a time. Step 1 ASR is approved for the current product configuration; Step 2
translation model selection is now active. Do not start later steps merely
because they are documented. Quality and correctness come before cost; include
paid and free candidates where relevant rather than restricting selection to
local/free models. Actual paid usage needs an agreed budget before spending.
“Best” means strongest measured candidate under disclosed evaluation conditions,
not a universal or unseen-audio claim.

## Agreed six-step roadmap

1. **ASR:** choose the strongest Arabic transcription model from measured results.
2. **Translation:** choose the strongest Arabic–English and Arabic–French
   translation models, prioritizing correctness over price.
3. **TTS:** choose the strongest speech synthesis models/voices.
4. **Translation evaluation criteria:** research established international
   evaluation approaches and primary sources. Define and document what a score
   such as “92% correct” actually measures, its denominator, scoring rules,
   reviewer qualifications, uncertainty, and serious religious meaning errors.
   Research how systems such as DeepL and Google Translate can be fairly compared;
   do not assume one is universally better or that a metric equals percent correct.
5. **Market and competitor research:** identify relevant competitors and compare
   Moin's Islamic religious translation use case with systems such as Gemini,
   DeepL, and others. Distinguish systems used by Moin from competitors; do not
   imply a partnership. Establish supported strengths, limitations, and positioning.
6. **Public benchmark:** build a reproducible domain benchmark with independent
   test material, appropriate expert review, fair competitor configurations,
   and transparent results. Aim for leadership in Islamic religious translation;
   claim superiority only to the extent demonstrated by the evidence.

Steps 1–3 need documented working scoring rules to select candidates. Step 4
formalizes the researched translation evaluation framework for public claims;
earlier selections remain provisional where those criteria require revalidation.
End-to-end machine validation supports the roadmap; it does not replace Step 4.

## Completion checkpoints

| Step | Deliverable before moving on |
| --- | --- |
| 1. ASR | Reproducible comparison, completed Arabic review, and a documented model/configuration choice with limitations or an explicit unresolved tie. |
| 2. Translation | Controlled text-only comparison, completed expert English/French reviews, and a justified choice for each language. |
| 3. TTS | Controlled voice comparison, completed listening reviews, and a justified voice choice for each language. |
| 4. Criteria | Sourced evaluation protocol defining metrics, human rubric, sampling, uncertainty, and exactly which accuracy claims are allowed; revalidate earlier choices if necessary. |
| 5. Market | Sourced competitor comparison and a clear, evidence-supported description of Moin's domain advantage and limitations. |
| 6. Benchmark | Independent evaluation results, reproducible methodology, and a public-facing report whose claims match the evidence. |

An unresolved tie is a reported result, not permission to declare a winner;
resolve it with further evidence or document a justified selection before moving on.

**Current status:** Step 1 is complete for the current product decision. The user
approved pinned Whisper large-v3 as the project ASR after reviewing the local
comparison. This selection is based on the nine-clip development sample and is
not a claim of universal or unseen-audio superiority. Fresh independent audio
and additional candidates remain useful, non-blocking validation. Step 2,
translation model selection, is now active. Next: establish a candidate shortlist
and comparison protocol, then compare Arabic-to-English and Arabic-to-French
configurations independently using the same user-reviewed Arabic reference text.

## Stage 1: ASR — current product choice recorded, within V1

- [x] Retain the nine approved recordings and user-corrected Arabic references.
- [x] Audit and freeze reference versions and scoring rules before comparison.
      Clip 4 remains `[غير واضح]` at the faded ending and is excluded as a whole
      from aggregate scoring until a shared boundary is marked.
- [x] Pin two local candidates, model revisions, decoding settings, runtime,
      and hardware. Inference receives audio/configuration only.
- [x] Run all nine clips through both candidates and save raw outputs, timing,
      failures, and identities in a new, separate run.
- [x] Report strict and alef-normalized Arabic WER/CER per clip and aggregate.
      The submitted clip-level human judgments are recorded in the v2 review
      results alongside the automated scores.
- [x] Build the anonymous Arabic review page with audio, frozen reference,
      transcripts, notes, and JSON export. The user can review Arabic directly.
- [x] User-approved current product configuration: `Systran/faster-whisper-large-v3`,
      revision `edaa852ec7e145841d8ffdb056a99866b5f0a478`, CPU int8, Arabic
      transcription, beam size 5. The run lock confirms this exact revision.
      On 8 scored clips (759 reference words), strict WER was 9.09% versus
      10.67% for Whisper small; the nine-clip human review marked large-v3
      8 correct, 1 minor, 0 serious versus small 0 correct, 5 minor, 4 serious.
      Large-v3 took 430.85 seconds versus 72.35 seconds for small across all
      nine clips. This decision selects the better of the two tested local
      candidates for the current product; it does not establish a global best.

The current comparison is `base-station/asr-benchmark-runs/nine-local-v2/` and
the review page is `base-station/benchmark-review/asr-nine-local-v2/index.html`.
The user-facing instructions are beside the page. The submitted review and
provenance are recorded in `base-station/asr-benchmark-runs/nine-local-v2/review-results/`.
The result describes this development sample only. Clip 4 has human judgments but
remains excluded from aggregate automated scores because its faded ending has
no shared scoring boundary. Additional models and fresh held-out audio can
strengthen the selection later, but do not block the next step.

## Stage 2: Translation — active, within V1

- [ ] Pin candidate translation configurations and provide each the same frozen,
      corrected Arabic reference text. This isolates translation from ASR errors.
- [ ] Build a separate anonymous text review page showing Arabic source and
      English/French outputs with judgement and comment export.
- [ ] Obtain Arabic–English and Arabic–French human meaning reviews using
      faithful, partly wrong, and serious meaning error labels. Religious terms
      and claims need explicit attention; failed outputs cannot count as faithful.
- [ ] Select English and French configurations independently when warranted.
      Keep Qur'an rendering and uncertainty routing visible in the composition.

The existing `nine-local-v1/index.html` contains 36 pending judgements on two
audio-input pipelines sharing one ASR. Preserve it as a separate earlier run.
Its results cannot be relabelled as an isolated translation comparison or used
to select an MT model. The current Step 2 work is to research candidate
configurations, then compare English and French outputs independently using
the same frozen, user-reviewed Arabic reference text. Recruit Arabic-English
and Arabic-French reviewers for the blinded meaning review; obtain an agreed
budget before any paid API usage.

## Stage 3: TTS — V3 quality selection

- [ ] Freeze approved English/French text and choose exact candidate voices and
      synthesis settings. All voices in a language receive identical text.
- [ ] Build an anonymous listening review page with text, playable candidate
      audio, judgement fields, religious-term notes, and comment export.
- [ ] Review clarity, naturalness, pronunciation, missing/added words, generation
      time, and failures. Use language-proficient listeners and bilingual review
      for religious names and terms. Select English and French voices separately.
- [ ] Verify that speech preserves the approved wording and never speaks a
      withheld translation. Follow the detailed V3 spec and phase checklist.

## Supporting validation: the complete machine (not Step 4)

- [ ] Combine the selected ASR, translation, safety rules, and voices; process
      the original audio and inspect transcription, meaning, speech, and delay.
- [ ] Record how ASR errors propagate into translation and speech; independent
      component scores cannot establish end-to-end accuracy.
- [ ] Publish configurations, per-stage evidence, unresolved errors, and sample
      limits. Reuse of the nine clips must be explicit. Additional unseen clips
      would require a separate agreed evaluation before generalization claims.

Review pages for the three stages are planned artifacts, not completed features.
Existing machine playback demonstrates execution only, not selected model quality.
