"""Direct text-to-text candidate evaluation; deliberately does not read audio."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from moin_benchmark.core import BenchmarkError, digest, exclusive, identifier, read, registry, secret_free, write_new
from moin_benchmark.adapters import runtime_identity

MAX_CHARACTERS = 50_000
TARGETS = {"en": "en", "fr": "fr"}
JUDGMENTS = ("faithful", "partly_wrong", "serious_meaning_error")
GOOGLE_ENDPOINT = "https://translation.googleapis.com/v3/projects/{project}/locations/global:translateText"
GOOGLE_MODEL = "projects/{project}/locations/global/models/general/nmt"
GOOGLE_SETTINGS = {"project_env": "MOIN_GOOGLE_CLOUD_PROJECT", "timeout_seconds": 60,
                   "source_language": "ar", "target_languages": ["en", "fr"],
                   "max_pilot_characters": MAX_CHARACTERS}


def validate_candidate(item: dict) -> None:
    if not isinstance(item, dict) or set(item) != {"id", "name", "adapter", "model", "revision", "settings"}:
        raise BenchmarkError("Invalid translation-only candidate schema")
    identifier(item["id"])
    if not isinstance(item["name"], str) or not item["name"].strip():
        raise BenchmarkError("Candidate name is required")
    if not isinstance(item["adapter"], str) or item["adapter"] not in {"google-cloud-nmt", "local-nllb", "local-qwen", "local-translategemma"}:
        raise BenchmarkError(f"Unsupported translation adapter: {item['adapter']}")
    if not isinstance(item["model"], str) or not item["model"] or not isinstance(item["revision"], str) or not item["revision"]:
        raise BenchmarkError("Candidate model and revision are required")
    if not isinstance(item["settings"], dict):
        raise BenchmarkError("Candidate settings must be an object")
    if item["adapter"] == "google-cloud-nmt":
        if item["model"] != GOOGLE_MODEL or item["revision"] != "general/nmt":
            raise BenchmarkError("Google candidate must use the general NMT model")
        settings = item["settings"]
        if set(settings) != set(GOOGLE_SETTINGS):
            raise BenchmarkError("Google candidate settings must define project, timeout, languages, and pilot cap")
        if not isinstance(settings["project_env"], str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", settings["project_env"]):
            raise BenchmarkError("Invalid Google project environment variable name")
        timeout = settings["timeout_seconds"]
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise BenchmarkError("Google timeout must be between 0 and 120 seconds")
        if settings["source_language"] != "ar" or settings["target_languages"] != ["en", "fr"]:
            raise BenchmarkError("Google pilot languages must be Arabic to English and French")
        if type(settings["max_pilot_characters"]) is not int or settings["max_pilot_characters"] != MAX_CHARACTERS:
            raise BenchmarkError("Google pilot cap must be 50,000 characters")
    elif item["settings"] != {} or not re.fullmatch(r"[0-9a-f]{40}", item["revision"]):
        raise BenchmarkError("Local candidates need empty settings and a pinned model revision")
    secret_free(item)


def load_candidates(path: Path) -> dict[str, dict]:
    candidates = read(path)
    if not isinstance(candidates, list) or not candidates:
        raise BenchmarkError("Translation candidates must be a non-empty array")
    result = {}
    for item in candidates:
        validate_candidate(item)
        cid = item["id"]
        if cid in result:
            raise BenchmarkError("Candidate IDs must be unique non-empty strings")
        result[cid] = item
    return result


def frozen_texts(corpus_dir: Path) -> tuple[list[dict], str, str]:
    """Read verified development transcript text only; never opens corpus audio."""
    clips = registry(corpus_dir)
    selected = []
    for clip in clips:
        if clip["split"] != "development":
            continue
        transcript = clip["transcript"]
        if transcript.get("state") != "verified" or not isinstance(transcript.get("text"), str):
            raise BenchmarkError(f"{clip['id']}: reviewed Arabic transcript required")
        selected.append({"id": clip["id"], "arabic": transcript["text"]})
    if len(selected) != 9:
        raise BenchmarkError("The translation pilot requires exactly nine reviewed development transcripts")
    corpus_hash = hashlib.sha256((corpus_dir / "corpus.json").read_bytes()).hexdigest()
    return selected, corpus_hash, digest(selected)


def _google_token() -> str:
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleRequest
    except ImportError as exc:
        raise RuntimeError("Install google-auth[requests] to use the Google Cloud NMT candidate") from exc
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-translation"])
    credentials.refresh(GoogleRequest())
    if not credentials.token:
        raise RuntimeError("Application Default Credentials did not provide an access token")
    return credentials.token


def _google_translate(candidate: dict, text: str, language: str, *, token_provider=_google_token, post=None) -> str:
    validate_candidate(candidate)
    if language not in TARGETS or not isinstance(text, str) or not text.strip():
        raise ValueError("Non-empty Arabic text and en or fr target required")
    if len(text) > MAX_CHARACTERS:
        raise ValueError(f"Input is {len(text)} characters; Moin pilot limit is {MAX_CHARACTERS:,}")
    project_env = candidate["settings"]["project_env"]
    project = os.environ.get(project_env, "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,62}", project):
        raise RuntimeError(f"Set {project_env} on the server and configure Application Default Credentials")
    token = token_provider()
    endpoint = GOOGLE_ENDPOINT.format(project=project)
    payload = {
        "contents": [text], "mimeType": "text/plain", "sourceLanguageCode": "ar",
        "targetLanguageCode": TARGETS[language],
        "model": GOOGLE_MODEL.format(project=project),
    }
    request = Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode(), headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8",
        "x-goog-user-project": project,
    }, method="POST")
    if post is None:
        with urlopen(request, timeout=candidate["settings"]["timeout_seconds"]) as response:
            body = response.read()
    else:
        body = post(request, candidate["settings"]["timeout_seconds"])
    try:
        decoded = json.loads(body)
    except (TypeError, ValueError):
        raise RuntimeError("Google Cloud response was not valid JSON") from None
    if not isinstance(decoded, dict):
        raise RuntimeError("Google Cloud response was not an object")
    translations = decoded.get("translations")
    if (not isinstance(translations, list) or len(translations) != 1 or
            not isinstance(translations[0], dict) or
            not isinstance(translations[0].get("translatedText"), str) or
            not translations[0]["translatedText"].strip()):
        raise RuntimeError("Google Cloud response did not contain one non-empty translatedText")
    return translations[0]["translatedText"]


def _local_translate(candidate: dict, text: str, language: str) -> str:
    adapter = candidate["adapter"]
    model_id, revision = candidate["model"], candidate["revision"]
    if adapter == "local-nllb":
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from moin_benchmark.adapters import _LOCAL_CACHE
        key = json.dumps({"translation_only": candidate}, sort_keys=True)
        if key not in _LOCAL_CACHE:
            tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, src_lang="arb_Arab")
            model = AutoModelForSeq2SeqLM.from_pretrained(model_id, revision=revision)
            _LOCAL_CACHE[key] = (tokenizer, model)
        tokenizer, model = _LOCAL_CACHE[key]
        import torch
        target_id = tokenizer.convert_tokens_to_ids("eng_Latn" if language == "en" else "fra_Latn")
        encoded = tokenizer(text, return_tensors="pt", truncation=False)
        return tokenizer.batch_decode(model.generate(**encoded, forced_bos_token_id=target_id, max_new_tokens=256), skip_special_tokens=True)[0]
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler
    from moin_benchmark.adapters import _LOCAL_CACHE
    key = json.dumps({"translation_only": candidate}, sort_keys=True)
    if key not in _LOCAL_CACHE:
        model, tokenizer = load(model_id, revision=revision)
        if adapter == "local-translategemma":
            tokenizer.add_eos_token("<end_of_turn>")
        _LOCAL_CACHE[key] = (model, tokenizer)
    model, tokenizer = _LOCAL_CACHE[key]
    if adapter == "local-translategemma":
        content = [{"type": "text", "source_lang_code": "ar", "target_lang_code": language, "text": text}]
        messages = [{"role": "user", "content": content}]
    else:
        instruction = ("Translate the Arabic text faithfully into English. Preserve its meaning and tone. Return only the English translation, with no explanation or commentary." if language == "en"
                      else "Traduisez fidèlement le texte arabe en français, en préservant son sens et son ton. Répondez uniquement avec la traduction française, sans explication ni commentaire.")
        messages = [{"role": "system", "content": instruction}, {"role": "user", "content": text}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=1024, sampler=make_sampler(temp=0.0), verbose=False).strip()


def translate_text(candidate: dict, text: str, language: str) -> str:
    """Translate one frozen Arabic string; network use is limited to explicit Google runs."""
    validate_candidate(candidate)
    if language not in TARGETS:
        raise ValueError("language must be en or fr")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Arabic source text is required")
    if candidate["adapter"] == "google-cloud-nmt":
        return _google_translate(candidate, text, language)
    return _local_translate(candidate, text, language)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def lock_workspace(workspace: Path, candidate_ids: list[str], candidates_path: Path) -> dict:
    candidates = load_candidates(candidates_path)
    if len(candidate_ids) < 2 or len(set(candidate_ids)) != len(candidate_ids):
        raise BenchmarkError("Lock at least two unique candidates for a comparison")
    unknown = set(candidate_ids) - candidates.keys()
    if unknown:
        raise BenchmarkError("Unknown candidate IDs: " + ", ".join(sorted(unknown)))
    records = [candidates[cid] for cid in candidate_ids]
    lock = {"created_at": _timestamp(), "candidate_file_sha256": digest(candidates), "candidates": records}
    workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_new(workspace / "lock.json", lock)
    return lock


def run_candidate(workspace: Path, candidate_id: str, corpus_dir: Path) -> Path:
    """Save each attempt before sending it, so a rerun cannot silently bill twice."""
    lock = read(workspace / "lock.json")
    matches = [item for item in lock["candidates"] if item["id"] == candidate_id]
    if len(matches) != 1:
        raise BenchmarkError("Candidate is not in this immutable comparison lock")
    candidate = matches[0]
    validate_candidate(candidate)
    clips, corpus_hash, source_hash = frozen_texts(corpus_dir)
    planned_characters = sum(len(clip["arabic"]) for clip in clips) * len(TARGETS)
    path = workspace / "runs" / f"{candidate_id}.json"
    with exclusive(workspace):
        if path.exists():
            previous = read(path)
            if (previous.get("source_texts_sha256") != source_hash or
                    previous.get("candidate") != candidate):
                raise BenchmarkError("Completed run belongs to a different source or candidate lock")
            return path
        if candidate["adapter"] == "google-cloud-nmt" and planned_characters > MAX_CHARACTERS:
            denial = workspace / "runs" / f"{candidate_id}-budget-denial.json"
            if not denial.exists():
                write_new(denial, {"schema": "moin-translation-budget-denial-v1", "candidate_id": candidate_id,
                                   "source_texts_sha256": source_hash,
                                   "planned_source_characters": planned_characters, "limit": MAX_CHARACTERS,
                                   "reason": "Pilot cumulative source-character cap exceeded; no requests made"})
            raise BenchmarkError(
                f"Pilot would submit {planned_characters:,} cumulative source characters across English and French; "
                f"limit is {MAX_CHARACTERS:,}. No requests were made."
            )
        if candidate["adapter"] == "google-cloud-nmt":
            project = os.environ.get(candidate["settings"]["project_env"], "").strip()
            if not re.fullmatch(r"[a-z][a-z0-9-]{4,62}", project):
                raise BenchmarkError(f"Set {candidate['settings']['project_env']} before running Google NMT")

        progress = workspace / "attempts" / candidate_id
        expected_stems = {f"{clip['id']}-{language}" for clip in clips for language in TARGETS}
        for prior in progress.glob("*.intent.json"):
            stem = prior.name.removesuffix(".intent.json")
            if stem not in expected_stems:
                raise BenchmarkError("Saved attempt belongs to a different Arabic source set")
        # Check all prior attempts before a new request. A changed source or an
        # unresolved in-flight attempt must not trigger any provider call.
        for clip in clips:
            for language in TARGETS:
                stem = f"{clip['id']}-{language}"
                intent_path, result_path = progress / f"{stem}.intent.json", progress / f"{stem}.result.json"
                if intent_path.exists():
                    intent = read(intent_path)
                    if (intent.get("source_texts_sha256") != source_hash or
                            intent.get("candidate_sha256") != digest(candidate) or
                            intent.get("source_characters") != len(clip["arabic"])):
                        raise BenchmarkError("Saved attempt belongs to a different source or candidate lock")
                    if not result_path.exists():
                        raise BenchmarkError(f"Unresolved attempt {stem}; inspect provider usage before any new request")
                    saved_result = read(result_path)
                    if saved_result.get("status") != "ok":
                        raise BenchmarkError(f"Saved failed result {stem}; inspect it before a new comparison")
                    if not isinstance(saved_result.get("text"), str) or not saved_result["text"].strip():
                        raise BenchmarkError(f"Saved result {stem} has no translation")
                elif result_path.exists():
                    raise BenchmarkError(f"Result {stem} has no matching attempt record")

        if candidate["adapter"] == "google-cloud-nmt" and not any(progress.glob("*.intent.json")):
            try:
                _google_token()
            except Exception:
                raise BenchmarkError("Google Application Default Credentials are unavailable; no translation request was made") from None

        outputs = []
        for clip in clips:
            row = {"clip_id": clip["id"], "source_arabic": clip["arabic"], "translations": {}}
            for language in TARGETS:
                stem = f"{clip['id']}-{language}"
                intent_path, result_path = progress / f"{stem}.intent.json", progress / f"{stem}.result.json"
                if result_path.exists():
                    result = read(result_path)
                else:
                    write_new(intent_path, {"schema": "moin-translation-attempt-v1", "created_at": _timestamp(),
                                            "candidate_id": candidate_id, "candidate_sha256": digest(candidate),
                                            "source_texts_sha256": source_hash, "clip_id": clip["id"],
                                            "target_language": language, "source_characters": len(clip["arabic"])})
                    started = time.perf_counter()
                    try:
                        translated = translate_text(candidate, clip["arabic"], language)
                        if not isinstance(translated, str) or not translated.strip():
                            raise RuntimeError("Translation result was empty")
                        result = {"status": "ok", "text": translated,
                                  "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)}
                    except Exception as exc:
                        # Never persist exception messages: they may contain request details.
                        result = {"status": "failed", "text": "", "error": type(exc).__name__,
                                  "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)}
                    write_new(result_path, result)
                if result.get("status") != "ok":
                    raise BenchmarkError(f"Saved failed result {stem}; inspect it before a new comparison")
                row["translations"][language] = {**result, "source_characters": len(clip["arabic"]),
                                                  "source_language": "ar", "target_language": language}
            outputs.append(row)
        record = {"schema": "moin-translation-run-v1", "created_at": _timestamp(), "candidate": candidate,
                  "runtime": runtime_identity(), "source_corpus_sha256": corpus_hash,
                  "source_texts_sha256": source_hash, "planned_source_characters": planned_characters,
                  "attempted_source_characters": sum(len(clip["arabic"]) for clip in clips) * len(TARGETS),
                  "clips": outputs}
        secret_free(record)
        write_new(path, record)
        return path


def create_review_package(workspace: Path, out: Path, *, seed: int | None = None) -> Path:
    lock = read(workspace / "lock.json")
    run_data = {}
    for candidate in lock["candidates"]:
        path = workspace / "runs" / f"{candidate['id']}.json"
        if not path.exists():
            raise BenchmarkError(f"Missing run for {candidate['id']}")
        run_data[candidate["id"]] = read(path)
        if run_data[candidate["id"]].get("candidate") != candidate:
            raise BenchmarkError("Run does not match the locked candidate")
    if len({run["source_texts_sha256"] for run in run_data.values()}) != 1:
        raise BenchmarkError("Cannot compare runs from different Arabic source texts")
    clips_by_id = [{row["clip_id"]: row for row in run_data[cid]["clips"]} for cid in run_data]
    ids = [row["clip_id"] for row in next(iter(run_data.values()))["clips"]]
    if any(set(rows) != set(ids) for rows in clips_by_id):
        raise BenchmarkError("Runs contain different clips")
    rng = random.Random(seed)
    export = {"schema": "moin-text-review-v1", "instructions": "For each anonymous output, judge whether it preserves the Arabic meaning. Use one of allowed_judgments. Pay special attention to Islamic terms in context, Qur'an and hadith quotations or attribution, and whether a literal rendering changes the intended religious meaning. Changed negation or obligation, false attribution, and serious additions or omissions are serious meaning errors. Add a concise comment when helpful.",
              "allowed_judgments": list(JUDGMENTS), "clips": []}
    mapping = {"created_at": _timestamp(), "labels": {}}
    for cid in ids:
        clip_refs = [rows[cid] for rows in clips_by_id]
        for language in ("en", "fr"):
            systems = []
            for index, row in enumerate(clip_refs):
                translation = row["translations"][language]
                if translation.get("status") != "ok" or not isinstance(translation.get("text"), str) or not translation["text"].strip():
                    raise BenchmarkError("Failed or empty translation cannot enter the review package")
                if row["source_arabic"] != clip_refs[0]["source_arabic"]:
                    raise BenchmarkError("Runs contain different Arabic source text")
                systems.append({"candidate_id": list(run_data)[index], "text": translation["text"], "status": translation["status"]})
            rng.shuffle(systems)
            anonymous = []
            for system in systems:
                label = f"System {len(anonymous) + 1}"
                anonymous.append({"label": label, "translation": system["text"], "status": system["status"], "judgment": "", "comment": ""})
                mapping["labels"][f"{cid}:{language}:{label}"] = system["candidate_id"]
            export["clips"].append({"clip_id": cid, "language": language, "source_arabic": clip_refs[0]["source_arabic"], "systems": anonymous})
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_new(out / "review.json", export)
    private_dir = workspace / "private"
    private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_new(private_dir / f"review-map-{digest(export)[:12]}.json", mapping)
    return out / "review.json"


def check_review(path: Path) -> dict[str, dict[str, int]]:
    """Validate a filled anonymous review without reading the private identity map."""
    review = read(path)
    if review.get("schema") != "moin-text-review-v1" or review.get("allowed_judgments") != list(JUDGMENTS):
        raise BenchmarkError("Unknown translation review schema or rubric")
    counts = {language: {judgment: 0 for judgment in JUDGMENTS} for language in TARGETS}
    for item in review.get("clips", []):
        language = item.get("language")
        if language not in TARGETS or not isinstance(item.get("systems"), list) or not item["systems"]:
            raise BenchmarkError("Invalid review item")
        for system in item["systems"]:
            judgment = system.get("judgment")
            if judgment not in JUDGMENTS or not isinstance(system.get("comment"), str):
                raise BenchmarkError(f"Incomplete or invalid judgment for {item.get('clip_id')} {language} {system.get('label')}")
            counts[language][judgment] += 1
    if not review.get("clips") or any(sum(counts[language].values()) == 0 for language in TARGETS):
        raise BenchmarkError("Review must contain completed English and French judgments")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Text-only benchmark over the nine frozen reviewed Arabic transcripts")
    parser.add_argument("--corpus", type=Path, default=Path("benchmark-data"))
    parser.add_argument("--candidates", type=Path, default=Path("benchmark-data/translation-candidates.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    lock = sub.add_parser("lock"); lock.add_argument("--workspace", type=Path, required=True); lock.add_argument("--candidate", action="append", required=True)
    run = sub.add_parser("run"); run.add_argument("--workspace", type=Path, required=True); run.add_argument("--candidate", required=True)
    review = sub.add_parser("review-package"); review.add_argument("--workspace", type=Path, required=True); review.add_argument("--out", type=Path, required=True); review.add_argument("--seed", type=int)
    check = sub.add_parser("review-check"); check.add_argument("--file", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for candidate in load_candidates(args.candidates).values():
                print(f"{candidate['id']}: {candidate['name']} ({candidate['adapter']})")
        elif args.command == "lock":
            lock_workspace(args.workspace, args.candidate, args.candidates)
            print(f"Locked candidates in {args.workspace / 'lock.json'}")
        elif args.command == "run":
            print(run_candidate(args.workspace, args.candidate, args.corpus))
        elif args.command == "review-check":
            print(json.dumps(check_review(args.file), indent=2))
        else:
            print(create_review_package(args.workspace, args.out, seed=args.seed))
    except (BenchmarkError, OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
