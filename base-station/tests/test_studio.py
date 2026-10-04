"""Real HTTP boundary tests with inference replaced by a controlled local double."""
import http.client
import json
from pathlib import Path
import threading
import time
import pytest
import moin_studio.server as studio_server
from moin_studio.server import Studio, Handler, ThreadingHTTPServer, LIMIT
from moin_studio.diagnostics import JobDiagnostics


@pytest.fixture
def service(tmp_path):
    class Process:
        pid = 999999
        def __init__(self, command, **kwargs):
            folder = Path(command[command.index('--out')+1]); folder.mkdir()
            (folder/'source.wav').write_bytes(b'0123456789')
            (folder/'segment-0001-en.mp3').write_bytes(b'generated mp3')
            (folder/'result.json').write_text(json.dumps({'segments':[{'result':{'failure':None,'arabic':'test','en':'meaning','fr':'sens'},'safety':{'outcome':'ordinary_translation'},'synthesis':{'en':{'status':'created','provider':'elevenlabs','file':'segment-0001-en.mp3'}}}]}))
        def wait(self): return 0
        def poll(self): return 0
    app=Studio(tmp_path, runner=Process)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.app=app
    threading.Thread(target=server.serve_forever,daemon=True).start()
    yield app, server.server_port
    server.shutdown();server.server_close()


def call(service, method, path, body=None, **headers):
    app, port=service
    conn=http.client.HTTPConnection('127.0.0.1',port)
    conn.request(method,path,body=body,headers=headers)
    result=conn.getresponse();payload=result.read();status=result.status
    conn.close()
    return status,payload


def auth(service):
    app,port=service
    return {'Origin':f'http://127.0.0.1:{port}','X-Moin-Token':app.token,'X-Filename':'recording.wav'}


def test_upload_process_result_and_audio_seek(service):
    status,payload=call(service,'POST','/api/upload',b'recorded audio',**auth(service))
    assert status==202
    jid=json.loads(payload)['id']
    for _ in range(100):
        status,payload=call(service,'GET','/api/state')
        jobs=json.loads(payload)['jobs']
        if jobs[0]['state']=='completed': break
        time.sleep(.01)
    assert jobs[0]['state']=='completed'
    status,payload=call(service,'GET',f'/api/jobs/{jid}/result')
    assert status==200 and json.loads(payload)['segments'][0]['result']['en']=='meaning'
    status,payload=call(service,'GET',f'/media/{jid}/source.wav',Range='bytes=2-5')
    assert status==206 and payload==b'2345'
    status,payload=call(service,'GET',f'/media/{jid}/segment-0001-en.mp3')
    assert status==200 and payload==b'generated mp3'
    assert call(service,'GET',f'/media/{jid}/process.log')[0]==404
    assert call(service,'GET','/brand/../../.git/config')[0]==404


def test_welcome_and_studio_are_separate_direct_routes(service):
    status, welcome = call(service, 'GET', '/')
    assert status == 200 and b'id="hero-title"' in welcome and b'href="/studio"' in welcome
    assert b'/welcome-assets/prayer-english.mp3' in welcome
    assert b'/welcome-assets/prayer-french.mp3' in welcome
    status, studio = call(service, 'GET', '/studio')
    assert status == 200 and b'id="upload-form"' in studio and b'id="youtube-form"' in studio
    for path in ('/haramain', '/haramain/makkah', '/live', '/favicon.svg', '/welcome.css', '/locale.js',
                 '/welcome-assets/prayer-source.wav', '/welcome-assets/prayer-english.mp3',
                 '/welcome-assets/prayer-french.mp3', '/welcome-assets/studio-result.jpg',
                 '/welcome-assets/studio.jpg', '/welcome-assets/live.jpg'):
        assert call(service, 'GET', path)[0] == 200


def test_foreign_pages_cannot_start_inference(service):
    assert call(service,'POST','/api/upload',b'a',**{'Origin':'https://example.com','X-Moin-Token':service[0].token})[0]==403
    assert call(service,'POST','/api/upload',b'a',Origin=f'http://127.0.0.1:{service[1]}')[0]==403
    assert call(service,'GET','/api/state',Host='attacker.example')[0]==403
    assert service[0].list_jobs()==[]


def test_invalid_upload_and_missing_results(service):
    headers=auth(service);headers['X-Filename']='script.exe'
    assert call(service,'POST','/api/upload',b'a',**headers)[0]==400
    assert call(service,'POST','/api/upload',b'',**auth(service))[0]==413
    assert call(service,'GET','/api/jobs/notreal/result')[0]==404


def test_recorded_youtube_link_queues_an_import_before_processing(monkeypatch, service):
    def fake_import(url, out, *, max_duration_seconds):
        assert url == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        assert max_duration_seconds == 300
        out.mkdir()
        (out / 'audio.wav').write_bytes(b'canonical audio')
        (out / 'metadata.json').write_text(json.dumps({'title': 'A recorded lesson'}))
        return out

    monkeypatch.setattr(studio_server, 'import_video', fake_import)
    headers=auth(service);headers['Content-Type']='application/json'
    status,payload=call(service,'POST','/api/youtube',json.dumps({'url':'https://youtu.be/dQw4w9WgXcQ'}),**headers)
    assert status==202
    jid=json.loads(payload)['id']
    for _ in range(100):
        status,payload=call(service,'GET','/api/state')
        jobs=json.loads(payload)['jobs']
        if jobs[0]['state']=='completed': break
        time.sleep(.01)
    assert jobs[0]['state']=='completed'
    assert jobs[0]['name']=='YouTube · A recorded lesson'
    assert call(service,'POST','/api/youtube',json.dumps({'url':'https://example.com/video'}),**headers)[0]==400


def test_restart_marks_unfinished_jobs_interrupted(tmp_path):
    app=Studio(tmp_path)
    jid,_=app.reserve('recording.wav');app.update(jid,state='processing')
    restarted=Studio(tmp_path)
    assert restarted.list_jobs()[0]['state']=='interrupted'
    with pytest.raises(KeyError): restarted.output('../outside')


def test_studio_candidate_can_be_selected_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('MOIN_STUDIO_CANDIDATE', 'local-translategemma')
    app=Studio(tmp_path)
    assert app.candidate == 'local-translategemma'


def test_queue_limit_and_queued_cancellation(tmp_path):
    app=Studio(tmp_path)
    ids=[app.reserve('recording.wav')[0] for _ in range(4)]
    with pytest.raises(ValueError,match='queue is full'):app.reserve('recording.wav')
    app.update(ids[0],state='queued');app.cancel(ids[0])
    assert app.jobs[ids[0]]['state']=='cancelled'
    app.reserve('recording.wav')


def test_default_worker_reuses_one_process_and_records_queue_and_machine_time(tmp_path):
    calls = []

    def processor(args, *, should_cancel, progress_callback):
        calls.append((threading.get_ident(), should_cancel()))
        progress_callback({'event': 'segments_ready', 'segment_count': 3, 'stage': 'segmenting'})
        progress_callback({'event': 'segment_started', 'current_segment': 2, 'segment_count': 3, 'stage': 'asr_translation'})
        args.out.mkdir()
        (args.out / 'source.wav').write_bytes(b'audio')
        result = {'timing_ms': {'total': 1}, 'segments': [{'result': {'failure': None, 'arabic': 'نص', 'en': 'Text', 'fr': 'Texte'}, 'safety': {'outcome': 'ordinary_translation'}}]}
        (args.out / 'result.json').write_text(json.dumps(result))
        return result

    app = Studio(tmp_path, processor=processor)
    ids = []
    for name in ('one.wav', 'two.wav'):
        jid, destination = app.reserve(name)
        destination.write_bytes(b'audio')
        app.update(jid, state='queued', queued=time.time(), message='Waiting')
        ids.append(jid)
    app.wake.set()

    for _ in range(200):
        if all(app.jobs[jid]['state'] == 'completed' for jid in ids):
            break
        time.sleep(.01)

    assert len(calls) == 2
    assert calls[0][0] == calls[1][0]
    assert calls[0][1] is calls[1][1] is False
    for jid in ids:
        assert set(app.jobs[jid]['timing_ms']) == {'queue_wait', 'machine', 'processing'}
        assert app.jobs[jid]['segment_count'] == 3
        assert app.jobs[jid]['current_segment'] == 2
        assert app.jobs[jid]['progress_stage'] == 'asr_translation'
        events = [json.loads(line) for line in (tmp_path / jid / 'diagnostics.jsonl').read_text().splitlines()]
        assert [event['stage'] for event in events if event['event'] == 'stage_finished'] == ['machine', 'playback_preparation']
        progress = [event for event in events if event['event'] == 'machine_progress']
        assert any(event['progress_event'] == 'segment_started' and event['current_segment'] == 2 for event in progress)


def test_job_diagnostics_record_stage_duration_and_safe_failure_details(tmp_path):
    path = tmp_path / 'job' / 'diagnostics.jsonl'
    diagnostics = JobDiagnostics(path)

    with diagnostics.stage('youtube_import'):
        pass
    with pytest.raises(RuntimeError):
        with diagnostics.stage('machine'):
            raise RuntimeError('private provider response')

    payload = path.read_text()
    events = [json.loads(line) for line in payload.splitlines()]
    assert [event['event'] for event in events] == [
        'stage_started', 'stage_finished', 'stage_started', 'stage_failed'
    ]
    assert events[1]['stage'] == 'youtube_import'
    assert events[1]['duration_ms'] >= 0
    assert events[3]['stage'] == 'machine'
    assert events[3]['error_type'] == 'RuntimeError'
    assert 'private provider response' not in payload
