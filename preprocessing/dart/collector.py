#!/usr/bin/env python3
"""TRACK2 B collector. Python 3.10+, standard library only; no LLM calls."""
import argparse
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager

VERSION = '0.1.0'
BASE = 'https://opendart.fss.or.kr/api/'
CATEGORIES = {
    'sga': ['판매비와관리비', '판매비및관리비', '대손상각비', '급여', '감가상각비'],
    'receivables': ['매출채권', '손실충당금', '대손충당금', '기대신용손실'],
    'segments': ['부문', '종합물류', '종속회사'],
    'teu': ['TEU', '물동량', '컨테이너'],
    'transport': ['해상', '철도', '트럭', '항공', '터미널', '매입'],
    'aging': ['연령분석', '연체', '손실률'],
}
ACCOUNTS = {
    'bad_debt_expense': 'sga', 'salary_sga': 'sga', 'depreciation_sga': 'sga',
    'sga_total': 'sga', 'trade_receivables': 'receivables',
    'loss_allowance': 'receivables', 'aging_bucket': 'aging', 'ecl_rate': 'aging',
    'logistics_segment_sales': 'segments', 'logistics_segment_cost': 'segments',
    'subsidiary_sales': 'segments', 'subsidiary_cost': 'segments',
    'elimination_sales': 'segments', 'elimination_cost': 'segments',
    'container_teu_annual': 'teu', 'sea_purchase': 'transport',
    'rail_purchase': 'transport', 'truck_purchase': 'transport',
    'air_purchase': 'transport', 'terminal_purchase': 'transport',
}
P0 = ['bad_debt_expense', 'salary_sga', 'depreciation_sga', 'trade_receivables', 'loss_allowance']
REVIEW_FIELDS = ['table_id', 'row', 'col', 'account_label', 'canonical_account', 'raw_value',
                 'unit', 'scope', 'period_start', 'period_end', 'value_kind',
                 'reviewed', 'reviewer', 'note']
VALUE_FIELDS = ['table_id', 'rcept_no', 'report_nm', 'filed_date', 'source_url', 'raw_sha256',
                'member', 'row', 'col', 'account_label', 'canonical_account', 'raw_value',
                'unit', 'scope', 'period_start', 'period_end', 'value_kind', 'value',
                'value_eok', 'reviewer', 'note']


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def readjson(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def atomic(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, p)


def jsonout(p, obj):
    atomic(p, json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8'))


def csvout(p, rows, fields):
    s = io.StringIO(newline='')
    w = csv.DictWriter(s, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    atomic(p, s.getvalue().encode('utf-8-sig'))


def csvin(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


@contextmanager
def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    p = root / 'collector.lock'
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('동시 실행 또는 남은 잠금: collector.lock. 실행 중인 프로세스가 없는지 확인하세요.')
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        p.unlink(missing_ok=True)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'state.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS requests (
          id TEXT PRIMARY KEY, endpoint TEXT, params TEXT, status TEXT,
          attempts INTEGER DEFAULT 0, path TEXT, digest TEXT, error TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS calls (at REAL);
        ''')

    def status(self):
        return dict(self.db.execute('SELECT status,count(*) FROM requests GROUP BY status').fetchall())

    def get(self, rid):
        return self.db.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()

    def verify(self, row):
        p = self.root / row['path']
        meta = p.with_suffix(p.suffix + '.json')
        if not p.exists() or sha(p.read_bytes()) != row['digest'] or not meta.exists():
            raise RuntimeError('원본 무결성 실패: ' + row['id'])
        if readjson(meta)['sha256'] != row['digest']:
            raise RuntimeError('메타데이터 해시 불일치: ' + row['id'])
        return p.read_bytes()

    def persist(self, rid, endpoint, params, payload, meta=None):
        digest = sha(payload)
        path = Path('data/raw') / (digest + '.bin')
        p = self.root / path
        if p.exists():
            if sha(p.read_bytes()) != digest:
                raise RuntimeError('기존 원본 훼손')
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as f:
                f.write(payload)
        sidecar = p.with_suffix('.bin.json')
        if not sidecar.exists():
            jsonout(sidecar, {'sha256': digest, 'collected_at': now(),
                             'endpoint': endpoint, 'params': params,
                             'terms': 'OpenDART 이용약관 확인필요', **(meta or {})})
        self.db.execute('''INSERT INTO requests(id,endpoint,params,status,path,digest,updated)
          VALUES(?,?,?,'COMPLETE',?,?,?) ON CONFLICT(id) DO UPDATE SET
          status='COMPLETE',path=excluded.path,digest=excluded.digest,error=NULL,updated=excluded.updated''',
                        (rid, endpoint, json.dumps(params), str(path), digest, now()))
        self.db.commit()
        return payload

    def request(self, endpoint, params, key, budget=200):
        rid = sha((endpoint + json.dumps(params, sort_keys=True)).encode())
        self.db.execute('INSERT OR IGNORE INTO requests(id,endpoint,params,status,updated) VALUES(?,?,?,\'PENDING\',?)',
                        (rid, endpoint, json.dumps(params), now()))
        self.db.commit()
        previous = self.get(rid)
        if previous['status'] == 'COMPLETE':
            return self.verify(previous)
        if previous['status'] == 'FAILED':
            raise RuntimeError('FAILED 요청: 상태 확인 후 retry 명령으로 재설정하세요.')
        if not key:
            self.mark(rid, 'BLOCKED', 'API_KEY_MISSING')
            raise RuntimeError('DART_API_KEY가 없습니다. 키는 로컬 .env에만 입력하세요.')
        for attempt in range(3):
            used = self.db.execute('SELECT count(*) FROM calls WHERE at>?', (time.time()-86400,)).fetchone()[0]
            if used >= budget:
                self.mark(rid, 'BLOCKED', 'LOCAL_24H_BUDGET')
                raise RuntimeError('로컬 24시간 요청 예산 소진. 다음에 재실행하세요.')
            self.db.execute('INSERT INTO calls VALUES(?)', (time.time(),))
            self.db.execute('UPDATE requests SET attempts=attempts+1 WHERE id=?', (rid,))
            self.db.commit()
            query = urllib.parse.urlencode({**params, 'crtfc_key': key})
            try:
                req = urllib.request.Request(BASE + endpoint + '?' + query, headers={'User-Agent': 'Track2BCollector/' + VERSION})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    payload = resp.read(64*1024*1024 + 1)
                if len(payload) > 64*1024*1024:
                    self.mark(rid, 'FAILED', 'RESPONSE_TOO_LARGE')
                    raise RuntimeError('응답 크기 제한 초과')
                if not payload:
                    raise OSError('EMPTY')
                status = None
                if payload.lstrip().startswith(b'{'):
                    status = json.loads(payload).get('status')
                elif not payload.startswith(b'PK'):
                    try:
                        status = ET.fromstring(payload).findtext('status')
                    except ET.ParseError:
                        pass
                if status and status != '000':
                    if status == '013' and endpoint == 'list.json':
                        return self.persist(rid, endpoint, params, payload)
                    if status in {'010','011','012','020','901','800'}:
                        self.mark(rid, 'BLOCKED', 'DART_' + status)
                        raise RuntimeError('DART 차단 코드 ' + status + '. 키·한도·점검 상태를 확인하세요.')
                    if status == '900':
                        raise OSError('DART_900')
                    self.mark(rid, 'FAILED', 'DART_' + status)
                    raise RuntimeError('DART 응답 코드 ' + status)
                if endpoint.endswith('.xml') and not zipfile.is_zipfile(io.BytesIO(payload)):
                    self.mark(rid, 'FAILED', 'NOT_ZIP')
                    raise RuntimeError('예상 ZIP 형식이 아닙니다.')
                return self.persist(rid, endpoint, params, payload)
            except urllib.error.HTTPError as e:
                error = 'HTTP_' + str(e.code)
                if e.code not in {429,500,502,503,504}:
                    self.mark(rid, 'BLOCKED', error)
                    raise RuntimeError(error) from None
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                error = 'NETWORK_TIMEOUT_EMPTY_OR_FORMAT'
            self.mark(rid, 'RETRY', error)
            if attempt < 2:
                time.sleep(2 ** attempt)
        self.mark(rid, 'FAILED', error)
        raise RuntimeError('3회 시도 실패. status 확인 후 retry 명령으로 재개하세요.')

    def mark(self, rid, status, error):
        self.db.execute('UPDATE requests SET status=?,error=?,updated=? WHERE id=?', (status,error,now(),rid))
        self.db.commit()


class Tables(HTMLParser):
    """DART XML/HTML tables. Grid coordinates expand rowspan/colspan."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.stack = []
        self.context = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            self.stack.append({'rows': [], 'cells': None, 'cell': None, 'context': self.context[-2400:]})
        elif self.stack:
            t = self.stack[-1]
            if tag == 'tr':
                t['cells'] = []
            elif tag in ('td','th','te'):
                def span(name):
                    try: return max(1, min(100, int(attrs.get(name, '1'))))
                    except ValueError: return 1
                t['cell'] = {'text':'', 'rs':span('rowspan'), 'cs':span('colspan')}
            elif tag in ('br','p') and t['cell'] is not None:
                t['cell']['text'] += ' '

    def handle_data(self, data):
        if self.stack and self.stack[-1]['cell'] is not None:
            self.stack[-1]['cell']['text'] += data
        elif not self.stack:
            self.context = (self.context + ' ' + data)[-4000:]

    def handle_endtag(self, tag):
        if not self.stack: return
        t = self.stack[-1]
        if tag in ('td','th','te') and t['cell'] is not None:
            if t['cells'] is not None: t['cells'].append(t['cell'])
            t['cell'] = None
        elif tag == 'tr' and t['cells'] is not None:
            t['rows'].append(t['cells'])
            t['cells'] = None
        elif tag == 'table':
            self.stack.pop()
            if t['rows']: self.tables.append(t)


def grid(rows):
    result = []
    spans = {}
    for r, cells in enumerate(rows):
        line = {}; c = 0
        for cell in cells:
            while (r,c) in spans:
                c += 1
            text = re.sub(r'\s+', ' ', cell['text']).strip()
            for rr in range(r, r+cell['rs']):
                for cc in range(c, c+cell['cs']):
                    spans[(rr,cc)] = text
            c += cell['cs']
        cols = [cc for rr,cc in spans if rr == r]
        line = [spans.get((r,cc), '') for cc in range(max(cols, default=-1)+1)]
        result.append(line)
    return result


def decode(data):
    encs = ['utf-8-sig', 'cp949', 'euc-kr']
    m = re.search(br'encoding=[\"\x27]([\w-]+)', data[:250])
    if m: encs.insert(0, m[1].decode('ascii'))
    for enc in encs:
        try: return data.decode(enc)
        except (UnicodeError, LookupError): pass
    raise ValueError('문자 인코딩 확인필요')


def zip_members(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    if sum(i.file_size for i in z.infolist()) > 256*1024*1024:
        raise ValueError('ZIP 해제 크기 제한 초과')
    return [(i.filename, z.read(i)) for i in z.infolist()
            if i.filename.lower().endswith(('.xml','.html','.htm')) and not i.is_dir()]


def classify(text):
    text = re.sub(r'\s+', '', text).upper()
    return [cat for cat, terms in CATEGORIES.items() if any(x.upper() in text for x in terms)]


def extract(root):
    store = Store(root)
    records = []
    for row in store.db.execute("SELECT * FROM requests WHERE status='COMPLETE' AND endpoint='manual'"):
        payload = store.verify(row)
        meta = json.loads(row['params'])
        for member, content in zip_members(payload):
            parser = Tables(); parser.feed(decode(content)); parser.close()
            for idx, table in enumerate(parser.tables):
                cells = grid(table['rows'])
                cats = classify(table['context'] + str(cells))
                if not cats: continue
                tid = sha((row['digest'] + member + str(idx)).encode())[:24]
                record = {'table_id':tid, 'raw_sha256':row['digest'], 'member':member,
                          'table_index':idx, 'context':table['context'], 'grid':cells,
                          'categories':cats, 'scope':'UNCONFIRMED', **meta}
                record['source_url'] = 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + meta['rcept_no']
                records.append(record)
    # Same bytes may be registered twice; table IDs are content-based.
    records = list({r['table_id']:r for r in records}.values())
    jsonout(root/'data/interim/tables.json', records)
    csvout(root/'data/interim/candidate_tables.csv',
           [{**r, 'categories':';'.join(r['categories']), 'rows':len(r['grid'])} for r in records],
           ['table_id','rcept_no','report_nm','filed_date','categories','scope','member','table_index','rows','context','source_url','raw_sha256'])
    # Human-review workbook is not silently regenerated over an edited copy.
    review = root/'data/review_values.csv'
    if not review.exists(): csvout(review, [], REVIEW_FIELDS)
    print('후보 표:', len(records))
    print('표 확인 명령: python collector.py inspect TABLE_ID')
    return records


def number(text):
    text = str(text).strip().replace(',', '').replace(' ', '').replace('\u00a0','').replace('−','-')
    if text in {'','-','–','—'}: raise ValueError('빈칸 또는 대시는 0으로 해석하지 않습니다.')
    if text.startswith('(') and text.endswith(')'): text = '-' + text[1:-1]
    if not re.fullmatch(r'-?\d+(\.\d+)?', text): raise ValueError('숫자 표기 확인필요: ' + text)
    return Decimal(text)


def reviewed_values(root, review):
    # Re-extract from hash-checked original rather than trusting editable tables.json.
    tables = {t['table_id']:t for t in extract(root)}
    output = []
    seen = set()
    units = {'원':Decimal(1), '천원':Decimal(1000), '백만원':Decimal(1000000),
             '억원':Decimal(100000000), 'TEU':Decimal(1), '%':Decimal(1)}
    for n, r in enumerate(csvin(review), 2):
        if r.get('reviewed','').upper() != 'YES': continue
        if not r['reviewer'].strip(): raise ValueError(f'{n}행 검수자 누락')
        t = tables[r['table_id']]
        ri, ci = int(r['row']), int(r['col'])
        if ri < 0 or ci < 0: raise ValueError('음수 좌표 금지')
        raw = t['grid'][ri][ci]
        if r['raw_value'].strip() != raw.strip(): raise ValueError(f'{n}행 원본 셀과 불일치')
        account = r['canonical_account']
        if account not in ACCOUNTS: raise ValueError('등록되지 않은 계정: ' + account)
        if r['scope'] not in {'CFS','BUSINESS'}: raise ValueError('CFS 또는 BUSINESS 범위를 명시하세요.')
        if ACCOUNTS[account] in {'sga','receivables','aging'} and r['scope'] != 'CFS':
            raise ValueError('주석 재무항목은 CFS만 허용')
        unit = r['unit']; v = number(raw) * units[unit]
        cat = ACCOUNTS[account]
        if (cat == 'teu' and unit != 'TEU') or (cat not in {'teu','aging'} and unit not in {'원','천원','백만원','억원'}):
            raise ValueError('계정과 단위 불일치')
        start = dt.date.fromisoformat(r['period_start']); end = dt.date.fromisoformat(r['period_end'])
        kind = r['value_kind']
        if end < start or kind not in {'quarter','cumulative','balance','annual'}:
            raise ValueError('기간·유형 확인필요')
        if cat in {'teu','segments','transport'} and (kind != 'annual' or start != dt.date(end.year,1,1) or end != dt.date(end.year,12,31)):
            raise ValueError('연간 진단자료의 기간은 1/1~12/31이어야 합니다.')
        if cat == 'receivables' and (kind != 'balance' or start != end): raise ValueError('채권 잔액은 동일한 기간말 날짜 사용')
        if cat == 'sga' and kind not in {'quarter','cumulative','annual'}: raise ValueError('판관비는 기간 흐름 자료')
        if end.month not in {3,6,9,12} or (end+dt.timedelta(days=1)).month == end.month:
            raise ValueError('분기말 날짜 확인필요')
        qstart = dt.date(end.year, end.month-2, 1)
        if kind == 'quarter' and start != qstart: raise ValueError('단독분기 시작일 불일치')
        if kind in {'cumulative','annual'} and start != dt.date(end.year,1,1): raise ValueError('누적 시작일 불일치')
        if kind == 'annual' and end.month != 12: raise ValueError('연간 종료일 불일치')
        identity = (t['rcept_no'],account,r['period_start'],r['period_end'],kind)
        if identity in seen: raise ValueError('동일 공시·계정·기간 중복. 원인 확인 후 하나만 검수하세요.')
        seen.add(identity)
        output.append({**t, **r, 'raw_value':raw, 'value':str(v),
                       'value_eok':str(v / Decimal(100000000)) if unit not in {'TEU','%'} else ''})
    return output


def export(root, review):
    values = reviewed_values(root, review)
    out = root/'data/processed'
    csvout(out/'reviewed_values.csv', values, VALUE_FIELDS)
    # Preserve report versions and period types. Quarterization only within same report/prior period end.
    quarterly = []
    for v in values:
        if ACCOUNTS[v['canonical_account']] not in {'sga','receivables','aging'}: continue
        end = dt.date.fromisoformat(v['period_end']); q = (end.month-1)//3+1
        item = {**v,'fiscal_quarter':f'{end.year}Q{q}', 'quarter_value':'', 'derivation':'', 'prior_rcept_no':''}
        if v['value_kind'] in {'quarter','balance'} or (q == 1 and v['value_kind'] == 'cumulative'):
            item.update(quarter_value=v['value'], derivation='direct')
        elif v['value_kind'] in {'annual','cumulative'}:
            prev_end = (dt.date(end.year,end.month-2,1)-dt.timedelta(days=1)).isoformat()
            # Cross-report subtraction may mix revisions. Require explicit independent review later.
            prev = [p for p in values if p['rcept_no']==v['rcept_no'] and p['canonical_account']==v['canonical_account']
                    and p['period_start']==v['period_start'] and p['period_end']==prev_end
                    and p['unit']==v['unit'] and p['value_kind']=='cumulative']
            if len(prev)==1:
                item.update(quarter_value=str(Decimal(v['value'])-Decimal(prev[0]['value'])),
                            derivation='same_report_cumulative_difference',prior_rcept_no=prev[0]['rcept_no'])
            else: item['derivation']='REVIEW_REQUIRED_prior_cumulative_or_revision_alignment'
        quarterly.append(item)
    csvout(out/'sga_receivables_quarterly.csv',quarterly, VALUE_FIELDS+['fiscal_quarter','quarter_value','derivation','prior_rcept_no'])
    for filename,cats in [('segments_teu_annual.csv',{'segments','teu'}),('transport_cost_annual.csv',{'transport'})]:
        csvout(out/filename,[v for v in values if ACCOUNTS[v['canonical_account']] in cats],VALUE_FIELDS)
    csvout(out/'accounts_mapping.csv',values,['account_label','canonical_account','rcept_no','member','table_id','period_start','period_end','scope','reviewer'])
    # Full target coverage; missing is never zero and no PASS until reviewed.
    coverage = []
    for year in range(2020,2027):
        for q in range(1,5):
            if (year,q)>(2026,2): continue
            for account in P0:
                matches = [x for x in quarterly if x['fiscal_quarter']==f'{year}Q{q}' and x['canonical_account']==account]
                ready = [x for x in matches if x['quarter_value']!='']
                coverage.append({'fiscal_quarter':f'{year}Q{q}','canonical_account':account,
                                 'status':'REVIEWED_VALUE' if ready else '확인필요',
                                 'source_count':len(matches),'revision_selection':'필요' if len(matches)>1 else '',
                                 'note':'공시버전별 보존; 모델 투입 전 as-of 선택 필요'})
    csvout(out/'qa_notes.csv',coverage,['fiscal_quarter','canonical_account','status','source_count','revision_selection','note'])
    jsonout(root/'reports/summary.json', {'version':VERSION,'generated_at':now(),'reviewed_values':len(values),
          'target_quarters':26,'coverage_cells':len(coverage), 'covered_cells':sum(x['status']=='REVIEWED_VALUE' for x in coverage),
          'status':'REVIEW_REQUIRED' if any(x['status']!='REVIEWED_VALUE' or x['revision_selection'] for x in coverage) else 'REVIEWED_COVERAGE',
          'limitations':['파일럿 실공시 검증 전','검수된 좌표와 숫자는 원본에서 재대조',
                         '계정·단위·연결범위·기간은 검수자의 확인에 의존','공시일은 일자 단위; 장중 as-of 사용 금지',
                         '정정 공시 버전 자동 통합하지 않음','합계 검산은 별도 reconcile 명령 필요']})
    print('검수값:',len(values),'| 자료 공백:',sum(x['status']!='REVIEWED_VALUE' for x in coverage))


def loadkey(root):
    key = os.environ.get('DART_API_KEY','')
    p = root/'.env'
    if not key and p.exists():
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('DART_API_KEY='): key = line.split('=',1)[1].strip().strip('\"\x27')
    if key and not re.fullmatch(r'[A-Za-z0-9]{40}',key): raise ValueError('DART_API_KEY 형식 확인필요')
    return key


def discover(root, args):
    store = Store(root); key=loadkey(root)
    data = store.request('corpCode.xml',{},key,args.budget)
    matches=[]
    for _, content in zip_members(data):
        for item in ET.fromstring(content).findall('list'):
            if item.findtext('corp_name')=='태웅로직스': matches.append(item.findtext('corp_code'))
    if len(matches)!=1: raise ValueError('태웅로직스 고유번호를 하나로 확인할 수 없습니다.')
    items=[]
    for year in range(args.start_year, int(args.freeze[:4])+1):
        page=1
        while True:
            p={'corp_code':matches[0],'bgn_de':f'{year}0101','end_de':min(f'{year}1231', args.freeze),
               'pblntf_ty':'A','last_reprt_at':'N','page_count':'100','page_no':str(page)}
            obj=json.loads(store.request('list.json',p,key,args.budget))
            if obj.get('status')=='013': break
            for report in obj.get('list',[]):
                name=report['report_nm']; m=re.search(r'(사업|반기|분기)보고서\s*\((\d{4})\.(\d{2})\)',name)
                if not m: continue
                y,month=int(m[2]),int(m[3])
                if (args.start_year,3)<=(y,month)<=(2026,6):
                    items.append({'rcept_no':report['rcept_no'],'report_nm':name,
                                  'filed_date':report['rcept_dt'], 'fiscal_period':f'{y}-{month:02}',
                                  'corp_code':matches[0]})
            if page>=int(obj.get('total_page',1)): break
            page+=1
    items=sorted({x['rcept_no']:x for x in items}.values(),key=lambda x:x['rcept_no'])
    path=root/'state/catalog.csv'
    # Catalog snapshots are frozen by explicit date.
    csvout(root/f'state/catalog_{args.freeze}.csv',items,['rcept_no','report_nm','filed_date','fiscal_period','corp_code'])
    csvout(path,items,['rcept_no','report_nm','filed_date','fiscal_period','corp_code'])
    print('정기보고서(정정 포함):',len(items))


def collect(root,args):
    catalog=csvin(root/'state/catalog.csv')
    if args.cmd == 'resume' and (root/'state/collection_plan.json').exists():
        saved=readjson(root/'state/collection_plan.json')
        selected=saved['reports']; args.pilot=saved['pilot']
    elif not args.all_reports:
        args.pilot=True
        # Annual + interim pilot; do not confuse request attempts with report count.
        selected=[]
        for term,period in [('사업보고서','2025-12'),('반기보고서','2026-06')]:
            found=[r for r in catalog if term in r['report_nm'] and r['fiscal_period']==period]
            if found: selected.append(found[-1])
        if len(selected)!=2: raise ValueError('2025 사업·2026 반기 파일럿 보고서 확인필요. catalog.csv를 확인하세요.')
    else: selected=catalog
    jsonout(root/'state/collection_plan.json',{'pilot':args.pilot,'reports':selected,'created_at':now()})
    store=Store(root)
    if args.dry_run:
        pending=sum(not store.get(sha(('document.xml'+json.dumps({'rcept_no':r['rcept_no']},sort_keys=True)).encode())) or
                    store.get(sha(('document.xml'+json.dumps({'rcept_no':r['rcept_no']},sort_keys=True)).encode()))['status']!='COMPLETE' for r in selected)
        print('대상 공시:',len(selected),'| 남은 문서 요청:',pending,'| 최초 시도 상한:',pending*3,'| 용량: 확인필요')
        return
    key=loadkey(root)
    for r in selected:
        store.request('document.xml',{'rcept_no':r['rcept_no']},key,args.budget)
        req=store.get(sha(('document.xml'+json.dumps({'rcept_no':r['rcept_no']},sort_keys=True)).encode()))
        # Report metadata belongs to separate registration; original API response preserved.
        store.persist('report-'+r['rcept_no'],'manual',r,store.verify(req))
        print(r['rcept_no'],'COMPLETE')


def reconcile(root,path):
    # Explicit arithmetic checks; no automatic claim that a chosen list is exhaustive.
    tables={t['table_id']:t for t in extract(root)}
    results=[]
    for r in csvin(path):
        t=tables[r['table_id']]; g=t['grid']; col=int(r['col']); total=int(r['total_row'])
        parts=[int(x) for x in r['component_rows'].split(';')]
        if min([col,total]+parts)<0 or len(parts)!=len(set(parts)) or total in parts: raise ValueError('합계 좌표 중복/음수')
        expected=number(g[total][col]); actual=sum((number(g[i][col]) for i in parts),Decimal(0))
        tolerance=number(r.get('tolerance','0'))
        if tolerance<0: raise ValueError('음수 허용오차')
        results.append({**r,'sum':str(actual),'total':str(expected),'difference':str(actual-expected),
                        'status':'PASS' if abs(actual-expected)<=tolerance else 'FAIL',
                        'source_url':t['source_url'],'raw_sha256':t['raw_sha256']})
    csvout(root/'reports/reconciliation.csv',results,['table_id','col','total_row','component_rows','tolerance','sum','total','difference','status','source_url','raw_sha256'])
    print('검산:',len(results),'| FAIL:',sum(x['status']=='FAIL' for x in results))
    return any(x['status']=='FAIL' for x in results)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--budget',type=int,default=200,help='로컬 최근24시간 최대 요청수(재시도 포함)')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('init')
    d=sub.add_parser('discover'); d.add_argument('--start-year',type=int,default=2020); d.add_argument('--freeze',default='20261110')
    c=sub.add_parser('collect',aliases=['resume']); c.add_argument('--pilot',action='store_true'); c.add_argument('--all',dest='all_reports',action='store_true'); c.add_argument('--dry-run',action='store_true')
    sub.add_parser('status'); sub.add_parser('validate'); sub.add_parser('retry'); sub.add_parser('extract')
    prep=sub.add_parser('prepare-review'); prep.add_argument('table_id')
    i=sub.add_parser('inspect'); i.add_argument('table_id')
    i=sub.add_parser('import-file'); i.add_argument('file',type=Path); i.add_argument('--receipt',required=True); i.add_argument('--report-name',required=True); i.add_argument('--filed-date',required=True)
    e=sub.add_parser('export'); e.add_argument('--review',type=Path)
    r=sub.add_parser('reconcile'); r.add_argument('file',type=Path)
    a=p.parse_args(); root=a.root.resolve()
    with lock(root):
        if a.cmd=='init':
            for path in ['data/raw','data/interim','data/processed','state','reports','logs']: (root/path).mkdir(parents=True,exist_ok=True)
            Store(root); print('초기화 완료. .env.example을 .env로 복사하고 로컬에서 키 입력.')
        elif a.cmd=='discover':
            dt.datetime.strptime(a.freeze,'%Y%m%d')
            if not 2020<=a.start_year<=2026: raise ValueError('start-year 범위 2020~2026')
            discover(root,a)
        elif a.cmd in {'collect','resume'}: collect(root,a)
        elif a.cmd=='status':
            s=Store(root); print(json.dumps(s.status(),ensure_ascii=False))
            for row in s.db.execute("SELECT id,status,attempts,error FROM requests WHERE status!='COMPLETE'"): print(dict(row))
        elif a.cmd=='retry':
            s=Store(root); s.db.execute("UPDATE requests SET status='PENDING' WHERE status IN ('FAILED','BLOCKED','RETRY')"); s.db.commit(); print('미완료 요청 재시도 준비')
        elif a.cmd=='validate':
            s=Store(root); count=0
            for row in s.db.execute("SELECT * FROM requests WHERE status='COMPLETE'"): s.verify(row); count+=1
            jsonout(root/'reports/integrity.json',{'checked':count,'integrity':'PASS' if count else 'NOT_COLLECTED','states':s.status(),'at':now()})
            print('원본 해시 검사:',count,'| 실제 자료 완성도 검증과 별개')
        elif a.cmd=='extract': extract(root)
        elif a.cmd=='prepare-review':
            tables=extract(root); found=[t for t in tables if t['table_id']==a.table_id]
            if not found: raise ValueError('table_id 없음')
            t=found[0]; path=root/'data/review_values.csv'; rows=csvin(path)
            existing={(r['table_id'],r['row'],r['col']) for r in rows}
            for ri,line in enumerate(t['grid']):
                label=next((x for x in line if x and not re.fullmatch(r'[\d,.() -]+',x)), '')
                for ci,cell in enumerate(line):
                    try: number(cell)
                    except ValueError: continue
                    if (t['table_id'],str(ri),str(ci)) in existing: continue
                    r=dict.fromkeys(REVIEW_FIELDS,''); r.update(table_id=t['table_id'],row=str(ri),col=str(ci),account_label=label,raw_value=cell)
                    rows.append(r)
            csvout(path,rows,REVIEW_FIELDS); print('검수 후보 추가:',path,'| reviewed=YES로 지정한 행만 내보냅니다.')
        elif a.cmd=='inspect':
            records=readjson(root/'data/interim/tables.json'); found=[t for t in records if t['table_id']==a.table_id]
            if not found: raise ValueError('table_id 없음')
            t=found[0]; print('출처:',t['source_url'],'\n문맥(연결·별도 수동확인):',t['context'])
            for n,row in enumerate(t['grid']): print(n, ' | '.join(f'[{i}] {v}' for i,v in enumerate(row)))
        elif a.cmd=='import-file':
            if not re.fullmatch(r'\d{14}',a.receipt): raise ValueError('접수번호 14자리')
            dt.datetime.strptime(a.filed_date,'%Y%m%d')
            data=a.file.read_bytes()
            if not zipfile.is_zipfile(io.BytesIO(data)): raise ValueError('공식 원문 ZIP을 입력하세요. PDF/XBRL TSV는 현재 미지원')
            zip_members(data)
            Store(root).persist('report-'+a.receipt,'manual',{'rcept_no':a.receipt,'report_nm':a.report_name,'filed_date':a.filed_date},data,
                                {'imported_file':a.file.name,'origin_verified':False})
            print('원본 등록 완료(제공자 진위는 수동 확인)')
        elif a.cmd=='export': export(root,a.review or root/'data/review_values.csv')
        elif a.cmd=='reconcile':
            if reconcile(root,a.file): return 1
    return 0


if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,ValueError,KeyError,IndexError,FileNotFoundError,InvalidOperation) as exc:
        # Never print URL/request objects which might include API keys.
        message=str(exc)
        secret=os.environ.get('DART_API_KEY','')
        if secret: message=message.replace(secret,'[REDACTED]')
        print('ERROR:',message,file=sys.stderr); sys.exit(2)
