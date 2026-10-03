#!/usr/bin/env python3
"""Build an explicitly unapproved rendering registry from staged QuranEnc data.

The script performs no network access. Refresh the staged publisher artifacts
separately, then run this file to reproduce ``renderings.draft.json``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
import sqlite3
from pathlib import Path


HERE = Path(__file__).resolve().parents[1] / "benchmark-data" / "staging-renderings"
RAW = HERE / "raw"
OUTPUT = HERE / "renderings.draft.json"
EXPECTED_AYAT = 6236


def sqlite_rows(path: Path) -> dict[tuple[int, int], dict[str, str]]:
    with sqlite3.connect(path) as db:
        rows = db.execute(
            "SELECT sura, aya, translation, footnotes FROM translations ORDER BY id"
        ).fetchall()
    result = {}
    for sura, aya, text, footnotes in rows:
        key = (int(sura), int(aya))
        if key in result:
            raise ValueError(f"duplicate translation key: {key}")
        result[key] = {"text": text, "footnotes": footnotes or ""}
    return result


def quranenc_arabic_and_english() -> tuple[dict, dict]:
    arabic, english = {}, {}
    for sura in range(1, 115):
        path = RAW / "quranenc-english-surahs" / f"{sura}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["result"]:
            key = (int(row["sura"]), int(row["aya"]))
            if key in arabic:
                raise ValueError(f"duplicate Arabic key: {key}")
            arabic[key] = row["arabic_text"]
            english[key] = {
                "text": row["translation"],
                "footnotes": row.get("footnotes") or "",
            }
    return arabic, english


def main() -> None:
    global RAW, OUTPUT
    parser = argparse.ArgumentParser(description="Assemble verbatim aligned QuranEnc renderings from saved publisher artifacts")
    parser.add_argument('--raw', type=Path, default=RAW)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    parser.add_argument('--select-published-sources', action='store_true', help='Select these documented publisher editions for benchmark use; does not assert human translation verification')
    args = parser.parse_args()
    RAW, OUTPUT = args.raw, args.out
    arabic, api_english = quranenc_arabic_and_english()
    sqlite_english = sqlite_rows(RAW / "english_rwwad.sqlite")
    french = sqlite_rows(RAW / "french_rashid.sqlite")
    keys = set(arabic)
    if len(keys) != EXPECTED_AYAT or keys != set(sqlite_english) or keys != set(french):
        raise ValueError("Arabic, English, and French do not share all 6,236 ayah keys")
    if api_english != sqlite_english:
        raise ValueError("English API responses differ from the staged English database")

    renderings = []
    for sura, aya in sorted(keys):
        en, fr = sqlite_english[(sura, aya)], french[(sura, aya)]
        renderings.append(
            {
                "reference": {"sura": sura, "aya": aya},
                "arabic": arabic[(sura, aya)],
                "english": {
                    **en,
                    "source": "QuranEnc — English Translation - Rowwad Translation Center",
                    "source_url": "https://quranenc.com/en/home",
                    "version": "1.0.19",
                    "approved": False,
                },
                "french": {
                    **fr,
                    "source": "QuranEnc — French Translation - Rachid Maach",
                    "source_url": "https://quranenc.com/fr",
                    "version": "1.0.3",
                    "approved": False,
                },
            }
        )

    registry = {
        "schema_version": 1,
        "detection_ready": False,
        "draft": True,
        "approval_note": "Full 6,236-ayah draft; exact editions await user review and approval.",
        "arabic_source": {
            "source": "QuranEnc aligned arabic_text fields",
            "source_url": "https://quranenc.com/api/v1/translation/sura/english_rwwad/{sura}",
            "retrieved_with": "English Rowwad v1.0.19 surah API responses",
        },
        "renderings": renderings,
    }
    if args.select_published_sources:
        registry.update(detection_ready=True, draft=False,
                        approval_note="Published sources selected on publisher provenance and reuse terms; not independent human translation verification.")
        for language, field, edition in (("en", "english", "english_rwwad"), ("fr", "french", "french_rashid")):
            metadata = next(t for t in json.loads((RAW / f"quranenc-list-{language}.json").read_text())["translations"] if t["key"] == edition)
            for entry in registry["renderings"]:
                if entry[field]["version"] != metadata["version"]:
                    raise ValueError("Edition version changed; review metadata and rebuild explicitly")
                entry[field]["approved"] = True
                entry[field]["publisher_description"] = metadata["description"]
        registry["source_selection"] = {
            "selected_by": "Operator selection of documented published editions",
            "date": date.today().isoformat(),
            "terms_urls": ["https://quranenc.com/en/home", "https://quranenc.com/fr"],
            "permission_basis": "Publisher permits verbatim reuse with attribution, edition/version disclosure, preserved notes, and update conditions.",
            "independent_human_translation_verification": False,
        }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUTPUT} with {len(renderings)} aligned ayat; selected={args.select_published_sources}")


if __name__ == "__main__":
    main()
