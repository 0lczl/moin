# Candidate configuration research — 2026-09-21

`candidates.example.json` provides one pinned current baseline.
`comparison.example.json` provides baseline plus a named OpenAI alternative.
These are configurations to evaluate, not a claim about which model is best.
They are not locked until the validated corpus is supplied and `candidates lock`
succeeds. Availability, quota, cost, and Arabic religious-speech quality have
not been established by live calls in this implementation session.

| Candidate | Exact components | Rationale |
| --- | --- | --- |
| Current baseline | Systran/faster-whisper-small at `536b0662742c02347bc0e980a01041f333bce120`; facebook/nllb-200-distilled-600M at `f8d333a098d19b4fd9a8b18f94170487ad3f821d` | Existing model family and decoding settings, now pinned |
| OpenAI alternative | `gpt-4o-mini-transcribe-2025-12-15`; `gpt-4.1-2025-04-14` | Published dated snapshots supported by the multipart-ASR/chat adapter; separate fixed English and French prompts |

Sources checked:

- [Whisper small immutable repository revision](https://huggingface.co/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120)
- [Meta NLLB repository metadata](https://huggingface.co/api/models/facebook/nllb-200-distilled-600M)
- [OpenAI transcription model](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)
- [GPT-4.1 snapshots](https://developers.openai.com/api/docs/models/gpt-4.1)

NLLB's model card identifies its CC-BY-NC-4.0 licence. Retain that constraint in
any later product-use decision; this file records a benchmark configuration.
The adapter never substitutes a model if a pinned snapshot is unavailable.

Qwen was investigated as an additional option. The [Qwen-MT API](https://www.alibabacloud.com/help/en/model-studio/qwen-mt-api)
has specialized translation parameters; the generic chat adapter must not be
presented as a tested Qwen-MT integration. Alibaba's
[model pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
and [release notes](https://www.alibabacloud.com/help/en/model-studio/model-release-notes)
list dated Qwen chat snapshots, but region/account access and an appropriate
ASR pairing need verification before adding a third candidate. This keeps the
initial example within the spec's maximum of four without pretending an
untested endpoint is available. Moin is selected and safety-composed after
blind development review; no winner has been preselected.

## Available local comparison — 2026-09-22

`local-comparison.json` locks two runnable local configurations: the pinned
baseline and the same Whisper ASR with Qwen2.5-7B-Instruct 4-bit translation.
The exact cached Qwen revision is
`c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed`; MLX runtime versions are recorded
in the comparison lock. Both NLLB and Qwen passed actual local load and short
translation preflights. Qwen requires macOS GPU access outside this shell's
restricted sandbox. No API credentials or paid provider calls are needed.

This comparison controls ASR (same revision and decoding settings). It compares
translation configurations; it does not establish the strongest available ASR.
Qwen uses explicit greedy sampling, fixed per-language prompts, and a 1024-token
output cap. The existing NLLB baseline retains its 256-token cap. These caps and
all other differences remain visible in the locked configurations.

The OpenAI configuration remains an unrun example because this task has no
configured provider credential. It is not represented as an evaluated candidate.
