"""TRACK2 B v0.3: normalize old/new CFS notes offline. Place next to collector.py."""
import argparse
import calendar
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import collector as c

VERSION='0.3.0'
CORE=['sga_total','bad_debt_expense','salary_sga','depreciation_sga','trade_receivables_gross','loss_allowance','trade_receivables_net']
ALIASES={
 '급여':'salary_sga','퇴직급여':'retirement_sga','복리후생비':'welfare_sga','복리후생':'welfare_sga',
 '감가상각비':'depreciation_sga','무형자산상각비':'amortization_sga','광고선전비':'advertising_sga',
 '지급수수료':'fees_sga','대손상각비':'bad_debt_expense','대손상각비(환입)':'bad_debt_expense',
 '대손상각비(대손충당금환입)':'bad_debt_expense','세금과공과':'taxes_sga','세금과공과금':'taxes_sga',
 '운반비':'transport_sga','보험료':'insurance_sga','지급임차료':'rent_sga','임차료':'rent_sga',
 '기타':'other_sga','기타판매비와관리비':'other_sga','판매비와관리비':'sga_total','합계':'sga_total'}
LABELS={'당기','전기','당기말','전기말','당반기','전반기','당반기말','전반기말','당분기','전분기','당분기말','전분기말'}
FIELDS=['value_id','rcept_no','report_nm','filed_date','report_fiscal_period','table_id','table_index','member',
 'row','col','canonical_account','account_label','period_label','period_start','period_end','value_kind','is_current_period',
 'raw_value','unit','value_krw','value_eok','analysis_value_krw','analysis_value_eok','derivation',
 'input_value_ids','available_date','source_url','raw_sha256','raw_revalidated','qa_status','note']

def compact(s):return re.sub(r'\s+','',str(s)).replace('&cr;','')
def cleanlabel(s):return compact(s).strip('<>〈〉＜＞[]')
def rowtext(row):return ' '.join(str(x) for x in row)
def numeric(x):
 try:return c.number(x)
 except ValueError:return None

def dates(y,m):return f'{y}-{m:02}-{calendar.monthrange(y,m)[1]}'
def acct(s):return ALIASES.get(compact(s).replace(',판관비',''))

def cfs_bounds(tables):
    """Ignore early contents-list mentions; use last major marker, then first CFS->OFS transition."""
    begin=None;finish=None
    for t in tables:
        ctx=compact(t['context'])
        marks=list(re.finditer(r'3\.연결재무제표주석|5\.재무제표주석',ctx))
        if not marks:continue
        marker='CFS' if '연결' in marks[-1][0] else 'OFS'
        if begin is None and marker=='CFS':begin=t['table_index']
        elif begin is not None and marker=='OFS' and t['table_index']>begin:
            finish=t['table_index'];break
    return begin,finish

def sga_schema(t):
    g=t['grid']
    if '판매비' not in t['context'][-600:]:return None
    for label_col in (0,1):
        salary=[i for i,r in enumerate(g) if len(r)>label_col and acct(r[label_col])=='salary_sga']
        total=[i for i,r in enumerate(g) if len(r)>label_col and acct(r[label_col])=='sga_total']
        detail=[i for i,r in enumerate(g) if len(r)>label_col and acct(r[label_col]) not in {None,'sga_total'}]
        if len(salary)==1 and len(total)==1 and len(detail)>=8:
            return label_col,total[0],detail
    return None

def receivable_schema(t):
    g=t['grid']
    for i,r in enumerate(g[:4]):
        headers=[compact(x) for x in r]
        gross=next((j for j,x in enumerate(headers) if x in {'채권액','총장부금액'}),None)
        loss=next((j for j,x in enumerate(headers) if x in {'대손충당금','손상차손누계액'}),None)
        net=next((j for j,x in enumerate(headers) if x in {'장부금액','장부금액합계'}),None)
        if None in (gross,loss,net):continue
        candidates=[(ri,ci) for ri,row in enumerate(g[i+1:],i+1) for ci in range(min(gross,len(row))) if compact(row[ci]) in {'매출채권','유동매출채권'}]
        if len(candidates)==1:return i,candidates[0][0],candidates[0][1],gross,loss,net
    return None

def preceding(t,index):
    return [index[(t['member'],t['table_index']-d)] for d in (1,2,3) if (t['member'],t['table_index']-d) in index]

def unit_evidence(t,index):
    for source in [t]+preceding(t,index):
        # Only short caption/heading tables are eligible as preceding unit evidence.
        if source is not t and len(source['grid'])>3:continue
        text=compact(str(source['grid']))
        if re.search(r'단위[:：]?천원',text):return source['table_id']
    return None

def period_meta(t,col,headers,index,kind):
    parts=[cleanlabel(r[col]) for r in headers if len(r)>col]
    labels=[x for x in parts if x in LABELS]
    evidence=[]
    if not labels:
        for prev in preceding(t,index):
            if len(prev['grid'])>3:continue
            found=[cleanlabel(x) for row in prev['grid'] for x in row if cleanlabel(x) in LABELS]
            if found:labels=found;evidence.append(prev['table_id']);break
    labels=list(dict.fromkeys(labels))
    if len(labels)!=1:raise ValueError('당기/전기 표기 미확인')
    label=labels[0];y,m=map(int,t['fiscal_period'].split('-'))
    if label.startswith('전'):
        y-=1
        if label=='전기말':m=12
    if kind=='balance':start=end=dates(y,m);value_kind='balance'
    else:
        end=dates(y,m)
        if m==12:value_kind='annual';start=f'{y}-01-01'
        elif '3개월' in parts:value_kind='quarter';start=f'{y}-{m-2:02}-01'
        elif '누적' in parts:value_kind='cumulative';start=f'{y}-01-01'
        elif m==3:value_kind='quarter';start=f'{y}-01-01'
        elif label in {'당반기','전반기'}:value_kind='cumulative';start=f'{y}-01-01'
        else:raise ValueError('3개월/누적 구분 미확인')
    return dict(period_label=label,period_start=start,period_end=end,value_kind=value_kind,
                is_current_period='YES' if label.startswith('당') else 'NO'),evidence


def run(tables,out,raw_verified=False,source_hash=''):
    byreport=defaultdict(list)
    for t in tables:
        if t['member']==t['rcept_no']+'.xml':byreport[t['rcept_no']].append(t)
    values=[];checks=[];issues=[];selected=[];movement_tables=[];scope_audit=[];report_audit=[];evidence_ids=set()
    def issue(t,reason,account='',kind='REVIEW_REQUIRED'):
        issues.append({'rcept_no':t['rcept_no'],'table_id':t['table_id'],'account':account,'status':kind,'reason':reason})
    def add(t,ri,col,label_col,account,meta,note=''):
        raw=t['grid'][ri][col];v=numeric(raw)
        if v is None:
            issue(t,'셀 공백/대시/비수치: 0으로 대치하지 않음',account);return None
        krw=v*1000;analysis=abs(krw) if account=='loss_allowance' else krw
        value_id=hashlib.sha256((t['table_id']+':'+str(ri)+':'+str(col)+':'+account+':'+meta['value_kind']).encode()).hexdigest()[:24]
        item={k:t[k] for k in ['rcept_no','report_nm','filed_date','table_id','table_index','member','source_url','raw_sha256']}
        item.update(value_id=value_id,report_fiscal_period=t['fiscal_period'],row=ri,col=col,canonical_account=account,
                    account_label=t['grid'][ri][label_col],raw_value=raw,unit='천원',value_krw=str(krw),value_eok=str(krw/100000000),
                    analysis_value_krw=str(analysis),analysis_value_eok=str(analysis/100000000),derivation='direct_cell',input_value_ids='',
                    available_date=t['filed_date'],raw_revalidated='YES' if raw_verified else 'NO',qa_status='PARSED_REVIEW_REQUIRED',note=note,**meta)
        values.append(item);return item
    def check(t,name,left,right,note=''):
        delta=left-right
        checks.append({'rcept_no':t['rcept_no'],'table_id':t['table_id'],'test':name,'left_thousand_krw':str(left),
                       'right_thousand_krw':str(right),'difference_thousand_krw':str(delta),
                       'status':'PASS' if delta==0 else ('ROUNDING_REVIEW' if abs(delta)<=1 else 'FAIL'),'note':note})
    for receipt,arr in sorted(byreport.items()):
        arr.sort(key=lambda t:t['table_index']);index={(t['member'],t['table_index']):t for t in arr}
        begin,end=cfs_bounds(arr)
        scope_audit.append({'rcept_no':receipt,'report_nm':arr[0]['report_nm'],'cfs_begin_index':begin,'ofs_begin_index':end,
                            'status':'BOUNDARIES_FOUND' if begin is not None and end is not None else 'REVIEW_REQUIRED'})
        if begin is None or end is None:
            issue(arr[0],'연결/별도 주석 경계 탐지 불가: 이번 공시 전체 자동추출 보류');continue
        count=Counter()
        for t in arr:
            if not begin<=t['table_index']<end:continue
            text=compact(str(t['grid']))
            if '매출채권' in text and '기초' in text and '기말' in text and ('대손상각비' in text or '기대신용손실전(환)입' in text) and len(t['grid'])>=4:
                movement_tables.append(t)
            sg=sga_schema(t);rc=receivable_schema(t)
            if not sg and not rc:continue
            category='sga' if sg else 'receivables';count[category]+=1
            selected.append({**t,'selected_kind':category});evidence_ids.add(t['table_id'])
            unit=unit_evidence(t,index)
            if not unit:
                issue(t,'천원 단위 근거 없음: 수치 변환 보류');continue
            evidence_ids.add(unit)
            if sg:
                lc,ti,detail=sg;first=min(detail+[ti]);headers=t['grid'][:first]
                for col in range(lc+1,len(t['grid'][ti])):
                    try:meta,evidence=period_meta(t,col,headers,index,'flow')
                    except ValueError as e:issue(t,f'{col}열: '+str(e));continue
                    evidence_ids.update(evidence)
                    # Include every detail row, even an unknown account, in arithmetic audit.
                    detailnums=[numeric(t['grid'][i][col]) if len(t['grid'][i])>col else None for i in detail]
                    total=numeric(t['grid'][ti][col])
                    if None not in detailnums and total is not None:check(t,'sga_detail_sum_col_'+str(col),sum(detailnums,Decimal(0)),total)
                    else:issue(t,f'{col}열 판관비 합계검산 보류(공백 존재)')
                    accounts=set()
                    for ri in [ti]+detail:
                        account=acct(t['grid'][ri][lc]);accounts.add(account)
                        if len(t['grid'][ri])<=col:issue(t,'셀 열 부족',account);continue
                        add(t,ri,col,lc,account,meta)
                    if 'bad_debt_expense' not in accounts:
                        issue(t,'판관비 표에 대손상각비 행 없음. 다른 비용/채권변동 값으로 대체하지 않음','bad_debt_expense','NOT_DISCLOSED_IN_SGA_TABLE')
                unknown=[r[lc] for r in t['grid'][first:] if len(r)>lc and r[lc] and acct(r[lc]) is None]
                if unknown:issue(t,'계정 매핑 미지원: '+str(unknown))
            else:
                hi,ri,lc,gross,loss,net=rc;headers=t['grid'][:hi+1]
                try:meta,evidence=period_meta(t,gross,headers,index,'balance')
                except ValueError as e:issue(t,str(e));continue
                evidence_ids.update(evidence)
                for col,account in [(gross,'trade_receivables_gross'),(loss,'loss_allowance'),(net,'trade_receivables_net')]:
                    add(t,ri,col,lc,account,meta,'유동 매출채권 한정. 충당금 value는 원문 음수, analysis_value는 절대액')
                row=t['grid'][ri];nums=[numeric(row[j]) for j in (gross,loss,net)]
                if None not in nums:check(t,'gross_plus_signed_allowance_equals_net',nums[0]+nums[1],nums[2],
                    '천원 표시액 차이 1도 정확 일치로 처리하지 않음')
        report_audit.append({'rcept_no':receipt,'report_nm':arr[0]['report_nm'],'fiscal_period':arr[0]['fiscal_period'],
                             'sga_tables':count['sga'],'receivables_tables':count['receivables'],
                             'status':'STRUCTURES_FOUND' if count['sga'] and count['receivables'] else 'REVIEW_REQUIRED'})
    # Derive Q1 within a half-year table only. Originals and derived values are both preserved.
    derived=[]
    for value in values:
        if value['value_kind']!='cumulative' or not value['period_end'].endswith('-06-30'):continue
        peers=[p for p in values if p['table_id']==value['table_id'] and p['canonical_account']==value['canonical_account']
               and p['value_kind']=='quarter' and p['period_end']==value['period_end']]
        if len(peers)!=1:continue
        peer=peers[0];amount=Decimal(value['value_krw'])-Decimal(peer['value_krw'])
        derived.append({**value,'value_id':value['value_id']+'_Q1','col':str(value['col'])+'-'+str(peer['col']),
                        'period_end':value['period_end'][:4]+'-03-31','value_kind':'quarter','raw_value':'',
                        'value_krw':str(amount),'value_eok':str(amount/100000000),'analysis_value_krw':str(amount),
                        'analysis_value_eok':str(amount/100000000),'derivation':'same_table_H1_minus_Q2',
                        'input_value_ids':value['value_id']+';'+peer['value_id'],'note':'동일 공시 반기 누적-2Q 3개월. 공시 버전 보존'})
    values+=derived
    # Preserve all vintages; wide view selects the latest OWN-period report for description only.
    own_reports={}
    for receipt,arr in sorted(byreport.items()):own_reports[arr[0]['fiscal_period']]=receipt
    long_index=defaultdict(list)
    for v in values:long_index[(v['rcept_no'],v['canonical_account'],v['period_end'],v['value_kind'])].append(v)
    quarter_rows=[];coverage=[];quarter_values=[]
    def choose(items,kind=None):
        items=[v for v in items if v['value_krw']!='']
        if not items:return None
        direct=[v for v in items if v['derivation']=='direct_cell']
        items=direct or items
        if len(set(v['analysis_value_krw'] for v in items))>1:return None
        return items[0]
    for y in range(2020,2027):
      for q in range(1,5):
        if (y,q)>(2026,2):continue
        end=dates(y,q*3);period=f'{y}-{q*3:02}';receipt=own_reports.get(period,'')
        row={'fiscal_quarter':f'{y}Q{q}','period_end':end,'selected_rcept_no':receipt,'selection_policy':'latest_own_report_for_description',
             'model_ready':'NO_asof_and_definition_audit_required'}
        for account in CORE:
            isbal=account in {'trade_receivables_gross','loss_allowance','trade_receivables_net'}
            kind='balance' if isbal else 'quarter'
            v=choose(long_index[(receipt,account,end,kind)])
            if not v and q==1 and not isbal:v=choose(long_index[(receipt,account,end,'cumulative')])
            status='MISSING';amount='';source_ids='';available=''
            if v:
                amount=v['analysis_value_krw'];status='DIRECT' if v['derivation']=='direct_cell' else 'SAME_TABLE_DERIVED';source_ids=v['value_id'];available=v['available_date']
            elif q==4 and not isbal:
                annual=choose(long_index[(receipt,account,end,'annual')])
                previous_period=f'{y}-09';previous_receipt=own_reports.get(previous_period,'');previous_end=dates(y,9)
                prior=choose(long_index[(previous_receipt,account,previous_end,'cumulative')])
                if annual and prior:
                    amount=str(Decimal(annual['analysis_value_krw'])-Decimal(prior['analysis_value_krw']))
                    status='CROSS_REPORT_Q4_REVIEW_REQUIRED';source_ids=annual['value_id']+';'+prior['value_id'];available=max(annual['available_date'],prior['available_date'])
            row[account+'_eok']=str(Decimal(amount)/100000000) if amount else ''
            row[account+'_status']=status
            coverage.append({'fiscal_quarter':row['fiscal_quarter'],'account':account,'status':status,'selected_rcept_no':receipt,
                             'value_eok':row[account+'_eok'],'input_value_ids':source_ids,'available_date':available})
            quarter_values.append({**coverage[-1],'value_krw':amount,'period_end':end,'model_ready':'NO_asof_and_definition_audit_required'})
        quarter_rows.append(row)
    historical_checks=[]
    for v in values:
        if v['derivation']!='same_table_H1_minus_Q2' or v['is_current_period']!='YES':continue
        candidates=[p for p in values if p['canonical_account']==v['canonical_account'] and p['period_start']==v['period_start']
                    and p['period_end']==v['period_end'] and p['value_kind']=='quarter' and p['derivation']=='direct_cell'
                    and p['is_current_period']=='YES' and p['report_fiscal_period']==v['period_end'][:7]
                    and p['filed_date']<=v['filed_date']]
        if not candidates:continue
        prior=sorted(candidates,key=lambda p:p['rcept_no'])[-1]
        delta=Decimal(v['analysis_value_krw'])-Decimal(prior['analysis_value_krw'])
        historical_checks.append({'account':v['canonical_account'],'period_end':v['period_end'],'h1_rcept_no':v['rcept_no'],
                                  'q1_rcept_no':prior['rcept_no'],'h1_implied_q1_eok':v['analysis_value_eok'],
                                  'q1_original_eok':prior['analysis_value_eok'],'difference_eok':str(delta/100000000),
                                  'status':'PASS' if delta==0 else ('ROUNDING_REVIEW' if abs(delta)<=1000 else 'DEFINITION_OR_VINTAGE_REVIEW')})
    issues=list({(x['rcept_no'],x['table_id'],x['account'],x['reason']):x for x in issues}.values())
    # Contradictory publications of the same item are surfaced, never silently averaged.
    comparable=defaultdict(list)
    for v in values:
        if v['derivation']=='direct_cell':comparable[(v['canonical_account'],v['period_start'],v['period_end'],v['value_kind'])].append(v)
    vintage=[]
    for key,items in comparable.items():
        numbers=set(v['analysis_value_krw'] for v in items)
        if len(numbers)>1:
            for v in items:vintage.append({k:v[k] for k in ['canonical_account','period_start','period_end','value_kind','rcept_no','filed_date','analysis_value_eok','value_id']})
    out.mkdir(parents=True,exist_ok=True)
    c.csvout(out/'p0_values_all_vintages.csv',values,FIELDS)
    c.jsonout(out/'p0_selected_tables.json',selected)
    c.jsonout(out/'allowance_movement_tables_for_review.json',movement_tables)
    c.csvout(out/'historical_consistency.csv',historical_checks,['account','period_end','h1_rcept_no','q1_rcept_no','h1_implied_q1_eok','q1_original_eok','difference_eok','status'])
    c.csvout(out/'p0_table_index.csv',selected,['table_id','rcept_no','report_nm','fiscal_period','table_index','member','selected_kind','source_url','raw_sha256'])
    c.csvout(out/'p0_checks.csv',checks,['rcept_no','table_id','test','left_thousand_krw','right_thousand_krw','difference_thousand_krw','status','note'])
    c.csvout(out/'qa_notes.csv',issues,['rcept_no','table_id','account','status','reason'])
    c.csvout(out/'report_availability.csv',report_audit,['rcept_no','report_nm','fiscal_period','sga_tables','receivables_tables','status'])
    c.csvout(out/'scope_boundaries.csv',scope_audit,['rcept_no','report_nm','cfs_begin_index','ofs_begin_index','status'])
    c.csvout(out/'sga_receivables_quarterly.csv',quarter_rows,list(quarter_rows[0]) if quarter_rows else [])
    c.csvout(out/'quarterly_account_values.csv',quarter_values,['fiscal_quarter','period_end','account','value_krw','value_eok','status','selected_rcept_no','input_value_ids','available_date','model_ready'])
    c.csvout(out/'quarterly_coverage.csv',coverage,['fiscal_quarter','account','status','value_eok','selected_rcept_no','input_value_ids','available_date'])
    c.csvout(out/'vintage_differences.csv',vintage,['canonical_account','period_start','period_end','value_kind','rcept_no','filed_date','analysis_value_eok','value_id'])
    mappings={}
    for v in values:mappings[(v['account_label'],v['canonical_account'])]={'account_label':v['account_label'],'canonical_account':v['canonical_account']}
    c.csvout(out/'accounts_mapping.csv',list(mappings.values()),['account_label','canonical_account'])
    summary={'version':VERSION,'source_json_sha256':source_hash,'input_tables':len(tables),'reports_in_input':len(byreport),
             'reports_with_sga':sum(x['sga_tables']>0 for x in report_audit),'reports_with_receivables':sum(x['receivables_tables']>0 for x in report_audit),
             'selected_tables':len(selected),'movement_tables_for_review':len(movement_tables),'values_all_vintages':len(values),'same_table_Q1_derived':len(derived),
             'checks':dict(Counter(x['status'] for x in checks)),'historical_consistency':dict(Counter(x['status'] for x in historical_checks)),'issues':len(issues),'vintage_difference_rows':len(vintage),
             'target_quarters':len(quarter_rows),'coverage':dict(Counter(x['status'] for x in coverage)),
             'raw_revalidated':raw_verified,'status':'REVIEW_REQUIRED',
             'limitations':['26분기 여부와 개별 계정 완성도는 구분','빈칸/대시 및 없는 계정은 0으로 채우지 않음',
                            'Q4 연간-9개월은 공시 간 정의·정정 확인 전 잠정치','원 공시일·비교기간·정정 버전 모두 보존; 분기표는 설명용 최신 자체공시 기준',
                            '2019 비교값은 참고용이며 목표 26분기에 포함하지 않음','P1 TEU/사업부문/운송매입 및 P2 채권연령은 후속 단계',
                            '충당금 변동표는 별도 원형 JSON에 보존; 과거 표의 기간·제각·환입 정규화는 별도 확인필요',
                            '주석 대목 경계 규칙은 이 입력 공시에서 검사; 다른 회사·새 공시의 포착률은 별도 확인필요']}
    c.jsonout(out/'p0_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--input',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--verify-raw',action='store_true')
    args=p.parse_args();root=args.root.resolve()
    try:
        with c.lock(root):
            source=args.input or root/'data/interim/tables.json'
            if args.verify_raw:
                if args.input:raise ValueError('--verify-raw는 로컬 원본에서 재생성합니다. --input과 함께 사용하지 마세요.')
                tables=c.extract(root)
            else:tables=c.readjson(source)
            summary=run(tables,args.output or root/'reports/p0_full',args.verify_raw,hashlib.sha256(source.read_bytes()).hexdigest())
        sys.exit(1 if summary['checks'].get('FAIL',0) else 0)
    except (RuntimeError,ValueError,KeyError,FileNotFoundError,IndexError) as exc:
        print('ERROR:',str(exc),file=sys.stderr);sys.exit(2)
