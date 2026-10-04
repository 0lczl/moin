# Spec: Haramain Video Center

## Problem Statement

Moin users need a trusted way to find content from the Grand Mosque in Makkah and the Prophet’s Mosque in Madinah, then understand it through Arabic transcription, English or French translation, and optional spoken output. The current experience processes a recorded file or a manually supplied recorded YouTube link. It does not provide visitors with a clear center for official sources, imams, live broadcasts, or previous videos.

## Solution

Add a dedicated Haramain Video Center. A visitor starts by choosing the Grand Mosque or the Prophet’s Mosque. The first release presents three imams for each mosque, each with a correctly identified portrait and visible name, a distinct live-broadcast area when one is available, and a clear route to previous videos. The center uses only official sources curated by the Moin team, such as official YouTube channels and official Presidency pages that publish video.

Opening a recorded video takes the visitor to the Moin reader: original Arabic audio, Arabic transcript, English and French translations, and an optional button to listen to translated speech. The page states that more imams and sources will be added later, and it does not claim that Haramain broadcasts receive real-time translation in this release.

## User Stories

1. As a visitor, I want to see the Grand Mosque and the Prophet’s Mosque as clear choices, so I can reach the content I want.
2. As a visitor, I want to see three imams for each mosque, so I can filter content by imam.
3. As a visitor, I want to know that content comes from an official source and see its link, so I can trust the origin of the video.
4. As a visitor, I want live broadcasts to appear in a separate area when available, so I can distinguish them from recorded videos.
5. As a visitor, I want to browse previous videos for the selected mosque, so I can watch previously published lessons and sermons.
6. As a visitor, I want to open a recorded video in the Moin reader, so I can play the Arabic audio and read the original transcript and translations.
7. As a visitor, I want to choose English or French, so I can understand the video in my language.
8. As a visitor, I want translated audio to play only when I press a listen button, so I control when playback starts.
9. As a visitor, I want to see an understandable status while processing is in progress, fails, or a video is unavailable, so I know what to do next.
10. As a visitor on a phone or computer, I want a clear Arabic and English interface with correct Arabic directionality, so I can use the center comfortably.
11. As the Moin team, I want the center to state that coverage will expand to additional imams and sources, so the first-release scope is honest and clear.
12. As a visitor, I want to see the correct photo and name for each featured sheikh, so I can recognize and select him before browsing his videos.

## Acceptance Criteria

- [ ] A dedicated center clearly presents the Grand Mosque and the Prophet’s Mosque.
- [ ] The first-release catalog contains three defined imams for each mosque.
- [ ] All six featured sheikhs have correctly identified, visible portraits paired with their Arabic/English names on the mosque pages. The portraits are accessible, responsive, and have named fallbacks if an image fails.
- [ ] The catalog contains only official sources manually approved by the Moin team.
- [ ] A live broadcast appears separately when available, with a clear state when no broadcast is available.
- [ ] A visitor can browse previous videos and filter visible content by mosque and imam.
- [ ] A recorded video opens in a reader that supports original Arabic, English, and French.
- [ ] Translated audio never starts automatically and requires a visitor action.
- [ ] The page presents processing, failure, and unavailability states without exposing secrets or internal errors.
- [ ] The interface works on phones and computers and uses the approved Moin logo, colors, and typography.
- [ ] The interface explicitly says that more imams and sources will be added later.

## Implementation Decisions

### Architecture & Schema

- The Moin team maintains a manually curated catalog of official sources. The first release does not use open YouTube search or unverified recommendations.
- The catalog consists of mosques, imams, sources, and videos. Each imam has a stable identity, bilingual name, mosque association, and an approved portrait reference. Each video includes its mosque, imam when known, title, official URL, content type (`live` or `recorded`), availability state, publication or broadcast time when available, and a permitted thumbnail.
- The six user-supplied images are locally served, web-optimized portrait assets. The owner confirmed each image-to-person match and affirmed public use in Moin on 2026-10-04; the original photographer and publication source were not independently verified.
- A stored processing result is associated with the video identifier, the Moin pipeline version, and the language so that completed work can be reused.
- Live broadcast is a discovery and viewing feature in this center. Real-time microphone-to-translation belongs to the Live Translator and remains separate.

### Interfaces & Contracts

- `/haramain` presents both mosques and their broadcast states.
- `/haramain/:mosque` presents the mosque’s previous content, available broadcast, and imam filters.
- `/haramain/video/:videoId` presents source information and either a stored result or processing status.
- A processing request returns a status identifier that can be checked until completion or failure, then returns Arabic text, translations, available audio, and safe timing information.
- Speech recognition, translation, and speech-synthesis keys remain on the server and never reach the browser.

### Behavior & Interactions

- The visitor chooses a mosque, then an imam, video, or available broadcast.
- The mosque view presents each featured imam as a portrait-and-name choice. Filtering and selected state remain clear to keyboard and screen-reader users and when an image does not load.
- An unprocessed video starts one processing job or joins an existing job for that video. A previously processed video shows its saved result immediately.
- The reader starts with Arabic, then allows English or French selection.
- The listen button appears for the chosen language only when audio is available or can be requested. Text remains available when speech cannot be generated.
- When a source fails or becomes invalid, it is removed from the catalog or shown as unavailable with its official source link rather than a blank page.

## Testing Decisions

- Unit tests validate catalog data and reject incomplete, duplicate, or non-official sources.
- Integration tests cover mosque selection, imam filtering, opening a video, joining existing processing, and reading a saved result.
- Interface tests cover available and unavailable broadcasts, empty or removed videos, and processing and failure states.
- Integration tests use local substitutes for ASR, translation, and speech synthesis, followed by a manual check using a real official video in a configured environment.
- Manual checks cover Arabic and English layouts, phone and computer use, original playback, and translated playback.
- Manual checks also compare all six displayed portraits with verified names, image crops, alternate text, fallback states, and recorded public-use provenance.

## Out of Scope

- **Real-time translation of Haramain broadcasts**: this requires an independent live-audio session and is covered by the Live Translator specification.
- **All imams and sources**: the first release begins with three imams per mosque.
- **Open search and downloading from arbitrary internet videos**: the first release protects source trust and source restrictions.
- **User accounts and public comments**: these are not required for the initial viewing experience.

## Open Questions

- Any additional official source links still require curation before they enter the catalog.
- Retention time, storage limits, and cost limits for processed videos and speech files require an operational decision before launch.
- The maximum video length shown to users requires a decision after performance measurement in the target environment.

## Further Notes

The six featured sheikhs are Sheikh Abdulsalam Al-Shuwaier, Sheikh Hassan Bukhari, and Sheikh Abdulrahman Al-Sudais for Makkah; and Sheikh Abdulrazzaq Al-Badr, Sheikh Saleh Al-Usaimi, and Sheikh Omar Falata for Madinah. The design follows the approved Moin presentation identity. Listening and understanding remain central, and Arabic text must remain readable right-to-left in both Arabic and English interfaces.
