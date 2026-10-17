#!/usr/bin/env python3
"""Sync Vite-compatible storefront defaults from backend canonical Python data."""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'backend/app/store_defaults.py'
TARGET = ROOT / 'frontend/src/state/storefrontDefaults.json'


def expected_data() -> str:
    spec = importlib.util.spec_from_file_location('velmora_store_defaults', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return json.dumps(module.default_storefront(), indent=2, ensure_ascii=False) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='fail if generated JSON is stale')
    args = parser.parse_args()
    expected = expected_data()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding='utf-8') != expected:
            print('Storefront defaults are out of sync. Run: python scripts/sync-storefront-defaults.py', file=sys.stderr)
            return 1
        print('Storefront defaults in sync')
    else:
        TARGET.write_text(expected, encoding='utf-8')
        print(f'Updated {TARGET.relative_to(ROOT)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
