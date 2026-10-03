"""Immutable ASR-only lock, inference, and scoring workflow."""
from __future__ import annotations

import inspect
import re
import time
from pathlib import Path

from moin_benchmark.core import audio_path, registry

from . import adapters
from .core import (
    AsrBenchmarkError, add_counts, digest, file_digest, now, read_json, require,
    score_pair, write_new,
)


_REVISION = re.compile(r"[0-9a-f]{40}")
_SENTINEL = "[غير واضح]"


class AsrBenchmark:
    def __init__(self, corpus_root: Path, workspace: Path):
        self.corpus_root = Path(corpus_root)
        self.workspace = Path(workspace)

    @staticmethod
    def implementation_identity() -> str:
        folder = Path(__file__).parent
        return digest({path.name: path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.py"))})

    @staticmethod
    def _validate_candidate(candidate: dict) -> None:
        require(isinstance(candidate, dict), "Candidate must be an object")
        require(set(candidate) == {"id", "name", "adapter", "model", "runtime", "settings"}, "Invalid candidate fields")
        require(isinstance(candidate["id"], str) and re.fullmatch(r"[a-z0-9_-]{1,80}", candidate["id"]), "Invalid candidate ID")
        require(candidate["adapter"] == "faster-whisper", "Unsupported ASR adapter")
        model, runtime, settings = candidate["model"], candidate["runtime"], candidate["settings"]
        require(set(model) == {"repository", "revision"}, "Invalid model fields")
        require(isinstance(model["repository"], str) and "/" in model["repository"], "Pinned model repository required")
        require(isinstance(model["revision"], str) and _REVISION.fullmatch(model["revision"]), "Immutable 40-character model revision required")
        require(runtime == {"device": "cpu", "compute_type": "int8"}, "This comparison requires CPU int8")
        require(set(settings) == {"language", "task", "beam_size", "temperature", "vad_filter", "condition_on_previous_text"}, "Invalid decoding settings")
        require(settings["language"] == "ar" and settings["task"] == "transcribe", "Arabic transcription settings required")
        require(isinstance(settings["beam_size"], int) and settings["beam_size"] >= 1, "Positive beam size required")
        require(settings["temperature"] == 0, "Deterministic temperature=0 required")
        require(isinstance(settings["vad_filter"], bool) and isinstance(settings["condition_on_previous_text"], bool), "Boolean decoding flags required")

    def _snapshot(self, protocol: dict) -> list[dict]:
        require(protocol.get("version") == "moin-asr-nine-v1", "Unsupported ASR protocol")
        exclusions = protocol.get("primary_score_exclusions")
        require(isinstance(exclusions, dict), "Primary-score exclusions required")
        clips = registry(self.corpus_root)
        require(len(clips) == 9 and all(clip["split"] == "development" for clip in clips), "ASR v1 requires the nine development clips")
        snapshot = []
        for clip in clips:
            path = audio_path(self.corpus_root, clip)
            reference = clip["transcript"]["text"]
            review_path = (self.corpus_root / clip["transcript"]["review_path"]).resolve()
            require(review_path.is_relative_to(self.corpus_root.resolve()), "Review path escapes corpus")
            require(review_path.read_text(encoding="utf-8").strip() == reference, f"{clip['id']}: corpus/reference file mismatch")
            excluded_reason = exclusions.get(clip["id"])
            if _SENTINEL in reference:
                require(isinstance(excluded_reason, str) and excluded_reason, f"{clip['id']}: unclear reference must be excluded explicitly")
            else:
                require(clip["id"] not in exclusions, f"{clip['id']}: unsupported score exclusion")
            snapshot.append({
                "id": clip["id"],
                "speaker": clip["speaker"],
                "tags": clip["tags"],
                "audio": str(path.relative_to(self.corpus_root.resolve())),
                "audio_sha256": clip["sha256"],
                "duration_seconds": clip["duration_seconds"],
                "reference": {
                    "text": reference,
                    "sha256": file_digest(review_path),
                    "state": "user-reviewed-working-reference",
                    "review_path": str(review_path.relative_to(self.corpus_root.resolve())),
                    "reviewer": clip["transcript"]["reviewer"],
                    "date": clip["transcript"]["date"],
                },
                "primary_score": {"included": excluded_reason is None, "exclusion_reason": excluded_reason},
            })
        require(set(exclusions) == {clip["id"] for clip in snapshot if not clip["primary_score"]["included"]}, "Unknown exclusion ID")
        return snapshot

    def lock(self, candidates_path: Path, protocol_path: Path) -> dict:
        require(not (self.workspace / "lock.json").exists(), "ASR comparison already locked")
        candidates = read_json(candidates_path)
        protocol = read_json(protocol_path)
        require(isinstance(candidates, list) and 2 <= len(candidates) <= 4, "Lock two to four candidates")
        for candidate in candidates:
            self._validate_candidate(candidate)
        require(len({candidate["id"] for candidate in candidates}) == len(candidates), "Duplicate candidate ID")
        snapshot = self._snapshot(protocol)
        lock = {
            "schema_version": 1,
            "locked_at": now(),
            "protocol": protocol,
            "protocol_identity": digest(protocol),
            "corpus_snapshot": snapshot,
            "corpus_identity": digest(snapshot),
            "implementation_identity": self.implementation_identity(),
            "runtime": adapters.runtime_identity(),
            "adapter_contract": str(inspect.signature(adapters.transcribe)),
            "candidates": {candidate["id"]: {"config": candidate, "identity": digest(candidate)} for candidate in candidates},
        }
        require("reference" not in lock["adapter_contract"], "Adapter contract must be audio-only")
        write_new(self.workspace / "lock.json", lock)
        return lock

    def locked(self) -> dict:
        lock = read_json(self.workspace / "lock.json")
        require(lock["protocol_identity"] == digest(lock["protocol"]), "Protocol changed after lock")
        require(lock["corpus_identity"] == digest(lock["corpus_snapshot"]), "Corpus snapshot changed after lock")
        require(lock["implementation_identity"] == self.implementation_identity(), "ASR implementation changed after lock")
        require(lock["runtime"] == adapters.runtime_identity(), "Runtime changed after lock")
        for entry in lock["candidates"].values():
            self._validate_candidate(entry["config"])
            require(entry["identity"] == digest(entry["config"]), "Candidate changed after lock")
        current = self._snapshot(lock["protocol"])
        require(digest(current) == lock["corpus_identity"], "Corpus/audio/reference changed after lock")
        return lock

    def result_path(self, candidate_id: str, clip_id: str) -> Path:
        return self.workspace / "runs" / candidate_id / f"{clip_id}.json"

    @staticmethod
    def _validate_result(result: dict, candidate_id: str, entry: dict, clip: dict, lock: dict) -> None:
        require(isinstance(result, dict), "Malformed result")
        require(result.get("schema_version") == 1, "Unsupported result schema")
        require(result.get("clip_id") == clip["id"] and result.get("candidate_id") == candidate_id, "Result path identity mismatch")
        require(result.get("candidate_identity") == entry["identity"], "Result candidate identity mismatch")
        require(result.get("corpus_identity") == lock["corpus_identity"], "Result corpus identity mismatch")
        require(result.get("audio_sha256") == clip["audio_sha256"], "Result audio identity mismatch")
        require(result.get("reference_sha256") == clip["reference"]["sha256"], "Result reference identity mismatch")
        require(result.get("inference_input") == {"audio_sha256": clip["audio_sha256"], "candidate_identity": entry["identity"]}, "Invalid inference input record")
        require(result.get("status") in {"ok", "failed"}, "Invalid result status")
        require(isinstance(result.get("raw_hypothesis"), str), "Invalid result hypothesis")
        require(isinstance(result.get("model_metadata"), dict), "Invalid model metadata")
        require(isinstance(result.get("attempt_wall_ms"), (int, float)) and result["attempt_wall_ms"] >= 0, "Invalid attempt timing")
        for key in ("elapsed_ms", "setup_ms"):
            require(result.get(key) is None or isinstance(result[key], (int, float)) and result[key] >= 0, f"Invalid {key}")
        if result["status"] == "ok":
            require(result["raw_hypothesis"].strip(), "Successful result must have a hypothesis")
            require(result["elapsed_ms"] is not None and result["setup_ms"] is not None, "Successful result requires inference timing")
            require(result.get("failure") is None, "Successful result cannot have a failure")
        else:
            require(isinstance(result.get("failure"), dict) and all(result["failure"].get(key) is not None for key in ("code", "message", "retryable")), "Failed result requires structured failure")

    def run(self, candidate_id: str, clip_id: str | None = None) -> dict:
        lock = self.locked()
        require(candidate_id in lock["candidates"], "Unknown candidate")
        entry = lock["candidates"][candidate_id]
        clips = lock["corpus_snapshot"]
        if clip_id is not None:
            clips = [clip for clip in clips if clip["id"] == clip_id]
            require(clips, "Unknown clip")
        recorded = reused = 0
        for clip in clips:
            destination = self.result_path(candidate_id, clip["id"])
            if destination.exists():
                result = read_json(destination)
                self._validate_result(result, candidate_id, entry, clip, lock)
                reused += 1
                continue
            audio = (self.corpus_root / clip["audio"]).resolve()
            attempt_started = time.perf_counter()
            try:
                inference = adapters.transcribe(audio, entry["config"])
                require(isinstance(inference, dict), "Malformed adapter output")
                require(inference.get("status") == "ok", "Adapter did not return success")
                require(isinstance(inference.get("raw_hypothesis"), str), "Malformed hypothesis")
                require(isinstance(inference.get("elapsed_ms"), (int, float)) and inference["elapsed_ms"] >= 0, "Malformed elapsed time")
                require(isinstance(inference.get("setup_ms"), (int, float)) and inference["setup_ms"] >= 0, "Malformed setup time")
                if not inference["raw_hypothesis"].strip():
                    inference = {**inference, "status": "failed", "failure": {
                        "code": "empty_hypothesis", "message": "Candidate returned no transcript.", "retryable": False}}
            except Exception as error:
                inference = {
                    "status": "failed", "raw_hypothesis": "", "elapsed_ms": None, "setup_ms": None,
                    "model_metadata": {},
                    "failure": {"code": "candidate_failed", "message": "Candidate failed; no output was substituted.",
                                "exception_type": type(error).__name__, "retryable": isinstance(error, TimeoutError)},
                }
            result = {
                "schema_version": 1,
                "recorded_at": now(),
                "clip_id": clip["id"],
                "candidate_id": candidate_id,
                "candidate_identity": entry["identity"],
                "corpus_identity": lock["corpus_identity"],
                "audio_sha256": clip["audio_sha256"],
                "reference_sha256": clip["reference"]["sha256"],
                "inference_input": {"audio_sha256": clip["audio_sha256"], "candidate_identity": entry["identity"]},
                "attempt_wall_ms": round((time.perf_counter() - attempt_started) * 1000, 3),
                **inference,
            }
            write_new(destination, result)
            recorded += 1
        return {"candidate": candidate_id, "recorded": recorded, "reused": reused}

    @staticmethod
    def _clip_score(clip: dict, result: dict) -> dict:
        base = {
            "clip_id": clip["id"], "candidate_id": result["candidate_id"],
            "duration_seconds": clip["duration_seconds"], "status": result["status"],
            "elapsed_ms": result["elapsed_ms"], "setup_ms": result["setup_ms"],
            "attempt_wall_ms": result["attempt_wall_ms"], "failure": result["failure"],
            "raw_hypothesis": result["raw_hypothesis"],
        }
        if not clip["primary_score"]["included"]:
            return {**base, "score_status": "excluded", "exclusion_reason": clip["primary_score"]["exclusion_reason"],
                    "strict": None, "alef": None}
        hypothesis = result["raw_hypothesis"] if result["status"] == "ok" else ""
        return {**base, "score_status": "scored" if result["status"] == "ok" else "failure_scored_as_empty_hypothesis",
                "exclusion_reason": None,
                "strict": score_pair(clip["reference"]["text"], hypothesis),
                "alef": score_pair(clip["reference"]["text"], hypothesis, alef=True)}

    def report(self) -> dict:
        lock = self.locked()
        candidates = []
        for candidate_id, entry in lock["candidates"].items():
            clip_scores = []
            for clip in lock["corpus_snapshot"]:
                path = self.result_path(candidate_id, clip["id"])
                require(path.exists(), f"Missing result: {candidate_id}/{clip['id']}")
                result = read_json(path)
                self._validate_result(result, candidate_id, entry, clip, lock)
                clip_scores.append(self._clip_score(clip, result))
            scored = [clip for clip in clip_scores if clip["score_status"] != "excluded"]
            strict = {
                "wer": add_counts([clip["strict"] for clip in scored], "wer"),
                "cer": add_counts([clip["strict"] for clip in scored], "cer"),
            }
            alef = {
                "wer": add_counts([clip["alef"] for clip in scored], "wer"),
                "cer": add_counts([clip["alef"] for clip in scored], "cer"),
            }
            failures = [{"clip_id": clip["clip_id"], "failure": clip["failure"]}
                        for clip in clip_scores if clip["status"] != "ok"]
            candidates.append({
                "id": candidate_id,
                "name": entry["config"]["name"],
                "identity": entry["identity"],
                "candidate_status": "complete" if not failures else "ineligible_failed_clips",
                "selection_eligible": not failures,
                "strict": strict,
                "alef": alef,
                "coverage": {
                    "scored_clips": len(scored), "total_clips": len(clip_scores),
                    "scored_duration_seconds": round(sum(clip["duration_seconds"] for clip in scored), 6),
                    "total_duration_seconds": round(sum(clip["duration_seconds"] for clip in clip_scores), 6),
                    "scored_reference_words": strict["wer"]["reference_units"],
                    "excluded": [{"clip_id": clip["clip_id"], "reason": clip["exclusion_reason"]}
                                 for clip in clip_scores if clip["score_status"] == "excluded"],
                },
                "failures": failures,
                "elapsed_ms": round(sum(clip["elapsed_ms"] or 0 for clip in clip_scores), 3),
                "setup_ms": round(sum(clip["setup_ms"] or 0 for clip in clip_scores), 3),
                "attempt_wall_ms": round(sum(clip["attempt_wall_ms"] for clip in clip_scores), 3),
                "missing_inference_timing_clips": sum(clip["elapsed_ms"] is None for clip in clip_scores),
                "clips": clip_scores,
            })
        report = {
            "schema_version": 1,
            "created_at": now(),
            "corpus_identity": lock["corpus_identity"],
            "protocol_identity": lock["protocol_identity"],
            "runtime": lock["runtime"],
            "selection_status": "pending_arabic_human_review",
            "selection_note": "Automated scores describe eight clear user-reviewed development clips. Review religious terms, names, Qur'an wording, omissions, additions, negation, and meaning before selecting a model.",
            "candidates": candidates,
        }
        write_new(self.workspace / "report.json", report)
        return report
