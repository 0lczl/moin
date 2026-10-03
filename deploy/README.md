# Hosted Moin pilot: deployment runbook

This is a prepared pilot deployment, not evidence that a public site is live.
It runs the three pages on one small Linux host behind HTTPS: Recording Studio,
Haramain Video Center, and Live Translator. The worker uses Groq's exact
`whisper-large-v3` model ID for ASR, DeepL for ordinary translation, the
approved QuranEnc renderings for the Qur'an guard, and ElevenLabs for optional
speech. The existing local Mac workflow remains available.

## Before deploying

1. Provision a Linux host with Docker Compose, persistent disk, and ports 80/443 open. For this pilot, the recommended starting size is a DigitalOcean Basic Droplet with **2 shared vCPU, 4 GiB RAM, and 80 GiB SSD** (USD 24/month at the checked October 2026 list price). Choose Ubuntu, a region near the intended audience, SSH-key login, and a cloud firewall permitting only SSH from the operator and HTTP/HTTPS to the public. This is a starting capacity, not a measured throughput guarantee. A smaller 2 GiB host may struggle with concurrent media conversion and 50 clients. Use a temporary HTTPS hostname; a raw IP address is insufficient for the configured HTTPS origin.
2. Confirm the actual plans and usage caps in the Groq, DeepL, and ElevenLabs dashboards. Set provider-side caps or alerts and a host billing alert. Moin's local ledger is an additional conservative stop, **not a guarantee that invoices stay below USD 100**: subscription charges, tax, retries outside this service, and price changes are outside it.
3. Create narrowly scoped API keys for Groq transcription, DeepL text translation, and ElevenLabs text to speech. Do not put them in Git or send them in chat.
4. Check the QuranEnc attribution and update obligations in `base-station/benchmark-data/rendering-research.md` before a public demonstration using saved Qur'an renderings.

For a short trial before buying a domain, `<PUBLIC_IPV4>.sslip.io` resolves to
the Droplet IP (for example `203.0.113.7.sslip.io`). Set that exact hostname in
`MOIN_PUBLIC_HOST` after confirming DNS resolves to the new Droplet. Caddy then
requests an HTTPS certificate. This address relies on a third-party DNS service;
move to a domain you control before treating the address as a durable public
identity. DigitalOcean's bundled 4 GiB size and pricing are documented at
https://www.digitalocean.com/pricing/droplets and the temporary DNS scheme at
https://sslip.io/ .

Render Free is suitable for a disposable interface preview only. It sleeps
after 15 idle minutes and its filesystem is erased on sleep/restart/redeploy;
it cannot attach a persistent disk. That conflicts with Moin's seven-day
recording retention, private browser-owned results, live-room state, and durable
spend ledger. Running the current full app there would silently lose user data.
See https://render.com/docs/free .

## Build a release from the current Mac workspace

Run at the repository root:

```sh
python3 tools/package_hosted.py --out /private/tmp/moin-hosted.tar.gz
```

The bundle includes the locally staged, Git-ignored Qur'an rendering registry.
It excludes recordings, benchmark reviews, models, and `.env`. Its `manifest.json`
lists SHA-256 digests for every file. Transfer the bundle to the host through a
private channel, unpack it, and enter the `moin-hosted` directory.

## Start on the host

```sh
cp deploy/hosted.env.example .env
chmod 600 .env
```

Edit `.env` locally on the host: set `MOIN_PUBLIC_HOST` to the DNS name and
replace the three API key placeholders. Then run:

```sh
docker compose --env-file .env -f compose.hosted.yaml up -d --build
```

Caddy obtains TLS automatically for the configured hostname and proxies to
Moin on a private Docker network. Only Caddy publishes ports. Moin refuses to
start in public mode if the HTTPS origin, keys, persistent budget ledger,
provider selection, media binaries, or trusted rendering registry is missing.
Check container logs without printing `.env`:

```sh
docker compose --env-file .env -f compose.hosted.yaml logs --tail=100 moin caddy
```

Open `https://YOUR_HOST/`, `/haramain`, and `/live`. Process a short authorized
recording, create one live room, join from a second browser, verify Arabic and
translated text, request speech, end the room, and confirm a second visitor
cannot read the first visitor's private recording. Test microphone permission
and Safari/Chrome behavior on the actual devices. Measure live text latency and
50-listener behavior on the host before claiming either target is met.

## Operating limits and recovery

- One live room at a time, lasting at most 60 minutes; no more than 50 joined listeners. The live worker has a small bounded queue and stops accepting segments when it falls behind.
- Recorded uploads: at most 64 MB and five minutes; recorded YouTube links: completed videos of at most five minutes. Per-address starts are throttled. Browser-owned recordings are private; approved catalog recordings are public.
- Recording results and live media are removed after seven days. The process checks on startup and hourly. Do not create longer-lived host backups of these files without revisiting this policy.
- The in-process recorded queue is not durable across restarts. Interrupted jobs are marked as such and must be resubmitted. Preserve the `moin_data` volume on upgrades; never use `docker compose down -v` unless deletion of all pilot data is intended.
- The spend ledger reserves usage before provider calls and can stop new billable work. It does not reconcile invoices. Review dashboard usage daily during the pilot.
- The fewer-than-ten-second live text goal and 50 concurrent listener capacity are **not yet verified on a deployed host**. Do not advertise them as achieved.

The fastest way to stop public traffic is to stop the Caddy service. This does
not erase persisted recordings or the budget ledger:

```sh
docker compose --env-file .env -f compose.hosted.yaml stop caddy
```
