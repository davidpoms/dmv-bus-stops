from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old_count = """
        SELECT COUNT(
            DISTINCT COALESCE(
                reviewer_id,
                CAST(user_id AS TEXT),
                anonymous_email
            )
        )
        FROM stop_reviews
        WHERE stop_id = ?
"""

new_count = """
        SELECT COUNT(
            DISTINCT COALESCE(
                reviewer_id,
                observer
            )
        )
        FROM stop_observations
        WHERE physical_stop_id = ?
"""

old_review = """
        SELECT
            ROUND(AVG(has_shelter),0),
            ROUND(AVG(has_bench),0),
            ROUND(AVG(bench_location_feasible),0),
            ROUND(AVG(
                (
                    curb_access_clear +
                    bus_ramp_access_clear +
                    landing_zone_clear +
                    rear_clear_zone_clear
                ) / 4.0
            ),2),
            AVG(reviewer_confidence)

        FROM stop_reviews
        WHERE stop_id = ?
"""

new_review = """
        SELECT
            ROUND(AVG(
                CASE
                    WHEN shelter_present IN ('yes','true','1')
                    THEN 1
                    ELSE 0
                END
            ),0),

            ROUND(AVG(
                CASE
                    WHEN bench_present IN ('yes','true','1')
                    THEN 1
                    ELSE 0
                END
            ),0),

            ROUND(AVG(
                CASE
                    WHEN bench_feasible IN ('yes','true','1')
                    THEN 1
                    ELSE 0
                END
            ),0),

            ROUND(AVG(
                CASE
                    WHEN ada_clearance_possible IN ('yes','true','1')
                    THEN 1
                    ELSE 0
                END
            ),2),

            AVG(confidence)

        FROM stop_observations
        WHERE physical_stop_id = ?
"""

if old_count in text:
    text = text.replace(old_count, new_count)
    print("Updated reviewer count query")
else:
    print("Reviewer count query not found")

if old_review in text:
    text = text.replace(old_review, new_review)
    print("Updated consensus aggregation query")
else:
    print("Consensus aggregation query not found")

p.write_text(text)
