import sqlite3
import json

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

row = conn.execute(
    """
    SELECT
        physical_stop_id,
        opportunity_score,
        factors
    FROM improvement_opportunities
    WHERE physical_stop_id=2108
    """
).fetchone()

print(row[0])
print(row[1])

factors = json.loads(row[2])

print("\nFACTOR KEYS")
print(factors.keys())

print("\nNETWORK")
print(factors.get("network"))

print("\nROUTE EXPOSURE")
print(factors.get("route_exposure"))

conn.close()