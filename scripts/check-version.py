#!/usr/bin/env python3
"""Check/sync package metadata with the single canonical root VERSION file."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version):
    raise SystemExit('Invalid root VERSION')
parser = argparse.ArgumentParser()
parser.add_argument('--sync', action='store_true', help='Update npm package and lockfile version metadata from VERSION')
args = parser.parse_args()
for filename in ('frontend/package.json', 'frontend/package-lock.json'):
    path = ROOT / filename
    data = json.loads(path.read_text(encoding='utf-8'))
    mismatch = data.get('version') != version or (filename.endswith('lock.json') and data.get('packages', {}).get('', {}).get('version') != version)
    if mismatch and not args.sync:
        raise SystemExit(f'{filename} differs from root VERSION; run python3 scripts/check-version.py --sync')
    if mismatch:
        data['version'] = version
        if filename.endswith('lock.json'):
            data['packages']['']['version'] = version
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'Velmora version metadata OK: {version}')
