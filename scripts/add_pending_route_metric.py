from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
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

new = """
            SUM(
                CASE
                    WHEN verified_stops > 0
                    AND verified_stops < total_stops
                    THEN 1
                    ELSE 0
                END
            ) AS partially_verified_routes,

            SUM(
                CASE
                    WHEN verified_stops = 0
                    THEN 1
                    ELSE 0
                END
            ) AS awaiting_verification_routes

        FROM route_progress
"""

if old not in text:
    print("Route metric block not found")
else:
    text = text.replace(old, new, 1)

p.write_text(text)

print("Added awaiting route verification metric")
