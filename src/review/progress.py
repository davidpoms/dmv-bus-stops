"""Read-only current progress, not a permanent achievement ledger."""

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.amenities.status_synthesis import canonical_dc_ward


# Current audited label crosswalks, not immutable award identities. Arlington's
# source is Census place GEOID 5103000 (CDP); stop_jurisdiction stores labels.
SCOPES = (
    ("dc_anc:1D", "dc_anc", "Neighborhood Steward — ANC 1D"),
    ("dc_anc:6D", "dc_anc", "Neighborhood Steward — ANC 6D"),
    ("dc_ward:1", "dc_ward", "Ward Steward — Ward 1"),
    ("dc_ward:6", "dc_ward", "Ward Steward — Ward 6"),
    ("census_place:5103000", "census_place", "Community Steward — Arlington"),
)

# Count community observations BEFORE identity validation: a mismatched second
# observation must invalidate the entire assignment, not disappear in a JOIN.
HISTORY_SQL = """
WITH owner_stops AS (
    SELECT DISTINCT stop_id FROM stop_review_assignments
    WHERE reviewer_id=? AND status='completed'
), candidates AS (
    SELECT a.id, a.stop_id, a.reviewer_id, a.completed_at,
           o.reviewer_id AS observation_reviewer,
           o.physical_stop_id AS observation_stop,
           COUNT(*) OVER (PARTITION BY a.id) AS observation_count
    FROM stop_review_assignments a
    JOIN owner_stops t ON t.stop_id=a.stop_id
    JOIN stop_observations o ON o.assignment_id=a.id
    JOIN physical_stops p ON p.id=a.stop_id
    JOIN community_reviewers r ON r.id=a.reviewer_id
    WHERE a.status='completed' AND o.source='community_review'
)
SELECT id,stop_id,reviewer_id,completed_at FROM candidates
WHERE observation_count=1 AND observation_reviewer=reviewer_id
  AND observation_stop=stop_id
"""

MEMBERSHIP_SQL = """
SELECT DISTINCT p.id,j.state,j.county,j.municipality,j.dc_ward,j.dc_anc
FROM physical_stops p
JOIN stop_gtfs_status s ON s.physical_stop_id=p.id AND s.current_gtfs=1
JOIN stop_jurisdiction j ON j.stop_id=p.id
WHERE (j.state='DC' AND (j.dc_anc IN ('1D','6D')
       OR canonical_dc_ward(j.dc_ward) IN ('1','6')))
   OR (j.state='VA' AND j.county='Arlington' AND j.municipality='Arlington')
"""


def completion_instant(value):
    """Accept the app's SQLite UTC format or an explicitly offset ISO instant.

    The inspected completion writer uses CURRENT_TIMESTAMP. Other naive formats
    have no established timezone provenance; never fall back to observed_at.
    """
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
            value,
        ):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        pass
    return None


def explorer_progress(total):
    thresholds = [5, 20, 50, 100]
    next_threshold = next((n for n in thresholds if n > total), None)
    return {
        "total": total, "configured_thresholds": thresholds,
        "crossed_thresholds": [n for n in thresholds if n <= total],
        "next_threshold": next_threshold,
        "remaining": next_threshold - total if next_threshold is not None else None,
        "all_milestones_reached": next_threshold is None,
    }


def geography_progress(scope, numerator, denominator):
    eligible = denominator >= 10
    percentages = ([25, 50, 75, 100] if denominator < 100 else [10, 25, 50, 75]) if eligible else []
    minimum = 5 if denominator < 100 else 10
    tiers = [{"percentage": p, "required_count": max(minimum, (denominator * p + 99) // 100)}
             for p in percentages]
    crossed = [t["percentage"] for t in tiers if numerator >= t["required_count"]]
    next_tier = next((t for t in tiers if numerator < t["required_count"]), None)
    return {
        "scope_key": scope[0], "family": "geography_steward",
        "dimension": scope[1], "display_title": scope[2],
        "numerator": numerator, "denominator": denominator,
        "current_percentage": 100 * numerator / denominator if denominator else None,
        "configured_tiers": tiers, "crossed_tiers": crossed,
        "next_tier_percentage": next_tier["percentage"] if next_tier else None,
        "required_count": next_tier["required_count"] if next_tier else None,
        "remaining": next_tier["required_count"] - numerator if next_tier else None,
        "eligible": eligible,
        "state": "ineligible" if not eligible else "all_milestones_reached" if not next_tier
                 else "no_progress" if numerator == 0 else "in_progress",
    }


def featured_geography(geographies):
    candidates = [g for g in geographies if g["eligible"] and g["numerator"] > 0]
    pending = [g for g in candidates if g["remaining"] is not None]
    # min is stable on ties, preserving the configured whitelist order.
    return min(pending, key=lambda g: g["remaining"]) if pending else next(iter(candidates), None)


def build_progress(database, reviewer_id, reviewer_key):
    """Own one short read snapshot; return only private aggregate projections.

    No account/schema creation or writes, even if the selected file is absent.
    PermissionError denotes a stale/mismatched authenticated session.
    """
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        owner = conn.execute(
            "SELECT display_name FROM community_reviewers WHERE id=? AND reviewer_key=?",
            (reviewer_id, reviewer_key),
        ).fetchone()
        if owner is None:
            raise PermissionError("Reviewer session does not match an account")
        as_of = datetime.now(timezone.utc).isoformat(timespec="seconds")
        history = conn.execute(HISTORY_SQL, (reviewer_id,)).fetchall()
        conn.create_function("canonical_dc_ward", 1, canonical_dc_ward, deterministic=True)
        memberships = conn.execute(MEMBERSHIP_SQL).fetchall()
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()

    qualified = [(assignment, stop, reviewer, instant)
                 for assignment, stop, reviewer, timestamp in history
                 if (instant := completion_instant(timestamp)) is not None]
    reviewed = {stop for _, stop, reviewer, _ in qualified if reviewer == reviewer_id}
    winners = {}
    for assignment, stop, reviewer, instant in qualified:
        if stop in reviewed:
            candidate = (instant, assignment, reviewer)
            if stop not in winners or candidate < winners[stop]:
                winners[stop] = candidate
    members = [set() for _ in SCOPES]
    for stop, state, county, municipality, ward, anc in memberships:
        matches = (state == "DC" and anc == "1D", state == "DC" and anc == "6D",
                   state == "DC" and canonical_dc_ward(ward) == "1",
                   state == "DC" and canonical_dc_ward(ward) == "6",
                   state == "VA" and county == "Arlington" and municipality == "Arlington")
        for group, match in zip(members, matches):
            if match:
                group.add(stop)
    geographies = [geography_progress(scope, len(group & reviewed), len(group))
                   for scope, group in zip(SCOPES, members)]
    return {
        "as_of": as_of, "display_name": owner[0] or "Community Volunteer",
        "distinct_stops_documented": len(reviewed), "explorer": explorer_progress(len(reviewed)),
        "first_looks": {
            "available": True, "count": sum(w[2] == reviewer_id for w in winners.values()),
            "provisional": True, "basis": "Qualifying completion instant, then numeric assignment ID.",
            "limitation": "Late qualifying history or corrected evidence can change this count.",
        },
        "geographies": geographies, "featured_geography": featured_geography(geographies),
        "limitations": [
            "Current progress only; crossed milestones are not permanent earned awards.",
            "Active network, geography membership and qualifying history can change progress.",
            "Only five approved current-progress scopes are included; identities are current label crosswalks.",
            "Ambiguous assignments and unusable completion timestamps are omitted.",
        ],
    }
