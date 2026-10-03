import io
import json
from pathlib import Path
import wave
from urllib.error import HTTPError

import pytest

from moin_studio import groq_asr


def wav_bytes(seconds=0.5):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * int(16000 * seconds))
    return stream.getvalue()


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_uploads_wav_to_exact_large_v3_and_parses_safe_metrics(tmp_path, monkeypatch):
    audio_path = tmp_path / "segment.wav"
    audio_path.write_bytes(wav_bytes(3))
    monkeypatch.setenv("GROQ_API_KEY", "test-key-never-logged")
    captured = {}

    def opener(request, *, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(json.dumps({"text": "  الحمد لله  "}).encode())

    result = groq_asr.transcribe(audio_path, timeout_seconds=7, opener=opener)
    request = captured["request"]
    body = request.data
    assert request.full_url == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert request.get_header("Authorization") == "Bearer test-key-never-logged"
    assert captured["timeout"] == 7.0
    assert b'name="model"\r\n\r\nwhisper-large-v3\r\n' in body
    assert b"whisper-large-v3-turbo" not in body
    assert b'name="language"\r\n\r\nar\r\n' in body
    assert b'name="response_format"\r\n\r\nverbose_json\r\n' in body
    assert wav_bytes(3) in body
    assert result["model"] == "whisper-large-v3"
    assert result["text"] == "الحمد لله"
    assert result["duration_seconds"] == 3
    assert result["billable_seconds_estimate"] == 10
    assert result["cost_usd_estimate"] == round(10 / 3600 * 0.111, 8)


def test_credential_is_env_only_and_missing_key_fails_without_request(tmp_path, monkeypatch):
    audio_path = tmp_path / "segment.wav"
    audio_path.write_bytes(wav_bytes())
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(groq_asr.GroqASRError) as exc:
        groq_asr.transcribe(audio_path, opener=lambda *_args, **_kwargs: pytest.fail("network seam called"))
    assert exc.value.code == "missing_credentials"
    assert "GROQ_API_KEY" not in str(exc.value)


def test_http_error_does_not_leak_provider_body_key_or_audio(tmp_path, monkeypatch):
    audio_path = tmp_path / "segment.wav"
    audio_path.write_bytes(wav_bytes())
    key = "very-secret-key"
    monkeypatch.setenv("GROQ_API_KEY", key)

    def opener(*_args, **_kwargs):
        raise HTTPError(groq_asr.API_URL, 401, "rejected", {}, io.BytesIO(f"{key} source-audio".encode()))

    with pytest.raises(groq_asr.GroqASRError) as exc:
        groq_asr.transcribe(audio_path, opener=opener)
    assert exc.value.code == "credential_rejected"
    assert key not in str(exc.value)
    assert "source-audio" not in str(exc.value)


def test_rejects_non_wav_empty_and_oversized_before_api(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    non_wav = tmp_path / "audio.mp3"
    non_wav.write_bytes(b"not a wav")
    with pytest.raises(groq_asr.GroqASRError) as invalid:
        groq_asr.transcribe(non_wav, opener=lambda *_args, **_kwargs: pytest.fail("network seam called"))
    assert invalid.value.code == "invalid_audio"

    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    with pytest.raises(groq_asr.GroqASRError) as empty_error:
        groq_asr.transcribe(empty, opener=lambda *_args, **_kwargs: pytest.fail("network seam called"))
    assert empty_error.value.code == "invalid_audio"

    oversized = tmp_path / "large.wav"
    oversized.write_bytes(b"0" * (groq_asr.MAX_UPLOAD_BYTES + 1))
    with pytest.raises(groq_asr.GroqASRError) as size_error:
        groq_asr.transcribe(oversized, opener=lambda *_args, **_kwargs: pytest.fail("network seam called"))
    assert size_error.value.code == "audio_too_large"


def test_minimum_billing_helper_validates_duration():
    assert groq_asr.minimum_billable_seconds(3.2) == 10
    assert groq_asr.minimum_billable_seconds(12) == 12
    for bad in (-1, float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            groq_asr.minimum_billable_seconds(bad)
