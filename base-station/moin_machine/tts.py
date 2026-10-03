"""ElevenLabs speech synthesis for the selected Moin voices.

Credentials are read only from the local process environment. Voice identifiers
are public configuration, so runs can record them without exposing a secret.
"""
from __future__ import annotations

import json
import os
import ssl
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi
from moin_studio.budget import BudgetExceeded, reserve_if_configured


ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"
MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"
VOICES = {
    "en": "Q2DodP8VbBgCc0KBzBTw",  # Moin-English, selected by the project owner.
    "fr": "O2TxFmt2yYpiOSygumnt",  # Moin-French, selected by the project owner.
}


def configuration() -> dict[str, Any]:
    """Return the non-secret synthesis identity saved with each result."""
    return {
        "provider": "elevenlabs",
        "model": MODEL_ID,
        "output_format": OUTPUT_FORMAT,
        "voices": dict(VOICES),
        "credential_env": "ELEVENLABS_API_KEY",
    }


def _failure(code: str, message: str) -> dict[str, str]:
    return {"status": "failed", "provider": "elevenlabs", "code": code, "message": message}


def synthesize(text: str, language: str, destination: Path, *, opener=urlopen) -> dict[str, Any]:
    """Create one MP3 or return a safe, operator-actionable status."""
    started = time.perf_counter()

    def timed(value: dict[str, Any]) -> dict[str, Any]:
        value["timing_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return value

    if not text:
        return timed({"status": "not_attempted_empty_text", "provider": "elevenlabs"})
    voice_id = VOICES.get(language)
    if voice_id is None:
        return timed(_failure("unsupported_language", "ElevenLabs is configured only for English and French playback."))
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return timed({
            "status": "not_configured", "provider": "elevenlabs", "code": "missing_api_key",
            "message": "ElevenLabs is not configured. Add ELEVENLABS_API_KEY in the Studio terminal and run the recording again.",
        })
    try:
        reserve_if_configured('tts_chars', len(text))
    except BudgetExceeded:
        return timed(_failure('budget_exhausted', 'The pilot speech allowance is exhausted. Text remains available.'))
    payload = json.dumps({"text": text, "model_id": MODEL_ID}, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{ELEVENLABS_API}/{voice_id}?output_format={OUTPUT_FORMAT}", data=payload,
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"}, method="POST",
    )
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with opener(request, timeout=60, context=context) as response:
            audio = response.read()
    except HTTPError as error:
        if error.code in (401, 403):
            return timed(_failure("credential_rejected", "ElevenLabs did not accept this API key. Check that it is active."))
        if error.code == 429:
            return timed(_failure("rate_limited", "ElevenLabs is temporarily rate-limiting speech generation. Try again shortly."))
        if error.code in (402, 422):
            return timed(_failure("quota_or_request_rejected", "ElevenLabs could not generate this speech. Check available credits and the selected voice."))
        return timed(_failure("provider_unavailable", "ElevenLabs could not generate speech right now. Try again shortly."))
    except (URLError, OSError, ssl.SSLError):
        return timed(_failure("provider_unavailable", "ElevenLabs could not be reached. Check the network and try again."))
    if not audio:
        return timed(_failure("provider_unavailable", "ElevenLabs returned no audio for this segment."))
    try:
        destination.write_bytes(audio)
    except OSError:
        return timed(_failure("local_write_failed", "Moin could not save the generated speech on this Mac."))
    return timed({
        "status": "created", "provider": "elevenlabs", "model": MODEL_ID,
        "voice_id": voice_id, "file": destination.name,
    })
