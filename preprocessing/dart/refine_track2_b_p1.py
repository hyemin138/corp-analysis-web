"""TRACK2 B annual business-data collector. Offline; standard library + collector.py."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import collector as c

FIELDS=['value_id','dataset','rcept_no','report_nm','filed_date','report_year','data_year','is_current_year',
        'table_id','member','row','col','metric','business','item','market','row_level','mode',
        'raw_value','unit','value','value_eok','source_url','raw_sha256','derivation','input_value_ids','note']

def norm(s):return re.sub(r'\s+','',str(s)).replace('&cr;','')
def num(x):
 try:return c.number(x)
 except ValueError:return None

def yearcols(header,report_year):
    periods=[int(m[1]) for s in header if (m:=re.search(r'제(\d+)기',norm(s)))]
    base=periods[0] if periods else None
    result={}
    for i,label in enumerate(header):
        text=norm(label)
        if m:=re.search(r'(20\d{2})년',text):result[i]=int(m[1])
        elif base is not None and (m:=re.search(r'제(\d+)기',text)):result[i]=report_year+int(m[1])-base
    return result

def mode_of(item):
    text=norm(item)
    for term,name in [('해상','sea'),('철도','rail'),('트럭','truck'),('항공','air'),('터미널','terminal')]:
        if term in text:return name
    if '내륙' in text:return 'inland_unspecified'
    return 'other'

def run(tables,out,verified=False,source_hash=''):
    reports=defaultdict(list)
    for t in tables:
        if t['member']==t['rcept_no']+'.xml' and t['fiscal_period'].endswith('-12') and '사업보고서' in t['report_nm']:
            reports[t['rcept_no']].append(t)
    values=[];selected=[];checks=[];issues=[]
    def record(t,year,ri,col,dataset,metric,business,unit,item='',market='',level='',mode='',note=''):
        raw=t['grid'][ri][col];v=num(raw)
        if v is None:
            issues.append({'rcept_no':t['rcept_no'],'table_id':t['table_id'],'row':ri,'col':col,'reason':'원문 공백/대시: 0 대치 안 함'});return
        actual=v if unit=='TEU' else v*1000
        vid=hashlib.sha256(f"{t['table_id']}:{ri}:{col}:{dataset}".encode()).hexdigest()[:24]
        row={k:t[k] for k in ['rcept_no','report_nm','filed_date','table_id','member','source_url','raw_sha256']}
        row.update(value_id=vid,dataset=dataset,report_year=int(t['fiscal_period'][:4]),data_year=year,
                   is_current_year='YES' if year==int(t['fiscal_period'][:4]) else 'NO',row=ri,col=col,
                   metric=metric,business=business,item=item,market=market,row_level=level,mode=mode,raw_value=raw,
                   unit=unit,value=str(actual),value_eok='' if unit=='TEU' else str(actual/100000000),
                   derivation='direct_cell',input_value_ids='',note=note)
        values.append(row)
    def check(receipt,tid,name,left,right):
        diff=left-right
        checks.append({'rcept_no':receipt,'table_id':tid,'test':name,'left_krw':str(left),'right_krw':str(right),'difference_krw':str(diff),
                       'status':'PASS' if not diff else ('ROUNDING_REVIEW' if abs(diff)<=1000 else 'FAIL')})
    for receipt,arr in sorted(reports.items()):
        arr.sort(key=lambda t:t['table_index']);idx={t['table_index']:t for t in arr};report_year=int(arr[0]['fiscal_period'][:4])
        for t in arr:
            g=t['grid'];ctx=norm(t['context']);text=norm(str(g))
            if not g:continue
            header=[norm(x) for x in g[0]];years=yearcols(g[0],report_year)
            if not years:continue
            kind=None
            if '사업부문별재무정보' in ctx[-350:] and len(g)>5 and '부문' in header and '매출총이익' in text:kind='segments'
            elif len(g)<=8 and ('품목' in header) and '종합물류' in text:kind='teu'
            elif '품목' in header and '해상운송료' in text and '철도운송료' in text and len(g)>=15:kind='transport'
            if not kind:continue
            captions=[idx.get(t['table_index']-d) for d in (1,2,3)]
            unit=None
            for caption in captions:
                if caption and len(caption['grid'])<=3:
                    cap=norm(str(caption['grid']))
                    if '단위' in cap:
                        if '천원' in cap:unit='천원';break
                        if 'TEU' in cap.upper():unit='TEU';break
            if kind=='teu' and unit!='TEU':continue # avoid sales tables with same product label
            if kind!='teu' and unit!='천원':
                issues.append({'rcept_no':receipt,'table_id':t['table_id'],'reason':'금액 단위 확인필요'});continue
            selected.append({**t,'p1_kind':kind,'unit_evidence':unit})
            if kind=='segments':
                metric_names={'매출액':'sales','매출원가':'cost','매출총이익':'gross_profit'}
                for ri,row in enumerate(g[1:],1):
                    metric=metric_names.get(norm(row[0]))
                    if not metric:continue
                    business=norm(row[1])
                    for col,year in years.items():record(t,year,ri,col,'segments',metric,business,unit,note='사업부문별 재무정보. 내부거래 연결조정 행 별도 보존')
            elif kind=='teu':
                for ri,row in enumerate(g[1:],1):
                    if len(row)<2 or norm(row[1])!='종합물류':continue
                    for col,year in years.items():record(t,year,ri,col,'teu','container_teu_annual','종합물류','TEU',note='종합물류 컨테이너 물동량; 연결 전체 매출 범위와 동일하지 않음; 분기 분할 금지')
            else:
                for ri,row in enumerate(g[1:],1):
                    if len(row)<3:continue
                    business,item,market=map(norm,row[:3])
                    if '종속' in business:level='subsidiary_total'
                    elif '연결조정' in business:level='elimination_total'
                    elif '총합계' in business:level='grand_total'
                    elif '소계' in item or item in {'합계',business+'합계'}:level='business_total'
                    elif market in {'소계','합계'}:level='item_subtotal'
                    else:level='geography_detail'
                    for col,year in years.items():record(t,year,ri,col,'transport','purchase',business,unit,item,market,level,mode_of(item),
                        '수익인식 미반영 매입총액 공시. 매출원가와 동일시 금지. 내륙운송을 트럭으로 단정하지 않음')
    # Legacy 2020 business categories can be reconciled as an explicit sum, without rewriting original labels.
    groups=defaultdict(list)
    for v in values:
        if v['dataset']=='segments':groups[(v['rcept_no'],v['data_year'],v['metric'])].append(v)
    legacy=[]
    for key,items in groups.items():
        bybusiness={v['business']:v for v in items}
        names=['국제물류','CIS물류','프로젝트물류']
        if all(x in bybusiness for x in names) and '종합물류' not in bybusiness:
            base=bybusiness[names[0]];amount=sum((Decimal(bybusiness[n]['value']) for n in names),Decimal(0))
            legacy.append({**base,'value_id':base['value_id']+'_legacy_sum','business':'종합물류','row':'','col':'','raw_value':'',
                           'value':str(amount),'value_eok':str(amount/100000000),'derivation':'sum_legacy_business_categories',
                           'input_value_ids':';'.join(bybusiness[n]['value_id'] for n in names),
                           'note':'국제+CIS+프로젝트 물류 합산; 원래 3개 분류도 별도 보존. 2021 공시 비교표의 종합물류와 대조 필요'})
        for metric in [key[2]]:
            total=bybusiness.get('합계')
            if total:
                parts=[v for v in items if v['business']!='합계']
                # Excludes derived legacy aggregate, which has not yet been appended.
                expected=max(len(g) for k,g in groups.items() if k[:2]==key[:2])
                if len(items)==expected:
                    check(key[0],total['table_id'],f'segment_sum_{metric}_{key[1]}',sum((Decimal(v['value']) for v in parts),Decimal(0)),Decimal(total['value']))
                else:checks.append({'rcept_no':key[0],'table_id':total['table_id'],'test':f'segment_sum_{metric}_{key[1]}','status':'INCOMPLETE_MISSING_COMPONENT'})
    values+=legacy
    # Segment sales-cost=gross profit, preserving eliminations.
    triples=defaultdict(dict)
    for v in values:
        if v['dataset']=='segments':triples[(v['rcept_no'],v['data_year'],v['business'])][v['metric']]=v
    for key,metrics in triples.items():
        if all(k in metrics for k in ['sales','cost','gross_profit']):
            check(key[0],metrics['sales']['table_id'],f'sales_minus_cost_{key[1]}_{key[2]}',Decimal(metrics['sales']['value'])-Decimal(metrics['cost']['value']),Decimal(metrics['gross_profit']['value']))
    # Procurement: sum item subtotals once only. Do not include domestic/foreign details or business totals again.
    procurement=defaultdict(list)
    for v in values:
        if v['dataset']=='transport':procurement[(v['rcept_no'],v['data_year'])].append(v)
    mode_values=[]
    for key,items in procurement.items():
        subtotals=[v for v in items if v['row_level']=='item_subtotal']
        totals=[v for v in items if v['row_level']=='grand_total' and v['market'] in {'합계','소계'}]
        adjustments=[v for v in items if v['row_level'] in {'subsidiary_total','elimination_total'}]
        if len(totals)==1 and subtotals:
            check(key[0],totals[0]['table_id'],f'purchase_items_plus_subsidiaries_and_eliminations_{key[1]}',sum((Decimal(v['value']) for v in subtotals+adjustments),Decimal(0)),Decimal(totals[0]['value']))
        grouped=defaultdict(list)
        for v in subtotals:grouped[v['mode']].append(v)
        for v in adjustments:grouped['subsidiary_unallocated' if v['row_level']=='subsidiary_total' else 'elimination_adjustment'].append(v)
        for mode,vs in grouped.items():
            amount=sum((Decimal(v['value']) for v in vs),Decimal(0))
            mode_values.append({'rcept_no':key[0],'data_year':key[1],'mode':mode,'value_krw':str(amount),'value_eok':str(amount/100000000),
                                'input_value_ids':';'.join(v['value_id'] for v in vs),'filed_date':vs[0]['filed_date'],
                                'note':'운송방식은 품목 소계만 합산. 종속회사·연결조정은 별도 범주. 국내·해외/사업부 소계 중복 제외'})
    # Annual view for 2020-2025. Prefer the report about that year; otherwise explicitly identify comparative-only data.
    annual=[]
    for year in range(2020,2026):
        row={'year':year,'period_start':f'{year}-01-01','period_end':f'{year}-12-31','frequency':'annual','model_ready':'NO_asof_and_scope_review_required'}
        for dataset in ['teu','segments','transport']:
            candidates=[v for v in values if v['dataset']==dataset and v['data_year']==year]
            own=sorted({v['rcept_no'] for v in candidates if v['is_current_year']=='YES'})
            receipts=sorted({v['rcept_no'] for v in candidates})
            chosen=own[-1] if own else (receipts[0] if receipts else '')
            row[dataset+'_rcept_no']=chosen;row[dataset+'_availability']='OWN_ANNUAL_REPORT' if own else ('COMPARATIVE_ONLY_REVIEW' if receipts else 'MISSING')
            chosenvalues=[v for v in candidates if v['rcept_no']==chosen]
            if dataset=='teu':
                matches=[v for v in chosenvalues if v['metric']=='container_teu_annual']
                row['container_teu_annual']=matches[0]['value'] if len(matches)==1 else ''
            elif dataset=='segments':
                bn={'종합물류':'logistics','종속법인':'subsidiary','종속회사':'subsidiary','연결조정':'elimination','합계':'consolidated'}
                for v in chosenvalues:
                    if v['business'] in bn:row[bn[v['business']]+'_'+v['metric']+'_eok']=v['value_eok']
            else:
                for mode in ['sea','rail','truck','air','terminal','inland_unspecified','other','subsidiary_unallocated','elimination_adjustment']:
                    match=[v for v in mode_values if v['rcept_no']==chosen and v['data_year']==year and v['mode']==mode]
                    row[mode+'_purchase_eok']=match[0]['value_eok'] if len(match)==1 else ''
        annual.append(row)
    out.mkdir(parents=True,exist_ok=True)
    c.csvout(out/'p1_values_all_vintages.csv',values,FIELDS)
    c.csvout(out/'transport_cost_annual.csv',[v for v in values if v['dataset']=='transport'],FIELDS)
    c.csvout(out/'segments_teu_annual.csv',[v for v in values if v['dataset'] in {'segments','teu'}],FIELDS)
    c.csvout(out/'transport_modes_annual.csv',mode_values,['rcept_no','data_year','mode','value_krw','value_eok','input_value_ids','filed_date','note'])
    fields=list(dict.fromkeys(k for row in annual for k in row))
    c.csvout(out/'annual_business_summary.csv',annual,fields)
    c.csvout(out/'p1_checks.csv',checks,['rcept_no','table_id','test','left_krw','right_krw','difference_krw','status'])
    c.csvout(out/'p1_issues.csv',issues,['rcept_no','table_id','row','col','reason'])
    c.jsonout(out/'p1_selected_tables.json',selected)
    summary={'annual_reports':len(reports),'selected_tables':len(selected),'by_dataset':dict(Counter(t['p1_kind'] for t in selected)),
             'values_with_comparatives':len(values),'checks':dict(Counter(x['status'] for x in checks)),'missing_cells':len(issues),
             'annual_summary_rows':len(annual),'raw_revalidated':verified,'source_json_sha256':source_hash,'status':'REVIEW_REQUIRED',
             'limitations':['금액자료는 사업현황 공시; 종합물류 TEU와 연결 전체 매출 범위 다름','연간 자료를 분기로 임의 분할하지 않음',
                            '2020 TEU가 비교기간에서 확보되면 그 보고서 공개일 이후에만 가용','매입액은 수익인식 미반영 총액으로 매출원가와 다를 수 있음',
                            '2018-2019 비교값·공시별 버전을 보존; 요약은 2020-2025','2020 구분 체계가 달라 3개 물류 부문 합산을 명시',
                            '내륙운송료는 트럭운송으로 단정하지 않음; 없는 운송수단은 공백 유지']}
    c.jsonout(out/'p1_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2));return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--input',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-raw',action='store_true')
    a=p.parse_args();root=a.root.resolve()
    try:
        with c.lock(root):
            source=a.input or root/'data/interim/tables.json'
            if a.verify_raw:
                if a.input:raise ValueError('--verify-raw와 --input은 함께 사용하지 않습니다.')
                tables=c.extract(root)
            else:tables=c.readjson(source)
            s=run(tables,a.output or root/'reports/p1_annual',a.verify_raw,hashlib.sha256(source.read_bytes()).hexdigest())
        sys.exit(1 if s['checks'].get('FAIL',0) else 0)
    except (ValueError,RuntimeError,KeyError,FileNotFoundError,IndexError) as e:print('ERROR:',str(e),file=sys.stderr);sys.exit(2)
