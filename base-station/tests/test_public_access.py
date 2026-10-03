"""Tests for anonymous session ownership and start-job throttling."""
from http.cookies import SimpleCookie

import pytest

from moin_studio.public_access import (
    OWNER_FINGERPRINT_FIELD,
    RateLimitExceeded,
    StartJobThrottle,
    assign_job_owner,
    can_access,
    can_cancel,
    new_session_token,
    read_session_cookie,
    session_cookie_header,
    session_fingerprint,
)


def test_private_job_is_owned_by_hashed_session_fingerprint():
    session = new_session_token()
    other = new_session_token()
    job = {'id': 'private-job'}

    assert len(session.encode()) >= 32
    assign_job_owner(job, session)
    assert job[OWNER_FINGERPRINT_FIELD] == session_fingerprint(session)
    assert session not in job[OWNER_FINGERPRINT_FIELD]
    assert can_access(job, session) is True
    assert can_cancel(job, session) is True
    assert can_access(job, other) is False
    assert can_cancel(job, other) is False
    assert can_access(job, None) is False


def test_catalog_jobs_are_public_for_read_but_never_cancellable():
    job = {'id': 'catalog-job', 'catalog_video_id': 'lesson-1'}
    assert can_access(job, None) is True
    assert can_access(job, 'forged') is True
    assert can_cancel(job, None) is False

    # Catalog identity takes precedence even if a job happens to carry owner data.
    owned_catalog_job = dict(job)
    owner = new_session_token()
    assign_job_owner(owned_catalog_job, owner)
    assert can_cancel(owned_catalog_job, owner) is False


@pytest.mark.parametrize('token', [None, '', 'short', 'a' * 43, 'x' * 44])
def test_forged_or_missing_session_tokens_cannot_access_private_jobs(token):
    job = {OWNER_FINGERPRINT_FIELD: '0' * 64}
    assert can_access(job, token) is False
    assert can_cancel(job, token) is False
    if token in (None, '', 'short', 'x' * 44):
        with pytest.raises(ValueError):
            session_fingerprint(token)


def test_session_cookie_is_secure_http_only_and_round_trips():
    token = new_session_token()
    header = session_cookie_header(token)
    cookie = SimpleCookie()
    cookie.load(header)
    morsel = cookie['moin_session']
    assert morsel.value == token
    assert morsel['httponly']
    assert morsel['secure']
    assert morsel['samesite'] == 'Lax'
    assert morsel['path'] == '/'
    assert read_session_cookie(f'other=ignored; {header}') == token
    assert read_session_cookie('') is None
    assert read_session_cookie('moin_session=forged') is None
    assert read_session_cookie('moin_session=' + token + '\r\nX-Evil: yes') is None


def test_start_throttle_enforces_sliding_window_and_bounded_ip_memory():
    throttle = StartJobThrottle(limit=2, window_seconds=10, max_tracked_ips=2)
    assert throttle.allow('192.0.2.1', now=0)
    assert throttle.allow('192.0.2.1', now=1)
    assert not throttle.allow('192.0.2.1', now=2)
    assert throttle.allow('192.0.2.1', now=10.5)
    assert not throttle.allow('192.0.2.1', now=10.6)
    with pytest.raises(RateLimitExceeded):
        throttle.check('192.0.2.1', now=10.6)
    assert throttle.allow('192.0.2.1', now=11)

    assert throttle.allow('2001:db8::1', now=11)
    assert throttle.allow('198.51.100.2', now=11)
    assert throttle.tracked_ip_count == 2
    assert throttle.allow('192.0.2.1', now=12)
    assert throttle.tracked_ip_count == 2
    with pytest.raises(ValueError):
        throttle.allow('not-an-ip', now=12)
