"""Candidate adapters for the Moin benchmark.

The public surface is deliberately small: validate a locked, secret-free
configuration and process one canonical audio file. Heavy local models are
loaded lazily, while remote credentials are resolved only from an environment
variable named by the configuration.
"""

from __future__ import annotations

import json
import math
import mimetypes
import os
import platform
import re
import ssl
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import certifi


_TOP_KEYS = {"id", "name", "adapter", "asr", "translation", "settings", "prompts"}
_MODEL_REQUIRED = {"model", "revision"}
_BASELINE_ASR = _MODEL_REQUIRED | {"device", "compute_type", "beam_size", "vad_filter"}
_BASELINE_MT = _MODEL_REQUIRED | {"source_lang", "max_new_tokens", "num_beams"}
_LOCAL_QWEN_MT = _MODEL_REQUIRED | {"max_new_tokens"}
_DEEPL_MT = _MODEL_REQUIRED | {"base_url", "credential_env", "endpoint", "source_lang", "target_lang_en", "target_lang_fr"}
_REMOTE_MODEL = _MODEL_REQUIRED | {"base_url", "credential_env", "endpoint"}
_SETTINGS = {"timeout_seconds"}
_PROMPTS = {"en", "fr"}
_LOCAL_CACHE: dict[str, tuple[Any, Any, Any]] = {}
_COMMIT_REVISION = re.compile(r"[0-9a-fA-F]{40}")
_WHISPER_MODEL = "Systran/faster-whisper-small"
_WHISPER_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
_QWEN_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
_QWEN_REVISION = "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed"
_TRANSLATEGEMMA_MODEL = "mlx-community/translategemma-4b-it-4bit"
_TRANSLATEGEMMA_REVISION = "5788ec08c047f3f2e17808101b8d9566ac930d58"
_WHISPER_LARGE_V3_MODEL = "Systran/faster-whisper-large-v3"
_WHISPER_LARGE_V3_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
_WHISPER_RUNTIME_FILES = ["model.bin", "config.json", "tokenizer.json", "vocabulary.*"]
_DEEPL_MODEL = "deepl-text-translation-api"
_DEEPL_REVISION = "v2"
_DEEPL_FREE_BASE_URL = "https://api-free.deepl.com"
_DEEPL_PRO_BASE_URL = "https://api.deepl.com"


class ProviderFailure(RuntimeError):
    """A provider error that is safe and useful to present to the operator."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise ValueError(f"unsupported {label} keys: {', '.join(sorted(extra))}")


def _nonempty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def validate_config(config: dict[str, Any]) -> None:
    """Validate the complete, intentionally narrow V1 candidate schema."""
    config = _mapping(config, "config")
    if set(config) != _TOP_KEYS:
        missing = _TOP_KEYS - set(config)
        extra = set(config) - _TOP_KEYS
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"unsupported: {', '.join(sorted(extra))}")
        raise ValueError("invalid candidate keys (" + "; ".join(details) + ")")

    _nonempty_string(config["id"], "id")
    _nonempty_string(config["name"], "name")
    if config["adapter"] not in {"baseline", "local-qwen", "local-translategemma", "deepl", "openai-compatible"}:
        raise ValueError("adapter must be baseline, local-qwen, local-translategemma, deepl, or openai-compatible")

    asr = _mapping(config["asr"], "asr")
    translation = _mapping(config["translation"], "translation")
    settings = _mapping(config["settings"], "settings")
    prompts = _mapping(config["prompts"], "prompts")
    is_local = config["adapter"] in {"baseline", "local-qwen", "local-translategemma", "deepl"}
    allowed_asr = _BASELINE_ASR if is_local else _REMOTE_MODEL
    allowed_mt = (_BASELINE_MT if config["adapter"] == "baseline" else
                  _LOCAL_QWEN_MT if config["adapter"] in {"local-qwen", "local-translategemma"} else _REMOTE_MODEL)
    if config["adapter"] == "deepl":
        allowed_mt = _DEEPL_MT
    _exact_keys(asr, allowed_asr, "asr")
    _exact_keys(translation, allowed_mt, "translation")
    _exact_keys(settings, _SETTINGS, "settings")
    _exact_keys(prompts, _PROMPTS, "prompts")
    for block_name, block in (("asr", asr), ("translation", translation)):
        if not _MODEL_REQUIRED <= set(block):
            raise ValueError(f"{block_name} requires model and revision")
        _nonempty_string(block["model"], f"{block_name}.model")
        _nonempty_string(block["revision"], f"{block_name}.revision")
    for language in _PROMPTS:
        if not isinstance(prompts.get(language), str):
            raise ValueError(f"prompts.{language} must be a string")

    timeout = settings.get("timeout_seconds", 60)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("settings.timeout_seconds must be positive")
    if is_local:
        if config["adapter"] == "baseline" and prompts != {"en": "", "fr": ""}:
            raise ValueError("baseline prompts must be empty because the adapter does not use them")
        revision_blocks = (("asr", asr),) if config["adapter"] == "deepl" else (("asr", asr), ("translation", translation))
        for block_name, block in revision_blocks:
            if not _COMMIT_REVISION.fullmatch(block["revision"]):
                raise ValueError(f"{block_name}.revision must be an immutable 40-character commit")
            if Path(block["model"]).exists():
                raise ValueError(f"{block_name}.model must be a pinned repository id, not a local path")
        if "device" in asr:
            _nonempty_string(asr["device"], "asr.device")
        if "compute_type" in asr:
            _nonempty_string(asr["compute_type"], "asr.compute_type")
        if "vad_filter" in asr and not isinstance(asr["vad_filter"], bool):
            raise ValueError("asr.vad_filter must be boolean")
        for block, key in ((asr, "beam_size"), (translation, "max_new_tokens"), (translation, "num_beams")):
            if key in block and (isinstance(block[key], bool) or not isinstance(block[key], int) or block[key] < 1):
                raise ValueError(f"{key} must be a positive integer")
        if "source_lang" in translation:
            _nonempty_string(translation["source_lang"], "translation.source_lang")
        if config["adapter"] == "local-qwen":
            for language in _PROMPTS:
                _nonempty_string(prompts[language], f"prompts.{language}")
            if translation["model"] != _QWEN_MODEL or translation["revision"] != _QWEN_REVISION:
                raise ValueError("local-qwen requires the pinned Qwen model and revision")
            if asr["model"] != _WHISPER_MODEL or asr["revision"] != _WHISPER_REVISION:
                raise ValueError("local-qwen requires the pinned baseline Whisper model and revision")
            max_tokens = translation.get("max_new_tokens", 256)
            if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 1024:
                raise ValueError("max_new_tokens must be an integer between 1 and 1024")
        if config["adapter"] == "local-translategemma":
            if prompts != {"en": "", "fr": ""}:
                raise ValueError("local-translategemma prompts must be empty; language instructions come from its chat template")
            if translation["model"] != _TRANSLATEGEMMA_MODEL or translation["revision"] != _TRANSLATEGEMMA_REVISION:
                raise ValueError("local-translategemma requires the pinned TranslateGemma model and revision")
            if asr["model"] != _WHISPER_LARGE_V3_MODEL or asr["revision"] != _WHISPER_LARGE_V3_REVISION:
                raise ValueError("local-translategemma requires the approved pinned Whisper large-v3 model and revision")
            max_tokens = translation.get("max_new_tokens", 256)
            if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 1024:
                raise ValueError("max_new_tokens must be an integer between 1 and 1024")
        if config["adapter"] == "deepl":
            if prompts != {"en": "", "fr": ""}:
                raise ValueError("deepl prompts must be empty; DeepL receives only source and target language codes")
            if asr["model"] != _WHISPER_LARGE_V3_MODEL or asr["revision"] != _WHISPER_LARGE_V3_REVISION:
                raise ValueError("deepl requires the approved pinned Whisper large-v3 model and revision")
            if translation["model"] != _DEEPL_MODEL or translation["revision"] != _DEEPL_REVISION:
                raise ValueError("deepl requires the supported DeepL text translation v2 endpoint")
            if translation["base_url"] != _DEEPL_FREE_BASE_URL or translation["endpoint"] != "/v2/translate":
                raise ValueError("deepl must use the configured DeepL API Free v2 translation endpoint")
            if translation["source_lang"] != "AR" or translation["target_lang_en"] != "EN-US" or translation["target_lang_fr"] != "FR":
                raise ValueError("deepl must use AR source and EN-US/FR targets")
            _nonempty_string(translation["credential_env"], "translation.credential_env")
    else:
        for language in _PROMPTS:
            _nonempty_string(prompts[language], f"prompts.{language}")
        for block_name, block in (("asr", asr), ("translation", translation)):
            for key in ("base_url", "credential_env"):
                _nonempty_string(block.get(key), f"{block_name}.{key}")
            if not block["base_url"].startswith(("http://", "https://")):
                raise ValueError(f"{block_name}.base_url must be an HTTP(S) URL")
            if "endpoint" in block:
                _nonempty_string(block["endpoint"], f"{block_name}.endpoint")
            if block["revision"] != block["model"]:
                raise ValueError(f"{block_name}.revision must equal the immutable provider model snapshot id")


def runtime_identity() -> dict[str, Any]:
    """Return non-secret runtime versions used to reproduce a candidate run."""
    packages: dict[str, str | None] = {}
    for package in ("faster-whisper", "huggingface-hub", "transformers", "torch", "mlx", "mlx-lm"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    return {"python": platform.python_version(), "packages": packages}


def asr_runtime_identity(config: dict[str, Any]) -> dict[str, Any]:
    """Describe the ASR actually selected for this run without recording secrets.

    The DeepL candidate can explicitly replace its configured local checkpoint
    with Groq's provider-managed exact model ID. That distinction belongs in
    run metadata, separate from the immutable candidate configuration.
    """
    block = config["asr"]
    if config["adapter"] == "deepl":
        selected = os.environ.get("MOIN_ASR_PROVIDER", "")
        if selected == "groq":
            return {
                "provider": "groq",
                "model": "whisper-large-v3",
                "revision": None,
                "identity_kind": "provider_model_id",
                "configured_local_checkpoint_used": False,
            }
        if selected not in {"", "local"}:
            return {"provider": "unsupported", "model": None, "revision": None, "identity_kind": "invalid_selection"}
    if config["adapter"] == "openai-compatible":
        return {
            "provider": "configured_remote_api",
            "model": block["model"],
            "revision": block["revision"],
            "identity_kind": "provider_model_id",
        }
    return {
        "provider": "local",
        "model": block["model"],
        "revision": block["revision"],
        "identity_kind": "pinned_checkpoint" if _COMMIT_REVISION.fullmatch(block["revision"]) else "configured_model_id",
    }


def _failure(stage: str, code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {"stage": stage, "code": code, "message": message, "retryable": retryable}


def _empty_result(started: float) -> dict[str, Any]:
    return {
        "arabic": "", "en": "", "fr": "",
        "timing_ms": {"model_load": 0, "asr": 0, "en": 0, "fr": 0, "translation_wall": 0, "total": round((time.perf_counter() - started) * 1000, 3)},
        "uncertainty": None, "failure": None,
    }


def _load_baseline(config: dict[str, Any]) -> tuple[Any, Any, Any]:
    key = json.dumps({"asr": config["asr"], "translation": config["translation"]}, sort_keys=True)
    if key in _LOCAL_CACHE:
        return _LOCAL_CACHE[key]
    from faster_whisper import WhisperModel
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    asr = config["asr"]
    model_ref = asr["model"]
    if not Path(model_ref).exists():
        from huggingface_hub import snapshot_download
        repo_id = model_ref if "/" in model_ref else f"Systran/faster-whisper-{model_ref}"
        model_ref = snapshot_download(
            repo_id=repo_id, revision=asr["revision"], allow_patterns=_WHISPER_RUNTIME_FILES,
        )
    whisper = WhisperModel(model_ref, device=asr.get("device", "cpu"), compute_type=asr.get("compute_type", "int8"))
    mt = config["translation"]
    tokenizer = AutoTokenizer.from_pretrained(mt["model"], revision=mt["revision"])
    translator = AutoModelForSeq2SeqLM.from_pretrained(mt["model"], revision=mt["revision"])
    _LOCAL_CACHE[key] = whisper, tokenizer, translator
    return whisper, tokenizer, translator


def _load_local_qwen(config: dict[str, Any]) -> tuple[Any, Any, Any]:
    key = json.dumps({"adapter": "local-qwen", "asr": config["asr"], "translation": config["translation"]}, sort_keys=True)
    if key in _LOCAL_CACHE:
        return _LOCAL_CACHE[key]
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download
    from mlx_lm import load

    asr = config["asr"]
    repo_id = asr["model"] if "/" in asr["model"] else f"Systran/faster-whisper-{asr['model']}"
    whisper_path = snapshot_download(
        repo_id=repo_id, revision=asr["revision"], allow_patterns=_WHISPER_RUNTIME_FILES,
    )
    whisper = WhisperModel(
        whisper_path, device=asr.get("device", "cpu"), compute_type=asr.get("compute_type", "int8"),
    )
    mt = config["translation"]
    model, tokenizer = load(mt["model"], revision=mt["revision"])
    _LOCAL_CACHE[key] = whisper, tokenizer, model
    return whisper, tokenizer, model


def _load_local_translategemma(config: dict[str, Any]) -> tuple[Any, Any, Any]:
    key = json.dumps({"adapter": "local-translategemma", "asr": config["asr"], "translation": config["translation"]}, sort_keys=True)
    if key in _LOCAL_CACHE:
        return _LOCAL_CACHE[key]
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download
    from mlx_lm import load

    asr = config["asr"]
    repo_id = asr["model"] if "/" in asr["model"] else f"Systran/faster-whisper-{asr['model']}"
    whisper_path = snapshot_download(
        repo_id=repo_id, revision=asr["revision"], allow_patterns=_WHISPER_RUNTIME_FILES,
    )
    whisper = WhisperModel(
        whisper_path, device=asr.get("device", "cpu"), compute_type=asr.get("compute_type", "int8"),
    )
    mt = config["translation"]
    model, tokenizer = load(mt["model"], revision=mt["revision"])
    _LOCAL_CACHE[key] = whisper, tokenizer, model
    return whisper, tokenizer, model


def _load_deepl_asr(config: dict[str, Any]) -> Any:
    """Load only the approved local ASR model for the DeepL pipeline."""
    key = json.dumps({"adapter": "deepl", "asr": config["asr"]}, sort_keys=True)
    if key in _LOCAL_CACHE:
        return _LOCAL_CACHE[key][0]
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download

    asr = config["asr"]
    whisper_path = snapshot_download(
        repo_id=asr["model"], revision=asr["revision"], allow_patterns=_WHISPER_RUNTIME_FILES,
    )
    whisper = WhisperModel(
        whisper_path, device=asr.get("device", "cpu"), compute_type=asr.get("compute_type", "int8"),
    )
    _LOCAL_CACHE[key] = (whisper, None, None)
    return whisper


def _mlx_generate(model: Any, tokenizer: Any, prompt: str, max_tokens: int) -> str:
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler

    return generate(
        model, tokenizer, prompt=prompt, max_tokens=max_tokens,
        sampler=make_sampler(temp=0.0), verbose=False,
    )


def _apply_guard(translation_guard: Any, result: dict[str, Any]) -> bool:
    """Return true when a safety decision supplies/withholds translations."""
    if result["uncertainty"]:
        return True
    if translation_guard is None:
        return False
    decision = translation_guard(result["arabic"])
    if decision is None:
        return False
    if not isinstance(decision, dict):
        raise ValueError("guard")
    en, fr = decision.get("en"), decision.get("fr")
    if en is not None and not isinstance(en, str):
        raise ValueError("guard")
    if fr is not None and not isinstance(fr, str):
        raise ValueError("guard")
    uncertainty = decision.get("uncertainty")
    if uncertainty is not None and not isinstance(uncertainty, str):
        raise ValueError("guard")
    result["en"], result["fr"] = en or "", fr or ""
    if uncertainty is not None:
        result["uncertainty"] = uncertainty
    return True


def _baseline(config: dict[str, Any], audio_path: Path, result: dict[str, Any], translation_guard: Any = None) -> None:
    result['_stage'] = 'model_load'
    started = time.perf_counter()
    whisper, tokenizer, translator = _load_baseline(config)
    result["timing_ms"]["model_load"] = round((time.perf_counter() - started) * 1000, 3)
    result['_stage'] = 'asr'
    asr_cfg, mt_cfg = config["asr"], config["translation"]
    started = time.perf_counter()
    segments, info = whisper.transcribe(
        str(audio_path), language="ar", beam_size=asr_cfg.get("beam_size", 1),
        vad_filter=asr_cfg.get("vad_filter", False),
    )
    result["arabic"] = " ".join(segment.text for segment in segments).strip()
    result["timing_ms"]["asr"] = round((time.perf_counter() - started) * 1000, 3)
    probability = getattr(info, "language_probability", None)
    if probability is not None and probability < 0.8:
        result["uncertainty"] = "low_asr_language_confidence"
    if not result["arabic"]:
        raise ValueError("empty transcript")
    result['_stage'] = 'guard'
    if _apply_guard(translation_guard, result):
        return

    targets = {"en": "eng_Latn", "fr": "fra_Latn"}
    tokenizer.src_lang = mt_cfg.get("source_lang", "arb_Arab")
    translation_started = time.perf_counter()
    for language, target in targets.items():
        result['_stage'] = language
        started = time.perf_counter()
        inputs = tokenizer(result["arabic"], return_tensors="pt")
        tokens = translator.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(target),
            max_new_tokens=mt_cfg.get("max_new_tokens", 256),
            num_beams=mt_cfg.get("num_beams", 1),
        )
        result[language] = tokenizer.batch_decode(tokens, skip_special_tokens=True)[0].strip()
        if not result[language]:
            raise ValueError("empty translation")
        result["timing_ms"][language] = round((time.perf_counter() - started) * 1000, 3)
    result["timing_ms"]["translation_wall"] = round((time.perf_counter() - translation_started) * 1000, 3)


def _local_qwen(config: dict[str, Any], audio_path: Path, result: dict[str, Any], translation_guard: Any = None) -> None:
    result["_stage"] = "model_load"
    started = time.perf_counter()
    whisper, tokenizer, model = _load_local_qwen(config)
    result["timing_ms"]["model_load"] = round((time.perf_counter() - started) * 1000, 3)
    result["_stage"] = "asr"
    asr = config["asr"]
    started = time.perf_counter()
    segments, info = whisper.transcribe(
        str(audio_path), language="ar", beam_size=asr.get("beam_size", 1),
        vad_filter=asr.get("vad_filter", False),
    )
    result["arabic"] = " ".join(segment.text for segment in segments).strip()
    result["timing_ms"]["asr"] = round((time.perf_counter() - started) * 1000, 3)
    probability = getattr(info, "language_probability", None)
    if probability is not None and probability < 0.8:
        result["uncertainty"] = "low_asr_language_confidence"
    if not result["arabic"]:
        raise ValueError("empty transcript")
    result["_stage"] = "guard"
    if _apply_guard(translation_guard, result):
        return

    max_tokens = config["translation"].get("max_new_tokens", 256)
    translation_started = time.perf_counter()
    for language in ("en", "fr"):
        result["_stage"] = language
        started = time.perf_counter()
        prompt = tokenizer.apply_chat_template([
            {"role": "system", "content": config["prompts"][language]},
            {"role": "user", "content": result["arabic"]},
        ], add_generation_prompt=True, tokenize=False)
        result[language] = _mlx_generate(model, tokenizer, prompt, max_tokens).strip()
        if not result[language]:
            raise ValueError("empty translation")
        result["timing_ms"][language] = round((time.perf_counter() - started) * 1000, 3)
    result["timing_ms"]["translation_wall"] = round((time.perf_counter() - translation_started) * 1000, 3)


def _local_translategemma(config: dict[str, Any], audio_path: Path, result: dict[str, Any], translation_guard: Any = None) -> None:
    result["_stage"] = "model_load"
    started = time.perf_counter()
    whisper, tokenizer, model = _load_local_translategemma(config)
    result["timing_ms"]["model_load"] = round((time.perf_counter() - started) * 1000, 3)
    result["_stage"] = "asr"
    asr = config["asr"]
    started = time.perf_counter()
    segments, info = whisper.transcribe(
        str(audio_path), language="ar", beam_size=asr.get("beam_size", 1),
        vad_filter=asr.get("vad_filter", False),
    )
    result["arabic"] = " ".join(segment.text for segment in segments).strip()
    result["timing_ms"]["asr"] = round((time.perf_counter() - started) * 1000, 3)
    probability = getattr(info, "language_probability", None)
    if probability is not None and probability < 0.8:
        result["uncertainty"] = "low_asr_language_confidence"
    if not result["arabic"]:
        raise ValueError("empty transcript")
    result["_stage"] = "guard"
    if _apply_guard(translation_guard, result):
        return

    translation_started = time.perf_counter()
    for language in ("en", "fr"):
        result["_stage"] = language
        started = time.perf_counter()
        messages = [{
            "role": "user",
            "content": [{
                "type": "text",
                "source_lang_code": "ar",
                "target_lang_code": language,
                "text": result["arabic"],
            }],
        }]
        # Follow the MLX checkpoint's documented tokenizer call; its template
        # requires one user message with language codes embedded in the content.
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        result[language] = _mlx_generate(
            model, tokenizer, prompt, config["translation"].get("max_new_tokens", 256),
        ).strip()
        if not result[language]:
            raise ValueError("empty translation")
        result["timing_ms"][language] = round((time.perf_counter() - started) * 1000, 3)
    result["timing_ms"]["translation_wall"] = round((time.perf_counter() - translation_started) * 1000, 3)


def _deepl_translation(config: dict[str, Any], arabic: str, language: str) -> str:
    block = config["translation"]
    token = os.environ.get(block["credential_env"])
    if not token:
        raise KeyError("credential")
    from moin_studio.budget import BudgetExceeded, reserve_if_configured

    try:
        reserve_if_configured("deepl_chars", len(arabic))
    except BudgetExceeded:
        raise ProviderFailure("budget_exhausted", "The configured DeepL character budget has been reached.") from None
    target = block[f"target_lang_{language}"]
    payload = json.dumps({
        "text": [arabic],
        "source_lang": block["source_lang"],
        "target_lang": target,
    }).encode("utf-8")
    urls = _deepl_urls(block)
    for number, url in enumerate(urls):
        request = Request(url, data=payload, headers={
            "Authorization": f"DeepL-Auth-Key {token}",
            "Content-Type": "application/json",
            "User-Agent": "Moin/1.0",
        }, method="POST")
        try:
            response = _request_json(request, config["settings"].get("timeout_seconds", 60))
            break
        except HTTPError as error:
            # A key belongs to either API Free or API Pro. When no operator
            # preference exists, one rejected Free request safely discovers a
            # Pro key without asking the user to expose or classify the key.
            if error.code in {401, 403} and number + 1 < len(urls):
                continue
            if error.code in {401, 403}:
                raise ProviderFailure("credential_rejected", "DeepL did not accept this API key. Check that the key is active.") from None
            if error.code == 429:
                raise ProviderFailure("rate_limited", "DeepL is temporarily rate-limiting requests. Try again shortly.", True) from None
            if error.code == 456:
                raise ProviderFailure("quota_exhausted", "The DeepL API character limit has been reached.") from None
            raise ProviderFailure("provider_rejected", "DeepL rejected this translation request.", error.code >= 500) from None
    try:
        text = response["translations"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise ValueError("response") from None
    if not isinstance(text, str) or not text.strip():
        raise ValueError("response")
    return text.strip()


def _deepl(config: dict[str, Any], audio_path: Path, result: dict[str, Any], translation_guard: Any = None) -> None:
    selected_asr = os.environ.get("MOIN_ASR_PROVIDER", "")
    if selected_asr not in {"", "local", "groq"}:
        raise ProviderFailure("provider_configuration", "MOIN_ASR_PROVIDER must be unset, local, or groq.")
    if selected_asr == "groq":
        from moin_studio import groq_asr

        result["_stage"] = "asr"
        started = time.perf_counter()
        try:
            remote = groq_asr.transcribe(
                audio_path,
                timeout_seconds=config["settings"].get("timeout_seconds", 60),
            )
        except groq_asr.GroqASRError as error:
            raise ProviderFailure(error.code, error.message, error.retryable) from None
        result["arabic"] = remote["text"].strip()
        result["timing_ms"]["model_load"] = 0
        result["timing_ms"]["asr"] = round((time.perf_counter() - started) * 1000, 3)
    else:
        result["_stage"] = "model_load"
        started = time.perf_counter()
        whisper = _load_deepl_asr(config)
        result["timing_ms"]["model_load"] = round((time.perf_counter() - started) * 1000, 3)
        result["_stage"] = "asr"
        asr = config["asr"]
        started = time.perf_counter()
        segments, info = whisper.transcribe(
            str(audio_path), language="ar", beam_size=asr.get("beam_size", 5),
            vad_filter=asr.get("vad_filter", False),
        )
        result["arabic"] = " ".join(segment.text for segment in segments).strip()
        result["timing_ms"]["asr"] = round((time.perf_counter() - started) * 1000, 3)
        probability = getattr(info, "language_probability", None)
        if probability is not None and probability < 0.8:
            result["uncertainty"] = "low_asr_language_confidence"
    if not result["arabic"]:
        raise ValueError("empty transcript")
    result["_stage"] = "guard"
    if _apply_guard(translation_guard, result):
        return
    def translate(language: str) -> tuple[str, str, float]:
        started = time.perf_counter()
        text = _deepl_translation(config, result["arabic"], language)
        return language, text, round((time.perf_counter() - started) * 1000, 3)

    # The two HTTPS calls are independent and use immutable inputs. Running
    # them together reduces wall time without changing either translation.
    translation_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="moin-deepl") as pool:
        futures = {language: pool.submit(translate, language) for language in ("en", "fr")}
        for language in ("en", "fr"):
            result["_stage"] = language
            _, text, elapsed = futures[language].result()
            result[language] = text
            result["timing_ms"][language] = elapsed
    result["timing_ms"]["translation_wall"] = round((time.perf_counter() - translation_started) * 1000, 3)


def _url(block: dict[str, Any], default_path: str) -> str:
    return block["base_url"].rstrip("/") + "/" + block.get("endpoint", default_path).lstrip("/")


def _deepl_urls(block: dict[str, Any]) -> list[str]:
    """Return the selected DeepL endpoint, or safely discover the plan once."""
    selected = os.environ.get("DEEPL_API_BASE_URL")
    base = (selected or block["base_url"]).rstrip("/")
    if base not in {_DEEPL_FREE_BASE_URL, _DEEPL_PRO_BASE_URL}:
        raise ProviderFailure("provider_configuration", "DeepL endpoint must be the official API Free or API Pro URL.")
    bases = [base] if selected or base == _DEEPL_PRO_BASE_URL else [base, _DEEPL_PRO_BASE_URL]
    return [item + "/" + block["endpoint"].lstrip("/") for item in bases]


def _authorization(block: dict[str, Any]) -> str:
    token = os.environ.get(block["credential_env"])
    if not token:
        raise KeyError("credential")
    return f"Bearer {token}"


def _request_json(request: Request, timeout: float) -> dict[str, Any]:
    # The bundled Python runtime can lack the macOS trust-store path. Certifi
    # supplies a verified CA bundle; we never disable certificate verification.
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=timeout, context=context) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("response")
    return value


def _remote_asr(config: dict[str, Any], audio_path: Path) -> str:
    block = config["asr"]
    boundary = "moin-" + uuid.uuid4().hex
    audio = audio_path.read_bytes()
    content_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
    fields = [("model", block["model"]), ("language", "ar")]
    body = bytearray()
    for name, value in fields:
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{audio_path.name}\"\r\nContent-Type: {content_type}\r\n\r\n".encode())
    body.extend(audio)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    request = Request(_url(block, "/audio/transcriptions"), data=bytes(body), headers={
        "Authorization": _authorization(block), "Content-Type": f"multipart/form-data; boundary={boundary}",
    }, method="POST")
    payload = _request_json(request, config["settings"].get("timeout_seconds", 60))
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("response")
    return text.strip()


def _remote_translation(config: dict[str, Any], arabic: str, language: str) -> str:
    block = config["translation"]
    payload = json.dumps({
        "model": block["model"],
        "messages": [
            {"role": "system", "content": config["prompts"][language]},
            {"role": "user", "content": arabic},
        ],
        "temperature": 0,
    }).encode()
    request = Request(_url(block, "/chat/completions"), data=payload, headers={
        "Authorization": _authorization(block), "Content-Type": "application/json",
    }, method="POST")
    response = _request_json(request, config["settings"].get("timeout_seconds", 60))
    try:
        text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ValueError("response") from None
    if not isinstance(text, str) or not text.strip():
        raise ValueError("response")
    return text.strip()


def process(config: dict[str, Any], audio_path: Path, *, translation_guard: Any = None) -> dict[str, Any]:
    """Process audio and always return the normalized candidate result shape."""
    overall = time.perf_counter()
    result = _empty_result(overall)
    try:
        validate_config(config)
    except (TypeError, ValueError):
        result["failure"] = _failure("config", "invalid_config", "Candidate configuration is invalid.")
        return result
    path = Path(audio_path)
    if not path.is_file():
        result["failure"] = _failure("input", "audio_unavailable", "Canonical audio is unavailable.")
        return result

    stage = "asr"
    try:
        if config["adapter"] == "baseline":
            _baseline(config, path, result, translation_guard)
        elif config["adapter"] == "local-qwen":
            _local_qwen(config, path, result, translation_guard)
        elif config["adapter"] == "local-translategemma":
            _local_translategemma(config, path, result, translation_guard)
        elif config["adapter"] == "deepl":
            _deepl(config, path, result, translation_guard)
        else:
            started = time.perf_counter()
            result["arabic"] = _remote_asr(config, path)
            result["timing_ms"]["asr"] = round((time.perf_counter() - started) * 1000, 3)
            stage = "guard"
            if _apply_guard(translation_guard, result):
                result["timing_ms"]["total"] = round((time.perf_counter() - overall) * 1000, 3)
                return result
            def translate(language: str) -> tuple[str, str, float]:
                started = time.perf_counter()
                text = _remote_translation(config, result["arabic"], language)
                return language, text, round((time.perf_counter() - started) * 1000, 3)

            translation_started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="moin-translation") as pool:
                futures = {language: pool.submit(translate, language) for language in ("en", "fr")}
                for language in ("en", "fr"):
                    stage = language
                    _, text, elapsed = futures[language].result()
                    result[language] = text
                    result["timing_ms"][language] = elapsed
            result["timing_ms"]["translation_wall"] = round((time.perf_counter() - translation_started) * 1000, 3)
    except ProviderFailure as error:
        result["failure"] = _failure(result.get("_stage", stage), error.code, error.message, error.retryable)
    except KeyError:
        result["failure"] = _failure(result.get("_stage", stage), "credential_unavailable", "Provider credential is unavailable.")
    except (OSError, TimeoutError):
        result["failure"] = _failure(result.get("_stage", stage), "provider_unavailable", "Candidate provider is unavailable.", True)
    except Exception:
        result["failure"] = _failure(result.get("_stage", stage), "candidate_failed", "Candidate processing failed.")
    result.pop("_stage", None)
    result["timing_ms"]["total"] = round((time.perf_counter() - overall) * 1000, 3)
    return result
