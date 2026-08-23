import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

import sqlite3
import requests

from src.amenities.matcher import haversine_m


DB = "src/database/dmv_bus_stops.db"

URL = (
    "https://gis.montgomerycountymd.gov/arcgis/rest/services/"
    "DOT/BusStops/FeatureServer/0/query"
)

PARAMS = {
    "where": "1=1",
    "outFields": "STOPID",
    "returnGeometry": "true",
    "outSR": 4326,
    "f": "json",
    "resultRecordCount": 6000
}


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


wmata_stops = conn.execute(
    """
    SELECT
        p.id,
        p.latitude,
        p.longitude
    FROM physical_stops p
    JOIN stop_wmata_evidence w
    ON p.id = w.physical_stop_id
    GROUP BY p.id
    """
).fetchall()


print(
    "WMATA physical stops:",
    len(wmata_stops)
)


response = requests.get(
    URL,
    params=PARAMS,
    timeout=60
)

data = response.json()

features = data.get(
    "features",
    []
)


distances = []


for feature in features:

    geometry = feature.get(
        "geometry"
    )

    if not geometry:
        continue

    lon = geometry.get("x")
    lat = geometry.get("y")

    if lat is None or lon is None:
        continue


    best = None

    for stop in wmata_stops:

        distance = haversine_m(
            lat,
            lon,
            stop["latitude"],
            stop["longitude"]
        )

        if best is None or distance < best:
            best = distance

    distances.append(best)


distances.sort()


print(
    "Montgomery records:",
    len(distances)
)


for threshold in [
    25,
    50,
    100,
    150,
    250,
    500
]:

    count = len(
        [
            d for d in distances
            if d <= threshold
        ]
    )

    print(
        f"{threshold} meters:",
        count
    )


print("\nClosest distances:")
for d in distances[:20]:
    print(
        round(d,2)
    )