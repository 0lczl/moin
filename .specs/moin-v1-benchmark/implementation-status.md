# Current evidence — 2026-09-22

- Nine user-reviewed references validate across three speakers. Clip 4 preserves
  its unclear ending. Source-use authorization is private-local only; publisher
  reuse licences are not asserted.
- Two exact local candidates locked before inference in
  `base-station/benchmark-runs/nine-local-v1/comparison.json`.
- All 18 candidate/clip runs completed with nonempty EN/FR and no execution
  failures. This is execution evidence, not meaning accuracy.
- Anonymous review exported to `base-station/benchmark-review/nine-local-v1/`:
  36 judgements. No labels submitted, identities not mapped publicly, no winner.
- Recorded-media machine implemented separately. Actual clip-3 run at
  `base-station/machine-runs/first-recorded-demo/` produced Arabic, EN/FR,
  safe ordinary-translation routing, and English/French speech files. Audio
  containers verified with ffprobe. The speech/translation quality is unreviewed.
- Full automated suite: 70 passed. Review JavaScript passes syntax checking.
  Browser policy blocked local-file preview, so no visual/UI validation claimed.
- YouTube importer implementation and mocked tests exist; no new download was
  performed to test it. Live ingestion and web processing are not implemented.

Still required for V1 evidence completion: human meaning labels, report,
selection, and full selected-safety-composition evaluation. The broader product
roadmap is in `.specs/README.md`; experimental recorded processing may proceed
without pretending to have selected a validated winner.

---

# V1 implementation status

Updated 2026-09-22. **Current scope: nine clips total**, as requested by the user.
`benchmark-data/protocol.json` selects the nine-clip comparison. No additional
clips or held-out final run are required. Human corrections have been applied;
reference/category/use metadata and actual candidate comparison remain pending.
Scores will be per-language counts out of nine, without an independent quality
claim. The historical implementation table below describes capabilities of the
older 12/20 workflow, not requirements for the current task.

Historical status before this scope revision: This tracks software delivery separately from measured
acceptance. The original acceptance checkboxes remain unmarked because they
require real permitted clips, human review, and controlled model runs.

| Phase | Software implemented | Evidence still required |
| --- | --- | --- |
| 1 | Corpus schema, canonical audio hashes, overlap checks, strict 12/20 split, baseline adapter, protocol, normalized failure records | Approve clip provenance/use and verify 12 Arabic transcripts; run baseline |
| 2 | Up-to-four config lock, remote adapter, anonymous review export/import, immutable reviews, per-language named JSON/Markdown reports | Lock chosen configurations with account access; execute comparison; user reviews English and French |
| 3 | Pre-translation Qur'an routing, conservative withholding, sourced rendering contract, composition selection and freeze | Use prepared publisher-sourced rendering registry; select from completed development review; inspect full Moin dev run |
| 4 | Frozen-only once-through final run, blind final review, independent 18/20 gates and honest missed-target reports | Execute final 20 clips once after freeze; user reviews both languages |

Entry point and operator instructions: `base-station/BENCHMARK.md`.
Source/model/rendering research is under `base-station/benchmark-data/`.
Downloaded draft assets remain local and ignored by Git. The user has volunteered
to review the prepared development files and bilingual candidate outputs.

Tests and the synthetic CLI smoke workflow demonstrate software behavior only;
they do not constitute human quality evidence or earn a 90% claim.

The previous 32-clip collection and its drafts were deleted at the user’s request. Replacement sources are nine user-selected YouTube Shorts (three per speaker). All nine are now saved locally with a native playback launcher and Arabic transcript drafts for development review; the original 12-development/20-final acceptance requirements have not been changed. The separate QuranEnc rendering registry remains available.

The user accepted the audio quality of all nine replacement clips on 2026-09-22 after local playback. `staging/dev-review.md` now provides per-clip transcript-verification checklists and editable copies in `staging/review-transcripts/`; original machine drafts and provenance are preserved. All nine transcripts remain unverified, and source-use decisions remain pending. Corpus completion still requires three additional development clips and twenty separate final clips. No candidate lock or real comparison has been started.
