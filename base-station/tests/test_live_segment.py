"""The live worker must apply the religious-content gate before DeepL/TTS."""
from pathlib import Path
import wave

from moin_studio.live_segment import LiveSegmentProcessor


def canonical_wav(_source: Path, destination: Path) -> None:
    with wave.open(str(destination), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b"\0\0" * 16000)


def test_live_text_is_published_before_speech(tmp_path, sample_renderings_path):
    source = tmp_path / "mic.webm"
    source.write_bytes(b"microphone")
    events = []
    def speak(text, language, destination):
        assert events[0][0] == "text"
        assert text == "A careful translation"
        assert language == "en"
        destination.write_bytes(b"mp3")
        return {"status": "created", "timing_ms": 11}
    worker = LiveSegmentProcessor(
        recognizer=lambda _: ("هذا درس في المسجد", 0.99),
        translator=lambda _arabic, _language: "A careful translation",
        speaker=speak,
        canonicalizer=canonical_wav,
        renderings_path=sample_renderings_path,
    )
    result = worker.process(source, "en", tmp_path / "out", lambda name, item: events.append((name, item)))
    assert [name for name, _ in events] == ["text", "audio"]
    assert result["translation"] == "A careful translation"
    assert result["audio_status"] == "ready"


def test_uncertain_asr_cannot_call_translation_or_speech(tmp_path, sample_renderings_path):
    source = tmp_path / "mic.webm"
    source.write_bytes(b"microphone")
    events = []
    worker = LiveSegmentProcessor(
        recognizer=lambda _: ("كلام غير مؤكد", 0.2),
        translator=lambda *_: (_ for _ in ()).throw(AssertionError("DeepL must not be called")),
        speaker=lambda *_: (_ for _ in ()).throw(AssertionError("TTS must not be called")),
        canonicalizer=canonical_wav,
        renderings_path=sample_renderings_path,
    )
    result = worker.process(source, "fr", tmp_path / "out", lambda name, item: events.append((name, item)))
    assert [name for name, _ in events] == ["text"]
    assert result["safety"] == "withheld"
    assert result["translation"] == ""


def test_quran_rendering_carries_publisher_attribution_without_deepl(tmp_path, sample_renderings_path):
    source = tmp_path / "mic.webm"
    source.write_bytes(b"microphone")
    worker = LiveSegmentProcessor(
        translator=lambda *_: (_ for _ in ()).throw(AssertionError("DeepL must not translate a matching verse")),
        speaker=lambda *_: {"status": "not_attempted"},
        canonicalizer=canonical_wav,
        renderings_path=sample_renderings_path,
    )
    arabic = worker.renderings["renderings"][0]["arabic"]
    worker.recognizer = lambda _: (arabic, 0.99)
    events = []
    result = worker.process(source, "en", tmp_path / "out", lambda phase, item: events.append((phase, item)))
    assert result["safety"] == "quran_rendering"
    assert result["translation"]
    assert result["sources"]["en"]["source"]
    assert result["sources"]["en"]["version"]
    assert events[0][0] == "text"
