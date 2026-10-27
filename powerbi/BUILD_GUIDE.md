# Power BI Desktop setup

1. Open `CreditRisk.pbip` in Power BI Desktop; keep both sibling report and semantic-model folders intact.
2. Open **Transform data → Manage parameters**. Replace `DataFolderPath`'s `SET_DATA_FOLDER_PATH` placeholder with the absolute path to this clone's `data` folder. Do not include a CSV filename. The queries allow a trailing slash or backslash.
3. Apply changes, approve local source access if prompted, then refresh. Confirm 1,600 loans and 19,200 monthly snapshots. Initial opening can be empty until refresh because local `.pbi/cache.abf` is excluded.
4. Check both report pages, December reference KPIs, cross-filters and bucket totals. The report uses the registered Financial Risk theme; the reusable original is `themes/financial-risk.json`.
5. For DAX comparison, follow `../docs/VALIDATION.md`. DAX queries under `reconciliation/` run against model measures and do not define replacement measures.

This setup is designed for portability by changing one parameter. It has not yet been verified by opening the sanitized publication folder in Power BI Desktop. Paths are not automatically relative to PBIP.
