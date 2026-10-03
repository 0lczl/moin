"""Audio-only ASR adapters. Reference text must never cross this boundary."""
from __future__ import annotations

import platform
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


_CACHE = {}
_RUNTIME_FILES = ["model.bin", "config.json", "tokenizer.json", "vocabulary.*", "preprocessor_config.json"]


def runtime_identity() -> dict:
    packages = {}
    for package in ("faster-whisper", "ctranslate2", "huggingface-hub", "numpy"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": packages}


def _load(config: dict):
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download

    model = config["model"]
    key = (model["repository"], model["revision"], config["runtime"]["device"], config["runtime"]["compute_type"])
    if key not in _CACHE:
        path = snapshot_download(repo_id=model["repository"], revision=model["revision"], allow_patterns=_RUNTIME_FILES)
        _CACHE[key] = WhisperModel(path, device=config["runtime"]["device"], compute_type=config["runtime"]["compute_type"])
    return _CACHE[key]


def transcribe(audio_path: Path, config: dict) -> dict:
    """Transcribe one path. Signature deliberately has no reference argument."""
    setup_started = time.perf_counter()
    model = _load(config)
    setup_ms = round((time.perf_counter() - setup_started) * 1000, 3)
    started = time.perf_counter()
    settings = config["settings"]
    segments, info = model.transcribe(
        str(audio_path),
        language=settings["language"],
        task=settings["task"],
        beam_size=settings["beam_size"],
        temperature=settings["temperature"],
        vad_filter=settings["vad_filter"],
        condition_on_previous_text=settings["condition_on_previous_text"],
    )
    segments = list(segments)
    return {
        "status": "ok",
        "raw_hypothesis": " ".join(segment.text for segment in segments).strip(),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "setup_ms": setup_ms,
        "model_metadata": {
            "detected_language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
            "segment_count": len(segments),
        },
        "failure": None,
    }
