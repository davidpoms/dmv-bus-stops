from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
            (
                SELECT COUNT(*)
                FROM stop_reviews
            ) AS total_reviews,

"""

new = """
            (
                SELECT COUNT(*)
                FROM stop_reviews
            ) AS total_reviews,

            (
                SELECT COUNT(*)
                FROM physical_stops
                WHERE id NOT IN (
                    SELECT DISTINCT stop_id
                    FROM stop_reviews
                )
            ) AS awaiting_review,

"""

if old not in text:
    print("Verification block not found")
else:
    text = text.replace(old, new, 1)

p.write_text(text)

print("Added awaiting review metric")
