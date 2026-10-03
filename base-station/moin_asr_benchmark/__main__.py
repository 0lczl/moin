from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import AsrBenchmarkError
from .runner import AsrBenchmark


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Moin Arabic ASR benchmark")
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    lock = sub.add_parser("lock")
    lock.add_argument("--candidates", type=Path, required=True)
    lock.add_argument("--protocol", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--candidate", required=True)
    run.add_argument("--clip")
    sub.add_parser("report")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    benchmark = AsrBenchmark(args.corpus, args.workspace)
    try:
        if args.command == "lock":
            result = benchmark.lock(args.candidates, args.protocol)
            output = {"locked": list(result["candidates"]), "corpus_identity": result["corpus_identity"]}
        elif args.command == "run":
            output = benchmark.run(args.candidate, args.clip)
        else:
            report = benchmark.report()
            output = {
                "selection_status": report["selection_status"],
                "candidates": [{
                    "id": item["id"],
                    "candidate_status": item["candidate_status"],
                    "selection_eligible": item["selection_eligible"],
                    "wer": item["strict"]["wer"]["rate"],
                    "cer": item["strict"]["cer"]["rate"],
                    "scored_words": item["coverage"]["scored_reference_words"],
                    "failures": len(item["failures"]),
                    "elapsed_ms": item["elapsed_ms"],
                    "attempt_wall_ms": item["attempt_wall_ms"],
                } for item in report["candidates"]],
            }
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except AsrBenchmarkError as error:
        print(f"error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
