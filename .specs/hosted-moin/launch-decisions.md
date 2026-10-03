# Hosted Moin pilot: owner decisions

This file records decisions given by the project owner for the first hosted pilot. It does not claim that a public site or live translation has been deployed.

| Topic | Decision |
| --- | --- |
| First release scope | Recording Studio, Haramain Video Center, and Live Mosque Translator |
| Job and live-room creation | Any visitor may create one without an account |
| Listener entry | By session link, code, or QR without an account |
| Monthly operating ceiling | USD 100 for this test, including hosting, processing, DeepL, and ElevenLabs; treat as a hard ceiling |
| Live text latency target | Less than 10 seconds from speech to visible translated text; to be measured before making a public claim |
| Concurrent live rooms | One in the first release |
| Listeners per room | The existing live spec targets 50, subject to a practical load test |
| Retention | Delete original media and generated results automatically after seven days; provide a download beforehand |
| Data location | No country-specific hosting requirement |
| Domain | Begin with a temporary service address; connect a custom domain later |
| Live worker startup | On-demand startup delay is acceptable before the first live segment; measure the under-ten-second target after the worker is ready |

## Engineering consequences

- Anonymous creation needs hard media limits, rate limits, abuse controls, private result access, and a global spending guardrail. The public API cannot reuse Studio's local shared job list or loopback token.
- Live capacity must be reserved separately from recorded jobs so a long recording cannot starve the one active room.
- The under-ten-second live goal is unverified. The existing full-recording path is too slow to support such a claim by inference alone. Measure short segments on the selected host, including queue, ASR, safety, translation, and delivery.
- A USD 100 ceiling is incompatible with an always-on high-performance GPU worker at currently published on-demand rates. Use on-demand work and measured quotas; stop accepting work when the budget guardrail is reached rather than silently exceeding it.
- Deployment, billing activation, provider credentials, and any domain connection remain separate operational steps. Do not put secrets in source files.

## Still to decide or verify

- Hosting architecture and provider after current documentation and price review.
- Exact global/per-visitor quotas within the monthly ceiling, based on measured cost per minute.
- Whether the less-than-ten-second target is achievable at the chosen cost and quality; if not, revisit scope, budget, or latency with the owner.
- A workable owner recovery policy for anonymous jobs and live rooms, whose private links can be lost.
