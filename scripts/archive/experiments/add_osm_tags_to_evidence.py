import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
cur=conn.cursor()

cur.execute("""
ALTER TABLE stop_osm_evidence
ADD COLUMN osm_tags TEXT
""")

conn.commit()
conn.close()

print("Added osm_tags")
