# Validation and reference figures

## Python tests

Run `python -B -m pytest -q -p no:cacheprovider` from the project root after installing `requirements.txt`. The tests check key uniqueness, data integrity, reference calculations, Power BI JSON structure and display settings. They do not run DAX in a Power BI engine.

## Reference values, December 2025

| DPD bucket | Exposure | Exposure share |
|---|---:|---:|
| 0 DPD | 144,219,580.26 | 92.4516% |
| 30–59 | 3,836,227.13 | 2.4592% |
| 60–89 | 2,613,820.74 | 1.6756% |
| 90+ | 5,325,097.36 | 3.4136% |
| Total | 155,994,725.49 | 100.0000% |

Four decimal places are retained for reference; programmatic comparisons use unrounded values.

## Actual Power BI DAX comparison

1. Configure `DataFolderPath`, refresh and run `powerbi/reconciliation/monthly.dax` and `month_segment.dax` in Power BI Desktop's DAX query view.
2. Copy each complete result grid with headers to UTF-8 tab-separated files outside version control.
3. Run `python -B -m src.reconciliation --monthly PATH_TO_MONTHLY.tsv --month-segment PATH_TO_MONTH_SEGMENT.tsv`.

The comparator checks 12 monthly and 36 month–segment rows, four original measures each; absolute tolerances are 0.01 for amounts and 1e-8 for rates. An empty 90+ result is conditionally normalized only for a month–segment with positive reference exposure, no 90+ observations, and three matching remaining metrics. This policy assumes the model and export reflect the same input data. The user previously verified the relevant January/Subprime BLANK directly in Desktop; this is reported evidence, not an automatically executed query.

`page2_monthly.dax` and `ux_category_check.dax` prepare actual-model checks for newer measures. These checks still need a fresh Power BI Desktop run and comparison. `monthly.tsv` and `month_segment.tsv` are local evidence and are intentionally excluded from the publication package.
