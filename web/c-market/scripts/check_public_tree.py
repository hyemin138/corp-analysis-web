"""Check staged C changes before publishing; never print secret values."""
from pathlib import Path
import subprocess, re, json, argparse
ROOT = Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',help='Scan committed changes from this base to HEAD; default is staged changes');args=parser.parse_args()
comparison=[args.base,'HEAD'] if args.base else ['--cached']
paths = subprocess.check_output(['git', 'diff',*comparison, '--name-only', '-z'], cwd=ROOT).decode().split('\0')
paths = [p for p in paths if p]
deleted=set(subprocess.check_output(['git','diff',*comparison,'--diff-filter=D','--name-only','-z'],cwd=ROOT).decode().split('\0'))
assert paths, 'No changed paths'
for path in paths:
    assert path.startswith('web/c-market/'), 'Change outside C scope'
    relative = path.removeprefix('web/c-market/')
    assert not any(p in relative.split('/') for p in ['node_modules','dist','qa','.env']), 'Private/generated path staged'
    assert not relative.startswith(('data/','public/data/')), 'Private snapshot path staged'
    if path in deleted:continue
    blob = subprocess.check_output(['git', 'show', ('HEAD:' if args.base else ':') + path], cwd=ROOT)
    assert len(blob) < 1_000_000, 'Unexpected large public file'
    text = blob.decode('utf-8-sig')
    assert not re.search(r'sk-ant-[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----', text), 'Possible credential; value suppressed'
unchanged = subprocess.run(['git','diff','--quiet','origin/main','--','README.md','.gitignore','analysis','db','preprocessing','web/README.md'],cwd=ROOT).returncode == 0
assert unchanged, 'Existing team files changed'
print(json.dumps({'status':'PASS','changed_files':len(paths),'deleted_files':len([p for p in paths if p in deleted]),'mode':'committed' if args.base else 'staged','scope':'C only','existing_team_files_unchanged':True,'private_data_staged':False,'credential_pattern_matches':0}))
