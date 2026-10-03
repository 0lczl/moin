"""Corpus and evidence storage. No provider dependencies or network calls."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import re
import wave
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class BenchmarkError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise BenchmarkError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise BenchmarkError(f"Cannot read valid JSON: {Path(path).name}") from None


def write_new(path, value):
    """Publish a complete JSON record atomically, without replacing an existing one."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise BenchmarkError(f"Immutable record already exists: {path.name}") from None
    finally:
        Path(temporary).unlink(missing_ok=True)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', value), 'Invalid identifier')
    return value


def secret_free(value):
    """Reject secret-bearing metadata; environment variable names are allowed."""
    if isinstance(value, dict):
        for key, item in value.items():
            require(not re.search(r'password|authorization|api[_-]?key|access[_-]?token|secret|credential', key, re.I)
                    or key.endswith('_env'), 'Credentials must be environment references only')
            secret_free(item)
    elif isinstance(value, list):
        for item in value:
            secret_free(item)
    elif isinstance(value, str):
        require(not re.search(r'Bearer\s+|sk-[A-Za-z0-9_-]{12,}|https?://[^/\s]+@', value), 'Secret-like metadata rejected')


TAGS = {'ordinary-teaching', 'islamic-terminology', 'natural-fast-speech', 'quran-adjacent'}


def corpus_counts(root):
    """Explicit profile; absent file preserves the original held-out protocol."""
    path = Path(root) / 'protocol.json'
    if not path.exists():
        return {'development': 12, 'final': 20}
    profile = read(path)
    require(profile == {'mode': 'nine-clip-comparison'}, 'Unsupported corpus protocol')
    return {'development': 9, 'final': 0}


def require_split(root, split):
    counts = corpus_counts(root)
    require(split in counts, 'Unknown split')
    require(counts[split] > 0, 'Nine-clip comparison has no separate final set')
    return counts[split]


def registry(root):
    clips = read(Path(root) / 'corpus.json')
    require(isinstance(clips, list), 'Corpus must be an array')
    ids, hashes, intervals = set(), set(), []
    for clip in clips:
        require(isinstance(clip, dict), 'Invalid clip record')
        cid = identifier(clip.get('id'))
        require(cid not in ids, 'Duplicate clip ID or split membership')
        ids.add(cid)
        require(clip.get('split') in ('development', 'final'), 'Invalid split')
        sha = clip.get('sha256', '')
        require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'Canonical audio SHA256 required')
        require(sha not in hashes, 'Duplicate audio across corpus')
        hashes.add(sha)
        for key in ('audio', 'speaker', 'source', 'source_start_seconds', 'duration_seconds', 'permission', 'tags', 'transcript'):
            require(key in clip, f'{cid}: missing {key}')
        require(isinstance(clip['speaker'], str) and clip['speaker'].strip(), f'{cid}: speaker required')
        require(isinstance(clip['source'], dict) and all(clip['source'].get(k) for k in ('uri', 'title', 'retrieved_at')), f'{cid}: incomplete provenance')
        perm = clip['permission']
        require(isinstance(perm, dict) and perm.get('decision') == 'permitted' and all(perm.get(k) for k in ('basis', 'reviewer', 'date')), f'{cid}: permitted-use decision required')
        require(isinstance(clip['duration_seconds'], (int, float)) and math.isfinite(clip['duration_seconds']) and clip['duration_seconds'] > 0, f'{cid}: invalid duration')
        require(isinstance(clip['source_start_seconds'], (int,float)) and math.isfinite(clip['source_start_seconds']) and clip['source_start_seconds'] >= 0, f'{cid}: invalid source offset')
        require(isinstance(clip['tags'], list) and (clip['tags'] or clip['split'] == 'final') and set(clip['tags']) <= TAGS, f'{cid}: invalid domain tags')
        t = clip['transcript']
        require(isinstance(t, dict) and t.get('state') in ('draft', 'verified'), f'{cid}: invalid transcript state')
        if clip['split'] == 'development' or t['state'] == 'verified':
            require(t.get('state') == 'verified' and all(t.get(k) for k in ('text', 'reviewer', 'date')), f'{cid}: human-verified transcript required')
        for uri, start, end in intervals:
            require(uri != clip['source']['uri'] or clip['source_start_seconds'] >= end or clip['source_start_seconds'] + clip['duration_seconds'] <= start,
                    f'{cid}: overlapping excerpts from the same source')
        intervals.append((clip['source']['uri'], clip['source_start_seconds'], clip['source_start_seconds'] + clip['duration_seconds']))
        secret_free(clip)
    return clips


def validate_corpus(root, split, *, final_allowed=False):
    expected = require_split(root, split)
    require(split != 'final' or final_allowed, 'Final access requires the frozen Moin composition')
    clips = [c for c in registry(root) if c['split'] == split]
    require(len(clips) == expected, f'{split} requires exactly {expected} clips')
    if split == 'development':
        require(len({c['speaker'] for c in clips}) >= 3, 'Development requires at least three speakers')
        require(set().union(*(set(c['tags']) for c in clips)) >= TAGS, 'Development lacks required categories')
    for c in clips:
        audio_path(root, c)
    return clips


def audio_path(root, clip):
    root = Path(root).resolve()
    p = (root / clip['audio']).resolve()
    require(p.is_relative_to(root), 'Audio must be inside the corpus directory')
    try:
        require(hashlib.sha256(p.read_bytes()).hexdigest() == clip['sha256'], 'Canonical audio hash mismatch')
        with wave.open(str(p), 'rb') as w:
            require((w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype()) == (1, 2, 16000, 'NONE'), 'Audio must be mono 16kHz PCM16 WAV')
            require(abs(w.getnframes()/16000 - clip['duration_seconds']) < .02, 'Audio duration mismatch')
    except (OSError, wave.Error):
        raise BenchmarkError('Canonical audio is missing or invalid') from None
    return p


@contextmanager
def exclusive(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = root / '.busy'
    try:
        lock.mkdir()
    except FileExistsError:
        raise BenchmarkError('Another operator command is running; inspect .busy if a process crashed') from None
    try:
        yield
    finally:
        lock.rmdir()
