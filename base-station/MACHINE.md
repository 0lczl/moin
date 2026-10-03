# Moin recorded-audio machine

`./machine` is an experimental, local, recorded-audio operator workflow. It is
not a live service and makes no quality or winner claim. It accepts local media,
canonicalizes it to mono 16 kHz PCM16 WAV with `ffmpeg`, then processes bounded
segments sequentially through one explicitly configured benchmark candidate.

```bash
./machine --audio recording.mp3 --config candidate.json --renderings official-renderings.json --out runs/2026-09-22
```

When the config is an array, select exactly one candidate:

```bash
./machine --audio recording.wav --config candidates.json --candidate local-qwen --renderings official-renderings.json --out runs/moin-1 --segment-seconds 30 --say
```

`--out` must not exist. A successful output contains `source.wav`, the Arabic,
English and French text files, `result.json`, and a self-contained `index.html`
with a local audio player. `result.json` records source and canonical hashes,
the full candidate config, runtime versions, trusted-rendering provenance,
per-segment offsets, results, and both safety decisions.

The CLI summary reports segment, failure, withheld, and translated counts. A
run with any candidate/provider failure keeps its evidence in `--out`, clears
any partial EN/FR text from the output artifacts, and exits with status `1`.
Treat such a run as failure-handling evidence, not successful inference.

Before machine translation, each Arabic segment is routed against the trusted
rendering registry. Exact Qur'anic matches use only approved renderings; near,
mixed, uncertain, empty, or registry-invalid text is withheld. Final routing is
also applied to every segment. With `--say`, only successful non-withheld EN/FR
text is sent to macOS `say`, as per-segment local audio files.

Segments are independent. A sentence or verse that crosses a boundary can lose
context, so inspect the timeline and safety provenance before relying on output.
The workflow creates no human labels or benchmark scores.

Run from `base-station` using the prepared environment:

```bash
HF_HUB_OFFLINE=1 .venv/bin/python -m moin_machine \
  --audio benchmark-data/staging/audio/oWj_w6LRuUY.wav \
  --config benchmark-data/local-comparison.json --candidate local-qwen \
  --renderings benchmark-data/staging-renderings/renderings.quranenc.json \
  --out machine-runs/my-recording --say
```

`benchmark-data/local-comparison.json` also contains the provisional
`local-translategemma` candidate, pinned to
`mlx-community/translategemma-4b-it-4bit@5788ec08c047f3f2e17808101b8d9566ac930d58`.
Select it with `--candidate local-translategemma` only after the weights are
available locally and have passed on-device inference checks. It uses the
Gemma Terms of Use; see [STUDIO.md](STUDIO.md#provisional-translategemma-candidate).
Neither the existing Qwen candidate nor TranslateGemma has earned a translation
winner claim.

Open the output `index.html` to listen and inspect. Qwen needs the Mac GPU;
restricted/headless environments without Metal cannot run this configuration.
The example configuration is provisional, not a human-reviewed winner.

For a completed YouTube recording, `tools/import_youtube.py URL --out NEW_DIR`
prepares `audio.wav` and sanitized provenance; then pass that audio to the
machine. It requires `yt-dlp` and `ffmpeg` (or an explicit `--yt-dlp` path).
Watch, Shorts, and short links are supported, including share parameters.
Live/upcoming videos are explicitly rejected. The importer is unit-tested;
a fresh network download has not yet been exercised in this implementation.
