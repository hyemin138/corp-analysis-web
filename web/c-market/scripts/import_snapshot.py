"""Import a private team snapshot locally. No collection, modelling or remote upload."""
from pathlib import Path
import argparse, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--from-app', required=True, type=Path,
                    help='Extracted TAEWOONG_C_DASHBOARD_APP directory from the private team ZIP')
args = parser.parse_args()
source = args.from_app.resolve()
snapshot = source / 'public/data/market.json'
manifest = json.loads((source / 'data/SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for entry in manifest:
    blob = (source / entry['file']).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == entry['sha256'], 'Input source hash mismatch'
data = json.loads(snapshot.read_text(encoding='utf-8'))
assert data['meta']['schemaVersion'] == 'c-market-desk/1.0'
assert data['meta']['researchStatus'] == 'CONDITIONAL_REVIEW'
assert data['meta']['newForecastEnabled'] is False
assert (len(data['states']), len(data['runs']), len(data['transitions'])) == (201, 62, 53)
complete = [x for x in data['states'] if x['primary_eligible'] is True]
assert len(complete) == 192
assert len({x['representative_regime'] for x in complete}) == 9
evaluated = [x for x in data['predictions'] if x['actual_available'] is True
             and x['target'] == 'EUMED_H28'
             and x['phase'] in {'EXPLORATORY_2025', 'EXPLORATORY_2026'}]
assert len(evaluated) == 880 and len({x['origin'] for x in evaluated}) == 80
target = ROOT / 'public/data/market.json'
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(snapshot, target)
(ROOT / 'data').mkdir(exist_ok=True)
audit = {'snapshot_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
         'source_files_verified': len(manifest), 'schema': data['meta']['schemaVersion'],
         'source_version': data['meta']['sourceVersion'], 'status': 'LOCAL_IMPORT_VERIFIED',
         'public_redistribution': 'NOT_CLEARED; excluded from Git'}
(ROOT / 'data/LOCAL_IMPORT.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps(audit))
