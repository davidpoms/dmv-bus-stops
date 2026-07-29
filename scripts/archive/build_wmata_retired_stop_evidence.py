import sqlite3
import json
from pathlib import Path


DB = "src/database/dmv_bus_stops.db"

sources = [
    Path("src/OSM dmv bus stop export.json"),
    Path("src/OSM bus stop export out body july 2026.geojson")
]


retired = []


for path in sources:
    if not path.exists():
        continue

    print("Scanning:", path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", data.get("features", []))

    for el in elements:

        tags = el.get("tags", {})

        note = tags.get("note", "").lower()

        if (
            "wmata metrobus service" in note
            and
            (
                "discontinued" in note
                or
                "discontinue" in note
                or
                "will be discontinued" in note
            )
        ):

            ref = (
                tags.get("ref:wmata")
                or
                tags.get("ref")
            )

            name = tags.get("name")

            lat = el.get("lat")
            lon = el.get("lon")

            if "geometry" in el:
                coords = el["geometry"]["coordinates"]
                lon = coords[0]
                lat = coords[1]


            retired.append(
                (
                    ref,
                    name,
                    lat,
                    lon,
                    tags.get("note")
                )
            )


print("Retired WMATA candidates:", len(retired))


conn = sqlite3.connect(DB)

conn.execute("""
CREATE TABLE IF NOT EXISTS wmata_retired_evidence (

    id INTEGER PRIMARY KEY,

    wmata_stop_id INTEGER,

    name TEXT,

    latitude REAL,

    longitude REAL,

    note TEXT,

    source TEXT DEFAULT 'OSM'

)
""")


conn.execute("DELETE FROM wmata_retired_evidence")


conn.executemany(
"""
INSERT INTO wmata_retired_evidence
(
wmata_stop_id,
name,
latitude,
longitude,
note
)
VALUES (?, ?, ?, ?, ?)
""",
retired
)


conn.commit()


print("Inserted:", len(retired))


conn.close()
