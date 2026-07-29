import sqlite3


DB = "src/database/dmv_bus_stops.db"


def query(sql, params=()):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(sql, params).fetchall()

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

            COUNT(o.id) AS review_count,

            AVG(o.confidence)
                AS confidence,

            sv.status

        FROM physical_stops ps

        LEFT JOIN stop_observations o
            ON ps.id = o.physical_stop_id

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
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
            ) AS reviewed_stops,


            (
                SELECT COUNT(*)
                FROM stop_observations
            ) AS total_reviews,


            (
                SELECT COUNT(*)
                FROM physical_stops
                WHERE id NOT IN (
                    SELECT DISTINCT physical_stop_id
                    FROM stop_observations
                )
            ) AS awaiting_review,


            (
                SELECT COUNT(*)
                FROM stop_consensus
                WHERE consensus_status='verified'
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
                FROM stop_observations
                WHERE bench_present='yes'
            ) AS community_benches,

            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_observations
                WHERE bench_present='no'
                AND bench_feasible='yes'
            ) AS community_bench_opportunities

        """
    )[0]


def route_validation_metrics():
    return query(
        """
        WITH consensus_stops AS (

            SELECT
                physical_stop_id AS stop_id

            FROM stop_observations

            GROUP BY physical_stop_id

            HAVING COUNT(
                DISTINCT observer
            ) >= 3

        ),

        route_progress AS (

            SELECT

                route_id,

                COUNT(DISTINCT stop_id) AS total_stops,

                COUNT(
                    DISTINCT CASE
                        WHEN stop_id IN (
                            SELECT stop_id
                            FROM consensus_stops
                        )
                        THEN stop_id
                    END
                ) AS verified_stops

            FROM stop_routes

            GROUP BY route_id

        )

        SELECT

            COUNT(*) AS total_routes,

            COALESCE(
                SUM(
                    CASE
                        WHEN verified_stops = total_stops
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS fully_verified_routes,

            COALESCE(
                SUM(
                    CASE
                        WHEN verified_stops > 0
                        AND verified_stops < total_stops
                        THEN 1
                        ELSE 0
                    END
                ),
                0
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
                        SELECT physical_stop_id
                        FROM stop_observations
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
                            SELECT physical_stop_id
                            FROM stop_observations
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
        "consensus": consensus_progress_metrics(),
    }





def stop_level_bench_metrics():

    return query(
        """
        SELECT


            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
                WHERE bench_present='yes'
            ) AS community_confirmed_benches,


            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
                WHERE bench_present='no'
                AND bench_feasible='yes'
            ) AS community_bench_opportunities,


            (
                SELECT COUNT(*)
                FROM physical_stops ps
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM stop_observations so
                    WHERE so.physical_stop_id = ps.id
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



def verification_funnel_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM physical_stops
            ) AS total_stops,

            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
            ) AS stops_with_reviews,

            (
                SELECT COUNT(*)
                FROM (
                    SELECT physical_stop_id
                    FROM stop_observations
                    GROUP BY physical_stop_id
                    HAVING COUNT(
                        DISTINCT COALESCE(
                            reviewer_id,
                            observer
                        )
                    ) >= 3
                )
            ) AS consensus_verified_stops,

            (
                SELECT COUNT(*)
                FROM physical_stops
            )
            -
            (
                SELECT COUNT(DISTINCT physical_stop_id)
                FROM stop_observations
            ) AS awaiting_review

        """
    )[0]



def reviewer_progress_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM community_reviewers
            ) AS reviewers,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
            ) AS assignments,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='completed'
            ) AS completed_assignments,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='assigned'
            ) AS pending_assignments

        """
    )[0]



def consensus_progress_metrics():
    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM physical_stops
            ) AS total_stops,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
            ) AS total_assignments,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='completed'
            ) AS completed_reviews,

            (
                SELECT COUNT(*)
                FROM stop_consensus
                WHERE consensus_status='verified'
            ) AS verified_stops,

            (
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE status='assigned'
            ) AS pending_reviews

        """
    )[0]



def bench_status_metrics():

    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM stop_observations
                WHERE bench_present = 'yes'
            ) AS confirmed_benches,


            (
                SELECT COUNT(*)
                FROM osm_features
                WHERE tags LIKE '%bench%'
            ) AS likely_osm_benches,


            (
                SELECT COUNT(*)
                FROM stop_observations
                WHERE bench_present = 'no'
                AND bench_feasible = 'yes'
            ) AS bench_candidates,


            (
                SELECT COUNT(*)
                FROM physical_stops p
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM stop_observations o
                    WHERE o.physical_stop_id = p.id
                )
            ) AS unknown_stops

        """
    )[0]





def bench_priority_metrics():

    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM stop_osm_evidence
                WHERE osm_bench = 1
            ) AS confirmed_benches,


            (
                SELECT COUNT(*)
                FROM stop_osm_evidence
                WHERE osm_shelter = 1
                AND osm_bench = 0
            ) AS shelter_without_bench,


            (
                SELECT COUNT(*)
                FROM stop_osm_evidence
                WHERE osm_bus_stop = 1
                AND osm_bench = 0
                AND osm_shelter = 0
            ) AS high_priority_reviews

        """
    )[0]



def wmata_history_for_stop(stop_id):

    return query(
        '''
        SELECT
            statuses,
            explanation,
            high_confidence_count,
            medium_confidence_count
        FROM stop_wmata_history_summary
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )



def wmata_history_for_stop(stop_id):

    return query(
        """
        SELECT
            statuses,
            explanation,
            high_confidence_count,
            medium_confidence_count
        FROM stop_wmata_history_summary
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )

