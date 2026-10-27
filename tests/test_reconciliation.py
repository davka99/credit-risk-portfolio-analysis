import csv
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from src import reconciliation as rec

class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monthly,cls.segments=rec.expected_results()

    def test_full_coverage(self):
        self.assertEqual(len(self.monthly),12)
        self.assertEqual(len(self.segments),36)
        self.assertEqual({r['month'] for r in self.monthly},set(rec.MONTHS))
        self.assertEqual({(r['month'],r['segment']) for r in self.segments},set((m,s) for m in rec.MONTHS for s in rec.SEGMENTS))

    def test_monthly_against_existing_python_report(self):
        with (rec.ROOT/'reference/monthly_kpis.csv').open(newline='',encoding='utf-8-sig') as f:
            rows={r['month']:r for r in csv.DictReader(f)}
        for r in self.monthly:
            x=rows[r['month']]
            self.assertAlmostEqual(r['total_ead'],float(x['exposure']),places=5)
            self.assertAlmostEqual(r['dpd30_rate'],float(x['dq30_pct'])/100,places=12)
            self.assertAlmostEqual(r['dpd90_rate'],float(x['dq90_pct'])/100,places=12)
            self.assertAlmostEqual(r['ecl_proxy'],float(x['illustrative_ecl']),places=6)

    def test_december_segment_against_existing_python_report(self):
        with (rec.ROOT/'reference/segment_kpis.csv').open(newline='',encoding='utf-8-sig') as f:
            rows={r['segment']:r for r in csv.DictReader(f)}
        for r in (x for x in self.segments if x['month']=='2025-12'):
            x=rows[r['segment']]
            self.assertAlmostEqual(r['total_ead'],float(x['exposure']),places=5)
            self.assertAlmostEqual(r['dpd30_rate'],float(x['dq30_pct'])/100,places=12)
            self.assertAlmostEqual(r['ecl_proxy'],float(x['ecl']),places=6)

    def test_missing_extra_and_duplicate_keys(self):
        sample=[dict(x) for x in self.monthly]
        issues=rec.compare(self.monthly,sample[:-1],('month',))
        self.assertTrue(any('saknas' in s for s in issues))
        sample.append(dict(sample[0],month='2026-01'))
        self.assertTrue(any('extra' in s for s in rec.compare(self.monthly,sample,('month',))))
        sample.append(dict(sample[0]))
        with self.assertRaisesRegex(rec.ReconciliationError,'dubbel nyckel'):rec.compare(self.monthly,sample,('month',))

    def test_tolerance_and_discrepancy(self):
        samples=[dict(x) for x in self.monthly]
        samples[0]['total_ead']+=0.005
        samples[0]['dpd30_rate']+=5e-9
        self.assertEqual(rec.compare(self.monthly,samples,('month',)),[])
        samples[0]['total_ead']+=0.02
        samples[0]['dpd90_rate']+=1e-6
        issues=rec.compare(self.monthly,samples,('month',))
        self.assertTrue(any('total_ead' in s for s in issues))
        self.assertTrue(any('dpd90_rate' in s for s in issues))

    def test_parse_export_and_reject_bad_values(self):
        with tempfile.TemporaryDirectory(dir=rec.ROOT) as d:
            p=Path(d)/'export.tsv'
            row=self.monthly[0]
            cols=('month',)+rec.METRICS
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f,delimiter='\t');w.writerow([f'[{c}]' for c in cols]);w.writerow([row[c] for c in cols])
            self.assertEqual(rec.load_export(p,('month',))[0],{c:row[c] for c in cols})
            p.write_text('[month]\t[total_ead]\t[dpd30_rate]\t[dpd90_rate]\t[ecl_proxy]\n2025-01\tNaN\t0\t0\t1\n',encoding='utf-8')
            with self.assertRaisesRegex(rec.ReconciliationError,'icke-ändligt'): rec.load_export(p,('month',))

    def test_duplicate_input_and_missing_month(self):
        with tempfile.TemporaryDirectory(dir=rec.ROOT) as d:
            for f in ('loans_synthetic.csv','monthly_snapshots_synthetic.csv'):shutil.copy(rec.ROOT/'data'/f,Path(d)/f)
            path=Path(d)/'monthly_snapshots_synthetic.csv'
            lines=path.read_text(encoding='utf-8').splitlines()
            with path.open('a',encoding='utf-8') as f:f.write(lines[1]+'\n')
            with self.assertRaisesRegex(rec.ReconciliationError,'Dubbla observationer'):rec.expected_results(Path(d))
            path.write_text('\n'.join(x for x in lines if ',2025-12,' not in x)+'\n',encoding='utf-8')
            with self.assertRaisesRegex(rec.ReconciliationError,'Månaderna'):rec.expected_results(Path(d))

    def test_segment_totals_reconcile_to_month(self):
        for month in rec.MONTHS:
            group=[r for r in self.segments if r['month']==month]
            total=next(r for r in self.monthly if r['month']==month)
            self.assertAlmostEqual(sum(r['total_ead'] for r in group),total['total_ead'],places=5)
            self.assertAlmostEqual(sum(r['ecl_proxy'] for r in group),total['ecl_proxy'],places=6)
            for metric in ('dpd30_rate','dpd90_rate'):
                weighted=sum(r[metric]*r['total_ead'] for r in group)/total['total_ead']
                self.assertAlmostEqual(weighted,total[metric],places=12)

    def test_end_to_end_with_simulated_exports(self):
        with tempfile.TemporaryDirectory(dir=rec.ROOT) as d:
            paths=[]
            for name,rows,keys in [('monthly',self.monthly,('month',)),('segments',self.segments,('month','segment'))]:
                path=Path(d)/(name+'.tsv');paths.append(path)
                with path.open('w',encoding='utf-8',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=keys+rec.METRICS,delimiter='\t',extrasaction='ignore');w.writeheader();w.writerows(rows)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rec.main(['--monthly',str(paths[0]),'--month-segment',str(paths[1])]),0)
            with paths[1].open('a',encoding='utf-8') as f:
                f.write(paths[1].read_text(encoding='utf-8').splitlines()[1]+'\n')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rec.main(['--monthly',str(paths[0]),'--month-segment',str(paths[1])]),2)

    def test_blank_allowed_only_with_explicit_zero_evidence(self):
        target = next(x for x in self.segments if x['month']=='2025-01' and x['segment']=='Subprime')
        self.assertEqual(target['_dpd90_count'], 0)
        actual = dict(target, dpd90_rate=None)
        normalized = []
        self.assertEqual(rec.compare([target], [actual], ('month','segment'), normalized), [])
        self.assertEqual(normalized, [(('2025-01','Subprime'),'dpd90_rate')])
        for changes in ({'_dpd90_count': 1}, {'total_ead': 0}, {'dpd90_rate': 0.01}, {'_dpd90_count': None}):
            bad_expected = dict(target, **changes)
            self.assertTrue(rec.compare([bad_expected], [actual], ('month','segment')), changes)
        self.assertTrue(rec.compare([target], [dict(actual, total_ead=0)], ('month','segment')))
        self.assertTrue(rec.compare([target], [dict(actual, ecl_proxy=actual['ecl_proxy']+1)], ('month','segment')))
        self.assertTrue(rec.compare([target], [dict(actual, dpd30_rate=actual['dpd30_rate']+0.001)], ('month','segment')))
        self.assertTrue(rec.compare([self.monthly[0]], [dict(self.monthly[0],dpd90_rate=None)], ('month',)))
        self.assertTrue(rec.compare([target], [dict(target, dpd30_rate=None)], ('month','segment')))

    def test_blank_parser_rejects_other_metrics(self):
        with tempfile.TemporaryDirectory(dir=rec.ROOT) as d:
            p = Path(d)/'e.tsv'
            p.write_text('month\tsegment\ttotal_ead\tdpd30_rate\tdpd90_rate\tecl_proxy\n2025-01\tSubprime\t1\t0\t\t1\n',encoding='utf-8')
            self.assertIsNone(rec.load_export(p,('month','segment'))[0]['dpd90_rate'])
            p.write_text('month\tsegment\ttotal_ead\tdpd30_rate\tdpd90_rate\tecl_proxy\n2025-01\tSubprime\t1\t\t0\t1\n',encoding='utf-8')
            with self.assertRaises(rec.ReconciliationError):rec.load_export(p,('month','segment'))

    def test_queries_reference_model_measures(self):
        for name in ('monthly.dax','month_segment.dax'):
            text=(rec.ROOT/'powerbi/reconciliation'/name).read_text(encoding='utf-8')
            self.assertNotIn('DEFINE',text.upper())
            for measure in ('[Total EAD]','[DPD 30+ Rate]','[DPD 90+ Rate]','[ECL Proxy]'):self.assertIn(measure,text)

if __name__=='__main__':unittest.main()
