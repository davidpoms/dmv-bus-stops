import sqlite3
import json

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()

row = c.execute(
    """
    SELECT
        physical_stop_id,
        opportunity_score,
        factors

    FROM improvement_opportunities

    WHERE physical_stop_id = 2685;
    """
).fetchone()

print(row)

if row:
    print(
        json.dumps(
            json.loads(row[2]),
            indent=2
        )
    )