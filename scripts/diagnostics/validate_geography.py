"""Read-only geography integrity checks for a selected database."""

import argparse
import os
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))

CHECKS = (
    ("physical stop count", "SELECT COUNT(*) FROM physical_stops"),
    ("jurisdiction count", "SELECT COUNT(*) FROM stop_jurisdiction"),
    ("missing states", "SELECT COUNT(*) FROM stop_jurisdiction WHERE state IS NULL"),
    ("DC missing wards", """
        SELECT COUNT(*) FROM stop_jurisdiction
        WHERE state='DC' AND dc_ward IS NULL
    """),
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    database = args.database.resolve()
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn:
        for name, sql in CHECKS:
            print(f"{name}: {conn.execute(sql).fetchone()[0]}")


if __name__ == "__main__":
    main()
