"""Rebuild canonical amenity status and review priority derived tables."""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.amenities.review_priority import rebuild_review_priority
from src.amenities.status_synthesis import rebuild_stop_amenity_status

DATABASE_PATH = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", BASE_DIR / "src" / "database" / "dmv_bus_stops.db"
))


def rebuild(database_path=DATABASE_PATH):
    conn = sqlite3.connect(database_path)
    try:
        rebuild_stop_amenity_status(conn)
        rows = rebuild_review_priority(conn)
        print(f"Rebuilt {len(rows):,} amenity review-priority rows")
        return rows
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", nargs="?", type=Path, default=DATABASE_PATH)
    args = parser.parse_args()
    rebuild(args.database)


if __name__ == "__main__":
    main()
