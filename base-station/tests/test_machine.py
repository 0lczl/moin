import argparse
import json
import wave
import threading
from pathlib import Path

import pytest

import moin_machine.machine as machine
from moin_machine.machine import MachineCancelled, MachineError, run_machine

COMMIT = "a" * 40


def candidate():
    return {"id": "test", "name": "Test", "adapter": "baseline", "asr": {"model": "org/asr", "revision": COMMIT}, "translation": {"model": "org/mt", "revision": COMMIT}, "settings": {}, "prompts": {"en": "", "fr": ""}}


def renderings():
    return {"schema_version": 1, "detection_ready": True, "renderings": [{"arabic": "الحمد لله رب العالمين", "english": {"text": "All praise is due to God", "source": "approved", "version": "1", "approved": True}, "french": {"text": "Louange à Dieu", "source": "approved", "version": "1", "approved": True}}]}


def wav(path: Path, frames=16000):
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 16000, frames, "NONE", "not compressed"))
        stream.writeframes(b"\0\0" * frames)


def inputs(tmp_path):
    audio, config, registry = tmp_path / "recording.wav", tmp_path / "candidate.json", tmp_path / "renderings.json"
    wav(audio)
    config.write_text(json.dumps(candidate()))
    registry.write_text(json.dumps(renderings(), ensure_ascii=False))
    return audio, config, registry


def args(audio, config, registry, output, say=False):
    return argparse.Namespace(audio=audio, config=config, candidate=None, renderings=registry, out=output, segment_seconds=30, say=say)


def copy_canonical(source, destination):
    Path(destination).write_bytes(Path(source).read_bytes())


def test_quran_is_guarded_before_translation_and_may_use_approved_speech(tmp_path):
    audio, config, registry = inputs(tmp_path)
    called = []

    def process(_config, _audio, *, translation_guard):
        guard = translation_guard("الحمد لله رب العالمين")
        assert guard == {"en": "All praise is due to God", "fr": "Louange à Dieu"}
        return {"arabic": "الحمد لله رب العالمين", "en": guard["en"], "fr": guard["fr"], "uncertainty": None, "failure": None, "timing_ms": {}}

    result = run_machine(args(audio, config, registry, tmp_path / "run", say=True), process=process, canonicalizer=copy_canonical, speaker=lambda *_: called.append(True) or {"status": "failed", "provider": "elevenlabs", "code": "fixture", "message": "fixture"})
    assert result["segments"][0]["safety"]["outcome"] == "quran_rendering"
    assert len(called) == 2
    assert result["segments"][0]["synthesis"] == {"en": {"status": "failed", "provider": "elevenlabs", "code": "fixture", "message": "fixture"}, "fr": {"status": "failed", "provider": "elevenlabs", "code": "fixture", "message": "fixture"}}
    assert result["synthesis"]["voices"] == {"en": "Q2DodP8VbBgCc0KBzBTw", "fr": "O2TxFmt2yYpiOSygumnt"}
    assert "All praise is due" in (tmp_path / "run" / "en.txt").read_text()


def test_withheld_text_is_never_passed_to_speech(tmp_path):
    audio, config, registry = inputs(tmp_path)
    spoken = []

    def process(_config, _audio, *, translation_guard):
        guard = translation_guard("الحمد لله رب العالمين كلام")
        assert guard == {"uncertainty": "possible_quran_or_mixed_speech"}
        return {"arabic": "الحمد لله رب العالمين كلام", "en": "unsafe", "fr": "dangereux", "uncertainty": guard["uncertainty"], "failure": None, "timing_ms": {}}

    result = run_machine(args(audio, config, registry, tmp_path / "run", say=True), process=process, canonicalizer=copy_canonical, speaker=lambda *x: spoken.append(x) or True)
    assert result["segments"][0]["safety"]["outcome"] == "withheld"
    assert result["segments"][0]["safety"]["reason"] == "candidate_uncertainty"
    assert not spoken
    assert (tmp_path / "run" / "en.txt").read_text() == "\n"


def test_rejects_existing_output_without_touching_it(tmp_path):
    audio, config, registry = inputs(tmp_path)
    output = tmp_path / "run"
    output.mkdir()
    marker = output / "keep"
    marker.write_text("keep")
    with pytest.raises(MachineError, match="new directory"):
        run_machine(args(audio, config, registry, output), canonicalizer=copy_canonical)
    assert marker.read_text() == "keep"


def test_candidate_failure_is_recorded_and_withheld(tmp_path):
    audio, config, registry = inputs(tmp_path)

    def failed(*_, **__):
        return {"arabic": "", "en": "unsafe partial", "fr": "partial dangereux", "uncertainty": None, "failure": {"code": "candidate_failed"}, "timing_ms": {}}

    result = run_machine(args(audio, config, registry, tmp_path / "run"), process=failed, canonicalizer=copy_canonical)
    assert result["segments"][0]["safety"]["reason"] == "candidate_failure"
    assert (tmp_path / "run" / "en.txt").read_text() == "\n"
    assert "unsafe partial" not in (tmp_path / "run" / "index.html").read_text()
    stored = json.loads((tmp_path / "run" / "result.json").read_text())
    assert stored["source"]["format"] == "mono 16 kHz PCM16 WAV"


def test_cli_returns_nonzero_and_reports_failure_counts(monkeypatch, capsys, tmp_path):
    record = {"segments": [{"result": {"failure": {"code": "candidate_failed"}}, "safety": {"outcome": "withheld"}}]}
    monkeypatch.setattr(machine, "run_machine", lambda _args: record)
    code = machine.main(["--audio", "a.wav", "--config", "c.json", "--renderings", "r.json", "--out", str(tmp_path / "run")])
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["failures"] == 1
    assert report["withheld"] == 1
    assert report["translated"] == 0


def test_machine_generates_independent_languages_concurrently_and_records_timings(tmp_path):
    audio, config, registry = inputs(tmp_path)
    gate = threading.Barrier(2, timeout=1)
    progress = []

    def process(_config, _audio, *, translation_guard):
        assert translation_guard("حديث عادي") is None
        return {"arabic": "حديث عادي", "en": "Teaching", "fr": "Enseignement", "uncertainty": None, "failure": None, "timing_ms": {"model_load": 1, "asr": 2, "en": 3, "fr": 4, "translation_wall": 4, "total": 7}}

    def speaker(_text, language, destination):
        gate.wait()
        destination.write_bytes(language.encode())
        return {"status": "created", "provider": "fixture", "file": destination.name, "timing_ms": 5}

    result = run_machine(args(audio, config, registry, tmp_path / "run", say=True), process=process, canonicalizer=copy_canonical, speaker=speaker, progress_callback=progress.append)
    segment = result["segments"][0]
    assert list(segment["synthesis"]) == ["en", "fr"]
    assert segment["synthesis_wall_ms"] >= 0
    assert set(result["timing_ms"]) == {"canonicalize", "segmenting", "processing", "artifacts", "total"}
    finished = {(event.get("stage"), event.get("current_segment"), event.get("segment_count"))
                for event in progress if event["event"] == "stage_finished"}
    assert ("canonicalize", None, None) in finished
    assert all((stage, 1, 1) in finished for stage in ("safety_pre_translation", "asr", "translation", "safety_final", "tts"))
    assert any(event["event"] == "segment_finished" and event["current_segment"] == 1 for event in progress)


def test_final_safety_reuses_pre_translation_classification(tmp_path, monkeypatch):
    audio, config, registry = inputs(tmp_path)
    original_route = machine.safety.route
    route_calls = []

    def counting_route(*values):
        route_calls.append(values[0])
        return original_route(*values)

    monkeypatch.setattr(machine.safety, "route", counting_route)

    def process(_config, _audio, *, translation_guard):
        assert translation_guard("حديث عادي") is None
        return {"arabic": "حديث عادي", "en": "Teaching", "fr": "Enseignement", "uncertainty": None, "failure": None, "timing_ms": {}}

    result = run_machine(args(audio, config, registry, tmp_path / "run"), process=process, canonicalizer=copy_canonical)
    assert route_calls == ["حديث عادي"]
    assert result["segments"][0]["safety"]["en"] == "Teaching"
    assert result["segments"][0]["safety"]["fr"] == "Enseignement"


def test_cancelled_machine_removes_partial_output(tmp_path):
    audio, config, registry = inputs(tmp_path)
    output = tmp_path / "run"
    with pytest.raises(MachineCancelled):
        run_machine(args(audio, config, registry, output), canonicalizer=copy_canonical, should_cancel=lambda: True)
    assert not output.exists()
