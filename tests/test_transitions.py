"""Delinquency transition rules for the synthetic portfolio.

These tests encode how days past due (DPD) can move between monthly
snapshots. They are written before the fix: on the original generator the
first three tests fail, which is the point.

Rules
-----
1. Every loan is current (0 DPD) before the first observed month, so the
   first snapshot can show at most 30 DPD.
2. DPD can rise by at most one bucket (30 days) per month. A loan cannot
   go from 0 to 60, 0 to 90 or 30 to 90 in a single month.
3. 90+ DPD is treated as default and is absorbing: once a loan reaches
   90, it stays at 90 for every later month in the window.
4. The simulation must still produce delinquency and cures, so the rules
   cannot be satisfied by simply removing all movement.
"""
import pandas as pd
import pytest

from src.pipeline import generate


@pytest.fixture(scope="module")
def transitions():
    """One row per loan and consecutive month pair: previous and current DPD."""
    _, snapshots = generate()
    s = snapshots.sort_values(["loan_id", "month"]).copy()
    s["prev_dpd"] = s.groupby("loan_id").dpd.shift()
    return s


def test_first_month_starts_at_most_30_dpd(transitions):
    first_month = transitions[transitions.month == transitions.month.min()]
    too_high = first_month[first_month.dpd > 30]
    assert too_high.empty, (
        f"{len(too_high)} loans start above 30 DPD in the first month; "
        f"DPD values seen: {sorted(too_high.dpd.unique())}"
    )


def test_dpd_rises_at_most_one_bucket_per_month(transitions):
    pairs = transitions.dropna(subset=["prev_dpd"])
    jumps = pairs[pairs.dpd - pairs.prev_dpd > 30]
    counts = jumps.groupby(["prev_dpd", "dpd"]).size().to_dict()
    assert jumps.empty, f"Impossible one-month DPD jumps (from, to): count = {counts}"


def test_default_is_absorbing(transitions):
    pairs = transitions.dropna(subset=["prev_dpd"])
    left_default = pairs[(pairs.prev_dpd >= 90) & (pairs.dpd < 90)]
    counts = left_default.dpd.value_counts().to_dict()
    assert left_default.empty, (
        f"{len(left_default)} transitions leave 90+ DPD; new DPD: count = {counts}"
    )


def test_transitions_are_not_degenerate(transitions):
    pairs = transitions.dropna(subset=["prev_dpd"])
    seen = set(zip(pairs.prev_dpd.astype(int), pairs.dpd.astype(int)))
    required = {(0, 30), (30, 60), (60, 90), (30, 0)}
    missing = required - seen
    assert not missing, f"Expected transitions never occur: {sorted(missing)}"
