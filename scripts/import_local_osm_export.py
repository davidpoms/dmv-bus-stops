import sqlite3
import json
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")

OSM_FILE = Path(
    "src/OSM dmv bus stop export.json"
)


conn = sqlite3.connect(DB)


conn.execute("""
CREATE TABLE IF NOT EXISTS osm_features (

    id INTEGER PRIMARY KEY,

    osm_id INTEGER,

    osm_type TEXT,

    lat REAL,

    lon REAL,

    tags TEXT

)
""")


with open(OSM_FILE) as f:
    data = json.load(f)


count = 0


for element in data["elements"]:

    tags = element.get("tags", {})

    conn.execute("""
    INSERT INTO osm_features
    (
        osm_id,
        osm_type,
        lat,
        lon,
        tags
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        element.get("id"),
        element.get("type"),
        element.get("lat"),
        element.get("lon"),
        json.dumps(tags)
    ))

    count += 1


conn.commit()
conn.close()

print("Imported", count, "OSM features")
