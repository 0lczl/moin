"""Validate the small, editor-maintained Haramain catalog before publication.

Workflow: edit catalog.json, run ``python -m moin_haramain.catalog validate``,
then refresh the Studio. New publishing channels require code review here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from tools.import_youtube import canonical_url

DEFAULT_CATALOG = Path(__file__).with_name('catalog.json')
APPROVED_CHANNELS = {
    'haram-lessons': ('makkah', 'UC3QAoXf9GN9xeQYhk-AZbTg'),
    'imam-affairs': ('makkah', 'UC-G8RL7iYJt5L_-7F5bRKLA'),
    'nabawi-lessons': ('madinah', 'UC0XNCc-DU8J5_ksR-eufPaw'),
}
EXPECTED_MOSQUES = {'makkah', 'madinah'}
VIDEO_STATES = {'available', 'unavailable'}


def _required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} is required')


def _bilingual(value, field):
    if not isinstance(value, dict) or set(value) != {'ar', 'en'}:
        raise ValueError(f'{field} needs Arabic and English')
    for locale in ('ar', 'en'):
        _required_text(value[locale], f'{field}.{locale}')


def _indexed(items, field):
    if not isinstance(items, list):
        raise ValueError(f'{field} must be a list')
    found = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f'{field} has an invalid entry')
        key = item.get('id')
        _required_text(key, f'{field}.id')
        if key in found:
            raise ValueError(f'duplicate {field} id: {key}')
        found[key] = item
    return found


def validate_catalog(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('unsupported catalog schema')
    _required_text(data.get('updated_at'), 'updated_at')
    mosques = _indexed(data.get('mosques'), 'mosques')
    if set(mosques) != EXPECTED_MOSQUES:
        raise ValueError('catalog must contain Makkah and Madinah')
    for mosque in mosques.values():
        _bilingual(mosque.get('name'), 'mosque.name')
        _bilingual(mosque.get('city'), 'mosque.city')

    imams = _indexed(data.get('imams'), 'imams')
    if any(sum(i.get('mosque_id') == mosque for i in imams.values()) != 3 for mosque in EXPECTED_MOSQUES):
        raise ValueError('first release requires three imams per mosque')
    for imam in imams.values():
        _bilingual(imam.get('name'), 'imam.name')
        if imam.get('mosque_id') not in mosques:
            raise ValueError('imam has unknown mosque')

    sources = _indexed(data.get('sources'), 'sources')
    for source in sources.values():
        approved = APPROVED_CHANNELS.get(source['id'])
        if approved != (source.get('mosque_id'), source.get('channel_id')):
            raise ValueError(f'source {source["id"]} is not an approved institutional channel')
        _bilingual(source.get('name'), 'source.name')
        _required_text(source.get('verified_at'), 'source.verified_at')
        expected = f'https://www.youtube.com/channel/{approved[1]}'
        if source.get('url') != expected:
            raise ValueError(f'source {source["id"]} has an unapproved URL')

    videos = _indexed(data.get('videos'), 'videos')
    used_urls = set()
    for video in videos.values():
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video['id']):
            raise ValueError('invalid video ID')
        _bilingual(video.get('title'), 'video.title')
        if video.get('kind') != 'recorded' or video.get('state') not in VIDEO_STATES:
            raise ValueError('video must be recorded and available or unavailable')
        source = sources.get(video.get('source_id'))
        imam = imams.get(video.get('imam_id'))
        if not source or not imam or not (source['mosque_id'] == imam['mosque_id'] == video.get('mosque_id')):
            raise ValueError('video source, imam, and mosque do not match')
        url, video_id = canonical_url(video.get('url', ''))
        if url != video['url'] or video_id != video['id'] or url in used_urls:
            raise ValueError('video URL must be canonical and unique')
        used_urls.add(url)
        duration = video.get('duration_seconds')
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
            raise ValueError('video duration must be a positive integer')

    broadcasts = data.get('broadcasts')
    if not isinstance(broadcasts, list) or {b.get('mosque_id') for b in broadcasts if isinstance(b, dict)} != EXPECTED_MOSQUES or len(broadcasts) != 2:
        raise ValueError('one broadcast state is required per mosque')
    for broadcast in broadcasts:
        source = sources.get(broadcast.get('source_id'))
        if not source or source['mosque_id'] != broadcast['mosque_id']:
            raise ValueError('broadcast needs an approved source in the same mosque')
        if broadcast.get('state') == 'unavailable':
            if broadcast.get('url') is not None or broadcast.get('verified_at') is not None:
                raise ValueError('unavailable broadcast cannot publish an old link')
        elif broadcast.get('state') == 'available':
            _required_text(broadcast.get('verified_at'), 'broadcast.verified_at')
            url = broadcast.get('url', '')
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or parsed.hostname not in {'youtube.com', 'www.youtube.com'} or parsed.username or parsed.password or parsed.port or parsed.fragment:
                raise ValueError('broadcast needs an official YouTube live URL')
            if parsed.path == '/watch':
                try:
                    canonical_url(url)
                except ValueError as error:
                    raise ValueError('broadcast needs one YouTube video ID') from error
            elif not re.fullmatch(r'/live/[A-Za-z0-9_-]{11}', parsed.path) or parsed.query:
                raise ValueError('broadcast needs one official YouTube live URL')
        else:
            raise ValueError('invalid broadcast state')
    return data


def load_catalog(path=DEFAULT_CATALOG):
    return validate_catalog(json.loads(Path(path).read_text(encoding='utf-8')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate'])
    parser.add_argument('--catalog', type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    data = load_catalog(args.catalog)
    print(f'Valid: {len(data["videos"])} recorded videos, {len(data["sources"])} approved sources')


if __name__ == '__main__':
    main()
