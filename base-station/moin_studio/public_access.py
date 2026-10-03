"""Anonymous browser ownership and public start-job throttling helpers.

These helpers keep browser session capabilities separate from job responses.
They contain no HTTP routing; handlers can use ``read_session_cookie`` and
``session_cookie_header`` at the boundary, then persist ``owner_fingerprint``
on private job records.
"""
from __future__ import annotations

from collections import OrderedDict, deque
import hashlib
import hmac
import ipaddress
import math
import re
import secrets
import threading
import time
from http.cookies import SimpleCookie


SESSION_COOKIE_NAME = 'moin_session'
SESSION_TOKEN_BYTES = 32
SESSION_TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{43}$')
OWNER_FINGERPRINT_FIELD = 'owner_fingerprint'
DEFAULT_SESSION_MAX_AGE = 30 * 24 * 60 * 60
DEFAULT_START_LIMIT = 4
DEFAULT_START_WINDOW_SECONDS = 60 * 60
DEFAULT_MAX_TRACKED_IPS = 10_000


class RateLimitExceeded(ValueError):
    """The IP has used all start-job slots in the current window."""


def new_session_token():
    """Return a URL-safe browser capability containing 32 random bytes."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def _valid_session_token(token):
    if not isinstance(token, str) or not SESSION_TOKEN_RE.fullmatch(token):
        return False
    # A 43-character URL-safe encoding can represent 32 bytes; validate the
    # unused tail bits as well so there is one canonical token representation.
    try:
        import base64
        padded = token + '=' * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode('ascii'))
    except (ValueError, UnicodeEncodeError):
        return False
    return len(decoded) == SESSION_TOKEN_BYTES and base64.urlsafe_b64encode(decoded).decode('ascii').rstrip('=') == token


def session_fingerprint(session_token):
    """Return the SHA-256 owner fingerprint for a valid session token."""
    if not _valid_session_token(session_token):
        raise ValueError('session token is invalid')
    return hashlib.sha256(session_token.encode('ascii')).hexdigest()


def assign_job_owner(job, session_token):
    """Attach a private job's hashed owner fingerprint in place."""
    if not isinstance(job, dict):
        raise TypeError('job must be a dictionary')
    job[OWNER_FINGERPRINT_FIELD] = session_fingerprint(session_token)
    return job


def can_access(job, session_token):
    """Whether the session can read this job.

    Catalog-backed jobs are intentionally public for read access. Private jobs
    require a valid session whose fingerprint matches the stored owner hash.
    Use :func:`can_cancel` for mutation authorization.
    """
    if not isinstance(job, dict):
        return False
    if job.get('catalog_video_id') is not None:
        return True
    stored = job.get(OWNER_FINGERPRINT_FIELD)
    if not isinstance(stored, str) or not re.fullmatch(r'[0-9a-f]{64}', stored):
        return False
    if not _valid_session_token(session_token):
        return False
    candidate = hashlib.sha256(session_token.encode('ascii')).hexdigest()
    return hmac.compare_digest(stored, candidate)


def can_cancel(job, session_token):
    """Whether a session may cancel a private job.

    Public catalog jobs are read-only even if a job dictionary also happens to
    contain an owner fingerprint.
    """
    if not isinstance(job, dict) or job.get('catalog_video_id') is not None:
        return False
    return can_access(job, session_token)


def session_cookie_header(session_token, *, secure=True,
                          max_age=DEFAULT_SESSION_MAX_AGE,
                          name=SESSION_COOKIE_NAME):
    """Build a Set-Cookie value with HttpOnly, SameSite=Lax, and Secure."""
    if not _valid_session_token(session_token):
        raise ValueError('session token is invalid')
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name):
        raise ValueError('cookie name is invalid')
    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 0:
        raise ValueError('max_age must be a non-negative integer')
    cookie = SimpleCookie()
    cookie[name] = session_token
    morsel = cookie[name]
    morsel['path'] = '/'
    morsel['httponly'] = True
    morsel['samesite'] = 'Lax'
    morsel['max-age'] = str(max_age)
    if secure:
        morsel['secure'] = True
    return morsel.OutputString()


def read_session_cookie(cookie_header, *, name=SESSION_COOKIE_NAME):
    """Extract a validated session token from a Cookie header, else ``None``."""
    if not isinstance(cookie_header, str) or len(cookie_header) > 8192:
        return None
    if '\r' in cookie_header or '\n' in cookie_header:
        return None
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name):
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except (TypeError, ValueError):
        return None
    morsel = cookie.get(name)
    if morsel is None or not _valid_session_token(morsel.value):
        return None
    return morsel.value


class StartJobThrottle:
    """Thread-safe per-IP sliding-window limiter with bounded memory.

    ``allow`` records an accepted start and returns ``False`` once the limit is
    reached. It counts accepted starts, not rejected retries. When the bounded
    IP table fills, the least recently used IP bucket is evicted.
    """

    def __init__(self, *, limit=DEFAULT_START_LIMIT,
                 window_seconds=DEFAULT_START_WINDOW_SECONDS,
                 max_tracked_ips=DEFAULT_MAX_TRACKED_IPS, clock=time.time):
        for field, value in (('limit', limit), ('max_tracked_ips', max_tracked_ips)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f'{field} must be a positive integer')
        if isinstance(window_seconds, bool) or not isinstance(window_seconds, (int, float)):
            raise ValueError('window_seconds must be a positive finite number')
        if not math.isfinite(window_seconds) or window_seconds <= 0:
            raise ValueError('window_seconds must be a positive finite number')
        self.limit = limit
        self.window_seconds = float(window_seconds)
        self.max_tracked_ips = max_tracked_ips
        self.clock = clock
        self.lock = threading.Lock()
        self._starts = OrderedDict()

    def allow(self, ip, *, now=None):
        """Record a start for a valid IP and report whether it was accepted."""
        try:
            address = ipaddress.ip_address(ip)
        except (ValueError, TypeError):
            raise ValueError('ip must be a valid IPv4 or IPv6 address') from None
        key = address.compressed
        timestamp = float(self.clock() if now is None else now)
        if not math.isfinite(timestamp):
            raise ValueError('now must be finite')
        cutoff = timestamp - self.window_seconds
        with self.lock:
            starts = self._starts.get(key)
            if starts is None:
                if len(self._starts) >= self.max_tracked_ips:
                    self._starts.popitem(last=False)
                starts = deque()
                self._starts[key] = starts
            else:
                self._starts.move_to_end(key)
            while starts and starts[0] <= cutoff:
                starts.popleft()
            if len(starts) >= self.limit:
                return False
            starts.append(timestamp)
            return True

    def check(self, ip, *, now=None):
        """Record a start or raise :class:`RateLimitExceeded`."""
        if not self.allow(ip, now=now):
            raise RateLimitExceeded('Too many jobs started from this address. Try again later.')

    @property
    def tracked_ip_count(self):
        """Current bounded number of IP buckets (useful for diagnostics/tests)."""
        with self.lock:
            return len(self._starts)
