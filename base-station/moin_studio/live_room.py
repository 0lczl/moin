"""Durable state for one live mosque translation room.

This module deliberately owns no HTTP, microphone, ASR, or translation code.
``RoomStore`` is the small persistence boundary used by the future live-room
routes in :mod:`moin_studio.server`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time


ROOM_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_LISTENERS = 50
ROOM_ID_BYTES = 18  # token_urlsafe produces a 24-character identifier
MANAGEMENT_SECRET_BYTES = 32


class LiveRoomError(Exception):
    """Base class for expected room operation failures."""


class ActiveRoomExists(LiveRoomError):
    """A live room is already active."""


class RoomNotFound(LiveRoomError):
    """The requested room is missing or has expired."""


class RoomEnded(LiveRoomError):
    """The requested room has ended."""


class RoomFull(LiveRoomError):
    """The room already has its maximum number of listeners."""


class ListenerNotFound(LiveRoomError):
    """The listener is not currently in the room."""


class InvalidManagementSecret(LiveRoomError):
    """The supplied management capability does not authorize this action."""


class RoomStore:
    """Persist one globally active room and recent archived room logs.

    ``root`` is a directory; state is stored in ``live-room.json``. The
    management secret is returned only by :meth:`create_room`; only its SHA-256
    digest is written to disk. Timestamps are Unix seconds and event sequence
    numbers start at one for each room.
    """

    def __init__(self, root, *, max_listeners=MAX_LISTENERS,
                 ttl_seconds=ROOM_TTL_SECONDS, max_active_seconds=60 * 60,
                 clock=time.time):
        if max_listeners < 1:
            raise ValueError('max_listeners must be positive')
        if ttl_seconds < 1:
            raise ValueError('ttl_seconds must be positive')
        if max_active_seconds < 1:
            raise ValueError('max_active_seconds must be positive')
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass
        self.path = self.root / 'live-room.json'
        self.max_listeners = int(max_listeners)
        self.ttl_seconds = int(ttl_seconds)
        self.max_active_seconds = int(max_active_seconds)
        self.clock = clock
        self.lock = threading.RLock()
        state = self._read()
        self._rooms = state['rooms']
        self._active_room_id = state['active_room_id']

    def _read(self):
        try:
            document = json.loads(self.path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return {'rooms': {}, 'active_room_id': None}
        except (OSError, ValueError) as exc:
            raise RuntimeError(f'Could not read live room state at {self.path}') from exc
        if not isinstance(document, dict) or document.get('version') != 1:
            raise RuntimeError(f'Unsupported live room state at {self.path}')
        # Accept the early single-room shape so an upgrade preserves an
        # existing room and its event history.
        if 'rooms' not in document:
            room = document.get('room')
            if room is not None and not isinstance(room, dict):
                raise RuntimeError(f'Invalid live room state at {self.path}')
            rooms = {room['id']: room} if room else {}
            active_id = room['id'] if room and room['ended_at'] is None else None
            return {'rooms': rooms, 'active_room_id': active_id}
        rooms = document.get('rooms')
        active_id = document.get('active_room_id')
        if not isinstance(rooms, dict) or (active_id is not None and active_id not in rooms):
            raise RuntimeError(f'Invalid live room state at {self.path}')
        return {'rooms': rooms, 'active_room_id': active_id}

    def _write(self):
        document = {
            'version': 1,
            'rooms': self._rooms,
            'active_room_id': self._active_room_id,
        }
        fd, temp_name = tempfile.mkstemp(prefix='.live-room-', suffix='.tmp', dir=self.root)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(document, stream, ensure_ascii=False, separators=(',', ':'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
            try:
                directory_fd = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                # Some filesystems do not permit syncing directories.
                pass
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _now(self, now):
        return float(self.clock() if now is None else now)

    def _public(self, room):
        return {
            'id': room['id'],
            'name': room['name'],
            'language': room['language'],
            'created_at': room['created_at'],
            'expires_at': room['expires_at'],
            'ended_at': room['ended_at'],
            'active': room['ended_at'] is None,
            'status': 'active' if room['ended_at'] is None else 'ended',
            'listener_count': len(room['listeners']),
        }

    def _require_room(self, room_id, *, active=False, now=None):
        timestamp = self._now(now)
        self._expire_active_locked(timestamp)
        room = self._rooms.get(room_id)
        if room is None or room['expires_at'] <= timestamp:
            raise RoomNotFound('This live room does not exist or has expired.')
        if active and room['ended_at'] is not None:
            raise RoomEnded('This live room has ended.')
        return room

    @staticmethod
    def _append_event(room, event_type, timestamp, **details):
        seq = room['next_event_seq']
        room['events'].append({'seq': seq, 'type': event_type, 'at': timestamp, **details})
        room['next_event_seq'] = seq + 1

    def create_room(self, name, language, *, now=None):
        """Create the sole active room; return ``(public_room, secret)``.

        The secret is an independent 32-byte random capability encoded as
        URL-safe text. It is never included in public room state or persisted.
        """
        name = str(name).strip()
        if not 1 <= len(name) <= 80:
            raise ValueError('Room name must contain between 1 and 80 characters.')
        if language not in {'en', 'fr'}:
            raise ValueError('Room language must be en or fr.')
        timestamp = self._now(now)
        with self.lock:
            self._cleanup_locked(timestamp)
            self._expire_active_locked(timestamp)
            if self._active_room_id is not None:
                raise ActiveRoomExists('A live room is already active.')
            secret = secrets.token_urlsafe(MANAGEMENT_SECRET_BYTES)
            room = {
                'id': secrets.token_urlsafe(ROOM_ID_BYTES),
                'name': name,
                'language': language,
                'management_secret_hash': hashlib.sha256(secret.encode('ascii')).hexdigest(),
                'created_at': timestamp,
                'expires_at': timestamp + self.ttl_seconds,
                'ended_at': None,
                'listeners': {},
                'events': [],
                'next_event_seq': 1,
            }
            self._append_event(room, 'room_created', timestamp)
            self._rooms[room['id']] = room
            self._active_room_id = room['id']
            self._write()
            return self._public(room), secret

    def join(self, room_id, *, now=None):
        """Join an active room and return its unguessable listener id."""
        timestamp = self._now(now)
        with self.lock:
            room = self._require_room(room_id, active=True, now=timestamp)
            if len(room['listeners']) >= self.max_listeners:
                raise RoomFull('This live room has reached its listener limit.')
            listener_id = secrets.token_urlsafe(24)
            listener_hash = hashlib.sha256(listener_id.encode('ascii')).hexdigest()
            room['listeners'][listener_hash] = timestamp
            self._append_event(room, 'listener_joined', timestamp)
            self._write()
            return listener_id

    def leave(self, room_id, listener_id, *, now=None):
        """Remove a listener and record the departure."""
        timestamp = self._now(now)
        with self.lock:
            room = self._require_room(room_id, now=timestamp)
            listener_hash = hashlib.sha256(str(listener_id).encode('utf-8')).hexdigest()
            if listener_hash not in room['listeners']:
                raise ListenerNotFound('This listener is not in the room.')
            del room['listeners'][listener_hash]
            self._append_event(room, 'listener_left', timestamp)
            self._write()
            return self._public(room)

    def end(self, room_id, management_secret, *, now=None):
        """End an active room after checking its management capability."""
        timestamp = self._now(now)
        with self.lock:
            room = self._require_room(room_id, active=True, now=timestamp)
            self._check_management_secret(room, management_secret)
            room['ended_at'] = timestamp
            self._append_event(room, 'room_ended', timestamp)
            self._active_room_id = None
            self._write()
            return self._public(room)

    @staticmethod
    def _check_management_secret(room, management_secret):
        supplied_hash = hashlib.sha256(str(management_secret).encode('utf-8')).hexdigest()
        if not hmac.compare_digest(supplied_hash, room['management_secret_hash']):
            raise InvalidManagementSecret('The management secret is invalid.')

    def authorize_admin(self, room_id, secret, *, now=None):
        """Validate an admin capability for an active or retained room."""
        timestamp = self._now(now)
        with self.lock:
            room = self._require_room(room_id, now=timestamp)
            self._check_management_secret(room, secret)
            return True

    def authorize_listener(self, room_id, listener_id, *, now=None):
        """Validate a listener capability while its room is active."""
        timestamp = self._now(now)
        with self.lock:
            room = self._require_room(room_id, active=True, now=timestamp)
            listener_hash = hashlib.sha256(str(listener_id).encode('utf-8')).hexdigest()
            if listener_hash not in room['listeners']:
                raise ListenerNotFound('This listener is not in the room.')
            return True

    def append_segment(self, room_id, admin_secret, segment, *, now=None):
        """Append a translated live segment as the next ordered room event.

        ``segment`` must be a JSON object prepared by the caller. The event
        store does not interpret transcript fields or call a provider.
        """
        if not isinstance(segment, dict):
            raise ValueError('segment must be a JSON object')
        try:
            # Copy and validate before changing durable state.
            payload = json.loads(json.dumps(segment, ensure_ascii=False))
        except (TypeError, ValueError) as exc:
            raise ValueError('segment must contain JSON-compatible values') from exc
        timestamp = self._now(now)
        with self.lock:
            room = self._require_room(room_id, active=True, now=timestamp)
            self._check_management_secret(room, admin_secret)
            self._append_event(room, 'segment', timestamp, segment=payload)
            self._write()
            return dict(room['events'][-1])

    def state(self, room_id=None, *, now=None):
        """Return sanitized state for ``room_id`` or the current room."""
        timestamp = self._now(now)
        with self.lock:
            if room_id is None:
                if self._active_room_id is None:
                    raise RoomNotFound('There is no current live room.')
                room = self._require_room(self._active_room_id, now=timestamp)
            else:
                room = self._require_room(room_id, now=timestamp)
            return self._public(room)

    def events(self, room_id, *, after=0, limit=100, listener_id=None,
               admin_secret=None, now=None):
        """Return events in sequence order, strictly after ``after``.

        ``limit`` is capped at 500 so an HTTP handler can safely expose this
        method without allowing unbounded responses. A valid listener may read
        only while the room is active; its admin capability can read retained
        events after the room ends.
        """
        if isinstance(after, bool) or int(after) < 0:
            raise ValueError('after must be a non-negative event sequence')
        if isinstance(limit, bool) or int(limit) < 1:
            raise ValueError('limit must be positive')
        after, limit = int(after), min(int(limit), 500)
        timestamp = self._now(now)
        with self.lock:
            if admin_secret is not None:
                room = self._require_room(room_id, now=timestamp)
                self._check_management_secret(room, admin_secret)
            elif listener_id is not None:
                room = self._require_room(room_id, active=True, now=timestamp)
                listener_hash = hashlib.sha256(str(listener_id).encode('utf-8')).hexdigest()
                if listener_hash not in room['listeners']:
                    raise ListenerNotFound('This listener is not in the room.')
            else:
                raise InvalidManagementSecret('A room capability is required to read events.')
            return [dict(event) for event in room['events'] if event['seq'] > after][:limit]

    def cleanup(self, *, now=None):
        """Delete every room record once its seven-day retention expires.

        Returns ``True`` when a room record was removed. ``create_room`` also
        performs this cleanup before enforcing the single-active-room rule.
        """
        timestamp = self._now(now)
        with self.lock:
            return self._cleanup_locked(timestamp)

    def _cleanup_locked(self, timestamp):
        expired = [room_id for room_id, room in self._rooms.items()
                   if room['expires_at'] <= timestamp]
        if not expired:
            return False
        for room_id in expired:
            del self._rooms[room_id]
            if room_id == self._active_room_id:
                self._active_room_id = None
        self._write()
        return True

    def _expire_active_locked(self, timestamp):
        """End an abandoned room after its short live lease, retaining history."""
        room_id = self._active_room_id
        if room_id is None:
            return False
        room = self._rooms.get(room_id)
        if room is None or room['created_at'] + self.max_active_seconds > timestamp:
            return False
        room['ended_at'] = timestamp
        room['end_reason'] = 'lease_expired'
        self._append_event(room, 'room_ended', timestamp, reason='lease_expired')
        self._active_room_id = None
        self._write()
        return True
