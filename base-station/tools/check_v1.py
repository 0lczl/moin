"""Read-only readiness audit; never reveals blind identities or assigns labels."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from moin_benchmark.core import BenchmarkError, digest, read, require, validate_corpus
from moin_benchmark.engine import Benchmark, LABELS


def check(corpus, workspace, package):
    b = Benchmark(corpus, workspace)
    clips = validate_corpus(corpus, 'development')
    results = b.results('development')  # validates pinned code/runtime/config/corpus
    mapping = read(workspace / 'development-review-map.json')
    exported = read(package / 'review.json')
    expected = mapping['package']
    require(exported.get('protocol') == expected['protocol'], 'Review protocol changed')
    rows = exported.get('items', [])
    expected_rows = {r['id']: r for r in expected['items']}
    require(len(rows) == len(expected_rows), 'Review count changed')
    seen = set()
    index = {(r['candidate'], r['clip_id']): r for r in results}
    clip_index = {c['id']: c for c in clips}
    for row in rows:
        key = row.get('id')
        require(key in expected_rows and key not in seen, 'Unknown or duplicate item')
        seen.add(key)
        content = lambda r: {k: v for k, v in r.items() if k not in ('label', 'comment')}
        require(content(row) == content(expected_rows[key]), 'Review content changed')
        require(row.get('label') is None or row['label'] in LABELS, 'Invalid label')
        require(isinstance(row.get('comment'), str), 'Invalid comment')
        require(not row['unavailable'] or row['label'] != 'faithful', 'Unavailable output cannot pass')
        meta = mapping['items'][key]
        require(digest(index[(meta['candidate'], meta['clip_id'])]) == meta['result_identity'], 'Recorded output changed')
        audio = (package / row['audio']).resolve()
        require(audio.is_relative_to(package.resolve()), 'Audio escapes review package')
        require(hashlib.sha256(audio.read_bytes()).hexdigest() == clip_index[meta['clip_id']]['sha256'], 'Review audio changed')
    submitted = (workspace / 'development-reviews.json').exists()
    if submitted:
        b.report('development')  # validate without revealing names in this audit
    return {'integrity': 'passed', 'clips': len(clips), 'recorded_runs': len(results),
            'execution_failures': sum(bool(r['failure']) for r in results),
            'judgements_required': len(rows), 'labels_in_exported_file': sum(r['label'] is not None for r in rows),
            'human_review_submitted': submitted,
            'next_step': 'Read the meaning report and select the safety composition.' if submitted else
                         'Complete and submit the human meaning review. Execution success does not determine a winner.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', type=Path, default=Path('benchmark-data'))
    p.add_argument('--workspace', type=Path, default=Path('benchmark-runs/nine-local-v1'))
    p.add_argument('--package', type=Path, default=Path('benchmark-review/nine-local-v1'))
    a = p.parse_args(argv)
    try:
        result = check(a.corpus, a.workspace, a.package)
    except (BenchmarkError, ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'integrity': 'failed', 'error': str(error) if isinstance(error, BenchmarkError) else 'Missing or malformed evidence'}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['human_review_submitted'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
