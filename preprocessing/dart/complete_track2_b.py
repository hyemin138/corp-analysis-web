"""TRACK2 B remaining variables: aging, reserve ratios, movements, all SGA and audit mapping.
Place next to collector.py. Offline, no LLM or HTTP calls.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import collector as c

VERSION='0.1.0'
D=Decimal

def norm(s):return re.sub(r'\s+','',str(s)).replace('&cr;','')
def num(s):
 try:return c.number(s)
 except ValueError:return None

def percent(s):return num(str(s).strip().rstrip('%')) if '%' in str(s) else None

def readcsv(p):return c.csvin(p)
def writecsv(p,rows,fields=None):
 if fields is None:fields=list(dict.fromkeys(k for row in rows for k in row))
 c.csvout(p,rows,fields)

def scan_original_tables(root):
    """Scan every primary XML table, including ones omitted by the original keyword filter."""
    store=c.Store(root);tables=[]
    try:
        for row in store.db.execute("SELECT * FROM requests WHERE status='COMPLETE' AND endpoint='manual'"):
            meta=json.loads(row['params']);payload=store.verify(row)
            for member,data in c.zip_members(payload):
                if member!=meta['rcept_no']+'.xml':continue
                parser=c.Tables();parser.feed(c.decode(data));parser.close()
                for idx,table in enumerate(parser.tables):
                    tid=c.sha((row['digest']+member+str(idx)).encode())[:24]
                    tables.append({'table_id':tid,'raw_sha256':row['digest'],'member':member,'table_index':idx,
                                   'context':table['context'],'grid':c.grid(table['rows']),**meta,
                                   'source_url':'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+meta['rcept_no']})
    finally:store.db.close()
    if not tables:raise ValueError('수집 완료 원문이 없습니다.')
    return list({t['table_id']:t for t in tables}.values())

def primary(t):return t['member']==t['rcept_no']+'.xml'
def age_schema(t):
    g=t['grid']
    if not g:return None
    header=[norm(x) for x in g[0]]
    if len(header)!=6 or not all('개월' in x or '년' in x for x in header[1:5]):return None
    if not ('3개월이하' in header[1] and '6개월' in header[2] and '12개월' in header[3] and '1년초과' in header[4]):return None
    rows=[i for i,row in enumerate(g) if row and norm(row[0])=='매출채권']
    return rows[0] if len(rows)==1 else None

def bounds(arr):
    begin=end=None
    for t in sorted(arr,key=lambda t:t['table_index']):
        m=list(re.finditer(r'3\.연결재무제표주석|5\.재무제표주석',norm(t['context'])))
        if not m:continue
        kind='CFS' if '연결' in m[-1][0] else 'OFS'
        if begin is None and kind=='CFS':begin=t['table_index']
        elif begin is not None and kind=='OFS' and t['table_index']>begin:end=t['table_index'];break
    return begin,end


def run(tables,p0dir,out,verified=False,source_hash='',scope='FILTERED_JSON_ONLY',p1dir=None):
    p0summary=c.readjson(p0dir/'p0_summary.json')
    if source_hash and p0summary['source_json_sha256']!=source_hash:
        raise ValueError('P0 결과와 입력 원문의 해시가 다릅니다. P0 v0.3을 먼저 재실행하세요.')
    values=readcsv(p0dir/'p0_values_all_vintages.csv')
    core=readcsv(p0dir/'quarterly_account_values.csv')
    byreport=defaultdict(list)
    for t in tables:
        if primary(t):byreport[t['rcept_no']].append(t)
    tmap={t['table_id']:t for t in tables};byp0=defaultdict(list)
    for v in values:byp0[(v['rcept_no'],v['canonical_account'])].append(v)
    ages=[];ageqa=[];ratios=[];reported_rates=[];rate_candidates=[];movements=[];movementqa=[]
    issue=[];report_rows=[];evidence_ids=set()
    # Explicit labels searched independently of whether aging is present.
    rate_terms=['기대신용손실률','기대신용손실율','기대손실률','기대손실율','신용손실률','평균손실률','손상률']
    for receipt,arr in sorted(byreport.items()):
        arr.sort(key=lambda t:t['table_index']);idx={t['table_index']:t for t in arr}
        age_found=0;usable=0;begin,end=bounds(arr)
        for t in arr:
            g=t['grid'];text=norm(str(g))
            if any(term in text for term in rate_terms):
                # Keep prose and matrices for review; never interpret composition percentages as ECL rates.
                rate_candidates.append(t)
            if g and '계정과목' in norm(str(g[0])) and '대손충당금' in norm(str(g[0])) and '설정률' in norm(str(g[0])):
                candidates=[(i,row) for i,row in enumerate(g[1:],1) if len(row)>=5 and norm(row[1])=='매출채권']
                if candidates:
                    evidence_ids.add(t['table_id'])
                    ri,row=candidates[0];rg=num(row[2]);ra=num(row[3]);rp=percent(row[4])
                    curg=[v for v in byp0[(receipt,'trade_receivables_gross')] if v['is_current_period']=='YES']
                    cura=[v for v in byp0[(receipt,'loss_allowance')] if v['is_current_period']=='YES']
                    match=bool(rg is not None and ra is not None and len(curg)==1 and len(cura)==1
                               and abs(rg*1000-D(curg[0]['value_krw']))<=1000 and abs(ra*1000-abs(D(cura[0]['value_krw'])))<=1000)
                    reported_rates.append({**{k:t[k] for k in ['rcept_no','report_nm','filed_date','table_id','source_url','raw_sha256']},
                         'row':ri,'col':4,'period_end':curg[0]['period_end'] if len(curg)==1 else '',
                         'raw_rate':row[4],'reported_allowance_setting_ratio_pct':str(rp) if rp is not None else '',
                         'matches_cfs_gross_and_allowance':match,
                         'definition':'대손충당금 설정률 공시값; 명시적 기대신용손실률과 구분'})
            ari=age_schema(t)
            if ari is not None:
                age_found+=1;evidence_ids.add(t['table_id']);row=g[ari];parts=[num(x) for x in row[1:5]];total=num(row[5])
                declared_unit=None;title=None
                for d in (1,2,3):
                    prev=idx.get(t['table_index']-d)
                    if prev and len(prev['grid'])<=3 and '단위' in norm(str(prev['grid'])) and '천원' in norm(str(prev['grid'])):
                        declared_unit='천원';title=prev['table_id'];break
                if title:evidence_ids.add(title)
                cfs=[v for v in byp0[(receipt,'trade_receivables_gross')] if v['is_current_period']=='YES']
                cfsvalue=D(cfs[0]['value_krw']) if len(cfs)==1 else None
                totaldiff=(total*1000-cfsvalue) if total is not None and cfsvalue is not None else None
                delta=(sum(parts,D(0))-total) if total is not None and None not in parts else None
                shares=[percent(x) for x in g[ari+1][1:5]] if len(g)>ari+1 and norm(g[ari+1][0])=='구성비율' else [None]*4
                errors=[abs(parts[i]/total*100-shares[i]) if parts[i] is not None and total and shares[i] is not None else None for i in range(4)]
                share_ok=all(e is not None and e<=D('0.15') for e in errors)
                # Only explicit statement scope plus a reconciled CFS total is eligible for derived features.
                neighboring=''.join(norm(idx[j]['context']) for j in range(max(0,t['table_index']-6),t['table_index']+1) if j in idx)
                explicit_scope='연결재무제표기준' in neighboring
                ok=bool(declared_unit and delta is not None and abs(delta)<=1 and totaldiff is not None and abs(totaldiff)<=1000 and share_ok and explicit_scope)
                status='ARITHMETIC_AND_SCOPE_CHECKED' if ok else 'REVIEW_REQUIRED'
                if ok:usable+=1
                qa={'rcept_no':receipt,'table_id':t['table_id'],'period_end':t['fiscal_period']+'-'+('31' if t['fiscal_period'][-2:] in ['03','12'] else '30'),
                    'declared_unit':declared_unit or '', 'unit_title_table_id':title or '', 'sum_minus_total_thousand_krw':str(delta) if delta is not None else '',
                    'total_minus_cfs_krw':str(totaldiff) if totaldiff is not None else '', 'explicit_cfs_scope_found':explicit_scope,
                    'reported_percentages_consistent':share_ok,'usable_for_derived_features':ok,'status':status,
                    'note':'소스 금액·단위·추출 오류 가능성은 수정하지 않고 보류. 경과기간을 연체기간으로 단정하지 않음'}
                ageqa.append(qa)
                for col in range(1,5):
                    amount=parts[col-1]*1000 if parts[col-1] is not None and declared_unit else None
                    ages.append({**{k:t[k] for k in ['rcept_no','report_nm','filed_date','table_id','source_url','raw_sha256']},
                        'period_end':qa['period_end'],'aging_bucket':norm(g[0][col]),'lower_month_exclusive':[None,3,6,12][col-1],
                        'upper_month_inclusive':[3,6,12,None][col-1],'row':ari,'col':col,'raw_value':row[col],
                        'declared_unit':declared_unit or '', 'amount_krw_as_declared':str(amount) if amount is not None else '',
                        'reported_share_pct':str(shares[col-1]) if shares[col-1] is not None else '',
                        'computed_share_pct':str(parts[col-1]/total*100) if total and parts[col-1] is not None else '',
                        'quality_status':status,'usable_for_features':ok,'raw_revalidated':verified,
                        'age_basis':'elapsed_period; due-date basis not confirmed'})
            # Normalize only CFS-note allowance movement matrices.
            if begin is None or end is None or not begin<=t['table_index']<end:continue
            if not ('매출채권' in text and '기초' in text and '기말' in text):continue
            if not ('대손상각비' in text or '기대신용손실전(환)입' in text):continue
            header=None;col=None
            for r in g[:4]:
                cols=[j for j,x in enumerate(r) if norm(x)=='매출채권']
                if len(cols)==1:header=r;col=cols[0];break
            if col is None:continue
            evidence_ids.add(t['table_id'])
            movement_unit_ok=any(prev and len(prev['grid'])<=3 and '단위' in norm(str(prev['grid'])) and '천원' in norm(str(prev['grid'])) for prev in [idx.get(t['table_index']-d) for d in (1,2,3)])
            if not movement_unit_ok:
                movementqa.append({'rcept_no':receipt,'table_id':t['table_id'],'window_end':'','status':'UNIT_REVIEW_REQUIRED'})
                continue
            starts=[i for i,r in enumerate(g) if '기초' in norm(''.join(r[:min(2,col)]))]
            ends=[i for i,r in enumerate(g) if '기말' in norm(''.join(r[:min(2,col)]))]
            if len(starts)!=1 or len(ends)!=1:continue
            opening,closing=starts[0],ends[0]
            closingnum=num(g[closing][col]);balances=byp0[(receipt,'loss_allowance')]
            matches=[v for v in balances if closingnum is not None and abs(abs(D(v['value_krw']))-closingnum*1000)<=1000]
            dates=sorted({v['period_end'] for v in matches});period_end=dates[0] if len(dates)==1 else ''
            flow_year=period_end[:4] if period_end else ''
            parts=[];missing=[];begin_amount=num(g[opening][col]);close_amount=closingnum
            for ri in range(opening,closing+1):
                label=' '.join(dict.fromkeys(x for x in g[ri][:col] if x))
                clean=norm(label)
                phase=('opening' if ri==opening else 'closing' if ri==closing else
                       'ecl_charge' if '대손상각비' in clean or '기대신용손실전(환)입' in clean else
                       'reversal' if '환입' in clean else 'writeoff' if '제각' in clean else 'other_change')
                raw=g[ri][col];v=num(raw)
                # Exclude pure category heading, preserve actual blank movement cells.
                if ri not in {opening,closing} and clean in {'금융자산의증가(감소)'}:continue
                if ri not in {opening,closing}:
                    if v is None:missing.append(ri)
                    else:parts.append(v)
                movements.append({**{k:t[k] for k in ['rcept_no','report_nm','filed_date','table_id','source_url','raw_sha256']},
                     'row':ri,'col':col,'phase':phase,'original_label':label,'window_start':flow_year+'-01-01' if flow_year else '',
                     'window_end':period_end,'period_assignment':'MATCHED_CFS_CLOSING_ALLOWANCE' if period_end else 'AMBIGUOUS_OR_MISMATCH',
                     'raw_value':raw,'value_krw':str(v*1000) if v is not None else '',
                     'status':'VALUE_PARSED' if v is not None else 'MISSING_NOT_ZERO','raw_revalidated':verified})
            delta=begin_amount+sum(parts,D(0))-close_amount if begin_amount is not None and close_amount is not None else None
            state=('PERIOD_REVIEW_REQUIRED' if not period_end else 'INCOMPLETE_BLANK_MOVEMENT' if missing else
                   'PASS' if delta==0 else 'ROUNDING_REVIEW' if delta is not None and abs(delta)<=1 else 'FAIL')
            movementqa.append({'rcept_no':receipt,'table_id':t['table_id'],'window_end':period_end,
                   'known_components_residual_thousand_krw':str(delta) if delta is not None else '',
                   'missing_movement_rows':';'.join(map(str,missing)),'status':state})
        report_rows.append({'rcept_no':receipt,'report_nm':arr[0]['report_nm'],'fiscal_period':arr[0]['fiscal_period'],
                            'aging_tables':age_found,'aging_tables_usable':usable,
                            'ecl_rate_status':'CANDIDATE_REVIEW' if any(x['rcept_no']==receipt for x in rate_candidates) else 'NOT_IDENTIFIED_BY_LABEL_SEARCH'})
    # Derived reserve coverage ratio is deliberately NOT called ecl_rate.
    for receipt,arr in sorted(byreport.items()):
        for gross in byp0[(receipt,'trade_receivables_gross')]:
            matches=[v for v in byp0[(receipt,'loss_allowance')] if v['period_end']==gross['period_end']]
            if len(matches)!=1:continue
            loss=matches[0];g=D(gross['value_krw']);a=abs(D(loss['value_krw']))
            ratios.append({'rcept_no':receipt,'filed_date':gross['filed_date'],'period_end':gross['period_end'],
                           'trade_receivables_gross_krw':str(g),'loss_allowance_abs_krw':str(a),
                           'allowance_ratio_pct':str(a/g*100) if g else '', 'ecl_rate':'',
                           'definition':'100 * abs(loss_allowance) / gross_trade_receivables; not a disclosed ECL rate',
                           'gross_value_id':gross['value_id'],'allowance_value_id':loss['value_id'],'raw_revalidated':verified})
    # Latest own-quarter descriptive view. Preserve historical input availability in long data.
    latest={}
    for receipt,arr in sorted(byreport.items()):latest[arr[0]['fiscal_period']]=receipt
    p2=[]
    for period,receipt in sorted(latest.items()):
        if not '2020-03'<=period<='2026-06':continue
        end=period+'-'+('31' if period[-2:] in ['03','12'] else '30')
        ratio=next((r for r in ratios if r['rcept_no']==receipt and r['period_end']==end),None)
        qa=next((r for r in ageqa if r['rcept_no']==receipt),None)
        buckets=[r for r in ages if r['rcept_no']==receipt]
        r={'fiscal_quarter':period[:4]+'Q'+str(int(period[-2:])//3),'period_end':end,'rcept_no':receipt,
           'allowance_ratio_pct':ratio['allowance_ratio_pct'] if ratio else '',
           'reported_allowance_setting_ratio_pct':next((x['reported_allowance_setting_ratio_pct'] for x in reported_rates if x['rcept_no']==receipt),''),
           'reported_setting_rate_matches_cfs':next((x['matches_cfs_gross_and_allowance'] for x in reported_rates if x['rcept_no']==receipt),False),
           'reported_setting_ratio_checked_pct':next((x['reported_allowance_setting_ratio_pct'] for x in reported_rates if x['rcept_no']==receipt and x['matches_cfs_gross_and_allowance']),''), 'ecl_rate':'',
           'ecl_rate_status':'CANDIDATE_REVIEW_NO_FINAL_RATE' if any(x['rcept_no']==receipt for x in rate_candidates) else 'NOT_IDENTIFIED_IN_SEARCHED_TABLES','aging_status':qa['status'] if qa else 'NOT_FOUND',
           'age_gt3m_share_pct':'','age_gt6m_share_pct':'','age_gt12m_share_pct':'',
           'model_ready':'NO_asof_and_definition_review_required'}
        if qa and qa['usable_for_derived_features'] and ratio and len(buckets)==4:
            denominator=D(ratio['trade_receivables_gross_krw']);nums=[D(x['amount_krw_as_declared']) for x in sorted(buckets,key=lambda x:x['col'])]
            r.update(age_gt3m_share_pct=str(sum(nums[1:],D(0))/denominator*100),
                     age_gt6m_share_pct=str(sum(nums[2:],D(0))/denominator*100),age_gt12m_share_pct=str(nums[3]/denominator*100))
        p2.append(r)
    # Convert ALL existing SGA component accounts into a quarter panel; keep cross-report Q4 provisional.
    sga_accounts=sorted({v['canonical_account'] for v in values if v['canonical_account'] not in {'trade_receivables_gross','trade_receivables_net','loss_allowance'}})
    vi=defaultdict(list)
    for v in values:vi[(v['rcept_no'],v['canonical_account'],v['period_end'],v['value_kind'])].append(v)
    def choose(xs):
        if not xs:return None
        direct=[x for x in xs if x['derivation']=='direct_cell'];xs=direct or xs
        return xs[0] if len({x['analysis_value_krw'] for x in xs})==1 else None
    sga_long=[];sga_wide=[]
    for r in p2:
        end=r['period_end'];receipt=r['rcept_no'];year=end[:4];quarter=int(r['fiscal_quarter'][-1]);wide={'fiscal_quarter':r['fiscal_quarter'],'period_end':end,'rcept_no':receipt}
        for account in sga_accounts:
            found=choose(vi[(receipt,account,end,'quarter')])
            if not found and quarter==1:found=choose(vi[(receipt,account,end,'cumulative')])
            amount=found['analysis_value_krw'] if found else '';state='DIRECT' if found and found['derivation']=='direct_cell' else 'SAME_TABLE_DERIVED' if found else 'MISSING'
            ids=found['value_id'] if found else ''
            if not found and quarter==4:
                annual=choose(vi[(receipt,account,end,'annual')]);pr=latest.get(year+'-09','');prior=choose(vi[(pr,account,year+'-09-30','cumulative')])
                if annual and prior:
                    amount=str(D(annual['analysis_value_krw'])-D(prior['analysis_value_krw']));state='CROSS_REPORT_Q4_REVIEW_REQUIRED';ids=annual['value_id']+';'+prior['value_id']
            eok=str(D(amount)/100000000) if amount else ''
            wide[account+'_eok']=eok;wide[account+'_status']=state
            sga_long.append({'fiscal_quarter':r['fiscal_quarter'],'period_end':end,'canonical_account':account,'value_krw':amount,'value_eok':eok,'status':state,'input_value_ids':ids})
        sga_wide.append(wide)
    # Observed mapping ranges are evidence, not a guarantee of unchanged accounting definition.
    mapping_groups=defaultdict(list)
    for v in values:mapping_groups[(v['account_label'],v['canonical_account'])].append(v)
    mappings=[]
    for (label,account),vs in sorted(mapping_groups.items()):
        ts=[tmap[v['table_id']] for v in vs if v['table_id'] in tmap]
        note='매출채권 및 기타채권' if account.startswith('trade_receivables') or account=='loss_allowance' else '판매비와 관리비'
        mappings.append({'original_account_label':label,'canonical_account':account,'statement_basis':'CFS','note_topic':note,
                        'observed_period_start':min(v['period_start'] for v in vs),'observed_period_end':max(v['period_end'] for v in vs),
                        'first_filed_date':min(v['filed_date'] for v in vs),'last_filed_date':max(v['filed_date'] for v in vs),
                        'rcept_nos':';'.join(sorted({v['rcept_no'] for v in vs})),'source_urls':';'.join(sorted({v['source_url'] for v in vs})),'table_ids':';'.join(sorted({v['table_id'] for v in vs})),
                        'validity_status':'OBSERVED_RANGE_ONLY_DEFINITION_REVIEW_REQUIRED'})
    out.mkdir(parents=True,exist_ok=True)
    writecsv(out/'aging_bucket.csv',ages)
    writecsv(out/'aging_quality.csv',ageqa)
    writecsv(out/'p2_features_quarterly.csv',p2)
    writecsv(out/'allowance_ratio_all_vintages.csv',ratios)
    writecsv(out/'reported_allowance_setting_rates.csv',reported_rates)
    writecsv(out/'allowance_movements.csv',movements)
    writecsv(out/'allowance_movement_checks.csv',movementqa)
    writecsv(out/'sga_details_all_accounts_quarterly.csv',sga_wide)
    writecsv(out/'sga_details_all_accounts_long.csv',sga_long)
    writecsv(out/'accounts_mapping_extended.csv',mappings)
    writecsv(out/'p2_report_availability.csv',report_rows)
    c.jsonout(out/'ecl_rate_candidates_for_review.json',rate_candidates)
    c.jsonout(out/'p2_evidence_tables.json',[t for t in tables if t['table_id'] in evidence_ids])
    unresolved=[r for r in sga_long if r['status']!='DIRECT']
    writecsv(out/'remaining_sga_register.csv',unresolved)
    # Transfer the earlier, substantive disagreements into the handoff folder.
    for name in ['historical_consistency.csv','vintage_differences.csv']:
        src=p0dir/name
        if src.exists():c.atomic(out/name,src.read_bytes())
    b2=[]
    if p1dir is not None and (p1dir/'annual_business_summary.csv').exists():
        p1summary=c.readjson(p1dir/'p1_summary.json')
        if source_hash and p1summary['source_json_sha256']!=source_hash:
            raise ValueError('P1 요약과 원문 해시 불일치. P1을 먼저 재실행하세요.')
        annuals={r['year']:r for r in readcsv(p1dir/'annual_business_summary.csv')}
        def own_annual(year,account):
            matches=[v for v in values if v['period_end']==year+'-12-31' and v['value_kind']=='annual'
                     and v['canonical_account']==account and v['is_current_period']=='YES']
            return sorted(matches,key=lambda v:v['rcept_no'])[-1] if matches else None
        needed={year:{account:own_annual(year,account) for account in ['sga_total','bad_debt_expense']} for year in ['2023','2024','2025']}
        if all(year in annuals and all(needed[year].values()) for year in needed):
            gp24=D(annuals['2024']['consolidated_gross_profit_eok']);gp25=D(annuals['2025']['consolidated_gross_profit_eok'])
            sga24=D(needed['2024']['sga_total']['analysis_value_eok']);sga25=D(needed['2025']['sga_total']['analysis_value_eok'])
            bd24=D(needed['2024']['bad_debt_expense']['analysis_value_eok']);bd25=D(needed['2025']['bad_debt_expense']['analysis_value_eok'])
            for label,before,after,expected in [('gross_profit_change',gp24,gp25,D('-139.6')),('sga_change',sga24,sga25,D('246.1')),('bad_debt_expense_change',bd24,bd25,D('114.9'))]:
                delta=after-before;b2.append({'indicator':label,'period_from':'2024','period_to':'2025','unit':'억원',
                    'before':str(before),'after':str(after),'change':str(delta),'plan_rounded_reference':str(expected),
                    'status':'MATCHES_PLAN_ROUNDED_VALUE' if delta.quantize(D('0.1'))==expected else 'REVIEW_REQUIRED',
                    'source':'P0 annual current-period SGA notes + P1 annual consolidated business table'})
            for year,expected in [('2023',D('4.68')),('2025',D('0.20'))]:
                op=D(annuals[year]['consolidated_gross_profit_eok'])-D(needed[year]['sga_total']['analysis_value_eok'])
                margin=op/D(annuals[year]['consolidated_sales_eok'])*100
                b2.append({'indicator':'op_margin_reconstructed','period_from':year,'period_to':year,'unit':'%',
                           'after':str(margin),'plan_rounded_reference':str(expected),
                           'status':'MATCHES_PLAN_ROUNDED_VALUE_JOINT_A_CHECK_REQUIRED' if margin.quantize(D('0.01'))==expected else 'REVIEW_REQUIRED',
                           'source':'(P1 gross profit - P0 SGA)/P1 sales. A original operating-income check remains.'})
            teu23=D(annuals['2023']['container_teu_annual']);teu25=D(annuals['2025']['container_teu_annual'])
            b2.append({'indicator':'container_teu_change','period_from':'2023','period_to':'2025','unit':'TEU',
                       'before':str(teu23),'after':str(teu25),'change':str(teu25-teu23),
                       'status':'MATCHES_PLAN_ENDPOINTS' if teu23==313540 and teu25==370280 else 'REVIEW_REQUIRED',
                       'source':'P1 company logistics TEU; scope differs from consolidated sales'})
    writecsv(out/'b2_plan_numeric_checks.csv',b2,['indicator','period_from','period_to','unit','before','after','change','plan_rounded_reference','status','source'])
    summary={'version':VERSION,'input_tables_scanned':len(tables),'search_scope':scope,'source_json_sha256':source_hash,
             'reports':len(byreport),'aging_tables':len(ageqa),'aging_report_qa':dict(Counter(r['status'] for r in ageqa)),
             'quarter_rows':len(p2),'aging_usable_quarters':sum(r['aging_status']=='ARITHMETIC_AND_SCOPE_CHECKED' for r in p2),
             'allowance_ratio_quarters':sum(bool(r['allowance_ratio_pct']) for r in p2),'reported_setting_rate_quarters':sum(bool(r['reported_allowance_setting_ratio_pct']) for r in p2),'reported_setting_rate_reconciled_quarters':sum(bool(r['reported_setting_ratio_checked_pct']) for r in p2),'explicit_ecl_candidates':len(rate_candidates),
             'explicit_ecl_values_finalized':0,'movement_tables':len(movementqa),'movement_qa':dict(Counter(r['status'] for r in movementqa)),
             'sga_accounts':len(sga_accounts),'sga_quarter_cells':dict(Counter(r['status'] for r in sga_long)),
             'mapping_rows':len(mappings),'b2_numeric_checks':len(b2),'raw_revalidated':verified,'status':'COLLECTION_AND_AVAILABILITY_AUDITED_REVIEW_REQUIRED',
             'limitations':['aging is elapsed period, not necessarily days past due','allowance_ratio is a calculated reserve coverage ratio, not ecl_rate',
                            'ECL label search cannot establish nonexistence under every alternative presentation',
                            'Q4 and historical discrepancies remain provisional; source cells are never repaired by guess',
                            'observed mapping ranges do not prove a single unchanged definition over all dates',
                            'descriptive latest-own-report panel requires an as-of vintage choice before forecasting']}
    c.jsonout(out/'completion_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2));return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--input',type=Path);p.add_argument('--p0-dir',type=Path);p.add_argument('--p1-dir',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-raw',action='store_true')
    a=p.parse_args();root=a.root.resolve()
    try:
        with c.lock(root):
            source=a.input or root/'data/interim/tables.json'
            if a.verify_raw:
                if a.input:raise ValueError('--verify-raw와 --input은 함께 사용하지 않습니다.')
                c.extract(root);tables=scan_original_tables(root);scope='ALL_PRIMARY_XML_TABLES'
            else:tables=c.readjson(source);scope='FILTERED_JSON_ONLY'
            s=run(tables,a.p0_dir or root/'reports/p0_full',a.output or root/'reports/b_remaining',a.verify_raw,hashlib.sha256(source.read_bytes()).hexdigest(),scope,a.p1_dir or root/'reports/p1_annual')
    except (RuntimeError,ValueError,KeyError,FileNotFoundError,IndexError) as e:print('ERROR:',str(e),file=sys.stderr);sys.exit(2)
