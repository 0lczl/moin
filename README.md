# Moin

Moin is a quality-first workflow for Arabic religious speech: it evaluates
candidate transcription and translation configurations, processes recorded
audio or video, and lets listeners review Arabic text, English and French
meanings, safety decisions, and generated playback. A three-page hosted pilot
has been prepared but has not yet been deployed or latency-tested.

This repository contains source code, design assets, specs, and documented
evaluation summaries. It excludes provider keys, source audio, raw human-review
exports, generated media, model weights, and the locally assembled Qur'an
rendering registry. Read [repository contents and reproducibility](docs/repository.md)
before using a clean checkout.

## Included

- `base-station/moin_benchmark/` — reproducible candidate comparison and blind
  meaning-review tools.
- `base-station/moin_machine/` — bounded recorded-media processing.
- `base-station/moin_studio/` — local review interface and restricted public-pilot server, including the Live Translator.
- `base-station/moin_haramain/` — curated Haramain video catalog and source validation.
- `base-station/moin_translation_benchmark/` — text-only translation pilot.
- `.specs/` — product and model-selection decisions.
- `presentation/` and `brand/presentation/` — current presentation assets and
  visual identity.

## Start locally

From `base-station/`, create the local environment and start Studio:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m moin_studio
```

Then open <http://127.0.0.1:8787>. The application is local and experimental.
Processing requires the separately assembled trusted rendering registry
described in [the source research](base-station/benchmark-data/rendering-research.md)
and the chosen provider credentials; without them, processing fails closed.
Benchmark output is not a claim that a model has won human meaning review.
The [Haramain Video Center](base-station/HARAMAIN-CENTER.md) is available at
<http://127.0.0.1:8787/haramain>, and the Live Translator at
<http://127.0.0.1:8787/live>, while Studio is running.

The hosted pilot's [deployment runbook](deploy/README.md) explains the
explicit release bundle, HTTPS proxy, provider secrets, spending safeguards,
and remaining on-host verification. The public site is not live yet.
For a supervised hackathon demonstration without a rented server, see the
[temporary Mac and Cloudflare Tunnel guide](deploy/free-demo.md). The judge link
works only while the operator's Mac and tunnel are running.

See [the architecture note](docs/architecture.md) for the current local system,
its performance boundaries, and a staged path toward a hosted website.

## Test

```sh
cd base-station
.venv/bin/python -m pytest -q
```

The GitHub workflow uses the small hosted dependency set plus `pytest`. From a
clean checkout, two tests requiring the nine private source recordings are
explicitly skipped; all other tests use synthetic fixtures.
