# Decision log

Method choices for the synthetic credit-risk case study, with the reason for each. The
numbers in `src/pipeline.py` are named constants at the top of the file.

## D1 – Synthetic data instead of real loan data

Real loan-level data with delinquency histories is not public in Sweden. A simulation
makes every rule visible and testable, at the cost that segment risk levels are set by
assumption. The README separates what the simulation sets from what the analysis finds.

## D2 – Portfolio design

- 1,600 loans, three risk segments (Prime 49 %, Near-prime 36 %, Subprime 15 %) and two
  products (personal 72 %, auto 28 %).
- Opening balances uniform between 22,000 and 240,000, read as SEK.
- Base 12-month PD of 1.8 %, 5.5 % and 14.5 % per segment, with loan-level lognormal noise
  (σ = 0.25), clipped to 0.2–60 %. LGD uniform between 25 % and 65 %.
- Fixed seed `990903`, so every run produces the same portfolio.

## D3 – Delinquency transitions

- Every loan is current in January 2025 and moves at most one 30-day bucket per month.
  A one-bucket rule is how real DPD counters behave and makes roll rates interpretable.
- New delinquency: one third of the loan's PD per month, rising by 6 % of that level each
  month, to create a mild deterioration over the year.
- Roll 30→60: 25 %, roll 60→90: 30 %, cure from 30–89 to current: 19 % per month. The
  same rates apply in every segment, so the analysis cannot find segment differences in
  roll rates (README, Limitations).
- Cure and roll use the same uniform draw from opposite ends, so a loan can never both
  cure and roll in the same month.

## D4 – Default definition

90+ DPD is treated as default and is absorbing. This mirrors the 90-days-past-due
backstop in the regulatory default definition, but it is a simulation rule, not a
validated definition.

## D5 – Balances

Current loans amortize 2.2 % of the opening balance per paid installment. Missed
installments are not amortized, a cured loan has paid its arrears, and balances are
frozen at default. Month-end balances are snapshots, so they are never summed across
months.

## D6 – Loss proxy, not IFRS 9

Loss proxy = balance × PD × LGD, with PD = 1 for defaulted (90+) balances and the assumed
12-month PD otherwise. It deliberately leaves out staging, lifetime PD, forward-looking
scenarios and discounting, which a real IFRS 9 ECL needs. The name "loss proxy" (and
"not IFRS 9" on every page) keeps that visible.

## D7 – Exposure-weighted delinquency, account-weighted roll rates

Delinquency rates are weighted by balance, because the business question is how much
money is at risk. Roll rates are counted per account, because they describe behaviour.

## D8 – PD back-test with Wilson intervals

The observed 12-month default rate per segment is compared with the mean assumed PD.
Wilson score intervals are used because default rates are small proportions, where the
normal approximation gives intervals that can go below zero. A PD is called consistent
when it lies inside the 95 % interval; one 12-month window is not enough to recalibrate.

## D9 – One number, three implementations

The key KPIs are computed in Python, re-computed in SQL (`sql/portfolio_analysis.sql`)
and in DAX (Power BI). The tests check that Python and SQL agree; the DAX check is
described in `docs/VALIDATION.md`.
