# Arabic ASR candidate research — 2026-09-23

This note narrows the models worth running on Moin's nine user-reviewed Islamic
speech clips. It is a candidate screen, not an accuracy result. No provider was
called and no model is declared the winner. The winner must come from the
project's own frozen-reference comparison and Arabic review.

## Evaluation input and host

The nine WAV files total **446.574 seconds (7.443 minutes)**, rather than nine
7.5-minute recordings. They run on a MacBook Air with an Apple M3 (8 CPU and 8
GPU cores), 16 GB unified memory, and macOS arm64. The existing Python 3.14
environment already has `faster-whisper==1.2.1` and
`ctranslate2==4.8.1`; the pinned Whisper-small weights are cached.

The references are working transcripts reviewed by the user, not independently
certified ground truth. Clip 4 has an untimed `[غير واضح]` faded ending. Until a
boundary is marked, the primary aggregate must cover the other eight clips and
show clip 4 separately. The existing `nine-local-v1` run compares translation
pipelines sharing Whisper small and stays frozen; it is not an ASR comparison.

## Runnable local shortlist

| Priority | Exact model/revision | Proposed runtime and fixed settings | Host fit and evidence |
| --- | --- | --- | --- |
| Baseline | `Systran/faster-whisper-small` at `536b0662742c02347bc0e980a01041f333bce120` | `faster-whisper==1.2.1`, `ctranslate2==4.8.1`, CPU `int8`; `language=ar`, `task=transcribe`, `beam_size=5`, `temperature=0`, `vad_filter=false`, no prompt | Already cached and known to run. It must be rerun with the dedicated ASR settings and snapshot rather than copying the old translation result. |
| Main challenger | `Systran/faster-whisper-large-v3` at `edaa852ec7e145841d8ffdb056a99866b5f0a478` | Same runtime and decoding controls as the baseline; CPU `int8` | This is the official CTranslate2 conversion of the 1.55B multilingual Whisper large-v3 checkpoint. The pinned repository is about 3.09 GB. CTranslate2 publishes macOS ARM64 wheels and supports ARM64 CPU; faster-whisper documents CPU int8. It is expected to fit in 16 GB, but that remains an inference until a peak-memory preflight succeeds. This CTranslate2 configuration uses the Mac CPU path, so latency may be several times the audio duration. Actual load, quality, memory, and time must be measured. |
| Optional fast challenger | `openai/whisper-large-v3-turbo` at `41f01f3fe87f28c78e2fbf8b568835947dd65ed9` (or a separately pinned CTranslate2 conversion) | Transformers/MPS or a verified converted checkpoint; same language/task/decoding policy where APIs match | 809M parameters and Arabic is in the model metadata. Its model card says it prunes decoder layers from 32 to 4 for much higher speed with a minor quality loss. It is useful if large-v3 latency is unacceptable, but quality-first selection should run full large-v3 first. |

Evidence: [faster-whisper usage and CPU int8](https://github.com/SYSTRAN/faster-whisper),
[CTranslate2 macOS ARM64 support](https://github.com/OpenNMT/CTranslate2/blob/master/docs/installation.md),
[pinned faster-whisper large-v3 conversion](https://huggingface.co/Systran/faster-whisper-large-v3/tree/edaa852ec7e145841d8ffdb056a99866b5f0a478),
[Whisper large-v3 model details](https://huggingface.co/openai/whisper-large-v3), and
[Whisper large-v3-turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo).

Use full large-v3 as the second actual local run. It changes model capacity
while keeping the proven adapter and decoding surface constant. Speed and
download size are secondary to transcription quality for this selection step.

## Promising local models that are not initial runnable candidates

`Qwen/Qwen3-ASR-1.7B` and `Qwen/Qwen3-ASR-0.6B` both list Arabic (`ar`), long
audio, and offline/streaming inference. Qwen's model card reports aggregate
multilingual results that are competitive with or better than Whisper large-v3
on several mixed-language datasets. Those tables are not Arabic-only and do not
cover Moin's religious speech, so they do not establish superiority here. The
official high-throughput path uses vLLM/CUDA, while this host is Apple Silicon.
Community MLX/CoreML/GGUF conversions exist, but adding one now would introduce
an independently converted model and runtime before it has been verified on
this machine. Keep Qwen3-ASR as the next local experiment after the two
controlled faster-whisper runs. Exact upstream repository sizes are about
1.88 GB (0.6B) and 4.7 GB (1.7B).

Meta Omnilingual ASR covers 1,600+ languages, but the published LLM checkpoints
are poor fits for this laptop: the 1B repository is about 9.1 GB, and the model
card reports roughly 10 GiB inference memory for the 3B model and 17 GiB for
7B on an A100. It is not an initial candidate on a 16 GB M3.

Evidence: [Qwen3-ASR supported languages, runtimes, and evaluation](https://huggingface.co/Qwen/Qwen3-ASR-0.6B),
[Qwen3-ASR Transformers integration](https://huggingface.co/docs/transformers/main/model_doc/qwen3_asr),
and [Meta omniASR-LLM-7B model card](https://huggingface.co/facebook/omniASR-LLM-7B).

## Paid API shortlist

The prices below are public list prices checked on 2026-09-23. The estimates
multiply 7.443 minutes by the listed rate and exclude taxes, storage, network,
free credits, add-ons, rounding differences, and retries. They authorize no
spend.

| Priority | Exact request configuration | Arabic support and reproducibility | Estimated nine-clip cost |
| --- | --- | --- | ---: |
| 1 | OpenAI `POST /v1/audio/transcriptions`, `model=gpt-4o-transcribe`, `language=ar`, `response_format=json`, no prompt | The API accepts ISO-639-1 input language and OpenAI says this model improves WER and language recognition over original Whisper. The current model page lists only the alias, not an immutable dated snapshot, so save request settings, response usage, and run date and disclose that the provider can update it. | **$0.0447** at $0.006/min |
| 2 | ElevenLabs `POST /v1/speech-to-text`, `model_id=scribe_v2`, `language_code=ara`, `no_verbatim=false`, `diarize=false`, event tagging off | Official docs list Arabic and place it in their vendor-published 10–20% WER band; the conditions and denominator are not established in this note. This supports inclusion, not a cross-provider rank. `scribe_v2` is a mutable provider ID; record the full request and run date. | **$0.0273** at $0.22/hour |
| 3 | Deepgram pre-recorded `/v1/listen`, `model=nova-3`, `language=ar`, formatting and diarization off | Official docs list `ar` plus many regional Arabic codes, including `ar-SA`; Arabic support was announced in January 2026. Prefer general `ar` for the mixed corpus unless all clips are verified Saudi. The public ID is mutable; save the returned model metadata and date. | **$0.0320** at $0.0043/min (monolingual pre-recorded PAYG) |

Primary sources: [OpenAI transcription request schema](https://developers.openai.com/api/reference/audio/createTranscription),
[OpenAI model page](https://developers.openai.com/api/docs/models/gpt-4o-transcribe),
[OpenAI pricing](https://developers.openai.com/api/docs/pricing),
[ElevenLabs request schema](https://elevenlabs.io/docs/api-reference/speech-to-text/convert),
[ElevenLabs Arabic support and published WER bands](https://elevenlabs.io/docs/overview/capabilities/speech-to-text),
[ElevenLabs pricing](https://elevenlabs.io/pricing/api),
[Deepgram language/model IDs](https://developers.deepgram.com/docs/models-languages-overview),
[Deepgram Arabic release note](https://developers.deepgram.com/changelog/2026/1/27), and
[Deepgram pricing](https://deepgram.com/pricing).

Google Cloud `chirp_3` supports `ar-SA`, `ar-XA`, and many Arabic regional codes,
but those Arabic entries are currently marked Preview. Its V2 list price is
$0.016/min (about $0.1191 for these files), or $0.003/min dynamic batch (about
$0.0223), with possible Cloud Storage charges. Keep it as a later candidate
until Preview status and region availability are acceptable. Sources:
[Chirp 3 language table](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)
and [Google Speech-to-Text pricing](https://cloud.google.com/speech-to-text/pricing).

The initial paid run, if a budget is later approved, should use all three
shortlisted APIs on the identical audio-only inputs. Provider claims and broad
benchmarks are not comparable enough to eliminate one before Moin's evaluation.

## Reproducible benchmark interface

The dedicated ASR runner should expose one common operation:

```text
transcribe(audio_path, candidate_config) -> {
  status, raw_text, elapsed_ms, provider_metadata, failure
}
```

`candidate_config` should contain an immutable local repository revision or the
exact provider model ID; runtime/package versions; language/task; decoding,
VAD, formatting and prompt settings; and a credential environment-variable
name rather than a secret. The adapter receives audio and configuration only.
References must never enter inference prompts or requests.

Each run must hash the frozen reference snapshot, every audio file, and the
candidate configuration; preserve raw hypotheses and failures; and refuse to
reuse outputs whose identities differ. Report strict Arabic-normalized WER and
CER plus a separately named alef-normalized diagnostic, per clip and as
micro-aggregates. Publish substitutions/deletions/insertions, denominators,
scored duration/word coverage, elapsed time, and failures. Do not average
per-clip WERs. Clip 4 stays outside the primary aggregate until its unclear
audio boundary is marked. Human review must separately flag religious terms,
names, Qur'an wording, negation, omissions/additions, and meaning changes.

The first implementation target is therefore:

1. rerun pinned Whisper small under a new ASR-only snapshot;
2. run pinned Whisper large-v3 with identical decoding controls;
3. generate an anonymous audio/transcript/diff review artifact; and
4. select only after the Arabic review, reporting a tie or limitation when the
   evidence does not distinguish the candidates.
