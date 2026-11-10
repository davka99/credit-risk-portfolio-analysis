"""ECL proxy rules: defaulted exposures (90+ DPD) carry PD = 1.

The proxy is illustrative and not IFRS 9 ECL, but it must at least treat
defaulted loans as defaulted. The SQL query must agree with Python.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.pipeline import analyze, generate

ROOT = Path(__file__).resolve().parents[1]


def _tiny_portfolio():
    loans = pd.DataFrame({
        "loan_id": [1, 2],
        "segment": ["Prime", "Subprime"],
        "product": ["Personal loan", "Auto loan"],
        "pd_12m_assumed": [0.02, 0.10],
        "lgd_assumed": [0.40, 0.50],
    })
    snapshots = pd.DataFrame({
        "loan_id": [1, 2],
        "month": ["2025-01", "2025-01"],
        "ead": [1000.0, 2000.0],
        "dpd": [0, 90],
        "dpd_bucket": ["Current", "90+"],
    })
    return loans, snapshots


def test_defaulted_exposure_uses_pd_of_one():
    loans, snapshots = _tiny_portfolio()
    monthly, segments, _, _ = analyze(loans, snapshots)
    performing = 1000.0 * 0.02 * 0.40   # assumed PD
    defaulted = 2000.0 * 1.00 * 0.50    # PD = 1 at 90+ DPD
    assert monthly.illustrative_ecl.iloc[0] == pytest.approx(performing + defaulted)
    by_segment = segments.set_index(segments.segment.astype(str)).ecl
    assert by_segment["Prime"] == pytest.approx(performing)
    assert by_segment["Subprime"] == pytest.approx(defaulted)


def test_defaulted_ecl_equals_ead_times_lgd_on_generated_data():
    loans, snapshots = generate()
    _, _, _, latest = analyze(loans, snapshots)
    defaulted = latest[latest.dpd >= 90]
    assert not defaulted.empty
    np.testing.assert_allclose(
        defaulted.ecl_12m_illustrative, defaulted.ead * defaulted.lgd_assumed
    )


def test_sql_segment_ecl_matches_python():
    loans, snapshots = generate()
    _, segments, _, _ = analyze(loans, snapshots)
    queries = [q for q in (ROOT / "sql/portfolio_analysis.sql").read_text().split(";") if "ecl_proxy" in q]
    assert len(queries) == 1
    with sqlite3.connect(":memory:") as con:
        loans.to_sql("loans", con, index=False)
        snapshots.to_sql("snapshots", con, index=False)
        sql = pd.read_sql_query(queries[0], con).set_index("segment").ecl_proxy
    python = segments.set_index(segments.segment.astype(str)).ecl
    for segment, value in python.items():
        assert sql[segment] == pytest.approx(value, abs=0.01)
