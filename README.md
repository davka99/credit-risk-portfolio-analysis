# Credit Risk & Portfolio Analytics

**A reproducible, end-to-end credit portfolio monitoring case study** combining Python, SQL and interactive business intelligence.

[**View the live interactive dashboard**](https://davka99.github.io/credit-risk-portfolio-analysis/reports/dashboard.html) · [Explore the analysis code](src/pipeline.py) · [Review SQL queries](sql/portfolio_analysis.sql) · [Power BI starter guide](powerbi/BUILD_GUIDE.md)

> **Portfolio simulation — not real lending data.** The 1,600 loans and all outcomes are synthetic. This is an analytical demonstration, not a deployed lending model, underwriting recommendation or IFRS 9-compliant calculation.

![Credit Risk dashboard — synthetic portfolio](assets/dashboard_preview.png)

## Executive summary

**Business problem:** A hypothetical credit portfolio team needs to identify where repayment delays are concentrated, how delinquency develops through time and which segments warrant closer monitoring. This case demonstrates an auditable workflow from generated loan records and monthly observations to SQL analysis and a decision-oriented dashboard.

**Illustrative findings (December 2025, synthetic data):**

| Metric | Result | Interpretation |
|---|---:|---|
| Portfolio outstanding exposure | 155.99 million synthetic currency units | Month-end outstanding balance proxy |
| 30+ DPD exposure share | **7.55%** | Share of outstanding exposure on accounts 30 or more days past due |
| 90+ DPD exposure share | **3.41%** | Severe delinquency proxy, not an established default rate |
| Illustrative expected-loss proxy | **3.43 million synthetic currency units** | Assumed 12-month PD × assumed LGD × outstanding exposure; **not** IFRS 9 ECL |
| Subprime 30+ DPD exposure share | **23.80%** | Compared with **2.91%** in Prime and **8.31%** in Near-prime |

Across the simulated months, the 30+ DPD exposure share rises from **0.93% in January** to **7.55% in December 2025**, peaking at **8.48% in September**. These patterns come from simulation assumptions, **not observed real-world credit trends**.

**Hypothetical business action:** Investigate the drivers of deterioration by segment and origination vintage, validate data definitions, and review whether earlier customer-support or collections interventions should be tested. No causal effectiveness or actual loss reduction is claimed.

## What the project demonstrates

- **Python (pandas, NumPy):** Seeded, reproducible synthetic loan generation, month-end records, validation and aggregation.
- **SQL / SQLite:** Exposure-based delinquency metrics, monthly account transitions (roll rates), segment analysis and window functions.
- **BI and visualization:** Interactive Plotly dashboard and a concise management-oriented presentation.
- **Data quality and testing:** Checks of dataset structure and accounting/aggregation logic with pytest.
- **Power BI / DAX:** A documented implementation pathway and reference measures; **no tested .pbix/.pbip deliverable is included**.

## Project structure

```text
├── assets/dashboard_preview.png      # Dashboard screenshot
├── data/                             # Clearly labelled synthetic CSVs and SQLite
├── powerbi/                          # Build guide and reference DAX measures
├── reports/                          # Interactive HTML and KPI output tables
├── sql/portfolio_analysis.sql        # Portfolio SQL queries
├── src/pipeline.py                   # Reproducible generation and analysis
├── tests/test_pipeline.py            # Automated tests
├── LEARNING_TASKS.md                 # Practical skills exercises
├── README.md
└── requirements.txt
```

## Reproduce locally

Requires **Python 3.11+**. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
python -m pytest -q
```

Then open `reports/dashboard.html`. Alternatively, [open the live dashboard](https://davka99.github.io/credit-risk-portfolio-analysis/reports/dashboard.html). Regenerated data use NumPy random seed **990903**.

## Key metric definitions

| Measure | Definition |
|---|---|
| Exposure / EAD proxy | Synthetic month-end outstanding balance; **not validated regulatory EAD** |
| 30+ DPD exposure share | Sum of balances for accounts with days past due ≥ 30 / total month-end balances |
| 90+ DPD exposure share | Sum of balances for accounts with days past due ≥ 90 / total month-end balances |
| Monthly roll rate | Number of accounts moving from one delinquency bucket to another / number starting in the source bucket |
| Illustrative loss proxy | Sum of balance × assumed 12-month PD × assumed LGD; excludes full IFRS 9 scenario, lifetime and discounting logic |

**Grain matters:** The exposure shares are balance-weighted snapshots, while roll rates describe transitions between account states. They must not be compared as though they were the same metric.

## Limitations and next steps

1. **Synthetic, simplified portfolio:** Migration, amortization and risk parameters are simulated. Figures cannot be generalized to real borrowers, lenders or markets.
2. **Risk definitions:** 90+ DPD is a severe-delinquency indicator, not a validated default definition. The loss proxy is **not IFRS 9 ECL**, which requires more detailed staging, forward-looking scenario analysis and discounting where applicable.
3. **Model validation:** No production PD model, temporal backtesting, causal collection-intervention evaluation or regulatory compliance assessment is claimed.
4. **Next iterations:** Origination-vintage views, concentration/drift monitoring, calibrated PD modelling with out-of-time validation, and a tested Power BI Desktop report with reconciled DAX KPIs.

## Methodological references

- [European Banking Authority — Loan Origination and Monitoring](https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring)
- [IFRS Foundation](https://www.ifrs.org/)
- [Basel Committee on Banking Supervision](https://www.bis.org/bcbs/)

These are methodological references, **not sources for the simulated numerical results**.

## AI assistance and learning track

The initial synthetic data pipeline, code, visualizations and project documentation were produced with AI assistance and checked through execution and automated tests. This portfolio showcases a practical workflow rather than claiming that all implementation was authored independently. Independent skills exercises and interview preparation are provided in [LEARNING_TASKS.md](LEARNING_TASKS.md).
