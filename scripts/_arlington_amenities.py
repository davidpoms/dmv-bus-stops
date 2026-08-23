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
    "https://arlgis.arlingtonva.us/arcgis/rest/services/"
    "Open_Data/od_Bus_Stop_Points/FeatureServer/0/query"
)


BASE_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json"
}


SOURCE = "ARLINGTON_COUNTY"
JURISDICTION = "ARLINGTON_COUNTY"

PAGE_SIZE = 1000


def normalize_yes_no(value):

    if value is None:
        return None

    text = str(value).strip().upper()

    if text in ("1", "YES", "Y", "TRUE"):
        return 1

    if text in ("0", "NO", "N", "FALSE"):
        return 0

    return None


def normalize_boarding_pad(front, rear):

    front_text = (
        str(front).strip().upper()
        if front is not None
        else ""
    )

    rear_text = (
        str(rear).strip().upper()
        if rear is not None
        else ""
    )

    positive_values = {
        ">= 5X8",
        "< 5X8",
        "YES",
        "Y"
    }

    negative_values = {
        "NO",
        "N",
        "NONE"
    }

    if (
        front_text in positive_values
        or rear_text in positive_values
    ):
        return 1

    if (
        front_text in negative_values
        and rear_text in negative_values
    ):
        return 0

    if (
        front_text in negative_values
        and rear_text in ("", "N/A")
    ):
        return 0

    if (
        rear_text in negative_values
        and front_text in ("", "N/A")
    ):
        return 0

    return None


def normalize_ada_path(sidewalk, curb_ramp):

    sidewalk_value = normalize_yes_no(
        sidewalk
    )

    curb_ramp_value = normalize_yes_no(
        curb_ramp
    )

    if (
        sidewalk_value == 1
        and curb_ramp_value == 1
    ):
        return 1

    if (
        sidewalk_value == 0
        and curb_ramp_value == 0
    ):
        return 0

    return None


def confidence_for_distance(distance_m):

    if distance_m <= 10:
        return "high"

    if distance_m <= 50:
        return "medium"

    return "low"


def fetch_features():

    all_features = []
    offset = 0

    while True:

        print(
            f"Fetching Arlington records "
            f"{offset}-{offset + PAGE_SIZE - 1}..."
        )

        params = BASE_PARAMS.copy()

        params.update(
            {
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE
            }
        )

        response = requests.get(
            URL,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(
                "Arlington ArcGIS error: "
                + json.dumps(
                    data["error"]
                )
            )

        page = data.get(
            "features",
            []
        )

        all_features.extend(
            page
        )

        if len(page) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return all_features


def main():

    print(
        "Fetching Arlington bus stops..."
    )

    features = fetch_features()

    print(
        "Records:",
        len(features)
    )

    matched = 0
    unmatched = 0
    skipped_inactive = 0
    skipped_no_geometry = 0
    skipped_no_amenities = 0
    inserted = 0

    amenity_counts = {
        "ada_bus_pad": 0,
        "ada_path": 0
    }


    for feature in features:

        attrs = feature.get(
            "attributes",
            {}
        )

        status = (
            str(
                attrs.get("Status")
            ).strip().upper()
            if attrs.get("Status") is not None
            else ""
        )

        if status != "NORMAL":
            skipped_inactive += 1
            continue


        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            skipped_no_geometry += 1
            continue


        lon = geometry.get("x")
        lat = geometry.get("y")

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
            attrs.get("RegionalID")
            or attrs.get("ID")
            or attrs.get("OBJECTID")
        )


        address = attrs.get(
            "AddressNumber"
        )

        on_street = attrs.get(
            "OnStreet"
        )

        at_street = attrs.get(
            "AtStreet"
        )

        notes_parts = [
            "Arlington County bus stop inventory."
        ]

        if on_street:
            notes_parts.append(
                "On street: "
                + str(on_street)
            )

        if at_street:
            notes_parts.append(
                "At street: "
                + str(at_street)
            )

        if address is not None:
            notes_parts.append(
                "Address number: "
                + str(address)
            )


        boarding_pad = normalize_boarding_pad(
            attrs.get("FrontBoardingPad"),
            attrs.get("RearBoardingPad")
        )

        ada_path = normalize_ada_path(
            attrs.get("SidewalkConnect"),
            attrs.get("CurbRamp")
        )


        records = []


        if boarding_pad is not None:

            records.append(
                (
                    "ada_bus_pad",
                    boarding_pad,
                    "Arlington boarding pad inventory."
                )
            )


        if ada_path is not None:

            records.append(
                (
                    "ada_path",
                    ada_path,
                    "Arlington sidewalk/curb-ramp inventory."
                )
            )


        if not records:
            skipped_no_amenities += 1
            continue


        for amenity_type, present, amenity_note in records:

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
                raw_value=(
                    "YES"
                    if present
                    else "NO"
                ),
                source_metadata=source_metadata,
                notes=(
                    " ".join(notes_parts)
                    + " "
                    + amenity_note
                )
            )


            if was_inserted:

                inserted += 1

                amenity_counts[
                    amenity_type
                ] += 1


    print()
    print(
        "Matched active stops:",
        matched
    )

    print(
        "Unmatched:",
        unmatched
    )

    print(
        "Skipped inactive:",
        skipped_inactive
    )

    print(
        "Skipped no geometry:",
        skipped_no_geometry
    )

    print(
        "Matched stops with no usable accessibility values:",
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
