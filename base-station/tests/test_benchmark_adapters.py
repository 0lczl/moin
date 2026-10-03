import json
import sys
import threading
from types import ModuleType
from pathlib import Path
from urllib.error import HTTPError

import pytest

from moin_benchmark import adapters


def baseline_config():
    return {
        "id": "baseline-v1", "name": "Current baseline", "adapter": "baseline",
        "asr": {"model": "Systran/faster-whisper-small", "revision": "536b0662742c02347bc0e980a01041f333bce120", "device": "cpu", "compute_type": "int8", "beam_size": 1, "vad_filter": False},
        "translation": {"model": "facebook/nllb-200-distilled-600M", "revision": "b" * 40, "source_lang": "arb_Arab", "max_new_tokens": 256, "num_beams": 1},
        "settings": {"timeout_seconds": 30},
        "prompts": {"en": "", "fr": ""},
    }


def remote_config():
    config = baseline_config()
    config.update(adapter="openai-compatible")
    config["asr"] = {"model": "asr-2026-08-01", "revision": "asr-2026-08-01", "base_url": "https://provider.invalid/v1", "credential_env": "MOIN_TEST_KEY"}
    config["translation"] = {"model": "translate-2026-08-01", "revision": "translate-2026-08-01", "base_url": "https://provider.invalid/v1", "credential_env": "MOIN_TEST_KEY"}
    config["prompts"] = {"en": "Translate faithfully into English.", "fr": "Traduisez fidèlement en français."}
    return config


def local_qwen_config():
    config = baseline_config()
    config.update(adapter="local-qwen", name="Local Whisper + Qwen")
    config["translation"] = {
        "model": "mlx-community/Qwen2.5-7B-Instruct-4bit",
        "revision": "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed",
        "max_new_tokens": 192,
    }
    config["prompts"] = {
        "en": "Translate the Arabic text faithfully into English. Return only the translation.",
        "fr": "Traduisez fidèlement le texte arabe en français. Répondez uniquement avec la traduction.",
    }
    return config


def local_translategemma_config():
    config = baseline_config()
    config.update(adapter="local-translategemma", name="Provisional TranslateGemma")
    config["asr"] = {
        "model": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
        "device": "cpu", "compute_type": "int8", "beam_size": 5, "vad_filter": False,
    }
    config["translation"] = {
        "model": "mlx-community/translategemma-4b-it-4bit",
        "revision": "5788ec08c047f3f2e17808101b8d9566ac930d58",
        "max_new_tokens": 1024,
    }
    config["prompts"] = {"en": "", "fr": ""}
    return config


def deepl_config():
    config = local_translategemma_config()
    config.update(id="deepl-v1", name="Whisper large-v3 + DeepL", adapter="deepl")
    config["translation"] = {
        "model": "deepl-text-translation-api", "revision": "v2",
        "base_url": "https://api-free.deepl.com", "endpoint": "/v2/translate",
        "credential_env": "DEEPL_AUTH_KEY", "source_lang": "AR",
        "target_lang_en": "EN-US", "target_lang_fr": "FR",
    }
    config["prompts"] = {"en": "", "fr": ""}
    return config


def test_config_is_exact_and_credentials_are_references():
    config = remote_config()
    adapters.validate_config(config)
    config["api_key"] = "secret"
    with pytest.raises(ValueError, match="unsupported"):
        adapters.validate_config(config)


def test_config_rejects_mutable_or_bypassed_model_identity(tmp_path):
    config = baseline_config()
    config["asr"]["revision"] = "main"
    with pytest.raises(ValueError, match="immutable"):
        adapters.validate_config(config)
    config = baseline_config()
    config["asr"]["model"] = str(tmp_path)
    with pytest.raises(ValueError, match="local path"):
        adapters.validate_config(config)
    config = remote_config()
    config["translation"]["revision"] = "friendly-alias"
    with pytest.raises(ValueError, match="snapshot"):
        adapters.validate_config(config)


def test_config_rejects_non_finite_and_invalid_baseline_settings():
    config = baseline_config()
    config["settings"]["timeout_seconds"] = float("nan")
    with pytest.raises(ValueError, match="positive"):
        adapters.validate_config(config)


def test_local_qwen_requires_pinned_model_nonempty_prompts_and_bounded_tokens():
    adapters.validate_config(local_qwen_config())
    config = local_qwen_config()
    config["translation"]["revision"] = "a" * 40
    with pytest.raises(ValueError, match="pinned Qwen"):
        adapters.validate_config(config)
    config = local_qwen_config()
    config["asr"]["revision"] = "a" * 40
    with pytest.raises(ValueError, match="baseline Whisper"):
        adapters.validate_config(config)
    config = local_qwen_config()
    config["prompts"]["fr"] = ""
    with pytest.raises(ValueError, match="prompts.fr"):
        adapters.validate_config(config)
    config = local_qwen_config()
    config["translation"]["max_new_tokens"] = 1025
    with pytest.raises(ValueError, match="between 1 and 1024"):
        adapters.validate_config(config)
    config = baseline_config()
    config["translation"]["num_beams"] = True
    with pytest.raises(ValueError, match="positive integer"):
        adapters.validate_config(config)


def test_local_translategemma_requires_exact_pins_and_template_owned_prompts():
    config = local_translategemma_config()
    adapters.validate_config(config)
    config["translation"]["revision"] = "a" * 40
    with pytest.raises(ValueError, match="pinned TranslateGemma"):
        adapters.validate_config(config)
    config = local_translategemma_config()
    config["asr"]["revision"] = "a" * 40
    with pytest.raises(ValueError, match="approved pinned Whisper large-v3"):
        adapters.validate_config(config)
    config = local_translategemma_config()
    config["prompts"]["en"] = "custom system prompt"
    with pytest.raises(ValueError, match="prompts must be empty"):
        adapters.validate_config(config)
    config = local_translategemma_config()
    config["translation"]["max_new_tokens"] = 1025
    with pytest.raises(ValueError, match="between 1 and 1024"):
        adapters.validate_config(config)


def test_published_translategemma_candidate_config_is_valid():
    candidates = json.loads((Path(__file__).parents[1] / "benchmark-data/local-comparison.json").read_text())
    config = next(candidate for candidate in candidates if candidate["id"] == "local-translategemma")
    adapters.validate_config(config)
    assert config["translation"]["revision"] == "5788ec08c047f3f2e17808101b8d9566ac930d58"


def test_published_deepl_candidate_config_is_valid():
    candidates = json.loads((Path(__file__).parents[1] / "benchmark-data/local-comparison.json").read_text())
    config = next(candidate for candidate in candidates if candidate["id"] == "deepl-v1")
    adapters.validate_config(config)
    assert config["translation"]["credential_env"] == "DEEPL_AUTH_KEY"


def test_deepl_candidate_is_secret_free_and_requires_the_approved_asr():
    adapters.validate_config(deepl_config())
    config = deepl_config()
    config["translation"]["base_url"] = "https://api.deepl.com"
    with pytest.raises(ValueError, match="API Free"):
        adapters.validate_config(config)
    config = deepl_config()
    config["asr"]["revision"] = "a" * 40
    with pytest.raises(ValueError, match="approved pinned Whisper"):
        adapters.validate_config(config)


def test_deepl_uses_local_large_asr_and_sends_only_text_with_a_server_key(monkeypatch, tmp_path):
    requests = []
    gate = threading.Barrier(2, timeout=1)

    class Segment:
        text = " السلام عليكم "

    class Whisper:
        def transcribe(self, path, **kwargs):
            assert kwargs == {"language": "ar", "beam_size": 5, "vad_filter": False}
            return [Segment()], type("Info", (), {"language_probability": .99})()

    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps(self.payload).encode()

    def fake_urlopen(request, timeout, **kwargs):
        requests.append((request, timeout))
        gate.wait()
        target = json.loads(request.data)["target_lang"]
        return Response({"translations": [{"text": {"EN-US": "Peace be upon you", "FR": "Que la paix soit sur vous"}[target]}]})

    monkeypatch.setenv("DEEPL_AUTH_KEY", "secret-key")
    monkeypatch.setattr(adapters, "_load_deepl_asr", lambda config: Whisper())
    monkeypatch.setattr(adapters, "urlopen", fake_urlopen)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(deepl_config(), audio)

    assert (result["arabic"], result["en"], result["fr"], result["failure"]) == (
        "السلام عليكم", "Peace be upon you", "Que la paix soit sur vous", None,
    )
    assert sorted((json.loads(item[0].data) for item in requests), key=lambda item: item["target_lang"]) == [
        {"text": ["السلام عليكم"], "source_lang": "AR", "target_lang": "EN-US"},
        {"text": ["السلام عليكم"], "source_lang": "AR", "target_lang": "FR"},
    ]
    assert all(item[0].headers["Authorization"] == "DeepL-Auth-Key secret-key" for item in requests)
    assert all(b"secret-key" not in item[0].data for item in requests)


def test_deepl_groq_uses_exact_provider_asr_and_reports_distinct_runtime(monkeypatch, tmp_path):
    from moin_studio import groq_asr

    seen_audio = []

    def transcribe(path, *, timeout_seconds):
        seen_audio.append((Path(path), timeout_seconds))
        return {"text": "السلام عليكم", "model": "whisper-large-v3"}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"translations":[{"text":"Peace"}]}'

    sent = []
    def fake_urlopen(request, timeout, **kwargs):
        sent.append(json.loads(request.data))
        return Response()

    monkeypatch.setenv("MOIN_ASR_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "groq-secret")
    monkeypatch.setenv("DEEPL_AUTH_KEY", "deepl-secret")
    monkeypatch.setattr(groq_asr, "transcribe", transcribe)
    monkeypatch.setattr(adapters, "urlopen", fake_urlopen)
    audio = tmp_path / "canonical-segment.wav"
    audio.write_bytes(b"wav")

    result = adapters.process(deepl_config(), audio)

    assert result["failure"] is None
    assert result["arabic"] == "السلام عليكم"
    assert seen_audio == [(audio, 30)]
    assert sent and all(item["text"] == ["السلام عليكم"] for item in sent)
    assert adapters.asr_runtime_identity(deepl_config()) == {
        "provider": "groq", "model": "whisper-large-v3", "revision": None,
        "identity_kind": "provider_model_id", "configured_local_checkpoint_used": False,
    }


def test_deepl_budget_reserves_each_target_translation_and_blocks_exhaustion(monkeypatch, tmp_path):
    from moin_studio.budget import DEEPL_CHAR_LIMIT_LIFETIME

    class Segment:
        text = " السلام عليكم "

    class Whisper:
        def transcribe(self, path, **kwargs):
            return [Segment()], type("Info", (), {"language_probability": .99})()

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"translations":[{"text":"Peace"}]}'

    monkeypatch.delenv("MOIN_ASR_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPL_AUTH_KEY", "deepl-secret")
    monkeypatch.setenv("MOIN_USAGE_LEDGER_DIR", str(tmp_path / "ledger"))
    monkeypatch.setattr(adapters, "_load_deepl_asr", lambda config: Whisper())
    calls = []
    monkeypatch.setattr(adapters, "urlopen", lambda request, timeout, **kwargs: calls.append(request) or Response())
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"wav")

    complete = adapters.process(deepl_config(), audio)
    assert complete["failure"] is None
    ledger = json.loads((tmp_path / "ledger" / "usage.json").read_text())
    assert ledger["deepl_chars_lifetime"] == 2 * len("السلام عليكم")
    assert len(calls) == 2

    ledger["deepl_chars_lifetime"] = DEEPL_CHAR_LIMIT_LIFETIME
    (tmp_path / "ledger" / "usage.json").write_text(json.dumps(ledger))
    calls.clear()
    exhausted = adapters.process(deepl_config(), audio)
    assert exhausted["failure"]["code"] == "budget_exhausted"
    assert exhausted["en"] == exhausted["fr"] == ""
    assert calls == []


def test_deepl_supports_the_pro_hostname_and_explains_a_rejected_key(monkeypatch, tmp_path):
    class Segment:
        text = " السلام عليكم "

    class Whisper:
        def transcribe(self, path, **kwargs):
            return [Segment()], type("Info", (), {"language_probability": .99})()

    seen = []
    def pro_urlopen(request, timeout, **kwargs):
        seen.append(request.full_url)
        raise HTTPError(request.full_url, 403, "forbidden", {}, None)

    monkeypatch.setenv("DEEPL_AUTH_KEY", "secret-key")
    monkeypatch.setenv("DEEPL_API_BASE_URL", "https://api.deepl.com")
    monkeypatch.setattr(adapters, "_load_deepl_asr", lambda config: Whisper())
    monkeypatch.setattr(adapters, "urlopen", pro_urlopen)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(deepl_config(), audio)

    assert seen == ["https://api.deepl.com/v2/translate"] * 2
    assert result["failure"] == {
        "stage": "en", "code": "credential_rejected",
        "message": "DeepL did not accept this API key. Check that the key is active.", "retryable": False,
    }


def test_deepl_falls_back_from_free_to_pro_without_exposing_the_key(monkeypatch, tmp_path):
    class Segment:
        text = " السلام عليكم "

    class Whisper:
        def transcribe(self, path, **kwargs):
            return [Segment()], type("Info", (), {"language_probability": .99})()

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"translations":[{"text":"Peace"}]}'

    seen = []
    def free_then_pro(request, timeout, **kwargs):
        seen.append(request.full_url)
        if request.full_url.startswith("https://api-free.deepl.com"):
            raise HTTPError(request.full_url, 403, "forbidden", {}, None)
        return Response()

    monkeypatch.setenv("DEEPL_AUTH_KEY", "secret-key")
    monkeypatch.delenv("DEEPL_API_BASE_URL", raising=False)
    monkeypatch.setattr(adapters, "_load_deepl_asr", lambda config: Whisper())
    monkeypatch.setattr(adapters, "urlopen", free_then_pro)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(deepl_config(), audio)

    assert result["failure"] is None
    assert (result["en"], result["fr"]) == ("Peace", "Peace")
    assert sorted(seen) == sorted([
        "https://api-free.deepl.com/v2/translate", "https://api.deepl.com/v2/translate",
        "https://api-free.deepl.com/v2/translate", "https://api.deepl.com/v2/translate",
    ])


def test_local_translategemma_uses_documented_language_template_and_guard_first(monkeypatch, tmp_path):
    calls = []

    class Segment:
        text = " الحمد لله "

    class Whisper:
        def transcribe(self, path, **kwargs):
            calls.append(("asr", kwargs))
            return [Segment()], type("Info", (), {"language_probability": .99})()

    class Tokenizer:
        def apply_chat_template(self, messages, **kwargs):
            calls.append(("template", messages, kwargs))
            return messages[0]["content"][0]["target_lang_code"]

    def fake_generate(model, tokenizer, prompt, max_tokens):
        calls.append(("generate", prompt, max_tokens))
        return {"en": " Praise be to Allah ", "fr": " Louange à Allah "}[prompt]

    monkeypatch.setattr(adapters, "_load_local_translategemma", lambda config: (Whisper(), Tokenizer(), object()))
    monkeypatch.setattr(adapters, "_mlx_generate", fake_generate)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")

    guarded = adapters.process(
        local_translategemma_config(), audio,
        translation_guard=lambda arabic: {"en": "trusted", "fr": "fiable", "uncertainty": "trusted"},
    )
    assert (guarded["en"], guarded["fr"]) == ("trusted", "fiable")
    assert [call[0] for call in calls] == ["asr"]
    calls.clear()

    result = adapters.process(local_translategemma_config(), audio)
    assert (result["arabic"], result["en"], result["fr"]) == (
        "الحمد لله", "Praise be to Allah", "Louange à Allah",
    )
    templates = [call for call in calls if call[0] == "template"]
    assert [call[1] for call in templates] == [
        [{"role": "user", "content": [{"type": "text", "source_lang_code": "ar", "target_lang_code": "en", "text": "الحمد لله"}]}],
        [{"role": "user", "content": [{"type": "text", "source_lang_code": "ar", "target_lang_code": "fr", "text": "الحمد لله"}]}],
    ]
    assert all(call[2] == {"add_generation_prompt": True} for call in templates)
    assert [(call[1], call[2]) for call in calls if call[0] == "generate"] == [("en", 1024), ("fr", 1024)]


def test_baseline_uses_greedy_pinned_models_and_normalizes(monkeypatch, tmp_path):
    calls = {}

    class Segment:
        text = " السلام عليكم "

    class Whisper:
        def transcribe(self, path, **kwargs):
            calls["asr"] = (path, kwargs)
            return [Segment()], type("Info", (), {"language_probability": .97})()

    class Tokenizer:
        src_lang = None
        def __call__(self, text, **kwargs): return {"input_ids": [1]}
        def convert_tokens_to_ids(self, target): return target
        def batch_decode(self, tokens, **kwargs): return [f" {tokens[0]} "]

    class Translator:
        def generate(self, **kwargs):
            calls.setdefault("translations", []).append(kwargs)
            return [kwargs["forced_bos_token_id"]]

    monkeypatch.setattr(adapters, "_load_baseline", lambda config: (Whisper(), Tokenizer(), Translator()))
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFFfixture")
    result = adapters.process(baseline_config(), audio)

    assert result["arabic"] == "السلام عليكم"
    assert result["en"] == "eng_Latn"
    assert result["fr"] == "fra_Latn"
    assert result["failure"] is None
    assert calls["asr"][1] == {"language": "ar", "beam_size": 1, "vad_filter": False}
    assert [call["num_beams"] for call in calls["translations"]] == [1, 1]
    assert set(result["timing_ms"]) == {"model_load", "asr", "en", "fr", "translation_wall", "total"}


def test_openai_compatible_transport_uses_multipart_and_json(monkeypatch, tmp_path):
    requests = []

    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps(self.payload).encode()

    def fake_urlopen(request, timeout, **kwargs):
        requests.append((request, timeout))
        if request.full_url.endswith("audio/transcriptions"):
            return Response({"text": "إنما الأعمال بالنيات"})
        body = json.loads(request.data)
        language = "English" if "English" in body["messages"][0]["content"] else "français"
        return Response({"choices": [{"message": {"content": language}}]})

    monkeypatch.setenv("MOIN_TEST_KEY", "top-secret")
    monkeypatch.setattr(adapters, "urlopen", fake_urlopen)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"audio bytes")
    result = adapters.process(remote_config(), audio)

    assert (result["arabic"], result["en"], result["fr"]) == ("إنما الأعمال بالنيات", "English", "français")
    assert result["failure"] is None
    assert requests[0][0].headers["Content-type"].startswith("multipart/form-data;")
    assert b'top-secret' not in requests[0][0].data
    assert json.loads(requests[1][0].data)["temperature"] == 0


def test_local_qwen_uses_chat_template_greedy_generation_and_guard_first(monkeypatch, tmp_path):
    calls = []

    class Segment:
        text = " السلام عليكم "

    class Whisper:
        def transcribe(self, path, **kwargs):
            return [Segment()], type("Info", (), {"language_probability": .99})()

    class Tokenizer:
        def apply_chat_template(self, messages, **kwargs):
            calls.append(("prompt", messages, kwargs))
            return f"PROMPT:{messages[0]['content']}:{messages[1]['content']}"

    def fake_generate(model, tokenizer, prompt, max_tokens):
        calls.append(("generate", {"prompt": prompt, "max_tokens": max_tokens}))
        return " translated "

    monkeypatch.setattr(adapters, "_load_local_qwen", lambda config: (Whisper(), Tokenizer(), object()))
    monkeypatch.setattr(adapters, "_mlx_generate", fake_generate)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")

    guarded = adapters.process(
        local_qwen_config(), audio,
        translation_guard=lambda arabic: {"en": "trusted", "fr": "fiable", "uncertainty": "trusted"},
    )
    assert (guarded["en"], guarded["fr"]) == ("trusted", "fiable")
    assert calls == []

    result = adapters.process(local_qwen_config(), audio)
    assert (result["arabic"], result["en"], result["fr"]) == ("السلام عليكم", "translated", "translated")
    prompts = [call for call in calls if call[0] == "prompt"]
    generations = [call for call in calls if call[0] == "generate"]
    assert [call[1][0]["content"] for call in prompts] == [
        local_qwen_config()["prompts"]["en"], local_qwen_config()["prompts"]["fr"],
    ]
    assert all(call[2] == {"add_generation_prompt": True, "tokenize": False} for call in prompts)
    assert all(call[1]["max_tokens"] == 192 for call in generations)


def test_mlx_generation_builds_an_explicit_zero_temperature_sampler(monkeypatch):
    calls = {}
    mlx_lm = ModuleType("mlx_lm")
    sample_utils = ModuleType("mlx_lm.sample_utils")
    greedy = object()

    def make_sampler(**kwargs):
        calls["sampler_args"] = kwargs
        return greedy

    def generate(model, tokenizer, **kwargs):
        calls["generate"] = kwargs
        return "translation"

    mlx_lm.generate = generate
    sample_utils.make_sampler = make_sampler
    monkeypatch.setitem(sys.modules, "mlx_lm", mlx_lm)
    monkeypatch.setitem(sys.modules, "mlx_lm.sample_utils", sample_utils)

    assert adapters._mlx_generate(object(), object(), "prompt", 77) == "translation"
    assert calls["sampler_args"] == {"temp": 0.0}
    assert calls["generate"]["sampler"] is greedy
    assert calls["generate"]["max_tokens"] == 77


def test_provider_errors_are_safe_and_do_not_leak_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("MOIN_TEST_KEY", "super-secret-token")
    monkeypatch.setattr(adapters, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("super-secret-token leaked")))
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")

    result = adapters.process(remote_config(), audio)

    assert result["failure"] == {"stage": "asr", "code": "candidate_failed", "message": "Candidate processing failed.", "retryable": False}
    assert "super-secret-token" not in json.dumps(result)


def test_translation_guard_skips_all_translation_calls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("MOIN_TEST_KEY", "fixture-key")

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"text":"Quranic Arabic"}'

    def fake_urlopen(request, timeout, **kwargs):
        calls.append(request.full_url)
        return Response()

    monkeypatch.setattr(adapters, "urlopen", fake_urlopen)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(
        remote_config(), audio,
        translation_guard=lambda arabic: {"en": "Trusted English", "fr": "Français fiable", "uncertainty": "trusted_quran_rendering"},
    )

    assert result["en"] == "Trusted English"
    assert result["fr"] == "Français fiable"
    assert result["uncertainty"] == "trusted_quran_rendering"
    assert calls == ["https://provider.invalid/v1/audio/transcriptions"]


def test_withheld_guard_normalizes_none_and_low_confidence_skips_translation(monkeypatch, tmp_path):
    calls = []

    class Segment:
        text = " ambiguous "

    class Whisper:
        def transcribe(self, path, **kwargs):
            return [Segment()], type("Info", (), {"language_probability": .2})()

    monkeypatch.setattr(adapters, "_load_baseline", lambda config: (Whisper(), object(), object()))
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(baseline_config(), audio, translation_guard=lambda arabic: calls.append(arabic))
    assert calls == []
    assert result["uncertainty"] == "low_asr_language_confidence"
    assert result["en"] == result["fr"] == ""


def test_guard_accepts_withheld_none_outputs(monkeypatch, tmp_path):
    monkeypatch.setenv("MOIN_TEST_KEY", "fixture-key")

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"text":"uncertain Arabic"}'

    monkeypatch.setattr(adapters, "urlopen", lambda *args, **kwargs: Response())
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(remote_config(), audio, translation_guard=lambda arabic: {"en": None, "fr": None, "uncertainty": "withheld"})
    assert result["en"] == result["fr"] == ""
    assert result["uncertainty"] == "withheld"


def test_empty_baseline_transcript_is_a_normalized_failure(monkeypatch, tmp_path):
    class Whisper:
        def transcribe(self, path, **kwargs):
            return [], type("Info", (), {"language_probability": 1.0})()

    monkeypatch.setattr(adapters, "_load_baseline", lambda config: (Whisper(), object(), object()))
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    result = adapters.process(baseline_config(), audio)
    assert result["failure"]["stage"] == "asr"
    assert result["failure"]["code"] == "candidate_failed"
    assert result["en"] == result["fr"] == ""


def test_runtime_identity_is_non_secret_and_versioned():
    identity = adapters.runtime_identity()
    assert identity["python"]
    assert set(identity["packages"]) == {"faster-whisper", "huggingface-hub", "transformers", "torch", "mlx", "mlx-lm"}


def test_missing_credential_and_audio_are_normalized(monkeypatch, tmp_path):
    monkeypatch.delenv("MOIN_TEST_KEY", raising=False)
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"fixture")
    missing_key = adapters.process(remote_config(), audio)
    missing_audio = adapters.process(remote_config(), tmp_path / "missing.wav")
    assert missing_key["failure"]["code"] == "credential_unavailable"
    assert missing_audio["failure"]["code"] == "audio_unavailable"
