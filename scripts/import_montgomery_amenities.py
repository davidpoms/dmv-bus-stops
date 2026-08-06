import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

import requests

from src.amenities.importer import insert_amenity_evidence
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


AMENITY_FIELDS = {
    "SHELTERS": "shelter",
    "BENCHES": "bench",
    "TRASHCANS": "trash_can",
    "SIGNS": "sign"
}


print(
    "Fetching Montgomery County bus stops..."
)


response = requests.get(
    URL,
    params=PARAMS,
    timeout=60
)

response.raise_for_status()


data = response.json()


features = data.get(
    "features",
    []
)


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



    match = find_nearest_physical_stop(
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
            source="MONTGOMERY_COUNTY",
            source_record_id=str(
                attrs.get("STOPID")
            ),
            amenity_type=amenity_type,
            present=present,
            confidence="high",
            match_distance_m=match["distance_m"],
            notes=None
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