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



def community_verification_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM physical_stops
            ) AS total_stops,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
            ) AS reviewed_stops,

            (
                SELECT COUNT(*)
                FROM stop_reviews
            ) AS total_reviews,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                GROUP BY stop_id
                HAVING COUNT(*) >= 3
            ) AS consensus_stops

        """
    )[0]


def bench_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM osm_features
                WHERE tags LIKE '%"bench": "yes"%'
            ) AS osm_bench_features,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                WHERE has_bench = 1
            ) AS community_benches,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                WHERE has_bench = 0
                AND bench_location_feasible = 1
            ) AS community_bench_opportunities

        """
    )[0]


def route_validation_metrics():

    return query(
        """
        WITH consensus_stops AS (

            SELECT
                stop_id

            FROM stop_reviews

            GROUP BY stop_id

            HAVING COUNT(*) >= 3

        ),

        route_progress AS (

            SELECT

                route_id,

                COUNT(stop_id) AS total_stops,

                SUM(
                    CASE
                        WHEN stop_id IN (
                            SELECT stop_id
                            FROM consensus_stops
                        )
                        THEN 1
                        ELSE 0
                    END
                ) AS verified_stops

            FROM stop_routes

            GROUP BY route_id

        )

        SELECT

            COUNT(*) AS total_routes,

            SUM(
                CASE
                    WHEN verified_stops = total_stops
                    THEN 1
                    ELSE 0
                END
            ) AS fully_verified_routes,

            SUM(
                CASE
                    WHEN verified_stops > 0
                    AND verified_stops < total_stops
                    THEN 1
                    ELSE 0
                END
            ) AS partially_verified_routes

        FROM route_progress

        """
    )[0]


def verification_coverage():
    return query(
        """
        SELECT

            COUNT(*) AS total_stops,

            SUM(
                CASE
                    WHEN id IN (
                        SELECT stop_id
                        FROM stop_reviews
                    )
                    THEN 1
                    ELSE 0
                END
            ) AS reviewed_stops,

            ROUND(
                100.0 *
                SUM(
                    CASE
                        WHEN id IN (
                            SELECT stop_id
                            FROM stop_reviews
                        )
                        THEN 1
                        ELSE 0
                    END
                ) / COUNT(*),
                1
            ) AS coverage_percent

        FROM physical_stops
        """
    )[0]



def dashboard_metrics():
    return {
        "verification": community_verification_metrics(),
        "coverage": verification_coverage(),
        "benches": stop_level_bench_metrics(),
        "routes": route_validation_metrics(),
    }





def stop_level_bench_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                WHERE has_bench = 1
            ) AS community_confirmed_benches,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                WHERE has_bench = 0
                AND bench_location_feasible = 1
            ) AS community_bench_opportunities,

            (
                SELECT COUNT(*)
                FROM physical_stops ps
                WHERE ps.id NOT IN (
                    SELECT DISTINCT stop_id
                    FROM stop_reviews
                )
            ) AS stops_needing_review

        """
    )[0]



def counties():
    return query(
        """
        SELECT
            state,
            county,
            stop_count
        FROM county_summary
        ORDER BY state, county
        """
    )


def municipalities():
    return query(
        """
        SELECT
            state,
            county,
            municipality,
            stop_count
        FROM municipality_summary
        ORDER BY state, county, municipality
        """
    )






def dc_ancs():
    return query(
        """
        SELECT
            dc_anc,
            stop_count
        FROM dc_anc_summary
        WHERE dc_anc IS NOT NULL
        ORDER BY dc_anc
        """
    )

