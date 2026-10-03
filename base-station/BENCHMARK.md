# Prepared local comparison

The nine-clip comparison is recorded in `benchmark-runs/nine-local-v1`.
Both local configurations processed all nine clips successfully. No human
meaning scores or winner exist yet.

Open `benchmark-review/nine-local-v1/index.html`, listen, choose each label,
and download `review.json`. There are 36 judgements: 9 clips × 2 systems × 2
languages. Download a draft before closing the page; import it to resume.
The original JSON can also be edited directly if the page cannot be opened.
Submit the finished downloaded file with:

```bash
.venv/bin/python -m moin_benchmark --workspace benchmark-runs/nine-local-v1 \
  review submit --split development --file /absolute/path/to/review.json --reviewer your-name
.venv/bin/python -m moin_benchmark --workspace benchmark-runs/nine-local-v1 \
  report development --out benchmark-review/nine-local-v1/report.md
```

Do not inspect the private mapping before reviewing. Scores are irreversible
once submitted. Do not label unavailable outputs faithful. Model names can be
revealed only after every judgement is supplied. The recorded machine can be
tried separately using [MACHINE.md](MACHINE.md).

---

# Moin V1 benchmark

This is a text-only evaluation tool for the recorded-media workflow. Run
commands from `base-station/`, with Python 3.11+ (use 3.11/3.12 for local ML
dependencies).
`./benchmark` and `python -m moin_benchmark` are equivalent. Activate the ML
virtual environment before invoking the executable for real local runs.

## Current nine-clip comparison

The user selected **nine clips total** on 2026-09-22. The active
`benchmark-data/protocol.json` contains `{"mode":"nine-clip-comparison"}`.
This requires exactly nine `development` records and zero `final` records.
No additional clips are needed. Each candidate produces nine English and nine
French outputs for blind review. Reports disclose that selection and evaluation
use the same sample; even 9/9 does not earn an independent quality claim.
Final-set commands are unavailable under this profile. Protocol changes after
locking are rejected. Reference verification, provenance, and category checks
still apply. The user's corrections are in `staging/review-transcripts/`.

Use the development commands below for comparison, report, and composition
selection. The final-run instructions and 12/20 counts below describe the legacy
held-out workflow for separate corpora without `protocol.json`.

## Historical evidence status (before nine-clip scope revision)

The workflow is implemented; no human benchmark scores or 90% claim exist.
`benchmark-data/corpus.json` starts empty deliberately. Synthetic test audio
proves software behavior only. The previous 32-clip collection was deleted at the user’s request. Nine
user-selected YouTube Shorts have been downloaded under `benchmark-data/staging/`
as development review material with machine-draft Arabic transcripts, pending curator checks of provenance,
content categories, clip boundaries, and Arabic transcripts. Do not relabel
machine transcripts as human verified.

## Corpus preparation

Supply exactly 12 development and 20 final records in `corpus.json`. Keep the
final references private to the curator. Each record has this shape:

```json
{
  "id": "dev-01",
  "split": "development",
  "audio": "audio/dev-01.wav",
  "sha256": "64 lowercase hex characters for the canonical WAV file",
  "speaker": "speaker-01",
  "source": {
    "uri": "https://publisher.example/recording",
    "title": "Recording title",
    "retrieved_at": "2026-09-21"
  },
  "source_start_seconds": 120,
  "duration_seconds": 30,
  "permission": {
    "decision": "permitted",
    "basis": "Exact permission or licence and its source URL",
    "reviewer": "Curator name",
    "date": "2026-09-21"
  },
  "tags": ["ordinary-teaching"],
  "transcript": {
    "state": "verified",
    "text": "Human-checked Arabic transcript",
    "reviewer": "Reviewer name",
    "date": "2026-09-21"
  }
}
```

Audio must be uncompressed mono 16 kHz PCM16 WAV. Duration and SHA256 must match.
Paths must stay inside the corpus directory. Duplicate IDs, audio hashes, and
overlapping time ranges from the same source are rejected. Development requires
at least three speakers and all four tags: `ordinary-teaching`,
`islamic-terminology`, `natural-fast-speech`, `quran-adjacent`. Tags are curatorial
judgements, not automatically inferred evidence. Final transcripts may remain
`{"state":"draft"}` and final tags may be empty to avoid content inspection;
candidates never receive reference transcripts or metadata.

```sh
./benchmark corpus validate --split development
./benchmark protocol
```

## Lock and compare

Copy `benchmark-data/candidates.example.json` to a working configuration file.
The baseline uses pinned Whisper small / NLLB 600M, CPU int8 ASR, greedy decoding,
and separate English/French translation. Unlike the live pipeline, one curated
clip is one utterance; there is no VAD resegmentation, TTS, or manual correction.

Lock one to four configurations together before running any comparison:

```sh
./benchmark candidates lock --file benchmark-data/candidates.example.json
./benchmark run --split development --candidate baseline --clip dev-01
# Process the remaining development clips; the existing record is reused:
./benchmark run --split development --candidate baseline
```

A full development run reuses existing records unchanged and processes only
missing clips. Explicitly rerunning a recorded clip is rejected. Repeat for
every candidate in the locked configuration. Failures become records;
there are no automatic retries, fallback models, or substituted outputs.

For paid providers use `adapter: "openai-compatible"`; both `asr` and
`translation` blocks contain `model`, `revision`, `base_url`, `credential_env`,
and optionally `endpoint`. The remote revision must equal the exact model
snapshot/deployment ID; operators must verify that the provider actually pins
that ID. ASR uses `/audio/transcriptions` multipart (Arabic); translation uses
`/chat/completions` with separate `prompts.en` and `prompts.fr`, temperature zero.
A provider-specific protocol such as Qwen-MT translation options needs its own
adapter; it is not automatically interchangeable with chat completions.
Credentials are resolved from named environment variables and never copied to
records. URLs must not embed credentials. Paid calls occur only on `run`.
Provider availability and account access still need a real controlled run.

Global `--corpus DIR` and `--workspace DIR` options come **before** the command.
A different development experiment needs a new workspace. Never reuse the final
set for tuning or move it into a new experiment after observing results.

## Blind human review

```sh
./benchmark review-package create --split development --out /tmp/moin-dev-review
```

Give the reviewer only that exported directory. It includes anonymized WAV
filenames, shuffled anonymous system outputs, the rubric, and `review.json`.
The private workspace contains candidate mappings and must not be shared.
The tool is a local operator protocol, not an access-controlled multi-user
service: an operator with filesystem access can see the underlying sources.

The reviewer listens to audio, then fills each English and French item separately
with `faithful`, `partly_wrong`, or `serious_meaning_error`, plus an optional
comment. Only `faithful` passes. Do not edit source/output fields. Keep the
reviewer independent from the operator who sees candidate identities.

```sh
./benchmark review submit --split development --file /tmp/moin-dev-review/review.json --reviewer 'Reviewer name'
./benchmark report development --out /tmp/moin-development-report.md
```

Submission requires every label and is immutable. The named report is blocked
until all labels are submitted. Failed, empty, or withheld outputs cannot be
marked faithful. Reports show each language separately, error counts, timings,
configuration identities and dates, and the blind-review protocol. Results are
not combined into a single ranking that could conceal one language's weakness.

## Religious safety and composition

Choose a candidate after examining the completed development report. Prepare a
trusted rendering registry using `renderings.example.json` and the schema in
`moin_benchmark/safety.py`. Each Arabic entry needs sourced English and French
text, a version, and explicit approval for each rendering. `detection_ready`
is a curator assertion of full intended detection coverage, not an automatic
proof of completeness. Do not enable it for a handful of sample verses.
The included empty example is deliberately ineligible. The complete prepared
registry is `benchmark-data/staging-renderings/renderings.quranenc.json`: QuranEnc
Rowwad English v1.0.19 and Rachid Maach French v1.0.3, joined to the publisher’s
own Arabic text. Source selection is based on publisher provenance and terms,
not a claim of independent human verification of every translation. See
`benchmark-data/rendering-research.md` for attribution and version obligations.

```sh
./benchmark composition select --candidate baseline --renderings benchmark-data/staging-renderings/renderings.quranenc.json
./benchmark run --candidate moin
./benchmark composition freeze --candidate moin
```

Safety runs after ASR and **before** translation requests. Exact normalized
Qur'an matches use only sourced renderings. Near matches, mixed quotation and
teaching, low-confidence ASR, missing rendering data, and failures withhold
output with a reason. Mixed content is withheld as a whole; this version does
not attempt verse-span reconstruction. Ordinary speech uses the selected
translation configuration. Text matching is conservative but cannot establish
that unrecognized or badly transcribed Qur'an is absent; human review remains
necessary. No theological-certification claim is made.

The selected configuration, prompts, rendering registry, and implementation
identity are hashed together. Moin must run on all 12 development clips before
freezing. Selection is immutable within this workspace; to repair a composition,
start another development experiment before final access. A freeze is not a
quality endorsement, and final evaluation can honestly fail.

## Final proof

```sh
./benchmark run --split final --candidate moin
./benchmark review-package create --split final --out /tmp/moin-final-review
./benchmark review submit --split final --file /tmp/moin-final-review/review.json --reviewer 'Reviewer name'
./benchmark report final --out /tmp/moin-evidence.json
```

Only the frozen composition can process final audio. All 20 clips run together,
once. A failed provider call stays in the denominator. Neither output edits nor
reruns are permitted. A hard process crash leaves the final attempt consumed;
preserve the incomplete workspace and disclose the interruption, rather than
silently restarting the final set. Run `./benchmark finalize-interrupted` to seal
all missing results as explicit non-passing interruption failures, with zero new
provider calls, so that the full denominator can still be reviewed and reported.
A stale `.busy` directory can be removed
only after checking no operator process remains; that does not reset final use.

The evidence JSON is the publishable report; review comments and raw source
material remain private. Publishing is a separate human action. The report
earns its 90% claim only with **18/20 English AND 18/20 French**. A miss is
reported as a miss, and sample accuracy is not a population-wide guarantee.

## Verification

```sh
.venv/bin/python -m pytest -q
```

Tests use generated audio and provider doubles. They cover split isolation,
required corpus metadata, comparison locks, unknown clips, immutable records,
anonymization, missing reviews, safe provider failures, pre-translation safety,
and the independent 18/20 gates. They perform no paid calls and supply no human
quality evidence.

For a dependency-free synthetic CLI walkthrough, run `python tools/benchmark_smoke.py`. It uses a temporary directory, makes no model calls, and demonstrates a deliberately missed French gate.

To reproduce the rendering assembly from the saved publisher artifacts:

```sh
python tools/prepare_renderings.py --select-published-sources --out benchmark-data/staging-renderings/renderings.quranenc.json
```

Without `--select-published-sources`, the builder emits an ineligible draft.
It joins all 114 saved QuranEnc surah API responses to the published SQLite
editions and refuses mismatched ayah keys, text, footnotes, or edition metadata.
Source URLs and retained raw filenames are listed in the rendering research note.

## Separate English and French reviewers

Two reviewers may split the languages: Arabic–English reviews 18 English items;
Arabic–French reviews 18 French items. Each uses their own copy of the exported
package and leaves the other language blank. Return `review-en.json` and
`review-fr.json` with reviewer names/initials. Preserve both originals and merge
only assigned-language labels/comments after verifying all other fields match.
Record both identities in the final submission's reviewer field. Missing or
conflicting labels must be resolved before submission; never fill them with
machine-generated judgements. The full instructions are in the local package's
`REVIEWERS.md`.

Read-only evidence check (exit 3 means human review is still pending, exit 2
means evidence failed validation, exit 0 means a valid review was submitted):

```bash
.venv/bin/python tools/check_v1.py
```

This check validates the lock, outputs, review contents, and matching audio
without exposing the blind model mapping or modifying evidence. It does not
certify translation quality or declare the whole V1 complete.
