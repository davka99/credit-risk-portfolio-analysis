"""Fully synthetic loan-portfolio case study. Reproducible and non-regulatory."""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
REPORTS = ROOT / 'reports'
SEED = 990903


def generate(n=1600, months=12):
    rng = np.random.default_rng(SEED)
    origination = rng.integers(0, 6, n)  # months before Jan 2025
    loan_id = np.arange(100001, 100001+n)
    segment = rng.choice(['Prime', 'Near-prime', 'Subprime'], n, p=[.49,.36,.15])
    product = rng.choice(['Personal loan','Auto loan'],n,p=[.72,.28])
    balance0 = rng.uniform(22000,240000,n).round(2)
    pd_12m = np.select([segment=='Prime',segment=='Near-prime',segment=='Subprime'],[.018,.055,.145])
    pd_12m = np.clip(pd_12m * rng.lognormal(0,.25,n),.002,.6)
    lgd = rng.uniform(.25,.65,n)
    accounts = pd.DataFrame({'loan_id':loan_id,'segment':segment,'product':product,
        'origination_date':(pd.Period('2024-07',freq='M')+origination).astype(str),
        'opening_balance':balance0,'pd_12m_assumed':pd_12m.round(6),'lgd_assumed':lgd.round(6)})
    dpd = np.zeros(n,dtype=int)
    records=[]
    for m in range(months):
        # 30+ delinquency probabilities respond to credit quality and a mild adverse environment.
        adverse = 1 + .06*m
        p_onset = np.minimum(pd_12m/3 * adverse, .4)
        u = rng.random(n)
        dpd=np.where((dpd==0)&(u<p_onset),30,dpd)
        u=rng.random(n)
        dpd=np.where((dpd==30)&(u<.25),60,dpd)
        u=rng.random(n)
        dpd=np.where((dpd==60)&(u<.3),90,dpd)
        u=rng.random(n)
        dpd=np.where((dpd>0)&(u<.19),0,dpd)
        # No unobserved cash flows are inferred; illustrative amortization only.
        ead=np.maximum(0,balance0 * (1-.022*m) * rng.uniform(.985,1.015,n)).round(2)
        buckets=np.select([dpd==0,dpd==30,dpd==60,dpd>=90],['Current','30-59','60-89','90+'],default='Current')
        month=str(pd.Period('2025-01',freq='M')+m)
        records.extend(zip(loan_id, [month]*n, ead, dpd, buckets))
    snapshots=pd.DataFrame(records,columns=['loan_id','month','ead','dpd','dpd_bucket'])
    return accounts,snapshots


def validate(accounts,snapshots):
    assert accounts.loan_id.is_unique
    assert not snapshots.duplicated(['loan_id','month']).any()
    assert snapshots.ead.ge(0).all()
    assert snapshots.dpd.isin([0,30,60,90]).all()
    assert snapshots.loan_id.isin(accounts.loan_id).all()
    assert snapshots.groupby('loan_id').month.nunique().eq(12).all()


def analyze(accounts,snapshots):
    joined=snapshots.merge(accounts,on='loan_id',validate='many_to_one')
    joined['ecl_12m_illustrative']=joined.ead*joined.pd_12m_assumed*joined.lgd_assumed
    joined['delinq_ead']=np.where(joined.dpd>=30,joined.ead,0)
    joined['severe_ead']=np.where(joined.dpd>=90,joined.ead,0)
    monthly=joined.groupby('month',as_index=False).agg(exposure=('ead','sum'),delinquent_ead=('delinq_ead','sum'),severe_ead=('severe_ead','sum'),illustrative_ecl=('ecl_12m_illustrative','sum'),loans=('loan_id','nunique'))
    monthly['dq30_pct']=monthly.delinquent_ead/monthly.exposure*100
    monthly['dq90_pct']=monthly.severe_ead/monthly.exposure*100
    latest=joined[joined.month==joined.month.max()].copy()
    segments=latest.groupby('segment',as_index=False).agg(exposure=('ead','sum'),delinquent_ead=('delinq_ead','sum'),ecl=('ecl_12m_illustrative','sum'),accounts=('loan_id','nunique'))
    segments['dq30_pct']=segments.delinquent_ead/segments.exposure*100
    ordered=['Prime','Near-prime','Subprime']
    segments['segment']=pd.Categorical(segments['segment'],ordered,ordered=True)
    segments=segments.sort_values('segment')
    trans=joined.sort_values(['loan_id','month']).copy()
    trans['next_bucket']=trans.groupby('loan_id').dpd_bucket.shift(-1)
    transitions=trans.dropna(subset=['next_bucket']).groupby(['dpd_bucket','next_bucket'],observed=True).size().unstack(fill_value=0)
    buckets=['Current','30-59','60-89','90+']
    transitions=transitions.reindex(index=buckets,columns=buckets,fill_value=0)
    roll=transitions.div(transitions.sum(axis=1),axis=0)*100
    return monthly,segments,roll,latest


def make_dashboard(monthly, segments,roll, latest):
    navy='#182B42'; blue='#316B9B'; orange='#D38B52'; ink='#182B42'; gray='#64748B'
    last=monthly.iloc[-1]
    headline=(f"{last.exposure/1e6:,.1f}M",f"{last.dq30_pct:.1f}%",f"{last.illustrative_ecl/1e6:,.2f}M")
    fig=make_subplots(rows=2,cols=2,subplot_titles=['Delinquency trend (exposure weighted)','Exposure by risk segment','Roll rates between monthly buckets','Illustrative ECL by segment'],specs=[[{'type':'xy'},{'type':'xy'}],[{'type':'heatmap'},{'type':'xy'}]],horizontal_spacing=.15,vertical_spacing=.22)
    fig.add_trace(go.Scatter(x=monthly.month,y=monthly.dq30_pct,name='30+ DPD',line={'color':blue,'width':3},mode='lines+markers',hovertemplate='%{x}<br>%{y:.2f}%<extra></extra>'),row=1,col=1)
    fig.add_trace(go.Scatter(x=monthly.month,y=monthly.dq90_pct,name='90+ DPD',line={'color':orange,'width':2},mode='lines',hovertemplate='%{x}<br>%{y:.2f}%<extra></extra>'),row=1,col=1)
    fig.add_trace(go.Bar(x=segments.segment.astype(str),y=segments.exposure/1e6,marker_color=[navy,blue,orange],showlegend=False,hovertemplate='%{x}<br>%{y:.1f}M<extra></extra>'),row=1,col=2)
    fig.add_trace(go.Heatmap(x=roll.columns.tolist(),y=roll.index.tolist(),z=roll.to_numpy(),colorscale=[[0,'#F1F5F9'],[.5,'#98B6D0'],[1,navy]],zmin=0,zmax=100,text=np.round(roll.to_numpy(),1),texttemplate='%{text:.1f}%',hovertemplate='%{y} → %{x}: %{z:.1f}%<extra></extra>',showscale=False),row=2,col=1)
    fig.add_trace(go.Bar(x=segments.segment.astype(str),y=segments.ecl/1e6,marker_color=[navy,blue,orange],showlegend=False,hovertemplate='%{x}<br>%{y:.2f}M<extra></extra>'),row=2,col=2)
    fig.update_layout(height=760,margin={'l':55,'r':35,'t':75,'b':45},plot_bgcolor='white',paper_bgcolor='white',font={'family':'Arial','color':ink,'size':12},legend={'orientation':'h','y':1.12,'x':0},title={'text':'PORTFOLIO RISK | Analyst view','x':.045,'font':{'size':18,'color':navy}})
    fig.update_xaxes(showgrid=False,linecolor='#E5EAF0');fig.update_yaxes(gridcolor='#E5EAF0',zeroline=False)
    fig.update_yaxes(title_text='Delinquent EAD (%)',row=1,col=1);fig.update_yaxes(title_text='Exposure (M synthetic units)',row=1,col=2);fig.update_yaxes(title_text='ECL proxy (M)',row=2,col=2)
    content=fig.to_html(full_html=False,include_plotlyjs=True,config={'displaylogo':False,'responsive':True})
    metrics=''.join(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>' for label,value in zip(['Exposure','30+ DPD · EAD weighted','ECL proxy · not IFRS 9'],headline))
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portfolio Risk | Executive Review</title><style>body{{margin:0;background:#F3F6FA;color:#182B42;font:14px Arial,sans-serif}}.wrap{{max-width:1250px;margin:36px auto;padding:0 22px}}header{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #DDE5EF;padding-bottom:22px}}h1{{font-size:30px;margin:8px 0;font-weight:600}}.eyebrow{{font-size:11px;letter-spacing:2px;color:#55708D;font-weight:bold}}.period{{color:#64748B}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}}.metric{{background:white;padding:24px;border:1px solid #E1E7F0;border-radius:7px}}.metric-label{{font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:#66788A}}.metric-value{{font-size:32px;font-weight:600;margin-top:13px;color:#182B42}}.panel{{background:white;border:1px solid #E1E7F0;border-radius:7px;padding:6px}}.foot{{line-height:1.65;color:#576879;font-size:12px;margin-top:16px}}@media(max-width:700px){{.metrics{{grid-template-columns:1fr}}h1{{font-size:22px}}}}</style></head><body><div class="wrap"><header><div><div class="eyebrow">RISK ANALYTICS / PORTFOLIO MONITORING</div><h1>Portfolio Risk Overview</h1></div><div class="period">Synthetic portfolio · January–December 2025</div></header><div class="metrics">{metrics}</div><div class="panel">{content}</div><div class="foot"><b>Interpretation:</b> Observed synthetic 30+ DPD trends and risk-segment distribution; differences are scenario-dependent and not evidence about real lenders. <b>Definitions:</b> EAD = simulated outstanding balance. 30+ DPD = EAD share with 30 or more days past due. Roll rate = share of accounts transitioning between consecutive monthly delinquency buckets. ECL proxy = EAD × assumed 12-month PD × assumed LGD; not compliant IFRS 9 ECL. No real customer data.</div></div></body></html>'''
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/'dashboard.html').write_text(html,encoding='utf8')
    fig.write_image(REPORTS/'dashboard_charts.png',width=1280,height=760,scale=1) if _has_kaleido() else None


def _has_kaleido():
    try: import kaleido; return True
    except ImportError: return False


def main():
    DATA.mkdir(exist_ok=True);REPORTS.mkdir(exist_ok=True)
    accounts,snapshots=generate();validate(accounts,snapshots)
    accounts.to_csv(DATA/'loans_synthetic.csv',index=False)
    snapshots.to_csv(DATA/'monthly_snapshots_synthetic.csv',index=False)
    with sqlite3.connect(DATA/'portfolio.sqlite') as con:
        accounts.to_sql('loans',con,if_exists='replace',index=False)
        snapshots.to_sql('snapshots',con,if_exists='replace',index=False)
    monthly,segments,roll,latest=analyze(accounts,snapshots)
    monthly.to_csv(REPORTS/'monthly_kpis.csv',index=False)
    segments.to_csv(REPORTS/'segment_kpis.csv',index=False)
    roll.to_csv(REPORTS/'roll_rates.csv')
    make_dashboard(monthly,segments,roll,latest)
    print(f'Generated {len(accounts):,} synthetic loans and {len(snapshots):,} monthly records')
    print(f'Latest period: {monthly.month.iloc[-1]}, 30+ DPD: {monthly.dq30_pct.iloc[-1]:.2f}%, ECL proxy: {monthly.illustrative_ecl.iloc[-1]:,.0f}')
    print(f'Open report: {REPORTS / "dashboard.html"}')

if __name__=='__main__': main()
