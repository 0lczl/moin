#!/usr/bin/env python3
"""Disposable synthetic smoke test for the complete benchmark CLI workflow.

This makes no model or provider calls and produces no reusable evidence. Run it
from ``base-station`` with ``python tools/benchmark_smoke.py``.
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import tempfile
import wave
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


BASE_STATION = Path(__file__).resolve().parents[1]
if str(BASE_STATION) not in sys.path:
    sys.path.insert(0, str(BASE_STATION))

from moin_benchmark.__main__ import main  # noqa: E402


SYNTHETIC_NOTICE = "SYNTHETIC SMOKE TEST — NOT BENCHMARK EVIDENCE — NO QUALITY CLAIM"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _wav(path: Path, sample: int) -> bytes:
    frames = struct.pack("<160h", *([sample] * 160))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16_000)
        output.writeframes(frames)
    return path.read_bytes()


def _fixtures(root: Path) -> tuple[Path, Path, Path]:
    corpus = root / "corpus"
    audio = corpus / "audio"
    audio.mkdir(parents=True)
    clips = []
    tags = ["ordinary-teaching", "islamic-terminology", "natural-fast-speech", "quran-adjacent"]
    for index in range(32):
        split = "development" if index < 12 else "final"
        clip_id = f"synthetic-{split[:3]}-{index + 1:02}"
        relative = f"audio/{clip_id}.wav"
        payload = _wav(corpus / relative, index + 1)
        clips.append({
            "id": clip_id,
            "split": split,
            "audio": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "speaker": f"synthetic-speaker-{index % 3 + 1}",
            "source": {"uri": f"synthetic://smoke/{index}", "title": SYNTHETIC_NOTICE, "retrieved_at": "2026-01-01"},
            "source_start_seconds": 0,
            "duration_seconds": 0.01,
            "permission": {"decision": "permitted", "basis": "generated synthetic fixture", "reviewer": "smoke-script", "date": "2026-01-01"},
            "tags": [tags[index % len(tags)]],
            "transcript": {"state": "verified", "text": f"نص اصطناعي {index + 1}", "reviewer": "smoke-script", "date": "2026-01-01"},
        })
    _write_json(corpus / "corpus.json", clips)

    candidates = root / "synthetic-candidates.json"
    _write_json(candidates, [{
        "id": "synthetic-baseline",
        "name": SYNTHETIC_NOTICE,
        "adapter": "baseline",
        "asr": {"model": "synthetic/faster-whisper", "revision": "a" * 40, "device": "cpu", "compute_type": "int8", "beam_size": 1, "vad_filter": False},
        "translation": {"model": "synthetic/nllb", "revision": "b" * 40, "source_lang": "arb_Arab", "max_new_tokens": 32, "num_beams": 1},
        "settings": {"timeout_seconds": 1},
        "prompts": {"en": "", "fr": ""},
    }])

    renderings = root / "synthetic-renderings.json"
    _write_json(renderings, {
        "schema_version": 1,
        "detection_ready": True,
        "renderings": [{
            "arabic": "الحمد لله رب العالمين",
            "english": {"text": "Synthetic trusted English", "source": SYNTHETIC_NOTICE, "version": "synthetic-1", "approved": True},
            "french": {"text": "Français fiable synthétique", "source": SYNTHETIC_NOTICE, "version": "synthetic-1", "approved": True},
        }],
    })
    return corpus, candidates, renderings


def _command(corpus: Path, workspace: Path, *args: str) -> dict:
    stdout, stderr = io.StringIO(), io.StringIO()
    argv = ["--corpus", str(corpus), "--workspace", str(workspace), *args]
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main(argv)
    if status:
        raise RuntimeError(f"command failed ({' '.join(args)}): {stderr.getvalue().strip()}")
    return json.loads(stdout.getvalue())


def _complete_review(path: Path, *, final: bool = False) -> None:
    review = json.loads(path.read_text())
    french_seen = 0
    for item in review["items"]:
        if final and item["language"] == "fr":
            french_seen += 1
            item["label"] = "faithful" if french_seen <= 17 else "partly_wrong"
        else:
            item["label"] = "faithful"
        item["comment"] = SYNTHETIC_NOTICE
    _write_json(path, review)


def _synthetic_process(config: dict, audio_path: Path, *, translation_guard=None) -> dict:
    arabic = "شرح اصطناعي عادي"
    decision = translation_guard(arabic) if translation_guard else None
    result = {
        "arabic": arabic,
        "en": "Synthetic English output",
        "fr": "Sortie française synthétique",
        "timing_ms": {"asr": 1, "en": 1, "fr": 1, "total": 3},
        "uncertainty": None,
        "failure": None,
    }
    if decision is not None:
        result.update(en=decision.get("en") or "", fr=decision.get("fr") or "", uncertainty=decision.get("uncertainty"))
    return result


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="moin-synthetic-smoke-") as temporary:
        root = Path(temporary)
        corpus, candidates, renderings = _fixtures(root)
        workspace = root / "private-workspace"
        development_review = root / "development-review"
        final_review = root / "final-review"

        with patch("moin_benchmark.adapters.process", _synthetic_process):
            _command(corpus, workspace, "corpus", "validate", "--split", "development")
            _command(corpus, workspace, "candidates", "lock", "--file", str(candidates))
            _command(corpus, workspace, "run", "--split", "development", "--candidate", "synthetic-baseline")
            _command(corpus, workspace, "review-package", "create", "--split", "development", "--out", str(development_review))
            _complete_review(development_review / "review.json")
            _command(corpus, workspace, "review", "submit", "--split", "development", "--file", str(development_review / "review.json"), "--reviewer", "synthetic-reviewer")
            _command(corpus, workspace, "report", "development")
            _command(corpus, workspace, "composition", "select", "--candidate", "synthetic-baseline", "--renderings", str(renderings))
            _command(corpus, workspace, "run", "--split", "development", "--candidate", "moin")
            _command(corpus, workspace, "composition", "freeze", "--candidate", "moin")
            _command(corpus, workspace, "run", "--split", "final", "--candidate", "moin")
            _command(corpus, workspace, "review-package", "create", "--split", "final", "--out", str(final_review))
            _complete_review(final_review / "review.json", final=True)
            _command(corpus, workspace, "review", "submit", "--split", "final", "--file", str(final_review / "review.json"), "--reviewer", "synthetic-reviewer")
            report = _command(corpus, workspace, "report", "final")

        languages = report["candidates"][0]["languages"]
        assert languages["en"]["faithful"] == 20
        assert languages["fr"]["faithful"] == 17
        assert report["quality_claim_90_percent"] is False
        return {
            "marker": SYNTHETIC_NOTICE,
            "workflow": "complete",
            "temporary_artifacts_deleted": True,
            "final": {"en_faithful": "20/20", "fr_faithful": "17/20", "quality_claim_90_percent": False},
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
