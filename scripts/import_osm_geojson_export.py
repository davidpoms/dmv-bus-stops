import sqlite3
import json
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")

OSM_FILE = Path(
    "src/OSM bus stop export out body july 2026.geojson"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
DELETE FROM osm_features
""")


with open(OSM_FILE) as f:
    data = json.load(f)


count = 0


for feature in data["features"]:

    geometry = feature.get("geometry", {})

    if geometry.get("type") != "Point":
        continue


    coords = geometry.get("coordinates")

    if not coords or len(coords) != 2:
        continue


    lon, lat = coords


    props = feature.get("properties", {})


    osm_id = props.get("@id")

    if osm_id and osm_id.startswith("node/"):
        osm_id = int(osm_id.split("/")[1])


    tags = {
        k:v
        for k,v in props.items()
        if not k.startswith("@")
    }


    cur.execute(
        """
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
            osm_id,
            "node",
            lat,
            lon,
            json.dumps(tags)
        )
    )


    count += 1


conn.commit()
conn.close()


print("Imported", count, "OSM features")
