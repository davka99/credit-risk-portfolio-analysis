# Power BI implementation guide (not a verified PBIX)

1. Open Power BI Desktop → Get data → Text/CSV. Import `data/loans_synthetic.csv` and `data/monthly_snapshots_synthetic.csv`.
2. Set `loan_id` integer in both tables, `ead` decimal, `dpd` whole number, `pd_12m_assumed` and `lgd_assumed` decimal. Convert `month` (YYYY-MM) to a proper first-of-month Date in Power Query.
3. Model: **Loans (1) → (*) MonthlySnapshots** on `loan_id` with single-direction filtering; do not relate on `month` alone.
4. Use a separate calendar date dimension for more advanced time analysis.
5. Add measures from `MEASURES.dax` and make a risk dashboard: 3 KPI cards, monthly trend, segment bar, bucket distribution. Use a white background, restrained navy/blue/orange accents, and explicit dates.
6. Confirm cards and totals match the Python CSV outputs before presenting the report. The DAX is a reference implementation and has not been tested in Power BI Desktop here.

**Never present this as a ready-made tested `.pbix` file.**
