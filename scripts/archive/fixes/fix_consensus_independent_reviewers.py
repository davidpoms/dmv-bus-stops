from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
            (
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_reviews
                GROUP BY stop_id
                HAVING COUNT(*) >= 3
            ) AS consensus_stops
"""

new = """
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
            ) AS consensus_stops
"""

if old not in text:
    print("Consensus block not found")
else:
    text = text.replace(old, new)
    p.write_text(text)
    print("Updated consensus to require independent reviewers")
