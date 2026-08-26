"""Read-only validation report for a rebuilt amenity review-priority database."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))


def report(database_path):
    conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    scalar = lambda sql: conn.execute(sql).fetchone()[0]
    score_distributions = {}
    for amenity in ("shelter", "bench"):
        values = [row[0] for row in conn.execute(
            "SELECT review_priority_score FROM stop_amenity_review_priority "
            "WHERE amenity_type=? ORDER BY review_priority_score", (amenity,)
        )]
        def quantile(q):
            position = (len(values) - 1) * q
            lower = int(position)
            upper = min(lower + 1, len(values) - 1)
            return values[lower] + (values[upper] - values[lower]) * (position-lower)
        score_distributions[amenity] = {
            "p50": quantile(.50), "p75": quantile(.75),
            "p90": quantile(.90), "p95": quantile(.95), "max": max(values),
        }
    output = {
        "active_stops": scalar(
            "SELECT COUNT(*) FROM stop_gtfs_status WHERE current_gtfs=1"
        ),
        "percentile_rows": scalar(
            "SELECT COUNT(rider_exposure_percentile) FROM opportunity_assessments"
        ),
        "priority_rows": scalar("SELECT COUNT(*) FROM stop_amenity_review_priority"),
        "duplicate_priority_identities": scalar("""
            SELECT COUNT(*) FROM (SELECT physical_stop_id,amenity_type,COUNT(*) n
            FROM stop_amenity_review_priority GROUP BY 1,2 HAVING n>1)
        """),
        "inactive_priority_rows": scalar("""
            SELECT COUNT(*) FROM stop_amenity_review_priority p
            LEFT JOIN stop_gtfs_status s ON s.physical_stop_id=p.physical_stop_id
            WHERE s.current_gtfs IS NULL OR s.current_gtfs!=1
        """),
        "workflow": [dict(row) for row in conn.execute("""
            SELECT amenity_type,workflow_state,COUNT(*) count
            FROM stop_amenity_review_priority GROUP BY 1,2 ORDER BY 1,2
        """)],
        "tiers": [dict(row) for row in conn.execute("""
            SELECT amenity_type,priority_tier,COUNT(*) count
            FROM stop_amenity_review_priority GROUP BY 1,2 ORDER BY 1,2
        """)],
        "scores": [dict(row) for row in conn.execute("""
            SELECT amenity_type,MIN(review_priority_score) minimum,
                   AVG(review_priority_score) average,MAX(review_priority_score) maximum
            FROM stop_amenity_review_priority GROUP BY 1
        """)],
        "score_percentiles": score_distributions,
        "high_ridership_unresolved": [dict(row) for row in conn.execute("""
            SELECT amenity_type,COUNT(*) count FROM stop_amenity_review_priority
            WHERE workflow_state!='consensus_reached'
              AND rider_exposure_percentile>=90 GROUP BY amenity_type
        """)],
        "percentile_distribution": dict(conn.execute("""
            SELECT MIN(rider_exposure_percentile),AVG(rider_exposure_percentile),
                   MAX(rider_exposure_percentile)
            FROM opportunity_assessments
        """).fetchone()),
        "top_20": [dict(row) for row in conn.execute("""
            SELECT p.physical_stop_id,ps.primary_name,j.state,j.county,j.municipality,
                   p.amenity_type,p.derived_status,p.workflow_state,
                   p.rider_exposure_percentile,p.review_priority_score,p.rationale
            FROM stop_amenity_review_priority p
            JOIN physical_stops ps ON ps.id=p.physical_stop_id
            LEFT JOIN stop_jurisdiction j ON j.stop_id=p.physical_stop_id
            WHERE p.workflow_state!='consensus_reached'
            ORDER BY p.review_priority_score DESC,p.physical_stop_id,p.amenity_type
            LIMIT 20
        """)],
        "workflow_examples": [dict(row) for row in conn.execute("""
            WITH ranked AS (
              SELECT p.physical_stop_id,ps.primary_name,p.amenity_type,
                     p.derived_status,p.workflow_state,p.rider_exposure_percentile,
                     p.review_priority_score,
                     ROW_NUMBER() OVER (PARTITION BY p.workflow_state
                                        ORDER BY p.review_priority_score DESC) n
              FROM stop_amenity_review_priority p
              JOIN physical_stops ps ON ps.id=p.physical_stop_id
            ) SELECT * FROM ranked WHERE n=1 ORDER BY review_priority_score DESC
        """)],
    }
    print(json.dumps(output, indent=2))
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    report(args.database)


if __name__ == "__main__":
    main()
