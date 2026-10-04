"""Small, private diagnostics for long-running Studio jobs.

Diagnostic writes are best-effort: a full disk or an unavailable log must not
change whether an otherwise valid recording can be processed.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
from typing import Iterator


class JobDiagnostics:
    """Append stage events without recording media, URLs, or exception text."""

    def __init__(self, path: Path):
        self.path = path
        self.stage_name: str | None = None
        self.failed_stage: str | None = None

    def record(self, event: str, **fields: object) -> None:
        row = {
            'timestamp': time.time(),
            'event': event,
            **fields,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(descriptor, 'a', encoding='utf-8') as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        except OSError:
            # Diagnostics must never take down the processing worker.
            return

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        self.stage_name = name
        started = time.perf_counter()
        self.record('stage_started', stage=name)
        try:
            yield
        except Exception as error:
            self.failed_stage = name
            self.record('stage_failed', stage=name,
                        duration_ms=round((time.perf_counter() - started) * 1000, 3),
                        error_type=type(error).__name__)
            raise
        else:
            self.record('stage_finished', stage=name,
                        duration_ms=round((time.perf_counter() - started) * 1000, 3))
        finally:
            self.stage_name = None
