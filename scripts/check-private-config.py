#!/usr/bin/env python3
"""Private preflight: compare env KEYS without printing secret VALUES."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

def parse_keys(path):
    keys = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name = line.split('=', 1)[0].strip()
        if name.startswith('export '):
            name = name[7:].strip()
        keys.add(name)
    return keys

def main():
    actual = ROOT / '.env.local'
    example = ROOT / '.env.local.example'
    if not actual.exists():
        print('No .env.local: compare skipped (safe for a new checkout).')
        return 0
    missing = parse_keys(actual) - parse_keys(example)
    extra = parse_keys(example) - parse_keys(actual)
    print('Missing from .env.local.example:', ', '.join(sorted(missing)) if missing else 'none')
    print('Unused in .env.local:', ', '.join(sorted(extra)) if extra else 'none')
    return 1 if missing or extra else 0

if __name__ == '__main__':
    sys.exit(main())
