"""Rebuild canonical shelter/bench status for current GTFS stops."""

import argparse
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.amenities.status_synthesis import rebuild_stop_amenity_status


DEFAULT_DB = Path("src/database/dmv_bus_stops.db")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    conn = sqlite3.connect(args.db)
    try:
        rows = rebuild_stop_amenity_status(conn)
        print(f"Rebuilt {len(rows)} canonical amenity status rows in {args.db}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
