# Phases: Moin V1 — Nine-Clip Model Comparison

## Updated priority: select components independently

The user now wants ASR selection first, followed by isolated translation
selection. Follow [the model-selection checklist](../model-selection.md) for
these new comparisons. Dedicated ASR and text-only translation review pages
remain to be built. The checklist below records the earlier frozen pipeline
comparison; do not overwrite its runs or treat it as an ASR comparison.
Bilingual review of that earlier run remains paused and does not block ASR work.

Source: `.specs/moin-v1-benchmark/spec.md`. User revised the scope on 2026-09-22:
the existing nine recordings are sufficient for the complete comparison.

## Phase 1: Prepare the nine reference clips

- [x] Download and canonicalize the nine user-selected recordings from three speakers.
- [x] Obtain user listening feedback and apply supplied Arabic corrections.
- [x] Finalize reference metadata, content categories, and private-local permitted-use records.
      Publisher redistribution licences remain unverified; see REFERENCE-NOTES.md.
- [x] Configure exactly nine development clips and zero final clips.

Preserve raw ASR drafts. Mark clip 4's unclear ending explicitly; do not substitute
a known supplication ending as clearly audible speech. Use the same canonical
audio for every candidate; references are never supplied to the models.

Validation: `benchmark protocol` reports 9/0; corpus validation accepts exactly
nine eligible clips. Missing reference/provenance fields still produce errors.

## Phase 2: Blind comparison

- [x] Lock up to four exact available candidate configurations before running.
      Two local candidates locked in `benchmark-runs/nine-local-v1/comparison.json`.
- [x] Process all nine clips per candidate; record failures without substitution.
      18 recorded runs, zero execution failures. Meaning quality remains unscored.
- [x] Export anonymous English and French outputs for independent human judgement.
      `base-station/benchmark-review/nine-local-v1/index.html` provides 36 judgements.
- [ ] Reveal identities only after all review labels are submitted.

Validation: each candidate contributes 18 judgements (9 clips × 2 languages).
Reports use nine as each language's denominator; failed outputs cannot pass.

## Phase 3: Select the Moin composition

- [ ] Select the configuration supported by completed blind results.
- [ ] Apply trusted Qur'an rendering and uncertainty handling.
- [ ] Exercise the selected safety composition on the same nine clips and record
      its exact configuration, outputs, and any withholding.

Validation: ordinary, recognized Qur'anic, and uncertain material follow their
respective safety routes. This reuse is disclosed; it is not a held-out test.

## Phase 4: Comparison report

- [ ] Present named candidates, English/French faithful counts out of nine,
      meaning errors, timing, configurations, and blind-review method.
- [ ] State that the nine clips were used for selection and evaluation.
- [ ] Make no independent 90% claim or claim of measured unseen-audio accuracy.

Validation: even 9/9 in both languages does not enable the independent quality
claim. Final-set commands are rejected for this profile. The older 12/20 workflow
remains supported only for separate corpora without the nine-clip profile.
