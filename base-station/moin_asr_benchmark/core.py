"""Deterministic identities and Arabic ASR scoring."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


class AsrBenchmarkError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AsrBenchmarkError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise AsrBenchmarkError(f"Cannot read valid JSON: {Path(path)}") from None


def write_new(path: Path, value) -> None:
    """Atomically create an immutable JSON artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise AsrBenchmarkError(f"Immutable artifact exists: {path}") from None
    finally:
        Path(temporary).unlink(missing_ok=True)


_ARABIC_MARK = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_ALEF_VARIANTS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})


def normalize_arabic(text: str, *, alef: bool = False) -> str:
    """NFKC, remove vocalization/tatweel/punctuation, and collapse whitespace.

    The optional diagnostic changes only alef variants. It does not stem words,
    remove repetitions, or merge ya/ta-marbuta/hamza-bearing letters.
    """
    require(isinstance(text, str), "Text must be a string")
    text = unicodedata.normalize("NFKC", text)
    text = _ARABIC_MARK.sub("", text).replace("ـ", "")
    text = "".join(" " if unicodedata.category(char).startswith("P") else char for char in text)
    if alef:
        text = text.translate(_ALEF_VARIANTS)
    return " ".join(text.split())


def _best(options):
    # Deterministic priority after total cost: substitution, deletion, insertion.
    return min(options, key=lambda item: (item[0], item[1], item[2], item[3]))


def edit_counts(reference, hypothesis) -> dict[str, int | float | None]:
    """Levenshtein counts with deterministic alignment and explicit denominator."""
    reference, hypothesis = list(reference), list(hypothesis)
    # Each cell is (cost, substitutions, deletions, insertions).
    row = [(j, 0, 0, j) for j in range(len(hypothesis) + 1)]
    for i, ref in enumerate(reference, start=1):
        next_row = [(i, 0, i, 0)]
        for j, hyp in enumerate(hypothesis, start=1):
            if ref == hyp:
                next_row.append(row[j - 1])
                continue
            diagonal = row[j - 1]
            above = row[j]
            left = next_row[j - 1]
            next_row.append(_best([
                (diagonal[0] + 1, diagonal[1] + 1, diagonal[2], diagonal[3]),
                (above[0] + 1, above[1], above[2] + 1, above[3]),
                (left[0] + 1, left[1], left[2], left[3] + 1),
            ]))
        row = next_row
    cost, substitutions, deletions, insertions = row[-1]
    denominator = len(reference)
    return {
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "errors": cost,
        "reference_units": denominator,
        "rate": cost / denominator if denominator else None,
    }


def score_pair(reference: str, hypothesis: str, *, alef: bool = False) -> dict:
    normalized_reference = normalize_arabic(reference, alef=alef)
    normalized_hypothesis = normalize_arabic(hypothesis, alef=alef)
    words = edit_counts(normalized_reference.split(), normalized_hypothesis.split())
    characters = edit_counts(normalized_reference.replace(" ", ""), normalized_hypothesis.replace(" ", ""))
    return {
        "normalization": "alef" if alef else "strict",
        "normalized_reference": normalized_reference,
        "normalized_hypothesis": normalized_hypothesis,
        "wer": words,
        "cer": characters,
    }


def add_counts(items: list[dict], key: str) -> dict:
    counts = {name: sum(item[key][name] for item in items) for name in (
        "substitutions", "deletions", "insertions", "errors", "reference_units"
    )}
    denominator = counts["reference_units"]
    counts["rate"] = counts["errors"] / denominator if denominator else None
    return counts
