from __future__ import annotations

import pytest
from difflib import SequenceMatcher
import random
from rapidfuzz.distance import Indel

from moin_benchmark.safety import _indel_can_reach_ratio, _is_near_or_mixed, route, validate_renderings


def _registry() -> dict:
    return {
        "schema_version": 1,
        "detection_ready": True,
        "renderings": [
            {
                "arabic": "قُلْ هُوَ اللَّهُ أَحَدٌ",
                "english": {
                    "text": "Approved English rendering",
                    "source": "Fixture source",
                    "version": "fixture-v1",
                    "approved": True,
                },
                "french": {
                    "text": "Rendu français approuvé",
                    "source": "Source de test",
                    "version": "fixture-v1",
                    "approved": True,
                },
            }
        ],
    }


def test_ordinary_speech_keeps_candidate_translations():
    result = route("نتحدث اليوم عن الصبر", "Today we discuss patience", "Aujourd'hui...", None, _registry())
    assert result["outcome"] == "ordinary_translation"
    assert result["en"] == "Today we discuss patience"
    assert result["fr"] == "Aujourd'hui..."


def test_exact_normalized_match_uses_both_approved_sourced_renderings():
    result = route("قل هو الله احد.", "machine en", "machine fr", None, _registry())
    assert result["outcome"] == "quran_rendering"
    assert result["en"] == "Approved English rendering"
    assert result["fr"] == "Rendu français approuvé"
    assert result["sources"]["en"] == {"source": "Fixture source", "version": "fixture-v1"}
    assert result["sources"]["fr"]["version"] == "fixture-v1"


@pytest.mark.parametrize(
    "arabic",
    [
        "قل هو الله احدا",  # close ASR result, but not exact
        "قال الشيخ قل هو الله احد ثم شرح المعنى",  # verse mixed with teaching
        "هو الله اهد",  # damaged fragment of the configured verse
    ],
)
def test_near_matches_and_mixed_speech_are_withheld(arabic):
    result = route(arabic, "machine en", "machine fr", None, _registry())
    assert result["outcome"] == "withheld"
    assert result["en"] is None and result["fr"] is None
    assert result["reason"] == "possible_quran_or_mixed_speech"


@pytest.mark.parametrize(
    ("speech", "expected"),
    [
        ("ذلك الكتاب لا ريب فيه هدى للمتقين", True),
        ("الكتاب لا ريب فيه هدى للمتقين", True),  # first word omitted by ASR
        ("ذلك الكتاب لا ريب فيه هدى للمتقن", True),  # final word damaged by ASR
        ("قال الشيخ ذلك الكتاب لا ريب فيه هدى للمتقين ثم شرح", True),
        ("درس اليوم عن الصبر", False),
    ],
)
def test_lossless_prefilters_preserve_verse_and_asr_fragment_decisions(speech, expected):
    assert _is_near_or_mixed(speech, "ذلك الكتاب لا ريب فيه هدى للمتقين") is expected


@pytest.mark.parametrize("arabic", [
    "الكتاب لا ريب فيه هدى للمتقين",  # ASR omitted the opening word
    "ذلك الكتاب لا ريب في هدى للمتقين",  # ASR omitted a short interior word
    "ذلك الكتاب لا ريب فيه هدى للمتقن",  # ASR damaged the final word
])
def test_asr_damaged_fragments_of_longer_verse_fail_closed(arabic):
    registry = _registry()
    registry["renderings"][0]["arabic"] = "ذلك الكتاب لا ريب فيه هدى للمتقين"
    result = route(arabic, "candidate en", "candidate fr", None, registry)
    assert result["outcome"] == "withheld"
    assert result["reason"] == "possible_quran_or_mixed_speech"


def test_indel_similarity_is_an_upper_bound_for_randomized_sequences():
    rng = random.Random(112)
    alphabet = "ابجد هوز XYZ"
    for _ in range(500):
        first = "".join(rng.choices(alphabet, k=rng.randrange(0, 81)))
        second = "".join(rng.choices(alphabet, k=rng.randrange(0, 81)))
        if not first and not second:
            continue
        upper_bound = Indel.normalized_similarity(first, second)
        actual = SequenceMatcher(None, first, second, autojunk=False).ratio()
        assert upper_bound + 1e-15 >= actual
        for threshold, value in (((21, 25), 0.84), ((39, 50), 0.78)):
            if actual >= value:
                assert _indel_can_reach_ratio(first, second, threshold)


def test_uncertainty_is_withheld_even_for_an_exact_match():
    result = route("قل هو الله أحد", "machine en", "machine fr", "low confidence", _registry())
    assert result["outcome"] == "withheld"
    assert result["reason"] == "candidate_uncertainty"


def test_empty_registry_fails_closed_for_ordinary_speech():
    result = route("هذا درس عادي", "ordinary", "ordinaire", None, {})
    assert result["outcome"] == "withheld"
    assert result["reason"] == "rendering_registry_unavailable"


def test_validation_requires_approved_sourced_renderings_in_both_languages():
    registry = _registry()
    registry["renderings"][0]["french"]["approved"] = False
    with pytest.raises(ValueError, match="french is not approved"):
        validate_renderings(registry)


def test_repeated_verses_are_valid_but_different_renderings_are_withheld():
    import copy
    registry = _registry()
    registry['renderings'][0]['reference'] = {'sura': 1, 'aya': 1}
    repeated = copy.deepcopy(registry['renderings'][0])
    repeated['reference'] = {'sura': 2, 'aya': 1}
    registry['renderings'].append(repeated)
    validate_renderings(registry)
    result = route('قل هو الله أحد', '', '', None, registry)
    assert result['outcome'] == 'quran_rendering'
    assert len(result['sources']['references']) == 2
    repeated['french']['text'] = 'Different context-sensitive rendering'
    result = route('قل هو الله أحد', '', '', None, registry)
    assert result['reason'] == 'ambiguous_repeated_verse'


def test_single_letter_verse_does_not_match_inside_ordinary_words():
    registry = _registry()
    registry['renderings'][0]['arabic'] = 'ق'
    result = route('هذا تسجيل صوتي', 'Recording', 'Enregistrement', None, registry)
    assert result['outcome'] == 'ordinary_translation'


def test_quran_footnotes_and_reference_are_preserved():
    registry = _registry()
    entry = registry['renderings'][0]
    entry['reference'] = {'sura':112,'aya':1}
    entry['english']['footnotes'] = 'Publisher footnote retained verbatim.'
    result = route('قل هو الله احد', '', '', None, registry)
    assert result['sources']['en']['footnotes'] == entry['english']['footnotes']
    assert result['sources']['references'] == [{'sura':112,'aya':1}]
