"""Operator CLI: python -m moin_benchmark (or ./benchmark)."""
import argparse
import json
import sys
from pathlib import Path
from .core import BenchmarkError, exclusive, validate_corpus
from .engine import Benchmark


def parser():
    p = argparse.ArgumentParser(prog='benchmark', description='Moin V1 blind text benchmark')
    p.add_argument('--corpus', type=Path, default=Path('benchmark-data'))
    p.add_argument('--workspace', type=Path, default=Path('benchmark-runs'))
    sub = p.add_subparsers(dest='command', required=True)
    corpus = sub.add_parser('corpus').add_subparsers(dest='action', required=True)
    c = corpus.add_parser('validate')
    c.add_argument('--split', choices=['development','final'], required=True)
    sub.add_parser('protocol')
    sub.add_parser('finalize-interrupted')
    c = sub.add_parser('candidates').add_subparsers(dest='action', required=True).add_parser('lock')
    c.add_argument('--file', type=Path, required=True)
    c = sub.add_parser('run')
    c.add_argument('--split', choices=['development','final'], default='development')
    c.add_argument('--candidate', required=True)
    c.add_argument('--clip')
    c = sub.add_parser('review-package').add_subparsers(dest='action', required=True).add_parser('create')
    c.add_argument('--split', choices=['development','final'], required=True)
    c.add_argument('--out', type=Path, required=True)
    c = sub.add_parser('review').add_subparsers(dest='action', required=True).add_parser('submit')
    c.add_argument('--split', choices=['development','final'], required=True)
    c.add_argument('--file', type=Path, required=True)
    c.add_argument('--reviewer', required=True)
    c = sub.add_parser('report')
    c.add_argument('split', choices=['development','final'])
    c.add_argument('--out', type=Path)
    composition = sub.add_parser('composition').add_subparsers(dest='action', required=True)
    c = composition.add_parser('select')
    c.add_argument('--candidate', required=True)
    c.add_argument('--renderings', type=Path, required=True)
    c = composition.add_parser('freeze')
    c.add_argument('--candidate', choices=['moin'], default='moin')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    b = Benchmark(args.corpus, args.workspace)
    try:
        with exclusive(args.workspace):
            if args.command == 'protocol':
                result = b.protocol()
            elif args.command == 'finalize-interrupted':
                result = b.finalize_interrupted()
            elif args.command == 'corpus':
                if args.split == 'final':
                    b.frozen()
                clips = validate_corpus(args.corpus,args.split,final_allowed=args.split == 'final')
                result = {'valid':True,'split':args.split,'clips':len(clips),'speakers':len({c['speaker'] for c in clips})}
            elif args.command == 'candidates':
                result = b.lock(args.file)
            elif args.command == 'run':
                result = b.run(args.split,args.candidate,args.clip)
            elif args.command == 'review-package':
                result = b.package(args.split,args.out)
            elif args.command == 'review':
                result = b.submit(args.split,args.file,args.reviewer)
            elif args.command == 'report':
                result = b.report(args.split)
                if args.out:
                    from .core import write_new
                    if args.out.suffix.lower() == '.md':
                        from .reporting import markdown
                        args.out.parent.mkdir(parents=True, exist_ok=True)
                        with args.out.open('x') as stream:
                            stream.write(markdown(result))
                    else:
                        write_new(args.out,result)
            elif args.action == 'select':
                result = b.select(args.candidate,args.renderings)
            else:
                result = b.freeze()
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (BenchmarkError, ValueError, KeyError, TypeError, OSError):
        # Only domain errors are safe to show; provider exceptions never reach here.
        exc = sys.exc_info()[1]
        message = str(exc) if isinstance(exc, BenchmarkError) else 'Invalid configuration or input; check the documented schema and file permissions'
        print(json.dumps({'error': {'code':'benchmark_rejected','message':message}}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
