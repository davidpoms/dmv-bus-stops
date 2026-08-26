"""Read-only route-link integrity checks for a selected database."""

import argparse
import os
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))

CHECKS = (
    ("stop_routes total", "SELECT COUNT(*) FROM stop_routes"),
    ("stop_routes without matching routes", """
        SELECT COUNT(*) FROM stop_routes sr
        LEFT JOIN routes r ON sr.route_id=r.id WHERE r.id IS NULL
    """),
    ("physical stops with routes", """
        SELECT COUNT(DISTINCT ps.id) FROM physical_stops ps
        JOIN physical_stop_members psm ON ps.id=psm.physical_stop_id
        JOIN stop_routes sr ON psm.bus_stop_id=sr.stop_id
    """),
    ("physical stops total", "SELECT COUNT(*) FROM physical_stops"),
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
