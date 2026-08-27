"""Read-only pilot metrics and review-lead authorization."""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone


ROLES = ("reviewer", "review_lead")


def review_lead_access(conn, authenticated_reviewer_id, reviewer_key):
    """Return (allowed, reason), requiring a verified, matching signed-in identity."""
    if not authenticated_reviewer_id or not reviewer_key:
        return False, "authentication_required"
    columns = {row[1] for row in conn.execute("PRAGMA table_info(community_reviewers)")}
    if "role" not in columns:
        return False, "role_migration_required"
    row = conn.execute(
        """
        SELECT reviewer_key,email_verified_at,role
        FROM community_reviewers WHERE id=?
        """,
        (authenticated_reviewer_id,),
    ).fetchone()
    if not row or row[0] != reviewer_key or not row[1]:
        return False, "authentication_required"
    if row[2] != "review_lead":
        return False, "review_lead_required"
    return True, None


def _scalar(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def _attention_examples(conn):
    definitions = {
        "evidence_conflicts": """
            SELECT DISTINCT s.physical_stop_id,p.primary_name
            FROM stop_amenity_status s
            JOIN physical_stops p ON p.id=s.physical_stop_id
            JOIN stop_gtfs_status g ON g.physical_stop_id=s.physical_stop_id
                                  AND g.current_gtfs=1
            WHERE s.evidence_conflict=1
               OR s.consensus_conflicts_with_other_evidence=1
            ORDER BY s.physical_stop_id LIMIT 10
        """,
        "near_consensus": """
            SELECT DISTINCT r.physical_stop_id,p.primary_name
            FROM stop_amenity_review_priority r
            JOIN physical_stops p ON p.id=r.physical_stop_id
            JOIN stop_gtfs_status g ON g.physical_stop_id=r.physical_stop_id
                                  AND g.current_gtfs=1
            WHERE r.workflow_state='one_observation_short'
            ORDER BY r.review_priority_score DESC,r.physical_stop_id LIMIT 10
        """,
        "community_conflicts": """
            SELECT DISTINCT s.physical_stop_id,p.primary_name
            FROM stop_amenity_status s
            JOIN physical_stops p ON p.id=s.physical_stop_id
            JOIN stop_gtfs_status g ON g.physical_stop_id=s.physical_stop_id
                                  AND g.current_gtfs=1
            WHERE s.community_yes_count>0 AND s.community_no_count>0
            ORDER BY s.physical_stop_id LIMIT 10
        """,
    }
    return {
        key: [
            {"physical_stop_id": row[0], "stop_name": row[1],
             "stop_url": f"/stop/{row[0]}"}
            for row in conn.execute(sql)
        ]
        for key, sql in definitions.items()
    }


def build_pilot_summary(conn, now=None, recent_limit=25):
    """Build the admin payload with grouped SQL and no private account fields."""
    now = now or datetime.now(timezone.utc)
    since_7 = (now - timedelta(days=7)).isoformat()
    since_30 = (now - timedelta(days=30)).isoformat()
    review_filter = "source='community_review'"

    total_reviewers = _scalar(conn, "SELECT COUNT(*) FROM community_reviewers")
    reviews_total = _scalar(
        conn, f"SELECT COUNT(*) FROM stop_observations WHERE {review_filter}"
    )
    contributor_counts = [
        row[1] for row in conn.execute(
            f"""
            SELECT reviewer_id,COUNT(*) FROM stop_observations
            WHERE {review_filter} AND reviewer_id IS NOT NULL
            GROUP BY reviewer_id
            """
        )
    ]
    active_total = _scalar(
        conn, "SELECT COUNT(*) FROM stop_gtfs_status WHERE current_gtfs=1"
    )
    reviewed_active = _scalar(
        conn, f"""
        SELECT COUNT(DISTINCT o.physical_stop_id)
        FROM stop_observations o
        JOIN stop_gtfs_status g ON g.physical_stop_id=o.physical_stop_id
                               AND g.current_gtfs=1
        WHERE o.{review_filter}
        """,
    )
    activity = {
        "total_reviewers": total_reviewers,
        "active_reviewers_7d": _scalar(
            conn, f"SELECT COUNT(DISTINCT reviewer_id) FROM stop_observations "
                  f"WHERE {review_filter} AND reviewer_id IS NOT NULL "
                  "AND datetime(observed_at)>=datetime(?)", (since_7,),
        ),
        "active_reviewers_30d": _scalar(
            conn, f"SELECT COUNT(DISTINCT reviewer_id) FROM stop_observations "
                  f"WHERE {review_filter} AND reviewer_id IS NOT NULL "
                  "AND datetime(observed_at)>=datetime(?)", (since_30,),
        ),
        "reviews_total": reviews_total,
        "reviews_7d": _scalar(
            conn, f"SELECT COUNT(*) FROM stop_observations WHERE {review_filter} "
                  "AND datetime(observed_at)>=datetime(?)", (since_7,),
        ),
        "reviews_30d": _scalar(
            conn, f"SELECT COUNT(*) FROM stop_observations WHERE {review_filter} "
                  "AND datetime(observed_at)>=datetime(?)", (since_30,),
        ),
        "median_reviews_per_contributor": (
            statistics.median(contributor_counts) if contributor_counts else 0
        ),
        "repeat_reviewers": sum(count >= 2 for count in contributor_counts),
        "repeat_observation_rate": round(
            sum(max(count - 1, 0) for count in contributor_counts) / reviews_total,
            4,
        ) if reviews_total else 0,
    }
    coverage = {
        "active_stops": active_total,
        "distinct_active_stops_reviewed": reviewed_active,
        "active_stops_never_reviewed": active_total - reviewed_active,
        "active_stop_review_percent": round(
            100 * reviewed_active / active_total, 2
        ) if active_total else 0,
        "stops_with_2plus_observations": _scalar(
            conn, f"""
            SELECT COUNT(*) FROM (
              SELECT o.physical_stop_id
              FROM stop_observations o
              JOIN stop_gtfs_status g ON g.physical_stop_id=o.physical_stop_id
                                     AND g.current_gtfs=1
              WHERE o.{review_filter}
              GROUP BY o.physical_stop_id HAVING COUNT(*)>=2
            )
            """,
        ),
    }
    geography_sql = f"""
        WITH reviewed AS (
          SELECT o.id,o.physical_stop_id
          FROM stop_observations o
          JOIN stop_gtfs_status g ON g.physical_stop_id=o.physical_stop_id
                                 AND g.current_gtfs=1
          WHERE o.{review_filter}
        ), dimensions AS (
          SELECT r.id,r.physical_stop_id,'state' dimension,j.state value
          FROM reviewed r JOIN stop_jurisdiction j ON j.stop_id=r.physical_stop_id
          UNION ALL SELECT r.id,r.physical_stop_id,'county',j.county
          FROM reviewed r JOIN stop_jurisdiction j ON j.stop_id=r.physical_stop_id
          UNION ALL SELECT r.id,r.physical_stop_id,'municipality',j.municipality
          FROM reviewed r JOIN stop_jurisdiction j ON j.stop_id=r.physical_stop_id
          UNION ALL SELECT r.id,r.physical_stop_id,'dc_ward',j.dc_ward
          FROM reviewed r JOIN stop_jurisdiction j ON j.stop_id=r.physical_stop_id
          UNION ALL SELECT r.id,r.physical_stop_id,'dc_anc',j.dc_anc
          FROM reviewed r JOIN stop_jurisdiction j ON j.stop_id=r.physical_stop_id
        )
        SELECT dimension,value,COUNT(DISTINCT id),COUNT(DISTINCT physical_stop_id)
        FROM dimensions WHERE value IS NOT NULL AND TRIM(value)!=''
        GROUP BY dimension,value ORDER BY dimension,value
    """
    geography = {key: [] for key in (
        "state", "county", "municipality", "dc_ward", "dc_anc"
    )}
    for dimension, value, reviews, stops in conn.execute(geography_sql):
        geography[dimension].append({
            "value": value, "review_count": reviews,
            "reviewed_stop_count": stops,
        })
    coverage["geography"] = geography
    coverage["review_modes"] = [
        {"review_mode": row[0] or "legacy/unspecified", "review_count": row[1]}
        for row in conn.execute(
            f"SELECT review_mode,COUNT(*) FROM stop_observations "
            f"WHERE {review_filter} GROUP BY review_mode ORDER BY COUNT(*) DESC"
        )
    ]
    coverage["routes"] = [
        {"route_id": row[0], "review_count": row[1], "reviewed_stop_count": row[2]}
        for row in conn.execute(
            f"""
            SELECT r.route_id,COUNT(DISTINCT o.id),COUNT(DISTINCT o.physical_stop_id)
            FROM stop_observations o
            JOIN stop_gtfs_status g ON g.physical_stop_id=o.physical_stop_id
                                   AND g.current_gtfs=1
            JOIN physical_stop_members pm ON pm.physical_stop_id=o.physical_stop_id
            JOIN stop_routes sr ON sr.stop_id=pm.bus_stop_id
            JOIN routes r ON r.id=sr.route_id
            WHERE o.{review_filter}
            GROUP BY r.route_id ORDER BY COUNT(DISTINCT o.id) DESC,r.route_id
            """
        )
    ]
    quality = {
        "stops_with_reached_consensus": _scalar(conn, """
            SELECT COUNT(DISTINCT r.physical_stop_id)
            FROM stop_amenity_review_priority r
            JOIN stop_gtfs_status g ON g.physical_stop_id=r.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE r.workflow_state='consensus_reached'
        """),
        "stops_near_consensus": _scalar(conn, """
            SELECT COUNT(DISTINCT r.physical_stop_id)
            FROM stop_amenity_review_priority r
            JOIN stop_gtfs_status g ON g.physical_stop_id=r.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE r.workflow_state='one_observation_short'
        """),
        "community_conflict_stops": _scalar(conn, """
            SELECT COUNT(DISTINCT s.physical_stop_id)
            FROM stop_amenity_status s
            JOIN stop_gtfs_status g ON g.physical_stop_id=s.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE s.community_yes_count>0 AND s.community_no_count>0
        """),
        "canonical_evidence_conflict_stops": _scalar(conn, """
            SELECT COUNT(DISTINCT s.physical_stop_id)
            FROM stop_amenity_status s
            JOIN stop_gtfs_status g ON g.physical_stop_id=s.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE s.evidence_conflict=1
               OR s.consensus_conflicts_with_other_evidence=1
        """),
        "unknown_bench_stops": _scalar(conn, """
            SELECT COUNT(*) FROM stop_amenity_status s
            JOIN stop_gtfs_status g ON g.physical_stop_id=s.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE s.amenity_type='bench' AND s.derived_status='unknown'
        """),
        "unknown_shelter_stops": _scalar(conn, """
            SELECT COUNT(*) FROM stop_amenity_status s
            JOIN stop_gtfs_status g ON g.physical_stop_id=s.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE s.amenity_type='shelter' AND s.derived_status='unknown'
        """),
        "reviews_with_unsure_presence": _scalar(
            conn, f"""SELECT COUNT(*) FROM stop_observations
                WHERE {review_filter} AND (
                  shelter_present='unknown' OR bench_present='unknown'
                )""",
        ),
    }
    attention = {
        "manual_identity_exceptions": _scalar(conn, """
            SELECT COUNT(*) FROM physical_stop_identity_state i
            JOIN stop_gtfs_status g ON g.physical_stop_id=i.physical_stop_id
                                   AND g.current_gtfs=1
            WHERE i.identity_status='manual_exception'
        """),
        "derived_integrity_anomalies": _scalar(conn, """
            SELECT COUNT(*) FROM (
              SELECT g.physical_stop_id,COUNT(s.amenity_type) status_rows
              FROM stop_gtfs_status g
              LEFT JOIN stop_amenity_status s
                     ON s.physical_stop_id=g.physical_stop_id
              WHERE g.current_gtfs=1
              GROUP BY g.physical_stop_id HAVING COUNT(s.amenity_type)!=2
            )
        """),
        "retired_stop_access_attempts": {
            "available": False,
            "reason": "request-attempt telemetry is not stored",
        },
        "failed_review_submissions": {
            "available": False,
            "reason": "failures are logged operationally but not stored as pilot metrics",
        },
        "examples": _attention_examples(conn),
    }
    recent = [
        {
            "observation_id": row[0], "physical_stop_id": row[1],
            "stop_name": row[2], "geography": {
                "state": row[3], "county": row[4], "municipality": row[5],
                "dc_ward": row[6], "dc_anc": row[7],
            },
            "review_mode": row[8] or "legacy/unspecified",
            "observed_at": row[9],
            "reviewer_display_name": row[10] or "Community Volunteer",
            "active_stop": bool(row[11]),
            "identity_status": row[12] or "current",
            "bench_status": row[13], "shelter_status": row[14],
            "stop_url": f"/stop/{row[1]}",
        }
        for row in conn.execute(
            f"""
            SELECT o.id,o.physical_stop_id,p.primary_name,j.state,j.county,
                   j.municipality,j.dc_ward,j.dc_anc,o.review_mode,o.observed_at,
                   cr.display_name,COALESCE(g.current_gtfs,0),i.identity_status,
                   MAX(CASE WHEN s.amenity_type='bench' THEN s.derived_status END),
                   MAX(CASE WHEN s.amenity_type='shelter' THEN s.derived_status END)
            FROM stop_observations o
            JOIN physical_stops p ON p.id=o.physical_stop_id
            LEFT JOIN stop_jurisdiction j ON j.stop_id=o.physical_stop_id
            LEFT JOIN community_reviewers cr ON cr.id=o.reviewer_id
            LEFT JOIN stop_gtfs_status g ON g.physical_stop_id=o.physical_stop_id
            LEFT JOIN physical_stop_identity_state i
                   ON i.physical_stop_id=o.physical_stop_id
            LEFT JOIN stop_amenity_status s ON s.physical_stop_id=o.physical_stop_id
            WHERE o.{review_filter}
            GROUP BY o.id ORDER BY datetime(o.observed_at) DESC,o.id DESC LIMIT ?
            """,
            (recent_limit,),
        )
    ]
    return {
        "generated_at": now.isoformat(),
        "definitions": {
            "active_reviewer": "distinct reviewer with a submitted community observation in the window",
            "review": "one submitted stop_observations row with source=community_review",
            "median_reviews_per_contributor": "median among reviewers with at least one submitted review",
            "repeat_reviewer": "reviewer with at least two submitted reviews",
            "repeat_observation_rate": "reviews beyond each contributor's first, divided by all reviews",
            "active_stop": "stop_gtfs_status.current_gtfs=1",
            "geography_coverage": "submitted reviews at active stops, grouped independently by each nonblank geography dimension",
            "route_coverage": "submitted reviews at active stops served by each route; one review may represent multiple served routes",
            "reached_consensus": "active stop with at least one amenity workflow_state=consensus_reached",
            "near_consensus": "active stop with at least one amenity workflow_state=one_observation_short",
            "community_conflict": "active stop where community yes and no observations coexist for an amenity",
            "canonical_evidence_conflict": "active stop with canonical evidence_conflict or consensus_conflicts_with_other_evidence",
            "unsure_presence": "submitted review with unknown shelter or bench presence",
        },
        "activity": activity,
        "coverage": coverage,
        "quality": quality,
        "needs_attention": attention,
        "recent_reviews": recent,
        "privacy": {
            "included": ["display name", "contribution counts", "review timestamps",
                         "route and geography activity"],
            "excluded": ["email", "login tokens", "auth-attempt hashes",
                         "sessions", "IP addresses", "private auth metadata"],
        },
        "read_only": True,
    }
