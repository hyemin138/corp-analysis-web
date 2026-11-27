"""Package a verified internal C V2 release. No collection, fitting or source mutations."""
from pathlib import Path
import csv,hashlib,json,os,re,subprocess,tempfile,zipfile
R=Path(__file__).resolve().parents[1];BASE=R.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 status=json.loads((R/'qa/v2/RELEASE_DECISION.json').read_text(encoding='utf8'))
 assert status['mandatory_defects']==0 and status['vera_complete'] and status['editor_complete'],'Independent review is not closed'
 for x in json.loads((R/'qa/v2/REVIEW_FREEZE_FINAL.json').read_text(encoding='utf8')):
  assert sha(R/x['path'])==x['sha256'],'Frozen source/build mismatch'
 for x in json.loads((R/'qa/v2/SOURCE_PROTECTION.json').read_text(encoding='utf8')):
  assert sha(Path(x['original_path']))==x['sha256'],'Original source changed'
 assert (R/'public/data/market.json').read_bytes()==(R/'dist/data/market.json').read_bytes()
 tracked=subprocess.check_output(['git','ls-files','-z','.'],cwd=R).decode().split('\0')
 files={R/p for p in tracked if p}
 files.update(p for p in (R/'dist').rglob('*') if p.is_file() and p.relative_to(R).as_posix()!='dist/data/market.json')
 files.update([R/'public/data/market.json',R/'data/LOCAL_IMPORT.json'])
 files.update(p for p in (R/'qa/v2').rglob('*') if p.is_file() and 'dispatch' not in p.parts and p.suffix not in {'.pyc','.zip'})
 for name in ['browser-v2-final.json','code-v2-final.tap','data-v2-final.tap']:
  p=R/'qa'/name;assert p.exists(),f'Missing final evidence: {name}';files.add(p)
 files={p for p in files if p.name not in {'FILE_MANIFEST.csv','ZIP_VERIFICATION.json'} and '__pycache__' not in p.parts}
 for p in files:
  assert p.is_relative_to(R) and p.stat().st_size<20_000_000
  if p.suffix in {'.ts','.tsx','.mjs','.py','.md','.csv','.json','.tap','.txt'}:
   assert not re.search(rb'sk-ant-[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----',p.read_bytes()),'Possible credential; value suppressed'
 rows=[{'path':p.relative_to(R).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
 with (R/'qa/v2/FILE_MANIFEST.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['path','bytes','sha256'],lineterminator='\n');w.writeheader();w.writerows(rows)
 files.add(R/'qa/v2/FILE_MANIFEST.csv')
 zpath=BASE/'TAEWOONG_C_DASHBOARD_V2_FINAL.zip';verification=BASE/'TAEWOONG_C_DASHBOARD_V2_FINAL_VERIFICATION.json'
 if zpath.exists():assert verification.exists() and json.loads(verification.read_text(encoding='utf8'))['zip_sha256']==sha(zpath),'Unrelated existing ZIP'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(files):z.write(p,'TAEWOONG_C_DASHBOARD_V2/'+p.relative_to(R).as_posix())
 scratch=Path(os.environ.get('ORCA_CHAT_SCRATCH_DIR',tempfile.gettempdir()));extract=Path(tempfile.mkdtemp(prefix='c_v2_verified_',dir=scratch));members=[]
 with zipfile.ZipFile(zpath) as z:
  assert z.testzip() is None
  for info in z.infolist():
   target=(extract/info.filename).resolve();assert target.is_relative_to(extract.resolve())
   rel=info.filename.split('/',1)[1];h=hashlib.sha256(z.read(info)).hexdigest();assert h==sha(R/rel)
   members.append({'path':rel,'sha256':h,'crc32':f'{info.CRC:08x}'})
  z.extractall(extract)
 app=extract/'TAEWOONG_C_DASHBOARD_V2';d=json.loads((app/'public/data/market.json').read_text(encoding='utf8'))
 assert len(d['states'])==201 and len(d['runs'])==62 and len(d['transitions'])==53
 assert not (app/'dist/data/market.json').exists(),'Duplicate snapshot shipped'
 result={'status':'PASS','zip_path':str(zpath),'zip_bytes':zpath.stat().st_size,'zip_sha256':sha(zpath),'files':len(files),'CRC':'PASS','member_SHA256':'PASS','private_snapshot_copies':1,'snapshot_sha256':sha(app/'public/data/market.json'),'source_originals_unchanged':11,'extracted_path':str(app),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip(),'offline_execution_check':'PENDING_SEPARATE_SMOKE','members':members}
 verification.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');zpath.with_suffix('.zip.sha256').write_text(result['zip_sha256']+'  '+zpath.name+'\n',encoding='utf8')
 print(json.dumps({k:v for k,v in result.items() if k!='members'},ensure_ascii=False))
if __name__=='__main__':main()
