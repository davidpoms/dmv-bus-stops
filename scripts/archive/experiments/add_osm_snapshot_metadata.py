import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    ("osm_snapshot_date", "TEXT"),
    ("osm_source_file", "TEXT")
]

for name, dtype in columns:
    try:
        cur.execute(
            f"ALTER TABLE stop_osm_evidence ADD COLUMN {name} {dtype}"
        )
        print("Added", name)
    except sqlite3.OperationalError:
        print(name, "already exists")

cur.execute("""
UPDATE stop_osm_evidence
SET
    osm_snapshot_date='2026-07-26',
    osm_source_file='OSM bus stop export out body july 2026.geojson'
WHERE osm_snapshot_date IS NULL
""")

conn.commit()
conn.close()

print("Added OSM snapshot metadata")
