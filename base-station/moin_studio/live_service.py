"""Sequential live-audio worker, separate from recorded Studio jobs."""
from __future__ import annotations

from pathlib import Path
import queue
import re
import shutil
import threading
import time
from typing import Callable

from moin_studio.live_room import RoomEnded, RoomStore
from moin_studio.live_segment import LiveSegmentProcessor


MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_PENDING_SEGMENTS = 3
MEDIA_SUFFIXES = {"audio/webm": ".webm", "audio/mp4": ".mp4", "audio/ogg": ".ogg"}
RETENTION_SECONDS = 7 * 24 * 3600


class LiveQueueFull(ValueError):
    pass


class LiveService:
    def __init__(self, root: Path, rooms: RoomStore,
                 processor_factory: Callable[[], LiveSegmentProcessor] = LiveSegmentProcessor):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.rooms = rooms
        self.processor_factory = processor_factory
        self.processor = None
        self.pending: queue.Queue[tuple[str, str, int, Path, str]] = queue.Queue(MAX_PENDING_SEGMENTS)
        self.lock = threading.Lock()
        self.next_index: dict[str, int] = {}
        self.cleanup()
        threading.Thread(target=self._work, name="moin-live-worker", daemon=True).start()
        threading.Thread(target=self._cleanup_loop, name="moin-live-cleanup", daemon=True).start()

    def _next_index(self, room_id: str) -> int:
        with self.lock:
            if room_id not in self.next_index:
                folder = self.root / room_id
                existing = [int(match[1]) for path in folder.glob("segment-*")
                            if (match := re.fullmatch(r"segment-(\d+)", path.name))]
                self.next_index[room_id] = max(existing, default=0) + 1
            index = self.next_index[room_id]
            self.next_index[room_id] += 1
            return index

    def submit(self, room_id: str, admin_secret: str, audio: bytes, content_type: str) -> int:
        self.rooms.authorize_admin(room_id, admin_secret)
        room = self.rooms.state(room_id)
        if room["status"] != "active":
            raise RoomEnded("This live room has ended.")
        mime = content_type.split(";", 1)[0].strip().lower()
        suffix = MEDIA_SUFFIXES.get(mime)
        if suffix is None:
            raise ValueError("Use WebM, MP4, or OGG microphone audio")
        if not 0 < len(audio) <= MAX_AUDIO_BYTES:
            raise ValueError("Microphone segment is empty or too large")
        if self.pending.full():
            raise LiveQueueFull("Live processing is behind; pause briefly and retry")
        index = self._next_index(room_id)
        folder = self.root / room_id / f"segment-{index:06d}"
        folder.mkdir(mode=0o700, parents=True, exist_ok=False)
        source = folder / f"source{suffix}"
        source.write_bytes(audio)
        try:
            self.pending.put_nowait((room_id, admin_secret, index, source, room["language"]))
        except queue.Full:
            source.unlink(missing_ok=True)
            folder.rmdir()
            raise LiveQueueFull("Live processing is behind; pause briefly and retry") from None
        self._event(room_id, admin_secret, index, "processing", {})
        return index

    def _event(self, room_id, admin_secret, index, phase, data):
        try:
            return self.rooms.append_segment(room_id, admin_secret, {
                "index": index, "phase": phase, **data,
            })
        except RoomEnded:
            # The administrator may end the room while a segment is in flight.
            return None

    def _work(self):
        while True:
            room_id, secret, index, source, language = self.pending.get()
            try:
                if self.processor is None:
                    self.processor = self.processor_factory()
                output = source.parent / "output"

                def publish(phase, result):
                    safe = {key: result[key] for key in
                            ("arabic", "translation", "language", "safety", "sources", "audio_status", "timing_ms")
                            if key in result}
                    if phase == "audio" and result.get("audio_status") == "ready":
                        safe["audio_url"] = f"/api/live/rooms/{room_id}/audio/{index}"
                    self._event(room_id, secret, index, phase, safe)

                self.processor.process(source, language, output, publish)
            except Exception:
                # A provider failure must not reveal audio, credentials, or
                # exception detail to listeners; the next segment can proceed.
                self._event(room_id, secret, index, "error", {
                    "message": "This segment could not be prepared. Please try again."
                })
            finally:
                self.pending.task_done()

    def audio(self, room_id: str, index: int) -> Path:
        if index < 1:
            raise ValueError("Invalid segment")
        folder = self.root / room_id / f"segment-{index:06d}" / "output"
        path = folder / "speech-en.mp3"
        if not path.is_file():
            path = folder / "speech-fr.mp3"
        if not path.is_file():
            raise FileNotFoundError("Speech is not available")
        return path

    def cleanup(self, *, now=None) -> int:
        cutoff = (time.time() if now is None else now) - RETENTION_SECONDS
        removed = 0
        for folder in self.root.iterdir():
            if folder.is_dir() and folder.stat().st_mtime < cutoff:
                shutil.rmtree(folder)
                removed += 1
        self.rooms.cleanup(now=now)
        return removed

    def _cleanup_loop(self):
        while True:
            time.sleep(3600)
            self.cleanup()
