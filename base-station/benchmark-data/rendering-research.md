# Qur'an rendering source research

Research date: 2026-09-21; assembly completed 2026-09-22. Published
QuranEnc Rowwad English v1.0.19 and Rachid Maach French v1.0.3 are selected as
the benchmark's trusted rendering sources. This is a documented publisher-source
selection, not a claim that Codex or the user independently verified every
translation. The original draft is retained alongside the assembled usable
`staging-renderings/renderings.quranenc.json`.

## Completed alignment

The final assembly uses QuranEnc's own `arabic_text` fields from all 114 surah
API responses, joined by `(sura, aya)` with its English/French SQLite editions.
This avoids changing Tanzil's basmala representation. Checks confirmed 6,236
matching keys, all 114 surahs with contiguous ayah numbers, and byte-for-byte
string equality between English API and SQLite translations and footnotes.
French translations and footnotes are copied verbatim. Sources, versions,
publisher descriptions, references, and footnotes are retained in the registry.
The full source artifacts and generated files have SHA256 checksums.

Repeated Arabic verses are valid: identical renderings retain all references;
conflicting contextual renderings are withheld rather than arbitrarily chosen.
The separate unapproved draft remains available for inspecting/changing source
selection before any composition is locked.

## Recommended source candidates

### Canonical Arabic detection text: Tanzil Uthmani v1.1

- Official download: <https://tanzil.net/download/>
- Official license: <https://tanzil.net/docs/Text_License>
- Updates: <https://tanzil.net/updates/>
- Staged source: `staging-renderings/raw/tanzil-quran-uthmani-v1.1.txt`

Tanzil identifies this as a carefully produced, specialist-verified text. Its
license is CC BY 3.0 with additional explicit terms: copies must be verbatim,
the source must be identified and linked, the copyright notice must remain,
and changing the Quran text is prohibited. The staged file retains the
publisher's notice and has 6,236 text rows plus the notice block.

This is the strongest candidate for the detection corpus, but the downloaded
plain-text edition prepends an unnumbered basmala to the first ayah of most
surahs. That representation cannot be silently split or stripped because the
publisher explicitly prohibits changing the text. It also does not directly
align with QuranEnc's 6,236 numbered translation rows. A source-approved
alignment method or explicit permission is required before creating the final
registry.

### English rendering: QuranEnc Rowwad Translation Center v1.0.19

- Publisher page and edition metadata: <https://quranenc.com/en/home>
- Metadata API: <https://quranenc.com/api/v1/translations/list/en>
- Dataset: <https://quranenc.com/downloads/sqlite/english_rwwad.zip>
- Staged source: `staging-renderings/raw/english_rwwad.sqlite`

The publisher describes the translation as produced by the Rowwad Translation
Center team in cooperation with the Rabwah Dawah Association, the Islamic
Content Service Association in Languages, and IslamHouse.com. The staged
database contains 6,236 unique `(sura, aya)` rows.

### French rendering: QuranEnc Rachid Maach v1.0.3

- Publisher page and edition metadata: <https://quranenc.com/fr>
- Metadata API: <https://quranenc.com/api/v1/translations/list/fr>
- Dataset: <https://quranenc.com/downloads/sqlite/french_rashid.zip>
- Staged source: `staging-renderings/raw/french_rashid.sqlite`

QuranEnc identifies Rachid Maach as the translator. The staged database
contains 6,236 unique `(sura, aya)` rows.

QuranEnc explicitly permits downloading and republication subject to all of
these conditions: do not modify, add, or delete content; identify the publisher
and QuranEnc.com; state the version; retain transcript information; notify the
source of translation notes; keep the translation updated to the latest
published version; and do not display it with inappropriate advertising. These
terms appear on both language pages. A frozen benchmark must preserve the
evaluated version while the user-facing product also needs a documented update
process to satisfy the publisher's update condition.

## Use and update obligations

The registry selects existing published translations. It does not require a
new trilingual scholarly certification; that was an overly restrictive initial
interpretation, not a requirement of the V1 spec. Human review is still required
for benchmark clips and bilingual candidate outputs.

Retain publisher attribution, versions, Arabic references, and footnotes whenever
renderings are displayed. Check QuranEnc's edition metadata before a new
comparison. If an edition changes, create a new composition and re-evaluate it;
do not silently alter frozen evidence. A public product needs to honor the
publisher's update conditions. No publication was performed in this session.

## Other sources assessed

### al-quran.fr Tadabbur-OS essential corpus v2026-08-13

- Download and CC0 statement: <https://www.al-quran.fr/downloads.php>
- Method: <https://www.al-quran.fr/methode.php>
- Staged archive: `staging-renderings/raw/al-quran-fr-essential-2026-08-13.zip`

The archive contains Arabic Hafs/Warsh text and English/French translations and
has an explicit CC0 dedication, including commercial reuse. Its published
method says the translations use internal Quranic coherence and classical
lexicography, exclude hadith, sira, and traditional tafsir as interpretive
authorities, use Claude and Gemini in a critical drafting process, and have one
human final arbiter. It is a legally clear research candidate, but this method
does not establish the independent scholarly or community approval needed for
Moin's trusted-rendering boundary. It is therefore staged for assessment only.

### ClearQuran / Talal Itani

- Official terms and downloads: <https://blog.clearquran.com/download>

The English translation is explicitly reusable, including commercially, under
CC BY-ND 4.0 with attribution and no modification. It has no paired French
edition, so it does not by itself satisfy Moin's bilingual routing contract.

### Tanzil translation downloads

- Translation catalogue and terms: <https://tanzil.net/trans/>

The catalogue includes English and French editions, but the catalogue terms
restrict translations to non-commercial use unless separate permission is
obtained from the translator or publisher. The site also warns that it does not
guarantee authenticity or accuracy. These files were not staged as an approved
product source.

### Quran Foundation APIs

- Content FAQ: <https://api-docs.quran.foundation/docs/tutorials/faq/>

The terms restrict long-term caching and redistribution of raw API content
without appropriate licensing. This is a poor fit for an immutable, bundled
benchmark registry, so no content was downloaded.

## Staged-file integrity

The exact downloaded artifacts and extracted databases are kept under
`staging-renderings/raw/`. Their SHA-256 values are recorded in
`staging-renderings/SHA256SUMS.txt`. The QuranEnc list API responses are retained
to preserve the edition keys, publisher descriptions, versions, and original
download URLs observed during this research.
