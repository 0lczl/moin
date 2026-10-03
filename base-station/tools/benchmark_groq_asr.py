"""Run an explicit nine-clip local quality/timing check against Groq.

Usage from base-station:
  GROQ_API_KEY=... .venv/bin/python tools/benchmark_groq_asr.py --output /tmp/groq-nine.json

Only audio files are uploaded. This create-only report stores score counts and
timings, never hypotheses, audio, references, API keys, or provider bodies. It
is a small development-sample measurement, not evidence of parity or production
quality.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from moin_benchmark.core import audio_path, registry, write_new
from moin_asr_benchmark.core import add_counts, score_pair
from moin_studio.groq_asr import MODEL_ID, GroqASRError, estimate_cost_usd, transcribe


def run(corpus_root: Path, output_path: Path, *, timeout_seconds: float = 30.0) -> dict:
    if not os.environ.get("GROQ_API_KEY", "").strip():
        raise ValueError("Set GROQ_API_KEY in the environment before running this benchmark.")
    clips = registry(corpus_root)
    if len(clips) != 9 or any(clip["split"] != "development" for clip in clips):
        raise ValueError("This benchmark requires the nine development clips.")
    protocol_path = PROJECT / "asr-benchmark-data" / "protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("version") != "moin-asr-nine-v1":
        raise ValueError("The checked-in nine-clip scoring protocol is unavailable.")
    exclusions = protocol.get("primary_score_exclusions", {})

    started = time.perf_counter()
    rows = []
    scored = []
    total_audio_seconds = 0.0
    for clip in clips:
        path = audio_path(corpus_root, clip)
        inference_started = time.perf_counter()
        try:
            result = transcribe(path, timeout_seconds=timeout_seconds)
        except GroqASRError as error:
            rows.append({
                "clip_id": clip["id"],
                "status": "failed",
                "failure": error.as_dict(),
                "elapsed_ms": round((time.perf_counter() - inference_started) * 1000, 3),
            })
            continue
        total_audio_seconds += result["duration_seconds"]
        row = {
            "clip_id": clip["id"],
            "status": "ok",
            "duration_seconds": result["duration_seconds"],
            "elapsed_ms": result["elapsed_ms"],
            "billable_seconds_estimate": result["billable_seconds_estimate"],
            "cost_usd_estimate": result["cost_usd_estimate"],
        }
        if clip["id"] in exclusions:
            row["score_included"] = False
            row["score_exclusion"] = exclusions[clip["id"]]
        else:
            metrics = score_pair(clip["transcript"]["text"], result["text"])
            row["score_included"] = True
            row["strict_wer"] = metrics["wer"]
            row["strict_cer"] = metrics["cer"]
            scored.append({"wer": metrics["wer"], "cer": metrics["cer"]})
        rows.append(row)

    failures = sum(row["status"] != "ok" for row in rows)
    successful = [row for row in rows if row["status"] == "ok"]
    total_cost = sum(row.get("cost_usd_estimate", 0) for row in successful)
    report = {
        "schema_version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": "Groq API",
        "model": MODEL_ID,
        "api_endpoint": "https://api.groq.com/openai/v1/audio/transcriptions",
        "credentials_env": "GROQ_API_KEY",
        "sample": {
            "clip_count": len(clips),
            "successful_clips": len(successful),
            "failed_clips": failures,
            "total_audio_seconds": round(total_audio_seconds, 3),
            "total_elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "estimated_asr_cost_usd": round(total_cost, 8),
        },
        "strict_micro_scores": {
            "wer": add_counts(scored, "wer") if scored else None,
            "cer": add_counts(scored, "cer") if scored else None,
            "scored_clip_count": len(scored),
        },
        "clips": rows,
        "limitations": [
            "Nine reused development clips only; this result does not establish parity or production quality.",
            "WER/CER use the project's user-reviewed working references and exclude the clip with an untimed unclear ending.",
            "Arabic human review is still required, especially for religious terms, names, Qur'an wording, omissions, and negation.",
            "Cost is an estimate using the current documented per-hour rate and ten-second per-request minimum; verify the invoice.",
        ],
    }
    write_new(output_path, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run Groq Whisper large-v3 on the nine local Arabic development clips")
    parser.add_argument("--corpus", type=Path, default=BASE / "benchmark-data")
    parser.add_argument("--output", type=Path, required=True, help="New report path; existing files are never replaced")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    try:
        report = run(args.corpus, args.output, timeout_seconds=args.timeout_seconds)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": str(args.output),
        "model": report["model"],
        "sample": report["sample"],
        "strict_micro_scores": report["strict_micro_scores"],
    }, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["sample"]["failed_clips"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
