# Phases: Haramain Video Center

> Source spec: `.specs/haramain-video-center/spec.md`

## Architectural Decisions

- **Catalog**: Manually curated data for mosque, imam, official source, and video. There is no open search in the first release.
- **Routes**: `/haramain` for the center, `/haramain/:mosque` for one mosque’s content, and `/haramain/video/:videoId` for the reader.
- **Results**: Reuse stored processing results associated with the video identifier and pipeline version.
- **Service boundary**: ASR, translation, and speech synthesis run on the server; provider keys remain secret.
- **Broadcasts**: A live broadcast is presented as official content; it does not mean real-time translation is enabled.
- **Portraits**: The six featured imams have verified, locally served photos paired with their names; asset order alone is not proof of identity. This enhancement is also included in the later frontend design plan.

---

## Phase 1: Discover a Mosque and Official Video

**User stories**: #1, #2, #3, #5, #10, #11
**Depends on**: — (none)

### What to build

Create a browsable center that presents the Grand Mosque and the Prophet’s Mosque, followed by a page for each mosque containing an initial catalog of official recorded videos from three imams. A visitor can choose an imam, see verified video cards, and open a simple video details page before processing is added.

### Acceptance criteria

- [ ] A visitor can open `/haramain` and choose either mosque.
- [ ] Each mosque page shows three imams and at least one official video per imam where available.
- [ ] Imam filtering works and returns cards from official sources only.
- [ ] Every card shows a title, source, official source link, and `recorded` state.
- [ ] The expansion notice is visible.
- [ ] The page works in Arabic and English on phones and computers, with correct Arabic directionality.

### Manual QA plan

1. **Choose a mosque**: Open `/haramain` on a 1440px-wide computer and choose the Grand Mosque. **Expected**: Only Grand Mosque content appears, including three imams and cards linked to official sources.
2. **Filter by imam**: On `/haramain/makkah`, choose an imam. **Expected**: Only that imam’s cards remain; a clear empty state appears if no video exists yet.
3. **Check source trust**: Open the source link on one card. **Expected**: An approved official organization opens in a new tab.
4. **Check mobile Arabic**: Open `/haramain` on a 390px-wide phone and switch to Arabic. **Expected**: No text or card overflows, and Arabic displays right-to-left.

---

## Phase 2: Recorded Video to Moin Reader

**User stories**: #6, #7, #8, #9
**Depends on**: Phase 1

### What to build

Connect a recorded-video card to the existing Moin pipeline. A visitor can start processing an official video or follow work already in progress, then open a saved result in a reader with original Arabic audio and transcript, English and French translations, and optional spoken output.

### Acceptance criteria

- [ ] Opening `/haramain/video/:videoId` presents the video source, current state, and saved result when ready.
- [ ] An unprocessed video creates one processing job that can be followed without starting duplicate work when reopened.
- [ ] The reader presents original Arabic, English, and French after processing completes.
- [ ] No translated audio starts before the visitor presses listen.
- [ ] Clear states exist for loading, processing, source failure, and partial processing failure.

### Manual QA plan

1. **Process an official video**: Open `/haramain/video/:videoId` for a short unprocessed video and start processing. **Expected**: Progress appears, followed by a reader containing Arabic audio, Arabic text, and both translations.
2. **Reuse a result**: Open the same video in a second window during processing or after completion. **Expected**: It follows the active state or presents the saved result; no second job begins.
3. **Optional speech**: Switch to English and press listen. **Expected**: Nothing plays before the press; then only available English speech plays.
4. **Unavailable source**: Open a catalog video marked unavailable. **Expected**: A clear explanation and source link appear without internal error details.

---

## Phase 3: Official Broadcasts and Availability

**User stories**: #4, #9
**Depends on**: Phase 1

### What to build

Add a distinct live-broadcast area to each mosque page. It presents an available official broadcast with its source link and verification time, or clearly explains that no broadcast is available without confusing it with recorded content.

### Acceptance criteria

- [ ] Live broadcast appears visually separate from previous-video archives.
- [ ] When an official broadcast is available, the visitor can open the source page or view it through an allowed method.
- [ ] When none is available, the page states that clearly rather than showing an empty or outdated card.
- [ ] The interface does not imply that real-time translation is enabled.

### Manual QA plan

1. **Available broadcast**: Add an available official broadcast to a test catalog and open `/haramain/makkah`. **Expected**: A clear broadcast section shows the official link and verification time.
2. **No broadcast**: Open a mosque with no current broadcast. **Expected**: The interface states that none is available and does not reuse an archive card in the broadcast area.
3. **Check wording**: Review text around the broadcast area. **Expected**: It makes no promise of real-time translation or completed processing merely because a broadcast is open.

---

## Phase 4: Content Management and Demo Readiness

**User stories**: #3, #5, #9, #10, #11, #12
**Depends on**: Phase 2, Phase 3

### What to build

Complete the presentation experience with managed catalog data and source states, accessibility and responsive improvements, correctly identified portraits for the six featured imams, clear messages, and a small stable set of official content for a judge demonstration.

### Acceptance criteria

- [ ] The Moin team can update a source, video, or availability state through a clear content-management workflow.
- [ ] A non-official, duplicate, or incomplete source cannot appear in the center.
- [ ] The interface handles an empty catalog, processing failure, and broadcast-source failure with useful messages.
- [ ] The interface follows Moin identity and remains usable with keyboard and touch controls.
- [ ] Each featured imam has a correctly matched portrait and visible bilingual name; image failure leaves a named, usable selection control.
- [ ] A documented demo journey exists: choose mosque, open video, read Arabic, choose translation, and request speech.

### Manual QA plan

1. **Update a source**: Change a video title or state using the approved management workflow, then open `/haramain`. **Expected**: Only the correct card reflects the update.
2. **Empty catalog**: Open a mosque with no videos in the test environment. **Expected**: A useful empty state appears and navigation remains intact.
3. **Accessibility**: Navigate from `/haramain` to the reader using only the keyboard. **Expected**: Focus is visible and filters, tabs, and listen controls are reachable.
4. **Judge demo**: Complete the full journey on a phone and computer using a prepared official video. **Expected**: No route is broken; Arabic, translation, and optional speech are clear.
5. **Verify portraits**: Open `/haramain/makkah` and `/haramain/madinah` and compare all six displayed portraits with confirmed identities and source records. **Expected**: Each portrait belongs to the named imam, displays without distortion on phone and computer, and has an accessible name; blocking one image leaves its named filter usable.
