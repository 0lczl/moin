# ASR reference audit — nine user-reviewed clips

Date: 2026-09-23. Scope: locate and audit the existing Arabic reference set for
the current ASR model-selection step. This is a provenance and scoring audit,
not an independent re-transcription or certification of every word.

## Canonical files and provenance

`base-station/benchmark-data/corpus.json` is the structured corpus record. Each
entry stores the current transcript, audio path/hash, speaker/source metadata,
and a `review_path` under
`base-station/benchmark-data/staging/review-transcripts/<YouTube-ID>.txt`.
Machine-generated drafts remain under `staging/draft-asr/`; keep them separate
from the user-reviewed references. The nine WAV files are under
`staging/audio/` and their IDs and hashes are in `corpus.json`.

The user listened to all nine recordings. They gave explicit word corrections
for clips 1–5 and edited clips 6–9 directly in the review files. The user later
described the set as almost correct and very good. This supports the label
**user-reviewed working references**; it does not establish independent,
word-perfect transcripts. The corpus currently calls their state `verified`,
which is stronger than the documented review process supports. For the new ASR
run, preserve provenance and prefer a distinct state such as `user-reviewed`.

| Clip | YouTube ID | Current reference path | Audit note |
| --- | --- | --- | --- |
| 1 | `XWsDJcbuE5s` | `staging/review-transcripts/XWsDJcbuE5s.txt` | Recorded corrections are reflected: `نقرا`, `السر`, `أصدق` (written `اصدق`), `إذن`. |
| 2 | `7WxtiPxZv1w` | `staging/review-transcripts/7WxtiPxZv1w.txt` | Corrections `ابو غتره`, `صاحب الغترة`, and `بيت شعر` are present. |
| 3 | `oWj_w6LRuUY` | `staging/review-transcripts/oWj_w6LRuUY.txt` | `منشغلا` is present. |
| 4 | `I0tWefiPh-0` | `staging/review-transcripts/I0tWefiPh-0.txt` | Corrected supplication is present through `وارحمني إنك انت`; ending is `[غير واضح]` because the recording fades. |
| 5 | `c5NrOlQ4oig` | `staging/review-transcripts/c5NrOlQ4oig.txt` | `دعته امرأة ذات منصب وجمال` and `يملا قلبه بها` are present. |
| 6 | `Zf4B7Vsk9hA` | `staging/review-transcripts/Zf4B7Vsk9hA.txt` | User edited the file directly; no separate correction list. |
| 7 | `w_gjJJ0U-oQ` | `staging/review-transcripts/w_gjJJ0U-oQ.txt` | User edited the file directly; no separate correction list. |
| 8 | `oCKv130bdDM` | `staging/review-transcripts/oCKv130bdDM.txt` | User edited the file directly; no separate correction list. |
| 9 | `PnQdtdUYDOg` | `staging/review-transcripts/PnQdtdUYDOg.txt` | User edited the file directly and later confirmed clip 9 was okay; includes Qur'an quotations. |

The corpus copies the same text from these review files. The existing
`benchmark-runs/nine-local-v1/comparison.json` fingerprints the corpus and
compares translation pipelines that share Whisper small. It is a separate,
already-exposed run. Do not edit its corpus, references, hashes, or results to
turn it into an ASR comparison. The nine clips are development/model-selection
material, not a held-out test set.

## Scoring decisions needed before an ASR comparison

1. **Freeze a separate ASR snapshot.** Copy the nine user-reviewed references
   into a new versioned ASR run or corpus snapshot, record hashes and the
   correction provenance, and leave the older translation run intact. Model
   inference must receive audio only, never the reference text.
2. **Resolve clip 4's scoring mask.** `[غير واضح]` is an annotation, not speech
   to score. The known supplication must not be inserted from memory. The
   transcript does not yet give a timestamp for where the ending becomes
   unintelligible. Mark the start/end of that unclear span by listening once,
   then exclude that same audio interval from both reference and hypothesis
   scoring; publish scored duration/word coverage. Until then, report clip 4
   separately or omit it from aggregate WER and disclose why. Do not silently
   count `[غير واضح]` as a reference word.
3. **Use transparent Arabic normalization.** A defensible primary score removes
   Unicode presentation differences, diacritics/tatweel and punctuation,
   normalizes whitespace, and tokenizes on whitespace while retaining the
   actual words. Do not stem, paraphrase, or normalize away repetitions,
   omissions, or lexical substitutions. Because user spelling is preserved
   and Arabic hamza/alif spelling varies, report a second clearly named,
   more permissive spelling-normalized WER (for example, normalize alef forms)
   alongside the primary score rather than hiding that choice in one number.
   Keep character error rate as a companion diagnostic, not a replacement for
   word errors or meaning review. Document exact normalization code/version.
4. **Show errors at clip level.** Report normalized WER/CER per clip and
   micro-aggregated totals, with the denominator and any excluded coverage.
   Separately flag errors affecting negation, religious terms/names, Qur'an
   wording, and meaning. Nine clips from three speakers support a small-sample
   comparison only; they do not establish performance on unseen speech.

No transcript was changed during this audit. The only known mandatory scoring
exception is clip 4's faded tail. The remaining user-entered wording—including
nonstandard spelling and apparent disfluencies—should stay intact for the
initial frozen run; normalization belongs in scoring, not silent reference
rewrites. If later listening identifies a genuine correction, issue a new
version and rerun every ASR candidate against that same version.
