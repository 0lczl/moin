import json
from pathlib import Path

from moin_machine import tts


def test_elevenlabs_requires_a_local_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    result = tts.synthesize("Hello", "en", tmp_path / "speech.mp3")
    assert result["status"] == "not_configured"
    assert not (tmp_path / "speech.mp3").exists()


def test_elevenlabs_uses_selected_voice_and_never_puts_key_in_body(monkeypatch, tmp_path):
    seen = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self): return b"ID3generated-mp3"

    def opener(request, timeout, **kwargs):
        seen.append((request, timeout, kwargs))
        return Response()

    monkeypatch.setenv("ELEVENLABS_API_KEY", "secret-key")
    output = tmp_path / "speech.mp3"
    result = tts.synthesize("Peace be upon you", "en", output, opener=opener)
    assert {key: result[key] for key in ("status", "provider", "model", "voice_id", "file")} == {"status": "created", "provider": "elevenlabs", "model": "eleven_multilingual_v2", "voice_id": "Q2DodP8VbBgCc0KBzBTw", "file": "speech.mp3"}
    assert result["timing_ms"] >= 0
    request, timeout, kwargs = seen[0]
    assert request.full_url == "https://api.elevenlabs.io/v1/text-to-speech/Q2DodP8VbBgCc0KBzBTw?output_format=mp3_44100_128"
    assert timeout == 60 and "context" in kwargs
    assert request.headers["Xi-api-key"] == "secret-key"
    assert json.loads(request.data) == {"text": "Peace be upon you", "model_id": "eleven_multilingual_v2"}
    assert b"secret-key" not in request.data
    assert output.read_bytes() == b"ID3generated-mp3"


def test_elevenlabs_records_french_voice_identity():
    config = tts.configuration()
    assert config["voices"]["fr"] == "O2TxFmt2yYpiOSygumnt"
    assert config["credential_env"] == "ELEVENLABS_API_KEY"
    assert "secret-key" not in json.dumps(config)
