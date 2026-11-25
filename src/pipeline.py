"""Fully synthetic loan-portfolio case study. Reproducible and non-regulatory.

Run ``python -m src.pipeline`` from the project root to regenerate the synthetic data,
the SQLite database, the KPI reports and the HTML dashboard.
"""
from pathlib import Path
from string import Template
import sqlite3

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
REPORTS = ROOT / 'reports'
TEMPLATES = Path(__file__).resolve().parent / 'templates'
SEED = 990903

SEGMENTS = ['Prime', 'Near-prime', 'Subprime']
BUCKETS = ['Current', '30-59', '60-89', '90+']

# Simulation assumptions (see docs/decisions.md). All values are illustrative.
SEGMENT_MIX = [.49, .36, .15]                 # share of loans per segment
SEGMENT_PD = {'Prime': .018, 'Near-prime': .055, 'Subprime': .145}  # base 12-month PD
PRODUCTS = ['Personal loan', 'Auto loan']
PRODUCT_MIX = [.72, .28]
ADVERSE_DRIFT = .06    # delinquency onset rises by 6 % of its base level per month
ROLL_30_TO_60 = .25    # monthly probability of rolling from 30-59 to 60-89 DPD
ROLL_60_TO_90 = .30    # monthly probability of rolling from 60-89 to 90+ DPD (default)
CURE = .19             # monthly probability that a 30-89 DPD loan pays all arrears
AMORTIZATION = .022    # share of the opening balance repaid per paid installment


def generate(n=1600, months=12):
    """Simulate ``n`` loans over ``months`` month-ends starting January 2025.

    Returns ``(accounts, snapshots)``: one row per loan, and one row per loan and month.
    """
    rng = np.random.default_rng(SEED)
    origination = rng.integers(0, 6, n)  # months before Jan 2025
    loan_id = np.arange(100001, 100001 + n)
    segment = rng.choice(SEGMENTS, n, p=SEGMENT_MIX)
    product = rng.choice(PRODUCTS, n, p=PRODUCT_MIX)
    balance0 = rng.uniform(22000, 240000, n).round(2)
    pd_12m = np.select([segment == s for s in SEGMENTS], [SEGMENT_PD[s] for s in SEGMENTS])
    pd_12m = np.clip(pd_12m * rng.lognormal(0, .25, n), .002, .6)
    lgd = rng.uniform(.25, .65, n)
    accounts = pd.DataFrame({
        'loan_id': loan_id,
        'segment': segment,
        'product': product,
        'origination_date': (pd.Period('2024-07', freq='M') + origination).astype(str),
        'opening_balance': balance0,
        'pd_12m_assumed': pd_12m.round(6),
        'lgd_assumed': lgd.round(6),
    })

    dpd = np.zeros(n, dtype=int)
    paid = np.zeros(n, dtype=int)  # installments paid since the January 2025 opening balance
    records = []
    for m in range(months):
        # 30+ delinquency probabilities respond to credit quality and a mild adverse environment.
        adverse = 1 + ADVERSE_DRIFT * m
        p_onset = np.minimum(pd_12m / 3 * adverse, .4)
        # Each loan makes at most one transition per month. Every rule reads the
        # start-of-month state (prev), so a loan cannot pass several buckets at once.
        prev = dpd.copy()
        u = rng.random(n)
        dpd = np.where((prev == 0) & (u < p_onset), 30, prev)         # new delinquency
        dpd = np.where((prev == 30) & (u < ROLL_30_TO_60), 60, dpd)   # roll 30 -> 60
        dpd = np.where((prev == 60) & (u < ROLL_60_TO_90), 90, dpd)   # roll 60 -> 90 (default)
        # Cure uses the top of the same draw, so it can never coincide with a roll.
        # 90+ is default and absorbing: no rule moves a loan out of prev == 90.
        dpd = np.where((prev > 0) & (prev < 90) & (u > 1 - CURE), 0, dpd)
        # Linear amortization of 2.2% of the opening balance per paid installment.
        # Installments due by month m: m + 1. Each 30 DPD is one missed installment, and a
        # cured loan has paid all arrears. Defaulted loans (90+) stop paying, so their
        # balance is frozen at the level reached before default.
        paid = np.where(dpd >= 90, paid, np.maximum(0, (m + 1) - dpd // 30))
        ead = np.maximum(0, balance0 * (1 - AMORTIZATION * paid)).round(2)
        buckets = np.select(
            [dpd == 0, dpd == 30, dpd == 60, dpd >= 90], BUCKETS, default='Current'
        )
        month = str(pd.Period('2025-01', freq='M') + m)
        records.extend(zip(loan_id, [month] * n, ead, dpd, buckets))

    snapshots = pd.DataFrame(records, columns=['loan_id', 'month', 'ead', 'dpd', 'dpd_bucket'])
    return accounts, snapshots


def validate(accounts, snapshots):
    """Data contracts: unique keys, valid DPD values, a full 12-month panel."""
    assert accounts.loan_id.is_unique
    assert not snapshots.duplicated(['loan_id', 'month']).any()
    assert snapshots.ead.ge(0).all()
    assert snapshots.dpd.isin([0, 30, 60, 90]).all()
    assert snapshots.loan_id.isin(accounts.loan_id).all()
    assert snapshots.groupby('loan_id').month.nunique().eq(12).all()


def analyze(accounts, snapshots):
    """Monthly KPIs, latest-month segment KPIs and one-month roll rates.

    Returns ``(monthly, segments, roll, latest)``.
    """
    joined = snapshots.merge(accounts, on='loan_id', validate='many_to_one')
    # Defaulted exposures (90+ DPD) carry PD = 1; performing loans use the assumed 12-month PD.
    joined['pd_effective'] = np.where(joined.dpd >= 90, 1.0, joined.pd_12m_assumed)
    joined['ecl_12m_illustrative'] = joined.ead * joined.pd_effective * joined.lgd_assumed
    joined['delinq_ead'] = np.where(joined.dpd >= 30, joined.ead, 0)
    joined['severe_ead'] = np.where(joined.dpd >= 90, joined.ead, 0)

    monthly = joined.groupby('month', as_index=False).agg(
        exposure=('ead', 'sum'),
        delinquent_ead=('delinq_ead', 'sum'),
        severe_ead=('severe_ead', 'sum'),
        illustrative_ecl=('ecl_12m_illustrative', 'sum'),
        loans=('loan_id', 'nunique'),
    )
    monthly['dq30_pct'] = monthly.delinquent_ead / monthly.exposure * 100
    monthly['dq90_pct'] = monthly.severe_ead / monthly.exposure * 100

    latest = joined[joined.month == joined.month.max()].copy()
    segments = latest.groupby('segment', as_index=False).agg(
        exposure=('ead', 'sum'),
        delinquent_ead=('delinq_ead', 'sum'),
        ecl=('ecl_12m_illustrative', 'sum'),
        accounts=('loan_id', 'nunique'),
    )
    segments['dq30_pct'] = segments.delinquent_ead / segments.exposure * 100
    segments['segment'] = pd.Categorical(segments['segment'], SEGMENTS, ordered=True)
    segments = segments.sort_values('segment')

    trans = joined.sort_values(['loan_id', 'month']).copy()
    trans['next_bucket'] = trans.groupby('loan_id').dpd_bucket.shift(-1)
    transitions = (
        trans.dropna(subset=['next_bucket'])
        .groupby(['dpd_bucket', 'next_bucket'], observed=True)
        .size()
        .unstack(fill_value=0)
    )
    transitions = transitions.reindex(index=BUCKETS, columns=BUCKETS, fill_value=0)
    roll = transitions.div(transitions.sum(axis=1), axis=0) * 100
    return monthly, segments, roll, latest


def pd_backtest(accounts, snapshots):
    """Compare the assumed 12-month PD with the observed 12-month default rate per segment.

    A loan counts as defaulted if it reaches 90+ DPD at any point in the observation window.
    All loans are current at the start of the window and observed for 12 months, so the
    observed rate is directly comparable with a 12-month PD.
    """
    defaulted = snapshots.groupby('loan_id').dpd.max().ge(90).rename('defaulted')
    joined = accounts.merge(defaulted, left_on='loan_id', right_index=True, validate='one_to_one')
    result = joined.groupby('segment', as_index=False).agg(
        loans=('loan_id', 'count'),
        assumed_pd=('pd_12m_assumed', 'mean'),
        observed_default_rate=('defaulted', 'mean'),
    )
    result['observed_to_assumed'] = result.observed_default_rate / result.assumed_pd
    # 95% Wilson score interval for the observed default rate (binomial sampling noise).
    z = 1.959964
    n = result.loans
    p = result.observed_default_rate
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    result['ci95_low'] = centre - half
    result['ci95_high'] = centre + half
    result['assumed_within_ci'] = result.assumed_pd.between(result.ci95_low, result.ci95_high)
    result['segment'] = pd.Categorical(result['segment'], SEGMENTS, ordered=True)
    return result.sort_values('segment').reset_index(drop=True)


def make_dashboard(monthly, segments, roll, latest):
    """Write the self-contained interactive dashboard to reports/dashboard.html."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    navy = '#182B42'
    blue = '#316B9B'
    orange = '#D38B52'
    ink = '#182B42'
    segment_colors = [navy, blue, orange]
    last = monthly.iloc[-1]
    headline = (
        f"{last.exposure/1e6:,.1f}M",
        f"{last.dq30_pct:.1f}%",
        f"{last.illustrative_ecl/1e6:,.2f}M",
    )

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[
            'Delinquency trend (exposure weighted)',
            'Exposure by risk segment',
            'Roll rates between monthly buckets',
            'Illustrative ECL by segment',
        ],
        specs=[[{'type': 'xy'}, {'type': 'xy'}], [{'type': 'heatmap'}, {'type': 'xy'}]],
        horizontal_spacing=.15,
        vertical_spacing=.22,
    )
    percent_hover = '%{x}<br>%{y:.2f}%<extra></extra>'
    fig.add_trace(
        go.Scatter(x=monthly.month, y=monthly.dq30_pct, name='30+ DPD',
                   line={'color': blue, 'width': 3}, mode='lines+markers',
                   hovertemplate=percent_hover),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=monthly.month, y=monthly.dq90_pct, name='90+ DPD',
                   line={'color': orange, 'width': 2}, mode='lines',
                   hovertemplate=percent_hover),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=segments.segment.astype(str), y=segments.exposure / 1e6,
               marker_color=segment_colors, showlegend=False,
               hovertemplate='%{x}<br>%{y:.1f}M<extra></extra>'),
        row=1, col=2,
    )
    fig.add_trace(
        go.Heatmap(x=roll.columns.tolist(), y=roll.index.tolist(), z=roll.to_numpy(),
                   colorscale=[[0, '#F1F5F9'], [.5, '#98B6D0'], [1, navy]], zmin=0, zmax=100,
                   text=np.round(roll.to_numpy(), 1), texttemplate='%{text:.1f}%',
                   hovertemplate='%{y} → %{x}: %{z:.1f}%<extra></extra>', showscale=False),
        row=2, col=1,
    )
    fig.add_trace(
        go.Bar(x=segments.segment.astype(str), y=segments.ecl / 1e6,
               marker_color=segment_colors, showlegend=False,
               hovertemplate='%{x}<br>%{y:.2f}M<extra></extra>'),
        row=2, col=2,
    )
    fig.update_layout(
        height=760,
        margin={'l': 55, 'r': 35, 't': 75, 'b': 45},
        plot_bgcolor='white',
        paper_bgcolor='white',
        font={'family': 'Arial', 'color': ink, 'size': 12},
        legend={'orientation': 'h', 'y': 1.12, 'x': 0},
        title={'text': 'PORTFOLIO RISK | Analyst view', 'x': .045,
               'font': {'size': 18, 'color': navy}},
    )
    fig.update_xaxes(showgrid=False, linecolor='#E5EAF0')
    fig.update_yaxes(gridcolor='#E5EAF0', zeroline=False)
    fig.update_yaxes(title_text='Delinquent EAD (%)', row=1, col=1)
    fig.update_yaxes(title_text='Exposure (M SEK, synthetic)', row=1, col=2)
    fig.update_yaxes(title_text='ECL proxy (M SEK)', row=2, col=2)

    content = fig.to_html(full_html=False, include_plotlyjs=True,
                          config={'displaylogo': False, 'responsive': True})
    labels = ['Exposure', '30+ DPD · EAD weighted', 'ECL proxy · not IFRS 9']
    metrics = ''.join(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>'
        for label, value in zip(labels, headline)
    )
    template = Template((TEMPLATES / 'dashboard.html').read_text(encoding='utf8'))
    html = template.substitute(metrics=metrics, content=content)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'dashboard.html').write_text(html, encoding='utf8')
    if _has_kaleido():
        fig.write_image(REPORTS / 'dashboard_charts.png', width=1280, height=760, scale=1)


def _has_kaleido():
    try:
        import kaleido  # noqa: F401
    except ImportError:
        return False
    return True


def main():
    DATA.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    accounts, snapshots = generate()
    validate(accounts, snapshots)
    accounts.to_csv(DATA / 'loans_synthetic.csv', index=False)
    snapshots.to_csv(DATA / 'monthly_snapshots_synthetic.csv', index=False)
    with sqlite3.connect(DATA / 'portfolio.sqlite') as con:
        accounts.to_sql('loans', con, if_exists='replace', index=False)
        snapshots.to_sql('snapshots', con, if_exists='replace', index=False)

    monthly, segments, roll, latest = analyze(accounts, snapshots)
    monthly.to_csv(REPORTS / 'monthly_kpis.csv', index=False)
    segments.to_csv(REPORTS / 'segment_kpis.csv', index=False)
    roll.to_csv(REPORTS / 'roll_rates.csv')
    pd_backtest(accounts, snapshots).to_csv(REPORTS / 'pd_backtest.csv', index=False)
    make_dashboard(monthly, segments, roll, latest)

    print(f'Generated {len(accounts):,} synthetic loans and {len(snapshots):,} monthly records')
    print(f'Latest period: {monthly.month.iloc[-1]}, '
          f'30+ DPD: {monthly.dq30_pct.iloc[-1]:.2f}%, '
          f'ECL proxy: {monthly.illustrative_ecl.iloc[-1]:,.0f}')
    print(f'Open report: {REPORTS / "dashboard.html"}')


if __name__ == '__main__':
    main()
