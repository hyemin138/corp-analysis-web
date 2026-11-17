"""Offline verify 2026-11-12 handoff snapshot and source trace (no DART HTTP)."""
from pathlib import Path
import csv, json, zipfile, re
from decimal import Decimal
from datetime import datetime, timedelta
from collections import Counter
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def rows(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def xcol(n):
    s=''
    while n: n,r=divmod(n-1,26);s=chr(65+r)+s
    return s
def verify():
    sc=rows('examples/B_quarterly_screened.csv');di=rows('examples/B_quarterly_diagnostic.csv')
    an=rows('examples/B_annual_diagnostic.csv');ce=rows('docs/evidence/quarterly_cell_decisions.csv')
    dictionary=rows('docs/evidence/variable_dictionary.csv');cv=rows('docs/evidence/variable_coverage.csv')
    catalog=rows('docs/evidence/source_catalog.csv');issues=rows('docs/review_register.csv')
    q4=rows('docs/evidence/feedback_20261112/q4_source_review.csv')
    summary=json.loads((ROOT/'docs/evidence/handoff_summary.json').read_text('utf-8'))
    var=[r['variable'] for r in dictionary]
    assert len(var)==len(set(var))==23
    assert len(sc)==len(di)==26 and [x['fiscal_quarter'] for x in sc]==[x['fiscal_quarter'] for x in di]
    assert len(an)==6 and len(cv)==23 and len(issues)==13
    assert len(catalog)==len({r['rcept_no'] for r in catalog})==29
    assert all(re.fullmatch(r'[a-f0-9]{64}',r['raw_sha256']) for r in catalog)
    periods=[r['fiscal_quarter'] for r in sc]
    assert periods[0]=='2020Q1' and periods[-1]=='2026Q2' and len(set(periods))==26
    assert len(ce)==26*23==598
    bycell={(r['fiscal_quarter'],r['variable']):r for r in ce}
    assert len(bycell)==598 and set(bycell)=={(p,v) for p in periods for v in var}
    present=0
    for row in sc:
        q=row['fiscal_quarter'];day=(datetime.strptime(row['filed_date'],'%Y%m%d').date()+timedelta(days=1)).isoformat()
        assert row['available_on_kst']==day and row['forecast_ready']!='YES'
        for v in var:
            c=bycell[(q,v)];value=row[v]
            assert value==c['screened_value']
            if c['decision'].startswith('HOLD') or c['decision'] in ('MISSING','NOT_IDENTIFIED'):
                assert not value
            if value: Decimal(value);present+=1
    assert present==543
    for item in cv:
        assert sum(bool(r[item['variable']]) for r in sc)==int(item['screened_values'])
    assert summary['quarters']==26 and summary['quarter_variables']==23
    assert summary['cells']==598 and summary['screened_nonempty_cells']==543
    assert summary['restored_in_feedback_review']==72 and summary['forecast_ready'] is False
    assert len(q4)==70 and sum(1 for r in ce if r['decision']=='USE_DERIVED_REVIEWED')==70
    for r in q4:
        assert r['scope']=='CONSOLIDATED_SGA_NOTE'
        assert Decimal(r['annual_eok'])-Decimal(r['nine_month_eok'])==Decimal(r['q4_eok'])
        assert bycell[(r['fiscal_quarter'],r['account'])]['screened_value']==r['q4_eok']
    checked=0;ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(ROOT/'examples/Track2_B_검토및인계.xlsx') as z:
        for sn,rows_ in ((1,sc),(2,di)):
            xml=ET.fromstring(z.read(f'xl/worksheets/sheet{sn}.xml'))
            idx={c.get('r'):c for c in xml.findall('.//x:c',ns)}
            assert not xml.findall('.//x:c[@t="e"]',ns)
            for i,row in enumerate(rows_,7):
                for j,v in enumerate(var,2):
                    cel=idx.get(xcol(j)+str(i));a=cel.find('x:v',ns) if cel is not None else None
                    actual=a.text if a is not None else ''
                    expected=row[v]
                    if not expected: assert not actual,(sn,i,v,actual)
                    else:
                        x=Decimal(expected)/(100 if v.endswith('_pct') else 1)
                        assert actual and abs(Decimal(actual)-x)<Decimal('1e-8'),(sn,i,v,actual,expected)
                    checked+=1
    assert checked==1196
    return {'status':'PASS','quarters':len(sc),'variables':len(var),'decision_cells':len(ce),
            'screened_nonempty':present,'source_reports':len(catalog),'restored_q4_cells':len(q4),
            'workbook_cells_checked':checked,'limitations':'Original DART raw ZIPs not independently revalidated.'}
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
