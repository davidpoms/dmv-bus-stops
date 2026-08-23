import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

deleted = conn.execute(
    """
    DELETE FROM stop_amenity_evidence
    WHERE source='MONTGOMERY_COUNTY'
    """
).rowcount

conn.commit()
conn.close()

print(
    "Deleted Montgomery records:",
    deleted
)