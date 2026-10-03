import json
from pathlib import Path

import pytest

from moin_translation_benchmark import runner


def google_candidate():
    return runner.load_candidates(Path(__file__).parents[1] / "benchmark-data" / "translation-candidates.json")["google-cloud-nmt"].copy()


def test_google_adapter_posts_only_text_with_arabic_source_and_target(monkeypatch):
    candidate = google_candidate()
    candidate["settings"] = {**candidate["settings"], "project_env": "MOIN_TEST_PROJECT"}
    monkeypatch.setenv("MOIN_TEST_PROJECT", "test-project")
    captured = {}

    def post(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return b'{"translations":[{"translatedText":"Faithful result"}]}'

    result = runner._google_translate(candidate, "نص عربي", "fr", token_provider=lambda: "fake-token", post=post)
    assert result == "Faithful result"
    assert captured["url"] == "https://translation.googleapis.com/v3/projects/test-project/locations/global:translateText"
    assert captured["body"] == {
        "contents": ["نص عربي"], "mimeType": "text/plain", "sourceLanguageCode": "ar",
        "targetLanguageCode": "fr", "model": "projects/test-project/locations/global/models/general/nmt",
    }
    assert captured["headers"]["Authorization"] == "Bearer fake-token"
    assert captured["headers"]["X-goog-user-project"] == "test-project"


def test_google_character_limit_fails_before_environment_or_credentials(monkeypatch):
    called = []
    monkeypatch.delenv("MOIN_TEST_PROJECT", raising=False)
    candidate = google_candidate()
    candidate["settings"] = {**candidate["settings"], "project_env": "MOIN_TEST_PROJECT"}
    with pytest.raises(ValueError, match="50,000"):
        runner._google_translate(candidate, "ا" * (runner.MAX_CHARACTERS + 1), "en", token_provider=lambda: called.append(True))
    assert called == []


def test_google_requires_server_project_before_credentials(monkeypatch):
    called = []
    monkeypatch.delenv("MOIN_TEST_PROJECT", raising=False)
    candidate = google_candidate()
    candidate["settings"] = {**candidate["settings"], "project_env": "MOIN_TEST_PROJECT"}
    with pytest.raises(RuntimeError, match="MOIN_TEST_PROJECT"):
        runner._google_translate(candidate, "كلمة", "en", token_provider=lambda: called.append(True))
    assert called == []


def test_google_pilot_cumulative_limit_preflights_before_any_translation(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    candidate = google_candidate()
    (workspace / "lock.json").write_text(json.dumps({"candidates": [candidate]}))
    clips = [{"id": f"dev-{i:02d}", "arabic": "ا" * 3_000} for i in range(9)]
    monkeypatch.setattr(runner, "frozen_texts", lambda _corpus: (clips, "a" * 64, "b" * 64))
    translated = []
    monkeypatch.setattr(runner, "translate_text", lambda *args: translated.append(args))
    monkeypatch.setenv("MOIN_GOOGLE_CLOUD_PROJECT", "test-project")

    with pytest.raises(runner.BenchmarkError, match="cumulative source characters.*No requests were made"):
        runner.run_candidate(workspace, "google-cloud-nmt", tmp_path)
    assert translated == []
    denial = json.loads((workspace / "runs" / "google-cloud-nmt-budget-denial.json").read_text())
    assert denial["planned_source_characters"] == 54_000


def test_google_candidate_rejects_bad_configuration():
    candidate = google_candidate()
    candidate["settings"] = {**candidate["settings"], "max_pilot_characters": 500_000}
    with pytest.raises(runner.BenchmarkError, match="50,000"):
        runner.validate_candidate(candidate)


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b'{}', b'{"translations":[]}',
                                  b'{"translations":[{"translatedText":" "}]}'])
def test_google_rejects_malformed_or_empty_response(monkeypatch, body):
    monkeypatch.setenv("MOIN_GOOGLE_CLOUD_PROJECT", "test-project")
    with pytest.raises(RuntimeError):
        runner._google_translate(google_candidate(), "عربي", "en", token_provider=lambda: "fake",
                                 post=lambda request, timeout: body)


def test_google_run_reuses_results_and_blocks_uncertain_attempt(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    candidate = google_candidate()
    (workspace / "lock.json").write_text(json.dumps({"candidates": [candidate]}))
    clips = [{"id": f"dev-{i:02d}", "arabic": "عربي"} for i in range(9)]
    monkeypatch.setattr(runner, "frozen_texts", lambda _corpus: (clips, "a" * 64, "b" * 64))
    monkeypatch.setenv("MOIN_GOOGLE_CLOUD_PROJECT", "test-project")
    calls = []
    monkeypatch.setattr(runner, "translate_text", lambda *args: calls.append(args) or "translated")
    monkeypatch.setattr(runner, "_google_token", lambda: "fake")
    first = runner.run_candidate(workspace, candidate["id"], tmp_path)
    assert len(calls) == 18
    assert runner.run_candidate(workspace, candidate["id"], tmp_path) == first
    assert len(calls) == 18
    first.unlink()
    assert runner.run_candidate(workspace, candidate["id"], tmp_path) == first
    assert len(calls) == 18
    first.unlink()
    (workspace / "attempts" / candidate["id"] / "dev-00-en.result.json").unlink()
    with pytest.raises(runner.BenchmarkError, match="Unresolved attempt"):
        runner.run_candidate(workspace, candidate["id"], tmp_path)
    assert len(calls) == 18


def test_google_failure_is_saved_and_stops_before_other_requests(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    candidate = google_candidate()
    (workspace / "lock.json").write_text(json.dumps({"candidates": [candidate]}))
    monkeypatch.setattr(runner, "frozen_texts", lambda _corpus: ([{"id": "dev-00", "arabic": "عربي"}], "a" * 64, "b" * 64))
    monkeypatch.setenv("MOIN_GOOGLE_CLOUD_PROJECT", "test-project")
    calls = []

    def fail(*args):
        calls.append(True)
        raise RuntimeError("Bearer sensitive-provider-detail")

    monkeypatch.setattr(runner, "translate_text", fail)
    monkeypatch.setattr(runner, "_google_token", lambda: "fake")
    with pytest.raises(runner.BenchmarkError, match="Saved failed result"):
        runner.run_candidate(workspace, candidate["id"], tmp_path)
    saved = (workspace / "attempts" / candidate["id"] / "dev-00-en.result.json").read_text()
    assert json.loads(saved)["status"] == "failed"
    assert "sensitive-provider-detail" not in saved
    with pytest.raises(runner.BenchmarkError, match="Saved failed result"):
        runner.run_candidate(workspace, candidate["id"], tmp_path)
    assert len(calls) == 1


def test_missing_google_credentials_fail_before_creating_an_attempt(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    candidate = google_candidate()
    (workspace / "lock.json").write_text(json.dumps({"candidates": [candidate]}))
    monkeypatch.setattr(runner, "frozen_texts", lambda _corpus: ([{"id": "dev-00", "arabic": "عربي"}], "a" * 64, "b" * 64))
    monkeypatch.setenv("MOIN_GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setattr(runner, "_google_token", lambda: (_ for _ in ()).throw(RuntimeError("sensitive detail")))
    with pytest.raises(runner.BenchmarkError, match="unavailable; no translation request was made"):
        runner.run_candidate(workspace, candidate["id"], tmp_path)
    assert not (workspace / "attempts").exists()


def test_frozen_texts_loads_nine_verified_texts_without_opening_audio():
    corpus = Path(__file__).parents[1] / "benchmark-data"
    clips, corpus_hash, source_hash = runner.frozen_texts(corpus)
    assert len(clips) == 9
    assert all(row["arabic"] for row in clips)
    assert len(corpus_hash) == 64
    assert len(source_hash) == 64


def test_review_package_anonymizes_candidate_names(tmp_path):
    workspace = tmp_path / "workspace"
    out = tmp_path / "review"
    candidates = [
        {"id": "candidate-a", "name": "System A secret", "adapter": "x", "model": "m1", "revision": "r1", "settings": {}},
        {"id": "candidate-b", "name": "System B secret", "adapter": "x", "model": "m2", "revision": "r2", "settings": {}},
    ]
    workspace.mkdir()
    (workspace / "lock.json").write_text(json.dumps({"candidates": candidates}))
    (workspace / "runs").mkdir()
    for c in candidates:
        record = {"candidate": c, "source_texts_sha256": "a" * 64,
                  "clips": [{"clip_id": "dev-01", "source_arabic": "عربي", "translations": {
            "en": {"text": "An English rendering", "status": "ok"},
            "fr": {"text": "Une traduction", "status": "ok"},
        }}]}
        (workspace / "runs" / f"{c['id']}.json").write_text(json.dumps(record))
    result = runner.create_review_package(workspace, out, seed=1)
    exported = result.read_text()
    assert "candidate-a" not in exported and "candidate-b" not in exported
    assert "System A secret" not in exported and "System B secret" not in exported
    assert len(json.loads(exported)["clips"]) == 2
    assert json.loads(exported)["allowed_judgments"] == list(runner.JUDGMENTS)
    with pytest.raises(runner.BenchmarkError, match="Incomplete or invalid judgment"):
        runner.check_review(result)
    filled = json.loads(exported)
    for item in filled["clips"]:
        for system in item["systems"]:
            system["judgment"] = "faithful"
    result.write_text(json.dumps(filled))
    assert runner.check_review(result) == {
        "en": {"faithful": 2, "partly_wrong": 0, "serious_meaning_error": 0},
        "fr": {"faithful": 2, "partly_wrong": 0, "serious_meaning_error": 0},
    }
    mapping = list((workspace / "private").glob("review-map-*.json"))
    assert len(mapping) == 1
    assert "candidate-a" in mapping[0].read_text() and "candidate-b" in mapping[0].read_text()
