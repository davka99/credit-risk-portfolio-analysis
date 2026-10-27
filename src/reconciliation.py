"""Reconcile the existing portfolio analysis with exported model DAX results."""
from __future__ import annotations
import argparse
import csv
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from src import pipeline

ROOT = Path(__file__).resolve().parents[1]
METRICS = ('total_ead', 'dpd30_rate', 'dpd90_rate', 'ecl_proxy')
MONTHS = tuple(f'2025-{i:02}' for i in range(1, 13))
SEGMENTS = ('Prime', 'Near-prime', 'Subprime')
TOLERANCE = {'total_ead': 0.01, 'dpd30_rate': 1e-8, 'dpd90_rate': 1e-8, 'ecl_proxy': 0.01}

class ReconciliationError(ValueError):
    pass

def expected_results(data_dir=ROOT / 'data'):
    loans = pd.read_csv(data_dir / 'loans_synthetic.csv')
    snapshots = pd.read_csv(data_dir / 'monthly_snapshots_synthetic.csv', dtype={'month': str})
    required_loans = ['loan_id', 'segment', 'pd_12m_assumed', 'lgd_assumed']
    required_snap = ['loan_id', 'month', 'ead', 'dpd', 'dpd_bucket']
    for name, frame, cols in [('loans', loans, required_loans), ('snapshots', snapshots, required_snap)]:
        missing = set(cols) - set(frame.columns)
        if missing: raise ReconciliationError(f'{name}: saknade kolumner {sorted(missing)}')
        if frame[cols].isna().any().any(): raise ReconciliationError(f'{name}: tomma obligatoriska värden')
    if loans.loan_id.duplicated().any(): raise ReconciliationError('Dubbla loan_id i lån')
    if snapshots.duplicated(['loan_id', 'month']).any(): raise ReconciliationError('Dubbla observationer per lån och månad')
    if set(snapshots.loan_id) != set(loans.loan_id): raise ReconciliationError('Lån och observationer har olika nycklar')
    if set(snapshots.month) != set(MONTHS): raise ReconciliationError('Månaderna motsvarar inte januari–december 2025')
    if set(loans.segment) != set(SEGMENTS): raise ReconciliationError('Oväntade eller saknade risksegment')
    if not snapshots.groupby('loan_id').month.nunique().eq(12).all(): raise ReconciliationError('Varje lån måste ha 12 månader')
    for name, series in [('ead',snapshots.ead),('dpd',snapshots.dpd),('pd_12m_assumed',loans.pd_12m_assumed),('lgd_assumed',loans.lgd_assumed)]:
        try: numbers = pd.to_numeric(series, errors='raise')
        except (ValueError, TypeError) as exc: raise ReconciliationError(f'{name}: ogiltigt tal') from exc
        if not np.isfinite(numbers).all(): raise ReconciliationError(f'{name}: icke-ändligt tal')
    if (snapshots.ead < 0).any() or not snapshots.dpd.isin([0,30,60,90]).all(): raise ReconciliationError('Ogiltig ead eller dpd')
    if not loans.pd_12m_assumed.between(0,1).all() or not loans.lgd_assumed.between(0,1).all(): raise ReconciliationError('PD/LGD utanför intervallet 0–1')
    def build(accounts, facts, segment=None):
        monthly, _, _, _ = pipeline.analyze(accounts, facts)
        counts = facts.groupby('month')['dpd'].apply(lambda values: int((values >= 90).sum()))
        result = []
        for row in monthly.itertuples(index=False):
            item = {'month': str(row.month), 'total_ead': float(row.exposure),
                    'dpd30_rate': float(row.dq30_pct) / 100, 'dpd90_rate': float(row.dq90_pct) / 100,
                    'ecl_proxy': float(row.illustrative_ecl)}
            item['_dpd90_count'] = int(counts.loc[row.month])
            if segment is not None: item['segment'] = segment
            if not all(math.isfinite(item[m]) for m in METRICS): raise ReconciliationError('Ogiltigt KPI-resultat, kontrollera exponeringen')
            result.append(item)
        return result
    monthly = build(loans, snapshots)
    segment_rows = []
    for segment in SEGMENTS:
        sub = loans[loans.segment == segment]
        segment_rows.extend(build(sub, snapshots[snapshots.loan_id.isin(sub.loan_id)], segment))
    return monthly, segment_rows

def load_export(path, keys):
    path=Path(path)
    text=path.read_text(encoding='utf-8-sig')
    if not text.strip(): raise ReconciliationError(f'{path}: tom fil')
    delimiter='\t' if '\t' in text.splitlines()[0] else ','
    reader=csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames: raise ReconciliationError('Saknar kolumnrubriker')
    headers=[x.strip().strip('[]').strip().lower() for x in reader.fieldnames]
    if len(headers)!=len(set(headers)): raise ReconciliationError('Dubbla kolumnrubriker')
    wanted=set(keys+METRICS)
    if set(headers)!=wanted: raise ReconciliationError(f'Fel kolumner: förväntar {sorted(wanted)}, fick {sorted(headers)}')
    output=[]
    for n, raw in enumerate(reader,2):
        if None in raw or any(v is None for v in raw.values()): raise ReconciliationError(f'Rad {n}: fel antal kolumner')
        row={headers[i]:raw[name].strip() for i,name in enumerate(reader.fieldnames)}
        for key in keys:
            if not row[key]: raise ReconciliationError(f'Rad {n}: tom nyckel {key}')
        for metric in METRICS:
            if row[metric] == '' and metric == 'dpd90_rate':
                row[metric] = None
                continue
            try: row[metric]=float(row[metric])
            except ValueError as exc: raise ReconciliationError(f'Rad {n}: ogiltigt tal för {metric}') from exc
            if not math.isfinite(row[metric]): raise ReconciliationError(f'Rad {n}: icke-ändligt tal för {metric}')
        output.append(row)
    return output

def compare(expected, actual, keys, normalized=None):
    def index(rows, label):
        out={}
        for row in rows:
            key=tuple(row[k] for k in keys)
            if any(not x for x in key): raise ReconciliationError(f'{label}: tom nyckel {key}')
            if key in out: raise ReconciliationError(f'{label}: dubbel nyckel {key}')
            out[key]=row
        return out
    exp=index(expected,'Python'); act=index(actual,'DAX')
    issues=[]
    for key in sorted(exp.keys()-act.keys()): issues.append(f'saknas i DAX: {key}')
    for key in sorted(act.keys()-exp.keys()): issues.append(f'extra i DAX: {key}')
    for key in sorted(exp.keys() & act.keys()):
        for metric in METRICS:
            actual_value=act[key][metric]
            if actual_value is None:
                # A blank is allowed only for 90+ on a month/segment row with
                # independently observed zero 90+ cases and positive exposure.
                other_metrics = ('total_ead', 'dpd30_rate', 'ecl_proxy')
                supported = (
                    metric == 'dpd90_rate' and keys == ('month', 'segment')
                    and exp[key].get('_dpd90_count') == 0
                    and exp[key]['dpd90_rate'] == 0.0
                    and exp[key]['total_ead'] > 0
                    and all(isinstance(act[key].get(m), (int, float))
                            and math.isfinite(act[key][m])
                            and abs(exp[key][m] - act[key][m]) <= TOLERANCE[m]
                            for m in other_metrics)
                    and act[key]['total_ead'] > 0
                )
                if not supported:
                    issues.append(f'{key} {metric}: tomt värde saknar stöd för noll')
                    continue
                actual_value = 0.0
                if normalized is not None: normalized.append((key, metric))
            if not math.isfinite(actual_value): issues.append(f'{key} {metric}: icke-ändligt DAX-värde'); continue
            diff=abs(exp[key][metric]-actual_value)
            if diff > TOLERANCE[metric]: issues.append(f'{key} {metric}: Python={exp[key][metric]:.12g}, DAX={actual_value:.12g}, diff={diff:.12g}, tolerans={TOLERANCE[metric]}')
    return issues

def main(argv=None):
    p=argparse.ArgumentParser(description='Jämför verklig DAX-export med Python-pipelinen')
    p.add_argument('--monthly',required=True,help='TSV/CSV från monthly.dax')
    p.add_argument('--month-segment',required=True,help='TSV/CSV från month_segment.dax')
    args=p.parse_args(argv)
    try:
        monthly,segments=expected_results()
        monthly_export = load_export(args.monthly, ('month',))
        segment_export = load_export(args.month_segment, ('month','segment'))
        normalized = []
        issues = compare(monthly, monthly_export, ('month',))
        issues += compare(segments, segment_export, ('month','segment'), normalized)
    except (ReconciliationError,OSError,ValueError) as exc:
        print(f'FEL: {exc}',file=sys.stderr);return 2
    if issues:
        print('\n'.join(issues));print(f'UNDERKÄNT: {len(issues)} avvikelser');return 1
    print('GODKÄNT: 12 månader och 36 månad–segment-rader, totalt 192 KPI-värden jämförda.')
    if normalized:
        for key, metric in normalized:
            print(f'VILLKORAD NORMALISERING: {key} {metric} tomt till 0; positiv EAD och inga 90+-rader i Python-data; övriga KPI matchar.')
        print('Skriptet kan inte själv verifiera DAX-BLANK, exporternas ursprung eller datalikhet; se QA-dokumentationen.')
    print('Förutsätter att exporterna kommer från den aktuella modellen och de aktuella CSV-filerna.')
    return 0
if __name__ == '__main__': raise SystemExit(main())
