"""Process one bounded microphone segment for a live room.

This module deliberately keeps the selected ASR, Qur'an safety gate, DeepL,
and ElevenLabs behind a small worker interface. The caller publishes text
before speech is synthesized, so listeners never wait for TTS to read it.
"""
from __future__ import annotations

from pathlib import Path
import os
import time
import wave
from typing import Any, Callable

from moin_benchmark import adapters
from moin_machine import tts
from moin_machine.machine import (
    MachineError,
    _final_safety,
    _pre_translation_guard,
    canonicalize,
    load_candidate,
    load_renderings,
)


BASE = Path(__file__).resolve().parents[1]
MAX_SEGMENT_SECONDS = 12
MIN_SEGMENT_SECONDS = 0.2


class LiveSegmentProcessor:
    """One worker's reusable model and safety configuration.

    `recognize`, `translate`, and `speak` are injectable for controlled tests
    and for a future remote ASR worker. Production uses the approved pinned
    Whisper large-v3 model and the existing provider adapters.
    """

    def __init__(
        self,
        *,
        config_path: Path = BASE / "benchmark-data/local-comparison.json",
        renderings_path: Path = BASE / "benchmark-data/staging-renderings/renderings.quranenc.json",
        recognizer: Callable[[Path], tuple[str, float | None]] | None = None,
        translator: Callable[[str, str], str] | None = None,
        speaker: Callable[[str, str, Path], dict[str, Any]] | None = None,
        canonicalizer: Callable[[Path, Path], None] = canonicalize,
    ):
        self.config = load_candidate(config_path, "deepl-v1")
        self.renderings = load_renderings(renderings_path)
        self.recognizer = recognizer or self._recognize
        self.translator = translator or self._translate
        self.speaker = speaker or tts.synthesize
        self.canonicalizer = canonicalizer

    def _recognize(self, path: Path) -> tuple[str, float | None]:
        if os.environ.get("MOIN_LIVE_ASR", "local") == "groq":
            from moin_studio.groq_asr import transcribe
            response = transcribe(path)
            return response["text"], None
        model = adapters._load_deepl_asr(self.config)
        settings = self.config["asr"]
        pieces, info = model.transcribe(
            str(path), language="ar", beam_size=settings.get("beam_size", 5),
            vad_filter=settings.get("vad_filter", False),
        )
        return " ".join(piece.text for piece in pieces).strip(), getattr(info, "language_probability", None)

    def _translate(self, arabic: str, language: str) -> str:
        return adapters._deepl_translation(self.config, arabic, language)

    def process(
        self,
        source: Path,
        language: str,
        output: Path,
        on_update: Callable[[str, dict[str, Any]], None],
    ) -> dict[str, Any]:
        if language not in {"en", "fr"}:
            raise ValueError("Unsupported live language")
        if not source.is_file() or not source.stat().st_size:
            raise MachineError("The microphone segment is empty")
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
        canonical = output / "source.wav"
        timings: dict[str, float] = {}
        started = time.perf_counter()
        self.canonicalizer(source, canonical)
        with wave.open(str(canonical), "rb") as stream:
            duration = stream.getnframes() / stream.getframerate()
        if not MIN_SEGMENT_SECONDS <= duration <= MAX_SEGMENT_SECONDS:
            raise MachineError("Microphone segments must be between 0.2 and 12 seconds")
        timings["canonicalize"] = round((time.perf_counter() - started) * 1000, 3)

        started = time.perf_counter()
        arabic, confidence = self.recognizer(canonical)
        arabic = arabic.strip()
        timings["asr"] = round((time.perf_counter() - started) * 1000, 3)
        if not arabic:
            raise MachineError("No Arabic speech was recognized in this segment")
        uncertainty = "low_asr_language_confidence" if confidence is not None and confidence < 0.8 else None
        result = {"arabic": arabic, "en": "", "fr": "", "uncertainty": uncertainty, "failure": None}

        started = time.perf_counter()
        guard = _pre_translation_guard(self.renderings)
        guarded = guard(arabic) if uncertainty is None else {"uncertainty": uncertainty}
        timings["safety"] = round((time.perf_counter() - started) * 1000, 3)
        if guarded and guarded.get("uncertainty"):
            result["uncertainty"] = guarded["uncertainty"]
        elif guarded and guarded.get(language):
            result[language] = guarded[language]
        elif guarded is None:
            started = time.perf_counter()
            result[language] = self.translator(arabic, language).strip()
            timings["translation"] = round((time.perf_counter() - started) * 1000, 3)

        decision = _final_safety(result, self.renderings, guard.decision)
        text = {
            "arabic": arabic,
            "translation": result[language],
            "language": language,
            "safety": decision["outcome"],
            "timing_ms": dict(timings),
            "audio_status": "pending" if result[language] else "unavailable",
        }
        if decision["outcome"] == "quran_rendering":
            text["sources"] = decision["sources"]
        on_update("text", text)
        if not result[language]:
            return text

        filename = f"speech-{language}.mp3"
        speech = self.speaker(result[language], language, output / filename)
        final = dict(text)
        final["audio_status"] = "ready" if speech.get("status") == "created" else "unavailable"
        if final["audio_status"] == "ready":
            final["audio_file"] = filename
        final["timing_ms"] = {**timings, "speech": speech.get("timing_ms", 0)}
        on_update("audio", final)
        return final
