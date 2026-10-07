"""Private display of verified durable awards; no current-progress evaluation."""

from .integrity import check_award_integrity
from .schema import connection
from .permanent_schema import TABLES, check_schema
from .permanent import check_claim_integrity, check_geography_integrity


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
            achievements.append((row["earned_at_utc"], row["award_id"],
                                 {field: row[field] for field in DISPLAY_FIELDS}))
        installed = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        # Explorer-only databases stay compatible. A partial migration fails
        # closed; reads never install or repair recognition schema.
        if installed & TABLES.keys():
            check_schema(conn)
            for row in conn.execute("SELECT physical_stop_id,earned_at_utc FROM recognition_first_look_claims WHERE reviewer_id=? ORDER BY earned_at_utc,physical_stop_id", (reviewer_id,)):
                check_claim_integrity(conn, row["physical_stop_id"])
                achievements.append((row["earned_at_utc"], "first-look:" + str(row["physical_stop_id"]).zfill(20),
                                     {"family": "first_look", "recognition_kind": "claim",
                                      "earned_at_utc": row["earned_at_utc"]}))
            for row in conn.execute("SELECT * FROM recognition_geography_awards WHERE reviewer_id=? ORDER BY earned_at_utc,award_id", (reviewer_id,)):
                check_geography_integrity(conn, row["award_id"])
                label = conn.execute("SELECT display_label FROM recognition_geography_scope_identities WHERE scope_key=?", (row["scope_key"],)).fetchone()[0]
                item = {key: row[key] for key in ("scope_key", "tier_key", "numerator", "denominator", "percentage", "earned_at_utc")}
                item.update(family="geography_steward", scope_label=label, recognition_kind="award")
                achievements.append((row["earned_at_utc"], row["award_id"], item))
        achievements = [item for _, _, item in sorted(achievements, key=lambda entry: entry[:2])]
    return {"available": True, "achievements": achievements}
