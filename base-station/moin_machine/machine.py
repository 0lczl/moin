"""Bounded, file-based processing for recorded Moin audio.

This is intentionally an operator tool, not a live service or a quality claim.
It processes sequential canonical WAV segments so a long recording cannot cause
unbounded model work or hide the context lost at segment boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import subprocess
import sys
import tempfile
import wave
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from moin_benchmark import adapters, safety
from moin_benchmark.core import BenchmarkError, secret_free
from moin_machine import tts


class MachineError(ValueError):
    """A safe, operator-actionable error."""


class MachineCancelled(RuntimeError):
    """Raised between bounded stages when the Studio cancels a local run."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MachineError(f"Cannot read valid JSON: {path.name}") from exc


def load_candidate(path: Path, candidate_id: str | None) -> dict[str, Any]:
    value = _read_json(path)
    candidates = value if isinstance(value, list) else [value]
    if not candidates or not all(isinstance(item, dict) for item in candidates):
        raise MachineError("Config must be one candidate object or an array of candidate objects")
    if candidate_id is None:
        if len(candidates) != 1:
            raise MachineError("Config contains multiple candidates; pass --candidate")
        selected = candidates[0]
    else:
        selected = next((item for item in candidates if item.get("id") == candidate_id), None)
        if selected is None:
            raise MachineError("Requested candidate is not in --config")
    try:
        secret_free(selected)
        adapters.validate_config(selected)
    except (BenchmarkError, ValueError, TypeError) as exc:
        raise MachineError("Candidate configuration is invalid or contains secret material") from exc
    return selected


def load_renderings(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    try:
        secret_free(value)
        safety.validate_renderings(value)
    except (BenchmarkError, ValueError, TypeError) as exc:
        raise MachineError("Trusted rendering registry is invalid or not detection-ready") from exc
    return value


def canonicalize(audio: Path, destination: Path, run: Callable[..., Any] = subprocess.run) -> None:
    if not audio.is_file():
        raise MachineError("Input audio is unavailable")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MachineError("ffmpeg is required to canonicalize recorded audio")
    completed = run(
        [ffmpeg, "-nostdin", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destination)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False, timeout=90,
    )
    if getattr(completed, "returncode", 1) != 0 or not destination.is_file():
        raise MachineError("ffmpeg could not canonicalize the supplied audio")
    try:
        with wave.open(str(destination), "rb") as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype()) != (1, 2, 16000, "NONE"):
                raise MachineError("ffmpeg did not produce mono 16 kHz PCM16 WAV")
    except wave.Error as exc:
        raise MachineError("ffmpeg did not produce a valid WAV file") from exc


def split_wav(source: Path, directory: Path, seconds: int) -> list[tuple[Path, float, float]]:
    if seconds < 1 or seconds > 600:
        raise MachineError("--segment-seconds must be between 1 and 600")
    with wave.open(str(source), "rb") as stream:
        rate, frames = stream.getframerate(), stream.getnframes()
        per_segment = seconds * rate
        result: list[tuple[Path, float, float]] = []
        for number, start_frame in enumerate(range(0, frames, per_segment), 1):
            count = min(per_segment, frames - start_frame)
            stream.setpos(start_frame)
            path = directory / f"segment-{number:04d}.wav"
            with wave.open(str(path), "wb") as output:
                output.setparams(stream.getparams())
                output.writeframes(stream.readframes(count))
            result.append((path, start_frame / rate, (start_frame + count) / rate))
    if not result:
        raise MachineError("Input audio contains no samples")
    return result


def _pre_translation_guard(registry: dict[str, Any]) -> Callable[[str], dict[str, str] | None]:
    def guard(arabic: str) -> dict[str, str] | None:
        decision = safety.route(arabic, "", "", None, registry)
        guard.decision = decision  # type: ignore[attr-defined]
        if decision["outcome"] == "ordinary_translation":
            return None
        if decision["outcome"] == "quran_rendering":
            return {"en": decision["en"], "fr": decision["fr"]}
        # The adapter treats uncertainty as a hard stop before calling MT.
        return {"uncertainty": str(decision["reason"])}
    guard.decision = None  # type: ignore[attr-defined]
    return guard


def _progress(callback: Callable[[dict[str, Any]], None] | None, event: str, **fields: Any) -> None:
    """Report safe, non-content processing progress without affecting a run."""
    if callback is None:
        return
    try:
        callback({"event": event, **fields})
    except Exception:
        # Progress is advisory; a UI or diagnostic write must not fail inference.
        return


def _final_safety(result: dict[str, Any], registry: dict[str, Any], predecision: dict[str, Any] | None = None) -> dict[str, Any]:
    if result.get("failure"):
        # A provider may have produced partial text before failing. It must not
        # escape into the text artifacts, page, or speech path.
        result["en"], result["fr"] = "", ""
        return {"outcome": "withheld", "reason": "candidate_failure", "sources": [], "en": None, "fr": None}
    # The pre-translation guard already classified this exact Arabic transcript.
    # Reuse that safety outcome after translation instead of scanning the full
    # rendering corpus a second time. Candidate failures still fail closed above.
    if result.get("uncertainty"):
        # Preserve the final safety reason: the pre-translation guard's
        # possible-Qur'an hold is represented as candidate uncertainty by the
        # adapter, which takes precedence when the final route runs.
        decision = safety.route(result.get("arabic", ""), result.get("en", ""), result.get("fr", ""), result.get("uncertainty"), registry)
    elif isinstance(predecision, dict) and predecision.get("outcome") in {"ordinary_translation", "quran_rendering", "withheld"}:
        decision = dict(predecision)
        if decision["outcome"] == "ordinary_translation":
            decision["en"], decision["fr"] = result.get("en", "") or "", result.get("fr", "") or ""
    else:
        decision = safety.route(result.get("arabic", ""), result.get("en", ""), result.get("fr", ""), result.get("uncertainty"), registry)
    result["en"], result["fr"] = decision["en"] or "", decision["fr"] or ""
    return decision


def _write_new_text(path: Path, value: str) -> None:
    # Output directory is new, but exclusive creation keeps the contract explicit.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value)


def _speak(text: str, language: str, path: Path) -> dict[str, str]:
    """Generate selected ElevenLabs playback; never fall back to device voices."""
    return tts.synthesize(text, language, path)


def _page(segments: list[dict[str, Any]], say: bool) -> str:
    rows = []
    for segment in segments:
        safety_info = segment["safety"]
        audio = ""
        if say:
            links = []
            for language in ("en", "fr"):
                synthesis = segment.get("synthesis", {}).get(language, {})
                file = synthesis.get("file")
                if file and synthesis.get("status") == "created":
                    links.append(f'<a href="{html.escape(file)}">{language.upper()} speech</a>')
                elif synthesis.get("status") == "failed":
                    links.append(f'{language.upper()} speech failed')
            audio = " · ".join(links)
        rows.append("<section><h2>%.2f–%.2fs: %s</h2><p><b>Arabic:</b> %s</p><p><b>English:</b> %s</p><p><b>French:</b> %s</p><p><b>Safety:</b> %s</p><p>%s</p></section>" % (
            segment["start_seconds"], segment["end_seconds"], html.escape(safety_info["outcome"]),
            html.escape(segment["result"].get("arabic", "")), html.escape(segment["result"].get("en", "")),
            html.escape(segment["result"].get("fr", "")), html.escape(safety_info["reason"]), audio))
    return "<!doctype html><meta charset=utf-8><title>Moin recorded-audio run</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}section{border-top:1px solid #ccc;padding:.75rem 0}p{white-space:pre-wrap}</style><h1>Moin experimental recorded-audio run</h1><p>Sequential bounded segments. A sentence or verse crossing a segment boundary may lose context; inspect the timeline before relying on a result.</p><audio controls src=\"source.wav\"></audio>" + "".join(rows)


def run_machine(
    args: argparse.Namespace, *,
    process: Callable[..., dict[str, Any]] = adapters.process,
    canonicalizer: Callable[..., None] = canonicalize,
    speaker: Callable[..., dict[str, Any]] = _speak,
    should_cancel: Callable[[], bool] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    overall_started = time.perf_counter()
    cancelled = should_cancel or (lambda: False)

    def check_cancelled() -> None:
        if cancelled():
            raise MachineCancelled("Processing cancelled")

    output = Path(args.out)
    if output.exists():
        raise MachineError("--out must name a new directory; refusing to overwrite an existing run")
    config, registry = load_candidate(Path(args.config), args.candidate), load_renderings(Path(args.renderings))
    try:
        output.mkdir(parents=True, mode=0o700)
    except OSError as exc:
        raise MachineError("Cannot create output directory") from exc
    try:
        with tempfile.TemporaryDirectory(prefix="moin-machine-") as temporary:
            canonical = Path(temporary) / "source.wav"
            started = time.perf_counter()
            _progress(progress_callback, "stage_started", stage="canonicalize")
            canonicalizer(Path(args.audio), canonical)
            canonicalize_ms = round((time.perf_counter() - started) * 1000, 3)
            _progress(progress_callback, "stage_finished", stage="canonicalize", duration_ms=canonicalize_ms)
            check_cancelled()
            shutil.copyfile(canonical, output / "source.wav")
            started = time.perf_counter()
            split_segments = split_wav(canonical, Path(temporary), args.segment_seconds)
            segmenting_ms = round((time.perf_counter() - started) * 1000, 3)
            _progress(progress_callback, "segments_ready", stage="segmenting", segment_count=len(split_segments), duration_ms=segmenting_ms)
            segments: list[dict[str, Any]] = []
            processing_started = time.perf_counter()
            for number, (audio, start, end) in enumerate(split_segments, 1):
                check_cancelled()
                _progress(progress_callback, "segment_started", stage="asr_translation", current_segment=number, segment_count=len(split_segments))
                guard = _pre_translation_guard(registry)
                guard_started: float | None = None

                def timed_guard(arabic: str) -> dict[str, str] | None:
                    nonlocal guard_started
                    guard_started = time.perf_counter()
                    _progress(progress_callback, "stage_started", stage="safety_pre_translation", current_segment=number, segment_count=len(split_segments))
                    decision = guard(arabic)
                    _progress(progress_callback, "stage_finished", stage="safety_pre_translation", current_segment=number,
                              segment_count=len(split_segments), duration_ms=round((time.perf_counter() - guard_started) * 1000, 3))
                    return decision

                process_started = time.perf_counter()
                result = process(config, audio, translation_guard=timed_guard)
                check_cancelled()
                timing = result.get("timing_ms", {})
                _progress(progress_callback, "stage_finished", stage="asr", current_segment=number,
                          segment_count=len(split_segments), duration_ms=timing.get("asr"))
                _progress(progress_callback, "stage_finished", stage="translation", current_segment=number,
                          segment_count=len(split_segments), duration_ms=timing.get("translation_wall"))
                _progress(progress_callback, "stage_started", stage="safety_final", current_segment=number, segment_count=len(split_segments))
                safety_started = time.perf_counter()
                decision = _final_safety(result, registry, guard.decision)
                _progress(progress_callback, "stage_finished", stage="safety_final", current_segment=number,
                          segment_count=len(split_segments), duration_ms=round((time.perf_counter() - safety_started) * 1000, 3))
                item = {"number": number, "start_seconds": start, "end_seconds": end, "result": result, "pre_translation_safety": guard.decision, "safety": decision}
                if args.say and decision["outcome"] != "withheld" and not result.get("failure"):
                    synthesis_started = time.perf_counter()
                    _progress(progress_callback, "stage_started", stage="tts", current_segment=number, segment_count=len(split_segments))

                    def synthesize(language: str) -> tuple[str, dict[str, Any]]:
                        filename = f"segment-{number:04d}-{language}.mp3"
                        if not result[language]:
                            return language, {"status": "not_attempted_empty_text", "provider": "elevenlabs", "timing_ms": 0}
                        return language, speaker(result[language], language, output / filename)

                    # English and French synthesis have independent text,
                    # voices, and output files, so their network waits overlap.
                    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="moin-tts") as pool:
                        futures = {language: pool.submit(synthesize, language) for language in ("en", "fr")}
                        synthesis = {language: futures[language].result()[1] for language in ("en", "fr")}
                    item["synthesis"] = synthesis
                    item["synthesis_wall_ms"] = round((time.perf_counter() - synthesis_started) * 1000, 3)
                    _progress(progress_callback, "stage_finished", stage="tts", current_segment=number,
                              segment_count=len(split_segments), duration_ms=item["synthesis_wall_ms"])
                    check_cancelled()
                segments.append(item)
                _progress(progress_callback, "segment_finished", stage="segment", current_segment=number,
                          segment_count=len(split_segments), duration_ms=round((time.perf_counter() - process_started) * 1000, 3))
            processing_ms = round((time.perf_counter() - processing_started) * 1000, 3)
            artifact_started = time.perf_counter()
            transcript = "\n".join(item["result"].get("arabic", "") for item in segments) + "\n"
            en = "\n".join(item["result"].get("en", "") for item in segments) + "\n"
            fr = "\n".join(item["result"].get("fr", "") for item in segments) + "\n"
            _write_new_text(output / "transcript.txt", transcript)
            _write_new_text(output / "en.txt", en)
            _write_new_text(output / "fr.txt", fr)
            artifact_ms = round((time.perf_counter() - artifact_started) * 1000, 3)
            runtime = adapters.runtime_identity()
            runtime["asr"] = adapters.asr_runtime_identity(config)
            record = {"kind": "experimental_recorded_audio", "created_at": datetime.now(timezone.utc).isoformat(), "experimental": True, "winner_claim": False, "boundary_caveat": "Segments are processed independently; speech crossing a boundary may lose context.", "source": {"original_name": Path(args.audio).name, "original_sha256": _sha256(Path(args.audio)), "canonical_sha256": _sha256(canonical), "format": "mono 16 kHz PCM16 WAV"}, "candidate": {"id": config["id"], "config": config, "runtime": runtime}, "renderings": {"sha256": _sha256(Path(args.renderings)), "schema_version": registry.get("schema_version")}, "synthesis": tts.configuration() if args.say else None, "segment_seconds": args.segment_seconds, "timing_ms": {"canonicalize": canonicalize_ms, "segmenting": segmenting_ms, "processing": processing_ms, "artifacts": artifact_ms, "total": round((time.perf_counter() - overall_started) * 1000, 3)}, "segments": segments}
            _write_new_text(output / "result.json", json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            _write_new_text(output / "index.html", _page(segments, args.say))
            return record
    except Exception:
        # A failed result is not a usable, apparently complete run.
        shutil.rmtree(output, ignore_errors=True)
        raise


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="machine", description="Experimental Moin recorded-audio processor")
    p.add_argument("--audio", type=Path, required=True, help="local recorded media")
    p.add_argument("--config", type=Path, required=True, help="candidate JSON object or array")
    p.add_argument("--candidate", help="candidate id when --config is an array")
    p.add_argument("--renderings", type=Path, required=True, help="official trusted rendering registry JSON")
    p.add_argument("--out", type=Path, required=True, help="new output directory")
    p.add_argument("--segment-seconds", type=int, default=30)
    p.add_argument("--say", action="store_true", help="synthesize non-withheld EN/FR segment speech with ElevenLabs")
    return p


def summary(record: dict[str, Any]) -> dict[str, int]:
    """Return counts that distinguish a completed artifact from a usable run."""
    segments = record["segments"]
    failures = sum(bool(item["result"].get("failure")) for item in segments)
    withheld = sum(item["safety"]["outcome"] == "withheld" for item in segments)
    return {"segments": len(segments), "failures": failures, "withheld": withheld, "translated": len(segments) - withheld}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = run_machine(args)
    except (MachineError, OSError, ValueError) as exc:
        print(json.dumps({"error": {"code": "machine_rejected", "message": str(exc)}}), file=sys.stderr)
        return 2
    report = {"out": str(args.out), "experimental": True, **summary(result)}
    print(json.dumps(report, ensure_ascii=False))
    # The complete evidence remains available for diagnosis, but automation must
    # not treat a run containing candidate/provider failures as a success.
    return 1 if report["failures"] else 0
