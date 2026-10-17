#!/usr/bin/env python3
"""Validate an original pg_dump -Fc + media.tar.gz + SHA256 bundle before restore.

This deliberately does not extract any archive or execute PostgreSQL commands.
The authoritative database integrity check remains `pg_restore --list`.
"""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

MAX_MEMBERS = 250_000
MAX_MEMBER_BYTES = 512 * 1024**2
MAX_TOTAL_BYTES = 64 * 1024**3


def paths_for(db_file: Path) -> tuple[Path, Path]:
    if not re.fullmatch(r"velmora-db-[0-9]{8}T[0-9]{6}Z\.dump", db_file.name):
        raise ValueError("Expected a timestamped Velmora database dump filename")
    media = db_file.with_name(db_file.name.replace("velmora-db-", "velmora-media-").replace(".dump", ".tar.gz"))
    checksums = db_file.with_suffix(".sha256")
    return media, checksums


def verify_hashes(db_file: Path, media_file: Path, checksum_file: Path) -> None:
    lines = checksum_file.read_text(encoding="utf-8").splitlines()
    expected = {}
    for line in lines:
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match[2] in expected:
            raise ValueError("Malformed or duplicate SHA256 manifest entry")
        expected[match[2]] = match[1]
    if set(expected) != {db_file.name, media_file.name}:
        raise ValueError("SHA256 manifest must contain exactly this DB and media pair")
    for path in (db_file, media_file):
        sha = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(chunk)
        if sha.hexdigest() != expected[path.name]:
            raise ValueError(f"SHA256 mismatch: {path.name}")


def verify_media(media_file: Path) -> None:
    total = 0
    count = 0
    with tarfile.open(media_file, "r:gz") as archive:
        for member in archive:
            count += 1
            if count > MAX_MEMBERS:
                raise ValueError("Media archive contains too many entries")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe media member type: {member.name!r}")
            name = member.name.removeprefix("./")
            path = PurePosixPath(name)
            if (path.is_absolute() or ".." in path.parts or not name or
                    "\\" in name or "\x00" in name or name.startswith("-")):
                raise ValueError(f"Unsafe media path: {member.name!r}")
            if member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"Oversized media member: {member.name!r}")
            total += member.size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("Uncompressed media archive exceeds safety limit")


def validate(db_file: Path) -> None:
    if not db_file.is_file():
        raise ValueError("Database dump is missing")
    media, checksums = paths_for(db_file)
    for path in (db_file, media, checksums):
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty backup component: {path.name}")
    if db_file.open("rb").read(5) != b"PGDMP":
        raise ValueError("Database backup is not a PostgreSQL custom-format dump")
    verify_hashes(db_file, media, checksums)
    verify_media(media)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database_dump", type=Path)
    args = parser.parse_args()
    try:
        validate(args.database_dump.resolve(strict=True))
    except (OSError, ValueError, tarfile.TarError, EOFError) as exc:
        print(f"BACKUP INVALID: {exc}", file=sys.stderr)
        return 1
    print("BACKUP VALID: header, paired SHA256 checksums and media archive paths/types")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
