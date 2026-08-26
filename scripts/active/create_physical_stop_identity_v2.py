"""Install additive Physical Stop Identity V2 foundation tables."""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.processing.physical_stop_identity_v2 import ensure_identity_schema

DEFAULT_DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("db", nargs="?", type=Path, default=DEFAULT_DB)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if not args.apply:
        print(f"Dry run only: would install V2 identity tables in {args.db}")
        return 0
    conn = sqlite3.connect(args.db)
    try:
        with conn:
            ensure_identity_schema(conn)
    finally:
        conn.close()
    print(f"Installed V2 identity foundation in {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
