#!/usr/bin/env python3
"""Assign the small pilot reviewer/review-lead role set."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PRODUCTION_DB = (ROOT / "src" / "database" / "dmv_bus_stops.db").resolve()
ROLES = ("reviewer", "review_lead", "owner")


def set_reviewer_role(conn, reviewer_id, role):
    if role not in ROLES:
        raise ValueError(f"role must be one of: {', '.join(ROLES)}")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(community_reviewers)")}
    if "role" not in columns:
        raise RuntimeError("reviewer role migration is required")
    row = conn.execute(
        "SELECT id,role FROM community_reviewers WHERE id=?", (reviewer_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"reviewer {reviewer_id} does not exist")
    before = row[1]
    with conn:
        conn.execute(
            "UPDATE community_reviewers SET role=? WHERE id=?", (role, reviewer_id)
        )
    return {"reviewer_id": reviewer_id, "before": before, "after": role}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path,
                        help="explicit SQLite database path")
    parser.add_argument("--reviewer-id", required=True, type=int)
    parser.add_argument("--role", required=True, choices=ROLES)
    parser.add_argument(
        "--allow-production-database", action="store_true",
        help="explicitly authorize the repository production database",
    )
    args = parser.parse_args(argv)
    target = args.db.resolve()
    if target == DEFAULT_PRODUCTION_DB and not args.allow_production_database:
        parser.error(
            "refusing the production database without --allow-production-database"
        )
    if not target.is_file():
        parser.error(f"database does not exist: {target}")
    conn = sqlite3.connect(target)
    try:
        result = set_reviewer_role(conn, args.reviewer_id, args.role)
    finally:
        conn.close()
    print(
        f"Reviewer {result['reviewer_id']}: "
        f"{result['before']} -> {result['after']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
