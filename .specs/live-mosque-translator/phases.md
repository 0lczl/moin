# Phases: Live Mosque Translator

> Source spec: `.specs/live-mosque-translator/spec.md`

## Architectural Decisions

- **Models**: `Session` for a live room and `Segment` for ordered content within it.
- **Routes**: `/live` creates a session, `/live/session/:sessionId` is for the administrator, and `/live/join/:sessionId` is for listeners.
- **Control**: The mosque administrator has a private management link or session secret; the public QR link is for listeners only.
- **Languages**: Every session has one target language, English or French. Language switching inside the room is unavailable.
- **Connectivity**: A long-lived real-time channel broadcasts state, segments, and attendance. Audio is sent as ordered short segments.
- **External services**: ASR, translation, and speech synthesis remain behind the server; provider keys never reach the browser.
- **Privacy**: Listeners do not sign in and their identities are not shown to the administrator. The stored record has private access.

---

## Phase 1: Create a Room and Join by QR

**User stories**: #1, #2, #3, #7, #8, #12
**Depends on**: — (none)

### What to build

Create a complete, demoable path from an administrator creating a named single-language session, to showing its QR code and identifier, to a listener joining from another browser. The administrator view shows a live connection count; the listener view shows the session name, language, and a waiting-for-translation state. This slice does not include microphone input or real translation yet.

### Acceptance criteria

- [ ] The administrator can open `/live`, choose English or French, enter a session name, and create the session.
- [ ] The administrator page shows an identifier, listener link, QR code, and a private management link that is not encoded in the QR code.
- [ ] A listener can open `/live/join/:sessionId` by QR or identifier and see the name and language before joining.
- [ ] The administrator’s connected count changes when listeners join and leave.
- [ ] A listener cannot reach administrator controls from the public join link.
- [ ] Clear states appear for an invalid, unknown, or ended session.

### Manual QA plan

1. **Create a session**: Open `/live` on a computer, enter `Masjid Al Noor — Friday Sermon`, choose English, and create a session. **Expected**: An administrator screen shows a QR code, identifier, and sharing link.
2. **Join by phone**: Scan the QR code from a phone on a working network. **Expected**: The phone shows a confirmation page with the session name and English, then joins the waiting state and increases the count on the computer.
3. **Keep management private**: Open the listener link in another browser. **Expected**: It does not show microphone or end-session controls.
4. **Reject a bad identifier**: Open `/live/join/invalid`. **Expected**: A clear message appears without a blank page or internal details.

---

## Phase 2: Audio Segment to Live Translated Text

**User stories**: #4, #5, #9, #11, #14
**Depends on**: Phase 1

### What to build

Add a narrow live path from the administrator microphone to short Arabic audio segments, then to Arabic transcript and target-language translated text delivered over the real-time channel. The administrator sees microphone and segment status, and the system stores timing for every stage. This phase provides text translation only, without translated speech.

### Acceptance criteria

- [ ] The administrator can grant microphone permission from a computer or phone and start sending audio.
- [ ] Arabic transcript and translation reach listeners in the correct order.
- [ ] The administrator screen shows microphone state and the most recent segment’s processing state.
- [ ] The listener sees a waiting-for-next-segment state before text arrives and an actionable message for network loss or processing failure.
- [ ] The system records capture, ASR, translation, and delivery timing without storing secrets.

### Manual QA plan

1. **Use real audio**: Create an English session on a computer, permit microphone access, and speak one short Arabic sentence. **Expected**: Arabic text and English translation appear in that order on the listener phone.
2. **Use the imam’s phone**: Create a session on a phone, permit microphone access, and speak one short Arabic sentence. **Expected**: Translated text reaches another listener and the phone shows an active microphone state.
3. **Deny permission**: Deny the microphone prompt. **Expected**: The screen explains that permission is required and how to try again.
4. **Reconnect listener**: Disable the listener phone’s network, then restore it during a session. **Expected**: The interruption state appears, then connection returns without changing segment order.

---

## Phase 3: Optional Listening and the 50-Listener Experience

**User stories**: #6, #10, #11, #14
**Depends on**: Phase 2

### What to build

Add translated-speech generation for successful segments and make it available to each listener only through a listen button. Improve event delivery and the attendance count so a session targets 50 concurrent listeners. Translated text remains available if speech is delayed or fails.

### Acceptance criteria

- [ ] A segment’s listen button appears only after its translated speech is available.
- [ ] Listener audio never starts automatically when translation arrives or when the listener joins.
- [ ] Translated text remains visible when speech is delayed or fails, with a clear status.
- [ ] The administrator sees the real connected count without names or personal data.
- [ ] A practical load measurement supports 50 concurrent listeners while preserving segment order.

### Manual QA plan

1. **Listen by choice**: Send a successful segment to an English session and open it on a phone. **Expected**: Text appears first and no sound plays until the listener presses listen.
2. **Speech failure**: Use a test environment where the speech provider fails for one segment. **Expected**: Text remains visible and speech availability is explained without stopping the session.
3. **Fifty listeners**: Connect 50 simulated clients or devices to a session. **Expected**: The administrator sees a count near 50 and text segments arrive in order without identities appearing.
4. **Phone playback**: Use headphones on a phone and press listen. **Expected**: Playback stays within the page and no following segment starts without another listener choice.

---

## Phase 4: End Session and Preserve a Demo-Ready Record

**User stories**: #5, #6, #11, #13, #14
**Depends on**: Phase 3

### What to build

Complete the session lifecycle: the administrator ends the room, listeners are notified, segments, results, and timing are saved, and the administrator can open a private record. This phase prepares a reliable judge-demo journey: create room, join by QR, speak Arabic, read translation, optionally listen, then save the session.

### Acceptance criteria

- [ ] Only the administrator can end a session from the management view.
- [ ] Audio input stops at the end and listeners see a clear completion message.
- [ ] The session, segments, results, and timing save successfully, or a clear save-failure state appears.
- [ ] The public listener link cannot open the saved session record.
- [ ] The administrator can review the session name, language, time, text segments, and available speech.

### Manual QA plan

1. **End normally**: Run a session with an administrator and listener, send two segments, then press end session. **Expected**: Microphone input stops, the listener sees completion, and a private record appears for the administrator.
2. **Protect the record**: Copy the public listener link after the session ends and open it in a private window. **Expected**: It cannot reveal saved segments or the administrator view.
3. **Handle storage failure**: Use a test environment where saving fails at session end. **Expected**: A retryable save-failure message appears and the interface does not say the record was saved.
4. **Complete a full demo**: From a phone and computer, create a French session, scan the QR code, speak an Arabic sentence, read the text, press listen, and end the session. **Expected**: The whole journey completes clearly using Moin identity.
