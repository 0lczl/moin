"""The hosted process must fail before taking traffic if essentials are absent."""
from pathlib import Path
import shutil

import pytest

from moin_studio.server import validate_public_configuration


def configured(tmp_path):
    return {
        'MOIN_PUBLIC_BASE_URL': 'https://moin.example',
        'GROQ_API_KEY': 'test-not-real',
        'DEEPL_AUTH_KEY': 'test-not-real',
        'ELEVENLABS_API_KEY': 'test-not-real',
        'MOIN_ASR_PROVIDER': 'groq',
        'MOIN_LIVE_ASR': 'groq',
        'MOIN_USAGE_LEDGER_DIR': str(tmp_path / 'ledger'),
    }


def test_public_configuration_requires_https_secrets_and_metering(tmp_path):
    options = configured(tmp_path)
    options['MOIN_PUBLIC_BASE_URL'] = 'http://moin.example'
    with pytest.raises(ValueError, match='HTTPS'):
        validate_public_configuration(tmp_path / 'storage', environ=options)

    options = configured(tmp_path)
    del options['MOIN_USAGE_LEDGER_DIR']
    with pytest.raises(ValueError, match='MOIN_USAGE_LEDGER_DIR'):
        validate_public_configuration(tmp_path / 'storage', environ=options)

    options = configured(tmp_path)
    options['MOIN_STUDIO_CANDIDATE'] = 'other'
    with pytest.raises(ValueError, match='deepl-v1'):
        validate_public_configuration(tmp_path / 'storage', environ=options)


def test_valid_public_configuration_checks_runtime_assets(tmp_path, monkeypatch, sample_renderings_path):
    fixture_base = tmp_path / 'base'
    config_dir = fixture_base / 'benchmark-data'
    renderings_dir = config_dir / 'staging-renderings'
    renderings_dir.mkdir(parents=True)
    source_config = Path(__file__).resolve().parents[1] / 'benchmark-data/local-comparison.json'
    shutil.copyfile(source_config, config_dir / 'local-comparison.json')
    shutil.copyfile(sample_renderings_path, renderings_dir / 'renderings.quranenc.json')
    monkeypatch.setattr('moin_studio.server.BASE', fixture_base)
    monkeypatch.setattr('moin_studio.server.shutil.which', lambda name: '/usr/bin/' + name)
    assert validate_public_configuration(tmp_path / 'storage', environ=configured(tmp_path)) == 'https://moin.example'
    assert (tmp_path / 'ledger').is_dir()
