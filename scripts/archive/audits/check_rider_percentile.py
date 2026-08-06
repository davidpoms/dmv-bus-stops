import sqlite3
import json

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
c = conn.cursor()

row = c.execute(
    """
    SELECT assessment_json
    FROM opportunity_assessments
    WHERE physical_stop_id = 2333
    """
).fetchone()

if row and row[0]:
    data = json.loads(row[0])
    print(data.get("rider_exposure_percentile"))
else:
    print("No assessment found")