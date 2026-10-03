# Qur'anic quotations are substituted, never machine-translated

Status: accepted

Moin's differentiator is Fidelity to the Shaykh's religious meaning, and the
highest-stakes case is when he recites Qur'an. A general MT model (NLLB-200) is
not merely lower-quality on classical Arabic — it is the wrong tool, because
Islamic scholarship distinguishes a *translation of the meanings* from a
translation of the text. We therefore ship the Qur'an text on the base station,
fuzzy-match ASR output against it, and emit an established published rendering
(e.g. Saheeh International for English) instead of model output. Ordinary
scholarly speech still goes through MT, corrected by a curated glossary of core
Islamic terms.

## Considered Options

- **Machine-translate everything.** Simplest, zero extra stages, and what the
  code does today. Rejected: it puts machine output in the listener's ear where
  a canonical rendering exists, which is the single most criticisable thing this
  product could do in front of a Saudi audience.
- **Treat religious sensitivity as a stated principle only** (slide, not code).
  Rejected: the claim is the differentiator, so it has to be demonstrable.

## Consequences

- The Qur'an corpus (<1 MB of text) and one published translation per demo
  language ship with the base station. Matching is string work, not inference —
  it costs no model time.
- **Hadith is explicitly excluded.** The corpus is far larger, quotations are
  paraphrased mid-speech, and unreliable matching is worse than none. Deferred
  to a future version.
- Translation licensing for each published rendering is an open item before any
  public build; not a prototype blocker.
