"""Provider preflight must select the matching API host without spending quota."""

import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError

import pytest


SPEC = importlib.util.spec_from_file_location(
    "run_free_demo", Path(__file__).resolve().parents[2] / "tools/run_free_demo.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class Success:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_deepl_preflight_uses_host_that_accepts_key():
    attempted = []

    def opener(request, **_kwargs):
        attempted.append(request.full_url)
        assert request.get_header("Authorization") == "DeepL-Auth-Key test:fx"
        if "api-free" in request.full_url:
            raise HTTPError(request.full_url, 403, "auth", {}, io.BytesIO(b"Authentication failed"))
        return Success()

    environment = {"DEEPL_AUTH_KEY": "test:fx"}
    launcher.check_deepl_credentials(environment, opener=opener)
    assert attempted == [
        "https://api-free.deepl.com/v2/usage",
        "https://api.deepl.com/v2/usage",
    ]
    assert environment["DEEPL_API_BASE_URL"] == "https://api.deepl.com"


def test_deepl_preflight_rejection_does_not_expose_key_or_response():
    def opener(request, **_kwargs):
        raise HTTPError(request.full_url, 403, "auth", {}, io.BytesIO(b"provider-account-details"))

    with pytest.raises(RuntimeError) as error:
        launcher.check_deepl_credentials({"DEEPL_AUTH_KEY": "secret-key"}, opener=opener)
    assert "both rejected" in str(error.value)
    assert "secret-key" not in str(error.value)
    assert "provider-account-details" not in str(error.value)
