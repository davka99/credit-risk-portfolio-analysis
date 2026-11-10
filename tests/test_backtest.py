"""PD back-test: assumed 12-month PD vs observed 12-month default rate."""
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline import generate, pd_backtest

ROOT = Path(__file__).resolve().parents[1]


def test_default_flag_counts_any_month_at_90_plus():
    loans = pd.DataFrame({
        "loan_id": [1, 2, 3],
        "segment": ["Prime", "Prime", "Subprime"],
        "pd_12m_assumed": [0.02, 0.04, 0.10],
    })
    snapshots = pd.DataFrame({
        "loan_id": [1, 1, 2, 2, 3, 3],
        "month": ["2025-01", "2025-02"] * 3,
        "dpd": [0, 0, 30, 0, 60, 90],  # loan 2 cures, loan 3 defaults
    })
    result = pd_backtest(loans, snapshots).set_index("segment")
    assert result.loc["Prime", "loans"] == 2
    assert result.loc["Prime", "assumed_pd"] == pytest.approx(0.03)
    assert result.loc["Prime", "observed_default_rate"] == 0
    assert result.loc["Subprime", "observed_default_rate"] == 1
    assert result.loc["Subprime", "observed_to_assumed"] == pytest.approx(10)


def test_wilson_interval_known_values():
    # 0 defaults out of 10 loans: Wilson 95% interval is [0, 0.2775].
    loans = pd.DataFrame({"loan_id": range(10), "segment": ["Prime"] * 10, "pd_12m_assumed": [0.1] * 10})
    snapshots = pd.DataFrame({"loan_id": range(10), "month": ["2025-01"] * 10, "dpd": [0] * 10})
    row = pd_backtest(loans, snapshots).iloc[0]
    assert row.ci95_low == pytest.approx(0, abs=1e-12)
    assert row.ci95_high == pytest.approx(0.2775, abs=1e-4)
    assert bool(row.assumed_within_ci)


def test_backtest_covers_portfolio_and_matches_sql():
    loans, snapshots = generate()
    python = pd_backtest(loans, snapshots)
    assert python.loans.sum() == len(loans)
    assert python.observed_default_rate.between(0, 1).all()
    queries = [q for q in (ROOT / "sql/portfolio_analysis.sql").read_text().split(";") if "observed_default_rate" in q]
    assert len(queries) == 1
    with sqlite3.connect(":memory:") as con:
        loans.to_sql("loans", con, index=False)
        snapshots.to_sql("snapshots", con, index=False)
        sql = pd.read_sql_query(queries[0], con).set_index("segment")
    for row in python.itertuples():
        assert sql.loc[row.segment, "loans"] == row.loans
        assert sql.loc[row.segment, "assumed_pd"] == pytest.approx(row.assumed_pd, abs=5e-5)
        assert sql.loc[row.segment, "observed_default_rate"] == pytest.approx(row.observed_default_rate, abs=5e-5)
