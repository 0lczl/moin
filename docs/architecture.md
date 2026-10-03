# Moin website architecture

This note describes the local application, the implemented hosted-pilot code,
and the longer-term architecture. The hosted code is prepared but no public
server has been deployed or measured yet.

## Current local system

```text
Browser (static HTML/CSS/JS)
        │ loopback HTTP, job id and local request token
        ▼
Studio server (127.0.0.1:8787)
        │ one in-process worker; one job at a time
        ├── YouTube import: yt-dlp + ffmpeg
        └── machine pipeline
              ├── local Whisper large-v3 ASR
              ├── Qur’an safety routing
              ├── DeepL text translation (EN and FR)
              └── ElevenLabs speech generation (EN and FR)
        │
        └── per-job folders under base-station/studio-runs/
```

The website is a small static interface served by Python's HTTP server. The
server binds to `127.0.0.1`; it is intended for one operator on one Mac, not for
direct internet access. The browser sends uploads or YouTube links to Studio,
then polls job state. A per-server token and same-origin checks protect the
local API from unrelated web pages. Provider credentials remain in the Studio
process environment and are never sent to browser code.

Studio stores each job's input, state, diagnostics, and output in its own local
folder. Job state is persisted in `job.json`; completed text, audio, and timing
evidence are written below `output/`. The diagnostics log records stage names,
durations, and safe failure metadata, not transcript text, media, signed URLs,
or credentials. Jobs survive a server restart when complete; jobs that were
active at shutdown are marked interrupted.

One worker handles jobs serially. It imports and canonicalizes media, splits
audio into bounded segments, then uses the pinned local Whisper model. The
configured ASR runs on CPU with int8 compute and beam size 5. Arabic text passes
through the Qur’an safety gate before translations or generated speech can be
used. Ordinary text goes to DeepL for English and French; those requests run in
parallel. Eligible translations go to ElevenLabs for playback, also in
parallel by language. The worker keeps the ASR model warm between jobs. The UI
reports queue time, current stage, elapsed time, and completed segment counts;
it does not estimate a percentage or completion time.

This is a local experimental workflow, with a 256 MB upload limit and a
five-minute YouTube limit. It has no hosted queue, multi-user identity,
distributed storage, worker autoscaling, or service-level availability target.
Local persistence and a loopback token are not a production account or
authorization system.

## Why a new web framework is not the latency fix

The browser and HTTP server spend little time compared with inference. Long
runs come from serial CPU Whisper work and safety classification over the
trusted rendering corpus, with speech generation adding provider wait time.
Changing the frontend framework or moving the same synchronous work behind a
different route would not make those stages faster. Keep stage-level timing,
profile actual runs, and optimize the measured ASR and safety costs before
choosing compute or model changes. Preserve the current fail-closed safety
behavior and validate any model or runtime change for quality.

## Implemented hosted pilot (deployment pending)

```text
Browser: Studio / Haramain / Live Translator
         │ HTTPS
         ▼
       Caddy ── private Docker network ── Moin Python HTTP service
                                         ├── recorded job worker → Groq Whisper large-v3
                                         │                     → Qur'an safety gate
                                         │                     → DeepL EN + FR
                                         │                     → ElevenLabs EN + FR
                                         └── live segment worker → Groq Whisper large-v3
                                                               → same safety gate
                                                               → DeepL selected language
                                                               → ElevenLabs optional playback
                                              │
                                              ▼
                                persistent job, room, media, budget data
```

The three static pages share navigation. Anonymous visitors may submit bounded
recordings or create the single live room. A private browser cookie owns each
recording; approved Haramain catalog results are public. A private fragment
link holds the room-management capability, and joined listeners have separate
unguessable capabilities for text and audio. The room accepts at most 50
listeners and expires after one hour. Original and generated media and text
are removed seven days after creation or completion by the hourly cleanup.

Public mode requires an HTTPS origin, provider keys, a persistent budget
ledger, the curated Qur'an rendering registry, and media tools before startup.
The ledger reserves estimated usage before billable calls, but provider-side
caps and invoice review are still needed to uphold the owner's USD 100 goal.
Deployment instructions and limitations are in `deploy/README.md`.

The recorded and live workers are separate in-process threads so a long
recorded job cannot directly occupy the live queue. State is file-backed, not
distributed. Recorded work interrupted by a process restart is marked for
resubmission. The live text target of under ten seconds and 50-listener load
target have not been verified on a host. Provider credentials are currently
unavailable in this workspace, so no end-to-end hosted measurement is claimed.

## Longer-term hosted target

Move the boundaries in steps so the local pipeline remains useful while the
service grows:

1. **Stabilize the job contract.** Keep the UI separate from processing. Define
   explicit job states and stage events, including cancellation, retry, and
   failure codes. Keep inference and safety logic behind a worker interface.
2. **Separate API and worker.** The API authenticates users, validates media
   requests, creates durable job records, and enqueues work. Dedicated workers
   claim jobs from a durable queue, report progress, and use compute suited to
   the selected ASR runtime. Queue limits, retries, idempotency, and per-user
   quotas belong at this boundary.
3. **Move job state and media to managed storage.** Put state in a database and
   source/output media in private object storage. Pass short-lived object
   references to workers; do not make media public by default. Set retention,
   deletion, and access rules for source audio and generated speech.
4. **Evolve public access.** Host the public UI separately from the API and
   worker when scale requires it. Revisit authentication if abuse or privacy
   needs outgrow the anonymous pilot decision.
   Keep DeepL and ElevenLabs credentials in server-side secret storage, and
   ensure neither keys nor private object references reach client bundles.
5. **Operate and scale deliberately.** Add per-stage metrics, queue age,
   worker health, cost limits, and alerting. Scale workers based on observed
   queue delay and memory/throughput measurements, not just web request volume.

Keep the trusted rendering registry versioned with each result. The safety gate
must run before translated text or speech is released, including in a hosted
worker and after any retry. A public deployment also needs reviewed policies
for source rights, user data retention, provider disclosures, and the limits of
experimental religious-content translation.

## Related implementation notes

- [Studio operation and local storage](../base-station/STUDIO.md)
- [Haramain catalog and source rules](../base-station/HARAMAIN-CENTER.md)
- [Safety design decision](adr/0001-never-machine-translate-quran.md)
