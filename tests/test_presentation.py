"""Static presentation checks; Power BI rendering must be checked separately."""
import json
import re
from src.reconciliation import ROOT
PAGES=ROOT/'powerbi/CreditRisk.Report/definition/pages'
P1=PAGES/'da7835d4cdf6b772b137/visuals'
P2=PAGES/'a42de11a9ce045d7b912/visuals'
def visual(folder, ident):return json.loads((folder/ident/'visual.json').read_text(encoding='utf8'))['visual']
def value(x):return x['expr']['Literal']['Value']

def test_donut_two_decimal_share_and_no_clipped_center():
    o=visual(P2,'43e2721647c5fd2efc95')['objects']
    assert value(o['centerValue'][0]['properties']['show'])=='false'
    assert value(o['labels'][0]['properties']['percentageLabelPrecision'])=='2L'
    assert value(o['labels'][0]['properties']['labelPrecision'])=='2L'

def test_percent_chart_labels_and_axes_use_two_decimals():
    for folder,ident in [(P1,'583045b7d52f6f300001'),(P1,'f457a64e5044e692c0f5'),(P2,'7e68e1721fb5ac549398'),(P2,'12fa327cb0f9e84e9db4')]:
        o=visual(folder,ident)['objects']
        assert value(o['labels'][0]['properties']['labelPrecision'])=='2L'
        assert value(o['valueAxis'][0]['properties']['labelPrecision'])=='2L'

def test_amount_cards_are_explicitly_in_millions():
    for folder,ident in [(P1,'25298adc65a53399b071'),(P1,'09dd0e5e4094d86e7a56'),(P2,'09c28d5815856deb5332')]:
        v=visual(folder,ident);props=v['objects']['value'][0]['properties']
        assert value(props['labelDisplayUnits'])=='1000000D'
        assert value(props['labelPrecision'])=='2L'
        assert 'millions' in value(v['visualContainerObjects']['title'][0]['properties']['text'])

def test_percent_tooltip_measures_retain_two_digit_format():
    s=(ROOT/'powerbi/CreditRisk.SemanticModel/definition/tables/MonthlySnapshots.tmdl').read_text(encoding='utf8')
    for name in ('DPD 90+ Rate | Presentation','DPD 30+ Rate | Latest Month','DPD 90+ Rate | Latest Month','EAD Share by DPD Category | Latest'):
        chunk=s.split("\tmeasure '"+name+"' =",1)[1].split('\n\tmeasure ',1)[0]
        assert 'formatString: 0.00%;-0.00%;0.00%' in chunk

def test_chart_subtitles_and_measure_aliases_are_business_friendly():
    for folder,ident in [(P1,'583045b7d52f6f300001'),(P1,'f457a64e5044e692c0f5'),(P2,'7e68e1721fb5ac549398'),(P2,'12fa327cb0f9e84e9db4'),(P2,'43e2721647c5fd2efc95'),(P2,'c0000000000000000002')]:
        v=visual(folder,ident);sub=v['visualContainerObjects']['subTitle'][0]['properties']
        assert value(sub['show'])=='true'
        assert len(value(sub['text']))>5
        for role in v['query']['queryState'].values():
            for projection in role['projections']:
                if projection['queryRef'].startswith('MonthlySnapshots.') and 'Measure' in projection['field']:
                    assert projection.get('displayName')

def test_qa_table_still_retains_four_decimals():
    text=(ROOT/'docs/VALIDATION.md').read_text(encoding='utf8')
    assert '92.4516%' in text and '3.4136%' in text
