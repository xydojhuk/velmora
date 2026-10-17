#!/usr/bin/env python3
"""Fail if a public release tree contains local state, secrets or generated outputs.

This is a path-policy check, NOT a replacement for gitleaks scanning file contents.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCKED_DIRS = {'.bootstrap', '.local', 'backups', 'node_modules', 'dist', 'build', '.git', '.pytest_cache', '__pycache__', '.venv', 'venv', '.mypy_cache', '.ruff_cache', '.tox', '.nox', 'media', 'uploads', 'storage', 'release', '.secrets', 'secrets'}
BLOCKED_EXACT = {'id_rsa', 'id_ed25519', '.pypirc', '.npmrc', 'installed.lock', '.env', '.coverage', 'coverage.xml'}
BLOCKED_EXTS = {'.pem', '.p12', '.pfx', '.key', '.dump', '.sqlite', '.sqlite3', '.db', '.zip', '.tgz', '.pyc', '.pyo'}


def forbidden(path: str) -> bool:
    name = Path(path).name
    parts = Path(path).parts
    if any(part in BLOCKED_DIRS for part in parts):
        return True
    if name in BLOCKED_EXACT or name.lower().endswith(tuple(BLOCKED_EXTS)) or name.lower().endswith(('.tar.gz', '.sql.gz')):
        return True
    if name == '.env' or (name.startswith('.env.') and not name.endswith('.example')):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tracked', action='store_true', help='check Git index instead of a directory')
    parser.add_argument('directory', nargs='?', type=Path)
    args = parser.parse_args()
    if args.tracked:
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'])
        items = [p.decode('utf-8', 'surrogateescape') for p in raw.split(b'\0') if p]
        base = ROOT
    else:
        base = args.directory or ROOT
        items = []
        for top, dirs, files in os.walk(base, followlinks=False):
            # Do not prune blocked directories: detect them.
            items.extend(str((Path(top) / name).relative_to(base)) for name in dirs + files)
    bad = sorted(path for path in items if forbidden(path))
    if bad:
        print('Release tree contains forbidden paths:', file=sys.stderr)
        for name in bad: print(f'  {name}', file=sys.stderr)
        return 1
    print(f'Release paths clean ({len(items)} examined)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
