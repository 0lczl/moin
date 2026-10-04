"""Catalog trust and the recorded-video route through the local Studio."""
import copy
import hashlib
import json
from pathlib import Path
import time
import wave

import pytest

from moin_haramain.catalog import load_catalog, validate_catalog
import moin_studio.server as studio_server
from test_studio import call, auth


def test_seed_is_official_and_six_clips_are_within_import_limit():
    catalog = load_catalog()
    assert len(catalog['imams']) == 6
    assert {v['imam_id'] for v in catalog['videos']} == {i['id'] for i in catalog['imams']}
    assert all(i['portrait'] == f'/haramain/portraits/{i["id"]}.jpg' for i in catalog['imams'])
    assert all(v['duration_seconds'] <= studio_server.YOUTUBE_MAX_SECONDS for v in catalog['videos'])


def test_packaged_catalog_audio_requires_matching_source_and_digest(tmp_path, monkeypatch):
    video_id = 'D3ofKhOUnXI'
    url = f'https://www.youtube.com/watch?v={video_id}'
    folder = tmp_path / 'catalog-audio' / video_id
    folder.mkdir(parents=True)
    audio = folder / 'audio.wav'
    with wave.open(str(audio), 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        stream.writeframes(bytes(32000))
    metadata = {
        'video_id': video_id, 'source_url': url, 'channel_id': 'UCofficial',
        'audio_sha256': hashlib.sha256(audio.read_bytes()).hexdigest(),
    }
    (folder / 'metadata.json').write_text(json.dumps(metadata))
    monkeypatch.setattr(studio_server, 'HARAMAIN_AUDIO', tmp_path / 'catalog-audio')
    app = studio_server.Studio(tmp_path / 'runs')
    monkeypatch.setattr(app, 'catalog_video', lambda _id: (
        {'sources': [{'id': 'approved', 'channel_id': 'UCofficial'}]},
        {'id': video_id, 'url': url, 'source_id': 'approved', 'state': 'available', 'duration_seconds': 1},
    ))
    assert app.catalog_audio(url) == folder
    audio.write_bytes(audio.read_bytes() + b'altered')
    with pytest.raises(studio_server.SourceMismatch):
        app.catalog_audio(url)


@pytest.mark.parametrize('mutation', [
    lambda c: c['videos'][1].update(id=c['videos'][0]['id']),
    lambda c: c['videos'][0].update(url='https://youtube.com/watch?v=dQw4w9WgXcQ'),
    lambda c: c['videos'][0].update(source_id='nabawi-lessons'),
    lambda c: c['sources'][0].update(channel_id='UCunknown'),
    lambda c: c['sources'][0].update(url='https://example.com/channel'),
    lambda c: c['videos'][0].update(title={'en': 'Missing Arabic'}),
    lambda c: c['imams'][0].update(portrait='/haramain/portraits/../other.jpg'),
    lambda c: c['broadcasts'][0].update(state='available', url='https://example.com/live'),
])
def test_reject_untrusted_duplicate_or_incomplete_catalog(mutation):
    catalog = copy.deepcopy(load_catalog())
    mutation(catalog)
    with pytest.raises(ValueError):
        validate_catalog(catalog)


@pytest.fixture
def haramain_service(tmp_path):
    class Process:
        pid = 999999
        def __init__(self, command, **kwargs):
            assert '--review-mixed-speech' in command
            folder = Path(command[command.index('--out') + 1]); folder.mkdir()
            (folder / 'source.wav').write_bytes(b'audio')
            (folder / 'result.json').write_text(json.dumps({'segments': [
                {'result': {'failure': None, 'arabic': 'العربية', 'en': 'English', 'fr': 'Français'},
                 'safety': {'outcome': 'ordinary_translation'}, 'synthesis': {}}
            ]}))
        def wait(self): return 0
        def poll(self): return 0

    import threading
    app = studio_server.Studio(tmp_path, runner=Process)
    server = studio_server.ThreadingHTTPServer(('127.0.0.1', 0), studio_server.Handler)
    server.app = app
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield app, server.server_port
    server.shutdown(); server.server_close()


def test_catalog_route_deduplicates_jobs_and_reuses_result(monkeypatch, haramain_service):
    video = load_catalog()['videos'][0]

    def fake_import(url, out, *, max_duration_seconds):
        assert url == video['url']
        assert max_duration_seconds == 300
        out.mkdir()
        (out / 'audio.wav').write_bytes(b'canonical audio')
        (out / 'metadata.json').write_text(json.dumps({'title': 'Verified clip', 'channel_id': 'UC3QAoXf9GN9xeQYhk-AZbTg'}))
        return out

    monkeypatch.setattr(studio_server, 'import_video', fake_import)
    assert call(haramain_service, 'GET', '/haramain')[0] == 200
    assert call(haramain_service, 'GET', '/haramain/makkah')[0] == 200
    assert call(haramain_service, 'GET', f'/haramain/video/{video["id"]}')[0] == 200
    for imam in load_catalog()['imams']:
        status, portrait = call(haramain_service, 'GET', imam['portrait'])
        assert status == 200 and portrait.startswith(b'\xff\xd8')
    status, payload = call(haramain_service, 'GET', '/api/haramain/catalog')
    assert status == 200 and len(json.loads(payload)['videos']) == 6
    status, payload = call(haramain_service, 'GET', f'/api/haramain/videos/{video["id"]}')
    assert status == 200 and json.loads(payload)['job'] is None

    headers = auth(haramain_service)
    status, payload = call(haramain_service, 'POST', f'/api/haramain/videos/{video["id"]}/process', b'{}', **headers)
    first = json.loads(payload)
    assert status == 202 and first['created'] is True
    status, payload = call(haramain_service, 'POST', f'/api/haramain/videos/{video["id"]}/process', b'{}', **headers)
    second = json.loads(payload)
    assert status == 202 and second['created'] is False
    assert first['job']['id'] == second['job']['id']

    for _ in range(100):
        status, payload = call(haramain_service, 'GET', f'/api/haramain/videos/{video["id"]}')
        job = json.loads(payload)['job']
        if job['state'] == 'completed': break
        time.sleep(.01)
    assert job['state'] == 'completed'
    assert job['missing_speech'] == 2
    assert len(haramain_service[0].list_jobs()) == 1
    status, payload = call(haramain_service, 'GET', f'/api/jobs/{job["id"]}/result')
    assert status == 200 and json.loads(payload)['segments'][0]['result']['fr'] == 'Français'
    status, payload = call(haramain_service, 'POST', f'/api/haramain/videos/{video["id"]}/process',
                           b'{"retry":true}', **headers)
    retried = json.loads(payload)
    assert status == 202 and retried['created'] is True
    assert retried['job']['id'] != job['id']


def test_invalid_catalog_does_not_publish(monkeypatch, haramain_service, tmp_path):
    catalog = copy.deepcopy(load_catalog())
    catalog['sources'][0]['channel_id'] = 'unapproved'
    file = tmp_path / 'catalog.json'
    file.write_text(json.dumps(catalog))
    haramain_service[0].catalog_path = file
    assert call(haramain_service, 'GET', '/api/haramain/catalog')[0] == 503


def test_video_from_wrong_channel_fails_before_inference(monkeypatch, haramain_service):
    video = load_catalog()['videos'][0]

    def wrong_channel(url, out, *, max_duration_seconds):
        out.mkdir()
        (out / 'audio.wav').write_bytes(b'canonical audio')
        (out / 'metadata.json').write_text(json.dumps({'title': 'Impersonated', 'channel_id': 'UCnotapproved'}))
        return out

    monkeypatch.setattr(studio_server, 'import_video', wrong_channel)
    headers = auth(haramain_service)
    status, payload = call(haramain_service, 'POST', f'/api/haramain/videos/{video["id"]}/process', b'{}', **headers)
    assert status == 202
    jid = json.loads(payload)['job']['id']
    for _ in range(100):
        job = haramain_service[0].jobs[jid]
        if job['state'] == 'failed': break
        time.sleep(.01)
    assert job['state'] == 'failed'
    assert not (haramain_service[0].root / jid / 'output' / 'result.json').exists()
