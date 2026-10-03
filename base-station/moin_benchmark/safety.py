"""Fail-closed routing for Qur'anic and ordinary benchmark text.

The rendering registry is deliberately data-only.  It must declare that its
detection corpus is ready and provide independently approved English and French
renderings before any speech may leave this boundary.
"""

from __future__ import annotations

from difflib import SequenceMatcher
import re
import unicodedata
from typing import Any
from rapidfuzz.distance import Indel


_SCHEMA_VERSION = 1
_SPACE = re.compile(r"\s+")
_WHOLE_RATIO_THRESHOLD = (21, 25)  # 0.84
_WINDOW_RATIO_THRESHOLD = (39, 50)  # 0.78


def _length_can_reach_ratio(first_length: int, second_length: int, threshold: tuple[int, int]) -> bool:
    """Whether any matching blocks could reach ``threshold`` by length alone."""

    if not first_length or not second_length:
        return False
    numerator, denominator = threshold
    return 2 * min(first_length, second_length) * denominator >= numerator * (first_length + second_length)


def _indel_can_reach_ratio(first: str, second: str, threshold: tuple[int, int]) -> bool:
    """Use Indel similarity as a lossless upper bound on SequenceMatcher.ratio.

    Indel similarity is ``2 * LCS / (len(first) + len(second))``. The greedy
    matching blocks used by SequenceMatcher cannot contain more matches than
    the longest common subsequence, so this score can only be higher. Keep one
    edit of slack for floating-point threshold rounding, then use the original
    SequenceMatcher ratio for the final decision.
    """

    total_length = len(first) + len(second)
    if not total_length:
        return True
    numerator, denominator = threshold
    max_distance = (total_length * (denominator - numerator)) // denominator + 1
    return Indel.distance(first, second, score_cutoff=max_distance) <= max_distance


def _normalise_arabic(text: str) -> str:
    """Return a comparison form without changing the text shown to users."""

    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text).replace("ـ", "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي"}))
    text = "".join(
        ch if ch.isalnum() or ch.isspace() else " "
        for ch in text
    )
    return _SPACE.sub(" ", text).strip()


def validate_renderings(data: dict) -> None:
    """Validate a complete, approved rendering and detection registry.

    Schema::

        {
          "schema_version": 1,
          "detection_ready": true,
          "renderings": [{
            "arabic": "...",
            "english": {"text": "...", "source": "...",
                        "version": "...", "approved": true},
            "french":  {"text": "...", "source": "...",
                        "version": "...", "approved": true}
          }]
        }

    ``detection_ready`` is a curator assertion that the configured entries are
    the full detection corpus intended for this run.  An empty or draft
    registry therefore cannot accidentally classify speech as ordinary.
    """

    if not isinstance(data, dict):
        raise ValueError("rendering registry must be an object")
    if data.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("unsupported rendering registry schema_version")
    if data.get("detection_ready") is not True:
        raise ValueError("Qur'an detection corpus is not ready")
    entries = data.get("renderings")
    if not isinstance(entries, list) or not entries:
        raise ValueError("rendering registry must contain at least one entry")

    references: set[tuple[int, int]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"renderings[{index}] must be an object")
        arabic = _normalise_arabic(entry.get("arabic", ""))
        if not arabic:
            raise ValueError(f"renderings[{index}].arabic is required")
        # Repeated Arabic verses are legitimate. References, when supplied,
        # must identify distinct ayat; ambiguous renderings are withheld below.
        reference = entry.get("reference")
        if reference is not None:
            if not isinstance(reference, dict):
                raise ValueError("invalid ayah reference")
            key = (reference.get("sura"), reference.get("aya"))
            if not all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in key) or key[0] > 114:
                raise ValueError("invalid ayah reference")
            if key in references:
                raise ValueError("duplicate ayah reference")
            references.add(key)
        for language in ("english", "french"):
            rendering = entry.get(language)
            if not isinstance(rendering, dict):
                raise ValueError(f"renderings[{index}].{language} is required")
            for field in ("text", "source", "version"):
                if not isinstance(rendering.get(field), str) or not rendering[field].strip():
                    raise ValueError(
                        f"renderings[{index}].{language}.{field} is required"
                    )
            for optional in ("footnotes", "source_url", "publisher_description"):
                if optional in rendering and not isinstance(rendering[optional], str):
                    raise ValueError(f"invalid rendering {optional}")
            if rendering.get("approved") is not True:
                raise ValueError(f"renderings[{index}].{language} is not approved")


def _withheld(reason: str) -> dict:
    return {
        "outcome": "withheld",
        "en": None,
        "fr": None,
        "reason": reason,
        "sources": [],
    }


def _is_near_or_mixed(
    speech: str,
    verse: str,
    speech_window_cache: dict[int, list[str]] | None = None,
) -> bool:
    if f" {speech} " in f" {verse} " or f" {verse} " in f" {speech} ":
        return True

    # Character similarity catches a small ASR error. Token overlap catches a
    # verse embedded in commentary even when punctuation/word endings differ.
    # Length and Indel similarity are upper bounds. SequenceMatcher remains the
    # final decision-maker at the original threshold.
    if _length_can_reach_ratio(len(speech), len(verse), _WHOLE_RATIO_THRESHOLD):
        matcher = SequenceMatcher(None, speech, verse, autojunk=False)
        if (_indel_can_reach_ratio(speech, verse, _WHOLE_RATIO_THRESHOLD)
                and matcher.ratio() >= 0.84):
            return True
    speech_tokens, verse_tokens = set(speech.split()), set(verse.split())
    if not speech_tokens or not verse_tokens:
        return False
    overlap = len(speech_tokens & verse_tokens)
    if overlap >= 3 and overlap / min(len(speech_tokens), len(verse_tokens)) >= 0.75:
        return True

    # A short, slightly damaged fragment of a longer verse has a low whole-text
    # similarity. Compare it with same-sized windows so one ASR substitution or
    # omission is still withheld instead of being treated as ordinary speech.
    speech_words, verse_words = speech.split(), verse.split()
    shorter, longer = sorted((speech_words, verse_words), key=len)
    if len(shorter) < 3:
        return False
    shorter_text = " ".join(shorter)
    window_matcher = SequenceMatcher(None, shorter_text, autojunk=False)
    for width in range(max(3, len(shorter) - 1), min(len(longer), len(shorter) + 1) + 1):
        if speech_window_cache is not None and len(speech_words) > len(verse_words):
            candidates = speech_window_cache.get(width)
            if candidates is None:
                candidates = []
                for start in range(len(speech_words) - width + 1):
                    candidates.append(" ".join(speech_words[start:start + width]))
                speech_window_cache[width] = candidates
        else:
            candidates = []
            for start in range(len(longer) - width + 1):
                candidates.append(" ".join(longer[start:start + width]))
        for window in candidates:
            window_length = len(window)
            if not _length_can_reach_ratio(len(shorter_text), window_length, _WINDOW_RATIO_THRESHOLD):
                continue
            if not _indel_can_reach_ratio(shorter_text, window, _WINDOW_RATIO_THRESHOLD):
                continue
            window_matcher.set_seq2(window)
            if window_matcher.ratio() >= 0.78:
                return True
    return False


def route(
    arabic: str,
    en: str,
    fr: str,
    uncertainty: str | None,
    renderings: dict,
) -> dict:
    """Route one candidate result through the religious-safety boundary."""

    if uncertainty is not None and str(uncertainty).strip():
        return _withheld("candidate_uncertainty")

    try:
        validate_renderings(renderings)
    except ValueError:
        return _withheld("rendering_registry_unavailable")

    speech = _normalise_arabic(arabic)
    if not speech:
        return _withheld("empty_arabic")

    entries: list[dict[str, Any]] = renderings["renderings"]
    normalized_entries = [(entry, _normalise_arabic(entry["arabic"])) for entry in entries]
    matches = [entry for entry, verse in normalized_entries if speech == verse]
    if matches:
        signatures = {
            tuple((e[lang]["text"], e[lang].get("footnotes", "")) for lang in ("english", "french"))
            for e in matches
        }
        if len(signatures) > 1:
            return _withheld("ambiguous_repeated_verse")
        entry = matches[0]
        sources = {}
        for language, key in (("english", "en"), ("french", "fr")):
            rendering = entry[language]
            sources[key] = {"source": rendering["source"], "version": rendering["version"]}
            for field in ("source_url", "footnotes", "publisher_description"):
                if field in rendering:
                    sources[key][field] = rendering[field]
        refs = [e["reference"] for e in matches if "reference" in e]
        if refs:
            sources["references"] = refs
        return {
            "outcome": "quran_rendering",
            "en": entry["english"]["text"],
            "fr": entry["french"]["text"],
            "reason": "exact_quran_match",
            "sources": sources,
        }

    speech_window_cache: dict[int, list[str]] = {}
    if any(_is_near_or_mixed(speech, verse, speech_window_cache) for _, verse in normalized_entries):
        return _withheld("possible_quran_or_mixed_speech")

    return {
        "outcome": "ordinary_translation",
        "en": en,
        "fr": fr,
        "reason": "no_quran_match",
        "sources": [],
    }
