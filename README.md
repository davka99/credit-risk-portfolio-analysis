# Credit Risk & Portfolio Analytics

A monthly risk review of a synthetic consumer-loan portfolio (1,600 loans, 2025) that answers three questions: how much exposure is delinquent, where the expected loss sits, and whether the default-probability (PD) assumptions held. The headline finding is that Near-prime, not Subprime, carries the largest share of the illustrative loss proxy (47% of it on 36% of exposure), while 30+ days-past-due exposure rose from 1.7% to 11.8% over the year. Python generates and analyzes the data, SQL reproduces the key queries, a Power BI project (PBIP, DAX) presents the results, and GitHub Actions runs the pytest suite.

**In plain words:** a bank lends money to 1,600 people. Each month some of them pay late. This project tracks how much money is paid late, which customer groups the bank should worry about most, and whether the bank's own risk estimates were right. The surprise: the middle-risk group, not the riskiest one, accounts for the largest part of the expected loss, because it is much bigger.

> **All borrower data and outcomes are synthetic.** This is a portfolio case study, not a production underwriting model, a validated default-rate estimate or an IFRS 9 expected-credit-loss calculation.

[Interactive HTML dashboard](https://davka99.github.io/credit-risk-portfolio-analysis/reports/dashboard.html) · [Power BI setup](powerbi/BUILD_GUIDE.md) · [Validation](docs/VALIDATION.md)

## Business question

A portfolio team reviews the loan book every month and needs to answer three questions:

1. How much exposure is delinquent, and is it getting worse?
2. Where is the expected loss concentrated?
3. Are the PD assumptions behind the loss proxy consistent with how the portfolio actually performed?

## Key findings (December 2025)

Amounts are in synthetic SEK.

| Metric | December 2025 | January 2025 |
|---|---:|---:|
| Portfolio exposure (EAD proxy) | 153.29 million | 201.36 million |
| 30+ DPD, exposure-weighted | 11.76% | 1.71% |
| 90+ DPD, exposure-weighted | 5.34% | 0.00% |
| Illustrative loss proxy | 6.72 million | – |

- **Delinquency rose every month until November and dipped slightly in December** (11.81% to 11.76%). 90+ keeps building because defaulted loans stay in the book.
- **Near-prime carries the largest share of the loss proxy.** It holds 36% of exposure but 47% of the loss proxy and 53% of 90+ exposure. Subprime has the highest rates (32.02% at 30+ DPD) but only 13% of exposure, and 34% of the loss proxy.
- **54% of the loss proxy comes from loans already in default**; the remaining 46% is the expected loss on performing loans.
- **Early delinquency is still recoverable.** In a typical month, 19% of 30–59 DPD accounts cure and 26% roll to 60–89. From 60–89 DPD, 31% roll into default within one month.
- **The PD back-test does not show a significant miscalibration.** Observed 12-month default rates versus assumed PD: Prime 2.24% vs 1.84%, Near-prime 6.88% vs 5.74%, Subprime 11.06% vs 14.67%. With 217–802 loans per segment, every assumed PD lies inside the 95% confidence interval of the observed rate.

![Share of exposure and share of the loss proxy per risk segment](assets/loss_vs_exposure_by_segment.png)

*How to read it: each pair of bars is one customer group. The light bar is its share of the money lent, the dark bar its share of the expected loss. Where the dark bar is longer, the group causes more loss than its size suggests.*

## Recommendation

1. **Plan collections capacity around Near-prime, not only Subprime.** Near-prime holds most of the delinquent and defaulted exposure, even though its rates are lower.
2. **Intervene before 60 DPD.** At 30–59 DPD, about one in five accounts still cures each month; at 60–89 DPD, about a third default the following month.
3. **Keep the current PD assumptions, but keep testing them.** Prime and Near-prime defaulted more than assumed and Subprime less, but one 12-month window cannot separate this from sampling noise. Repeat the back-test on new windows and vintages before recalibrating.

These recommendations follow from the synthetic data and illustrate the analysis workflow; they are not evidence about real lenders.

## What the simulation sets, and what the analysis finds

Some results follow directly from the simulation design and should not be read as discoveries:

- **Set by design:** segment PD levels (Subprime riskiest), a gradual monthly increase in delinquency onset, and the same roll and cure probabilities in every segment.
- **Found by the analysis:** where exposure and the loss proxy concentrate given the portfolio mix, how much of the loss proxy is already defaulted, and whether realized defaults are consistent with the assumed PDs.

## Dashboards

**Executive Overview** — December portfolio exposure, delinquency and loss proxy.

![Power BI Executive Overview](assets/powerbi-executive-overview.png)

*How to read it: the three cards are the December figures. The left chart shows, month by month, how large a share of the money lent is at least 30 days late (dark) and at least 90 days late (blue). The right chart shows the same 30-day share per customer group. Amounts are in millions of synthetic SEK.*

**Delinquency & Portfolio Analysis** — month, segment and product filters, trends, risk segments and exposure mix.

![Power BI Delinquency and Portfolio Analysis](assets/powerbi-delinquency-analysis.png)

*How to read it: the filters at the top change every chart on the page. The ring shows how the money lent splits by days late; the bars at the bottom show the late amounts in millions of synthetic SEK.*

## Data and model

The dataset contains 1,600 synthetic loans and 19,200 monthly observations for January–December 2025. `Loans` has one row per loan; `MonthlySnapshots` has one row per loan per month, linked one-to-many on `loan_id`. Month-end balances are snapshots, so summing across months is not a single-month exposure.

```text
Loans (1)  ── loan_id ──>  (*) MonthlySnapshots
  segment, product,              month, EAD, DPD,
  assumed PD and LGD             DPD bucket
```

Simulation rules (`src/pipeline.py`, seed `990903`):

- Every loan is current at the start of the window. DPD can rise by at most one 30-day bucket per month.
- 90+ DPD is treated as default and is absorbing: a defaulted loan stays at 90+.
- Current loans amortize 2.2% of the opening balance per paid installment. Missed installments are not amortized, a cured loan has paid its arrears, and defaulted balances are frozen.

## KPI definitions

| Measure | Definition |
|---|---|
| Exposure / EAD proxy | Simulated month-end outstanding balance; not a validated regulatory EAD. |
| 30+ / 90+ DPD rate | Balance on loans with DPD ≥ 30 / ≥ 90 divided by total balance in the same month and filter context. |
| 30+ month-on-month change | Latest selected month's 30+ rate minus the previous calendar month's rate, in percentage points. Blank when the previous month has no exposure. |
| Illustrative loss proxy | Sum of balance × PD × assumed LGD, where PD = 1 for defaulted exposures (90+ DPD) and the assumed 12-month PD otherwise. It excludes IFRS 9 staging, forward-looking scenarios and discounting. |
| Roll rate | Share of accounts moving between delinquency buckets from one month to the next; account-weighted, not exposure-weighted. |
| Observed 12-month default rate | Share of loans in a segment that reach 90+ DPD at any point in the 12-month window, with a 95% Wilson confidence interval. |

## Project structure

| Path | Content |
|---|---|
| `src/pipeline.py` | Data generation, validation, KPIs, roll rates, PD back-test and HTML dashboard (template in `src/templates/`) |
| `src/readme_figures.py` | The README figure (share of exposure vs share of loss proxy) |
| `docs/decisions.md` | Every simulation and method choice, with the reason |
| `sql/portfolio_analysis.sql` | SQLite queries: monthly delinquency, roll rates, segment loss proxy, PD back-test |
| `powerbi/` | Power BI project (PBIP with PBIR report and TMDL semantic model), DAX measures and theme |
| `tests/` | pytest suite |
| `data/`, `reports/`, `reference/` | Generated synthetic data, KPI outputs and reference values used by the tests |

## How to run

Requires Python 3.12. From the project root:

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m src.pipeline
```

**macOS / Linux**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q -p no:cacheprovider
python -m src.pipeline
```

`src.pipeline` regenerates the data, the SQLite database, the KPI reports and the HTML dashboard (it overwrites the files in `data/` and `reports/`). To redraw the README figure, install matplotlib and run `python -m src.readme_figures`.

To open the Power BI report, open `powerbi/CreditRisk.pbip` in Power BI Desktop, set the `DataFolderPath` parameter to the absolute path of the `data` folder and refresh. See [Power BI setup](powerbi/BUILD_GUIDE.md).

## Quality assurance

- **52 Python tests pass** (2026-11-25), covering delinquency transition rules, balance rules, the loss proxy and the PD back-test in both Python and SQL, data contracts, reference KPI values and report structure. GitHub Actions runs the suite on every pull request and push to `main`.
- **Power BI Desktop check** (2026-11-10): after refresh on the current data, December exposure, 30+ and 90+ rates, month-on-month change, segment rates, delinquent-bucket amounts and the loss proxy matched the Python results.
- The full measure-by-measure reconciliation against exported DAX results is described in [Validation](docs/VALIDATION.md); it has not been repeated on the current data.

## Limitations

- All data is synthetic, and segment risk levels are set by assumption.
- The observation window is 12 months for loans originated within six months of each other, so vintage analysis is not meaningful on this data.
- Roll and cure probabilities are the same in every segment, so segment differences in roll rates cannot be analyzed.
- The loss proxy is not IFRS 9 ECL and 90+ DPD is a simulation default, not a validated regulatory definition.

## Technology

Python 3.12, NumPy, pandas, Plotly, matplotlib, pytest, SQLite, Power Query (M), DAX, Power BI PBIP (PBIR and TMDL), GitHub Actions.

## License

Code: MIT (see `LICENSE`). All data in the repository is synthetic.
