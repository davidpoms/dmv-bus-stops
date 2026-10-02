"""Owner-only recent completed reviews, projected without persistent changes."""

import heapq
import sqlite3
from pathlib import Path

from src.review.progress import completion_instant


ACTIVITY_SQL = """
SELECT a.id, a.stop_id, p.primary_name, a.completed_at
FROM stop_review_assignments a
JOIN physical_stops p ON p.id=a.stop_id
JOIN stop_observations o ON o.assignment_id=a.id
WHERE a.reviewer_id=? AND a.status='completed'
  AND o.source='community_review'
  AND o.reviewer_id=a.reviewer_id AND o.physical_stop_id=a.stop_id
  AND (SELECT COUNT(*) FROM stop_observations evidence
       WHERE evidence.assignment_id=a.id AND evidence.source='community_review')=1
"""


def build_recent_activity(database, reviewer_id, reviewer_key):
    """Validate ownership and read history in one read-only snapshot.

    Count community evidence before identity matching so conflicting duplicates
    cannot disappear in the join. Other observation sources are not completions.
    Parse before limiting; SQLite text ordering cannot order mixed UTC offsets.
    """
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        if conn.execute(
            "SELECT 1 FROM community_reviewers WHERE id=? AND reviewer_key=?",
            (reviewer_id, reviewer_key),
        ).fetchone() is None:
            raise PermissionError("Reviewer session does not match an account")
        qualified = (
            (instant, assignment, stop, name)
            for assignment, stop, name, timestamp in conn.execute(ACTIVITY_SQL, (reviewer_id,))
            if (instant := completion_instant(timestamp)) is not None
        )
        recent = heapq.nlargest(5, qualified, key=lambda row: (row[0], row[1]))
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()
    return {
        "available": True,
        "activities": [
            {"stop_id": stop, "stop_name": name or "Bus Stop",
             "completed_at": instant.isoformat().replace("+00:00", "Z")}
            for instant, _assignment, stop, name in recent
        ],
        "limitations": [
            "Only completed reviews with matching community evidence and usable completion times are shown.",
            "Stop names are current labels, not historical snapshots.",
        ],
    }
