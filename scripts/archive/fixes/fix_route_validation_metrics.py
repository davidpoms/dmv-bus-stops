from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

start = text.index("def route_validation_metrics():")
end = text.index("\ndef verification_coverage():", start)

new_function = r'''def route_validation_metrics():
    return query(
        """
        WITH consensus_stops AS (

            SELECT
                stop_id

            FROM stop_reviews

            GROUP BY stop_id

            HAVING COUNT(
                DISTINCT COALESCE(
                    reviewer_id,
                    CAST(user_id AS TEXT),
                    anonymous_email
                )
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


'''

text = text[:start] + new_function + text[end+1:]

p.write_text(text)

print("Updated route validation metrics")
