from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def verification_funnel_metrics():
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
            ) AS stops_with_reviews,

            (
                SELECT COUNT(*)
                FROM (
                    SELECT stop_id
                    FROM stop_reviews
                    GROUP BY stop_id
                    HAVING COUNT(
                        DISTINCT COALESCE(
                            reviewer_id,
                            CAST(user_id AS TEXT),
                            anonymous_email
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
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
            ) AS awaiting_review

        """
    )[0]

'''

if "def verification_funnel_metrics" not in text:
    p.write_text(text + addition)

print("Added verification funnel metrics")
