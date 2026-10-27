"""Static report checks and independent CSV QA; these do not execute DAX."""
import json
import pandas as pd
import pytest
from src.reconciliation import ROOT
from src.page2_reference import snapshot_reference

DATA=ROOT/'data'
PAGE=ROOT/'powerbi/CreditRisk.Report/definition/pages/a42de11a9ce045d7b912'

@pytest.fixture(scope='module')
def source():
    loans=pd.read_csv(DATA/'loans_synthetic.csv')
    snapshots=pd.read_csv(DATA/'monthly_snapshots_synthetic.csv',dtype={'month':str})
    return loans,snapshots

def test_input_grain_and_dpd_bucket_consistency(source):
    loans,facts=source
    assert loans.loan_id.is_unique
    assert not facts.duplicated(['loan_id','month']).any()
    assert set(facts.loan_id)==set(loans.loan_id)
    expected={0:'Current',30:'30-59',60:'60-89',90:'90+'}
    assert facts.dpd.isin(expected).all()
    assert (facts.dpd.map(expected)==facts.dpd_bucket).all()
    assert len(facts)==19200

def test_filtered_bucket_and_segment_sums_without_duplicate_exposure(source):
    loans,facts=source
    joined=facts.merge(loans,on='loan_id',validate='many_to_one')
    assert len(joined)==len(facts)
    for month in sorted(joined.month.unique()):
        for segment in [None,'Prime','Near-prime','Subprime']:
            for product in [None,'Personal loan','Auto loan']:
                mask=joined.month.eq(month)
                if segment is not None:mask &= joined.segment.eq(segment)
                if product is not None:mask &= joined['product'].eq(product)
                frame=joined[mask]
                result=snapshot_reference(months=[month],segments=[segment] if segment else None,products=[product] if product else None)
                assert result is not None
                expected=frame.ead.sum()
                assert result['ead']==pytest.approx(expected,abs=0.01)
                assert sum(result['bucket_ead'].values())==pytest.approx(expected,abs=0.01)
                assert sum(result['segment_ead'].values())==pytest.approx(expected,abs=0.01)

def test_disconnected_months_use_discrete_columns():
    file=PAGE/'visuals/7e68e1721fb5ac549398/visual.json'
    visual=json.loads(file.read_text(encoding='utf8'))['visual']
    title=visual['visualContainerObjects']['title'][0]['properties']['text']['expr']['Literal']['Value']
    assert 'selected months' in title
    assert visual['visualType']=='clusteredColumnChart'
    assert visual['query']['queryState']['Category']['projections'][0]['queryRef']=='MonthlySnapshots.month'
    selection=snapshot_reference(months=['2025-01','2025-12'])
    assert selection['month']=='2025-12'

def test_kpi_formats_and_synthetic_label():
    table=(ROOT/'powerbi/CreditRisk.SemanticModel/definition/tables/MonthlySnapshots.tmdl').read_text(encoding='utf8')
    for name in ('DPD 30+ Rate | Latest Month','DPD 90+ Rate | Latest Month'):
        start=table.index("\tmeasure '"+name+"' =")
        measure=table[start:table.index('\n\tmeasure ',start+1)]
        assert 'formatString: 0.00%;-0.00%;0.00%' in measure
    visual=json.loads((PAGE/'visuals/6767291036aebd30634f/visual.json').read_text(encoding='utf8'))
    assert 'SYNTHETIC DATA ONLY' in json.dumps(visual).upper()
    assert 'percentage points' in json.dumps(visual)
