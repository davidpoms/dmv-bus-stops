from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

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
'''

if "def community_verification_metrics" not in text:
    p.write_text(text + addition)

print("Added dashboard community metrics")
