# Free Render judging demo

This deploys the existing three-page Moin pilot to one **free** Render web
service. It is a disposable judging environment, not the persistent pilot in
`deploy/README.md`. The three provider keys stay in Render's secret environment
variables. The service serves Recording Studio, Haramain Video Center, and Live
Translator from one HTTPS URL.

## Create the service

1. Connect the `0lczl/moin` GitHub repository to Render. If it is missing from
   the picker, [configure Render's GitHub App](https://github.com/apps/render/installations/new)
   for **Only select repositories → moin**.
2. In Render, choose **New → Blueprint**, select `0lczl/moin`, and use the
   repository's `render.yaml`.
3. Confirm that `moin-judges-0lczl` is a **Free** web service. Do not upgrade
   the plan or add a paid database or disk.
4. Enter `GROQ_API_KEY`, `DEEPL_AUTH_KEY`, and `ELEVENLABS_API_KEY` when Render
   requests secret values. Never put them in GitHub, a screenshot, or chat.
5. Deploy and wait for `/healthz` to respond with `{"status":"ok"}`. Render sets
   `RENDER_EXTERNAL_URL`; Moin uses it for strict same-origin checks and QR
   links, so no hostname configuration is needed.
6. Open `/`, `/haramain`, and `/live` at the Render URL. Process an authorized
   short audio clip, confirm Arabic/English/French text and speech, then join
   a live room from a second browser. The result is unverified until these
   checks pass on the actual Render service.

## Free-tier limits

- Render Free has 0.1 CPU and 512 MB RAM. Actual media throughput and 50
  listener capacity have **not** been measured on this instance. Start the
  judge test with a short clip; do not claim a performance target from local
  Mac results.
- After 15 idle minutes the service sleeps. The next request can take about a
  minute to wake it. Local files, live rooms, recordings, and the in-app spend
  ledger disappear on sleep, restart, or redeploy. Download wanted results
  immediately. The application flags this state in its Recording Studio UI.
- A live room works only while the service is awake. Its state cannot survive
  a restart; the host must create a new room.
- Because the in-app ledger is ephemeral, set provider-side limits or alerts
  on the Groq, DeepL, and ElevenLabs keys before inviting judges. The app's
  per-address throttles are useful but do not replace account-side caps.
- The bundled QuranEnc registry is an attributed, frozen source snapshot.
  Review [`QURANENC_NOTICE.md`](../QURANENC_NOTICE.md) before public use and
  update the approved editions when the publishers release a new version.

Official references: [Render Free limitations](https://render.com/docs/free),
[Render compute plans](https://render.com/docs/compute-plans),
[Render Blueprints](https://render.com/docs/infrastructure-as-code),
[Render default environment variables](https://render.com/docs/environment-variables).
