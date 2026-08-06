import sqlite3
from pathlib import Path

db = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(db)

conn.execute("""
CREATE TABLE IF NOT EXISTS stop_environment (

    id INTEGER PRIMARY KEY,

    stop_id INTEGER UNIQUE,

    sidewalk_nearby BOOLEAN,

    crossing_nearby BOOLEAN,

    bus_shelter_nearby BOOLEAN,

    nearby_buildings INTEGER,

    nearby_parks INTEGER,

    tree_cover_score REAL,

    road_class TEXT,

    osm_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(stop_id)
        REFERENCES physical_stops(id)

);
""")

conn.commit()
conn.close()

print("Created stop_environment table")
