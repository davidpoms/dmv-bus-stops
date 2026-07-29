from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

text = text.replace(
"""
            SELECT
                stop_id

            FROM stop_observations

            GROUP BY physical_stop_id

            HAVING COUNT(
                DISTINCT COALESCE(
                    reviewer_id,
                    CAST(user_id AS TEXT),
                    anonymous_email
                )
            ) >= 3
""",
"""
            SELECT
                physical_stop_id AS stop_id

            FROM stop_observations

            GROUP BY physical_stop_id

            HAVING COUNT(
                DISTINCT observer
            ) >= 3
"""
)

p.write_text(text)

print("Fixed route validation query for stop_observations")
