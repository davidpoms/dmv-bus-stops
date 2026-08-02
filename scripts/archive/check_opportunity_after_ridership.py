import sqlite3
import json

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

row = c.execute(
    """
    SELECT
        physical_stop_id,
        opportunity_score,
        factors
    FROM improvement_opportunities
    ORDER BY opportunity_score DESC
    LIMIT 5
    """
).fetchall()


for r in row:
    print("\nSTOP", r[0])
    print("SCORE", r[1])

    factors=json.loads(r[2])

    print(
        "RIDERSHIP",
        factors.get("route_exposure")
    )