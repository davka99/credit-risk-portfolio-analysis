"""Balance (EAD proxy) rules for the synthetic portfolio.

1. A loan that misses a payment does not amortize: when DPD rises, the
   balance is the same as the month before.
2. A defaulted loan (90+ DPD) stops paying, so its balance is frozen.
3. A loan that is current in two consecutive months pays its installment,
   so its balance falls.
4. Balances are never negative and never exceed the opening balance.
"""
import numpy as np
import pytest

from src.pipeline import generate


@pytest.fixture(scope="module")
def panel():
    loans, snapshots = generate()
    s = snapshots.sort_values(["loan_id", "month"]).merge(
        loans[["loan_id", "opening_balance"]], on="loan_id"
    )
    s["prev_dpd"] = s.groupby("loan_id").dpd.shift()
    s["prev_ead"] = s.groupby("loan_id").ead.shift()
    return s.dropna(subset=["prev_dpd"])


def test_no_amortization_when_a_payment_is_missed(panel):
    missed = panel[panel.dpd > panel.prev_dpd]
    assert not missed.empty
    np.testing.assert_allclose(missed.ead, missed.prev_ead)


def test_defaulted_balance_is_frozen(panel):
    defaulted = panel[(panel.prev_dpd >= 90) & (panel.dpd >= 90)]
    assert not defaulted.empty
    np.testing.assert_allclose(defaulted.ead, defaulted.prev_ead)


def test_current_loans_amortize(panel):
    current = panel[(panel.prev_dpd == 0) & (panel.dpd == 0)]
    assert (current.ead < current.prev_ead).all()


def test_balances_within_bounds(panel):
    assert (panel.ead >= 0).all()
    assert (panel.ead <= panel.opening_balance + 0.01).all()
