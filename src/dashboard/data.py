import sqlite3


DB = "src/database/dmv_bus_stops.db"


def query(sql):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(sql).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def jurisdiction_totals():
    return query(
        """
        SELECT
            state,
            COUNT(*) AS stop_count
        FROM stop_jurisdiction
        GROUP BY state
        ORDER BY stop_count DESC
        """
    )


def top_counties(limit=10):
    return query(
        f"""
        SELECT
            state,
            county,
            stop_count
        FROM county_summary
        ORDER BY stop_count DESC
        LIMIT {limit}
        """
    )


def top_municipalities(limit=10):
    return query(
        f"""
        SELECT
            state,
            county,
            municipality,
            stop_count
        FROM municipality_summary
        ORDER BY stop_count DESC
        LIMIT {limit}
        """
    )


def dc_wards():
    return query(
        """
        SELECT
            dc_ward,
            stop_count
        FROM dc_ward_summary
        ORDER BY dc_ward
        """
    )


def validation_progress():
    return query(
        """
        SELECT

            ps.id AS stop_id,
            ps.primary_name,

            COUNT(sr.id) AS review_count,

            AVG(sr.reviewer_confidence)
                AS confidence,

            sv.status

        FROM physical_stops ps

        LEFT JOIN stop_reviews sr
            ON ps.id = sr.stop_id

        LEFT JOIN stop_validation sv
            ON ps.id = sv.physical_stop_id

        GROUP BY ps.id

        ORDER BY review_count ASC

        """
    )

