import json
import re
from pathlib import Path
import pandas as pd
import pytest
from src.page2_reference import snapshot_reference
from src.reconciliation import ROOT

PAGE='a42de11a9ce045d7b912'
PAGES=ROOT/'powerbi/CreditRisk.Report/definition/pages'

def test_snapshot_latest_month_and_not_multimonth_sum():
    jan=snapshot_reference(months=['2025-01'])
    selected=snapshot_reference(months=['2025-01','2025-12'])
    dec=snapshot_reference(months=['2025-12'])
    assert jan['month']=='2025-01' and jan['change30_pp'] is None
    assert selected['month']=='2025-12'
    assert selected['ead']==pytest.approx(155994725.49,abs=0.01)
    assert selected['ead']==pytest.approx(dec['ead'])
    assert selected['ead']!=pytest.approx(jan['ead']+dec['ead'])

def test_mom_uses_prior_calendar_month_outside_selection():
    latest=snapshot_reference(months=['2025-12'])
    assert latest['rate30']==pytest.approx(0.07548425238746193,abs=1e-12)
    assert latest['rate90']==pytest.approx(0.03413639367147297,abs=1e-12)
    assert latest['change30_pp']==pytest.approx(7.5484252387461925-7.4115856022892395,abs=1e-9)
    assert snapshot_reference(months=['2025-01'])['change30_pp'] is None

def test_risk_segment_blank90_zero_with_positive_exposure():
    v=snapshot_reference(months=['2025-01'],segments=['Subprime'])
    assert v['ead']==pytest.approx(26582264.30,abs=0.01)
    assert v['rate90']==0
    assert v['change30_pp'] is None

def test_filters_bucket_and_reference_grain():
    v=snapshot_reference(months=['2025-01','2025-12'],segments=['Prime','Subprime'],products=['Auto loan'])
    assert v['month']=='2025-12'
    assert set(v['segment_ead']) <= {'Prime','Subprime'}
    assert sum(v['bucket_ead'].values())==pytest.approx(v['ead'],abs=0.01)
    loans=pd.read_csv(ROOT/'data/loans_synthetic.csv')
    facts=pd.read_csv(ROOT/'data/monthly_snapshots_synthetic.csv')
    sub=loans[loans.segment.isin(['Prime','Subprime']) & (loans['product']=='Auto loan')]
    expected=facts[(facts['month']=='2025-12') & facts.loan_id.isin(sub.loan_id)].ead.sum()
    assert v['ead']==pytest.approx(expected,abs=0.01)
    assert snapshot_reference(months=['2030-01']) is None

def test_page_structure_positions_and_bindings():
    meta=json.loads((PAGES/'pages.json').read_text(encoding='utf8'))
    assert meta['pageOrder']==['da7835d4cdf6b772b137',PAGE]
    page=json.loads((PAGES/PAGE/'page.json').read_text(encoding='utf8'))
    assert page['name']==PAGE and page['displayName']=='Delinquency & Portfolio Analysis'
    docs=[]
    for file in (PAGES/PAGE/'visuals').glob('*/visual.json'):
        v=json.loads(file.read_text(encoding='utf8'));assert v['name']==file.parent.name
        assert re.fullmatch(r'[a-f0-9]{20}',v['name'])
        p=v['position']; assert 0<=p['x'] and 0<=p['y'] and p['x']+p['width']<=page['width'] and p['y']+p['height']<=page['height']
        docs.append(v)
    assert len(docs)==14 and len({v['name'] for v in docs})==14
    types=[v['visual']['visualType'] for v in docs]
    assert types.count('cardVisual')==5 and types.count('slicer')==3 and types.count('clusteredColumnChart')==1 and types.count('clusteredBarChart')==2 and types.count('donutChart')==1
    slicers=[v for v in docs if v['visual']['visualType']=='slicer']
    fields={p['queryRef'] for v in slicers for p in v['visual']['query']['queryState']['Values']['projections']}
    assert fields=={'MonthlySnapshots.month','Loans.segment','Loans.product'}
    trends=[v for v in docs if v['visual']['visualType']=='clusteredColumnChart']
    y=trends[0]['visual']['query']['queryState']['Y']['projections']
    assert {p['queryRef'] for p in y}=={'MonthlySnapshots.DPD 30+ Rate','MonthlySnapshots.DPD 90+ Rate | Presentation'}
    assert 'SYNTHETIC DATA' in json.dumps(docs).upper()

def test_model_measure_bindings_and_source_preserved():
    table=(ROOT/'powerbi/CreditRisk.SemanticModel/definition/tables/MonthlySnapshots.tmdl').read_text(encoding='utf8')
    names=re.findall(r"^\tmeasure '([^']+)'",table,re.MULTILINE)
    for name in ['Analysis Latest Month','Analysis Month Label','Total EAD | Latest Month','DPD 30+ Rate | Latest Month','DPD 90+ Rate | Latest Month','DPD 30+ Change MoM pp']:
        assert names.count(name)==1
    assert 'ALLSELECTED(Loans[segment])' in table
    assert 'REMOVEFILTERS(MonthlySnapshots[dpd_bucket])' in table
    assert 'EDATE(SelectedMonth, -1)' in table
    assert 'REMOVEFILTERS(MonthlySnapshots[month])' in table
    for file in (PAGES/PAGE/'visuals').glob('*/visual.json'):
        v=json.loads(file.read_text(encoding='utf8'))
        for role in v['visual'].get('query',{}).get('queryState',{}).values():
            for p in role['projections']:
                f=p['field']
                if 'Measure' in f:
                    assert f['Measure']['Property'] in names
    assert 'File.Contents(Text.TrimEnd(DataFolderPath' in table


# A focused list, not an exhaustive parser or registry of all DAX keywords.
DAX_MOM_RESERVED_NAMES = frozenset({
    'PREVIOUSMONTH', 'EDATE', 'CALCULATE', 'REMOVEFILTERS', 'MAX',
    'ALLSELECTED', 'IF', 'ISBLANK', 'BLANK', 'COALESCE', 'RETURN', 'VAR',
})

def dax_variable_conflicts(expression):
    variables = re.findall(r"(?i)\bVAR\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", expression)
    return {name for name in variables if name.upper() in DAX_MOM_RESERVED_NAMES}

def test_mom_variable_names_do_not_collide_with_dax_functions():
    table = (ROOT/'powerbi/CreditRisk.SemanticModel/definition/tables/MonthlySnapshots.tmdl').read_text(encoding='utf8')
    start = table.index("\tmeasure 'DPD 30+ Change MoM pp' =")
    end = table.index('\n\tcolumn loan_id', start)
    measure = table[start:end]
    assert dax_variable_conflicts(measure) == set()
    assert dax_variable_conflicts('VAR PreviousMonth = 1 RETURN PreviousMonth') == {'PreviousMonth'}
    assert dax_variable_conflicts('VAR previousmonth = 1 RETURN previousmonth') == {'previousmonth'}
    assert 'VAR PriorMonthDate = EDATE(SelectedMonth, -1)' in measure
    assert measure.count('MonthlySnapshots[month] = PriorMonthDate') == 2
    assert '100 * (CurrentRate - COALESCE(PreviousRate, 0))' in measure
