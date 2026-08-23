import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

import json
import requests

from src.amenities.importer import insert_amenity_evidence
from src.amenities.matcher import find_nearest_physical_stop


DB = Path(
    "src/database/dmv_bus_stops.db"
)


URL = (
    "https://geoportal.alexandriava.gov/server/rest/services/"
    "Hosted/Bus_Stops/FeatureServer/1/query"
)


PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json"
}


SOURCE = "ALEXANDRIA"

JURISDICTION = "ALEXANDRIA"


# Alexandria's explicit stop-level amenity/infrastructure fields.
#
# Fields intentionally excluded:
# - routes: transit evidence belongs elsewhere
# - ownership/maintain/tenants: contextual stop information
# - poletype/infobox/mapcase: equipment details that are not
#   currently part of the public amenity vocabulary
#
# The fields below represent conditions that are useful to the
# stop improvement / waiting-environment evidence model.

AMENITY_FIELDS = {
    "hasshelter": "shelter",
    "hasbench": "bench",
    "hastrash": "trash_can",
    "hasrecyling": "recycling",
    "hasbikerack": "bikerack",
    "hasbusbulb": "bus_bulb",
    "hasbusbay": "bus_bay",
    "hasadabuspad": "ada_bus_pad",
    "hasadapath": "ada_path",
    "hasrealtimesign": "real_time_sign",
    "hasstreetlight": "streetlight",
    "hasparking": "parking"
}


def normalize_presence(value):

    if value is None:
        return None

    text = str(value).strip().upper()

    if text in (
        "YES",
        "Y",
        "TRUE",
        "1"
    ):
        return 1

    if text in (
        "NO",
        "N",
        "FALSE",
        "0"
    ):
        return 0

    # Preserve unknown/unusual source values rather than
    # incorrectly turning them into "no".
    return None


def confidence_for_distance(distance_m):

    if distance_m <= 10:
        return "high"

    if distance_m <= 50:
        return "medium"

    return "low"


def fetch_features():

    response = requests.get(
        URL,
        params=PARAMS,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(
            "Alexandria ArcGIS error: "
            + json.dumps(data["error"])
        )

    return data.get(
        "features",
        []
    )


def main():

    print(
        "Fetching Alexandria bus stops..."
    )

    features = fetch_features()

    print(
        "Records:",
        len(features)
    )

    matched = 0
    unmatched = 0
    skipped_no_geometry = 0
    skipped_no_amenities = 0
    inserted = 0

    amenity_counts = {
        amenity_type: 0
        for amenity_type in AMENITY_FIELDS.values()
    }


    for feature in features:

        attrs = feature.get(
            "attributes",
            {}
        )

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            skipped_no_geometry += 1
            continue


        lon = geometry.get(
            "x"
        )

        lat = geometry.get(
            "y"
        )

        if lat is None or lon is None:
            skipped_no_geometry += 1
            continue


        source_metadata = dict(
            attrs
        )

        source_metadata["source_lat"] = lat
        source_metadata["source_lon"] = lon

        source_metadata = json.dumps(
            source_metadata,
            separators=(",", ":")
        )


        match = find_nearest_physical_stop(
            DB,
            lat,
            lon
        )


        if not match:
            unmatched += 1
            continue


        matched += 1


        stop_id = match[
            "physical_stop_id"
        ]

        distance_m = match[
            "distance_m"
        ]

        confidence = confidence_for_distance(
            distance_m
        )


        record_id = (
            attrs.get("stopid")
            or attrs.get("facilityid")
            or attrs.get("objectid")
        )


        notes_parts = [
            "Alexandria City bus stop inventory."
        ]


        stop_name = attrs.get(
            "stopname"
        )

        nearest_address = attrs.get(
            "nearestaddress"
        )

        if stop_name:
            notes_parts.append(
                "Source stop: " + str(stop_name)
            )

        if nearest_address:
            notes_parts.append(
                "Address: " + str(nearest_address)
            )


        inserted_for_stop = 0


        for field, amenity_type in AMENITY_FIELDS.items():

            raw_value = attrs.get(
                field
            )

            if raw_value is None:
                continue


            present = normalize_presence(
                raw_value
            )


            # Alexandria occasionally uses values such as
            # UNKNOWN rather than YES/NO. Do not manufacture
            # a presence/absence determination from those.
            if present is None:
                continue


            was_inserted = insert_amenity_evidence(
                DB,
                physical_stop_id=stop_id,
                source=SOURCE,
                source_record_id=str(
                    record_id
                ),
                amenity_type=amenity_type,
                present=present,
                confidence=confidence,
                match_distance_m=distance_m,
                jurisdiction=JURISDICTION,
                value=(
                    "yes"
                    if present
                    else "no"
                ),
                raw_value=str(
                    raw_value
                ),
                source_metadata=source_metadata,
                notes=" ".join(
                    notes_parts
                )
            )


            if was_inserted:
                inserted += 1
                inserted_for_stop += 1
                amenity_counts[
                    amenity_type
                ] += 1


        if inserted_for_stop == 0:
            skipped_no_amenities += 1


    print()
    print(
        "Matched stops:",
        matched
    )

    print(
        "Unmatched:",
        unmatched
    )

    print(
        "Skipped no geometry:",
        skipped_no_geometry
    )

    print(
        "Matched stops with no usable amenity values:",
        skipped_no_amenities
    )

    print(
        "Inserted amenity records:",
        inserted
    )

    print()
    print(
        "Inserted by amenity:"
    )

    for amenity_type, count in amenity_counts.items():

        print(
            f"  {amenity_type}: {count}"
        )


if __name__ == "__main__":
    main()
