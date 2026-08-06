import sqlite3
import json

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
c = conn.cursor()

row = c.execute(
    """
    SELECT
        combined_route_weekday_boardings,
        assessment_json
    FROM opportunity_assessments
    WHERE physical_stop_id = 2333
    """
).fetchone()

print("Boardings:", row[0])

data = json.loads(row[1])

for key, value in data.items():
    print(key, ":", value)