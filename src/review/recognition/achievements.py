"""Private display of verified durable awards; no current-progress evaluation."""

from .integrity import check_award_integrity
from .schema import connection


DISPLAY_FIELDS = ("family", "scope_key", "tier_key", "numerator", "earned_at_utc")


def build_achievements(database, reviewer_id, reviewer_key):
    """Authenticate and verify all owner awards in one read-only snapshot.

    Integrity failures propagate; never return a partial set as verified.
    Missing recognition tables are unavailable, not an empty award history.
    """
    with connection(database) as conn:
        conn.execute("BEGIN")
        if conn.execute("SELECT 1 FROM community_reviewers WHERE id=? AND reviewer_key=?",
                        (reviewer_id, reviewer_key)).fetchone() is None:
            raise PermissionError("Reviewer session does not match an account")
        rows = conn.execute("""SELECT award_id,family,scope_key,tier_key,numerator,earned_at_utc
            FROM recognition_awards WHERE reviewer_id=? ORDER BY earned_at_utc,award_id""",
                            (reviewer_id,)).fetchall()
        achievements = []
        for row in rows:
            check_award_integrity(conn, row["award_id"])
            achievements.append({field: row[field] for field in DISPLAY_FIELDS})
    return {"available": True, "achievements": achievements}
