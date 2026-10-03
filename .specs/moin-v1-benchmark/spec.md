# Spec: Moin V1 — Religious Arabic Benchmark and Model Selection

## Component selection update — 2026-09-22

ASR selection is now the immediate priority, followed by a translation-only
comparison using identical corrected Arabic text. See
[model-selection.md](../model-selection.md) for the governing stage checklist.
The original audio-input comparison below remains valid as historical pipeline
evidence, but cannot by itself select the best ASR or isolate translation errors.
Keep its frozen runs intact; new comparisons require separate run identities.

## Current scope — revised by user on 2026-09-22

Use only the nine existing user-selected clips for the complete V1 comparison.
No additional development clips or separate final recordings are required.
The CLI calls this set `development`; all candidates process the same nine clips.
Report English and French faithful counts out of nine independently. Because
these clips also inform model selection, results describe this sample only and
cannot establish accuracy on unseen audio or earn an independent 90% quality claim.
The selected safety composition may be exercised on the same clips, with that
reuse disclosed. Original ASR drafts stay preserved alongside user corrections;
unclear audio remains explicitly marked instead of reconstructed from memory.

## Problem Statement

Moin has an Arabic transcription and translation pipeline, but it has not
proved that it preserves the intended meaning of informal religious Arabic.
Fluent output may still be wrong, especially when speech contains Islamic
terminology, Qur'anic material, or natural informal-halaqah delivery.

The team needs a rapid, defensible method to choose the highest-quality
combination of available models. Model reputation, speed, and general-purpose
leaderboards are not sufficient evidence for this domain.

## Solution

Create a reproducible benchmark that compares no more than four fully specified
candidates on Arabic religious speech and evaluates English and French meaning
separately through blind human review.

Moin is evaluated as a quality pipeline, not as a newly trained foundation
model. It may use the strongest external ASR or translation models as
components, then add religious-safety rules. The benchmark will identify the
configuration that earns the right to become Moin V2.

## User Stories

1. As the project lead, I want a fixed evaluation protocol, so that model
   selection is based on evidence rather than impressions.
2. As a benchmark curator, I want representative informal-halaqah clips from
   several speakers with recorded provenance, so that results reflect Moin's
   actual target domain.
3. As a model operator, I want every candidate to process identical audio and
   produce a normalized Arabic transcript plus English and French text, so that
   comparison is fair.
4. As a bilingual Arabic-English-French reviewer, I want anonymous outputs and
   a small consistent rubric, so that brand expectations cannot influence my
   judgement.
5. As a project lead, I want English and French scores reported independently,
   so that one language cannot conceal weakness in the other.
6. As a listener, I want detected Qur'anic content to use a trusted rendering
   instead of model-generated text, so that high-stakes content is handled
   responsibly.
7. As a hackathon judge, I want a named comparison table and an explanation of
   the blind-review method, so that Moin's quality claim is credible.

## Acceptance Criteria

- [ ] The corpus contains the nine existing clips with human-reviewed Arabic
      references and recorded uncertainty; no additional or final set is required.
- [ ] The development set represents informal halaqahs from at least three
      speakers, including ordinary teaching, dense Islamic terminology, natural
      or fast speech, and Qur'an-adjacent material.
- [ ] Every clip records source provenance and a permitted-use decision. Draft
      transcripts may be automated, but development transcripts are verified.
- [ ] At most four exact candidate configurations are locked before the first
      comparison; each run retains the provider/model, version, settings,
      prompts, date, and timing without storing secrets.
- [ ] Reviewers see only anonymous system labels until their development scores
      are final.
- [ ] Every target-language output is labelled faithful, partly wrong, or
      serious meaning error; only faithful is a passing result.
- [ ] Qur'anic material is routed to documented trusted English and French
      renderings rather than machine translation.
- [ ] The selected Moin configuration records its exact composition; any
      evaluation on the nine selection clips is disclosed as reuse.
- [ ] The report gives faithful counts out of nine separately for English and
      French and makes no independent 90% or unseen-audio quality claim.
- [ ] The report truthfully presents named candidates, per-language scores, the
      rubric, blind-review process, timing observations, and any missed target.

## Implementation Decisions

### Architecture & Schema

- **Corpus is a first-class asset.** A clip has a stable ID, provenance, speaker
  label, domain tags, duration, transcript state, and exactly one membership:
  development or final.
- **Candidate adapters are deep modules.** A candidate accepts canonical Arabic
  audio and returns Arabic transcript, English text, French text, timing,
  uncertainty, and configuration identity. Provider-specific transport,
  authentication, prompt handling, retries, and parsing stay internal.
- **Religious safety is a deep module.** It returns safe ordinary translation,
  sourced Qur'an rendering, or withheld output with an auditable reason. Corpus
  matching, glossary context, and confidence logic stay internal.
- **Evaluation records become immutable after review.** Blind labels are stored
  separately from candidate identities until scoring is complete.
- **Credentials are local-only.** Reports use non-secret configuration labels
  and never include provider keys or raw credentials.

### Interfaces & Contracts

- **Corpus contract:** retrieve the canonical audio and allowed metadata for a
  chosen split. The nine-clip profile rejects final-set operations.
- **Candidate contract:** process a clip without human correction and return the
  transcript, both target-language outputs, stage timing, and a normalized
  error or uncertainty state.
- **Review contract:** present source material and one anonymous output per
  language; store one rubric label and optional comment without candidate name.
- **Reporting contract:** calculate faithful rates and error counts per language
  and state explicitly that there is no independent held-out evaluation.

### Behavior & Interactions

- The same nine clips are used to compare and choose; any repairs and reuse
  are disclosed, with no separate final test.
- Candidates include Moin Quality Pipeline, the current baseline, and selected
  named alternatives such as an OpenAI and Qwen configuration. Their exact
  versions are selected through research, then locked.
- Reviewers judge preserved intended meaning rather than literal word order.
  Altering, omitting, inventing, or materially softening a religious claim is
  not faithful.
- A false religious claim, reversal of meaning, wrong Qur'an handling, or
  confident fabrication is a serious error.
- Provider failure or malformed output is recorded as a failure. It is never
  silently replaced after comparison begins.

## Testing Decisions

- Unit-test corpus validation, including required metadata, duplicate IDs,
  split separation, speaker diversity, and source state.
- Unit-test normalized candidate results and secret-free report generation.
- Unit-test safety routing with ordinary speech, Qur'anic material, near
  matches, and insufficient-confidence cases.
- Unit-test scoring, including nine-clip denominators, independent language scores, and
  rejection of held-out quality claims in the nine-clip profile.
- Integration-test adapters with recorded fixtures or provider doubles; paid
  live calls are controlled benchmark runs, not unit tests.

## Out of Scope

- **Live microphone demonstration:** belongs to V2 after a winner is selected.
- **Text-to-speech:** quality is assessed as text first.
- **Offline-only operation, compression, quantization, and one-bit work:** this
  version prioritizes the quality ceiling.
- **Other target languages:** V1 evaluates English and French only.
- **New foundation-model training or fine-tuning:** use it only after evidence
  shows that available candidates cannot meet the target.

## Open Questions

- Which exact four candidate configurations are available, affordable, and
  stable enough to lock?
- Which public recordings have suitable permissions and representative informal
  halaqah audio quality?
- Which trusted English and French Qur'an renderings can be used publicly?

## Further Notes

V1 is the evidence gate for all later work. A model winning a general benchmark
does not win Moin; it must earn its result in this corpus and rubric.
