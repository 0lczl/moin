#!/usr/bin/env python3
"""Import a recorded YouTube video as canonical benchmark audio.

Usage:
    python tools/import_youtube.py URL --out benchmark-data/imports/clip-name
    python tools/import_youtube.py URL --out DIR --yt-dlp /path/to/yt-dlp

The destination must not exist. The tool writes only ``audio.wav`` and a small
``metadata.json`` provenance record; yt-dlp's full metadata and signed media
URLs are never persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit


_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def canonical_url(value: str) -> tuple[str, str]:
    """Validate a supported recorded-video URL and return canonical URL/id."""
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValueError("invalid YouTube URL") from exc
    if parsed.scheme != "https" or parsed.hostname not in _HOSTS or parsed.username or parsed.password or parsed.port:
        raise ValueError("URL must be a public HTTPS youtube.com or youtu.be video URL without credentials")
    if parsed.fragment:
        raise ValueError("URL fragments are unsupported")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if "list" in query:
        raise ValueError("playlists are unsupported; provide one recorded video URL")
    if set(query) - {"v", "si", "feature"}:
        raise ValueError("unsupported YouTube URL parameters")

    if parsed.hostname == "youtu.be":
        video_id = parsed.path.removeprefix("/")
        if "/" in video_id or "v" in query:
            raise ValueError("use a canonical youtu.be/VIDEO_ID URL without extra parameters")
    elif parsed.path == "/watch":
        query = parse_qs(parsed.query, keep_blank_values=True)
        if "v" not in query or len(query["v"]) != 1:
            if "list" in query:
                raise ValueError("playlists are unsupported; provide one recorded video URL")
            raise ValueError("use a canonical youtube.com/watch?v=VIDEO_ID URL")
        video_id = query["v"][0]
    elif parsed.path.startswith("/shorts/") and "v" not in query:
        parts = parsed.path.split("/")
        video_id = parts[2] if len(parts) == 3 else ""
    else:
        raise ValueError("supported forms are youtube.com/watch?v=ID, youtube.com/shorts/ID, and youtu.be/ID")
    if not _VIDEO_ID.fullmatch(video_id):
        raise ValueError("YouTube video ID must be 11 URL-safe characters")
    return f"https://www.youtube.com/watch?v={video_id}", video_id


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join("".join(" " if ord(char) < 32 or ord(char) == 127 else char for char in value).split())


def _metadata_text(value: Any) -> str:
    cleaned = _clean_text(value)
    return cleaned[:500]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    # A public job must not occupy the sole recorded worker indefinitely when
    # YouTube or a media decoder stalls. The duration is checked before download.
    if '--dump-single-json' in command:
        timeout = 45
    elif Path(command[0]).name == 'ffmpeg':
        timeout = 120
    else:
        timeout = 180
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)


def import_failure_code(error: Exception) -> str:
    """Return a safe, bounded category without exposing extractor output or URLs."""
    if isinstance(error, subprocess.TimeoutExpired):
        return "youtube_import_timeout"
    if isinstance(error, subprocess.CalledProcessError):
        detail = (error.stderr or "").lower()
        if "no supported javascript runtime" in detail or "yt-dlp-ejs" in detail:
            return "youtube_js_unavailable"
        if "sign in to confirm" in detail or "not a bot" in detail or "http error 403" in detail:
            return "youtube_access_blocked"
        if "requested format is not available" in detail or "no video formats found" in detail:
            return "youtube_audio_unavailable"
        command = error.cmd if isinstance(error.cmd, (list, tuple)) else [error.cmd]
        if command and Path(str(command[0])).name == "ffmpeg":
            return "audio_decode_failed"
        return "youtube_extraction_failed"
    if isinstance(error, (FileNotFoundError, PermissionError)):
        return "import_dependency_unavailable"
    if isinstance(error, ValueError):
        return "youtube_metadata_invalid"
    return "youtube_import_failed"


def import_video(url: str, out: Path, *, yt_dlp: Path | None = None, max_duration_seconds: int | None = None) -> Path:
    canonical, expected_id = canonical_url(url)
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"destination already exists: {out}")
    if not out.parent.is_dir():
        raise FileNotFoundError(f"destination parent does not exist: {out.parent}")
    if max_duration_seconds is not None and (isinstance(max_duration_seconds, bool) or not isinstance(max_duration_seconds, int) or max_duration_seconds < 1):
        raise ValueError("max_duration_seconds must be a positive integer")

    bundled = Path(sys.executable).with_name("yt-dlp")
    executable = str(yt_dlp) if yt_dlp is not None else (str(bundled) if bundled.is_file() else shutil.which("yt-dlp"))
    if not executable:
        raise FileNotFoundError("yt-dlp was not found; install it or pass --yt-dlp /path/to/yt-dlp")
    if yt_dlp is not None and not Path(yt_dlp).is_file():
        raise FileNotFoundError(f"yt-dlp executable does not exist: {yt_dlp}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg was not found on PATH")

    temporary = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        probe = _run([executable, "--no-playlist", "--skip-download", "--dump-single-json", canonical])
        info = json.loads(probe.stdout)
        if not isinstance(info, dict) or info.get("id") != expected_id:
            raise ValueError("yt-dlp returned unexpected video metadata")
        if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
            raise ValueError("live and upcoming URLs are unsupported; provide a completed recorded video")
        duration = info.get("duration")
        if max_duration_seconds is not None and (not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0 or duration > max_duration_seconds):
            raise ValueError(f"video must be a completed recording no longer than {max_duration_seconds // 60} minutes")

        _run([
            executable, "--no-playlist", "--no-progress", "--no-write-info-json",
            "--no-write-playlist-metafiles", "-f", "bestaudio", "-o",
            str(temporary / "source.%(ext)s"), canonical,
        ])
        sources = [path for path in temporary.glob("source.*") if path.is_file()]
        if len(sources) != 1:
            raise RuntimeError("yt-dlp did not produce exactly one audio file")
        audio = temporary / "audio.wav"
        _run([
            ffmpeg, "-nostdin", "-v", "error", "-i", str(sources[0]),
            "-map_metadata", "-1", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio),
        ])
        if not audio.is_file() or not audio.stat().st_size:
            raise RuntimeError("ffmpeg did not produce canonical audio")
        with wave.open(str(audio), "rb") as canonical_audio:
            if (canonical_audio.getnchannels(), canonical_audio.getsampwidth(), canonical_audio.getframerate(), canonical_audio.getcomptype()) != (1, 2, 16000, "NONE") or canonical_audio.getnframes() == 0:
                raise ValueError("ffmpeg did not produce mono 16kHz PCM16 audio")
        sources[0].unlink()
        metadata = {
            "source_url": canonical,
            "title": _metadata_text(info.get("title")),
            "uploader": _metadata_text(info.get("uploader")),
            "channel_id": _metadata_text(info.get("channel_id")),
            "video_id": expected_id,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
        }
        (temporary / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        temporary.rename(out)
        return out
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="canonical URL of a completed recorded YouTube video")
    parser.add_argument("--out", required=True, type=Path, help="new destination directory")
    parser.add_argument("--yt-dlp", type=Path, help="explicit yt-dlp executable path")
    args = parser.parse_args(argv)
    try:
        imported = import_video(args.url, args.out, yt_dlp=args.yt_dlp)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(imported)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
