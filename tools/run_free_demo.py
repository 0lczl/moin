#!/usr/bin/env python3
"""Run the public pilot on this Mac behind a temporary Cloudflare Quick Tunnel.

Provider keys are read from the environment or an invisible terminal prompt.
They are passed only to the local Moin process and are never written to disk.
"""
from __future__ import annotations

import argparse
from collections import deque
import getpass
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import webbrowser

import certifi


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "base-station"
PYTHON = BASE / ".venv/bin/python"
STORAGE = BASE / "studio-runs/public-demo"
LEDGER = BASE / "studio-runs/public-demo-ledger"
URL_FILE = STORAGE / "public-demo-url.txt"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com\b")
KEYS = (
    ("GROQ_API_KEY", "Groq API key"),
    ("DEEPL_AUTH_KEY", "DeepL API key"),
    ("ELEVENLABS_API_KEY", "ElevenLabs API key"),
)


def provider_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name, label in KEYS:
        if not env.get(name, "").strip():
            if not sys.stdin.isatty():
                raise RuntimeError(f"{label} requires an interactive Terminal")
            env[name] = getpass.getpass(f"Paste {label} (input hidden): ").strip()
        if not env[name]:
            raise RuntimeError(f"{label} cannot be empty")
    env.update({
        "MOIN_ASR_PROVIDER": "groq",
        "MOIN_LIVE_ASR": "groq",
        "MOIN_USAGE_LEDGER_DIR": str(LEDGER),
        "MOIN_PUBLIC_BASE_URL": "https://preflight.invalid",
        "SSL_CERT_FILE": certifi.where(),
        "PATH": str(BASE / ".venv/bin") + os.pathsep + env.get("PATH", ""),
    })
    return env


def check_local_requirements(env: dict[str, str]) -> None:
    if not PYTHON.is_file():
        raise RuntimeError("The prepared Python environment is missing: base-station/.venv")
    if shutil.which("cloudflared") is None:
        raise RuntimeError("Install the free tunnel client with: brew install cloudflared")
    STORAGE.mkdir(parents=True, exist_ok=True, mode=0o700)
    LEDGER.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = subprocess.run(
        [str(PYTHON), "-m", "moin_studio", "--public", "--check-public",
         "--storage", str(STORAGE)],
        cwd=BASE, env=env, capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Moin public preflight failed:\n" + result.stderr.strip())
    check_groq_credentials(env)


def check_groq_credentials(env: dict[str, str], opener=urlopen) -> None:
    """Check the chosen ASR key before advertising a working public demo.

    A model lookup has no audio usage. Never include the response body or key
    in an error because provider responses can contain account details.
    """
    request = Request(
        "https://api.groq.com/openai/v1/models/whisper-large-v3",
        headers={"Authorization": f"Bearer {env['GROQ_API_KEY']}"},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with opener(request, timeout=12, context=context) as response:
            if response.status != 200:
                raise RuntimeError("Groq could not confirm Whisper large-v3 availability.")
    except HTTPError as error:
        if error.code in (401, 403):
            raise RuntimeError(
                "Groq rejected the API key. Stop this run and restart with a fresh "
                "Groq key from console.groq.com/keys. If GROQ_API_KEY is set in "
                "your shell, unset it first so the launcher prompts again."
            ) from None
        raise RuntimeError(f"Groq model check failed (HTTP {error.code}). Retry shortly.") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Could not reach Groq to check the API key. Check the network and retry.") from None


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def tunnel_url(process: subprocess.Popen[str], timeout: float = 60) -> str:
    found = threading.Event()
    blocked = threading.Event()
    public_url: list[str] = []
    recent: deque[str] = deque(maxlen=6)

    def read_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            recent.append(line.strip())
            if "precheck complete hard_fail=true" in line:
                blocked.set()
            match = URL_PATTERN.search(line)
            if match and not public_url:
                public_url.append(match.group(0))
                found.set()

    threading.Thread(target=read_output, daemon=True).start()
    deadline = time.monotonic() + timeout
    found_at: float | None = None
    while time.monotonic() < deadline:
        if blocked.is_set():
            raise RuntimeError("This network blocks Cloudflare Tunnel (port 7844). "
                               "Connect the Mac to another network, such as an iPhone hotspot, and retry.")
        if found.is_set() and found_at is None:
            found_at = time.monotonic()
        # A Quick Tunnel prints its URL before checking edge connectivity.
        if found_at is not None and time.monotonic() - found_at >= 5:
            return public_url[0]
        time.sleep(0.25)
        if process.poll() is not None:
            break
    raise RuntimeError("Cloudflare did not provide a demo URL. " + " | ".join(recent))


def wait_for_page(url: str, host: str | None = None, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    last_error = "service did not respond"
    while time.monotonic() < deadline:
        try:
            request = Request(url, headers={"Host": host} if host else {})
            context = (ssl.create_default_context(cafile=certifi.where())
                       if urlsplit(url).scheme == "https" else None)
            with urlopen(request, timeout=5, context=context) as response:
                body = response.read(4096)
                if (response.status == 200
                        and "text/html" in response.headers.get("Content-Type", "")
                        and b"Moin" in body):
                    return
                last_error = f"HTTP {response.status} did not contain a Moin page"
        except HTTPError as error:
            last_error = ("Cloudflare tunnel is not connected (HTTP 530). "
                          "Try an iPhone hotspot or another network."
                          if error.code == 530 else str(error))
        except (URLError, TimeoutError) as error:
            last_error = str(error)
        time.sleep(0.5)
    raise RuntimeError(f"Demo page did not become ready: {last_error}")


def stop(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Validate without opening a public tunnel")
    args = parser.parse_args()
    cloudflared: subprocess.Popen[str] | None = None
    moin: subprocess.Popen[str] | None = None
    try:
        URL_FILE.unlink(missing_ok=True)
        env = provider_environment()
        check_local_requirements(env)
        if args.check_only:
            print("Local public-demo requirements are ready. No tunnel was opened.")
            return 0

        port = free_port()
        cloudflared = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            env={name: value for name, value in os.environ.items()
                 if name not in {key for key, _label in KEYS}},
        )
        public_url = tunnel_url(cloudflared)
        env["MOIN_PUBLIC_BASE_URL"] = public_url
        moin = subprocess.Popen(
            [str(PYTHON), "-m", "moin_studio", "--public", "--host", "127.0.0.1",
             "--port", str(port), "--storage", str(STORAGE)],
            cwd=BASE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        host = urlsplit(public_url).netloc
        wait_for_page(f"http://127.0.0.1:{port}/", host=host)
        wait_for_page(public_url + "/", timeout=45)
        for page in ("/haramain", "/live"):
            wait_for_page(public_url + page, timeout=20)

        URL_FILE.write_text(public_url + "\n", encoding="utf-8")
        print("\nMoin public demo is ready:", public_url, flush=True)
        print("Keep this Mac awake, connected, and this Terminal open.")
        print("Anyone with the link can use the demo and consume provider free-tier quotas.")
        print("The link changes when you restart. Press Ctrl+C to stop.\n", flush=True)
        webbrowser.open(public_url)
        while cloudflared.poll() is None and moin.poll() is None:
            time.sleep(1)
        raise RuntimeError("The demo stopped unexpectedly; restart this command for a new link")
    except KeyboardInterrupt:
        print("\nStopping the public demo.")
        return 0
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        URL_FILE.unlink(missing_ok=True)
        stop(moin)
        stop(cloudflared)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda _signum, _frame: sys.exit(0))
    raise SystemExit(main())
