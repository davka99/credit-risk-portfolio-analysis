"""Checks for report pedagogy and presentation reference data, not a DAX engine."""
import json
import re
import pandas as pd
import pytest
from src.reconciliation import ROOT
from src.page2_reference import snapshot_reference

PAGES=ROOT/'powerbi/CreditRisk.Report/definition/pages'
P1=PAGES/'da7835d4cdf6b772b137'
P2=PAGES/'a42de11a9ce045d7b912'

def load(page,name):
    return json.loads((page/'visuals'/name/'visual.json').read_text(encoding='utf8'))

def test_bucket_values_and_december_portfolio_share():
    data=pd.read_csv(ROOT/'data/monthly_snapshots_synthetic.csv')
    mapping={0:'Current',30:'30-59',60:'60-89',90:'90+'}
    assert set(data.dpd)==set(mapping)
    assert (data.dpd.map(mapping)==data.dpd_bucket).all()
    assert set(data.loc[data.dpd_bucket.eq('Current'),'dpd'])=={0}
    v=snapshot_reference(months=['2025-12']);b=v['bucket_ead'];total=v['ead']
    assert b==pytest.approx({'Current':144219580.26,'30-59':3836227.13,'60-89':2613820.74,'90+':5325097.36},abs=0.01)
    assert sum(b.values())==pytest.approx(total,abs=0.01)
    assert sum(x/total for x in b.values())==pytest.approx(1,abs=1e-12)
    assert sum(b[k] for k in ('30-59','60-89','90+'))==pytest.approx(11775145.23,abs=0.01)
    assert sum(b[k] for k in ('30-59','60-89','90+'))/total==pytest.approx(v['rate30'],abs=1e-12)

def test_both_pages_and_standalone_column_charts():
    meta=json.loads((PAGES/'pages.json').read_text(encoding='utf8'))
    assert 'da7835d4cdf6b772b137' in meta['pageOrder'] and 'a42de11a9ce045d7b912' in meta['pageOrder']
    for page,id in [(P1,'583045b7d52f6f300001'),(P2,'7e68e1721fb5ac549398')]:
        v=load(page,id)['visual']
        assert v['visualType']=='clusteredColumnChart'
        assert {p['queryRef'] for p in v['query']['queryState']['Y']['projections']}=={'MonthlySnapshots.DPD 30+ Rate','MonthlySnapshots.DPD 90+ Rate | Presentation'}

def test_bucket_visuals_separate_mix_and_delayed_exposure():
    mix=load(P2,'43e2721647c5fd2efc95')['visual']; delayed=load(P2,'c0000000000000000002')['visual']
    assert mix['visualType']=='donutChart' and delayed['visualType']=='clusteredBarChart'
    for v in (mix,delayed):
        roles=v['query']['queryState']
        assert roles['Category']['projections'][0]['queryRef']=='MonthlySnapshots.DPD Category'
        assert roles['Tooltips']['projections'][0]['queryRef']=='MonthlySnapshots.EAD Share by DPD Category | Latest'
    assert mix['query']['queryState']['Y']['projections'][0]['queryRef']=='MonthlySnapshots.EAD by DPD Category | Latest'
    assert delayed['query']['queryState']['Y']['projections'][0]['queryRef']=='MonthlySnapshots.Delinquent EAD by Category | Latest'

def test_presentation_model_avoids_original_measure_changes():
    s=(ROOT/'powerbi/CreditRisk.SemanticModel/definition/tables/MonthlySnapshots.tmdl').read_text(encoding='utf8')
    assert "column 'DPD Category' = SWITCH(MonthlySnapshots[dpd_bucket]" in s
    for label in ('0 DPD','30-59 DPD','60-89 DPD','90+ DPD'):assert '"'+label+'"' in s
    assert 'REMOVEFILTERS(MonthlySnapshots[DPD Category])' in s
    assert "measure 'DPD 90+ Rate | Presentation' = [DPD 90+ Rate]" in s
    assert 'BucketName IN {"30-59 DPD", "60-89 DPD", "90+ DPD"}' in s

def test_visible_synthetic_definitions_and_segment_colors():
    text=json.dumps(load(P1,'c0000000000000000001'))+json.dumps(load(P2,'6767291036aebd30634f'))
    for phrase in ('EAD','DPD','30+','90+','Subprime','SYNTHETIC DATA','percentage points'):
        assert phrase.lower() in text.lower()
    segment=load(P2,'12fa327cb0f9e84e9db4')
    content=json.dumps(segment)
    for color in ('#182B42','#316B9B','#D38B52'):assert color in content
