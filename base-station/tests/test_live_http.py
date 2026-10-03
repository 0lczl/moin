"""Exercise the live room through its actual HTTP routes with fake inference."""
import http.client
import json
import threading
import time

import pytest

from moin_studio.server import Handler, Studio, ThreadingHTTPServer


@pytest.fixture
def live_server(tmp_path):
    studio = Studio(tmp_path)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.app = studio
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield studio, server.server_port
    server.shutdown()
    server.server_close()


def call(service, method, path, body=None, *, headers=None):
    _, port = service
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
    request_headers = {'Host': f'127.0.0.1:{port}', **(headers or {})}
    if method == 'POST':
        request_headers['Origin'] = f'http://127.0.0.1:{port}'
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    payload = response.read()
    status = response.status
    connection.close()
    return status, payload


def json_call(service, method, path, value=None, *, headers=None):
    body = json.dumps(value if value is not None else {}).encode() if method == 'POST' else None
    status, payload = call(service, method, path, body,
                           headers={'Content-Type': 'application/json', **(headers or {})})
    return status, json.loads(payload)


def test_create_join_qr_private_management_and_ended_record(live_server):
    status, room = json_call(live_server, 'POST', '/api/live/rooms',
                             {'name': 'Friday lesson', 'language': 'en'})
    assert status == 201
    room_id = room['id']
    assert room['join_url'].endswith(f'/live/join/{room_id}')
    assert '#secret=' in room['admin_url']
    assert call(live_server, 'GET', f'/live/join/{room_id}')[0] == 200
    qr_status, svg = call(live_server, 'GET', f'/api/live/rooms/{room_id}/qr.svg')
    assert qr_status == 200 and b'<svg' in svg
    assert room['admin_token'].encode() not in svg

    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/admin')[0] == 403
    status, joined = json_call(live_server, 'POST', f'/api/live/rooms/{room_id}/join')
    assert status == 201
    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}')[1]['listener_count'] == 1
    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/events')[0] == 403
    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/events',
                     headers={'X-Moin-Listener': joined['listener_id']})[0] == 200

    status, ended = json_call(live_server, 'POST', f'/api/live/rooms/{room_id}/end',
                              headers={'X-Moin-Admin': room['admin_token']})
    assert status == 200 and ended['room']['status'] == 'ended'
    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/events',
                     headers={'X-Moin-Listener': joined['listener_id']})[0] == 409
    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/events',
                     headers={'X-Moin-Admin': room['admin_token']})[0] == 200


def test_audio_segment_text_precedes_speech_and_listener_access(live_server):
    class FakeProcessor:
        def process(self, source, language, output, update):
            output.mkdir()
            update('text', {'arabic': 'السلام عليكم', 'translation': 'Peace be upon you',
                            'language': language, 'safety': 'ordinary_translation',
                            'audio_status': 'pending'})
            (output / 'speech-en.mp3').write_bytes(b'fake mp3')
            update('audio', {'arabic': 'السلام عليكم', 'translation': 'Peace be upon you',
                             'language': language, 'safety': 'ordinary_translation',
                             'audio_status': 'ready'})

    live_server[0].live_service.processor_factory = FakeProcessor
    status, room = json_call(live_server, 'POST', '/api/live/rooms',
                             {'name': 'Lesson', 'language': 'en'})
    assert status == 201
    room_id = room['id']
    listener = json_call(live_server, 'POST', f'/api/live/rooms/{room_id}/join')[1]['listener_id']
    status, payload = call(live_server, 'POST', f'/api/live/rooms/{room_id}/audio', b'audio',
                           headers={'X-Moin-Admin': room['admin_token'], 'Content-Type': 'audio/webm'})
    assert status == 202
    index = json.loads(payload)['index']
    for _ in range(100):
        _, data = json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/events',
                            headers={'X-Moin-Listener': listener})
        phases = [event['segment']['phase'] for event in data['events'] if event['type'] == 'segment']
        if 'audio' in phases:
            break
        time.sleep(.01)
    assert phases == ['processing', 'text', 'audio']
    assert call(live_server, 'GET', f'/api/live/rooms/{room_id}/audio/{index}')[0] == 404
    assert call(live_server, 'GET', f'/api/live/rooms/{room_id}/audio/{index}',
                headers={'X-Moin-Listener': listener}) == (200, b'fake mp3')


def test_fifty_browser_clients_can_join_and_receive_the_same_text(live_server):
    status, room = json_call(live_server, 'POST', '/api/live/rooms',
                             {'name': 'Capacity check', 'language': 'fr'})
    assert status == 201
    room_id = room['id']
    listeners = []
    for _ in range(50):
        status, result = json_call(live_server, 'POST', f'/api/live/rooms/{room_id}/join')
        assert status == 201
        listeners.append(result['listener_id'])
    assert json_call(live_server, 'GET', f'/api/live/rooms/{room_id}')[1]['listener_count'] == 50
    assert json_call(live_server, 'POST', f'/api/live/rooms/{room_id}/join')[0] == 409

    live_server[0].live.append_segment(room_id, room['admin_token'],
                                       {'index': 1, 'phase': 'text', 'arabic': 'السلام عليكم',
                                        'translation': 'Que la paix soit sur vous'})
    for listener in listeners:
        status, response = json_call(live_server, 'GET', f'/api/live/rooms/{room_id}/events',
                                     headers={'X-Moin-Listener': listener})
        assert status == 200
        assert any(event.get('segment', {}).get('translation') == 'Que la paix soit sur vous'
                   for event in response['events'])
