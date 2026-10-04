# Phases: Moin Welcome and Bilingual Frontend

> Source spec: .specs/moin-frontend-design/spec.md

## Architectural Decisions

- **Routes:** `/` is welcome; `/studio` is the existing recording studio; `/haramain`, `/live`, and their nested routes remain directly addressable.
- **Language:** Arabic and English are interface locales. Use the browser preference on a first visit and one saved explicit choice thereafter. Interface language never changes Arabic source content, English/French translation selection, or a live room's target language.
- **Visual identity:** Reuse the approved Moin logo, colors, typography, and restrained visual character. Tahseel informs the welcome page's explanation sequence, not its visual identity or claims.
- **Example:** The welcome example is a locally served, real Moin sample and current screenshots. It does not depend on a stored processing job or on API availability.
- **Sheikh portraits:** The six featured Haramain sheikhs have locally served, correctly identified photos with visible names and accessible fallbacks. Match each supplied image to the person and confirm public-use provenance before publication.
- **System boundary:** Preserve the current processing and live-room APIs. Only page routing needed for the new entry page changes outside the frontend.

---

## Phase 1: Open Moin through a clear welcome page

**User stories:** #1, #2, #6, #7, #10, #12
**Depends on:** —

### What to build

Make `/` a fast, bilingual welcome entry using the approved Moin identity. Give its first viewport a simple explanation, an unmistakable **Try the recording studio** action, a jump to the explanation below, and an Arabic/English control. Move the existing studio to `/studio` and update the home and studio destinations so visitors can enter the tool and return to welcome. Keep the welcome content independent of processing state. This phase is complete when a new visitor can understand the product and reach the functioning studio from the new root route.

### Acceptance criteria

- [ ] `/` opens the welcome hero in the appropriate first-visit interface language and offers the language switch.
- [ ] The primary action opens `/studio`, where the existing upload, YouTube import, job list, and reader remain available.
- [ ] A direct visit to `/studio` works, and the brand/home action returns to `/`.
- [ ] The welcome hero and route links remain usable when processing is unavailable.
- [ ] Desktop and phone layouts keep the headline, primary action, and language control readable and operable.

### Manual QA plan

1. **First visit:** Clear Moin site data, set the browser's preferred language to Arabic, and open `/`. **Expected:** Arabic hero text reads right-to-left, the Moin logo is intact, and the primary action is visible. Repeat with English preferred. **Expected:** English left-to-right layout.
2. **Enter and return:** From `/`, choose **Try the recording studio**; then use the Moin home link. **Expected:** `/studio` shows the existing recording form, then `/` returns to welcome. The browser Back button moves between them correctly.
3. **Direct studio URL:** Open `/studio` in a new tab. **Expected:** the recording studio loads directly, with the upload control and YouTube field present.
4. **No processing state:** In browser DevTools, block `/api/state` and refresh `/`. **Expected:** the welcome explanation and action remain visible and usable. Remove the block before further checks.
5. **Small screen:** Open `/` at a 390px viewport or on a phone. **Expected:** the logo, language control, headline, and primary action fit without horizontal scrolling or overlapping text.

---

## Phase 2: Show real output and make the three services recognizable

**User stories:** #3, #4, #5, #12, #13
**Depends on:** Phase 1

### What to build

Complete the welcome page's explanation in the Tahseel-inspired order: a real, clearly labeled Moin example with original Arabic audio, a short Arabic-text/translation excerpt, and current product screenshots; three concise paths to the studio, Haramain videos, and live translator; three plain-language steps; then a final invitation to try Moin. Make the experimental status and need to review important meanings clear. Keep media and screenshots local to the site so the explanation survives empty or expired processing history. In the Haramain path, make all six featured sheikhs recognizable with correctly matched, approved portraits and names on their mosque pages while retaining the existing video-filter behavior. This phase is complete when a visitor can see what Moin produces, choose the appropriate area, and recognize a sheikh before choosing his videos.

### Acceptance criteria

- [ ] The example identifies what is original source audio and what is machine-generated text or translation; it does not present output as independently certified correct.
- [ ] Example audio, excerpt, and screenshots load without a live job; optional-media failure leaves explanatory text and links intact.
- [ ] Each of the three areas has a short, accurate description and a working destination.
- [ ] The Haramain center shows a portrait and visible name for all six featured sheikhs; each photo maps to the right catalog identity and its selection filters the correct videos.
- [ ] Portraits have localized accessible alternatives, responsive crops, named fallbacks, and confirmed public-use provenance.
- [ ] Arabic and English versions use short, natural copy; neither promises an accuracy percentage, guaranteed live latency, or speech availability.
- [ ] The explanation, screenshots, and final action remain legible on desktop and phone.

### Manual QA plan

1. **Understand the example:** Open `/` and activate the hero's explanation link. **Expected:** the page scrolls to a labeled real example; the Arabic source, transcript, translation, and any playable audio are distinguishable, and the example is marked as machine-generated where appropriate.
2. **Independent content:** Open `/` in a new browser session with no previous Moin jobs. **Expected:** the example and screenshots are present without starting processing.
3. **Choose a service:** From `/`, open each service link in turn. **Expected:** the studio opens at `/studio`, videos at `/haramain`, and live translation at `/live`; browser Back returns to the same welcome page.
4. **Media fallback:** Temporarily block the example audio or an example image in DevTools and reload `/`. **Expected:** explanatory text, alternative text or fallback, and all service links remain usable.
5. **Read on a phone:** Open `/` at 390px and 768px widths. **Expected:** example labels, screenshots, three paths, steps, and final action have no clipped text or horizontal page scroll.
6. **Recognize the sheikhs:** Visit `/haramain/makkah` and `/haramain/madinah` in both interface languages. **Expected:** each mosque shows its three named sheikhs with correctly matched portraits; selecting each sheikh filters to that person's videos. Inspect the six source-to-name matches with the supplied reference images rather than trusting their attachment order.
7. **Portrait fallback and phone layout:** At 390px, view both mosque pages and temporarily block one portrait request. **Expected:** faces are not stretched or cut off awkwardly, names remain readable, and the blocked portrait has a named fallback without breaking the filter.

---

## Phase 3: Carry one interface language through every task

**User stories:** #6, #7, #8, #9
**Depends on:** Phases 1–2

### What to build

Complete Arabic/English localization of the studio, including forms, progress, job states, errors, result reader, tabs, playback, and downloads. Unify the existing separate Haramain and live language preferences with the welcome/studio control, including live-room entry. Apply the correct page direction and keep Arabic passages right-to-left regardless of interface locale. A visitor can select a language once and follow a full recording or live-room journey without switching UI languages unexpectedly. Translation output language and live-room target remain independent choices.

### Acceptance criteria

- [ ] The same recognizable language control and saved choice work on welcome, studio, Haramain, live translator, and live-room entry.
- [ ] With no saved choice, Arabic browser preference yields Arabic UI; otherwise the UI starts in English. An explicit choice overrides browser preference across routes.
- [ ] All studio interaction states, including unsuccessful upload/import and a completed result, are understandable in both interface languages.
- [ ] Document `lang` and `dir` reflect the interface; Arabic transcription remains RTL in English UI, and URLs, times, and filenames remain readable in Arabic UI.
- [ ] Switching the interface language does not change an English/French result tab or the target language of an existing live room.
- [ ] Reloading and moving between routes preserve the explicit interface choice.

### Manual QA plan

1. **Persist a choice:** On `/`, switch to Arabic, then visit `/studio`, `/haramain`, and `/live`. Create a room named “Language QA” on `/live`, choose English as its translation target, and open its generated listener link at `/live/join/<room-id>`. Reload each page. **Expected:** Arabic interface remains selected and page direction is RTL. Switch to English on one page and revisit the others. **Expected:** English remains selected while the room still targets English translation.
2. **Use the studio in Arabic:** At `/studio`, submit an empty or invalid upload, then process a permitted short recording or recorded YouTube link. **Expected:** validation, progress, job state, result controls, and download labels are Arabic; the original Arabic transcript and English/French outputs remain correctly identified.
3. **Keep language concepts separate:** On a completed result, select the French tab and change the interface language. **Expected:** the interface labels change; when French output is selected its text remains French rather than being regenerated or relabeled as another language. In a live room, changing UI language does not change the room's target language.
4. **Check failure copy:** With the network temporarily offline after a page has loaded, attempt an action in both UI languages. **Expected:** the visible error is readable in the selected language and gives a clear recovery action.
5. **Storage fallback:** Disable browser storage for the site if the browser permits it, then use the language control on `/`. **Expected:** the current page still switches language without a crash, even if the choice cannot persist.

---

## Phase 4: Make navigation and phone use consistent

**User stories:** #8, #10, #11
**Depends on:** Phases 1–3

### What to build

Apply one recognizable Moin navigation pattern across the three working areas, while keeping the welcome page focused on introduction. Show the active area and clear ways to return to welcome or a parent collection/room entry from nested views. Resolve cross-page differences in the language control, headers, typography, and functional feedback. Complete keyboard, focus, contrast, reduced-motion, and phone-size review across the visitor paths. This phase is complete when a visitor can enter any page directly, know where they are, and move between areas without losing their chosen interface language.

### Acceptance criteria

- [ ] Every working area visibly identifies the current area and exposes routes to the other two areas and welcome.
- [ ] Nested Haramain and live views provide meaningful parent/return cues; direct entry and browser Back work.
- [ ] The same language-control placement and active state are easy to recognize on desktop and phone.
- [ ] All primary controls are usable by keyboard and touch, with visible focus and adequate contrast and hit area.
- [ ] At 390px, 768px, and desktop widths, the welcome, studio, video center, live translator, and representative nested views have no clipped content or unwanted horizontal scrolling.
- [ ] Reduced-motion preference prevents nonessential motion without hiding content or feedback.

### Manual QA plan

1. **Navigate by route:** Open `/`, `/studio`, `/haramain`, and `/live` directly, then use each page's navigation. **Expected:** the current area is clear, the home action reaches welcome, and links to the other areas work without opening a confusing separate experience.
2. **Navigate a nested view:** From `/haramain`, open any recorded video and copy its detail URL into a new tab. From `/live`, create a room named “Navigation QA” and copy its listener link into a new tab. **Expected:** both direct-entry views identify their parent/context and offer a clear way back; browser Back behaves normally after in-site navigation.
3. **Keyboard route:** Starting at `/`, use Tab, Enter, and Shift+Tab to reach the language control, primary action, service links, and representative form fields. **Expected:** focus is always visible and the controls work without a pointer; a skip-to-content action is available in the working-area shell.
4. **Phone route:** At a 390px viewport, visit all four top-level routes, a Haramain video, and a live listener view. **Expected:** navigation, language control, content, and primary actions remain legible and tappable without page-width overflow.
5. **Motion and contrast:** Enable reduced motion, revisit `/` and a processing/result state in `/studio`, then inspect light and dark brand surfaces. **Expected:** content is visible without entrance effects, status is communicated by text as well as color, and functional text has readable contrast.
