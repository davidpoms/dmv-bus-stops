import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

import requests
import sqlite3

from src.amenities.matcher import find_nearest_physical_stop

DB = Path(
    "src/database/dmv_bus_stops.db"
)

URL = (
    "https://gis.montgomerycountymd.gov/arcgis/rest/services/"
    "DOT/BusStops/FeatureServer/0/query"
)


PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": 4326,
    "f": "json"
}


conn = sqlite3.connect(DB)


response = requests.get(
    URL,
    params=PARAMS,
    timeout=60
)

features = response.json()["features"]


total = 0
matched = 0
wmata = 0


for feature in features:

    total += 1

    geometry = feature.get("geometry")

    if not geometry:
        continue

    lon = geometry["x"]
    lat = geometry["y"]


    match = find_nearest_physical_stop(
        DB,
        lat,
        lon
    )


    if not match:
        continue


    matched += 1


    exists = conn.execute(
        """
        SELECT 1
        FROM stop_wmata_evidence
        WHERE physical_stop_id=?
        LIMIT 1
        """,
        (
            match["physical_stop_id"],
        )
    ).fetchone()


    if exists:
        wmata += 1


print("Montgomery records:", total)
print("Geometry matched:", matched)
print("WMATA overlap:", wmata)