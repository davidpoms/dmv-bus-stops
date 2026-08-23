"""Deprecated compatibility entry point for the safe DDOT ArcGIS importer."""

from import_ddot_arcgis_amenities import main


if __name__ == "__main__":
    main()
    raise SystemExit(0)

"""Legacy implementation retained below temporarily for source history."""

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
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": 4326,
    "f": "json"
}


raise SystemExit("Legacy implementation must not execute")

print("Fetching DDOT shelters...")


data = requests.get(
    URL,
    params=params
).json()


features = data["features"]


print(
    "DDOT shelters:",
    len(features)
)


matched = 0
inserted = 0
skipped = 0


for feature in features:

    attrs = feature["attributes"]

    lat = attrs.get("Latitude")
    lon = attrs.get("Longitude")

    if not lat or not lon:
        skipped += 1
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


    was_inserted = insert_amenity_evidence(
        DB,
        physical_stop_id=match["physical_stop_id"],
        source="DDOT",
        source_record_id=str(
            attrs.get("DDOT_SHELTER_ID")
        ),
        amenity_type="shelter",
        present=1,
        confidence=match["confidence"],
        match_distance_m=match["distance_m"],
        notes=attrs.get("Sales_Address")
    )


    if was_inserted:
        inserted += 1


print()
print(
    "Matched DDOT shelters:",
    matched
)

print(
    "Inserted evidence:",
    inserted
)

print(
    "No match:",
    skipped
)
