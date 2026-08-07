import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

import requests

from src.amenities.importer import insert_amenity_evidence
from src.amenities.matcher import find_nearest_wmata_stop
from src.amenities.route_filter import has_wmata_route, extract_wmata_routes

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
    "returnTrueCurves": "false",
    "outSR": "4326",
    "f": "json"
}


AMENITY_FIELDS = {
    "SHELTERS": "shelter",
    "BENCHES": "bench",
    "TRASHCANS": "trash_can",
    "SIGNS": "sign"
}


print(
    "Fetching Montgomery County bus stops..."
)



all_features = []

offset = 0

page_size = 2000


while True:

    print(
        f"Fetching records {offset}-{offset + page_size - 1}"
    )

    params = PARAMS.copy()

    params.update(
        {
            "resultOffset": offset,
            "resultRecordCount": page_size
        }
    )


    response = requests.get(
        URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    page = data.get(
        "features",
        []
    )


    all_features.extend(page)


    if len(page) < page_size:
        break


    offset += page_size



features = all_features


print(
    "Records:",
    len(features)
)

matched = 0
inserted = 0
skipped = 0


for feature in features:

    attrs = feature.get(
        "attributes",
        {}
    )
    routes = attrs.get("ROUTES")

    if not has_wmata_route(routes):
      continue

    geometry = feature.get(
        "geometry"
    )


    if not geometry:
        continue


    lon = geometry.get(
        "x"
    )

    lat = geometry.get(
        "y"
    )


    if lat is None or lon is None:
        continue



    match = find_nearest_wmata_stop(
        DB,
        lat,
        lon
    )


    if not match:
        skipped += 1
        continue


    matched += 1


    stop_id = match["physical_stop_id"]


    for field, amenity_type in AMENITY_FIELDS.items():

        value = attrs.get(
            field
        )


        if value is None:
            continue


        present = 1 if value > 0 else 0


        was_inserted = insert_amenity_evidence(
            DB,
            physical_stop_id=stop_id,
            source="MONTGOMERY_COUNTY_WMATA",
            source_record_id=str(
                attrs.get("STOPID")
            ),
            amenity_type=amenity_type,
            present=present,
            confidence="high",
            match_distance_m=match["distance_m"],
        jurisdiction="MONTGOMERY_COUNTY",
        value="yes" if present else "no",
        raw_value=str(value),
            notes="WMATA routes: " + ",".join(
               extract_wmata_routes(routes)
            ),
        )


        if was_inserted:
            inserted += 1



print()
print(
    "Matched stops:",
    matched
)

print(
    "Inserted amenity records:",
    inserted
)

print(
    "Skipped:",
    skipped
)