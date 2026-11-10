# Validation and reference figures

## Python tests

Run `python -B -m pytest -q -p no:cacheprovider` from the project root after installing `requirements.txt`. The tests check key uniqueness, data integrity, reference calculations, Power BI JSON structure and display settings. They do not run DAX in a Power BI engine.

## Reference values, December 2025

| DPD bucket | Exposure | Exposure share |
|---|---:|---:|
| 0 DPD | 138,140,272.66 | 88.5432% |
| 30–59 | 7,791,840.83 | 4.9943% |
| 60–89 | 2,671,070.35 | 1.7121% |
| 90+ | 7,411,342.15 | 4.7504% |
| Total | 156,014,525.99 | 100.0000% |

Four decimal places are retained for reference; programmatic comparisons use unrounded values.

## Actual Power BI DAX comparison

**Status after the simulation fix (November 2026):** the delinquency transitions and the ECL proxy were corrected and all data was regenerated. The Power BI checks described below were made on the previous data and must be repeated against the regenerated files.


1. Configure `DataFolderPath`, refresh and run `powerbi/reconciliation/monthly.dax` and `month_segment.dax` in Power BI Desktop's DAX query view.
2. Copy each complete result grid with headers to UTF-8 tab-separated files outside version control.
3. Run `python -B -m src.reconciliation --monthly PATH_TO_MONTHLY.tsv --month-segment PATH_TO_MONTH_SEGMENT.tsv`.

The comparator checks 12 monthly and 36 month–segment rows, four original measures each; absolute tolerances are 0.01 for amounts and 1e-8 for rates. An empty 90+ result is conditionally normalized only for a month–segment with positive reference exposure, no 90+ observations, and three matching remaining metrics. This policy assumes the model and export reflect the same input data. The user previously verified the relevant January/Subprime BLANK directly in Desktop; this is reported evidence, not an automatically executed query.

In the earlier reconciliation, 192 original KPI values from actual Power BI exports were compared with Python under this conditional BLANK policy. This 192-value reconciliation was not rerun in the subsequent clean GitHub clone. `monthly.tsv` and `month_segment.tsv` are local evidence and are intentionally excluded from the publication package.

The user subsequently verified a preconfigured Desktop test copy made from a clean GitHub clone: the project opened, refresh succeeded, both pages loaded, segment and product filters worked, and selecting multiple months showed the latest month's KPI without summing month-end exposures. All six representative actual-model DAX checks in the local `QA_Desktop_Check.dax` returned PASS. This was verified manually in Power BI Desktop. The test copy was configured before opening; manual replacement of the placeholder in the original clean clone has not been separately verified.

`page2_monthly.dax` and `ux_category_check.dax` are separate prepared queries for newer measures; their full query results and comparison have not been verified in the new clone. The six representative checks do not constitute exhaustive validation of every measure, month, filter combination or visual.
