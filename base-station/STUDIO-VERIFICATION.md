# Moin Studio verification — 2026-09-22

Story: select local recorded Arabic media in the website, upload it to the
loopback service, process it with the existing local machine, and read/listen
to the resulting Arabic/English/French material.

| Boundary | Evidence |
| --- | --- |
| UI and brand | Moin signal mark and local IBM Plex Sans Arabic fonts loaded; narrow layout inspected; 1280px geometry confirmed a 474px/451px two-column workspace |
| Browser → API | File chooser selected approved oWj_w6LRuUY.wav; Process recording returned an accepted job and visible processing status |
| API → models | Job b46c5274f83100547531d468 completed with zero failures and zero withheld segments using the configured local candidate |
| Models → saved result | Arabic, EN, FR, source WAV, result JSON, original AIFF synthesis, and browser WAV speech exist in the job output |
| Result → UI | Read & listen opened the newly processed job, showing the French translation and language-specific download/audio controls |
| Audio → browser | Explicit Play French audio button changed to Pause audio; audio element reported paused=false, readyState=4, no error, currentTime advancing, duration 19.780227 seconds |
| Automated suite | 77 tests passed, including real loopback HTTP tests with fake inference |

Browser automation of the native audio play control crashed the in-app tab.
Added an explicit accessible playback button; browser playback through that
button was verified successfully, then paused. No claim is made about whether
that native-control crash affects other browsers.

No meaning-quality scores were assigned. The benchmark lock, raw candidate
outputs, and anonymous review mapping were not changed. The V1 review goal is
still paused pending human reviewers. No live or YouTube website ingestion is
claimed by this delivery.
