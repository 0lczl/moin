# Spec: Live Mosque Translator

## Problem Statement

A mosque may have worshippers who do not understand Arabic while the imam delivers a lesson or sermon in Arabic. A mosque administrator or imam needs to start a session from a laptop connected to the mosque microphone or from the imam’s phone, choose the translation language, and share a simple way to join. A listener needs to join from a phone browser without an app or account, read the translation, and optionally listen to it. The administrator also needs to see how many people joined and preserve the session after it ends.

## Solution

Add an independent page called Live Mosque Translator in Arabic and English. The administrator creates a session with a visible name and one target language: English or French. The system produces a unique identifier, a join link, and a QR code. Listeners scan the code or enter the identifier in their browser, then see the session name and language before joining.

The administrator captures short Arabic audio segments through the microphone. The server processes every segment through the Moin pipeline and delivers translated text to listeners in real time. Translated speech is optional when available and never starts automatically. The first release targets 50 concurrent listeners per session. The administrator sees the attendance count without personal listener data, and the platform saves the session record and results when the session ends.

## User Stories

1. As a mosque administrator or imam, I want to open the Live Mosque Translator in Arabic or English, so I can create a session easily.
2. As an administrator, I want to enter a visible session name and choose English or French before creating it, so listeners know that they joined the correct room.
3. As an administrator, I want a session identifier, link, and QR code, so I can share the session quickly with worshippers.
4. As an administrator, I want to start the microphone from a laptop connected to the mosque microphone or from the imam’s phone, so Arabic speech reaches the platform.
5. As an administrator, I want to see audio status, Arabic text, translated text, and processing status, so I know that the session is working.
6. As an administrator, I want to see a connected-listener count without personal data, so I know that listeners reached the session.
7. As a listener, I want to join from my phone browser by scanning a QR code or entering an identifier without an account or app, so registration does not block me.
8. As a listener, I want to see the session name and language before joining, so I avoid the wrong room or language.
9. As a listener, I want to see translated text as it arrives, so I can follow the meaning even if I do not play speech.
10. As a listener, I want to press a listen button to play translated speech, so I control audio on my phone.
11. As a listener, I want a clear message if the network disconnects, the session ends, or translation is delayed, so I understand the interruption.
12. As a listener, I want to leave and join a session in another language, so I do not have to change language inside a room that does not suit me.
13. As an administrator, I want to end the session and save its record and results, so I can review it later.
14. As the Moin team, I want to measure attendance and time from spoken segment to text and speech, so we can identify bottlenecks before making a speed claim.

## Acceptance Criteria

- [ ] An independent Live Mosque Translator page supports Arabic and English.
- [ ] An administrator creates a session with a visible name and exactly one target language: English or French.
- [ ] A session creates an unguessable identifier, join link, and QR code, plus a private management link unavailable to listeners.
- [ ] A listener joins in the browser by QR code or identifier without an account or app.
- [ ] Audio input can start from a laptop connected to the mosque microphone or from the imam’s phone after browser permission is granted.
- [ ] Translated text reaches listeners during the session in segment order.
- [ ] Translated speech never begins without an explicit listener action.
- [ ] The administrator sees the real-time connected count without listener identities or personal data.
- [ ] The first release targets 50 concurrent listeners per session for operation and testing.
- [ ] An ended session, its record, and its results are saved, with a clear state if saving fails.
- [ ] The interface clearly handles microphone permission, network loss, processing delay, external-service failure, and session end.
- [ ] ASR, translation, and speech-synthesis keys remain on the server.

## Implementation Decisions

### Architecture & Schema

- A **Session** represents one live room and contains an unguessable identifier, name, language, state, creation/start/end times, and current connected count.
- A **Segment** represents an ordered piece of audio within a session and contains Arabic audio, Arabic transcript, translation, stage statuses, and a translated-audio reference when available.
- The administrator uses a private management link or browser session that keeps the control secret outside the public join link. Listeners do not need accounts.
- The system uses a long-lived real-time channel to broadcast session state, attendance, text segments, and audio availability to listeners.
- Short audio segments travel from the administrator browser to a persistent backend service, then through ASR, translation, and speech synthesis before ordered results are broadcast.
- Results and recordings are stored under configurable retention and private access rules. Saved sessions are not public by default.

### Interfaces & Contracts

- `/live` presents language and session-name selection and creates a session.
- `/live/session/:sessionId` is the administrator view, authorized by the session’s private management secret.
- `/live/join/:sessionId` is the listener view and verifies that the session exists, is active, and has a declared language.
- The create-session request returns join and administrator links, an identifier, and QR data. It never returns the administrator secret to a public request.
- The audio channel accepts ordered segments only from the administrator and rejects listener audio or audio after session end.
- The update channel emits defined events: session state, listener count, Arabic transcript, translation, audio availability, and display-safe error.

### Behavior & Interactions

- The administrator selects language and name, creates the session, then is asked for microphone permission.
- The administrator screen shows the QR code and identifier in a large, mosque-display-friendly area.
- The listener confirms the session name and language before joining. Language cannot change inside a session; the listener exits and joins another language session instead.
- Translated text arrives first, segment by segment. The listen button appears when translated speech becomes available for a segment.
- A client attempts to reconnect after network loss and displays its connection state. It does not display segments out of order or twice.
- When the administrator ends a session, audio input stops, listeners receive a clear completion message, and results are saved.

## Testing Decisions

- Unit tests cover session identifiers, state transitions, management and join rules, and segment ordering.
- Integration tests cover a locally substituted microphone-to-ASR-to-translation-to-listener path with substitute external providers.
- Multi-client testing covers one administrator and 50 listeners, segment ordering, and attendance updates.
- Failure tests cover microphone permission, network loss, translation or speech failure, and ending a session with connected listeners.
- Manual real-device checks cover QR scanning, joining from a phone and computer, and listener-requested speech.
- Timing measurements cover capture to transcript and transcript to speech, with safe measurement storage.

## Out of Scope

- **Changing listener language inside one session**: each session has one language; the listener joins a different session when needed.
- **Native iOS or Android apps**: the first release is browser-only.
- **More than 50 concurrent listeners**: scaling follows live-infrastructure measurement.
- **Cloning or imitating the imam’s voice**: Moin uses licensed voices designed for the project.
- **Listener sign-in**: it is unnecessary for the initial joining experience.

## Open Questions

- Recording, text, and speech-file retention length and access ownership require a decision before public launch.
- The acceptable spoken-word-to-text-and-speech delay requires real measurement and a target before making a live-speed claim.
- Administrator accounts can be added later if management across multiple mosques or a long-term archive requires them.

## Further Notes

Arabic is always the source language in the first release. The administrator’s choice of English or French means that the room is intended for that listener language. Translated text is the primary experience; translated speech is delivered when the listener requests it. The interface uses the approved Moin identity and should feel calm, clear, and appropriate for a mosque.
