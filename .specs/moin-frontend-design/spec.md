# Spec: Moin Welcome and Bilingual Frontend

## Problem Statement

Moin currently opens directly into the recording studio. A first-time visitor, including a hackathon judge, does not get a short explanation of what Moin does or an easy choice among the recording studio, Haramain videos, and live translator. The studio itself is English-only, while the other two areas have separate Arabic/English controls that remember different preferences. Navigation and presentation vary between areas. The result feels like several tools rather than one understandable website.

## Solution

Make `/` a public welcome page and move the existing recording studio to `/studio`. The welcome page follows the *structure and explanatory rhythm* of the [Tahseel welcome page](https://tahseel-web.vercel.app/welcome): a direct opening statement and action, a real visual example, a few plain-language steps, and a closing invitation to try the product. Its visual identity is Moin's approved logo, deep green, ivory, gold, and typography, rather than Tahseel's visual identity.

The primary action is **Try the recording studio**. Clear secondary paths lead to Haramain videos and the live translator. An existing real Moin example and fresh screenshots explain the output without requiring a running processing job or a newly produced promotional video. The welcome page distinguishes Arabic source audio, machine-generated Arabic text, English/French translations, and optional translated speech. It presents the service as experimental and makes no unsupported accuracy or real-time performance claim.

Give all four areas a consistent Arabic/English interface-language control and recognizable navigation. A first-time visitor sees Arabic if their browser's preferred language is Arabic, and English otherwise; their explicit choice is remembered across pages. The interface language does not change the Arabic source material, translation target, or language of an existing live room.

## User Stories

1. As a first-time visitor, I want to understand Moin in a few simple words, so I can decide whether it helps me follow Arabic teaching.
2. As a visitor, I want one prominent way to try a recording, so I can reach the working studio without guessing where to start.
3. As a visitor, I want to see a real example of Moin's input and output, so I can understand what the machine produces before uploading anything.
4. As a visitor, I want to discover the Haramain video center and live translator, so I can choose the experience that fits my situation.
5. As a visitor, I want to know the three basic steps and the limits of the experiment, so I understand what to expect without an exaggerated quality promise.
6. As an Arabic-speaking visitor, I want the complete interface in natural right-to-left Arabic, so I can use it comfortably.
7. As an English-speaking visitor, I want the complete interface in English, so I can use it comfortably.
8. As a returning visitor, I want my explicit interface-language choice to follow me across the welcome page, studio, Haramain center, live translator, and live-room entry, so the website feels consistent.
9. As a studio user, I want uploads, YouTube import, processing states, errors, result reading, and download controls to be understandable in the selected interface language, so the newly bilingual studio remains usable end to end.
10. As a visitor, I want to move among the welcome page and three tools with clear current-location cues and a way back, so I do not feel trapped inside a page.
11. As a visitor on a phone or using a keyboard, I want readable layout, accessible controls, and visible focus, so I can complete the same journeys as a desktop visitor.
12. As a visitor on the free public demo, I want the welcome page to load and explain Moin even when processing is unavailable or the server has no saved results, so I can still navigate to a working area.
13. As a Haramain video visitor, I want to see a correctly identified photo and name for each featured sheikh, so I can recognize whom I am choosing before opening his videos.

## Acceptance Criteria

- [ ] `/` presents the Moin welcome page; `/studio` presents the existing recording workflow and result reader without losing their behavior. Existing Haramain and live routes remain reachable, including direct links to nested pages.
- [ ] The first welcome viewport contains the approved Moin logo, a specific plain-language description, a prominent action to `/studio`, a secondary jump to the explanation, and an Arabic/English interface-language control.
- [ ] The welcome page includes a real, clearly labeled example and current product screenshots, a concise explanation of the user journey, and clear links to all three areas. The explanatory section works without a live job or server-persisted result.
- [ ] The Haramain center displays a portrait and visible Arabic/English name for each of its six featured sheikhs: Sheikh Abdulrazzaq Al-Badr, Sheikh Saleh Al-Usaimi, Sheikh Omar Falata, Sheikh Abdulsalam Al-Shuwaier, Sheikh Hassan Bukhari, and Sheikh Abdulrahman Al-Sudais. A portrait is never the only way to identify or select a sheikh.
- [ ] Each portrait is matched to the correct person before publication, uses an accessible localized text alternative, crops without distortion, and remains clear on desktop and phone. A missing image has a named fallback rather than a broken-image icon.
- [ ] The welcome copy says that outputs are machine-generated and require review for important religious meanings. It makes no numerical accuracy, guaranteed-latency, or always-available speech claim.
- [ ] The approved Moin visual identity is used throughout. The Tahseel reference informs page organization, not copied branding, colors, illustrations, wording, or screenshots.
- [ ] Every area, including the studio and live-room entry, exposes the same recognizable Arabic/English interface control. An explicit choice persists across routes; absent a choice, Arabic-browser visitors start in Arabic and others in English.
- [ ] Changing interface language updates visible navigation, labels, instructions, processing/status/error messages, and result controls; it updates document `lang` and `dir`. Arabic source passages retain right-to-left direction in either interface language.
- [ ] Interface language remains separate from English/French translation tabs and from a live room's chosen target language.
- [ ] Visitors can move between the welcome page and the three tools through visible navigation; active location and parent/back links are clear where a page has nested levels. Browser back/forward navigation works.
- [ ] Desktop and narrow-phone layouts have readable text, touch-sized controls, keyboard-accessible navigation, visible focus, sufficient contrast, and reduced-motion behavior. Meaning and primary actions are visible without relying on animation.
- [ ] Existing processing, translation, speech, and live-room APIs and their behavior are unchanged by the design work.

## Implementation Decisions

### Architecture & Schema

- This is a frontend and page-routing change. It introduces no database schema, account system, model selection, or processing pipeline change.
- The welcome's real example and screenshots are stable, locally served presentation assets. They are not fetched from ephemeral processing history. Use existing approved material and freshly captured screenshots of the current product; label any machine output as an example, not a verified translation.
- The six attached portraits are candidate assets for the Haramain center. Store approved, web-optimized copies locally, associate each with the existing sheikh identity, and record its source and permission for public use. Do not infer a person's identity from attachment order alone.
- The existing Moin identity is the visual authority. A small shared set of navigation, language, typography, color, and focus conventions should serve all pages while preserving task-specific layouts.

### Interfaces & Contracts

- Public destinations are `/` for welcome, `/studio` for recording, `/haramain` for the video center, and `/live` for the live translator. Existing nested Haramain and live-room URLs continue to open directly.
- The brand/home link leads to `/`; the recording-studio navigation item leads to `/studio`.
- Store one explicit interface-language preference for the site; use browser preference only when none has been saved. If browser storage is unavailable, the switch still works for the current page.
- The interface has two locales, Arabic and English. This control is distinct from selecting English or French as a translation output.

### Behavior & Interactions

- Welcome is a **Persuade** surface: introduce the product, show honest proof, then offer a clear action. Inner pages are **Operate** surfaces: the task and feedback remain primary.
- Suggested content sequence: hero and primary action; real Arabic-to-translation example with screenshots; three ways to use Moin; three simple steps; final invitation and concise experimental-use note. Use short, concrete copy rather than technical model names or superlatives.
- The primary hero action opens `/studio`. Secondary links open `/haramain` and `/live`; an explanation link scrolls to the real example.
- The welcome page does not depend on processing API readiness. If any optional demonstration media fails, text, screenshots, and route links remain usable.
- Locale changes preserve the current route and, where practical, the visitor's place in a form or result. They must not silently change the target language of a live session.
- Navigation on inner pages retains a clear path back to welcome; Haramain collection/video views and live room views keep their own visible location/return cues.
- On each mosque's Haramain page, show the featured sheikhs as recognizable portrait-and-name choices connected to the existing video filter. Keep the selected state understandable without relying on color or the photograph. Where a video detail identifies a featured sheikh, use the same approved portrait consistently when the layout permits.

## Testing Decisions

- Automated checks should cover route availability after the move, direct links, default and persisted locale behavior, and the separation between interface locale and translation/live-room target language.
- Manual checks should cover Arabic and English copy, real-example labeling, desktop and phone layouts, keyboard and screen-reader navigation, visible focus, reduced motion, and the existing studio upload-to-result journey in both interface languages.
- Manually verify all six portrait-to-name matches with the user-provided identities, image crop, alternate text, fallback state, and public-use provenance before release.
- Do not add tests that merely compare static copy or mirror implementation details.

## Out of Scope

- **Backend performance and model work**: processing speed, ASR, translation, TTS, and live-stream architecture remain separate tasks.
- **New promotional video**: use the existing real example and product screenshots now.
- **More interface or translation languages**: only Arabic/English interface and existing Arabic source with English/French outputs are in this release.
- **New accuracy claims**: the human translation and ASR review does not justify a universal percentage on the welcome page.
- **Frontend framework migration**: a new framework or starter kit is not required to deliver this design.

## Open Questions

- Confirm which of the six supplied image files belongs to each named sheikh, and the source or public-use permission for each, before implementing the portraits. The attachment order alone does not establish identity.
- Exact final marketing wording and selected screenshots should be reviewed against the implemented page before release.

## Further Notes

- The welcome should feel calm and trustworthy, appropriate for religious learning and careful listening. The signature moment is a clear transition from the Arabic source to readable meaning, not a decorative AI motif.
- The [Tahseel welcome page](https://tahseel-web.vercel.app/welcome) was reviewed as a structural reference: short hero, explainer material, simple steps, and a clear way into the product.
