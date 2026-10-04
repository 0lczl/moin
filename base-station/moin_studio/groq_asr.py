"""Optional Groq speech-to-text adapter pinned to Whisper large-v3.

The module has no third-party runtime dependency. It sends one bounded WAV file
to Groq's OpenAI-compatible transcription endpoint and deliberately excludes
provider response bodies from all raised errors.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import math
import os
from pathlib import Path
import socket
import time
import wave
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid
from moin_studio.budget import BudgetExceeded, reserve_if_configured


MODEL_ID = "whisper-large-v3"
API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
KEY_ENV = "GROQ_API_KEY"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MIN_BILLED_SECONDS = 10.0
PRICE_PER_AUDIO_HOUR_USD = 0.111
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class AudioInfo:
    duration_seconds: float
    byte_count: int


class GroqASRError(RuntimeError):
    """A provider failure containing only safe, non-payload details."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def as_dict(self) -> dict[str, str | bool]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def minimum_billable_seconds(duration_seconds: float) -> float:
    """Return the documented minimum-billed duration for one API request.

    Groq bills a minimum of ten seconds per request. This helper models that
    floor; it does not include retries, currency conversion, or future price
    changes.
    """
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float)):
        raise ValueError("duration_seconds must be a finite non-negative number")
    if not math.isfinite(duration_seconds) or duration_seconds < 0:
        raise ValueError("duration_seconds must be a finite non-negative number")
    return max(MIN_BILLED_SECONDS, float(duration_seconds))


def estimate_cost_usd(duration_seconds: float) -> float:
    """Estimate current Whisper large-v3 cost for a single request."""
    return minimum_billable_seconds(duration_seconds) / 3600 * PRICE_PER_AUDIO_HOUR_USD


def inspect_wav(path: Path) -> AudioInfo:
    """Validate a regular, bounded WAV and return its duration without decoding."""
    path = Path(path)
    try:
        if not path.is_file():
            raise GroqASRError("invalid_audio", "Choose an existing WAV recording.")
        size = path.stat().st_size
        if size <= 0:
            raise GroqASRError("invalid_audio", "The WAV recording is empty.")
        if size > MAX_UPLOAD_BYTES:
            raise GroqASRError("audio_too_large", "The WAV recording exceeds the 25 MB upload limit.")
        data = path.read_bytes()
        if not data or len(data) > MAX_UPLOAD_BYTES:
            raise GroqASRError("audio_too_large", "The WAV recording exceeds the 25 MB upload limit.")
        with wave.open(io.BytesIO(data), "rb") as wav:
            if wav.getnframes() <= 0 or wav.getframerate() <= 0:
                raise GroqASRError("invalid_audio", "The WAV recording contains no audio frames.")
            duration = wav.getnframes() / wav.getframerate()
        if not math.isfinite(duration) or duration <= 0:
            raise GroqASRError("invalid_audio", "The WAV recording has an invalid duration.")
        return AudioInfo(duration_seconds=duration, byte_count=len(data))
    except GroqASRError:
        raise
    except (OSError, wave.Error, EOFError):
        raise GroqASRError("invalid_audio", "The recording is not a readable WAV file.") from None


def _multipart(audio: bytes, boundary: str) -> bytes:
    """Build the small multipart request using fixed, non-user-controlled fields."""
    marker = boundary.encode("ascii")
    parts = []
    fields = (
        ("model", MODEL_ID),
        ("language", "ar"),
        ("response_format", "verbose_json"),
        ("temperature", "0"),
    )
    for name, value in fields:
        parts.extend((b"--" + marker + b"\r\n",
                      f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                      value.encode("ascii") + b"\r\n"))
    parts.extend((b"--" + marker + b"\r\n",
                  b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n',
                  b"Content-Type: audio/wav\r\n\r\n", audio, b"\r\n",
                  b"--" + marker + b"--\r\n"))
    return b"".join(parts)


def transcribe(
    audio_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    opener=None,
) -> dict:
    """Transcribe an Arabic WAV with exact Whisper large-v3.

    The key is read only from ``GROQ_API_KEY``. ``opener`` is a test seam and
    should not be supplied by production callers.
    """
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive finite number")
    info = inspect_wav(Path(audio_path))
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise GroqASRError("missing_credentials", "Groq ASR is not configured.")
    try:
        reserve_if_configured('asr_billable_seconds', math.ceil(minimum_billable_seconds(info.duration_seconds)))
    except BudgetExceeded:
        raise GroqASRError('budget_exhausted', 'The pilot ASR allowance is exhausted.') from None

    try:
        audio = Path(audio_path).read_bytes()
    except OSError:
        raise GroqASRError("invalid_audio", "The WAV recording could not be read.") from None
    if not audio or len(audio) > MAX_UPLOAD_BYTES:
        raise GroqASRError("audio_too_large", "The WAV recording exceeds the 25 MB upload limit.")

    boundary = "moin-" + uuid.uuid4().hex
    request = Request(
        API_URL,
        data=_multipart(audio, boundary),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "Moin/1.0 (+https://github.com/0lczl/moin)",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        open_url = opener or urlopen
        with open_url(request, timeout=float(timeout_seconds)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 401:
            raise GroqASRError("credential_rejected", "Groq did not accept the API key.") from None
        if error.code == 403:
            if error.read(128).startswith(b"error code: 1010"):
                raise GroqASRError("network_blocked", "Cloudflare blocked the request to Groq.") from None
            raise GroqASRError("access_denied", "Groq denied access to this ASR model or project.") from None
        if error.code == 413:
            raise GroqASRError("audio_too_large", "Groq rejected the WAV upload size.") from None
        if error.code == 429:
            raise GroqASRError("rate_limited", "Groq is rate-limiting ASR requests.", retryable=True) from None
        raise GroqASRError(
            "provider_unavailable" if error.code >= 500 else "provider_rejected",
            "Groq could not complete this ASR request.", retryable=error.code >= 500,
        ) from None
    except (TimeoutError, socket.timeout):
        raise GroqASRError("timeout", "Groq ASR request timed out.", retryable=True) from None
    except URLError:
        raise GroqASRError("network_error", "Groq ASR could not be reached.", retryable=True) from None
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError):
        raise GroqASRError("invalid_response", "Groq returned an unreadable ASR response.", retryable=True) from None
    except OSError:
        raise GroqASRError("network_error", "Groq ASR could not be reached.", retryable=True) from None

    transcript = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(transcript, str):
        raise GroqASRError("invalid_response", "Groq returned an incomplete ASR response.", retryable=True)
    return {
        "status": "ok",
        "model": MODEL_ID,
        "text": transcript.strip(),
        "duration_seconds": info.duration_seconds,
        "billable_seconds_estimate": minimum_billable_seconds(info.duration_seconds),
        "cost_usd_estimate": round(estimate_cost_usd(info.duration_seconds), 8),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
