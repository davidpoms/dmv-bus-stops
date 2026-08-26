"""Generate the deterministic, read-only Physical Stop Identity V2 proposal."""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.processing.physical_stop_v2_proposal import (
    canonical_json, generate_manifest, manifest_sha256,
)

DEFAULT_DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    uri = f"file:{args.db.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        manifest = generate_manifest(conn, validate=args.validate)
    finally:
        conn.close()
    fingerprint = manifest_sha256(manifest)
    if args.out:
        args.out.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    print(json.dumps({
        "proposal_version": manifest["proposal_version"],
        "canonical_manifest_sha256": fingerprint,
        "automatic_parent_count": manifest["automatic_parent_count"],
        "child_group_count": manifest["child_group_count"],
        "manual_exception_count": len(manifest["manual_exceptions"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
