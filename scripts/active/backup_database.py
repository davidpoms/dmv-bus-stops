"""Create and verify an online SQLite backup without changing the source database."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def create_verified_backup(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise ValueError("source database does not exist")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing backup: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{source.as_posix()}?mode=ro"
    try:
        with closing(sqlite3.connect(source_uri, uri=True)) as source_conn:
            with closing(sqlite3.connect(destination)) as backup_conn:
                source_conn.backup(backup_conn)
        with closing(sqlite3.connect(
            f"file:{destination.as_posix()}?mode=ro", uri=True
        )) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
            active_stops = conn.execute(
                "SELECT COUNT(*) FROM stop_gtfs_status WHERE current_gtfs=1"
            ).fetchone()[0]
            reviewers = conn.execute("SELECT COUNT(*) FROM community_reviewers").fetchone()[0]
            observations = conn.execute("SELECT COUNT(*) FROM stop_observations").fetchone()[0]
        if integrity != "ok" or foreign_keys:
            raise RuntimeError("backup verification failed")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_sha256": sha256(source),
        "backup": str(destination),
        "backup_sha256": sha256(destination),
        "integrity_check": integrity,
        "foreign_key_violations": foreign_keys,
        "active_stops": active_stops,
        "reviewers": reviewers,
        "observations": observations,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    result = create_verified_backup(args.source, args.output)
    output = json.dumps(result, indent=2)
    if args.manifest:
        if args.manifest.exists():
            raise FileExistsError(f"refusing to overwrite existing manifest: {args.manifest}")
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
