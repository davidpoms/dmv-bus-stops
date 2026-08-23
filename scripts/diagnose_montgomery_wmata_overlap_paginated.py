import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

import requests
import sqlite3

from src.amenities.matcher import haversine_m


DB = "src/database/dmv_bus_stops.db"

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


def fetch_all():

    records = []

    offset = 0
    page_size = 2000

    while True:

        print(
            f"Fetching {offset}-{offset+page_size-1}"
        )

        params = PARAMS.copy()

        params.update(
            {
                "resultOffset": offset,
                "resultRecordCount": page_size
            }
        )

        r = requests.get(
            URL,
            params=params,
            timeout=60
        )

        r.raise_for_status()

        data = r.json()

        page = data.get(
            "features",
            []
        )

        records.extend(page)

        if len(page) < page_size:
            break

        offset += page_size

    return records


def is_wmata_route(routes):

    if not routes:
        return False

    routes = routes.upper()

    prefixes = [
        "C",
        "D",
        "M",
        "P",
        "A",
        "F"
    ]

    for route in routes.replace(",", " ").split():

        route = route.strip()

        if any(
            route.startswith(p)
            for p in prefixes
        ):
            return True

    return False


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


wmata_stops = conn.execute(
    """
    SELECT
        physical_stop_id,
        wmata_stop_id
    FROM stop_wmata_evidence
    """
).fetchall()


physical_coords = {}

for row in conn.execute(
    """
    SELECT
        id,
        latitude,
        longitude
    FROM physical_stops
    """
):

    physical_coords[row["id"]] = (
        row["latitude"],
        row["longitude"]
    )


records = fetch_all()

print()
print(
    "Montgomery records:",
    len(records)
)


wmata_candidates = 0
matched = 0
overlap = 0


for feature in records:

    attrs = feature["attributes"]
    geom = feature.get("geometry")

    if not geom:
        continue


    routes = attrs.get(
        "ROUTES"
    )


    if not is_wmata_route(routes):
        continue


    wmata_candidates += 1


    lon = geom["x"]
    lat = geom["y"]


    best_distance = None


    for row in wmata_stops:

        coords = physical_coords.get(
            row["physical_stop_id"]
        )

        if not coords:
            continue


        d = haversine_m(
            lat,
            lon,
            coords[0],
            coords[1]
        )


        if best_distance is None or d < best_distance:
            best_distance = d


    if best_distance and best_distance <= 50:
        matched += 1


print()
print(
    "Likely WMATA route records:",
    wmata_candidates
)

print(
    "Within 50m of WMATA physical stop:",
    matched
)