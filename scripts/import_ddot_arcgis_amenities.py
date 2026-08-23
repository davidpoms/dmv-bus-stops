"""Dry-run-first importer for current DDOT ArcGIS shelter assets."""

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.amenities.ddot import build_source_record_id, feature_coordinates, percentile
from src.amenities.importer import insert_amenity_evidence
from src.amenities.matcher import find_nearest_physical_stop


DB = Path("src/database/dmv_bus_stops.db")
URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)
SOURCE = "DDOT_ARCGIS"
JURISDICTION = "DISTRICT_OF_COLUMBIA"

# Chosen after inspecting the live nearest-DC-stop distribution. There is no
# clean global break; 25m accepts the validated problem cases while the long
# tail remains review-only or unmatched.
ACCEPT_DISTANCE_M = 25.0
REVIEW_DISTANCE_M = 100.0
REQUIRED_UNIQUE_COLUMNS = (
    "physical_stop_id", "source", "source_record_id", "amenity_type"
)


def fetch_features():
    response = requests.get(
        URL,
        params={
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "json",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload.get("features", [])


def analyze_features(features, db=DB):
    results = []
    for feature in features:
        attrs = feature.get("attributes") or {}
        coords = feature_coordinates(feature)
        if coords is None:
            results.append({
                "status": "unmatched",
                "reason": "invalid_coordinates",
                "attributes": attrs,
            })
            continue
        latitude, longitude = coords
        source_record_id = build_source_record_id(attrs, latitude, longitude)
        match = find_nearest_physical_stop(
            db,
            latitude,
            longitude,
            jurisdiction_state="DC",
            maximum_distance_m=math.inf,
        )
        if match is None:
            results.append({
                "status": "unmatched",
                "reason": "no_dc_stop_within_review_distance",
                "attributes": attrs,
                "latitude": latitude,
                "longitude": longitude,
                "source_record_id": source_record_id,
            })
            continue
        if match["distance_m"] <= ACCEPT_DISTANCE_M:
            status = "accepted"
            reason = None
        elif match["distance_m"] <= REVIEW_DISTANCE_M:
            status = "review"
            reason = "distance_requires_review"
        else:
            status = "unmatched"
            reason = "nearest_dc_stop_beyond_review_distance"
        results.append({
            "status": status,
            "reason": reason,
            "attributes": attrs,
            "latitude": latitude,
            "longitude": longitude,
            "source_record_id": source_record_id,
            **match,
        })
    return results


def build_report(features, results):
    distances = sorted(result["distance_m"] for result in results if "distance_m" in result)
    identities = [result.get("source_record_id") for result in results if result.get("source_record_id")]
    identity_counts = Counter(identities)
    ddot_counts = Counter(
        str(result["attributes"].get("DDOT_ID"))
        for result in results
        if result.get("attributes", {}).get("DDOT_ID") is not None
    )
    accepted = [result for result in results if result["status"] == "accepted"]
    return {
        "policy": {
            "accepted_max_distance_m": ACCEPT_DISTANCE_M,
            "review_max_distance_m": REVIEW_DISTANCE_M,
        },
        "source_feature_count": len(features),
        "valid_coordinate_count": sum(feature_coordinates(feature) is not None for feature in features),
        "accepted_count": len(accepted),
        "review_count": sum(result["status"] == "review" for result in results),
        "unmatched_count": sum(result["status"] == "unmatched" for result in results),
        "distance_percentiles_m": {
            label: percentile(distances, value)
            for label, value in (
                ("min", 0), ("p25", 25), ("p50", 50), ("p75", 75),
                ("p90", 90), ("p95", 95), ("p99", 99), ("max", 100),
            )
        },
        "distance_threshold_counts": {
            str(threshold): sum(distance <= threshold for distance in distances)
            for threshold in (10, 15, 20, 25, 30, 40, 50, 75, 100)
        },
        "repeated_ddot_id_groups": sum(count > 1 for count in ddot_counts.values()),
        "distinct_source_identity_count": len(identity_counts),
        "duplicate_generated_identities": {
            identity: count for identity, count in identity_counts.items() if count > 1
        },
        "accepted_matches_by_physical_stop": dict(
            Counter(str(result["physical_stop_id"]) for result in accepted)
        ),
        "accepted_non_dc_count": sum(result.get("state") != "DC" for result in accepted),
        "results": results,
    }


def insert_accepted(results, db=DB):
    import sqlite3

    conn = sqlite3.connect(db)
    compatible_index = False
    for index in conn.execute("PRAGMA index_list(stop_amenity_evidence)"):
        if not index[2]:
            continue
        columns = tuple(
            row[2] for row in conn.execute(f"PRAGMA index_info({index[1]})")
        )
        if columns == REQUIRED_UNIQUE_COLUMNS:
            compatible_index = True
            break
    conn.close()
    if not compatible_index:
        raise RuntimeError(
            "Apply disabled: the source-record-aware unique index has not "
            "passed compatibility review or been installed."
        )

    inserted = 0
    for result in results:
        if result["status"] != "accepted":
            continue
        # Defense in depth: the matcher already selects only state='DC'.
        if result.get("state") != "DC":
            raise RuntimeError("Refusing to insert DDOT evidence outside DC")
        attrs = result["attributes"]
        metadata = dict(attrs)
        metadata.update({
            "source_latitude": result["latitude"],
            "source_longitude": result["longitude"],
            "match_policy": "nearest_dc_physical_stop",
        })
        inserted += insert_amenity_evidence(
            db,
            physical_stop_id=result["physical_stop_id"],
            source=SOURCE,
            source_record_id=result["source_record_id"],
            amenity_type="shelter",
            present=1,
            confidence=result["confidence"],
            match_distance_m=result["distance_m"],
            notes=attrs.get("Sales_Address"),
            jurisdiction=JURISDICTION,
            value="yes",
            raw_value="published_shelter_asset",
            source_metadata=json.dumps(metadata, sort_keys=True, default=str),
        )
    return inserted


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--apply", action="store_true", help="Write accepted evidence; default is dry-run")
    args = parser.parse_args(argv)
    features = fetch_features()
    results = analyze_features(features, args.db)
    report = build_report(features, results)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    if args.apply:
        print(f"Inserted evidence: {insert_accepted(results, args.db)}")
    else:
        print("DRY RUN: no database rows changed")
    return report


if __name__ == "__main__":
    main()
