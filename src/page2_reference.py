"""Independent numerical reference for page 2 snapshot and prior-month semantics."""
from pathlib import Path
import pandas as pd
from src.reconciliation import ROOT

def snapshot_reference(months=None, segments=None, products=None, data_dir=ROOT / 'data'):
    loans=pd.read_csv(data_dir/'loans_synthetic.csv')
    facts=pd.read_csv(data_dir/'monthly_snapshots_synthetic.csv',dtype={'month':str})
    if segments is not None: loans=loans[loans.segment.isin(segments)]
    if products is not None: loans=loans[loans['product'].isin(products)]
    joined=facts.merge(loans,on='loan_id',validate='many_to_one')
    selected=joined if months is None else joined[joined.month.isin(months)]
    if selected.empty: return None
    latest=selected.month.max(); current=joined[joined.month.eq(latest)]
    previous=str(pd.Period(latest,freq='M')-1); prior=joined[joined.month.eq(previous)]
    def metrics(frame):
        ead=float(frame.ead.sum())
        if ead<=0:return (ead,None,None)
        return ead,float(frame.loc[frame.dpd.ge(30),'ead'].sum())/ead,float(frame.loc[frame.dpd.ge(90),'ead'].sum())/ead
    ead,r30,r90=metrics(current); _,p30,_=metrics(prior)
    return {'month':latest,'ead':ead,'rate30':r30,'rate90':r90,'change30_pp':None if r30 is None or p30 is None else 100*(r30-p30),
            'segment_ead':current.groupby('segment',observed=True).ead.sum().to_dict(),
            'bucket_ead':current.groupby('dpd_bucket',observed=True).ead.sum().to_dict()}
