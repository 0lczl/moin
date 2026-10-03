import json
from pathlib import Path

import pytest

from moin_asr_benchmark import adapters
from moin_asr_benchmark.core import edit_counts, normalize_arabic, score_pair
from moin_asr_benchmark.runner import AsrBenchmark
from tools.prepare_asr_review import build as build_review


BASE = Path(__file__).resolve().parents[1]
CORPUS = BASE / "benchmark-data"
CANDIDATES = BASE / "asr-benchmark-data" / "candidates.example.json"
PROTOCOL = BASE / "asr-benchmark-data" / "protocol.json"


def require_local_corpus_audio():
    """The nine source recordings are intentionally absent from GitHub."""
    clips = json.loads((CORPUS / "corpus.json").read_text())
    if any(not (CORPUS / clip["audio"]).is_file() for clip in clips):
        pytest.skip("nine-clip source audio is local-only")


def test_arabic_normalization_is_explicit_and_conservative():
    assert normalize_arabic("  أَسْأَلُـ،  ") == "أسأل"
    assert normalize_arabic("أَسْأَلُـ،", alef=True) == "اسال"
    assert normalize_arabic("إذن أذن") == "إذن أذن"
    assert normalize_arabic("قُلْ ۞ هُوَ") == "قل هو"
    assert normalize_arabic("قال قال") == "قال قال"


def test_edit_counts_and_empty_reference_semantics():
    counts = edit_counts("a b c d".split(), "a x d y".split())
    assert counts == {
        "substitutions": 1, "deletions": 1, "insertions": 1,
        "errors": 3, "reference_units": 4, "rate": .75,
    }
    assert edit_counts(["a", "a"], ["a"])["deletions"] == 1
    assert edit_counts(["a", "b"], [])["deletions"] == 2
    assert edit_counts([], ["extra"])["rate"] is None
    assert edit_counts([], ["extra"])["insertions"] == 1


def test_strict_and_alef_scores_are_separate():
    strict = score_pair("إذن", "اذن")
    relaxed = score_pair("إذن", "اذن", alef=True)
    assert strict["wer"]["rate"] == 1
    assert relaxed["wer"]["rate"] == 0


def test_audio_only_runner_preserves_failures_exclusion_and_micro_counts(monkeypatch, tmp_path):
    require_local_corpus_audio()
    calls = []

    def fake_transcribe(audio_path, config):
        calls.append((Path(audio_path), json.loads(json.dumps(config))))
        if config["id"] == "whisper-large-v3" and Path(audio_path).stem == "XWsDJcbuE5s":
            raise TimeoutError("fixture")
        return {
            "status": "ok", "raw_hypothesis": "كلام تجريبي", "elapsed_ms": 10,
            "setup_ms": 2, "model_metadata": {"fixture": True}, "failure": None,
        }

    monkeypatch.setattr(adapters, "transcribe", fake_transcribe)
    benchmark = AsrBenchmark(CORPUS, tmp_path)
    lock = benchmark.lock(CANDIDATES, PROTOCOL)
    assert "reference" not in lock["adapter_contract"]

    benchmark.run("whisper-small")
    benchmark.run("whisper-large-v3")
    report = benchmark.report()

    assert len(calls) == 18
    assert all(len(call) == 2 for call in calls)
    assert all("reference" not in config for _, config in calls)
    for candidate in report["candidates"]:
        assert candidate["coverage"]["scored_clips"] == 8
        assert candidate["coverage"]["total_clips"] == 9
        assert candidate["coverage"]["excluded"][0]["clip_id"] == "I0tWefiPh-0"
        assert candidate["strict"]["wer"]["reference_units"] == candidate["coverage"]["scored_reference_words"]
    large = next(item for item in report["candidates"] if item["id"] == "whisper-large-v3")
    assert large["failures"][0]["clip_id"] == "XWsDJcbuE5s"
    assert large["candidate_status"] == "ineligible_failed_clips"
    assert large["selection_eligible"] is False
    failed = next(item for item in large["clips"] if item["clip_id"] == "XWsDJcbuE5s")
    assert failed["score_status"] == "failure_scored_as_empty_hypothesis"
    assert failed["strict"]["wer"]["deletions"] > 0
    assert failed["elapsed_ms"] is None
    assert failed["attempt_wall_ms"] >= 0
    raw = json.loads((tmp_path / "runs/whisper-small/XWsDJcbuE5s.json").read_text())
    assert set(raw["inference_input"]) == {"audio_sha256", "candidate_identity"}
    assert "reference" not in raw["inference_input"]

    raw["status"] = "ok"
    raw["raw_hypothesis"] = ""
    raw["elapsed_ms"] = None
    raw["setup_ms"] = None
    raw["failure"] = None
    (tmp_path / "runs/whisper-small/XWsDJcbuE5s.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="Successful result"):
        benchmark.run("whisper-small")


def test_lock_hashes_references_audio_and_settings(tmp_path):
    require_local_corpus_audio()
    lock = AsrBenchmark(CORPUS, tmp_path).lock(CANDIDATES, PROTOCOL)
    assert len(lock["corpus_identity"]) == 64
    assert all(len(clip["audio_sha256"]) == 64 for clip in lock["corpus_snapshot"])
    assert all(len(clip["reference"]["sha256"]) == 64 for clip in lock["corpus_snapshot"])
    assert all(len(item["identity"]) == 64 for item in lock["candidates"].values())
    assert lock["corpus_snapshot"][3]["primary_score"]["included"] is False
    assert "[غير واضح]" in lock["corpus_snapshot"][3]["reference"]["text"]


def test_review_page_resolves_audio_and_keeps_model_ids_private(tmp_path):
    workspace, corpus = tmp_path / "private-run", tmp_path / "source-corpus"
    workspace.mkdir()
    audio = corpus / "audio" / "clip.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"fixture")
    (workspace / "lock.json").write_text(json.dumps({
        "corpus_identity": "a" * 64,
        "corpus_snapshot": [{
            "id": "clip", "audio": "audio/clip.wav",
            "reference": {"text": "النص المرجعي"},
            "primary_score": {"included": True, "exclusion_reason": None},
        }],
    }))
    candidates = []
    for candidate_id, identity, hypothesis in (
        ("secret-model-small", "b" * 64, "النص الأول"),
        ("secret-model-large", "c" * 64, "النص الثاني"),
    ):
        candidates.append({
            "id": candidate_id, "identity": identity,
            "clips": [{"clip_id": "clip", "raw_hypothesis": hypothesis, "status": "ok"}],
        })
    (workspace / "report.json").write_text(json.dumps({"candidates": candidates}))
    output = tmp_path / "public" / "nested" / "review.html"

    build_review(workspace, corpus, output)

    html = output.read_text()
    relative = __import__("re").search(r'"audio":\s*"([^"]+)"', html).group(1)
    assert (output.parent / relative).resolve() == audio.resolve()
    assert "secret-model-small" not in html
    assert "secret-model-large" not in html
    mapping = json.loads((workspace / "review-map.json").read_text())
    assert set(mapping["systems"].values()) == {"secret-model-small", "secret-model-large"}
