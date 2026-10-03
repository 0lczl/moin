# Moin quality-first translation workflow

This directory contains the current Moin submission: a controlled Arabic
speech/translation benchmark, a bounded recorded-media processor, and a local
Studio for reviewing recordings, transcripts, translations, and playback.

## What is here

- [BENCHMARK.md](BENCHMARK.md) — reproducible candidate comparison and blind
  meaning-review workflow.
- [MACHINE.md](MACHINE.md) — bounded local processing for a recorded audio or
  video file.
- [STUDIO.md](STUDIO.md) — local browser interface for uploads and review.
- [TRANSLATION-BENCHMARK.md](TRANSLATION-BENCHMARK.md) — text-only translation
  candidate pilot.

Run the commands from this directory with Python 3.11 or later. The practical
entry point for the human-reviewed English translation pipeline is Moin Studio
with a local DeepL API Free key:

```sh
read -rs 'DEEPL_AUTH_KEY?Paste your DeepL API Free key, then press Return: '; echo
export DEEPL_AUTH_KEY
read -rs 'ELEVENLABS_API_KEY?Paste your ElevenLabs API key, then press Return: '; echo
export ELEVENLABS_API_KEY
.venv/bin/python -m moin_studio
```

The interface listens only on `127.0.0.1`. It transcribes locally with Whisper
large-v3 and sends only Arabic text to DeepL for English/French translation.
It accepts local media and completed public YouTube links up to five minutes.
Keep Studio running between recordings: its serialized worker retains the pinned
Whisper model in memory after the first cold load. Independent English/French
translation and speech requests overlap, and the saved job/result records expose
queue, model-load, ASR, translation, and speech timings for performance review.
See [STUDIO.md](STUDIO.md) for the exact privacy boundary and pilot steps.

## Verification

```sh
.venv/bin/python -m pytest -q
```
