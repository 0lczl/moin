# Translation engine pilot

This is a separate, text-only experiment for Step 2. It sends the nine frozen,
human-reviewed Arabic transcripts directly to translation candidates. It does
not read audio, run ASR, or change the live translator or the existing audio
benchmark. Candidate results are provisional until human reviewers judge the
English and French meanings.

The candidate list is in `benchmark-data/translation-candidates.json`. It
contains the local NLLB, Qwen, and TranslateGemma candidates plus Google Cloud
Translation NMT. This does not select a winner or change any default. Google
Cloud Translation is a paid service; requests occur only when an operator
explicitly runs the Google candidate. Its v3 endpoint uses the general NMT
model, Arabic source, and English or French target.

For Google, install the listed requirements, configure Application Default
Credentials on the server, and set `MOIN_GOOGLE_CLOUD_PROJECT`. The identity
needs access to Cloud Translation and the Google Cloud project must have the
API enabled and billing configured. No key or credential is stored in this
repository or run artifacts. Each input is checked against the 50,000-character
Moin pilot limit and rejected whole if it exceeds the limit. Before any Google
authentication or request, the runner also sums all nine Arabic inputs across
both target languages and aborts the complete pilot if the cumulative source
character total exceeds 50,000. This cap is Moin's own safeguard. It does not
guarantee that usage is free, because the Cloud project may have other usage or
Google may change its allowance. The expected free monthly NMT allowance must
be checked in the project's current billing console before a real run.

The local project environment now has `google-auth[requests]` installed. On a
new server, install that package from `requirements.txt`, enable Cloud
Translation API and billing for the selected project, and configure server-side
Application Default Credentials. Do not put a service-account key in this
repository or send it to a reviewer.

From `base-station/`, create a new private workspace, lock at least two
candidates, then run each candidate once:

```sh
.venv/bin/python -m moin_translation_benchmark list
.venv/bin/python -m moin_translation_benchmark lock \
  --workspace translation-benchmark-runs/translation-pilot-v1 \
  --candidate local-nllb --candidate google-cloud-nmt
.venv/bin/python -m moin_translation_benchmark run \
  --workspace translation-benchmark-runs/translation-pilot-v1 --candidate local-nllb
.venv/bin/python -m moin_translation_benchmark run \
  --workspace translation-benchmark-runs/translation-pilot-v1 --candidate google-cloud-nmt
.venv/bin/python -m moin_translation_benchmark review-package \
  --workspace translation-benchmark-runs/translation-pilot-v1 \
  --out /tmp/moin-translation-review
```

The immutable workspace lock records the candidate configurations; each run
records the candidate, corpus and frozen-text hashes, timestamp, per-language
output, source-character accounting, status, and timings. Each request gets an
intent record before being sent and an immutable result record afterward. A
completed run is reused without new requests. If a request fails, the runner
saves the failure and stops; failed outputs never enter the review export. If
the process dies with an intent but no result, the next run stops and asks the
operator to inspect provider usage before creating a fresh comparison
workspace. The runner never silently retries an uncertain billable request.
The review export contains Arabic and anonymous translations only. The private
workspace contains the identity map; share only `/tmp/moin-translation-review`
with the reviewers. Fill each `judgment` in `review.json` with
`faithful`, `partly_wrong`, or `serious_meaning_error`, plus an optional
comment. The result is a small pilot, not a broad accuracy claim. Review each
language independently and examine religious terminology and meaning errors.
The organizer's scientific reference document supplied by the project owner
also emphasizes preserving the meaning of Islamic terms in context, checking
Qur'an and hadith quotations and attribution, and avoiding overly literal
renderings that change religious meaning. Reviewers should annotate such
errors in this pilot. Its suggested terminology glossary is a useful source
for a later, separately measured glossary experiment; the current Google run
remains standard NMT.
After reviewers fill `review.json`, validate that every judgment uses the
allowed rubric and see English/French counts separately:

```sh
.venv/bin/python -m moin_translation_benchmark review-check \
  --file /tmp/moin-translation-review/review.json
```

No request is made during setup or tests. Validate locally with:

```sh
.venv/bin/python -m pytest -q tests/test_translation_benchmark.py
```
