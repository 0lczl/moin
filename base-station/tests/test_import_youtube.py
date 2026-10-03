from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path

import pytest

from tools import import_youtube


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/shorts/dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://youtube.com/shorts/dQw4w9WgXcQ?si=shared",
])
def test_canonical_supported_urls(url):
    assert import_youtube.canonical_url(url) == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ",
    )


@pytest.mark.parametrize("url, message", [
    ("http://youtube.com/watch?v=dQw4w9WgXcQ", "public HTTPS"),
    ("https://user:secret@youtube.com/watch?v=dQw4w9WgXcQ", "without credentials"),
    ("https://127.0.0.1/watch?v=dQw4w9WgXcQ", "public HTTPS"),
    ("https://youtube.com/watch?v=dQw4w9WgXcQ&list=PL123", "playlists"),
])
def test_rejects_noncanonical_or_unsafe_urls(url, message):
    with pytest.raises(ValueError, match=message):
        import_youtube.canonical_url(url)


def _mock_tools(monkeypatch, tmp_path, *, live=False, fail_download=False):
    downloader = tmp_path / "yt-dlp"
    downloader.write_text("fixture")
    monkeypatch.setattr(import_youtube.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    calls = []

    def run(command):
        calls.append(command)
        if "--dump-single-json" in command:
            payload = {"id": "dQw4w9WgXcQ", "title": " A\n title ", "uploader": "Uploader", "channel_id": "UCofficial", "is_live": live, "duration": 60}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if command[0] == str(downloader):
            if fail_download:
                raise subprocess.CalledProcessError(1, command)
            template = Path(command[command.index("-o") + 1])
            Path(str(template).replace("%(ext)s", "webm")).write_bytes(b"source")
            return subprocess.CompletedProcess(command, 0, "", "")
        with wave.open(command[-1], "wb") as audio:
            audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(bytes(320))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(import_youtube, "_run", run)
    return downloader, calls


def test_import_canonicalizes_audio_and_retains_only_sanitized_provenance(monkeypatch, tmp_path):
    downloader, calls = _mock_tools(monkeypatch, tmp_path)
    out = tmp_path / "new-import"
    import_youtube.import_video("https://youtu.be/dQw4w9WgXcQ", out, yt_dlp=downloader)

    assert sorted(path.name for path in out.iterdir()) == ["audio.wav", "metadata.json"]
    assert calls[0] == [str(downloader), "--no-playlist", "--skip-download", "--dump-single-json", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    assert calls[1][0] == str(downloader) and "--no-playlist" in calls[1]
    assert calls[2][0] == "/usr/bin/ffmpeg"
    assert [calls[2][calls[2].index(flag) + 1] for flag in ("-ac", "-ar", "-c:a")] == ["1", "16000", "pcm_s16le"]
    metadata = json.loads((out / "metadata.json").read_text())
    assert metadata["title"] == "A title"
    assert metadata["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert metadata["channel_id"] == "UCofficial"
    assert metadata["audio_sha256"] == hashlib.sha256((out / "audio.wav").read_bytes()).hexdigest()
    assert set(metadata) == {"source_url", "title", "uploader", "channel_id", "video_id", "retrieved_at", "audio_sha256"}


def test_live_url_is_rejected_before_download_with_actionable_message(monkeypatch, tmp_path):
    downloader, calls = _mock_tools(monkeypatch, tmp_path, live=True)
    out = tmp_path / "live"
    with pytest.raises(ValueError, match="completed recorded video"):
        import_youtube.import_video("https://youtu.be/dQw4w9WgXcQ", out, yt_dlp=downloader)
    assert len(calls) == 1
    assert not out.exists()


def test_failed_download_cleans_temporary_output(monkeypatch, tmp_path):
    downloader, _ = _mock_tools(monkeypatch, tmp_path, fail_download=True)
    out = tmp_path / "failed"
    with pytest.raises(subprocess.CalledProcessError):
        import_youtube.import_video("https://youtu.be/dQw4w9WgXcQ", out, yt_dlp=downloader)
    assert not out.exists()
    assert not list(tmp_path.glob(".failed-*"))


def test_existing_destination_is_never_overwritten(monkeypatch, tmp_path):
    out = tmp_path / "existing"
    out.mkdir()
    marker = out / "keep"
    marker.write_text("unchanged")
    with pytest.raises(FileExistsError, match="already exists"):
        import_youtube.import_video("https://youtu.be/dQw4w9WgXcQ", out)
    assert marker.read_text() == "unchanged"


def test_duration_limit_rejects_a_long_recording_before_download(monkeypatch, tmp_path):
    downloader, calls = _mock_tools(monkeypatch, tmp_path)

    def run(command):
        if "--dump-single-json" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps({"id": "dQw4w9WgXcQ", "duration": 301}), "")
        raise AssertionError("download must not begin")

    monkeypatch.setattr(import_youtube, "_run", run)
    with pytest.raises(ValueError, match="no longer than 5 minutes"):
        import_youtube.import_video("https://youtu.be/dQw4w9WgXcQ", tmp_path / "long", yt_dlp=downloader, max_duration_seconds=300)
    assert len(calls) == 0
