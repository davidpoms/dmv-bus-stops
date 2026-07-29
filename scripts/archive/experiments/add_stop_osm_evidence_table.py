import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS stop_osm_evidence (

    stop_id INTEGER PRIMARY KEY,

    osm_bus_stop BOOLEAN DEFAULT 0,

    osm_bench BOOLEAN DEFAULT 0,

    osm_shelter BOOLEAN DEFAULT 0,

    osm_feature_id INTEGER,

    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(stop_id)
        REFERENCES physical_stops(id)

)
""")

conn.commit()
conn.close()

print("Created stop_osm_evidence table")
