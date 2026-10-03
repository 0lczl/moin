#!/usr/bin/env python3
"""Make a minimal, secret-free release bundle from this local workspace.

The Qur'an rendering registry is intentionally Git-ignored. It is included in
this explicitly built bundle so a new host does not silently lose the safety
gate. The manifest records every packaged file's SHA-256 digest.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'Dockerfile.hosted', 'compose.hosted.yaml', 'deploy/Caddyfile',
    'deploy/hosted.env.example', 'deploy/README.md',
    'base-station/requirements-hosted.txt',
    'base-station/benchmark-data/local-comparison.json',
    'base-station/benchmark-data/rendering-research.md',
    'base-station/benchmark-data/staging-renderings/renderings.quranenc.json',
]
DIRECTORIES = [
    'brand', 'base-station/moin_benchmark', 'base-station/moin_machine',
    'base-station/moin_studio', 'base-station/moin_haramain', 'base-station/tools',
]


def selected_files():
    result = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        result.extend(path for path in (ROOT / directory).rglob('*') if path.is_file()
                      and '__pycache__' not in path.parts
                      and path.suffix not in {'.pyc', '.pyo'}
                      and path.name != '.DS_Store')
    missing = [str(path.relative_to(ROOT)) for path in result if not path.is_file()]
    if missing:
        raise SystemExit('Release asset missing: ' + ', '.join(missing))
    return sorted(set(result))


def package(destination: Path):
    paths = selected_files()
    manifest = {}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, 'w:gz') as archive:
        for path in paths:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            manifest[name] = hashlib.sha256(data).hexdigest()
            info = tarfile.TarInfo('moin-hosted/' + name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
        payload = (json.dumps({'version': 1, 'sha256': manifest}, indent=2,
                              sort_keys=True) + '\n').encode()
        info = tarfile.TarInfo('moin-hosted/manifest.json')
        info.size = len(payload)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(payload))
    return len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    count = package(args.out)
    print(f'Packaged {count} files at {args.out}')


if __name__ == '__main__':
    main()
