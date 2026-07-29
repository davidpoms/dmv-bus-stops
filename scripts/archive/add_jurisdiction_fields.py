import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)

for sql in [
    "ALTER TABLE stop_environment ADD COLUMN jurisdiction TEXT",
    "ALTER TABLE stop_environment ADD COLUMN road_distance_meters REAL",
    "ALTER TABLE stop_environment ADD COLUMN jurisdiction_confidence REAL"
]:
    try:
        conn.execute(sql)
    except sqlite3.OperationalError:
        pass

conn.commit()
conn.close()

print("Added jurisdiction fields")
