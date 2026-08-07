import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

cursor = conn.execute(
    """
    DELETE FROM stop_amenity_evidence
    WHERE source LIKE 'MONTGOMERY_COUNTY%'
    """
)

conn.commit()

print(
    "Deleted:",
    cursor.rowcount
)

conn.close()