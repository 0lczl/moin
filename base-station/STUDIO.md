# Moin Studio

A local website for recorded Arabic audio/video, transcription, English/French
translation, and generated speech. It uses the selected local ASR candidate,
Whisper large-v3, then calls DeepL API Free v2 for text translation and
ElevenLabs for speech. API keys never reach the web page or result files.

## Start

For the DeepL pipeline, open Terminal and run the following from
`base-station`. The first command accepts the key without displaying it or
putting it in shell history:

```bash
read -rs 'DEEPL_AUTH_KEY?Paste your DeepL API Free key, then press Return: '; echo
export DEEPL_AUTH_KEY
read -rs 'ELEVENLABS_API_KEY?Paste your ElevenLabs API key, then press Return: '; echo
export ELEVENLABS_API_KEY
.venv/bin/python -m moin_studio
```

Open http://127.0.0.1:8787. Keep the terminal open; Ctrl+C stops the server and
cancels active processing. The service listens only on this Mac. Run from a normal
macOS terminal with the approved Whisper large-v3 model available; the prepared
Python environment, trusted-rendering registry, and ffmpeg are also required.

The curated Haramain Video Center is at `http://127.0.0.1:8787/haramain`. It
uses the same queue and saved results; see [HARAMAIN-CENTER.md](HARAMAIN-CENTER.md)
for source management and the demo journey.

Studio keeps its serialized inference worker alive for the lifetime of the server.
The first recording loads the pinned Whisper large-v3 snapshot; later recordings
reuse that exact in-memory model instead of starting Python and loading Whisper
again. Restarting Studio intentionally makes the next recording a cold run.

The YouTube field also needs `yt-dlp`. It is listed in `requirements.txt`; if it
is absent, install the project requirements in the same virtual environment
before launching Studio.

`deepl-v1` is the default candidate. It sends only the Arabic transcript of each
non-withheld segment to DeepL API Free at `api-free.deepl.com`; the original audio
and the DeepL key remain on the Mac. A missing key produces a clear failure state
and no partial translation is displayed. Other configured local candidates remain
available only for development comparisons.

ElevenLabs receives the final English or French translation only; it never receives
the Arabic source audio. The selected voices are `Moin-English`
(`Q2DodP8VbBgCc0KBzBTw`) and `Moin-French` (`O2TxFmt2yYpiOSygumnt`). The source
audio is not used to copy or train a voice. A missing ElevenLabs key leaves speech
unavailable with an explicit message; Moin does not silently substitute macOS speech.
Independent English and French DeepL requests run concurrently after ASR and safety
checks. Their ElevenLabs requests also run concurrently, with separate text, voice,
and output files. Segments and ASR remain serialized to preserve the approved model
behavior and bounded context contract.

When a key is rejected by the API Free hostname, Studio automatically tries the
official API Pro hostname once. No plan setting or key disclosure is required.

## Use

1. Choose or drop a recording (up to 256 MB), or paste a public completed
   YouTube Watch, Shorts, or `youtu.be` link up to five minutes long. Live,
   upcoming, playlists, and other hosts are rejected.
2. Press **Process recording**. Upload progress is measured; processing shows
   elapsed time rather than an invented completion percentage.
3. Open **Read & listen** when ready. Switch between Arabic, English, and French.
   Use a timestamp to seek the original. Translated audio appears where generated.
4. Download text or the full result record. Uncertain/failed passages remain
   explicitly marked; they are not supplied with invented speech.

The sample recording is the existing clip-3 machine result. It is not a new
benchmark run. English is the human-reviewed DeepL direction for this development
sample. French output remains experimental until its independent Arabic–French
review is complete. Generated text is not verified religious advice.

## Storage and recovery

Uploads and job state live in ignored `studio-runs/`. Each job has its own input,
output directory, private machine log, and `diagnostics.jsonl` stage log. The stage
log records import, inference, and playback-preparation durations and safe error
types, without exception text or media contents. Only the output allowlist is served
by HTTP. Processing is serialized; at most four uploads/queued/active jobs are
accepted. Cancel a queued or active job in the page. Completed results survive
server restarts. Interrupted jobs are marked interrupted; upload again to retry.
The service does not silently rerun or replace a result.

Each job records milliseconds for queue wait, machine work, and total processing in
`job.json`. `output/result.json` records canonicalization, segmentation, processing,
artifact, and total timings. Each candidate segment records model loading, ASR,
English translation, French translation, and candidate total time; each generated
voice records its own provider time plus the pair's wall time. These timings make
cold-start, provider, and queue delays distinguishable without recording credentials.

EN/FR AIFF synthesis files are additionally converted to WAV for browser
playback. Original machine evidence remains unchanged. Failed synthesis leaves
text available with an unavailable-playback message.

The website imports completed YouTube recordings into its private local job
folder before processing. The separate `tools/import_youtube.py` importer is
also available when an operator wants to prepare a file from Terminal.

## Validation

The suite includes real loopback HTTP tests with controlled inference doubles:
upload → queue → result → audio byte-range playback; origin/token/host checks;
invalid input; private-file isolation; interrupted jobs; queue limits and cancel.
A real user-approved recording was uploaded through the browser for full local
model verification. See the verification note for the final observed outcome.

## Provisional TranslateGemma candidate

The candidate is `mlx-community/translategemma-4b-it-4bit` at revision
`5788ec08c047f3f2e17808101b8d9566ac930d58` (4-bit, about 2.18 GB of model
weights). It uses the Gemma Terms of Use, not an Apache or MIT license. Review
[Google's Gemma terms](https://ai.google.dev/gemma/terms) before distributing
the weights or offering them through a hosted service.

This is an integration candidate, not a quality decision. Before selecting it
in Studio, verify the pinned snapshot loads and produces EN/FR output on the
Mac's Metal-enabled runtime. Arabic→French in particular needs human review;
the official materials do not establish it as a specifically evaluated pair.
