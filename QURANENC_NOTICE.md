# QuranEnc source notice for Moin's Qur'an guard

The registry at `base-station/benchmark-data/staging-renderings/renderings.quranenc.json`
contains Qur'anic Arabic and the published English/French renderings used to
guard Moin's automatic translation. It is published here to make the public
judging build reproducible; it is **not** a Moin-authored translation.

- Publisher: [QuranEnc.com](https://quranenc.com/).
- English edition: Rowwad Translation Center, version 1.0.19,
  [publisher page](https://quranenc.com/en/home).
- French edition: Rachid Maach, version 1.0.3,
  [publisher page](https://quranenc.com/fr).
- Arabic verse text and translated verse/footnote strings are copied from the
  QuranEnc editions without editorial changes. The registry joins them by
  surah and ayah and retains publisher, version, reference, and footnotes.
- Snapshot assembled 2026-09-22; SHA-256 of the published JSON:
  `d94c4fa5d961a25390e1bc4da88519e961113acd9e77bdaaee3bf99233690317`.

QuranEnc permits download and republication subject to its
[terms and policies](https://quranenc.com/fr). Moin must preserve publisher
attribution and version, avoid changing the translations, and check for
updates before a new public release. The research, source selection, and
integrity checks are documented in
[`base-station/benchmark-data/rendering-research.md`](base-station/benchmark-data/rendering-research.md).
