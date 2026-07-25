from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
            (
                SELECT COUNT(*)
                FROM stop_reviews
                GROUP BY stop_id
                HAVING COUNT(*) >= 3
            ) AS consensus_stops
"""

new = """
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM (
                        SELECT stop_id
                        FROM stop_reviews
                        GROUP BY stop_id
                        HAVING COUNT(*) >= 3
                    )
                ),
                0
            ) AS consensus_stops
"""

if old in text:
    text = text.replace(old, new)
else:
    print("Pattern not found; inspect manually")

p.write_text(text)

print("Fixed consensus_stops NULL handling")
