# Spec: Google Cloud NMT Translation Pilot

## Problem Statement

Moin has an approved Arabic ASR configuration, but it has not selected a
translation engine for Arabic-to-English and Arabic-to-French religious speech.
The project needs to assess Google Cloud Translation NMT on the nine
user-reviewed Arabic texts without mixing ASR errors into the result, exposing
credentials, or accidentally consuming an unbounded paid service.

## Solution

Provide a server-side Google Cloud Translation NMT candidate and a controlled,
text-only pilot. The pilot translates the frozen Arabic references into English
and French, records reproducible non-secret evidence, and prepares anonymous
human-review material. It uses a fixed 50,000-character run allowance and
never makes a provider call unless an operator deliberately runs the pilot with
a configured Google Cloud credential.

## User Stories

1. As the project operator, I want to configure Google Cloud credentials only
   on the server, so that no credential is stored in source control or sent to
   a browser.
2. As the project operator, I want to run Google NMT against the reviewed
   Arabic source texts, so that ASR quality cannot influence the translation
   decision.
3. As the project operator, I want each English and French result saved with
   its model, language, timing, source identity, and character accounting, so
   that the pilot can be reproduced and audited.
4. As a bilingual reviewer, I want anonymized Arabic source text and one target
   language output at a time, so that I can judge meaning, Islamic terminology,
   and fluency without knowing the system identity.
5. As the project operator, I want a failed, missing, malformed, unauthorized,
   or over-budget provider response to be recorded as a failed result, so that
   it cannot be reviewed or reported as faithful.
6. As the product owner, I want English and French to be chosen independently,
   so that a strong result in one language does not conceal a weak result in
   the other.

## Acceptance Criteria

- [ ] The candidate uses Google Cloud Translation NMT with Arabic as the source
  and English or French as the target, and is separate from all local and
  existing candidate configurations.
- [ ] No credential, API key, bearer token, service-account JSON, or billing
  identifier is written into configuration, source, records, review packages,
  or browser assets.
- [ ] Translation runs consume only the frozen, user-reviewed Arabic reference
  text and not the recorded audio or an ASR output.
- [ ] A run stops before it would exceed 50,000 source characters, records the
  reason, and does not silently continue.
- [ ] A completed run records separate English and French outputs with
  non-secret provider identity, language pair, source identity, timing, and
  character count.
- [ ] An anonymous review package can be created for the outputs and enforces
  the existing `faithful`, `partly_wrong`, and `serious_meaning_error` labels.
- [ ] Automated tests cover configuration validation, request construction,
  character-budget enforcement, response parsing, and failure handling without
  contacting Google.
- [ ] The documentation states the credential setup, explicit run command,
  free-tier assumption, 50,000-character pilot cap, and the fact that human
  review is still required before selecting a winner.

## Implementation Decisions

### Architecture & Schema

The Google NMT adapter is a provider-specific, server-side deep module. Its
public text-translation operation accepts a validated candidate configuration,
one Arabic source string, and exactly one target language. It returns a
normalized result or a structured failure without revealing credential details.

The candidate configuration is secret-free and identifies the provider API,
the configured credential environment variable, Arabic source, supported
targets, model identity, timeout, and maximum pilot character allowance. The
credential itself is resolved only at runtime from the configured server
environment.

The text pilot has its own evidence record format. Each record includes the
frozen source-text identity, input character count, target language, output or
failure, elapsed time, candidate identity, and non-secret runtime identity.
It keeps English and French outputs separate.

### Interfaces & Contracts

The adapter constructs a Google Cloud Translation NMT request with Arabic as
the source language and the requested English or French target language. It
uses authenticated server-to-provider transport; browser clients never call the
provider directly.

The text-pilot command accepts a candidate and the reviewed source corpus. It
refuses unvalidated configuration, missing credentials, unsupported languages,
empty source text, output that exceeds its pre-run allowance, and pre-existing
records that would make a run ambiguous. Re-running a completed record reuses
it rather than requesting another translation.

The review export contains source text, target output, anonymous system labels,
the established three-level rubric, optional reviewer comments, and no
credential or candidate identity mapping.

### Behavior & Interactions

The initial pilot evaluates standard Google NMT only. Glossaries, Adaptive
Translation, Translation LLM, automatic quality claims, and web deployment are
separate experiments.

Before each provider request, the pilot counts the source characters and
refuses the request if the cumulative count would exceed 50,000. Provider or
transport failures are saved as failures; a failure is never substituted with a
different model or retried automatically.

Reviewers evaluate Arabic-English and Arabic-French items independently.
Religious meaning reversal, changed negation or obligation, false attribution,
and serious addition or omission are serious meaning errors. A completed pilot
is evidence for this nine-text development sample only; it is not a claim that
Google NMT is universally best or that Moin has a final translation winner.

## Testing Decisions

Adapter unit tests will replace HTTP transport with a deterministic fake and
assert request payload, URL construction, authentication boundary, decoded
output, and safe error normalization. Pilot workflow tests will use a temporary
reviewed corpus and fake adapter to test run locking, character accounting,
reuse, failure records, and anonymous export. Existing benchmark adapter and
workflow tests are the prior art.

## Out of Scope

- **Adaptive Translation, Translation LLM, and glossaries**: they alter the
  experiment and may have different pricing; compare them only in a separately
  approved evaluation.
- **Live website deployment**: this pilot establishes a backend integration and
  review evidence, not the public production architecture.
- **Translation-model selection claim**: selection requires completed bilingual
  human review of the prepared outputs.
- **TTS selection**: this is Step 3 of the roadmap and begins after Step 2 has
  usable review evidence.

## Open Questions

- Which Google Cloud project and server-side credential will the operator use
  for the controlled pilot?
- Which named Arabic-English and Arabic-French reviewers will submit the blind
  assessments?
- Should a later, separately budgeted comparison test a terminology glossary
  after the standard-NMT result is reviewed?

## Further Notes

Google Cloud billing and API activation are prerequisites for an actual call,
even when the expected NMT usage remains within the provider's monthly free
allowance. The 50,000-character allowance is Moin's internal safety cap, below
the provider free-tier allowance, and must be disclosed with the pilot result.
