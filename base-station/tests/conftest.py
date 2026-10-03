"""Small, synthetic assets for tests that must run from a clean checkout."""

import json

import pytest


@pytest.fixture
def sample_renderings_path(tmp_path):
    path = tmp_path / "renderings.fixture.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "detection_ready": True,
        "renderings": [{
            "arabic": "هذا نص تجريبي لا يمثل آية",
            "english": {
                "text": "This is a synthetic test rendering",
                "source": "Test fixture",
                "version": "1",
                "approved": True,
            },
            "french": {
                "text": "Ceci est un rendu de test synthétique",
                "source": "Test fixture",
                "version": "1",
                "approved": True,
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return path
