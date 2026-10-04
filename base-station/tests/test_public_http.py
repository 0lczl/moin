"""Public pilot privacy behavior exercised at the HTTP boundary."""
import http.client
import json
import threading

import pytest

from moin_studio.server import Handler, Studio, ThreadingHTTPServer


@pytest.fixture
def public_server(tmp_path, monkeypatch):
    monkeypatch.setenv('MOIN_PUBLIC_BASE_URL', 'https://moin.example')
    app = Studio(tmp_path, public_mode=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.app = app
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield app, server.server_port
    server.shutdown()
    server.server_close()


def request(service, method, path, *, body=None, cookie=None, origin=None):
    connection = http.client.HTTPConnection('127.0.0.1', service[1], timeout=5)
    headers = {'Host': 'moin.example'}
    if cookie:
        headers['Cookie'] = cookie
    if origin:
        headers['Origin'] = origin
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    status = response.status
    cookie_header = response.getheader('Set-Cookie')
    data = response.read()
    connection.close()
    return status, cookie_header, data


def test_private_job_is_visible_only_to_its_anonymous_browser(public_server):
    app, _ = public_server
    status, cookie_header, payload = request(public_server, 'GET', '/api/state')
    assert status == 200
    assert b'"public": true' in payload
    assert 'Secure' in cookie_header and 'HttpOnly' in cookie_header
    owner_cookie = cookie_header.split(';', 1)[0]
    _, other_header, _ = request(public_server, 'GET', '/api/state')
    other_cookie = other_header.split(';', 1)[0]

    from moin_studio.public_access import read_session_cookie
    jid, _ = app.reserve('lesson.wav', owner_token=read_session_cookie(owner_cookie))
    output = app.root / jid / 'output'
    output.mkdir()
    (output / 'result.json').write_text('{"segments":[]}')
    app.update(jid, state='completed')

    own = json.loads(request(public_server, 'GET', '/api/state', cookie=owner_cookie)[2])
    other = json.loads(request(public_server, 'GET', '/api/state', cookie=other_cookie)[2])
    assert [job['id'] for job in own['jobs']] == [jid]
    assert not other['jobs']
    assert 'owner_fingerprint' not in own['jobs'][0]
    assert request(public_server, 'GET', f'/api/jobs/{jid}/result', cookie=other_cookie)[0] == 404
    assert request(public_server, 'GET', f'/media/{jid}/result.json', cookie=other_cookie)[0] == 404
    assert request(public_server, 'GET', f'/api/jobs/{jid}/result', cookie=owner_cookie)[0] == 200


def test_public_upload_requires_initialized_session_and_same_origin(public_server):
    status, _, _ = request(public_server, 'POST', '/api/upload', body=b'a',
                           origin='https://moin.example')
    assert status == 403
    _, cookie_header, _ = request(public_server, 'GET', '/api/state')
    cookie = cookie_header.split(';', 1)[0]
    status, _, _ = request(public_server, 'POST', '/api/upload', body=b'a',
                           cookie=cookie, origin='https://foreign.example')
    assert status == 403


def test_public_static_assets_are_cached_without_caching_session_state(public_server):
    connection = http.client.HTTPConnection('127.0.0.1', public_server[1], timeout=5)
    connection.request('GET', '/welcome.css', headers={'Host': 'moin.example'})
    response = connection.getresponse()
    assert response.status == 200
    assert response.getheader('Cache-Control') == 'public, max-age=300'
    response.read()
    connection.close()

    connection = http.client.HTTPConnection('127.0.0.1', public_server[1], timeout=5)
    connection.request('GET', '/api/state', headers={'Host': 'moin.example'})
    response = connection.getresponse()
    assert response.getheader('Cache-Control') == 'no-store'
    response.read()
    connection.close()


def test_render_demo_exposes_ephemeral_state_and_health(tmp_path, monkeypatch):
    monkeypatch.delenv('MOIN_PUBLIC_BASE_URL', raising=False)
    monkeypatch.setenv('RENDER_EXTERNAL_URL', 'https://moin-judges-demo.onrender.com')
    monkeypatch.setenv('MOIN_EPHEMERAL_DEMO', '1')
    app = Studio(tmp_path, public_mode=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.app = app
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        connection.request('GET', '/healthz', headers={'Host': 'internal-health-check'})
        response = connection.getresponse()
        assert response.status == 200
        assert json.loads(response.read()) == {'status': 'ok'}
        connection.close()

        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        connection.request('GET', '/api/state', headers={'Host': 'moin-judges-demo.onrender.com'})
        response = connection.getresponse()
        assert response.status == 200
        assert json.loads(response.read())['ephemeral'] is True
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
