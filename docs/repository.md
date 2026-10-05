# Repository guide

This is the reviewable source for Moin's experimental three-page pilot. The
Python service owns the API and background workers; the HTML, CSS, and JavaScript
pages in `base-station/moin_studio/static/` are served by it. See
[architecture.md](architecture.md) for the request and processing flow and
[deploy/README.md](../deploy/README.md) for the prepared hosted pilot.

## What is public source

| Path | Purpose |
| --- | --- |
| `base-station/moin_studio/` | HTTP routes, recording and live-room workers, access controls, budget ledger, and three page assets |
| `base-station/moin_machine/` | Recorded-media pipeline and speech synthesis |
| `base-station/moin_benchmark/`, `moin_asr_benchmark/`, `moin_translation_benchmark/` | Benchmark code and safety routing |
| `base-station/benchmark-data/`, `asr-benchmark-data/` | Public protocol, example configuration, corpus metadata, and source research |
| `base-station/tests/` | Unit and route tests, with synthetic rendering data for clean-checkout tests |
| `.specs/`, `PROJECT-LOG.md` | Product decisions, protocol, aggregate evidence, and limitations |
| `brand/`, `presentation/` | Current identity and judge presentation assets |
| `docs/scientific-sources/` | Challenge reference PDF, QuranEnc source selection, integrity metadata, and Arabic slide copy |

Local recordings, model downloads, user jobs, raw benchmark runs, blind review
exports, and API keys are Git-ignored. They
remain in the operator workspace and are **not deleted** by this cleanup. The
aggregate ASR and English-review findings are recorded in `PROJECT-LOG.md`;
the underlying private files can be inspected locally by the project owner.
The attributed QuranEnc registry is tracked in Git as the explicit exception
for published rendering data. Its notice is in [QURANENC_NOTICE.md](../QURANENC_NOTICE.md);
the [scientific source pack](scientific-sources/README.md) links it to the
challenge reference. Publisher attribution, versions, notes, and update
obligations still apply. Its exact inputs and assembly method are described in
`base-station/benchmark-data/rendering-research.md` and
`base-station/tools/prepare_renderings.py`.

## Verify a clean checkout

Use Python 3.12. These checks do not call paid providers or download model
weights:

```sh
cd base-station
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-hosted.txt pytest
.venv/bin/python -m pytest -q
```

Two ASR integration tests skip when the private nine-clip audio corpus is not
present. A complete local run executes them. Synthetic renderings keep all
other tests independent of the full trusted registry. Full recording
processing and public deployment require the bundled registry and server-side
provider credentials; the server fails closed when
they are missing.

The prepared deployment bundle includes the registry when built on the
operator's machine with `python3 tools/package_hosted.py --out ...`. Do not
upload that bundle or `.env` to a public repository. A clean clone includes
the published registry; provider credentials and model dependencies still need
to be configured before running the complete translation pipeline.

## Review boundaries

The public pilot is not deployed. Its less-than-ten-second live translation
target, 50-listener capacity, and provider spending have not been validated on
a host. The nine-clip ASR comparison and English translation review are small
development evaluations, not universal accuracy percentages. French human
translation review is still pending. See `PROJECT-LOG.md` for the exact scope.

No open-source license has been selected for this repository. Showing source to
judges does not grant reuse permission; the project owner can choose a license
later without changing the technical release.
