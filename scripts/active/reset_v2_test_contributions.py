"""ONE-TIME PRE-VOLUNTEER reset of disposable test contributions for V2 cutover.

This is not a routine migration or reconciliation strategy. After real volunteer
work begins, reviewer accounts and contribution history are durable.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_DATABASE = Path(os.environ.get(
    "DMV_BUS_STOPS_DB", ROOT / "src" / "database" / "dmv_bus_stops.db"
))
CONFIRMATION = "RESET DISPOSABLE V2 TEST CONTRIBUTIONS"

# Child-to-parent order. This list is deliberately narrow and audited.
TABLES = (
    "reviewer_login_tokens", "reviewer_auth_attempts", "community_reviewer_routes",
    "stop_observations",
    "stop_review_assignments", "stop_consensus", "community_stewardships",
    "review_feedback", "community_requests", "community_reviewers",
)


def reset_test_contributions(conn, *, confirmation, allow_default=False,
                             database_path=None):
    if confirmation != CONFIRMATION:
        raise ValueError(f"confirmation must exactly equal: {CONFIRMATION}")
    if database_path is not None:
        target = Path(database_path).resolve()
        if target == DEFAULT_DATABASE.resolve() and not allow_default:
            raise ValueError("refusing the default database without --allow-default-database")
    existing = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in TABLES if table in existing}
    with conn:
        for table in TABLES:
            if table in existing:
                conn.execute(f"DELETE FROM {table}")
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ONE-TIME PRE-VOLUNTEER destructive reset of test contributions only."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--allow-default-database", action="store_true")
    args = parser.parse_args(argv)
    conn = sqlite3.connect(args.db)
    try:
        counts = reset_test_contributions(
            conn, confirmation=args.confirm, allow_default=args.allow_default_database,
            database_path=args.db,
        )
    finally:
        conn.close()
    print("Deleted disposable contribution rows:")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
