# Credit Risk & Portfolio Analytics

A reproducible synthetic credit-portfolio monitoring project for exploring exposure-weighted delinquency, risk segments, and monthly portfolio movement. Python generates and analyzes the data; SQLite illustrates SQL analysis; a Power BI Desktop project provides an editable report and semantic model as versionable text.

**All borrower data and outcomes are synthetic.** This is a portfolio case study, not a production underwriting model, a validated default-rate estimate, or an IFRS 9 expected-credit-loss calculation.

[Interactive HTML dashboard](https://davka99.github.io/credit-risk-portfolio-analysis/reports/dashboard.html) · [Power BI setup](powerbi/BUILD_GUIDE.md) · [Validation](docs/VALIDATION.md) · [Publication audit](PUBLICATION_READINESS.md)

![Preview of the existing HTML dashboard](assets/dashboard_preview.png)

## Executive Summary

A portfolio team needs to monitor how exposure and overdue balances evolve, identify simulated segments that warrant investigation, and understand where severe delinquency is concentrated. The project supports consistent portfolio monitoring and informed discussion using entirely synthetic data.

In December 2025, simulated exposure (EAD proxy) was approximately **155.99 million**, with **7.55%** at 30+ days past due and **3.41%** at 90+ days past due. The illustrative loss proxy was approximately **3.43 million**; it is not IFRS 9 ECL.

The exposure-weighted 30+ delinquency rate was approximately **23.80% for Subprime**, **8.31% for Near-prime**, and **2.91% for Prime**. These differences flag areas for closer monitoring, not causal conclusions. A portfolio team could investigate segment and product mix, examine monthly movements, and review the simulation assumptions before drawing further conclusions. Findings from this synthetic case study do not establish real-world outcomes or support underwriting decisions.

## Data and model

The dataset contains 1,600 synthetic loans and 19,200 monthly observations for January–December 2025. `Loans` has one row per loan; `MonthlySnapshots` has one row per loan per month. A single-direction one-to-many relationship on `loan_id` links the dimension to snapshots. Month-end balances are snapshots, so summing across months is not a single-month exposure.

```text
Loans (1)  ── loan_id ──>  (*) MonthlySnapshots
  segment, product,              month, EAD, DPD,
  assumed PD and LGD             DPD bucket
```

The existing CSVs are synthetic, reproducible inputs. The pipeline also writes a SQLite copy, KPI CSVs and the Plotly HTML dashboard. The input CSVs and SQLite file are present for SQL practice; Power BI imports the CSVs. The simulation generates DPD values 0, 30, 60 and 90. `Current` is 0 DPD in this dataset; intervals are presentation buckets, not evidence of observed repayment behavior.

## Measures and limitations

| Measure | Definition |
|---|---|
| Exposure / EAD proxy | Simulated month-end outstanding balance; not a validated regulatory EAD. |
| 30+ / 90+ DPD rate | Balance on loans with DPD ≥ 30 / ≥ 90 divided by total balance for the same context. |
| 30+ month-on-month change | Latest selected month's 30+ rate minus the immediately preceding calendar month's rate, expressed in percentage points. Blank when the prior month has no positive exposure. |
| Illustrative ECL proxy | Sum of balance × assumed 12-month PD × assumed LGD. It excludes full IFRS 9 staging, forward-looking scenarios and discounting. |
| Roll rate | Account-count share transitioning between consecutive recorded delinquency buckets; it is not exposure-weighted. |

90+ DPD is a severe-delinquency indicator, not a validated contractual or regulatory default definition. Prime, Near-prime and Subprime are simulated segments with different assumed PD baselines; findings do not generalize to real lenders.

## Reports

- **Executive Overview:** December snapshot cards, monthly delinquency history and comparison by risk segment.
- **Delinquency & Portfolio Analysis:** month, segment and product filters; latest-selected-month snapshot cards; change against the prior calendar month; selected-month trend; exposure mix and delinquent-bucket comparison. Cards and distributions use the latest month within the selection, rather than summing balances across months.

The Power BI project is stored as PBIP with PBIR report definitions and TMDL semantic-model definitions. The custom JSON theme is under `powerbi/themes/`; a registered copy is included with the report. The opening preview shows the HTML dashboard.

**Executive Overview** — December portfolio exposure and delinquency.

![Power BI Executive Overview](assets/powerbi-executive-overview.png)

**Delinquency & Portfolio Analysis** — trends, risk segments and exposure mix.

![Power BI Delinquency and Portfolio Analysis](assets/powerbi-delinquency-analysis.png)

## Python setup and reproduction

Requires Python 3.11+ and Internet access to install packages. From the project root in Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

To regenerate the synthetic data, SQLite, KPI reports and HTML dashboard:

```powershell
.\.venv\Scripts\python.exe -B -m src.pipeline
```

**The pipeline overwrites** the generated files in `data/` and `reports/`. Use a disposable copy if you want to preserve the checked-in versions. NumPy random seed is `990903`; exact packages are specified as ranges rather than a lockfile.

## Open Power BI Desktop

1. Open `powerbi/CreditRisk.pbip` in a compatible Power BI Desktop version. Keep `CreditRisk.Report` and `CreditRisk.SemanticModel` adjacent to it.
2. In **Transform data → Manage parameters**, set `DataFolderPath` to the absolute path of this clone's `data` folder. The checked-in placeholder `SET_DATA_FOLDER_PATH` is intentionally not a working path. There is no portable automatic detection of the PBIP folder.
3. Apply the change, grant local file access if prompted, and refresh. Both CSVs must be in that folder with their original names.
4. Verify that both pages load, filters work, the portfolio exposure card and bucket totals agree, and the latest-month/previous-month behavior matches the definitions above. Project cache and per-user settings are intentionally excluded; a fresh project opens without cached data until refresh.

See [Power BI setup and limitations](powerbi/BUILD_GUIDE.md). The user verified opening and refresh in a preconfigured test copy made from a clean GitHub clone. Manually replacing the placeholder in the original clone has not been separately verified.

## Quality assurance

- **37 Python tests passed** in the documented isolated environment, covering the generator, data contracts, reference calculations and report structure.
- In an earlier verification, **192 original KPI values** from actual Power BI exports were reconciled against Python across 12 months and 36 month–segment combinations for four original measures, using the documented conditional BLANK rule. This reconciliation was not rerun in the new clean clone.
- In a preconfigured test copy made from a clean GitHub clone, the user verified that the PBIP opened, refresh succeeded, both pages loaded, segment and product filters worked, and multiple-month selection used the latest month without summing exposures. All **6 of 6 representative DAX checks** passed in Power BI Desktop.
- A broader, complete validation of every measure, filter combination and visual has not been performed. Manual configuration of the placeholder in the original clean clone remains unverified.

The Python comparator reads exported actual-model DAX results; it does not evaluate DAX itself. The original exports are not included as source files; obtain fresh exports for a new reconciliation. See [validation instructions](docs/VALIDATION.md) for the BLANK rule, tolerances and reproducible checks. Static model checks and simulated export tests are not actual DAX execution.

## Technology

Python 3.11+, NumPy, pandas, Plotly, pytest, SQLite SQL, Power Query/M, DAX, PBIR and TMDL. Power BI Desktop is a separate installation. The initial pipeline, code and documentation used AI assistance; verification status is documented rather than inferred.
