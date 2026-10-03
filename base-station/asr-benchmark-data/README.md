# Dedicated Arabic ASR comparison

This comparison is separate from `benchmark-runs/nine-local-v1`, which is a
translation-pipeline comparison whose two candidates share Whisper small.

From `base-station/`, create a new immutable run directory:

```sh
./asr-benchmark \
  --corpus benchmark-data \
  --workspace asr-benchmark-runs/nine-local-v2 \
  lock \
  --candidates asr-benchmark-data/candidates.example.json \
  --protocol asr-benchmark-data/protocol.json

./asr-benchmark --corpus benchmark-data --workspace asr-benchmark-runs/nine-local-v2 run --candidate whisper-small
./asr-benchmark --corpus benchmark-data --workspace asr-benchmark-runs/nine-local-v2 run --candidate whisper-large-v3
./asr-benchmark --corpus benchmark-data --workspace asr-benchmark-runs/nine-local-v2 report

.venv/bin/python tools/prepare_asr_review.py \
  --workspace asr-benchmark-runs/nine-local-v2 \
  --corpus benchmark-data \
  --output asr-benchmark-runs/nine-local-v2/review/index.html
```

The lock fingerprints the reference snapshot, each reference file, every audio
file, both model/configuration identities, implementation, and runtime. Result
records are create-only and contain the audio/configuration identities supplied
to inference; reference text is never passed to the ASR adapter. A failed model
or clip remains in the run and makes that candidate selection-ineligible.

`report.json` includes raw hypotheses, per-clip strict and alef-normalized
WER/CER, micro aggregates, failures, elapsed time, and score coverage. Clip 4 is
shown but excluded from the primary aggregate until the faded unclear tail has
a timed boundary. `review/index.html` is an anonymous local listening page with
judgements, error flags, comments, browser autosave, and JSON export. Keep
`review-map.json` hidden until the review is exported.
