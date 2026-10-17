#!/usr/bin/env python3
"""Offline self-test of the backup bundle validator: no Docker/database needed."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile

source = Path(__file__).resolve().parent / 'validate-backup.py'
spec = importlib.util.spec_from_file_location('validate_backup', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def bundle(directory, member='photos/example.webp', symlink=False):
    stamp = '20261015T170000Z'
    database = directory / f'velmora-db-{stamp}.dump'
    media = directory / f'velmora-media-{stamp}.tar.gz'
    checksums = database.with_suffix('.sha256')
    database.write_bytes(b'PGDMP\x00test-fixture')
    with tarfile.open(media, 'w:gz') as archive:
        item = tarfile.TarInfo(member)
        if symlink:
            item.type = tarfile.SYMTYPE
            item.linkname = '../../outside'
            archive.addfile(item)
        else:
            payload = b'content'
            item.size = len(payload)
            archive.addfile(item, io.BytesIO(payload))
    checksums.write_text(''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in (database, media)))
    return database, media


with tempfile.TemporaryDirectory() as temporary:
    folder = Path(temporary)
    db, media = bundle(folder)
    module.validate(db)
    media.write_bytes(media.read_bytes() + b'corruption')
    try:
        module.validate(db)
    except ValueError as exc:
        assert 'SHA256' in str(exc)
    else:
        raise AssertionError('Tampered media passed checksum')
    db, media = bundle(folder, '../outside')
    try:
        module.validate(db)
    except ValueError as exc:
        assert 'Unsafe media path' in str(exc)
    else:
        raise AssertionError('Traversal archive passed')
    db, media = bundle(folder, symlink=True)
    try:
        module.validate(db)
    except ValueError as exc:
        assert 'Unsafe media member type' in str(exc)
    else:
        raise AssertionError('Symlink archive passed')
print('Backup-validator regression tests passed')
