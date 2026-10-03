"""The hosted pilot stops work before its conservative provider allowances."""
import pytest

from moin_studio.budget import BudgetExceeded, BudgetLedger


def test_reservations_survive_restart_and_enforce_lifetime_and_monthly_caps(tmp_path):
    ledger = BudgetLedger(tmp_path)
    a = ledger.reserve('deepl_chars', 500_000, month='2026-10')
    assert a['deepl_chars_lifetime'] == 500_000
    restarted = BudgetLedger(tmp_path)
    restarted.reserve('deepl_chars', 400_000, month='2026-11')
    with pytest.raises(BudgetExceeded):
        restarted.reserve('deepl_chars', 1, month='2026-11')
    restarted.reserve('tts_chars', 400_000, month='2026-10')
    with pytest.raises(BudgetExceeded):
        restarted.reserve('tts_chars', 1, month='2026-10')
    assert restarted.reserve('tts_chars', 1, month='2026-11')['usage']['tts_chars'] == 1


def test_unknown_or_invalid_reservations_do_not_change_ledger(tmp_path):
    ledger = BudgetLedger(tmp_path)
    with pytest.raises(ValueError):
        ledger.reserve('nope', 1)
    with pytest.raises(ValueError):
        ledger.reserve('tts_chars', -1)
    with pytest.raises(ValueError):
        ledger.reserve('tts_chars', True)
    assert not ledger.path.exists()
