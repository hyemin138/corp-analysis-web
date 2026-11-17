import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from types import SimpleNamespace
import urllib.parse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import collector as c

# All values and receipts here are SYNTHETIC. Not Taewoong financial data.
XML = '''<?xml version="1.0" encoding="utf-8"?><DOCUMENT><TITLE>연결재무제표 주석</TITLE>
<P>판매비와관리비 (단위: 천원) 테스트 가상표</P><TABLE><TR><TD>항목</TD><TD>2025 누적</TD></TR>
<TR><TD>급여</TD><TD>1,000</TD></TR><TR><TD>감가상각비</TD><TD>200</TD></TR>
<TR><TD>대손상각비</TD><TD>(100)</TD></TR><TR><TD>합계</TD><TD>1,100</TD></TR></TABLE>
<P>매출채권</P><TABLE><TR><TD rowspan="2">매출채권</TD><TD colspan="2">분류</TD></TR>
<TR><TD>10</TD><TD>20</TD></TR></TABLE></DOCUMENT>'''

def zipped():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr('report.xml',XML)
    return b.getvalue()

class TestCollector(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.s=c.Store(self.root)
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def import_data(self,receipt='20990101000001'):
        self.s.persist('report-'+receipt,'manual',{'rcept_no':receipt,'report_nm':'SYNTHETIC 사업보고서 (2025.12)','filed_date':'20260301'},zipped())
        return c.extract(self.root)[0]
    def review(self,t,**changes):
        row=dict.fromkeys(c.REVIEW_FIELDS,'')
        row.update(table_id=t['table_id'],row='3',col='1',account_label='대손상각비',canonical_account='bad_debt_expense',raw_value='(100)',unit='천원',scope='CFS',period_start='2025-01-01',period_end='2025-12-31',value_kind='annual',reviewed='YES',reviewer='SYNTHETIC_TEST')
        row.update(changes);p=self.root/'data/review_values.csv';c.csvout(p,[row],c.REVIEW_FIELDS);return p
    def test_extract_grid(self):
        self.import_data();ts=c.readjson(self.root/'data/interim/tables.json')
        self.assertEqual(len(ts),2);self.assertEqual(ts[1]['grid'][1],['매출채권','10','20'])
    def test_resume_no_http(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('HTTP must not run')):
            params={'rcept_no':'20990101000001'};rid=c.sha(('document.xml'+json.dumps(params,sort_keys=True)).encode())
            self.s.persist(rid,'document.xml',params,zipped())
            self.assertEqual(self.s.request('document.xml',params,''),zipped())
    def test_tamper_detected(self):
        self.import_data();r=self.s.get('report-20990101000001');(self.root/r['path']).write_bytes(b'tampered')
        with self.assertRaises(RuntimeError):self.s.verify(r)
    def test_sidecar_required(self):
        self.import_data();r=self.s.get('report-20990101000001');(self.root/r['path']).with_suffix('.bin.json').unlink()
        with self.assertRaises(RuntimeError):self.s.verify(r)
    def test_key_missing_no_http(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError()):
            with self.assertRaises(RuntimeError):self.s.request('document.xml',{'rcept_no':'x'},'')
        self.assertEqual(self.s.status(),{'BLOCKED':1})
    def test_budget_no_http(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError()):
            with self.assertRaises(RuntimeError):self.s.request('document.xml',{'rcept_no':'x'},'x'*40,budget=0)
        self.assertEqual(self.s.status(),{'BLOCKED':1})
    def test_numbers_and_missing(self):
        self.assertEqual(c.number('(1,100)'),-1100)
        for s in ['-','','1,100*','1%']:
            with self.assertRaises(ValueError):c.number(s)
    def test_export_units_and_coverage(self):
        t=self.import_data();p=self.review(t);c.export(self.root,p)
        r=c.csvin(self.root/'data/processed/reviewed_values.csv')[0]
        self.assertEqual(r['value'],'-100000');self.assertEqual(r['value_eok'],'-0.001')
        q=c.csvin(self.root/'data/processed/sga_receivables_quarterly.csv')[0]
        self.assertEqual(q['quarter_value'],'') # annual is not Q4 without prior cumulative
        qa=c.csvin(self.root/'data/processed/qa_notes.csv');self.assertEqual(len(qa),26*5)
        self.assertEqual(c.readjson(self.root/'reports/summary.json')['status'],'REVIEW_REQUIRED')
    def test_unreviewed_excluded(self):
        t=self.import_data();p=self.review(t,reviewed='');self.assertEqual(c.reviewed_values(self.root,p),[])
    def test_raw_cell_mismatch(self):
        t=self.import_data();p=self.review(t,raw_value='100')
        with self.assertRaises(ValueError):c.reviewed_values(self.root,p)
    def test_ofs_rejected(self):
        t=self.import_data();p=self.review(t,scope='OFS')
        with self.assertRaises(ValueError):c.reviewed_values(self.root,p)
    def test_annual_teu_quarter_rejected(self):
        t=self.import_data();p=self.review(t,canonical_account='container_teu_annual',unit='TEU',scope='BUSINESS',value_kind='quarter',period_start='2025-10-01')
        with self.assertRaises(ValueError):c.reviewed_values(self.root,p)
    def test_reconcile_pass_and_fail(self):
        t=self.import_data();p=self.root/'check.csv'
        fields=['table_id','col','total_row','component_rows','tolerance']
        r={'table_id':t['table_id'],'col':'1','total_row':'4','component_rows':'1;2;3','tolerance':'0'}
        c.csvout(p,[r],fields);self.assertFalse(c.reconcile(self.root,p))
        c.csvout(p,[{**r,'component_rows':'1;2'}],fields);self.assertTrue(c.reconcile(self.root,p))
    def test_lock(self):
        with c.lock(self.root):
            with self.assertRaises(RuntimeError):
                with c.lock(self.root):pass
        self.assertFalse((self.root/'collector.lock').exists())
    def test_same_raw_not_rewritten(self):
        self.import_data();r=self.s.get('report-20990101000001');p=self.root/r['path'];before=p.stat().st_mtime_ns
        self.import_data();self.assertEqual(p.stat().st_mtime_ns,before)
    def test_duplicate_review_rejected(self):
        t=self.import_data();p=self.review(t);rows=c.csvin(p);c.csvout(p,rows+rows,c.REVIEW_FIELDS)
        with self.assertRaises(ValueError):c.reviewed_values(self.root,p)
    def test_api_mock_end_to_end_and_resume(self):
        # SYNTHETIC API responses. No requests leave this test.
        corp=io.BytesIO()
        with zipfile.ZipFile(corp,'w') as z:
            z.writestr('CORPCODE.xml','<result><list><corp_name>태웅로직스</corp_name><corp_code>99999999</corp_code></list></result>')
        reports=[{'rcept_no':'20260301000001','report_nm':'사업보고서 (2025.12)','rcept_dt':'20260301'},
                 {'rcept_no':'20260801000001','report_nm':'반기보고서 (2026.06)','rcept_dt':'20260801'},
                 {'rcept_no':'20261101000001','report_nm':'분기보고서 (2026.09)','rcept_dt':'20261101'}]
        calls=[]
        def http(req,timeout):
            calls.append(req.full_url)
            if '/corpCode.xml?' in req.full_url: data=corp.getvalue()
            elif '/list.json?' in req.full_url:
                params=urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
                data=json.dumps({'status':'000','total_page':1,'list':reports if params['bgn_de']==['20260101'] else []}).encode()
            else: data=zipped()
            response=io.BytesIO(data)
            return response
        args=SimpleNamespace(start_year=2020,freeze='20261110',budget=200,cmd='collect',pilot=True,all_reports=False,dry_run=False)
        with patch.dict('os.environ',{'DART_API_KEY':'x'*40}), patch('urllib.request.urlopen',side_effect=http):
            c.discover(self.root,args)
            self.assertEqual(len(c.csvin(self.root/'state/catalog.csv')),2)
            c.collect(self.root,args)
            count=len(calls)
            args.cmd='resume';args.pilot=False
            c.collect(self.root,args)
            self.assertEqual(len(calls),count)
            self.assertTrue(c.readjson(self.root/'state/collection_plan.json')['pilot'])
            self.assertEqual(len(c.extract(self.root)),2)
        for p in self.root.rglob('*.json'):
            self.assertNotIn('x'*40,p.read_text())
    def test_quarter_from_same_report_only(self):
        t=self.import_data(); p=self.review(t,row='1',raw_value='1,000',canonical_account='salary_sga',period_end='2025-06-30',value_kind='cumulative')
        rows=c.csvin(p)
        rows.append({**rows[0],'row':'2','raw_value':'200','period_end':'2025-03-31'})
        c.csvout(p,rows,c.REVIEW_FIELDS);c.export(self.root,p)
        q=c.csvin(self.root/'data/processed/sga_receivables_quarterly.csv')
        self.assertEqual(q[0]['quarter_value'],'800000')
        self.assertEqual(q[1]['quarter_value'],'200000')
    def test_api_error_blocked_no_secret(self):
        with patch('urllib.request.urlopen',return_value=io.BytesIO(b'<result><status>020</status></result>')):
            with self.assertRaises(RuntimeError):self.s.request('document.xml',{'rcept_no':'test'},'x'*40)
        self.assertEqual(self.s.status(),{'BLOCKED':1})
    def test_transient_error_retries(self):
        calls=[io.BytesIO(b''),io.BytesIO(zipped())]
        with patch('urllib.request.urlopen',side_effect=calls),patch('time.sleep'):
            self.s.request('document.xml',{'rcept_no':'test'},'x'*40)
        row=self.s.db.execute('SELECT * FROM requests').fetchone()
        self.assertEqual(row['attempts'],2);self.assertEqual(row['status'],'COMPLETE')
    def test_negative_coordinate_rejected(self):
        t=self.import_data();p=self.review(t,row='-1')
        with self.assertRaises(ValueError):c.reviewed_values(self.root,p)

if __name__=='__main__':unittest.main()
