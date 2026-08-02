import sqlite3
import json

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()

row = c.execute(
    """
    SELECT
        physical_stop_id,
        combined_route_weekday_boardings,
        highest_route_weekday_boardings,
        routes_served,
        assessment_json

    FROM opportunity_assessments

    WHERE physical_stop_id = 2685;
    """
).fetchone()


print(row)

if row:
    print(json.dumps(
        json.loads(row[4]),
        indent=2
    ))