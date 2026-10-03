# Haramain Video Center

Open `http://127.0.0.1:8787/haramain` after starting Moin Studio. The center
shares the Studio's local processing queue, Whisper large-v3, DeepL, and
ElevenLabs configuration. It is currently a local pilot, not a public website;
another device cannot join this loopback server.

The first catalog contains three named scholars and one short recorded lesson
per scholar in each mosque. All six seeded recordings were checked on 2026-10-03 against the
uploader channel ID and duration returned by YouTube. The source channels are
the verified institutional channels for the Grand Mosque lessons, Imams and
Muezzins Affairs, and the Prophet's Mosque lessons. The catalog records source
and video URLs; it does not perform a fresh YouTube verification on every page
load. A curator must recheck a link before a public demonstration.

## Curate content

1. Edit [`moin_haramain/catalog.json`](moin_haramain/catalog.json) to update a
   title, availability state, or add a completed recording by one of the six
   listed scholars. Each entry needs a canonical YouTube Watch URL, source ID,
   scholar ID, mosque ID, bilingual title, and duration in seconds.
2. Confirm on the publishing channel that the video belongs to its listed
   source, is a completed recording, and is no longer than five minutes if it
   should be processable. The importer checks the publishing channel again
   before processing; a mismatch fails the job. Update source `verified_at` when rechecking the
   channel. Update catalog `updated_at` for each editorial change.
3. Run `.venv/bin/python -m moin_haramain.catalog validate` from
   `base-station`. Refresh the center page. The server reads the catalog again
   on each request, so no restart is needed. An invalid catalog is withheld
   and the page shows an availability error.

New institutional publishing channels require an explicit addition to
`APPROVED_CHANNELS` in [`moin_haramain/catalog.py`](moin_haramain/catalog.py),
followed by verification of the organization and channel ID. A source name or
an `official` label in JSON cannot authorize an arbitrary channel. Duplicate,
noncanonical, mismatched, or incomplete video records are rejected.

The two broadcast records default to `unavailable`. Only set one to
`available` after verifying that the institution is actually broadcasting,
entering its official YouTube live URL, and recording the verification time.
Set it back to `unavailable` and clear its URL/time when the broadcast ends.
No automatic live-status polling runs in this pilot. The broadcast section
links to the official source and never promises live translation.

## Judge demonstration

1. Start Studio with the local Whisper model and private DeepL and ElevenLabs
   environment variables as described in [`STUDIO.md`](STUDIO.md).
2. Open `/haramain`, choose Makkah or Madinah, and choose one of the listed
   scholars.
3. Open the recorded lesson in Moin. Check its official source link before
   starting the demonstration.
4. Press **Prepare transcript and translations**. Wait for the job status to
   become ready. Reopening the same lesson follows that job; a completed
   result remains available after Studio restarts.
5. Play the Arabic original, read its transcript, switch to English or French,
   and press **Listen to this translation** if speech was created. Playback
   never starts automatically.

For a reliable presentation, process one approved short recording in advance
and inspect the Arabic and both translations. The six catalog entries have not
all undergone a human translation review. French in particular must not be
presented as validated religious translation. A recording that YouTube removes
or restricts may fail import; the page preserves its official source link and
shows a safe failure state.
