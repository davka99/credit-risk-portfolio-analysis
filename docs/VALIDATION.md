# Validation and reference figures

## Python tests

Run `python -B -m pytest -q -p no:cacheprovider` from the project root after installing `requirements.txt`. The suite (51 tests, 2026-11-10) checks:

- **Simulation rules:** at most one DPD bucket per month, absorbing default at 90+, no amortization on missed installments, frozen balances in default.
- **Calculations:** the loss proxy (PD = 1 at 90+ DPD), the PD back-test and its Wilson interval, and that the SQL queries return the same results as Python.
- **Data contracts:** unique keys, valid DPD values, non-negative balances, 12 months per loan.
- **Reference values:** monthly and segment KPIs against `reference/`, and the December figures below.
- **Report structure:** Power BI page and visual definitions.

The tests do not run DAX in a Power BI engine.

## Reference values, December 2025

| DPD bucket | Exposure | Exposure share |
|---|---:|---:|
| 0 DPD | 135,269,882.22 | 88.2447% |
| 30–59 | 6,319,797.39 | 4.1228% |
| 60–89 | 3,517,781.50 | 2.2949% |
| 90+ | 8,182,035.76 | 5.3376% |
| Total | 153,289,496.87 | 100.0000% |

Four decimal places are retained for reference; programmatic comparisons use unrounded values.

## Power BI Desktop check, current data

Checked on 2026-11-10 after refreshing the model on the current data. For December 2025, the report shows the same values as Python:

| Measure | Value |
|---|---:|
| Portfolio exposure | 153.29 million |
| 30+ DPD rate | 11.76% |
| 90+ DPD rate | 5.34% |
| 30+ change vs November | −0.06 pp |
| 30+ DPD rate by segment | Prime 3.90% · Near-prime 15.40% · Subprime 32.02% |
| Delinquent exposure 30–59 / 60–89 / 90+ | 6.32 / 3.52 / 8.18 million |
| Loss proxy | 6.72 million |

## Full DAX reconciliation

1. Configure `DataFolderPath`, refresh and run `powerbi/reconciliation/monthly.dax` and `month_segment.dax` in Power BI Desktop's DAX query view.
2. Copy each complete result grid with headers to UTF-8 tab-separated files outside version control.
3. Run `python -B -m src.reconciliation --monthly PATH_TO_MONTHLY.tsv --month-segment PATH_TO_MONTH_SEGMENT.tsv`.

The comparator checks 12 monthly and 36 month–segment rows with four measures each (192 values); absolute tolerances are 0.01 for amounts and 1e-8 for rates. An empty 90+ result is accepted only for a month–segment with positive exposure, no 90+ observations and three matching remaining metrics.

This full reconciliation passed on the previous version of the data. It has not yet been repeated on the current data; the Desktop check above covers the December figures only.
