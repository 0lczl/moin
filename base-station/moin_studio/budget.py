"""Conservative, durable spend allowances for the anonymous hosted pilot.

These limits reserve usage before network calls. They are intentionally below
the owner's USD 100 ceiling; provider-side key limits and billing alerts are
still required because prices, retries, taxes, and external account usage are
outside this application's control.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile


TTS_CHAR_LIMIT_PER_MONTH = 400_000
DEEPL_CHAR_LIMIT_LIFETIME = 900_000
ASR_BILLABLE_SECONDS_PER_MONTH = 100_000
TTS_USD_PER_1000_CHARS = 0.10
ASR_USD_PER_HOUR = 0.111
# DigitalOcean Basic 2 vCPU / 4 GiB pilot Droplet (October 2026 list price).
# This is a planning reserve, not a billing integration or invoice cap.
RESERVED_HOST_USD_PER_MONTH = 24.0
DEEPL_USD_PER_MILLION_CHARS_ESTIMATE = 25.0
RESERVED_MISC_USD_PER_MONTH = 10.0
OWNER_CEILING_USD_PER_MONTH = 100.0


class BudgetExceeded(RuntimeError):
    """Further billable work is blocked until a later period or new decision."""


class BudgetLedger:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.root / 'usage.json'
        self.lock_path = self.root / '.usage.lock'

    @staticmethod
    def _month():
        return datetime.now(timezone.utc).strftime('%Y-%m')

    def reserve(self, kind: str, quantity: int, *, month=None) -> dict:
        """Atomically reserve provider usage; failed calls stay reserved.

        `kind` is `tts_chars`, `deepl_chars`, or `asr_billable_seconds`.
        A reservation is not a claim that the provider actually billed it.
        """
        if kind not in {'tts_chars', 'deepl_chars', 'asr_billable_seconds'}:
            raise ValueError('Unknown budget resource')
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError('Budget quantity must be a positive integer')
        month = month or self._month()
        if not isinstance(month, str) or len(month) != 7 or month[4] != '-':
            raise ValueError('Invalid budget month')
        with self.lock_path.open('a+b') as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                try:
                    state = json.loads(self.path.read_text())
                except FileNotFoundError:
                    state = {'version': 1, 'deepl_chars_lifetime': 0, 'months': {}}
                if not isinstance(state, dict) or state.get('version') != 1:
                    raise RuntimeError('Budget ledger is invalid')
                usage = state['months'].setdefault(month, {
                    'tts_chars': 0, 'asr_billable_seconds': 0,
                })
                if kind == 'deepl_chars':
                    proposed = state['deepl_chars_lifetime'] + quantity
                    if proposed > DEEPL_CHAR_LIMIT_LIFETIME:
                        raise BudgetExceeded('DeepL pilot character allowance is exhausted')
                    state['deepl_chars_lifetime'] = proposed
                else:
                    proposed = usage[kind] + quantity
                    cap = TTS_CHAR_LIMIT_PER_MONTH if kind == 'tts_chars' else ASR_BILLABLE_SECONDS_PER_MONTH
                    if proposed > cap:
                        raise BudgetExceeded(f'{kind} monthly pilot allowance is exhausted')
                    usage[kind] = proposed
                # Treat every lifetime DeepL character as if it were billed
                # again this month. That intentionally overcounts on the free
                # plan and leaves room for a paid plan or account changes.
                estimated = (RESERVED_HOST_USD_PER_MONTH + RESERVED_MISC_USD_PER_MONTH
                             + state['deepl_chars_lifetime'] / 1_000_000 * DEEPL_USD_PER_MILLION_CHARS_ESTIMATE
                             + usage['tts_chars'] / 1000 * TTS_USD_PER_1000_CHARS
                             + usage['asr_billable_seconds'] / 3600 * ASR_USD_PER_HOUR)
                if estimated > OWNER_CEILING_USD_PER_MONTH:
                    raise BudgetExceeded('The monthly pilot spend ceiling is reached')
                fd, temporary = tempfile.mkstemp(prefix='.usage-', suffix='.tmp', dir=self.root)
                try:
                    os.fchmod(fd, 0o600)
                    with os.fdopen(fd, 'w') as stream:
                        json.dump(state, stream, separators=(',', ':'))
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, self.path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
                return {'month': month, 'usage': dict(usage),
                        'deepl_chars_lifetime': state['deepl_chars_lifetime'],
                        'estimated_usd': round(estimated, 4)}
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def reserve_if_configured(kind: str, quantity: int) -> dict | None:
    """Local runs are unmetered; a hosted worker must configure a ledger."""
    root = os.environ.get('MOIN_USAGE_LEDGER_DIR')
    if not root:
        return None
    return BudgetLedger(Path(root)).reserve(kind, quantity)
