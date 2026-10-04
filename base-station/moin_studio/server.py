"""Local Studio server and restricted public-pilot HTTP service for Moin."""
from __future__ import annotations
import argparse
import json
import io
import ipaddress
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from tools.import_youtube import canonical_url, import_video
from moin_machine.machine import MachineCancelled, run_machine
from moin_haramain.catalog import DEFAULT_CATALOG, load_catalog
from moin_studio.diagnostics import JobDiagnostics
from moin_studio.live_room import (
    ActiveRoomExists, InvalidManagementSecret, ListenerNotFound,
    RoomEnded, RoomFull, RoomNotFound, RoomStore,
)
from moin_studio.live_service import LiveQueueFull, LiveService, MAX_AUDIO_BYTES
from moin_studio.public_access import (
    RateLimitExceeded, StartJobThrottle, assign_job_owner, can_access,
    can_cancel, new_session_token, read_session_cookie, session_cookie_header,
)
from moin_studio.budget import BudgetLedger

BASE = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / 'static'
BRAND = BASE.parent / 'brand'
LIMIT = 256 * 1024 * 1024
PUBLIC_UPLOAD_LIMIT = 64 * 1024 * 1024
EXTENSIONS = {'.wav', '.mp3', '.m4a', '.mp4', '.webm', '.ogg', '.flac', '.aiff', '.mov'}
YOUTUBE_MAX_SECONDS = 300
HARAMAIN_STATIC = STATIC / 'haramain'
HARAMAIN_PIPELINE = 'haramain-v1'
LIVE_STATIC = STATIC / 'live'
LIVE_ID = r'[A-Za-z0-9_-]{24,32}'
PUBLIC_RETENTION_SECONDS = 7 * 24 * 3600


def validate_public_configuration(storage: Path, *, environ=None):
    """Fail closed before accepting anonymous requests on a hosted worker."""
    values = os.environ if environ is None else environ
    origin = (values.get('MOIN_PUBLIC_BASE_URL') or values.get('RENDER_EXTERNAL_URL') or '').rstrip('/')
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('MOIN_PUBLIC_BASE_URL must be one HTTPS origin')
    if values.get('MOIN_STUDIO_CANDIDATE', 'deepl-v1') != 'deepl-v1':
        raise ValueError('Public mode currently supports only MOIN_STUDIO_CANDIDATE=deepl-v1')
    for name in ('GROQ_API_KEY', 'DEEPL_AUTH_KEY', 'ELEVENLABS_API_KEY'):
        if not values.get(name, '').strip():
            raise ValueError(f'{name} is required for public mode')
    if values.get('MOIN_ASR_PROVIDER') != 'groq' or values.get('MOIN_LIVE_ASR') != 'groq':
        raise ValueError('Public mode requires MOIN_ASR_PROVIDER=groq and MOIN_LIVE_ASR=groq')
    ledger = values.get('MOIN_USAGE_LEDGER_DIR', '')
    if not ledger or not Path(ledger).is_absolute():
        raise ValueError('MOIN_USAGE_LEDGER_DIR must be an absolute directory')
    storage = Path(storage).resolve()
    if not storage.is_absolute() or storage == Path(ledger).resolve():
        raise ValueError('Use separate storage and budget directories')
    for command in ('ffmpeg', 'ffprobe', 'yt-dlp'):
        bundled = Path(sys.executable).with_name(command)
        if shutil.which(command) is None and not bundled.is_file():
            raise ValueError(f'{command} is required for public mode')
    from moin_machine.machine import load_candidate, load_renderings
    load_candidate(BASE / 'benchmark-data/local-comparison.json', 'deepl-v1')
    load_renderings(BASE / 'benchmark-data/staging-renderings/renderings.quranenc.json')
    BudgetLedger(Path(ledger))
    return origin


class SourceMismatch(ValueError):
    """The imported recording was not published by its catalog source."""


class VideoUnavailable(ValueError):
    pass


class VideoTooLong(ValueError):
    pass


class QueueFull(ValueError):
    pass


class Studio:
    def __init__(self, root, runner=None, processor=run_machine, catalog_path=DEFAULT_CATALOG,
                 public_mode=False):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_mode = public_mode
        self.public_base_url = (os.environ.get('MOIN_PUBLIC_BASE_URL') or
                                os.environ.get('RENDER_EXTERNAL_URL') or '').rstrip('/') if public_mode else ''
        self.ephemeral_demo = public_mode and os.environ.get('MOIN_EPHEMERAL_DEMO') == '1'
        if public_mode:
            public_url = urlsplit(self.public_base_url)
            if public_url.scheme != 'https' or not public_url.netloc or public_url.path or public_url.query:
                raise ValueError('MOIN_PUBLIC_BASE_URL must be one HTTPS origin')
        self.start_throttle = StartJobThrottle() if public_mode else None
        self.upload_limit = PUBLIC_UPLOAD_LIMIT if public_mode else LIMIT
        self.live = RoomStore(self.root / 'live')
        self.live_service = LiveService(self.root / 'live-media', self.live)
        # Select a configured candidate through the environment so experiments
        # remain explicit and changing the provisional default needs no code edit.
        self.candidate = os.environ.get('MOIN_STUDIO_CANDIDATE', 'deepl-v1')
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.runner = runner
        self.processor = processor
        self.catalog_path = Path(catalog_path)
        # Match the former subprocess boundary: production runs use only the
        # already-pinned local model snapshot and never fetch a newer model.
        os.environ['HF_HUB_OFFLINE'] = '1'
        self.jobs = {}
        self.processes = {}
        for p in self.root.glob('*/job.json'):
            try:
                job = json.loads(p.read_text())
                if job['state'] in ('uploading', 'queued', 'processing'):
                    job.update(state='interrupted', message='The studio stopped before this recording finished. Upload it again to retry.')
                self.jobs[job['id']] = job
            except (OSError, ValueError, KeyError):
                continue
        if self.public_mode:
            self.cleanup_expired()
            threading.Thread(target=self._cleanup_loop, name='moin-studio-cleanup', daemon=True).start()
        self.wake = threading.Event()
        threading.Thread(target=self.work, daemon=True).start()

    def cleanup_expired(self, *, now=None):
        """Remove terminal public-pilot jobs after the selected seven days."""
        cutoff = (time.time() if now is None else now) - PUBLIC_RETENTION_SECONDS
        removed = []
        with self.lock:
            for jid, job in list(self.jobs.items()):
                if job['state'] in {'completed', 'partial', 'failed', 'cancelled', 'interrupted'} \
                        and job['created'] < cutoff:
                    shutil.rmtree(self.root / jid, ignore_errors=True)
                    del self.jobs[jid]
                    removed.append(jid)
        return removed

    def _cleanup_loop(self):
        while True:
            time.sleep(3600)
            self.cleanup_expired()

    def save(self, job):
        folder = self.root / job['id']
        temp = folder / 'job.tmp'
        temp.write_text(json.dumps(job))
        temp.replace(folder / 'job.json')

    def list_jobs(self, session_token=None):
        with self.lock:
            jobs = (j for j in self.jobs.values() if not self.public_mode or can_access(j, session_token))
            return sorted(({k: v for k, v in j.items() if k != 'owner_fingerprint'} for j in jobs),
                          key=lambda j: j['created'], reverse=True)

    def reserve(self, name, owner_token=None):
        suffix = Path(name).suffix.lower()
        if suffix not in EXTENSIONS:
            raise ValueError('Choose WAV, MP3, M4A, MP4, WebM, OGG, FLAC, AIFF, or MOV.')
        with self.lock:
            if sum(j['state'] in ('uploading','queued','processing') for j in self.jobs.values()) >= 4:
                raise QueueFull('The queue is full. Wait for a recording to finish.')
            jid = secrets.token_hex(12)
            folder = self.root / jid
            folder.mkdir(mode=0o700)
            job = {'id': jid, 'name': Path(name).name[:180], 'state': 'uploading', 'created': time.time(), 'message': 'Receiving recording', 'suffix': suffix}
            if self.public_mode:
                assign_job_owner(job, owner_token)
            self.jobs[jid] = job
            self.save(job)
            return jid, folder / ('input' + suffix)

    def reserve_youtube(self, url, *, catalog_video_id=None, catalog_version=None,
                        owner_token=None):
        canonical, video_id = canonical_url(url)
        with self.lock:
            if sum(j['state'] in ('uploading', 'queued', 'processing') for j in self.jobs.values()) >= 4:
                raise QueueFull('The queue is full. Wait for a recording to finish.')
            jid = secrets.token_hex(12)
            folder = self.root / jid
            folder.mkdir(mode=0o700)
            job = {
                'id': jid, 'name': f'YouTube · {video_id}', 'state': 'queued', 'created': time.time(),
                'message': 'Waiting to import the recorded YouTube video', 'suffix': '.wav',
                'source': 'youtube', 'source_url': canonical,
            }
            if catalog_video_id is not None:
                job['catalog_video_id'] = catalog_video_id
                job['catalog_version'] = catalog_version
            elif self.public_mode:
                assign_job_owner(job, owner_token)
            job['queued'] = job['created']
            self.jobs[jid] = job
            self.save(job)
            self.wake.set()
            return jid

    def catalog(self):
        return load_catalog(self.catalog_path)

    def catalog_video(self, video_id):
        catalog = self.catalog()
        video = next((item for item in catalog['videos'] if item['id'] == video_id), None)
        if video is None:
            raise KeyError(video_id)
        return catalog, video

    def catalog_version(self):
        return f'{HARAMAIN_PIPELINE}:{self.candidate}'

    def catalog_job(self, video):
        version = self.catalog_version()
        with self.lock:
            matches = [job for job in self.jobs.values()
                       if job.get('catalog_video_id') == video['id']
                       and job.get('source_url') == video['url']
                       and job.get('catalog_version') == version
                       and job['state'] in {'queued', 'processing', 'completed', 'partial', 'failed', 'interrupted'}]
            return dict(max(matches, key=lambda job: job['created'])) if matches else None

    def start_catalog_video(self, video_id, *, retry=False):
        _, video = self.catalog_video(video_id)
        if video['state'] != 'available':
            raise VideoUnavailable('This recording is currently unavailable. Open its official source for details.')
        if video['duration_seconds'] > YOUTUBE_MAX_SECONDS:
            raise VideoTooLong('This recording is longer than the current five-minute processing limit.')
        with self.lock:
            existing = self.catalog_job(video)
            if existing and (existing['state'] in {'queued', 'processing'}
                             or (not retry and existing['state'] in {'completed', 'partial'})):
                return existing, False
            jid = self.reserve_youtube(video['url'], catalog_video_id=video_id,
                                       catalog_version=self.catalog_version())
            return dict(self.jobs[jid]), True

    def update(self, jid, **values):
        with self.lock:
            self.jobs[jid].update(values)
            self.save(self.jobs[jid])

    def cancel(self, jid):
        with self.lock:
            job = self.jobs[jid]
            if job['state'] not in ('queued', 'processing'):
                raise ValueError('This recording is no longer queued or processing.')
            self.update(jid, state='cancelled', message='Processing cancelled. Upload again to retry.')
            process = self.processes.get(jid)
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)

    def machine_args(self, audio, output, *, review_mixed_speech=False):
        return argparse.Namespace(
            audio=audio,
            config=BASE / 'benchmark-data/local-comparison.json',
            candidate=self.candidate,
            renderings=BASE / 'benchmark-data/staging-renderings/renderings.quranenc.json',
            out=output,
            segment_seconds=30,
            say=True,
            review_mixed_speech=review_mixed_speech,
        )

    def run_job(self, jid, audio, output, log, progress_callback=None):
        """Run in the long-lived Studio process so the approved ASR stays warm."""
        if self.runner is None:
            return self.processor(
                self.machine_args(audio, output, review_mixed_speech=bool(self.jobs[jid].get('catalog_video_id'))),
                should_cancel=lambda: self.jobs[jid]['state'] == 'cancelled',
                progress_callback=progress_callback,
            )

        # Retained as a controlled test seam. Production does not spawn one
        # Python process per recording because that discards the Whisper cache.
        command = [sys.executable, '-m', 'moin_machine', '--audio', str(audio),
                   '--config', str(BASE / 'benchmark-data/local-comparison.json'), '--candidate', self.candidate,
                   '--renderings', str(BASE / 'benchmark-data/staging-renderings/renderings.quranenc.json'),
                   '--out', str(output), '--say']
        if self.jobs[jid].get('catalog_video_id'):
            command.append('--review-mixed-speech')
        with self.lock:
            process = self.runner(command, cwd=BASE, env={**os.environ, 'HF_HUB_OFFLINE':'1'}, stdout=log, stderr=log, start_new_session=True)
            self.processes[jid] = process
        process.wait()
        result_path = output / 'result.json'
        return json.loads(result_path.read_text()) if result_path.exists() else None

    def work(self):
        while True:
            self.wake.wait()
            self.wake.clear()
            while True:
                with self.lock:
                    pending = sorted((j for j in self.jobs.values() if j['state'] == 'queued'), key=lambda j: j['created'])
                    if not pending:
                        break
                    job = pending[0]
                    jid = job['id']
                    started = time.time()
                    queue_wait_ms = round((started - job.get('queued', job['created'])) * 1000, 3)
                    self.update(jid, state='processing', started=started, timing_ms={'queue_wait': queue_wait_ms}, message='Transcribing, translating, and preparing playback')
                folder = self.root / jid
                diagnostics = JobDiagnostics(folder / 'diagnostics.jsonl')
                try:
                    audio = folder / ('input' + job['suffix'])
                    if job.get('source') == 'youtube':
                        import_started = time.perf_counter()
                        self.update(jid, state='processing', progress_stage='importing', message='Importing recorded YouTube audio')
                        with diagnostics.stage('youtube_import'):
                            imported = import_video(job['source_url'], folder / 'youtube-import', max_duration_seconds=YOUTUBE_MAX_SECONDS)
                        youtube_import_ms = round((time.perf_counter() - import_started) * 1000, 3)
                        shutil.copyfile(imported / 'audio.wav', audio)
                        metadata = json.loads((imported / 'metadata.json').read_text())
                        if job.get('catalog_video_id'):
                            catalog, catalog_video = self.catalog_video(job['catalog_video_id'])
                            source = next(item for item in catalog['sources'] if item['id'] == catalog_video['source_id'])
                            if (catalog_video['url'] != job['source_url']
                                    or metadata.get('channel_id') != source['channel_id']):
                                raise SourceMismatch('The recording no longer matches its approved institutional source')
                        title = metadata.get('title')
                        if isinstance(title, str) and title:
                            self.update(jid, name=f'YouTube · {title[:160]}', message='Transcribing, translating, and preparing playback')

                    def report_progress(event):
                        name = event.get('event')
                        stage = event.get('stage')
                        current = event.get('current_segment')
                        count = event.get('segment_count')
                        values = {}
                        if isinstance(current, int) and current > 0:
                            values['current_segment'] = current
                        if isinstance(count, int) and count > 0:
                            values['segment_count'] = count
                        if name == 'segments_ready' and isinstance(count, int) and count > 0:
                            values['segment_count'] = count
                        segment_suffix = f' · Segment {current} of {count}' if current and count else ''
                        if name == 'stage_started' and stage == 'canonicalize':
                            values['progress_stage'] = 'canonicalize'
                            values['message'] = 'Preparing audio'
                        elif name == 'stage_finished' and stage == 'canonicalize':
                            values['message'] = 'Audio prepared'
                        elif name == 'segments_ready':
                            values['progress_stage'] = 'segmenting'
                            values['message'] = f'Audio prepared · {count} segments'
                        elif name == 'segment_started':
                            values['progress_stage'] = 'asr_translation'
                            values['message'] = f'Transcribing and translating{segment_suffix}'
                        elif name == 'stage_started' and stage in {'safety_pre_translation', 'safety_final'}:
                            values['progress_stage'] = stage
                            values['message'] = f'Checking translation safety{segment_suffix}'
                        elif name == 'stage_finished' and stage == 'safety_pre_translation':
                            values['progress_stage'] = 'asr_translation'
                            values['message'] = f'Transcribing and translating{segment_suffix}'
                        elif name == 'stage_started' and stage == 'tts':
                            values['progress_stage'] = 'tts'
                            values['message'] = f'Preparing speech{segment_suffix}'
                        elif name == 'stage_finished' and stage == 'tts':
                            values['message'] = f'Speech ready{segment_suffix}'
                        elif name == 'segment_finished':
                            values['progress_stage'] = 'segment_complete'
                            values['message'] = f'Segment {current} of {count} complete'
                        if values:
                            self.update(jid, **values)
                        safe_fields = {key: event[key] for key in ('stage', 'current_segment', 'segment_count', 'duration_ms')
                                       if key in event and isinstance(event[key], (str, int, float))}
                        diagnostics.record('machine_progress', progress_event=name, **safe_fields)

                    with (folder / 'process.log').open('w') as log:
                        with self.lock:
                            if job['state'] == 'cancelled':
                                continue
                        machine_started = time.perf_counter()
                        with diagnostics.stage('machine'):
                            result = self.run_job(jid, audio, folder / 'output', log, report_progress)
                        machine_ms = round((time.perf_counter() - machine_started) * 1000, 3)
                    with self.lock:
                        self.processes.pop(jid, None)
                        if job['state'] == 'cancelled':
                            shutil.rmtree(folder / 'output', ignore_errors=True)
                            continue
                    if result is not None:
                        failures = sum(bool(x['result'].get('failure')) for x in result['segments'])
                        withheld = sum(x['safety']['outcome'] == 'withheld' for x in result['segments'])
                        missing_speech = sum(
                            bool(x['result'].get(language))
                            and x.get('synthesis', {}).get(language, {}).get('status') != 'created'
                            for x in result['segments'] for language in ('en', 'fr')
                        )
                        with diagnostics.stage('playback_preparation'):
                            self.make_playback(folder / 'output', result)
                        finished = time.time()
                        timing = dict(self.jobs[jid].get('timing_ms', {}))
                        timing.update(machine=machine_ms, processing=round((finished - started) * 1000, 3))
                        if job.get('source') == 'youtube':
                            timing['youtube_import'] = youtube_import_ms
                        self.update(jid, state='partial' if failures else 'completed', finished=finished, failures=failures, withheld=withheld, missing_speech=missing_speech, timing_ms=timing,
                                    message='Some segments failed. Inspect the result.' if failures else 'Ready to read and listen')
                    else:
                        self.update(jid, state='failed', finished=time.time(), message='Processing could not finish. Check that the local models and Mac GPU are available, or try another media file.')
                except MachineCancelled:
                    shutil.rmtree(folder / 'output', ignore_errors=True)
                except SourceMismatch as error:
                    diagnostics.record('job_failed', failure_code='source_mismatch',
                                        error_type=type(error).__name__, stage=diagnostics.stage_name)
                    self.update(jid, state='failed', finished=time.time(),
                                message='The recording did not match its approved institutional channel. Check the official source link.')
                except Exception as error:
                    diagnostics.record('job_failed', failure_code='processing_error',
                                        error_type=type(error).__name__, stage=diagnostics.stage_name)
                    with self.lock:
                        self.processes.pop(jid, None)
                        if job['state'] != 'cancelled':
                            self.update(jid, state='failed', finished=time.time(), message='This recording could not be processed. Try another file or check the studio terminal.')

    @staticmethod
    def make_playback(folder, result):
        # ElevenLabs MP3 output plays directly. Preserve legacy AIFF support.
        for segment in result['segments']:
            for item in segment.get('synthesis', {}).values():
                if item.get('status') == 'created':
                    name = Path(item['file']).name
                    if name != item['file']:
                        continue
                    target = folder / (Path(name).stem + '.wav')
                    if name.endswith('.aiff') and not target.exists():
                        subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(folder/name),str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=60)

        # Join complete ElevenLabs segment sets into seekable lesson audio.
        for language in ('en', 'fr'):
            names = []
            for segment in result['segments']:
                speech = segment.get('synthesis', {}).get(language, {})
                name = speech.get('file', '')
                if speech.get('status') != 'created' or not re.fullmatch(rf'segment-\d{{4,}}-{language}\.mp3', name) or not (folder / name).is_file():
                    names = []
                    break
                names.append(name)
            if not names:
                continue
            target = folder / f'full-{language}.mp3'
            if target.exists() and target.stat().st_mtime >= max((folder / name).stat().st_mtime for name in names):
                continue
            manifest = folder / f'.full-{language}.ffconcat'
            temporary = folder / f'full-{language}.pending.mp3'
            try:
                manifest.write_text('ffconcat version 1.0\n' + ''.join(f"file '{name}'\n" for name in names))
                run = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'concat', '-safe', '1', '-i', str(manifest), '-c', 'copy', '-y', str(temporary)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=120)
                if run.returncode == 0 and temporary.is_file() and temporary.stat().st_size:
                    temporary.replace(target)
            except (OSError, subprocess.TimeoutExpired):
                pass
            finally:
                manifest.unlink(missing_ok=True)
                temporary.unlink(missing_ok=True)

    def output(self, jid):
        if jid == 'demo':
            return BASE / 'machine-runs/first-recorded-demo'
        if not re.fullmatch('[0-9a-f]{24}', jid) or jid not in self.jobs:
            raise KeyError(jid)
        return self.root / jid / 'output'


class Handler(BaseHTTPRequestHandler):
    server_version = 'MoinStudio'
    def log_message(self, *_):
        pass

    def send_json(self, value, status=200, *, cookie=None):
        payload = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.headers_common('application/json; charset=utf-8', len(payload))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(payload)

    def session_token(self):
        return read_session_cookie(self.headers.get('Cookie'))

    def client_ip(self):
        candidate = (self.headers.get('X-Moin-Client-IP') if self.server.app.public_mode
                     else None) or self.client_address[0]
        return str(ipaddress.ip_address(candidate))

    def can_read_job(self, app, jid):
        if jid == 'demo':
            return True
        job = app.jobs.get(jid)
        return bool(job and (not app.public_mode or can_access(job, self.session_token())))

    def read_json(self, limit=4096):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValueError('Invalid request length') from None
        if not 0 < length <= limit:
            raise ValueError('Request is empty or too large')
        value = json.loads(self.rfile.read(length).decode('utf-8'))
        if not isinstance(value, dict):
            raise ValueError('Expected a JSON object')
        return value

    def live_error(self, error):
        if isinstance(error, (RoomNotFound, ListenerNotFound)):
            return self.send_json({'error':'Room or listener not found'}, 404)
        if isinstance(error, InvalidManagementSecret):
            return self.send_json({'error':'Private room link is invalid'}, 403)
        if isinstance(error, (RoomEnded, RoomFull, ActiveRoomExists)):
            return self.send_json({'error':str(error)}, 409)
        return self.send_json({'error':'Invalid live-room request'}, 400)

    def live_post(self, path, app):
        if path == '/api/live/rooms':
            try:
                if app.public_mode:
                    app.start_throttle.check(self.client_ip())
                body = self.read_json()
                if set(body) != {'name', 'language'} or not isinstance(body['name'], str):
                    raise ValueError('Expected a room name and language')
                room, secret = app.live.create_room(body['name'], body['language'])
                base_url = app.public_base_url if app.public_mode else f'http://{self.headers["Host"]}'
                join_url = f'{base_url}/live/join/{room["id"]}'
                admin_url = f'{base_url}/live/session/{room["id"]}#secret={secret}'
                return self.send_json({**room, 'join_url':join_url, 'admin_url':admin_url,
                                       'admin_token':secret}, 201)
            except RateLimitExceeded:
                return self.send_json({'error':'Too many rooms started from this address.'}, 429)
            except ValueError as error:
                return self.live_error(error)
            except (ValueError, ActiveRoomExists) as error:
                return self.live_error(error)
        match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})/audio', path)
        if match:
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_AUDIO_BYTES:
                    return self.send_json({'error':'Microphone segment is empty or too large'}, 413)
                self.connection.settimeout(30)
                audio = self.rfile.read(length)
                if len(audio) != length:
                    return self.send_json({'error':'Microphone upload was incomplete'}, 400)
                index = app.live_service.submit(match[1], self.headers.get('X-Moin-Admin',''),
                                                audio, self.headers.get('Content-Type',''))
                return self.send_json({'index':index}, 202)
            except LiveQueueFull as error:
                return self.send_json({'error':str(error)}, 429)
            except (ValueError, RoomNotFound, RoomEnded, InvalidManagementSecret) as error:
                return self.live_error(error)
        match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})/(join|leave|end)', path)
        if not match:
            return self.send_json({'error':'Not found'}, 404)
        room_id, action = match.groups()
        try:
            body = self.read_json()
            if action == 'join':
                if body: raise ValueError('Unexpected join fields')
                return self.send_json({'listener_id': app.live.join(room_id)}, 201)
            if action == 'leave':
                if set(body) != {'listener_id'} or not isinstance(body['listener_id'], str):
                    raise ValueError('Expected listener_id')
                app.live.leave(room_id, body['listener_id'])
                return self.send_json({'left': True})
            if body: raise ValueError('Unexpected end fields')
            room = app.live.end(room_id, self.headers.get('X-Moin-Admin',''))
            return self.send_json({'room': room})
        except (ValueError, RoomNotFound, RoomEnded, RoomFull, ListenerNotFound,
                InvalidManagementSecret) as error:
            return self.live_error(error)

    def headers_common(self, content_type, length):
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; media-src 'self' blob:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'")

    def valid_host(self):
        if self.server.app.public_mode:
            return self.headers.get('Host') == urlsplit(self.server.app.public_base_url).netloc
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def allowed_origin(self):
        if self.server.app.public_mode:
            return self.server.app.public_base_url
        return f'http://{self.headers.get("Host", "")}'

    def file(self, path):
        if not path.is_file():
            return self.send_json({'error':'File not available'}, 404)
        size = path.stat().st_size
        start, end, status = 0, size-1, 200
        requested = self.headers.get('Range')
        if requested:
            match = re.fullmatch(r'bytes=(\d+)-(\d*)', requested)
            if not match:
                return self.send_json({'error':'Unsupported byte range'},416)
            start = int(match[1]); end = min(int(match[2]) if match[2] else size-1, size-1)
            if start > end:
                return self.send_json({'error':'Range outside file'},416)
            status = 206
        self.send_response(status)
        self.headers_common(mimetypes.guess_type(path.name)[0] or 'application/octet-stream', end-start+1)
        self.send_header('Accept-Ranges','bytes')
        if status == 206:
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with path.open('rb') as stream:
            stream.seek(start)
            remaining = end-start+1
            while remaining:
                data = stream.read(min(65536, remaining))
                if not data: break
                self.wfile.write(data)
                remaining -= len(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/healthz':
            return self.send_json({'status':'ok'})
        if not self.valid_host(): return self.send_json({'error':'Invalid host'},403)
        app = self.server.app
        try:
            match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})', path)
            if match:
                return self.send_json(app.live.state(match[1]))
            match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})/admin', path)
            if match:
                app.live.authorize_admin(match[1], self.headers.get('X-Moin-Admin',''))
                return self.send_json({'room':app.live.state(match[1])})
            match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})/events', path)
            if match:
                room_id = match[1]
                admin = self.headers.get('X-Moin-Admin')
                listener = self.headers.get('X-Moin-Listener')
                after = parse_qs(urlsplit(self.path).query).get('after', ['0'])[0]
                return self.send_json({'events':app.live.events(room_id, after=after,
                                       admin_secret=admin, listener_id=listener)})
            match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})/audio/(\d{{1,6}})', path)
            if match:
                room_id, index = match.groups()
                admin = self.headers.get('X-Moin-Admin')
                if admin:
                    app.live.authorize_admin(room_id, admin)
                else:
                    app.live.authorize_listener(room_id, self.headers.get('X-Moin-Listener',''))
                return self.file(app.live_service.audio(room_id, int(index)))
            match = re.fullmatch(rf'/api/live/rooms/({LIVE_ID})/qr\.svg', path)
            if match:
                room = app.live.state(match[1])
                try:
                    import segno
                except ImportError:
                    return self.send_json({'error':'QR generation is unavailable'},503)
                base_url = app.public_base_url if app.public_mode else f'http://{self.headers["Host"]}'
                qr = segno.make(f'{base_url}/live/join/{room["id"]}', error='m')
                stream = io.BytesIO()
                qr.save(stream, kind='svg', scale=6, border=2, xmldecl=False)
                payload = stream.getvalue()
                self.send_response(200)
                self.headers_common('image/svg+xml; charset=utf-8', len(payload))
                self.end_headers()
                return self.wfile.write(payload)
            if path == '/api/state':
                token = self.session_token() if app.public_mode else None
                cookie = None
                if app.public_mode and token is None:
                    token = new_session_token()
                    cookie = session_cookie_header(token, secure=True)
                return self.send_json({'token': 'public-session' if app.public_mode else app.token,
                                       'jobs':app.list_jobs(token), 'maxBytes':app.upload_limit,
                                       'public':app.public_mode,
                                       'ephemeral':app.ephemeral_demo,
                                       'demo':(app.output('demo')/'result.json').exists()}, cookie=cookie)
            if path == '/api/haramain/catalog':
                try:
                    return self.send_json(app.catalog())
                except (OSError, ValueError):
                    return self.send_json({'error': 'The Haramain catalog is unavailable.'}, 503)
            match = re.fullmatch(r'/api/haramain/videos/([A-Za-z0-9_-]{11})', path)
            if match:
                try:
                    catalog, video = app.catalog_video(match[1])
                except (OSError, ValueError):
                    return self.send_json({'error': 'The Haramain catalog is unavailable.'}, 503)
                return self.send_json({
                    'video': video,
                    'imam': next(i for i in catalog['imams'] if i['id'] == video['imam_id']),
                    'source': next(s for s in catalog['sources'] if s['id'] == video['source_id']),
                    'job': {k:v for k,v in (app.catalog_job(video) or {}).items()
                            if k != 'owner_fingerprint'} or None,
                })
            match = re.fullmatch(r'/api/jobs/([a-z0-9]+)/result',path)
            if match:
                if not self.can_read_job(app, match[1]):
                    return self.send_json({'error':'Result is not available'},404)
                output = app.output(match[1])
                result = json.loads((output/'result.json').read_text())
                app.make_playback(output, result)
                return self.send_json(result)
            match = re.fullmatch(r'/media/([a-z0-9]+)/([a-zA-Z0-9_.-]+)',path)
            if match:
                if not self.can_read_job(app, match[1]):
                    return self.send_json({'error':'File not available'},404)
                filename = match[2]
                if filename not in {'source.wav','transcript.txt','en.txt','fr.txt','result.json','full-en.mp3','full-fr.mp3'} and not re.fullmatch(r'segment-\d{4,}-(en|fr)\.(mp3|wav|aiff)',filename):
                    return self.send_json({'error':'File not available'},404)
                return self.file(app.output(match[1])/filename)
            if path.startswith('/brand/'):
                rel = path.removeprefix('/brand/')
                asset = (BRAND/rel).resolve()
                if asset.is_relative_to(BRAND.resolve()) and asset.suffix in {'.svg','.css','.woff2','.ttf'}:
                    return self.file(asset)
            if path in {'/haramain', '/haramain/'} or re.fullmatch(r'/haramain/(makkah|madinah|video/[A-Za-z0-9_-]{11})', path):
                return self.file(HARAMAIN_STATIC / 'index.html')
            if path in {'/haramain/app.js', '/haramain/style.css'}:
                return self.file(HARAMAIN_STATIC / path.rsplit('/', 1)[1])
            portrait = re.fullmatch(r'/haramain/portraits/(badr|usaimi|falata|shuwaier|bukhari|sudais)\.jpg', path)
            if portrait:
                return self.file(HARAMAIN_STATIC / 'portraits' / f'{portrait[1]}.jpg')
            if path in {'/live', '/live/'} or re.fullmatch(rf'/live/(?:session|join)/{LIVE_ID}', path):
                return self.file(LIVE_STATIC / 'index.html')
            if path in {'/live/app.js', '/live/style.css'}:
                return self.file(LIVE_STATIC / path.rsplit('/', 1)[1])
            if path == '/':
                return self.file(STATIC / 'welcome.html')
            if path in {'/studio', '/studio/'}:
                return self.file(STATIC / 'index.html')
            if path in {'/welcome.css', '/welcome.js', '/locale.js', '/favicon.svg', '/app.js', '/style.css'}:
                return self.file(STATIC / path[1:])
            if re.fullmatch(r'/welcome-assets/(prayer-source\.wav|prayer-english\.mp3|prayer-french\.mp3|studio-result\.jpg|studio\.jpg|live\.jpg)', path):
                return self.file(STATIC / path[1:])
            return self.send_json({'error':'Not found'},404)
        except (RoomNotFound, RoomEnded, ListenerNotFound, InvalidManagementSecret) as error:
            return self.live_error(error)
        except (KeyError, OSError, ValueError):
            return self.send_json({'error':'Result is not available yet'},404)

    def do_POST(self):
        self.connection.settimeout(30)
        app = self.server.app
        origin = self.headers.get('Origin')
        allowed = ({app.public_base_url} if app.public_mode else
                   {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'})
        path = urlsplit(self.path).path
        if path.startswith('/api/live/'):
            if not self.valid_host() or origin not in allowed:
                return self.send_json({'error':'Reload the live room and try again'},403)
            return self.live_post(path, app)
        token = self.session_token() if app.public_mode else None
        if not self.valid_host() or origin not in allowed or (app.public_mode and token is None) or \
                (not app.public_mode and not secrets.compare_digest(self.headers.get('X-Moin-Token',''), app.token)):
            return self.send_json({'error':'Reload the studio and try again'},403)
        if app.public_mode and (path in {'/api/upload','/api/youtube'} or path.endswith('/process')):
            try:
                app.start_throttle.check(self.client_ip())
            except (RateLimitExceeded, ValueError):
                return self.send_json({'error':'Too many processing requests. Try again later.'},429)
        match = re.fullmatch(r'/api/haramain/videos/([A-Za-z0-9_-]{11})/process', path)
        if match:
            try:
                body = self.read_json(limit=64)
                if set(body) - {'retry'} or type(body.get('retry', False)) is not bool:
                    raise ValueError('Invalid retry flag')
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                return self.send_json({'code': 'invalid_request'}, 400)
            try:
                job, created = app.start_catalog_video(match[1], retry=body.get('retry', False))
                return self.send_json({'job': job, 'created': created}, 202)
            except KeyError:
                return self.send_json({'code': 'not_found'}, 404)
            except VideoUnavailable:
                return self.send_json({'code': 'video_unavailable'}, 409)
            except VideoTooLong:
                return self.send_json({'code': 'video_too_long'}, 409)
            except QueueFull:
                return self.send_json({'code': 'queue_full'}, 409)
            except (OSError, ValueError):
                return self.send_json({'code': 'catalog_unavailable'}, 503)
        match = re.fullmatch(r'/api/jobs/([0-9a-f]{24})/cancel',path)
        if match:
            try:
                if app.public_mode and not can_cancel(app.jobs.get(match[1]), token):
                    return self.send_json({'error':'Recording cannot be cancelled'},404)
                app.cancel(match[1]); return self.send_json({'cancelled':True})
            except (KeyError, ValueError):
                return self.send_json({'error':'Recording cannot be cancelled'},409)
        if path == '/api/youtube':
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Enter one recorded YouTube link.')
                body = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(body, dict) or set(body) != {'url'} or not isinstance(body['url'], str):
                    raise ValueError('Enter one recorded YouTube link.')
                jid = app.reserve_youtube(body['url'], owner_token=token)
                return self.send_json({'id': jid}, 202)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                return self.send_json({'error': str(error)}, 400)
        if path != '/api/upload': return self.send_json({'error':'Not found'},404)
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= app.upload_limit:
                return self.send_json({'error':f'Choose a recording between 1 byte and {app.upload_limit // 1024 // 1024} MB'},413)
            name = unquote(self.headers.get('X-Filename','recording.wav'))
            jid, destination = app.reserve(name, owner_token=token)
        except ValueError as error:
            return self.send_json({'error':str(error)},400)
        try:
            self.connection.settimeout(120)
            with destination.open('xb') as stream:
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(65536,remaining))
                    if not chunk: raise OSError('Incomplete upload')
                    stream.write(chunk); remaining -= len(chunk)
            if app.public_mode:
                try:
                    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                            '-of', 'default=noprint_wrappers=1:nokey=1', str(destination)],
                                           capture_output=True, text=True, timeout=15, check=False)
                    duration = float(probe.stdout.strip())
                    if probe.returncode or not 0 < duration <= YOUTUBE_MAX_SECONDS:
                        raise ValueError()
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    destination.unlink(missing_ok=True)
                    app.update(jid,state='failed',finished=time.time(),message='Recording must contain at most five minutes of playable audio.')
                    return self.send_json({'error':'Recording must contain at most five minutes of playable audio.'},400)
            app.update(jid,state='queued',queued=time.time(),message='Waiting for local processing')
            app.wake.set()
            return self.send_json({'id':jid},202)
        except OSError:
            app.update(jid,state='failed',message='Upload interrupted. Please try again.')
            return self.send_json({'error':'Upload interrupted'},400)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8787)
    p.add_argument('--storage',type=Path,default=BASE/'studio-runs')
    p.add_argument('--host',default='127.0.0.1',help='Bind address; use 0.0.0.0 only behind a trusted reverse proxy')
    p.add_argument('--public',action='store_true',help='Enable restricted anonymous pilot mode')
    p.add_argument('--check-public',action='store_true',help='Validate public configuration and exit')
    args = p.parse_args()
    if args.check_public and not args.public:
        p.error('--check-public requires --public')
    if args.public:
        try:
            validate_public_configuration(args.storage)
        except ValueError as error:
            p.error(str(error))
        if args.check_public:
            print('Public pilot configuration is ready',flush=True)
            return
    app = Studio(args.storage, public_mode=args.public)
    demo = app.output('demo')
    if (demo/'result.json').exists():
        app.make_playback(demo,json.loads((demo/'result.json').read_text()))
    server = ThreadingHTTPServer((args.host,args.port),Handler)
    server.app = app
    print(f'Moin Studio: {app.public_base_url if args.public else f"http://{args.host}:{args.port}"}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        with app.lock:
            for jid in list(app.processes):
                app.cancel(jid)
        server.server_close()

if __name__ == '__main__': main()
